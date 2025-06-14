import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.config import settings
from app.services.video_processor import VideoProcessor


class TestVideoProcessor:
    """VideoProcessorのテスト"""

    @pytest.fixture
    def video_processor(self):
        """VideoProcessorインスタンス"""
        return VideoProcessor()

    @pytest.fixture
    def mock_file_handler(self):
        """FileHandlerのモック"""
        with patch("app.services.video_processor.FileHandler") as mock:
            mock.get_file_path.return_value = "/path/to/test_video.mp4"
            mock.get_audio_path.return_value = "/path/to/test_audio.wav"
            yield mock

    @pytest.mark.asyncio
    async def test_extract_audio_success(self, video_processor, mock_file_handler):
        """音声抽出成功テスト"""
        task_id = "test-task-123"

        # VideoProcessor.get_video_infoをモック
        with patch.object(video_processor, "get_video_info") as mock_get_info:
            mock_get_info.return_value = {"duration": 120.0}

            # ffmpeg実行をモック
            with patch.object(
                video_processor, "_run_ffmpeg_extract_mp3", new_callable=AsyncMock
            ) as mock_ffmpeg:
                with patch("os.path.exists", return_value=True):
                    with patch("os.path.getsize", return_value=1024 * 1024):  # 1MB
                        result = await video_processor.extract_audio(task_id)

                        # FileHandlerの呼び出し確認
                        mock_file_handler.get_file_path.assert_called_once_with(task_id)
                        mock_file_handler.get_audio_path.assert_called_once_with(
                            task_id
                        )

                        # ffmpeg実行確認
                        mock_ffmpeg.assert_called_once()

                        # 結果確認（.wavから.mp3に変換されることを考慮）
                        assert result.endswith(".mp3")

    @pytest.mark.asyncio
    async def test_extract_audio_video_file_not_found(
        self, video_processor, mock_file_handler
    ):
        """動画ファイルが見つからない場合のテスト"""
        task_id = "non-existent-task"
        mock_file_handler.get_file_path.return_value = None

        with pytest.raises(FileNotFoundError) as exc_info:
            await video_processor.extract_audio(task_id)

        assert "動画ファイルが見つかりません" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_audio_output_file_not_created(
        self, video_processor, mock_file_handler
    ):
        """出力ファイルが作成されない場合のテスト"""
        task_id = "test-task-456"

        with patch.object(video_processor, "get_video_info") as mock_get_info:
            mock_get_info.return_value = {"duration": 120.0}

            with patch.object(
                video_processor, "_run_ffmpeg_extract_mp3", new_callable=AsyncMock
            ):
                with patch("os.path.exists", return_value=False):
                    with pytest.raises(RuntimeError) as exc_info:
                        await video_processor.extract_audio(task_id)

                    assert "音声ファイルの生成に失敗しました" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_audio_ffmpeg_error(self, video_processor, mock_file_handler):
        """ffmpegエラー時のテスト"""
        task_id = "test-task-789"

        with patch.object(video_processor, "get_video_info") as mock_get_info:
            mock_get_info.return_value = {"duration": 120.0}

            # ffmpeg実行でエラーを発生させる
            with patch.object(
                video_processor, "_run_ffmpeg_extract_mp3", new_callable=AsyncMock
            ) as mock_ffmpeg:
                mock_ffmpeg.side_effect = RuntimeError("ffmpeg error")

                with patch("os.path.exists", return_value=True):
                    with patch("os.remove") as mock_remove:
                        with pytest.raises(RuntimeError) as exc_info:
                            await video_processor.extract_audio(task_id)

                        assert "音声抽出中にエラーが発生しました" in str(exc_info.value)
                        # エラー時にファイルが削除されることを確認
                        mock_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_ffmpeg_extract_success(self, video_processor):
        """ffmpeg実行成功テスト"""
        input_path = "/path/to/input.mp4"
        output_path = "/path/to/output.wav"

        # asyncio.create_subprocess_execをモック
        mock_process = Mock()
        mock_process.communicate = AsyncMock(return_value=(b"success", b""))
        mock_process.returncode = 0

        with patch(
            "asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_process

            # エラーが発生しないことを確認
            await video_processor._run_ffmpeg_extract(input_path, output_path)

            # subprocess実行確認
            mock_exec.assert_called_once()
            mock_process.communicate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_ffmpeg_extract_failure(self, video_processor):
        """ffmpeg実行失敗テスト"""
        input_path = "/path/to/input.mp4"
        output_path = "/path/to/output.wav"

        # ffmpegエラーをシミュレート
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"ffmpeg error occurred")
        )
        mock_process.returncode = 1

        with patch(
            "asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_process

            with pytest.raises(RuntimeError) as exc_info:
                await video_processor._run_ffmpeg_extract(input_path, output_path)

            assert "ffmpegエラー" in str(exc_info.value)
            assert "ffmpeg error occurred" in str(exc_info.value)

    def test_get_video_info_success(self, video_processor):
        """動画情報取得成功テスト"""
        video_path = "/path/to/video.mp4"

        # ffmpeg.probeの戻り値をモック
        mock_probe_data = {
            "format": {"duration": "120.5", "size": "1048576"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "44100",
                    "channels": 2,
                },
            ],
        }

        with patch("ffmpeg.probe", return_value=mock_probe_data):
            result = video_processor.get_video_info(video_path)

            # 結果確認
            assert result["duration"] == 120.5
            assert result["size"] == 1048576
            assert result["video"]["codec"] == "h264"
            assert result["video"]["width"] == 1920
            assert result["video"]["height"] == 1080
            assert result["video"]["fps"] == 30.0
            assert result["audio"]["codec"] == "aac"
            assert result["audio"]["sample_rate"] == 44100
            assert result["audio"]["channels"] == 2

    def test_get_video_info_no_video_stream(self, video_processor):
        """動画ストリームなしの場合のテスト"""
        video_path = "/path/to/audio_only.mp4"

        # 音声のみのファイルをシミュレート
        mock_probe_data = {
            "format": {"duration": "60.0", "size": "524288"},
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "44100",
                    "channels": 2,
                }
            ],
        }

        with patch("ffmpeg.probe", return_value=mock_probe_data):
            result = video_processor.get_video_info(video_path)

            # 動画情報がNoneであることを確認
            assert result["video"]["codec"] is None
            assert result["video"]["width"] is None
            assert result["video"]["height"] is None
            assert result["video"]["fps"] is None

            # 音声情報は正常に取得できることを確認
            assert result["audio"]["codec"] == "aac"

    def test_get_video_info_error(self, video_processor):
        """動画情報取得エラーテスト"""
        video_path = "/path/to/invalid_video.mp4"

        with patch("ffmpeg.probe", side_effect=Exception("Probe failed")):
            with pytest.raises(RuntimeError) as exc_info:
                video_processor.get_video_info(video_path)

            assert "動画情報の取得に失敗しました" in str(exc_info.value)


class TestVideoProcessorIntegration:
    """VideoProcessorの結合テスト"""

    @pytest.mark.asyncio
    async def test_extract_audio_with_real_directories(self):
        """実際のディレクトリを使用した音声抽出テスト"""
        video_processor = VideoProcessor()

        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            # 設定を一時的に変更
            original_upload_dir = settings.upload_dir
            original_temp_dir = settings.temp_dir

            settings.upload_dir = os.path.join(temp_dir, "uploads")
            settings.temp_dir = os.path.join(temp_dir, "temp")

            os.makedirs(settings.upload_dir, exist_ok=True)
            os.makedirs(settings.temp_dir, exist_ok=True)

            try:
                task_id = "integration-test"
                video_path = os.path.join(settings.upload_dir, f"{task_id}.mp4")

                # ダミー動画ファイルを作成
                with open(video_path, "wb") as f:
                    f.write(b"fake video content")

                # ffmpeg.probeをモック（実際のffprobeは実行しない）
                mock_probe_data = {
                    "format": {"duration": "60.0", "size": "1048576"},
                    "streams": [
                        {
                            "codec_type": "video",
                            "codec_name": "h264",
                            "width": 1920,
                            "height": 1080,
                            "r_frame_rate": "30/1",
                        },
                        {
                            "codec_type": "audio",
                            "codec_name": "aac",
                            "sample_rate": "44100",
                            "channels": 2,
                        },
                    ],
                }
                with patch("ffmpeg.probe", return_value=mock_probe_data):
                    # ffmpeg実行をモック（実際のffmpegは実行しない）
                    with patch.object(
                        video_processor,
                        "_run_ffmpeg_extract_mp3",
                        new_callable=AsyncMock,
                    ):
                        # 出力ファイルが作成されたことをシミュレート
                        audio_path = os.path.join(settings.temp_dir, f"{task_id}.mp3")
                        with open(audio_path, "wb") as f:
                            f.write(b"fake audio content")

                        result = await video_processor.extract_audio(task_id)
                        assert result == audio_path
                        assert os.path.exists(result)

            finally:
                # 設定を元に戻す
                settings.upload_dir = original_upload_dir
                settings.temp_dir = original_temp_dir
