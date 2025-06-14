import asyncio
import json
from datetime import datetime
from typing import Dict, List

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse

from app.models import (
    ErrorResponse,
    MinutesTask,
    ProcessingStepName,
    ProcessingStepStatus,
    TaskListResponse,
    TaskResultResponse,
    TaskStatus,
    TaskStatusResponse,
    UploadResponse,
)
from app.services.minutes_generator import MinutesGeneratorService
from app.services.transcription import TranscriptionService
from app.services.video_processor import VideoProcessor
from app.utils.file_handler import FileHandler
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# グローバルタスクストア（共有ストアから参照）
from app.store import tasks_store

# WebSocket接続管理
websocket_connections: Dict[str, List[WebSocket]] = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_media(file: UploadFile = File(...)):
    """動画・音声ファイルをアップロードして処理を開始"""

    logger.info(
        f"ファイルアップロード開始: {file.filename} (サイズ: {file.size} bytes)"
    )

    try:
        # ファイルバリデーション（動画・音声両方対応）
        file_type = FileHandler.validate_media_file(file)
        logger.info(f"ファイルバリデーション成功: {file.filename} (タイプ: {file_type})")

        # タスクIDを生成
        task_id = FileHandler.generate_task_id()
        logger.info(f"タスクID生成: {task_id}")

        # ファイルを保存
        file_path, file_size = await FileHandler.save_uploaded_file(file, task_id)
        logger.info(f"ファイル保存完了: {file_path} ({file_size} bytes)")

        # タスクを作成
        task = MinutesTask(
            task_id=task_id,
            video_filename=file.filename,
            video_size=file_size,
            upload_timestamp=datetime.now(),
        )

        # アップロード完了をマーク
        task.update_step_status(
            ProcessingStepName.UPLOAD, ProcessingStepStatus.COMPLETED, 100
        )

        # タスクストアに保存
        tasks_store[task_id] = task

        logger.info(f"タスク作成完了: {task_id} - {file.filename}")

        # タスクキューに追加（ファイルタイプに応じた処理）
        from app.services.task_queue import get_task_queue

        queue = get_task_queue()
        if file_type == "video":
            queue_id = await queue.add_task(task_id, process_video_task, task_id)
        else:  # audio
            queue_id = await queue.add_task(task_id, process_audio_task, task_id)

        logger.info(f"タスクをキューに追加: {task_id} (キューID: {queue_id}, タイプ: {file_type})")

        return UploadResponse(task_id=task_id, status=TaskStatus.QUEUED)

    except HTTPException as e:
        logger.warning(f"ファイルアップロードHTTPエラー: {file.filename} - {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"ファイルアップロードエラー: {file.filename} - {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"アップロード中にエラーが発生しました: {str(e)}"
        )


@router.get("/tasks", response_model=TaskListResponse)
async def get_all_tasks():
    """全タスクの一覧を取得"""
    logger.info(f"タスク一覧取得: {len(tasks_store)}件のタスク")
    tasks = list(tasks_store.values())
    # 新しい順にソート
    tasks.sort(key=lambda x: x.upload_timestamp, reverse=True)
    return TaskListResponse(tasks=tasks)


@router.get("/queue/status")
async def get_queue_status():
    """タスクキューの状態を取得"""
    from app.services.task_queue import get_task_queue

    queue = get_task_queue()
    return queue.get_queue_status()


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """特定タスクのステータスを取得"""
    logger.debug(f"タスクステータス取得: {task_id}")

    if task_id not in tasks_store:
        logger.warning(f"タスクが見つかりません: {task_id}")
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")

    task = tasks_store[task_id]
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        current_step=task.current_step,
        overall_progress=task.overall_progress,
        steps=task.steps,
        video_filename=task.video_filename,
        upload_timestamp=task.upload_timestamp,
        error_message=task.error_message,
    )


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """完了したタスクの結果を取得"""
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")

    task = tasks_store[task_id]

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="タスクがまだ完了していません")

    if not task.transcription or not task.minutes:
        raise HTTPException(status_code=500, detail="処理結果が見つかりません")

    return TaskResultResponse(
        task_id=task.task_id,
        video_filename=task.video_filename,
        transcription=task.transcription,
        minutes=task.minutes,
        upload_timestamp=task.upload_timestamp,
    )


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """タスクを削除"""
    logger.info(f"タスク削除要求: {task_id}")
    
    if task_id not in tasks_store:
        logger.warning(f"削除対象のタスクが見つかりません: {task_id}")
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")

    task = tasks_store[task_id]
    
    # 処理中のタスクは削除できない
    if task.status == TaskStatus.PROCESSING:
        logger.warning(f"処理中のタスクは削除できません: {task_id}")
        raise HTTPException(status_code=400, detail="処理中のタスクは削除できません")
    
    try:
        # ファイルクリーンアップ
        FileHandler.cleanup_files(task_id)
        logger.info(f"ファイルクリーンアップ完了: {task_id}")
        
        # タスクストアから削除
        del tasks_store[task_id]
        logger.info(f"タスク削除完了: {task_id}")
        
        # WebSocket接続がある場合は削除
        if task_id in websocket_connections:
            del websocket_connections[task_id]
            logger.info(f"WebSocket接続削除完了: {task_id}")
        
        return JSONResponse(
            status_code=200,
            content={"message": f"タスク {task_id} を削除しました"}
        )
        
    except Exception as e:
        logger.error(f"タスク削除エラー: {task_id} - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"タスクの削除中にエラーが発生しました: {str(e)}"
        )


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket接続でリアルタイム進捗を配信"""
    await websocket.accept()

    # 接続を管理リストに追加
    if task_id not in websocket_connections:
        websocket_connections[task_id] = []
    websocket_connections[task_id].append(websocket)

    try:
        while True:
            # 接続を維持（クライアントからのメッセージを受信）
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 接続が切断された場合は管理リストから削除
        if task_id in websocket_connections:
            websocket_connections[task_id].remove(websocket)
            if not websocket_connections[task_id]:
                del websocket_connections[task_id]


async def process_video_task(task_id: str):
    """動画処理のメインタスク"""
    if task_id not in tasks_store:
        return

    task = tasks_store[task_id]

    try:
        # ステータスを処理中に変更
        task.status = TaskStatus.PROCESSING
        await broadcast_progress_update(task_id, task)

        # 1. 音声抽出
        task.update_step_status(
            ProcessingStepName.AUDIO_EXTRACTION, ProcessingStepStatus.PROCESSING
        )
        await broadcast_progress_update(task_id, task)

        video_processor = VideoProcessor()
        audio_path = await video_processor.extract_audio(task_id)

        task.update_step_status(
            ProcessingStepName.AUDIO_EXTRACTION, ProcessingStepStatus.COMPLETED, 100
        )
        await broadcast_progress_update(task_id, task)

        # 2. 文字起こし
        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.PROCESSING
        )
        await broadcast_progress_update(task_id, task)

        transcription_service = TranscriptionService()
        transcription = await transcription_service.transcribe_audio(audio_path)
        task.transcription = transcription

        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.COMPLETED, 100
        )
        await broadcast_progress_update(task_id, task)

        # 3. 議事録生成
        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.PROCESSING
        )
        await broadcast_progress_update(task_id, task)

        minutes_service = MinutesGeneratorService()
        minutes = await minutes_service.generate_minutes(transcription)
        task.minutes = minutes

        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.COMPLETED, 100
        )

        # 最終的な進捗更新を送信
        await broadcast_progress_update(task_id, task)

        # 完了通知
        await broadcast_task_completed(task_id, task)

    except Exception as e:
        # エラー処理
        error_message = f"処理中にエラーが発生しました: {str(e)}"
        task.status = TaskStatus.FAILED
        task.error_message = error_message

        # 現在のステップをエラーに設定
        if task.current_step:
            task.update_step_status(
                task.current_step,
                ProcessingStepStatus.FAILED,
                error_message=error_message,
            )

        await broadcast_task_failed(task_id, task, error_message)

    finally:
        # ファイルクリーンアップ
        FileHandler.cleanup_files(task_id)


async def process_audio_task(task_id: str):
    """音声処理のメインタスク"""
    if task_id not in tasks_store:
        return

    task = tasks_store[task_id]

    try:
        # ステータスを処理中に変更
        task.status = TaskStatus.PROCESSING
        await broadcast_progress_update(task_id, task)

        # 音声ファイルの場合は音声抽出をスキップ
        logger.info(f"音声ファイル処理開始: {task_id}")

        # 音声ファイルのパスを取得
        audio_path = FileHandler.get_file_path(task_id)
        if not audio_path:
            raise Exception("音声ファイルが見つかりません")

        # 音声抽出ステップをスキップしてCOMPLETEDに設定
        task.update_step_status(
            ProcessingStepName.AUDIO_EXTRACTION, ProcessingStepStatus.COMPLETED, 100
        )
        await broadcast_progress_update(task_id, task)

        # 文字起こし
        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.PROCESSING
        )
        await broadcast_progress_update(task_id, task)

        transcription_service = TranscriptionService()
        transcription = await transcription_service.transcribe_audio(audio_path)
        task.transcription = transcription

        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.COMPLETED, 100
        )
        await broadcast_progress_update(task_id, task)

        # 議事録生成
        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.PROCESSING
        )
        await broadcast_progress_update(task_id, task)

        minutes_service = MinutesGeneratorService()
        minutes = await minutes_service.generate_minutes(transcription)
        task.minutes = minutes

        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.COMPLETED, 100
        )

        # 最終的な進捗更新を送信
        await broadcast_progress_update(task_id, task)

        # 完了通知
        await broadcast_task_completed(task_id, task)

    except Exception as e:
        # エラー処理
        error_message = f"音声処理中にエラーが発生しました: {str(e)}"
        task.status = TaskStatus.FAILED
        task.error_message = error_message

        # 現在のステップをエラーに設定
        if task.current_step:
            task.update_step_status(
                task.current_step,
                ProcessingStepStatus.FAILED,
                error_message=error_message,
            )

        await broadcast_task_failed(task_id, task, error_message)

    finally:
        # ファイルクリーンアップ
        FileHandler.cleanup_files(task_id)


async def broadcast_progress_update(task_id: str, task: MinutesTask):
    """進捗更新をWebSocketクライアントに配信"""
    if task_id not in websocket_connections:
        return

    message = {
        "type": "progress_update",
        "task_id": task_id,
        "data": {
            "status": task.status,
            "current_step": task.current_step,
            "overall_progress": task.overall_progress,
            "steps": [step.model_dump() for step in task.steps],
        },
    }

    # 接続中の全クライアントに配信
    disconnected = []
    for websocket in websocket_connections[task_id]:
        try:
            await websocket.send_text(json.dumps(message))
        except:
            disconnected.append(websocket)

    # 切断されたWebSocketを削除
    for ws in disconnected:
        websocket_connections[task_id].remove(ws)


async def broadcast_task_completed(task_id: str, task: MinutesTask):
    """タスク完了をWebSocketクライアントに配信"""
    if task_id not in websocket_connections:
        logger.warning(f"WebSocket接続が見つかりません: {task_id}")
        return

    logger.info(f"タスク完了をWebSocketで配信: {task_id}")

    message = {
        "type": "task_completed",
        "task_id": task_id,
        "data": {
            "status": task.status,
            "video_filename": task.video_filename,
            "overall_progress": task.overall_progress,
            "steps": [step.model_dump() for step in task.steps],
            "message": f"{task.video_filename}の議事録生成が完了しました",
        },
    }

    disconnected = []
    for websocket in websocket_connections[task_id]:
        try:
            await websocket.send_text(json.dumps(message))
            logger.debug(f"WebSocketメッセージ送信成功: {task_id}")
        except Exception as e:
            logger.error(f"WebSocketメッセージ送信失敗: {task_id} - {str(e)}")
            disconnected.append(websocket)

    # 切断されたWebSocketを削除
    for ws in disconnected:
        websocket_connections[task_id].remove(ws)

    logger.info(
        f"WebSocket配信完了: {task_id} (接続数: {len(websocket_connections[task_id])})"
    )


async def broadcast_task_failed(task_id: str, task: MinutesTask, error_message: str):
    """タスク失敗をWebSocketクライアントに配信"""
    if task_id not in websocket_connections:
        return

    message = {
        "type": "task_failed",
        "task_id": task_id,
        "data": {
            "video_filename": task.video_filename,
            "error_message": error_message,
            "message": f"{task.video_filename}の処理中にエラーが発生しました",
        },
    }

    disconnected = []
    for websocket in websocket_connections[task_id]:
        try:
            await websocket.send_text(json.dumps(message))
            logger.debug(f"WebSocketメッセージ送信成功: {task_id}")
        except Exception as e:
            logger.error(f"WebSocketメッセージ送信失敗: {task_id} - {str(e)}")
            disconnected.append(websocket)

    # 切断されたWebSocketを削除
    for ws in disconnected:
        websocket_connections[task_id].remove(ws)

    logger.info(
        f"WebSocket配信完了: {task_id} (接続数: {len(websocket_connections[task_id])})"
    )
