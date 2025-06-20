from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""

    # API Keys
    openai_api_key: str
    anthropic_api_key: Optional[str] = None

    # Basic認証設定（非推奨）
    basic_auth_username: Optional[str] = None
    basic_auth_password: Optional[str] = None
    
    # APIキー認証設定
    api_keys: Optional[str] = Field(
        default=None,
        description="有効なAPIキーのカンマ区切りリスト"
    )
    master_api_key: Optional[str] = Field(
        default=None,
        description="マスターAPIキー（開発用）"
    )
    auth_enabled: bool = Field(
        default=True,
        description="認証機能の有効/無効"
    )

    # セッション設定
    session_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="セッション暗号化キー（本番環境では必ず変更すること）"
    )
    session_max_age: int = Field(
        default=86400,  # 24時間
        description="セッションの有効期限（秒）"
    )

    # Server設定
    host: str = Field(
        default="127.0.0.1", description="本番環境では特定のIPアドレスを指定推奨"
    )
    port: int = 8000
    debug: bool = False

    # CORS設定
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:5173",
    ]

    # ファイル設定
    max_file_size: int = 5 * 1024 * 1024 * 1024  # 5GB
    # 対応動画形式
    allowed_video_extensions: list[str] = [
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
    ]

    # 対応音声形式
    allowed_audio_extensions: list[str] = [
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".flac",
        ".ogg",
        ".wma",
    ]
    upload_dir: str = "uploads"
    temp_dir: str = "temp"

    # 処理設定
    max_concurrent_tasks: int = 3  # 同時実行タスク数（Whisper API制限考慮）
    task_timeout: int = 7200  # 2時間（大きなファイル対応）

    # 音声処理設定
    audio_max_file_size_mb: int = 20  # Whisper API制限の安全マージン
    audio_bitrate_max: int = 96  # 最大ビットレート (kbps)
    audio_chunk_duration_max: int = 900  # 最大チャンク時間 (秒) - 15分
    upload_chunk_size: int = 16384  # アップロード時のチャンクサイズ (16KB)

    # Whisper設定
    whisper_model: str = "whisper-1"
    whisper_language: str = "ja"

    # GPT設定
    gpt_model: str = "o3"
    gpt_max_tokens: int = 4000

    # チャット機能設定
    chat_enabled: bool = True
    chat_max_sessions_per_task: int = 5
    chat_session_timeout_hours: int = 6
    chat_max_messages_per_session: int = 100
    chat_max_tokens_per_request: int = 8000
    chat_rate_limit_per_minute: int = 10
    
    # OpenAI Chat設定  
    openai_chat_model: str = "gpt-4.1"  # gpt-4.1, o3-mini, gpt-4o (課金後利用可能)
    openai_chat_max_tokens: int = 4000
    openai_chat_temperature: float = 0.3
    openai_timeout_seconds: int = 60
    
    # ロギング設定
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_format: str = "standard"  # standard, detailed, json
    
    # タイムゾーン設定
    timezone: str = "Asia/Tokyo"  # 日本時間をデフォルトに

    # ストレージ設定
    storage_dir: str = "storage"
    enable_persistence: bool = True
    cleanup_old_tasks_hours: int = 72  # 72時間後に古いタスクをクリーンアップ

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# グローバル設定インスタンス
settings = Settings()
