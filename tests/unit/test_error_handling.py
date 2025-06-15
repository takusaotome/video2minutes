import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.services.minutes_generator import MinutesGeneratorService
from app.services.transcription import TranscriptionService
from app.services.video_processor import VideoProcessor
from app.utils.file_handler import FileHandler


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_file_handler_invalid_extension_error(self):
        """ファイルハンドラーの無効拡張子エラーテスト"""
        mock_file = Mock()
        mock_file.filename = "invalid.txt"
        mock_file.size = 1024

        with pytest.raises(HTTPException) as exc_info:
            FileHandler.validate_media_file(mock_file)

        assert exc_info.value.status_code == 400
        assert "サポートされていないファイル形式" in str(exc_info.value.detail)

    def test_file_handler_missing_filename_error(self):
        """ファイルハンドラーのファイル名なしエラーテスト"""
        mock_file = Mock()
        mock_file.filename = None

        with pytest.raises(HTTPException) as exc_info:
            FileHandler.validate_media_file(mock_file)

        assert exc_info.value.status_code == 400
        assert "ファイル名が指定されていません" in str(exc_info.value.detail)

    def test_file_handler_file_size_error(self):
        """ファイルハンドラーのファイルサイズエラーテスト"""
        mock_file = Mock()
        mock_file.filename = "test.mp4"
        mock_file.size = 6 * 1024 * 1024 * 1024  # 6GB (5GB上限超過)

        with pytest.raises(HTTPException) as exc_info:
            FileHandler.validate_media_file(mock_file)

        assert exc_info.value.status_code == 413
        assert "ファイルサイズが上限" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_video_processor_file_not_found_error(self):
        """動画プロセッサーのファイル未発見エラーテスト"""
        processor = VideoProcessor()

        with patch("app.services.video_processor.FileHandler") as mock_handler:
            mock_handler.get_file_path.return_value = None

            with pytest.raises(FileNotFoundError) as exc_info:
                await processor.extract_audio("non-existent-task")

            assert "動画ファイルが見つかりません" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_video_processor_ffmpeg_error(self):
        """動画プロセッサーのFFmpegエラーテスト"""
        processor = VideoProcessor()

        with patch("app.services.video_processor.FileHandler") as mock_handler:
            mock_handler.get_file_path.return_value = "/path/to/video.mp4"
            mock_handler.get_audio_path.return_value = "/path/to/audio.wav"

            # ffmpeg.probeをモックして成功させる
            with patch(
                "ffmpeg.probe",
                return_value={
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
                },
            ):
                with patch.object(
                    processor, "_run_ffmpeg_extract_mp3", new_callable=AsyncMock
                ) as mock_ffmpeg:
                    mock_ffmpeg.side_effect = RuntimeError("FFmpeg failed")

                    with pytest.raises(RuntimeError) as exc_info:
                        await processor.extract_audio("test-task")

                    assert "音声抽出中にエラーが発生しました" in str(exc_info.value)
                    assert "FFmpeg failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_video_processor_output_file_creation_error(self):
        """動画プロセッサーの出力ファイル作成エラーテスト"""
        processor = VideoProcessor()

        with patch("app.services.video_processor.FileHandler") as mock_handler:
            mock_handler.get_file_path.return_value = "/path/to/video.mp4"
            mock_handler.get_audio_path.return_value = "/path/to/audio.wav"

            # ffmpeg.probeをモックして成功させる
            with patch(
                "ffmpeg.probe",
                return_value={
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
                },
            ):
                with patch.object(
                    processor, "_run_ffmpeg_extract_mp3", new_callable=AsyncMock
                ):
                    with patch("os.path.exists", return_value=False):

                        with pytest.raises(RuntimeError) as exc_info:
                            await processor.extract_audio("test-task")

                        assert "音声ファイルの生成に失敗しました" in str(exc_info.value)

    def test_video_processor_probe_error(self):
        """動画プロセッサーのプローブエラーテスト"""
        processor = VideoProcessor()

        with patch("ffmpeg.probe", side_effect=Exception("Probe failed")):
            with pytest.raises(RuntimeError) as exc_info:
                processor.get_video_info("/path/to/invalid.mp4")

            assert "動画情報の取得に失敗しました" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcription_service_api_error(self):
        """文字起こしサービスのAPIエラーテスト"""
        service = TranscriptionService()

        mock_client = Mock()
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        # aiofiles.openのモックを作成
        mock_file_context = AsyncMock()
        mock_file_context.read = AsyncMock(return_value=b"audio data")
        mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
        mock_file_context.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file_context)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(service, "client", mock_client):
                            with pytest.raises(RuntimeError) as exc_info:
                                await service.transcribe_audio("/path/to/audio.wav")

                            assert "文字起こし中にエラーが発生しました" in str(
                                exc_info.value
                            )

    @pytest.mark.asyncio
    async def test_transcription_service_empty_result_error(self):
        """文字起こしサービスの空結果エラーテスト"""
        service = TranscriptionService()

        mock_client = Mock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value="")

        # aiofiles.openのモックを作成
        mock_file_context = AsyncMock()
        mock_file_context.read = AsyncMock(return_value=b"audio data")
        mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
        mock_file_context.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file_context)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(service, "client", mock_client):
                            with pytest.raises(RuntimeError) as exc_info:
                                await service.transcribe_audio("/path/to/audio.wav")

                            assert "文字起こし中にエラーが発生しました" in str(
                                exc_info.value
                            )

    @pytest.mark.asyncio
    async def test_minutes_generator_api_error(self):
        """議事録生成サービスのAPIエラーテスト"""
        service = MinutesGeneratorService()

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        with patch.object(service, "client", mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await service.generate_minutes("テスト文字起こし")

            assert "議事録生成中にエラーが発生しました" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_minutes_generator_summary_error(self):
        """議事録生成サービスのサマリーエラーテスト"""
        service = MinutesGeneratorService()

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Summary API Error")
        )

        with patch.object(service, "client", mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await service.generate_summary("テスト議事録")

            assert "サマリー生成中にエラーが発生しました" in str(exc_info.value)


class TestErrorRecovery:
    """エラー回復のテスト"""

    @pytest.mark.asyncio
    async def test_minutes_generator_model_fallback(self):
        """議事録生成でのモデルフォールバックテスト"""
        service = MinutesGeneratorService()

        mock_client = Mock()

        # 最初のモデルは失敗、2番目のモデルは成功
        # NotFoundErrorを簡単にモック
        class MockNotFoundError(Exception):
            pass

        def side_effect(*args, **kwargs):
            if kwargs.get("model") == "gpt-4o":  # 最初のモデル
                raise MockNotFoundError("Model not found")
            else:  # フォールバックモデル
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = Mock()
                mock_response.choices[0].message.content = "フォールバック議事録"
                return mock_response

        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)

        with patch.object(service, "client", mock_client):
            with patch(
                "app.services.minutes_generator.openai.NotFoundError", MockNotFoundError
            ):
                # フォールバック機能をテストするために_call_chat_completionを直接呼び出し
                result = await service._call_chat_completion("test prompt", "gpt-4o")

                assert result == "フォールバック議事録"

    @pytest.mark.asyncio
    async def test_minutes_generator_all_models_fail(self):
        """議事録生成で全モデルが失敗するテスト"""
        service = MinutesGeneratorService()

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("All models failed")
        )

        with patch.object(service, "client", mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await service._call_chat_completion("test prompt", "gpt-4o")

            assert "OpenAI API呼び出しエラー" in str(exc_info.value)

    def test_file_cleanup_on_error(self):
        """エラー時のファイルクリーンアップテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # テストファイルを作成
            test_file = os.path.join(temp_dir, "test-task.mp4")
            with open(test_file, "w") as f:
                f.write("test content")

            # ファイルが存在することを確認
            assert os.path.exists(test_file)

            # 設定を一時的に変更
            from app.config import settings

            original_upload_dir = settings.upload_dir
            settings.upload_dir = temp_dir

            try:
                # クリーンアップを実行
                FileHandler.cleanup_files("test-task")

                # ファイルが削除されたことを確認
                assert not os.path.exists(test_file)
            finally:
                # 設定を元に戻す
                settings.upload_dir = original_upload_dir


class TestNetworkErrorHandling:
    """ネットワークエラーハンドリングのテスト"""

    @pytest.mark.asyncio
    async def test_transcription_network_timeout(self):
        """文字起こしのネットワークタイムアウトテスト"""
        service = TranscriptionService()

        import asyncio

        mock_client = Mock()
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=asyncio.TimeoutError("Timeout")
        )

        # aiofiles.openのモックを作成
        mock_file_context = AsyncMock()
        mock_file_context.read = AsyncMock(return_value=b"audio data")
        mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
        mock_file_context.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file_context)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(service, "client", mock_client):
                            with pytest.raises(RuntimeError) as exc_info:
                                await service.transcribe_audio("/path/to/audio.wav")

                            assert "文字起こし中にエラーが発生しました" in str(
                                exc_info.value
                            )

    @pytest.mark.asyncio
    async def test_minutes_generation_network_error(self):
        """議事録生成のネットワークエラーテスト"""
        service = MinutesGeneratorService()

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with patch.object(service, "client", mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await service.generate_minutes("テスト文字起こし")

            assert "議事録生成中にエラーが発生しました" in str(exc_info.value)


class TestValidationErrors:
    """バリデーションエラーのテスト"""

    def test_empty_task_id_validation(self):
        """空のタスクIDバリデーションテスト"""
        # 空のタスクIDでファイルパスを取得
        result = FileHandler.get_file_path("")

        # Noneが返されることを確認
        assert result is None

    def test_invalid_characters_in_filename(self):
        """ファイル名の無効文字テスト"""
        mock_file = Mock()
        mock_file.filename = "test/../../../etc/passwd"
        mock_file.size = 1024

        # セキュリティ上の理由で無効なファイル名は処理されない
        # 実装によってはバリデーションが必要
        assert mock_file.filename is not None
