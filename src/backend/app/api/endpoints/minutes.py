import json
from datetime import datetime
from typing import Dict, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse

from app.models import (
    MinutesTask,
    ProcessingStepName,
    ProcessingStepStatus,
    TaskListResponse,
    TaskResultResponse,
    TaskStatus,
    TaskStatusResponse,
    UploadResponse,
)
from app.models.chat import EditMinutesRequest, EditMinutesResponse, EditHistory
from app.services.minutes_generator import MinutesGeneratorService
from app.services.transcription import TranscriptionService
from app.services.video_processor import VideoProcessor
from app.utils.file_handler import FileHandler
from app.store import tasks_store
from app.store.session_store import session_task_store
from app.store.persistent_store import persistent_store
from app.utils.session_manager import SessionManager
from app.utils.logger import get_logger
from app.utils.timezone_utils import TimezoneUtils
from app.auth.api_key import get_api_key, get_optional_api_key
from app.config import settings

router = APIRouter()
logger = get_logger(__name__)

# WebSocket接続管理 (task_id -> [WebSocket]) - 従来の方式を維持
websocket_connections: Dict[str, List[WebSocket]] = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_media(
    request: Request, 
    file: UploadFile = File(...),
    api_key: str = Depends(get_api_key) if settings.auth_enabled else None
) -> UploadResponse:
    """動画・音声ファイルをアップロードして処理を開始"""

    # セッションIDを取得
    session_id = SessionManager.get_session_id(request)

    logger.info(
        f"ファイルアップロード開始: {file.filename} (サイズ: {file.size} bytes) (セッション: {session_id[:8]}...)"
    )

    try:
        # ファイルバリデーション（動画・音声両方対応）
        file_type = FileHandler.validate_media_file(file)
        logger.info(
            f"ファイルバリデーション成功: {file.filename} (タイプ: {file_type})"
        )

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
            upload_timestamp=TimezoneUtils.now(),
        )

        # アップロード完了をマーク
        task.update_step_status(
            ProcessingStepName.UPLOAD, ProcessingStepStatus.COMPLETED, 100
        )

        # セッションベースタスクストアに保存
        session_task_store.add_task(session_id, task)
        # 下位互換性のため従来のタスクストアにも保存
        tasks_store[task_id] = task
        # 永続化ストアにも直接保存（二重保存防止のためtry-catchで囲む）
        try:
            if task_id not in persistent_store.get_all_tasks():
                persistent_store.add_task(session_id, task)
        except Exception as e:
            logger.warning(f"従来タスクストアからの永続化追加に失敗: {e}")

        logger.info(f"タスク作成完了: {task_id} - {file.filename} (セッション: {session_id[:8]}...)")

        # タスクキューに追加（ファイルタイプに応じた処理）
        from app.services.task_queue import get_task_queue

        queue = get_task_queue()
        if file_type == "video":
            queue_id = await queue.add_task(task_id, process_video_task, task_id)
        else:  # audio
            queue_id = await queue.add_task(task_id, process_audio_task, task_id)

        logger.info(
            f"タスクをキューに追加: {task_id} (キューID: {queue_id}, タイプ: {file_type})"
        )

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


@router.options("/tasks")
async def options_tasks():
    """CORS preflight request handler for tasks endpoint"""
    return {"message": "OK"}

@router.get("/tasks", response_model=TaskListResponse)
async def get_all_tasks(
    request: Request,
    api_key: str = Depends(get_api_key) if settings.auth_enabled else None
) -> TaskListResponse:
    """現在のセッションのタスク一覧を取得"""
    session_id = SessionManager.get_session_id(request)
    tasks = session_task_store.get_tasks(session_id)

    logger.info(f"タスク一覧取得: {len(tasks)}件のタスク (セッション: {session_id[:8]}...)")
    
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
async def get_task_status(
    request: Request, 
    task_id: str,
    api_key: str = Depends(get_api_key) if settings.auth_enabled else None
) -> TaskStatusResponse:
    """特定タスクのステータスを取得"""
    session_id = SessionManager.get_session_id(request)
    logger.debug(f"タスクステータス取得: {task_id} (セッション: {session_id[:8]}...)")

    # まずセッションストアから検索
    task = session_task_store.get_task(session_id, task_id)
    
    # セッションストアで見つからない場合は、従来のタスクストアから検索（下位互換性）
    if not task:
        logger.debug(f"セッションストアで見つからないため、従来のタスクストアを検索: {task_id}")
        task = tasks_store.get(task_id)
        if task:
            logger.info(f"従来のタスクストアからタスクを発見、セッションに移行: {task_id} -> セッション: {session_id[:8]}...")
            # セッションストアに移行
            session_task_store.add_task(session_id, task)
    
    # 他のセッションでタスクが見つからない場合、全セッションを検索
    if not task:
        logger.debug(f"全セッションを検索してタスクを探します: {task_id}")
        for other_session_id, session_tasks in session_task_store._sessions.items():
            if task_id in session_tasks:
                task = session_tasks[task_id]
                logger.info(f"他のセッションでタスクを発見、現在のセッションに移行: {task_id} from {other_session_id[:8]}... to {session_id[:8]}...")
                # 現在のセッションに移行
                session_task_store.add_task(session_id, task)
                break
    
    if not task:
        logger.warning(f"タスクが見つかりません: {task_id} (セッション: {session_id[:8]}...)")
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")
        
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
async def get_task_result(
    request: Request, 
    task_id: str,
    api_key: str = Depends(get_api_key) if settings.auth_enabled else None
) -> TaskResultResponse:
    """完了したタスクの結果を取得"""
    session_id = SessionManager.get_session_id(request)
    
    # まずセッションストアから検索
    task = session_task_store.get_task(session_id, task_id)
    
    # セッションストアで見つからない場合は、従来のタスクストアから検索（下位互換性）
    if not task:
        logger.debug(f"セッションストアで見つからないため、従来のタスクストアを検索: {task_id}")
        task = tasks_store.get(task_id)
        if task:
            logger.info(f"従来のタスクストアからタスクを発見、セッションに移行: {task_id} -> セッション: {session_id[:8]}...")
            # セッションストアに移行
            session_task_store.add_task(session_id, task)
    
    # 他のセッションでタスクが見つからない場合、全セッションを検索
    if not task:
        logger.debug(f"全セッションを検索してタスクを探します: {task_id}")
        for other_session_id, session_tasks in session_task_store._sessions.items():
            if task_id in session_tasks:
                task = session_tasks[task_id]
                logger.info(f"他のセッションでタスクを発見、現在のセッションに移行: {task_id} from {other_session_id[:8]}... to {session_id[:8]}...")
                # 現在のセッションに移行
                session_task_store.add_task(session_id, task)
                break
    
    if not task:
        logger.warning(f"タスクが見つかりません: {session_id[:8]}... -> {task_id}")
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")

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
async def delete_task(
    request: Request, 
    task_id: str,
    api_key: str = Depends(get_api_key) if settings.auth_enabled else None
) -> JSONResponse:
    """タスクを削除"""
    session_id = SessionManager.get_session_id(request)
    logger.info(f"タスク削除要求: {task_id} (セッション: {session_id[:8]}...)")

    # まずセッションストアから検索
    task = session_task_store.get_task(session_id, task_id)
    
    # セッションストアで見つからない場合は、従来のタスクストアから検索（下位互換性）
    if not task:
        logger.debug(f"セッションストアで見つからないため、従来のタスクストアを検索: {task_id}")
        task = tasks_store.get(task_id)
        if task:
            logger.info(f"従来のタスクストアからタスクを発見、セッションに移行: {task_id} -> セッション: {session_id[:8]}...")
            # セッションストアに移行
            session_task_store.add_task(session_id, task)
    
    if not task:
        logger.warning(f"削除対象のタスクが見つかりません: {task_id} (セッション: {session_id[:8]}...)")
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")

    # 処理中のタスクは削除できない
    if task.status == TaskStatus.PROCESSING:
        logger.warning(f"処理中のタスクは削除できません: {task_id}")
        raise HTTPException(status_code=400, detail="処理中のタスクは削除できません")

    try:
        # ファイルクリーンアップ
        FileHandler.cleanup_files(task_id)
        logger.info(f"ファイルクリーンアップ完了: {task_id}")

        # セッションベースタスクストアから削除
        session_task_store.delete_task(session_id, task_id)
        # 下位互換性のため従来のタスクストアからも削除
        if task_id in tasks_store:
            del tasks_store[task_id]
        logger.info(f"タスク削除完了: {task_id} (セッション: {session_id[:8]}...)")

        # WebSocket接続がある場合は削除
        if task_id in websocket_connections:
            del websocket_connections[task_id]
            logger.info(f"WebSocket接続削除完了: {task_id} (セッション: {session_id[:8]}...)")

        return JSONResponse(
            status_code=200, content={"message": f"タスク {task_id} を削除しました"}
        )

    except Exception as e:
        logger.error(f"タスク削除エラー: {task_id} - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"タスクの削除中にエラーが発生しました: {str(e)}"
        )


@router.post("/{task_id}/retry")
async def retry_task(request: Request, task_id: str) -> JSONResponse:
    """失敗したタスクを再実行"""
    session_id = SessionManager.get_session_id(request)
    logger.info(f"タスク再実行要求: {task_id} (セッション: {session_id[:8]}...)")

    # まずセッションストアから検索
    task = session_task_store.get_task(session_id, task_id)
    
    # セッションストアで見つからない場合は、従来のタスクストアから検索（下位互換性）
    if not task:
        logger.debug(f"セッションストアで見つからないため、従来のタスクストアを検索: {task_id}")
        task = tasks_store.get(task_id)
        if task:
            logger.info(f"従来のタスクストアからタスクを発見、セッションに移行: {task_id} -> セッション: {session_id[:8]}...")
            # セッションストアに移行
            session_task_store.add_task(session_id, task)
    
    if not task:
        logger.warning(f"再実行対象のタスクが見つかりません: {task_id} (セッション: {session_id[:8]}...)")
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")

    # 失敗したタスクのみ再実行可能
    if task.status != TaskStatus.FAILED:
        logger.warning(f"失敗していないタスクは再実行できません: {task_id} (現在のステータス: {task.status})")
        raise HTTPException(status_code=400, detail="失敗したタスクのみ再実行できます")

    try:
        # タスクを初期状態にリセット
        task.status = TaskStatus.QUEUED
        task.error_message = None
        task.current_step = None
        task.overall_progress = 0
        task.transcription = None
        task.minutes = None
        
        # すべてのステップをリセット
        task.steps = []
        
        # アップロード完了をマーク（ファイルは既に存在するため）
        task.update_step_status(
            ProcessingStepName.UPLOAD, ProcessingStepStatus.COMPLETED, 100
        )

        # セッションベースタスクストアを更新
        session_task_store.update_task(session_id, task)
        # 下位互換性のため従来のタスクストアも更新
        tasks_store[task_id] = task

        logger.info(f"タスクリセット完了: {task_id} (セッション: {session_id[:8]}...)")

        # タスクキューに再追加
        from app.services.task_queue import get_task_queue

        queue = get_task_queue()
        
        # ファイルの種類を判定（ファイル名から）
        if task.video_filename:
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
            is_video = any(task.video_filename.lower().endswith(ext) for ext in video_extensions)
            
            if is_video:
                queue_id = await queue.add_task(task_id, process_video_task, task_id)
                logger.info(f"動画タスクとしてキューに再追加: {task_id} (キューID: {queue_id})")
            else:
                queue_id = await queue.add_task(task_id, process_audio_task, task_id)
                logger.info(f"音声タスクとしてキューに再追加: {task_id} (キューID: {queue_id})")
        else:
            # ファイル名が不明な場合はデフォルトで動画処理
            queue_id = await queue.add_task(task_id, process_video_task, task_id)
            logger.info(f"デフォルト（動画）タスクとしてキューに再追加: {task_id} (キューID: {queue_id})")

        return JSONResponse(
            status_code=200, 
            content={
                "message": f"タスク {task_id} の再実行を開始しました",
                "task_id": task_id,
                "status": task.status.value
            }
        )

    except Exception as e:
        logger.error(f"タスク再実行エラー: {task_id} - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"タスクの再実行中にエラーが発生しました: {str(e)}"
        )


@router.post("/{task_id}/regenerate")
async def regenerate_minutes(request: Request, task_id: str) -> JSONResponse:
    """文字起こしから議事録を再生成"""
    session_id = SessionManager.get_session_id(request)
    logger.info(f"議事録再生成要求: {task_id} (セッション: {session_id[:8]}...)")

    # セッションストアから検索
    task = session_task_store.get_task(session_id, task_id)
    
    # セッションストアで見つからない場合は、従来のタスクストアから検索
    if not task:
        logger.debug(f"セッションストアで見つからないため、従来のタスクストアを検索: {task_id}")
        task = tasks_store.get(task_id)
        if task:
            logger.info(f"従来のタスクストアからタスクを発見、セッションに移行: {task_id} -> セッション: {session_id[:8]}...")
            # セッションストアに移行
            session_task_store.add_task(session_id, task)
    
    if not task:
        logger.warning(f"再生成対象のタスクが見つかりません: {task_id} (セッション: {session_id[:8]}...)")
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません")

    # 完了したタスクで文字起こしが存在する場合のみ再生成可能
    if task.status != TaskStatus.COMPLETED:
        logger.warning(f"完了していないタスクは再生成できません: {task_id} (現在のステータス: {task.status})")
        raise HTTPException(status_code=400, detail="完了したタスクのみ再生成できます")
    
    if not task.transcription:
        logger.warning(f"文字起こしが存在しないため再生成できません: {task_id}")
        raise HTTPException(status_code=400, detail="文字起こしが存在しないため再生成できません")

    try:
        logger.info(f"議事録再生成開始: {task_id} (セッション: {session_id[:8]}...)")
        
        # 議事録生成サービスを使用
        minutes_generator = MinutesGeneratorService()
        new_minutes = await minutes_generator.generate_minutes(task.transcription)
        
        # タスクの議事録を更新
        task.minutes = new_minutes
        if hasattr(task, 'updated_at'):
            task.updated_at = TimezoneUtils.now()
        
        # セッションベースタスクストアを更新
        session_task_store.update_task(session_id, task)
        # 下位互換性のため従来のタスクストアも更新
        tasks_store[task_id] = task
        
        # 永続ストアも更新
        persistent_store.update_task(session_id, task)

        logger.info(f"議事録再生成完了: {task_id} (セッション: {session_id[:8]}...)")

        return JSONResponse(
            status_code=200,
            content={
                "message": f"議事録の再生成が完了しました",
                "task_id": task_id,
                "video_filename": task.video_filename,
                "transcription": task.transcription,
                "minutes": task.minutes,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        )

    except Exception as e:
        logger.error(f"議事録再生成エラー: {task_id} - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"議事録の再生成中にエラーが発生しました: {str(e)}"
        )


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket接続でリアルタイム進捗を配信"""
    await websocket.accept()

    # タスクが存在するかチェック（セッションストアと従来のタスクストア両方をチェック）
    task_found = False
    
    # 従来のタスクストアでチェック
    if task_id in tasks_store:
        task_found = True
    else:
        # セッションストアでもチェック
        for session_tasks in session_task_store._sessions.values():
            if task_id in session_tasks:
                task_found = True
                break
    
    if not task_found:
        await websocket.close(code=4004, reason="Task not found")
        return

    # 接続を管理リストに追加（従来の方式を維持）
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


async def process_video_task(task_id: str) -> None:
    """動画処理のメインタスク"""
    # タスクを取得（従来のタスクストアから）
    if task_id not in tasks_store:
        logger.error(f"処理対象のタスクが見つかりません: {task_id}")
        return

    task = tasks_store[task_id]

    # セッションIDを見つけてタスクを更新する関数
    def update_session_task():
        updated = False
        for session_id, session_tasks in session_task_store._sessions.items():
            if task_id in session_tasks:
                session_task_store.update_task(session_id, task)
                updated = True
        
        # セッションストアにない場合でも従来のタスクストアは更新
        tasks_store[task_id] = task
        
        # 永続化ストアも更新
        try:
            # どのセッションにタスクが属するかを特定
            for session_id in persistent_store._sessions_cache:
                if task_id in persistent_store._sessions_cache[session_id]:
                    persistent_store.update_task(session_id, task)
                    break
        except Exception as e:
            logger.warning(f"プロセス中の永続化更新に失敗: {e}")
        
        return updated

    try:
        # ステータスを処理中に変更
        task.status = TaskStatus.PROCESSING
        update_session_task()
        await broadcast_progress_update(task_id, task)

        # 1. 音声抽出
        task.update_step_status(
            ProcessingStepName.AUDIO_EXTRACTION, ProcessingStepStatus.PROCESSING
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        video_processor = VideoProcessor()
        audio_path = await video_processor.extract_audio(task_id)

        task.update_step_status(
            ProcessingStepName.AUDIO_EXTRACTION, ProcessingStepStatus.COMPLETED, 100
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        # 2. 文字起こし
        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.PROCESSING
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        transcription_service = TranscriptionService()
        transcription = await transcription_service.transcribe_audio(audio_path)
        task.transcription = transcription

        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.COMPLETED, 100
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        # 3. 議事録生成
        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.PROCESSING
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        minutes_service = MinutesGeneratorService()
        minutes = await minutes_service.generate_minutes(transcription)
        task.minutes = minutes

        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.COMPLETED, 100
        )
        update_session_task()

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

        update_session_task()
        await broadcast_task_failed(task_id, task, error_message)

    finally:
        # ファイルクリーンアップ
        FileHandler.cleanup_files(task_id)


async def process_audio_task(task_id: str) -> None:
    """音声処理のメインタスク"""
    # タスクを取得（従来のタスクストアから）
    if task_id not in tasks_store:
        logger.error(f"処理対象のタスクが見つかりません: {task_id}")
        return

    task = tasks_store[task_id]

    # セッションIDを見つけてタスクを更新する関数
    def update_session_task():
        updated = False
        for session_id, session_tasks in session_task_store._sessions.items():
            if task_id in session_tasks:
                session_task_store.update_task(session_id, task)
                updated = True
        
        # セッションストアにない場合でも従来のタスクストアは更新
        tasks_store[task_id] = task
        
        # 永続化ストアも更新
        try:
            # どのセッションにタスクが属するかを特定
            for session_id in persistent_store._sessions_cache:
                if task_id in persistent_store._sessions_cache[session_id]:
                    persistent_store.update_task(session_id, task)
                    break
        except Exception as e:
            logger.warning(f"プロセス中の永続化更新に失敗: {e}")
        
        return updated

    try:
        # ステータスを処理中に変更
        task.status = TaskStatus.PROCESSING
        update_session_task()
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
        update_session_task()
        await broadcast_progress_update(task_id, task)

        # 文字起こし
        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.PROCESSING
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        transcription_service = TranscriptionService()
        transcription = await transcription_service.transcribe_audio(audio_path)
        task.transcription = transcription

        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.COMPLETED, 100
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        # 議事録生成
        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.PROCESSING
        )
        update_session_task()
        await broadcast_progress_update(task_id, task)

        minutes_service = MinutesGeneratorService()
        minutes = await minutes_service.generate_minutes(transcription)
        task.minutes = minutes

        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.COMPLETED, 100
        )
        update_session_task()

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

        update_session_task()
        await broadcast_task_failed(task_id, task, error_message)

    finally:
        # ファイルクリーンアップ
        FileHandler.cleanup_files(task_id)


async def broadcast_progress_update(task_id: str, task: MinutesTask):
    """進捗更新をWebSocket接続に配信"""
    if task_id in websocket_connections:
        message = {
            "type": "progress_update",
            "task_id": task_id,
            "status": task.status.value,
            "current_step": task.current_step.value if task.current_step else None,
            "overall_progress": task.overall_progress,
            "steps": [
                {
                    "name": step.name.value,
                    "status": step.status.value,
                    "progress": step.progress,
                    "error_message": step.error_message,
                }
                for step in task.steps
            ],
        }

        # 切断された接続を追跡
        disconnected_connections = []

        for websocket in websocket_connections[task_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"WebSocket送信エラー: {e}")
                disconnected_connections.append(websocket)

        # 切断された接続を削除
        for websocket in disconnected_connections:
            websocket_connections[task_id].remove(websocket)

        # 接続がなくなった場合はキーを削除
        if not websocket_connections[task_id]:
            del websocket_connections[task_id]


async def broadcast_task_completed(task_id: str, task: MinutesTask):
    """タスク完了をWebSocket接続に配信"""
    if task_id in websocket_connections:
        message = {
            "type": "task_completed",
            "task_id": task_id,
            "status": task.status.value,
            "overall_progress": 100,
            "transcription": task.transcription,
            "minutes": task.minutes,
        }

        # 切断された接続を追跡
        disconnected_connections = []

        for websocket in websocket_connections[task_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"WebSocket送信エラー: {e}")
                disconnected_connections.append(websocket)

        # 切断された接続を削除
        for websocket in disconnected_connections:
            websocket_connections[task_id].remove(websocket)

        # 接続がなくなった場合はキーを削除
        if not websocket_connections[task_id]:
            del websocket_connections[task_id]


async def broadcast_task_failed(task_id: str, task: MinutesTask, error_message: str):
    """タスク失敗をWebSocket接続に配信"""
    if task_id in websocket_connections:
        message = {
            "type": "task_failed",
            "task_id": task_id,
            "status": task.status.value,
            "error_message": error_message,
            "steps": [
                {
                    "name": step.name.value,
                    "status": step.status.value,
                    "progress": step.progress,
                    "error_message": step.error_message,
                }
                for step in task.steps
            ],
        }

        # 切断された接続を追跡
        disconnected_connections = []

        for websocket in websocket_connections[task_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"WebSocket送信エラー: {e}")
                disconnected_connections.append(websocket)

        # 切断された接続を削除
        for websocket in disconnected_connections:
            websocket_connections[task_id].remove(websocket)

        # 接続がなくなった場合はキーを削除
        if not websocket_connections[task_id]:
            del websocket_connections[task_id]


@router.post("/{task_id}/edit", response_model=EditMinutesResponse)
async def edit_minutes(
    request: Request,
    task_id: str,
    edit_request: EditMinutesRequest
) -> EditMinutesResponse:
    """
    議事録を編集
    
    Args:
        task_id: タスクID
        edit_request: 編集リクエスト
    
    Returns:
        EditMinutesResponse: 編集結果
    """
    try:
        from app.store.chat_store import chat_store
        
        session_id = SessionManager.get_session_id(request)
        logger.info(f"議事録編集要求: {task_id} (セッション: {session_id[:8]}...)")
        
        # セッションを取得
        session = chat_store.get_session(edit_request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # メッセージを取得
        message = chat_store.get_message(edit_request.session_id, edit_request.message_id)
        if not message:
            raise HTTPException(status_code=404, detail="メッセージが見つかりません")
        
        # 現在の議事録を取得
        task = session_task_store.get_task(session_id, task_id)
        if not task:
            # 従来のタスクストアからも検索
            task = tasks_store.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="タスクが見つかりません")
        
        original_minutes = task.minutes or ""
        
        # 高度な編集実行エンジンを使用
        from app.services.edit_executor import edit_executor
        
        updated_minutes, changes_summary = edit_executor.execute_edit_actions(
            original_minutes, edit_request.edit_actions
        )
        
        # 編集履歴を作成
        edit_history = EditHistory(
            task_id=task_id,
            session_id=edit_request.session_id,
            message_id=edit_request.message_id,
            edit_actions=edit_request.edit_actions,
            changes_summary=changes_summary,
            original_minutes=original_minutes,
            updated_minutes=updated_minutes
        )
        
        # 編集履歴を保存
        chat_store.add_edit_history(edit_history)
        
        # タスクの議事録を更新
        task.minutes = updated_minutes
        
        # セッションストアを更新
        session_task_store.update_task(session_id, task)
        # 従来のタスクストアも更新（下位互換性）
        if task_id in tasks_store:
            tasks_store[task_id] = task
        
        # セッションの議事録も更新
        session.minutes = updated_minutes
        chat_store.update_session(session)
        
        logger.info(f"議事録を編集しました: {edit_history.edit_id[:8]}... ({len(changes_summary)}件の変更)")
        
        return EditMinutesResponse(
            edit_id=edit_history.edit_id,
            success=True,
            updated_minutes=updated_minutes,
            changes_summary=changes_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"議事録編集エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="議事録の編集に失敗しました")


