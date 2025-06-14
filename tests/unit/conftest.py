import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'backend'))

# テスト用環境変数を設定
os.environ.setdefault('OPENAI_API_KEY', 'test-openai-key')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-anthropic-key')

from app.main import create_app
from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """イベントループをセッションスコープで作成"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """FastAPIテストクライアント"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """設定のモック"""
    settings.openai_api_key = "test-key"
    settings.anthropic_api_key = "test-key"
    settings.upload_dir = "test_uploads"
    settings.temp_dir = "test_temp"
    return settings


@pytest.fixture
def temp_file():
    """一時ファイル作成"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
        f.write(b"fake video content")
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_openai_client():
    """OpenAIクライアントのモック"""
    mock_client = Mock()
    mock_client.audio = Mock()
    mock_client.audio.transcriptions = Mock()
    mock_client.audio.transcriptions.create = AsyncMock()
    return mock_client


@pytest.fixture
def sample_task_data():
    """サンプルタスクデータ"""
    return {
        "task_id": "test-task-123",
        "video_filename": "test_video.mp4",
        "video_size": 1024000,
        "transcription": "これはテスト用の音声文字起こし結果です。",
        "minutes": "## 会議議事録\n\n### 要約\nテスト会議の内容です。"
    }


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """テスト後のファイルクリーンアップ"""
    yield
    # テスト用ディレクトリが存在する場合は削除
    for dir_name in ["test_uploads", "test_temp"]:
        if os.path.exists(dir_name):
            import shutil
            shutil.rmtree(dir_name)


@pytest.fixture
def mock_video_processor():
    """VideoProcessorのモック"""
    mock = Mock()
    mock.extract_audio = AsyncMock(return_value="/path/to/audio.wav")
    mock.get_video_info = Mock(return_value={
        "duration": 120.0,
        "size": 1024000,
        "video": {"codec": "h264", "width": 1920, "height": 1080, "fps": 30.0},
        "audio": {"codec": "aac", "sample_rate": 44100, "channels": 2}
    })
    return mock


@pytest.fixture
def mock_transcription_service():
    """TranscriptionServiceのモック"""
    mock = Mock()
    mock.transcribe_audio = AsyncMock(return_value="テスト用文字起こし結果")
    mock.transcribe_with_timestamps = AsyncMock(return_value={
        "text": "テスト用文字起こし結果",
        "segments": []
    })
    return mock