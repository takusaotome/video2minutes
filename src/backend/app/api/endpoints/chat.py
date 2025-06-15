"""チャット機能のAPIエンドポイント"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import JSONResponse

from app.models.chat import (
    CreateChatSessionRequest,
    CreateChatSessionResponse,
    SendMessageRequest,
    SendMessageResponse,
    EditMinutesRequest,
    EditMinutesResponse,
    ChatHistoryResponse,
    ChatSession,
    ChatMessage,
    EditHistory,
    MessageType,
    MessageIntent
)
from app.store.chat_store import chat_store
from app.store.session_store import session_task_store
from app.utils.logger import get_logger
from app.utils.session_manager import SessionManager

logger = get_logger(__name__)

router = APIRouter()


@router.post("/sessions", response_model=CreateChatSessionResponse)
async def create_chat_session(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_request: CreateChatSessionRequest = None
) -> CreateChatSessionResponse:
    """
    新しいチャットセッションを作成
    
    Args:
        task_id: 関連するタスクID
        session_request: セッション作成リクエスト
    
    Returns:
        CreateChatSessionResponse: セッション作成結果
    """
    try:
        # タスクが存在するかチェック
        session_id = SessionManager.get_session_id(request)
        task = session_task_store.get_task(session_id, task_id)
        if not task:
            # 従来のタスクストアからも取得を試行
            from app.store import tasks_store
            task = tasks_store.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="タスクが見つかりません")
        
        if task.status.value != "completed":
            raise HTTPException(status_code=400, detail="タスクが完了していないため、チャットセッションを作成できません")
        
        # 文字起こしと議事録のデータを取得
        transcription = session_request.transcription if session_request else task.transcription or ""
        minutes = session_request.minutes if session_request else task.minutes or ""
        
        if not transcription:
            raise HTTPException(status_code=400, detail="文字起こしデータが必要です")
        
        if not minutes:
            raise HTTPException(status_code=400, detail="議事録データが必要です")
        
        # 新しいチャットセッションを作成
        session = ChatSession(
            task_id=task_id,
            transcription=transcription,
            minutes=minutes,
            context_tokens=_estimate_tokens(transcription + minutes)
        )
        
        # セッションを保存
        chat_store.create_session(session)
        
        logger.info(f"チャットセッションを作成しました: {session.session_id[:8]}... for task {task_id[:8]}...")
        
        return CreateChatSessionResponse(
            session_id=session.session_id,
            context_tokens=session.context_tokens
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"チャットセッション作成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="セッション作成に失敗しました")


@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID")
) -> ChatHistoryResponse:
    """
    チャット履歴を取得
    
    Args:
        task_id: タスクID
        session_id: セッションID
    
    Returns:
        ChatHistoryResponse: チャット履歴
    """
    try:
        # セッションを取得
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # メッセージを取得
        messages = chat_store.get_messages(session_id)
        
        # 総使用トークン数を計算
        total_tokens = sum(message.tokens_used for message in messages)
        
        logger.debug(f"チャット履歴を取得: {session_id[:8]}... ({len(messages)}件のメッセージ)")
        
        return ChatHistoryResponse(
            messages=messages,
            total_tokens=total_tokens,
            session_info=session
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"チャット履歴取得エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="チャット履歴の取得に失敗しました")


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID")
) -> JSONResponse:
    """
    チャットセッションを削除
    
    Args:
        task_id: タスクID
        session_id: セッションID
    
    Returns:
        JSONResponse: 削除結果
    """
    try:
        # セッションを取得して権限チェック
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # セッションを削除
        success = chat_store.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=500, detail="セッションの削除に失敗しました")
        
        logger.info(f"チャットセッションを削除しました: {session_id[:8]}...")
        
        return JSONResponse(
            status_code=200,
            content={"message": "セッションが正常に削除されました", "session_id": session_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"セッション削除エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="セッションの削除に失敗しました")


@router.get("/sessions")
async def list_chat_sessions(
    request: Request,
    task_id: str = Path(..., description="タスクID")
) -> JSONResponse:
    """
    タスクに関連するチャットセッション一覧を取得
    
    Args:
        task_id: タスクID
    
    Returns:
        JSONResponse: セッション一覧
    """
    try:
        # タスクが存在するかチェック
        session_id = SessionManager.get_session_id(request)
        task = session_task_store.get_task(session_id, task_id)
        if not task:
            # 従来のタスクストアからも取得を試行
            from app.store import tasks_store
            task = tasks_store.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="タスクが見つかりません")
        
        # タスクに関連するセッションを取得
        sessions = chat_store.get_sessions_by_task(task_id)
        
        # セッション情報を整理
        session_list = []
        for session in sessions:
            messages = chat_store.get_messages(session.session_id)
            session_list.append({
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "total_messages": session.total_messages,
                "context_tokens": session.context_tokens,
                "is_active": session.is_active,
                "message_count": len(messages)
            })
        
        logger.debug(f"タスクのセッション一覧を取得: {task_id[:8]}... ({len(session_list)}件)")
        
        return JSONResponse(
            status_code=200,
            content={
                "task_id": task_id,
                "sessions": session_list,
                "total_sessions": len(session_list)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"セッション一覧取得エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="セッション一覧の取得に失敗しました")


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_chat_message(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID"),
    message_request: SendMessageRequest = None
) -> SendMessageResponse:
    """
    チャットメッセージを送信してAI回答を取得
    
    Args:
        task_id: タスクID
        session_id: セッションID
        message_request: メッセージ送信リクエスト
    
    Returns:
        SendMessageResponse: AI回答
    """
    try:
        # セッションを取得
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # OpenAIサービスでメッセージを処理
        from app.services.openai_service import openai_service
        from app.services.citation_service import citation_service
        
        # 既存のメッセージ履歴を取得
        existing_messages = chat_store.get_messages(session_id)
        
        ai_response = await openai_service.process_chat_message(
            session=session,
            message=message_request.message,
            intent=message_request.intent,
            chat_history=existing_messages
        )
        
        # 引用を抽出・強化
        enhanced_citations = citation_service.extract_citations_from_response(
            ai_response["response"],
            session.transcription,
            session
        )
        
        # AI回答の引用とマージ
        all_citations = ai_response["citations"] + enhanced_citations
        
        # メッセージを作成
        chat_message = ChatMessage(
            session_id=session_id,
            message=message_request.message,
            response=ai_response["response"],
            message_type=message_request.message_type,
            intent=message_request.intent,
            citations=all_citations,
            edit_actions=ai_response["edit_actions"],
            tokens_used=ai_response["tokens_used"],
            processing_time=ai_response["processing_time"]
        )
        
        # メッセージを保存
        chat_store.add_message(chat_message)
        
        logger.info(f"チャットメッセージを処理: {session_id[:8]}... -> {chat_message.message_id[:8]}...")
        
        return SendMessageResponse(
            message_id=chat_message.message_id,
            response=chat_message.response,
            citations=all_citations,
            tokens_used=chat_message.tokens_used,
            edit_actions=chat_message.edit_actions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"チャットメッセージ処理エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="メッセージの処理に失敗しました")






@router.get("/sessions/{session_id}/citations")
async def get_session_citations(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID"),
    message_id: str = None
) -> JSONResponse:
    """
    セッションまたは特定メッセージの引用一覧を取得
    
    Args:
        task_id: タスクID
        session_id: セッションID
        message_id: メッセージID（指定時は該当メッセージの引用のみ）
    
    Returns:
        JSONResponse: 引用一覧
    """
    try:
        # セッションを取得
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        if message_id:
            # 特定メッセージの引用を取得
            message = chat_store.get_message(session_id, message_id)
            if not message:
                raise HTTPException(status_code=404, detail="メッセージが見つかりません")
            
            citations_data = []
            for citation in message.citations:
                citations_data.append({
                    "citation_id": citation.citation_id,
                    "text": citation.text,
                    "start_time": citation.start_time,
                    "confidence": citation.confidence,
                    "context": citation.context,
                    "highlight_start": citation.highlight_start,
                    "highlight_end": citation.highlight_end,
                    "message_id": message_id
                })
            
            return JSONResponse(
                status_code=200,
                content={
                    "session_id": session_id,
                    "message_id": message_id,
                    "citations": citations_data,
                    "total_citations": len(citations_data)
                }
            )
        else:
            # セッション全体の引用を取得
            messages = chat_store.get_messages(session_id)
            all_citations = []
            
            for message in messages:
                for citation in message.citations:
                    all_citations.append({
                        "citation_id": citation.citation_id,
                        "text": citation.text,
                        "start_time": citation.start_time,
                        "confidence": citation.confidence,
                        "context": citation.context,
                        "highlight_start": citation.highlight_start,
                        "highlight_end": citation.highlight_end,
                        "message_id": message.message_id
                    })
            
            # 信頼度でソート
            all_citations.sort(key=lambda x: x["confidence"], reverse=True)
            
            return JSONResponse(
                status_code=200,
                content={
                    "session_id": session_id,
                    "citations": all_citations,
                    "total_citations": len(all_citations),
                    "total_messages": len(messages)
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"引用取得エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="引用の取得に失敗しました")


@router.post("/sessions/{session_id}/highlights")
async def create_highlight(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID"),
    highlight_data: Dict = None
) -> JSONResponse:
    """
    新しいハイライトを作成
    
    Args:
        task_id: タスクID
        session_id: セッションID
        highlight_data: ハイライト情報
    
    Returns:
        JSONResponse: 作成結果
    """
    try:
        from app.services.citation_service import citation_service
        
        # セッションを取得
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # ハイライト情報を検証
        required_fields = ["start_position", "end_position", "highlighted_text"]
        if not all(field in highlight_data for field in required_fields):
            raise HTTPException(status_code=400, detail="必須フィールドが不足しています")
        
        # 新しい引用を作成
        from app.models.chat import Citation
        
        citation = Citation(
            text=highlight_data["highlighted_text"],
            start_time=highlight_data.get("timestamp", "00:00:00"),
            confidence=highlight_data.get("confidence", 0.9),
            context=highlight_data.get("context", ""),
            highlight_start=highlight_data["start_position"],
            highlight_end=highlight_data["end_position"]
        )
        
        # ハイライト情報を作成
        highlight_info = citation_service.create_highlight_info(citation, session.transcription)
        
        logger.info(f"ハイライト作成: {citation.citation_id[:8]}... in session {session_id[:8]}...")
        
        return JSONResponse(
            status_code=201,
            content={
                "highlight_id": citation.citation_id,
                "highlight_info": highlight_info,
                "success": True
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ハイライト作成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ハイライトの作成に失敗しました")


@router.post("/sessions/{session_id}/analyze-edit")
async def analyze_edit_intent(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID"),
    edit_instruction: str = None
) -> JSONResponse:
    """
    編集インテント解析テスト用エンドポイント
    
    Args:
        task_id: タスクID
        session_id: セッションID  
        edit_instruction: 編集指示
    
    Returns:
        JSONResponse: 解析結果
    """
    try:
        from app.services.edit_intent_analyzer import edit_intent_analyzer
        
        # セッションを取得
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # 編集インテント解析を実行
        edit_actions, explanation = edit_intent_analyzer.analyze_edit_intent(
            edit_instruction, session.minutes
        )
        
        # 結果を整理
        actions_data = []
        for action in edit_actions:
            actions_data.append({
                "action_type": action.action_type.value,
                "target": action.target,
                "replacement": action.replacement,
                "scope": action.scope.value if action.scope else None,
                "content": action.content,
                "item_id": action.item_id,
                "updates": action.updates,
                "description": action.description
            })
        
        logger.info(f"編集インテント解析テスト完了: {len(edit_actions)}件のアクション")
        
        return JSONResponse(
            status_code=200,
            content={
                "edit_instruction": edit_instruction,
                "explanation": explanation,
                "edit_actions": actions_data,
                "actions_count": len(edit_actions)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"編集インテント解析テストエラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="編集インテント解析に失敗しました")


def _estimate_tokens(text: str) -> int:
    """
    テキストのトークン数を概算
    
    Args:
        text: 対象テキスト
    
    Returns:
        int: 推定トークン数
    """
    # 日本語の場合、約1.5文字で1トークンの概算
    # 英語の場合、約4文字で1トークンの概算
    # ここでは日本語メインと仮定
    japanese_chars = sum(1 for char in text if ord(char) > 127)
    english_chars = len(text) - japanese_chars
    
    estimated_tokens = int(japanese_chars / 1.5) + int(english_chars / 4)
    
    # 最低100トークンは確保
    return max(estimated_tokens, 100)


@router.get("/sessions/{session_id}/edit-history")
async def get_edit_history(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID"),
    limit: int = 20,
    include_details: bool = False
) -> JSONResponse:
    """
    セッションの編集履歴を取得
    
    Args:
        task_id: タスクID
        session_id: セッションID
        limit: 取得件数制限
        include_details: 詳細情報を含めるか
    
    Returns:
        JSONResponse: 編集履歴
    """
    try:
        # セッションを取得
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # 編集履歴を取得
        edit_histories = chat_store.get_edit_history(session_id, limit=limit)
        
        if not edit_histories:
            return JSONResponse(
                status_code=200,
                content={
                    "session_id": session_id,
                    "edit_history": [],
                    "total_edits": 0,
                    "comparison_data": {"versions": [], "timeline": []}
                }
            )
        
        # 編集履歴サービスでデータを整理
        from app.services.edit_history_service import edit_history_service
        
        # 編集エントリを作成
        edit_entries = []
        for history in edit_histories:
            entry = edit_history_service.create_edit_entry(
                task_id=history.task_id,
                session_id=history.session_id,
                message_id=history.message_id,
                edit_actions=history.edit_actions,
                original_minutes=history.original_minutes,
                updated_minutes=history.updated_minutes
            )
            entry["edit_id"] = history.edit_id
            entry["timestamp"] = history.timestamp.isoformat()
            entry["reverted"] = history.reverted
            edit_entries.append(entry)
        
        # 比較データを作成
        comparison_data = edit_history_service.create_comparison_data(edit_entries)
        
        # レスポンスデータを整理
        response_data = {
            "session_id": session_id,
            "edit_history": edit_entries if include_details else [
                {
                    "edit_id": entry["edit_id"],
                    "timestamp": entry["timestamp"],
                    "changes_summary": entry["changes_summary"],
                    "edit_type": entry.get("edit_type", "normal"),
                    "reverted": entry.get("reverted", False)
                } for entry in edit_entries
            ],
            "total_edits": len(edit_entries),
            "comparison_data": comparison_data
        }
        
        logger.info(f"編集履歴取得: {session_id[:8]}... ({len(edit_entries)}件)")
        
        return JSONResponse(status_code=200, content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"編集履歴取得エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="編集履歴の取得に失敗しました")


@router.post("/sessions/{session_id}/edit-history/{edit_id}/undo")
async def undo_edit(
    request: Request,
    task_id: str = Path(..., description="タスクID"),
    session_id: str = Path(..., description="セッションID"),
    edit_id: str = Path(..., description="編集ID")
) -> JSONResponse:
    """
    指定した編集を取り消し
    
    Args:
        task_id: タスクID
        session_id: セッションID
        edit_id: 取り消し対象の編集ID
    
    Returns:
        JSONResponse: 取り消し結果
    """
    try:
        from app.services.edit_history_service import edit_history_service
        from app.utils.session_manager import SessionManager
        
        # セッションを取得
        session = chat_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
        if session.task_id != task_id:
            raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
        
        # 対象の編集履歴を取得
        edit_history = chat_store.get_edit_history_by_id(edit_id)
        if not edit_history:
            raise HTTPException(status_code=404, detail="指定された編集が見つかりません")
        
        if edit_history.session_id != session_id:
            raise HTTPException(status_code=403, detail="編集へのアクセス権限がありません")
        
        # 現在のタスクを取得
        session_id_from_request = SessionManager.get_session_id(request)
        task = session_task_store.get_task(session_id_from_request, task_id)
        if not task:
            # 従来のタスクストアからも検索
            from app.store import tasks_store
            task = tasks_store.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="タスクが見つかりません")
        
        current_minutes = task.minutes or ""
        
        # 編集エントリを作成
        edit_entry = edit_history_service.create_edit_entry(
            task_id=edit_history.task_id,
            session_id=edit_history.session_id,
            message_id=edit_history.message_id,
            edit_actions=edit_history.edit_actions,
            original_minutes=edit_history.original_minutes,
            updated_minutes=edit_history.updated_minutes
        )
        edit_entry["edit_id"] = edit_history.edit_id
        edit_entry["reverted"] = edit_history.reverted
        
        # 取り消し操作の妥当性を検証
        is_valid, error_message = edit_history_service.validate_undo_operation(
            edit_entry, current_minutes
        )
        
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": error_message,
                    "edit_id": edit_id
                }
            )
        
        # 取り消し用エントリを作成
        undo_entry = edit_history_service.create_undo_entry(edit_entry)
        
        # 議事録を元に戻す
        restored_minutes = edit_history.original_minutes
        
        # タスクの議事録を更新
        task.minutes = restored_minutes
        session_task_store.update_task(session_id_from_request, task)
        
        # 従来のタスクストアも更新（下位互換性）
        from app.store import tasks_store
        if task_id in tasks_store:
            tasks_store[task_id] = task
        
        # セッションの議事録も更新
        session.minutes = restored_minutes
        chat_store.update_session(session)
        
        # 元の編集を取り消し済みとしてマーク
        edit_history.reverted = True
        chat_store.update_edit_history(edit_history)
        
        # 取り消し履歴を追加
        undo_history = EditHistory(
            task_id=task_id,
            session_id=session_id,
            message_id=undo_entry["message_id"],
            edit_actions=[],
            changes_summary=undo_entry["changes_summary"],
            original_minutes=edit_history.updated_minutes,
            updated_minutes=edit_history.original_minutes
        )
        chat_store.add_edit_history(undo_history)
        
        logger.info(f"編集を取り消し: {edit_id[:8]}... -> {undo_history.edit_id[:8]}...")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "undo_edit_id": undo_history.edit_id,
                "restored_minutes": restored_minutes,
                "changes_summary": undo_entry["changes_summary"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"編集取り消しエラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="編集の取り消しに失敗しました")