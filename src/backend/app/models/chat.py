"""チャット機能のデータモデル"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """メッセージタイプ"""
    USER = "user"
    ASSISTANT = "assistant"


class MessageIntent(str, Enum):
    """メッセージの意図"""
    QUESTION = "question"
    EDIT_REQUEST = "edit_request"


class EditActionType(str, Enum):
    """編集アクションのタイプ"""
    REPLACE_TEXT = "replace_text"
    ADD_ACTION_ITEM = "add_action_item"
    UPDATE_ACTION_ITEM = "update_action_item"
    ADD_CONTENT = "add_content"
    RESTRUCTURE = "restructure"


class EditScope(str, Enum):
    """編集の適用範囲"""
    ALL = "all"
    SECTION = "section"
    SPECIFIC = "specific"


class Citation(BaseModel):
    """引用情報"""
    citation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="引用ID")
    text: str = Field(..., description="引用テキスト")
    start_time: Optional[str] = Field(None, description="タイムスタンプ（形式: HH:MM:SS）")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="信頼度スコア")
    context: str = Field("", description="前後の文脈")
    highlight_start: Optional[int] = Field(None, description="ハイライト開始位置（文字インデックス）")
    highlight_end: Optional[int] = Field(None, description="ハイライト終了位置（文字インデックス）")


class EditAction(BaseModel):
    """編集アクション"""
    action_type: EditActionType = Field(..., description="編集アクションのタイプ")
    target: Optional[str] = Field(None, description="対象テキスト（置換の場合）")
    replacement: Optional[str] = Field(None, description="置換テキスト")
    scope: Optional[EditScope] = Field(None, description="適用範囲")
    content: Optional[Dict] = Field(None, description="追加・更新内容")
    item_id: Optional[str] = Field(None, description="更新対象のID")
    updates: Optional[Dict] = Field(None, description="更新内容")
    description: str = Field("", description="編集内容の説明")


class ChatSession(BaseModel):
    """チャットセッション"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="セッションID")
    task_id: str = Field(..., description="関連するタスクID")
    transcription: str = Field("", description="文字起こし全文")
    minutes: str = Field("", description="議事録内容")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    last_activity: datetime = Field(default_factory=datetime.now, description="最終アクティビティ日時")
    context_tokens: int = Field(0, description="コンテキストトークン数")
    total_messages: int = Field(0, description="総メッセージ数")
    is_active: bool = Field(True, description="アクティブ状態")


class ChatMessage(BaseModel):
    """チャットメッセージ"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="メッセージID")
    session_id: str = Field(..., description="セッションID")
    message: str = Field(..., description="ユーザーメッセージ")
    response: str = Field("", description="AIの回答")
    message_type: MessageType = Field(MessageType.USER, description="メッセージタイプ")
    intent: MessageIntent = Field(MessageIntent.QUESTION, description="メッセージの意図")
    timestamp: datetime = Field(default_factory=datetime.now, description="タイムスタンプ")
    citations: List[Citation] = Field(default_factory=list, description="引用リスト")
    edit_actions: List[EditAction] = Field(default_factory=list, description="編集アクション（編集リクエストの場合）")
    tokens_used: int = Field(0, description="使用トークン数")
    processing_time: float = Field(0.0, description="処理時間（秒）")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")


class EditHistory(BaseModel):
    """編集履歴"""
    edit_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="編集ID")
    task_id: str = Field(..., description="タスクID")
    session_id: str = Field(..., description="セッションID")
    message_id: str = Field(..., description="メッセージID")
    edit_actions: List[EditAction] = Field(..., description="編集アクション")
    changes_summary: List[str] = Field(..., description="変更内容の要約")
    original_minutes: str = Field(..., description="編集前の議事録")
    updated_minutes: str = Field(..., description="編集後の議事録")
    timestamp: datetime = Field(default_factory=datetime.now, description="編集日時")
    reverted: bool = Field(False, description="取り消しフラグ")


# API Request/Response Models

class CreateChatSessionRequest(BaseModel):
    """チャットセッション作成リクエスト"""
    transcription: str = Field(..., description="文字起こし全文")
    minutes: str = Field(..., description="議事録内容")


class CreateChatSessionResponse(BaseModel):
    """チャットセッション作成レスポンス"""
    session_id: str = Field(..., description="セッションID")
    context_tokens: int = Field(..., description="コンテキストトークン数")


class SendMessageRequest(BaseModel):
    """メッセージ送信リクエスト"""
    message: str = Field(..., min_length=1, max_length=2000, description="ユーザーの質問")
    message_type: MessageType = Field(MessageType.USER, description="メッセージタイプ")
    intent: MessageIntent = Field(MessageIntent.QUESTION, description="メッセージの意図")


class SendMessageResponse(BaseModel):
    """メッセージ送信レスポンス"""
    message_id: str = Field(..., description="メッセージID")
    response: str = Field(..., description="AI回答")
    citations: List[Citation] = Field(default_factory=list, description="引用リスト")
    tokens_used: int = Field(..., description="使用トークン数")
    edit_actions: List[EditAction] = Field(default_factory=list, description="編集アクション（編集リクエストの場合）")


class EditMinutesRequest(BaseModel):
    """議事録編集リクエスト"""
    session_id: str = Field(..., description="セッションID")
    message_id: str = Field(..., description="メッセージID")
    edit_actions: List[EditAction] = Field(..., description="編集アクション")


class EditMinutesResponse(BaseModel):
    """議事録編集レスポンス"""
    edit_id: str = Field(..., description="編集ID")
    success: bool = Field(..., description="編集成功フラグ")
    updated_minutes: str = Field(..., description="更新後の議事録全文")
    changes_summary: List[str] = Field(..., description="変更内容の要約")


class ChatHistoryResponse(BaseModel):
    """チャット履歴レスポンス"""
    messages: List[ChatMessage] = Field(..., description="メッセージリスト")
    total_tokens: int = Field(0, description="総使用トークン数")
    session_info: ChatSession = Field(..., description="セッション情報")


class TokenUsage(BaseModel):
    """トークン使用量情報"""
    prompt_tokens: int = Field(0, description="プロンプトトークン数")
    completion_tokens: int = Field(0, description="完了トークン数")
    total_tokens: int = Field(0, description="総トークン数")
    estimated_cost: float = Field(0.0, description="推定コスト（USD）")


# 統計・監視用モデル

class ChatStats(BaseModel):
    """チャット統計情報"""
    total_sessions: int = Field(0, description="総セッション数")
    active_sessions: int = Field(0, description="アクティブセッション数")
    total_messages: int = Field(0, description="総メッセージ数")
    total_questions: int = Field(0, description="総質問数")
    total_edit_requests: int = Field(0, description="総編集リクエスト数")
    total_tokens_used: int = Field(0, description="総使用トークン数")
    average_response_time: float = Field(0.0, description="平均応答時間")
    average_session_duration: float = Field(0.0, description="平均セッション時間")


class ErrorInfo(BaseModel):
    """エラー情報"""
    error_code: str = Field(..., description="エラーコード")
    error_message: str = Field(..., description="エラーメッセージ")
    details: Optional[Dict] = Field(None, description="詳細情報")
    timestamp: datetime = Field(default_factory=datetime.now, description="発生日時")
    session_id: Optional[str] = Field(None, description="関連セッションID")