from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# チャット機能関連のモデルをインポート
from app.models.chat import (
    ChatSession,
    ChatMessage,
    EditAction,
    EditHistory,
    Citation,
    MessageType,
    MessageIntent,
    EditActionType,
    EditScope,
    CreateChatSessionRequest,
    CreateChatSessionResponse,
    SendMessageRequest,
    SendMessageResponse,
    EditMinutesRequest,
    EditMinutesResponse,
    ChatHistoryResponse,
    TokenUsage,
    ChatStats,
    ErrorInfo,
)


class TaskStatus(str, Enum):
    """タスクステータス"""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStepStatus(str, Enum):
    """処理ステップステータス"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStepName(str, Enum):
    """処理ステップ名"""

    UPLOAD = "upload"
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    MINUTES_GENERATION = "minutes_generation"


class ProcessingStep(BaseModel):
    """処理ステップ"""

    name: ProcessingStepName
    status: ProcessingStepStatus = ProcessingStepStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class MinutesTask(BaseModel):
    """議事録生成タスク"""

    task_id: str
    status: TaskStatus = TaskStatus.QUEUED
    video_filename: str
    video_size: int
    upload_timestamp: datetime
    current_step: Optional[ProcessingStepName] = None
    overall_progress: int = Field(default=0, ge=0, le=100)
    steps: List[ProcessingStep] = Field(
        default_factory=lambda: [
            ProcessingStep(name=ProcessingStepName.UPLOAD),
            ProcessingStep(name=ProcessingStepName.AUDIO_EXTRACTION),
            ProcessingStep(name=ProcessingStepName.TRANSCRIPTION),
            ProcessingStep(name=ProcessingStepName.MINUTES_GENERATION),
        ]
    )
    transcription: Optional[str] = None
    minutes: Optional[str] = None
    error_message: Optional[str] = None

    def get_current_step(self) -> Optional[ProcessingStep]:
        """現在実行中のステップを取得"""
        for step in self.steps:
            if step.status == ProcessingStepStatus.PROCESSING:
                return step
        return None

    def update_step_status(
        self,
        step_name: ProcessingStepName,
        status: ProcessingStepStatus,
        progress: int = 0,
        error_message: Optional[str] = None,
    ):
        """ステップのステータスを更新"""
        for step in self.steps:
            if step.name == step_name:
                step.status = status
                step.progress = progress
                if status == ProcessingStepStatus.PROCESSING:
                    step.started_at = datetime.now()
                    self.current_step = step_name
                elif status in [
                    ProcessingStepStatus.COMPLETED,
                    ProcessingStepStatus.FAILED,
                ]:
                    step.completed_at = datetime.now()
                    if status == ProcessingStepStatus.FAILED:
                        step.error_message = error_message
                        self.status = TaskStatus.FAILED
                        self.error_message = error_message
                break

        # 全体の進捗を計算
        self._update_overall_progress()

    def _update_overall_progress(self):
        """全体の進捗を計算"""
        total_progress = sum(step.progress for step in self.steps)
        self.overall_progress = total_progress // len(self.steps)

        # 全ステップ完了の場合
        if all(step.status == ProcessingStepStatus.COMPLETED for step in self.steps):
            self.status = TaskStatus.COMPLETED
            self.current_step = None


class UploadResponse(BaseModel):
    """アップロード応答"""

    task_id: str
    status: TaskStatus
    message: str = "ファイルのアップロードが完了しました。処理を開始します。"


class TaskListResponse(BaseModel):
    """タスク一覧応答"""

    tasks: List[MinutesTask]


class TaskStatusResponse(BaseModel):
    """タスクステータス応答"""

    task_id: str
    status: TaskStatus
    current_step: Optional[ProcessingStepName]
    overall_progress: int
    steps: List[ProcessingStep]
    video_filename: str
    upload_timestamp: datetime
    error_message: Optional[str] = None


class TaskResultResponse(BaseModel):
    """タスク結果応答"""

    task_id: str
    video_filename: str
    transcription: str
    minutes: str
    upload_timestamp: datetime


class WebSocketMessage(BaseModel):
    """WebSocketメッセージ"""

    type: str  # "progress_update", "task_completed", "task_failed"
    task_id: str
    data: Dict[str, Any]


class ErrorResponse(BaseModel):
    """エラー応答"""

    error: str
    message: str
    task_id: Optional[str] = None