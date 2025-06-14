import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Generator

# テスト用環境変数を設定
os.environ.setdefault('OPENAI_API_KEY', 'test-openai-key')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-anthropic-key')

from fastapi.testclient import TestClient
from app.main import create_app
from app.models import MinutesTask, ProcessingStepName


@pytest.fixture(scope="session")
def event_loop():
    """イベントループを作成"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """モック設定"""
    with pytest.MonkeyPatch.context() as m:
        m.setenv('OPENAI_API_KEY', 'test-openai-key')
        m.setenv('ANTHROPIC_API_KEY', 'test-anthropic-key')
        
        # テスト用設定値
        from app.config import settings
        m.setattr(settings, 'max_file_size', 100 * 1024 * 1024)  # 100MB
        m.setattr(settings, 'upload_dir', 'test_uploads')
        m.setattr(settings, 'temp_dir', 'test_temp')
        m.setattr(settings, 'max_concurrent_tasks', 2)
        m.setattr(settings, 'debug', True)
        
        yield settings


@pytest.fixture
def temp_dir():
    """一時ディレクトリ"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_file():
    """モックファイル"""
    mock = Mock()
    mock.filename = "test_video.mp4"
    mock.size = 1024 * 1024  # 1MB
    mock.content_type = "video/mp4"
    mock.read = AsyncMock(return_value=b"test video content")
    return mock


@pytest.fixture
def mock_large_file():
    """大きなファイルのモック"""
    mock = Mock()
    mock.filename = "large_video.mp4"
    mock.size = 6 * 1024 * 1024 * 1024  # 6GB (制限超過)
    mock.content_type = "video/mp4"
    mock.read = AsyncMock(return_value=b"large video content")
    return mock


@pytest.fixture
def mock_invalid_file():
    """無効なファイルのモック"""
    mock = Mock()
    mock.filename = "invalid.txt"
    mock.size = 1024
    mock.content_type = "text/plain"
    mock.read = AsyncMock(return_value=b"invalid content")
    return mock


@pytest.fixture
def sample_task():
    """サンプルタスク"""
    return MinutesTask(
        task_id="test-task-123",
        video_filename="test_video.mp4",
        video_size=1024 * 1024,
        upload_timestamp=datetime.now()
    )


@pytest.fixture
def client(mock_settings):
    """FastAPIテストクライアント"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_video_processor():
    """モック動画プロセッサー"""
    mock = Mock()
    mock.extract_audio = AsyncMock(return_value="/path/to/audio.mp3")
    return mock


@pytest.fixture
def mock_transcription_service():
    """モック文字起こしサービス"""
    mock = Mock()
    mock.transcribe_audio = AsyncMock(return_value="テスト文字起こし結果")
    return mock


@pytest.fixture
def mock_minutes_generator():
    """モック議事録ジェネレーター"""
    mock = Mock()
    mock.generate_minutes = AsyncMock(return_value="# テスト議事録\n\n## 概要\n\nテスト内容")
    return mock


@pytest.fixture
def mock_openai_client():
    """モックOpenAIクライアント"""
    mock = Mock()
    
    # 音声書き起こしのモック
    mock.audio = Mock()
    mock.audio.transcriptions = Mock()
    mock.audio.transcriptions.create = AsyncMock()
    
    # チャット完了のモック
    mock.chat = Mock()
    mock.chat.completions = Mock()
    mock.chat.completions.create = AsyncMock()
    
    return mock


@pytest.fixture
def sample_transcription():
    """サンプル文字起こしテキスト"""
    return """
    こんにちは、皆さん。今日の会議を始めます。
    まず、プロジェクトの進捗について報告します。
    現在、開発は順調に進んでいます。
    次に、課題について話し合いましょう。
    """


@pytest.fixture
def sample_minutes():
    """サンプル議事録"""
    return """
# 会議議事録

## 会議概要
- 日時: 2024年1月15日
- 参加者: チームメンバー

## 議題
1. プロジェクト進捗報告
2. 課題の検討

## 決定事項
- 開発は順調に進行中
- 次回会議で詳細レビュー実施
"""


@pytest.fixture
def aiofiles_mock():
    """aiofilesのモックヘルパー"""
    def create_mock(content: bytes):
        """aiofiles.openのモックを作成"""
        mock_aiofiles_open = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
        mock_file_context.__aexit__ = AsyncMock(return_value=None)
        mock_file_context.read = AsyncMock(return_value=content)
        mock_aiofiles_open.return_value = mock_file_context
        return mock_aiofiles_open
    
    return create_mock


@pytest.fixture(autouse=True)
def cleanup_test_dirs():
    """テスト後のクリーンアップ"""
    yield
    
    # テスト用ディレクトリをクリーンアップ
    test_dirs = ['test_uploads', 'test_temp', 'uploads', 'temp']
    for dir_name in test_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name, ignore_errors=True)