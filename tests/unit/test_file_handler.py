import os
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, UploadFile

from app.config import settings
from app.utils.file_handler import FileHandler


class TestFileHandler:
    """FileHandlerのテスト"""

    def test_generate_task_id(self):
        """タスクID生成のテスト"""
        task_id = FileHandler.generate_task_id()

        assert isinstance(task_id, str)
        assert len(task_id) > 0

        # 複数回生成して異なることを確認
        task_id2 = FileHandler.generate_task_id()
        assert task_id != task_id2

    def test_validate_video_file_success(self):
        """動画ファイルバリデーション成功テスト"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_video.mp4"
        mock_file.size = 1024 * 1024  # 1MB

        # 例外が発生しないことを確認
        try:
            FileHandler.validate_video_file(mock_file)
        except HTTPException:
            pytest.fail("validate_video_file raised HTTPException unexpectedly")

    def test_validate_video_file_no_filename(self):
        """ファイル名なしバリデーションテスト"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = None

        with pytest.raises(HTTPException) as exc_info:
            FileHandler.validate_video_file(mock_file)

        assert exc_info.value.status_code == 400
        assert "ファイル名が指定されていません" in str(exc_info.value.detail)

    def test_validate_video_file_invalid_extension(self):
        """無効な拡張子バリデーションテスト"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_file.txt"

        with pytest.raises(HTTPException) as exc_info:
            FileHandler.validate_video_file(mock_file)

        assert exc_info.value.status_code == 400
        assert "サポートされていないファイル形式" in str(exc_info.value.detail)

    def test_validate_video_file_size_too_large(self):
        """ファイルサイズ上限超過バリデーションテスト"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_video.mp4"
        mock_file.size = settings.max_file_size + 1

        with pytest.raises(HTTPException) as exc_info:
            FileHandler.validate_video_file(mock_file)

        assert exc_info.value.status_code == 413
        assert "ファイルサイズが上限" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_save_uploaded_file_success(self, mock_settings):
        """ファイル保存成功テスト"""
        # テスト用ディレクトリを作成
        os.makedirs(mock_settings.upload_dir, exist_ok=True)

        # モックファイルデータ
        test_data = b"fake video content"

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_video.mp4"
        mock_file.read = AsyncMock()
        mock_file.read.side_effect = [test_data, b""]  # 最初にデータ、次に空

        task_id = "test-task-123"

        file_path, file_size = await FileHandler.save_uploaded_file(mock_file, task_id)

        # 結果確認
        expected_path = os.path.join(mock_settings.upload_dir, f"{task_id}.mp4")
        assert file_path == expected_path
        assert file_size == len(test_data)

        # ファイルが実際に作成されたことを確認
        assert os.path.exists(file_path)

        # ファイル内容確認
        with open(file_path, "rb") as f:
            content = f.read()
        assert content == test_data

    @pytest.mark.asyncio
    async def test_save_uploaded_file_size_limit_exceeded(self, mock_settings):
        """ファイルサイズ上限超過時の保存テスト"""
        # テスト用ディレクトリを作成
        os.makedirs(mock_settings.upload_dir, exist_ok=True)

        # 上限を超えるサイズのデータを生成
        large_data = b"x" * (settings.max_file_size + 1)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large_video.mp4"
        mock_file.read = AsyncMock()
        mock_file.read.side_effect = [large_data, b""]

        task_id = "test-task-456"

        with pytest.raises(HTTPException) as exc_info:
            await FileHandler.save_uploaded_file(mock_file, task_id)

        assert exc_info.value.status_code == 413
        assert "ファイルサイズが上限" in str(exc_info.value.detail)

        # ファイルが作成されていないことを確認
        expected_path = os.path.join(mock_settings.upload_dir, f"{task_id}.mp4")
        assert not os.path.exists(expected_path)

    def test_get_file_path_exists(self, mock_settings):
        """存在するファイルパス取得テスト"""
        # テスト用ディレクトリを作成
        os.makedirs(mock_settings.upload_dir, exist_ok=True)

        task_id = "test-task-789"
        test_file_path = os.path.join(mock_settings.upload_dir, f"{task_id}.mp4")

        # テストファイルを作成
        with open(test_file_path, "w") as f:
            f.write("test content")

        result = FileHandler.get_file_path(task_id)
        assert result == test_file_path

    def test_get_file_path_not_exists(self, mock_settings):
        """存在しないファイルパス取得テスト"""
        result = FileHandler.get_file_path("non-existent-task")
        assert result is None

    def test_get_audio_path(self, mock_settings):
        """音声ファイルパス取得テスト"""
        task_id = "test-audio-task"
        expected_path = os.path.join(mock_settings.temp_dir, f"{task_id}.mp3")

        result = FileHandler.get_audio_path(task_id)
        assert result == expected_path

    def test_cleanup_files(self, mock_settings):
        """ファイルクリーンアップテスト"""
        # テスト用ディレクトリを作成
        os.makedirs(mock_settings.upload_dir, exist_ok=True)
        os.makedirs(mock_settings.temp_dir, exist_ok=True)

        task_id = "cleanup-test-task"

        # テストファイルを作成
        video_file = os.path.join(mock_settings.upload_dir, f"{task_id}.mp4")
        audio_file = os.path.join(mock_settings.temp_dir, f"{task_id}.wav")

        with open(video_file, "w") as f:
            f.write("video content")
        with open(audio_file, "w") as f:
            f.write("audio content")

        # ファイルが存在することを確認
        assert os.path.exists(video_file)
        assert os.path.exists(audio_file)

        # クリーンアップ実行
        FileHandler.cleanup_files(task_id)

        # ファイルが削除されたことを確認
        assert not os.path.exists(video_file)
        assert not os.path.exists(audio_file)

    def test_cleanup_files_no_files(self, mock_settings):
        """存在しないファイルのクリーンアップテスト"""
        # ファイルが存在しない場合でもエラーにならないことを確認
        try:
            FileHandler.cleanup_files("non-existent-task")
        except Exception:
            pytest.fail("cleanup_files raised exception unexpectedly")


class TestFileValidation:
    """ファイルバリデーション関連のテスト"""

    @pytest.mark.parametrize(
        "filename,should_pass",
        [
            ("video.mp4", True),
            ("video.avi", True),
            ("video.mov", True),
            ("video.mkv", True),
            ("video.wmv", True),
            ("video.flv", True),
            ("video.webm", True),
            ("VIDEO.MP4", True),  # 大文字
            ("video.txt", False),
            ("video.jpg", False),
            ("video.mp3", False),
            ("video", False),  # 拡張子なし
        ],
    )
    def test_file_extension_validation(self, filename, should_pass):
        """ファイル拡張子バリデーションのパラメータ化テスト"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = filename
        mock_file.size = 1024

        if should_pass:
            try:
                FileHandler.validate_video_file(mock_file)
            except HTTPException:
                pytest.fail(f"validate_video_file should pass for {filename}")
        else:
            with pytest.raises(HTTPException):
                FileHandler.validate_video_file(mock_file)
