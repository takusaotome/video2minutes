import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch
import pytest
from app.services.video_processor import VideoProcessor


class TestVideoProcessorSimple:
    """VideoProcessorのシンプルなテスト（カバレッジ向上用）"""

    @pytest.fixture
    def video_processor(self):
        """VideoProcessorインスタンス"""
        return VideoProcessor()

    def test_calculate_max_bitrate_valid_input(self, video_processor):
        """ビットレート計算の正常ケース"""
        bitrate = video_processor._calculate_max_bitrate(600, 25)  # 10分、25MB
        assert bitrate > 0

    def test_calculate_max_bitrate_zero_duration(self, video_processor):
        """ゼロ秒の場合のビットレート計算"""
        bitrate = video_processor._calculate_max_bitrate(0, 25)
        assert bitrate == 32  # デフォルト値

    def test_calculate_max_bitrate_negative_duration(self, video_processor):
        """負の値の場合のビットレート計算"""
        bitrate = video_processor._calculate_max_bitrate(-10, 25)
        assert bitrate == 32  # デフォルト値

    def test_calculate_max_bitrate_minimum_value(self, video_processor):
        """最小値のビットレート計算"""
        bitrate = video_processor._calculate_max_bitrate(10000, 1)  # 非常に長い時間、小さなファイル
        assert bitrate >= 16  # 最低16kbps

    def test_cleanup_temp_files_no_files(self, video_processor):
        """ファイルが存在しない場合のクリーンアップテスト"""
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = []  # ファイルなし

            # エラーが発生しないことを確認
            video_processor.cleanup_temp_files("test-task-123")

    def test_cleanup_temp_files_with_files(self, video_processor):
        """ファイルが存在する場合のクリーンアップテスト"""
        with patch('glob.glob') as mock_glob:
            with patch('os.remove') as mock_remove:
                with patch('os.path.exists') as mock_exists:
                    mock_glob.return_value = ["/tmp/file1.wav", "/tmp/file2.mp3"]
                    mock_exists.return_value = True

                    video_processor.cleanup_temp_files("test-task-123")

                    # 各ファイルが削除されることを確認
                    assert mock_remove.call_count == 2

    @pytest.mark.asyncio
    async def test_get_video_info_simple(self, video_processor):
        """簡易版動画情報取得テスト"""
        with patch('ffmpeg.probe') as mock_probe:
            mock_probe.return_value = {
                "format": {
                    "duration": "600.0",
                    "size": "104857600"
                },
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 1920,
                        "height": 1080
                    }
                ]
            }

            info = await video_processor.get_video_info("/path/to/video.mp4")

            assert info["duration"] == 600.0
            assert info["file_size"] == 104857600
            assert info["width"] == 1920
            assert info["height"] == 1080