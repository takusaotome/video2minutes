from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest

from app.config import settings
from app.services.transcription import TranscriptionService


class TestTranscriptionService:
    """TranscriptionServiceのテスト"""

    @pytest.fixture
    def transcription_service(self):
        """TranscriptionServiceインスタンス"""
        return TranscriptionService()

    @pytest.fixture
    def mock_openai_client(self):
        """OpenAIクライアントのモック"""
        mock_client = Mock()
        mock_client.audio = Mock()
        mock_client.audio.transcriptions = Mock()
        mock_client.audio.transcriptions.create = AsyncMock()
        return mock_client

    def create_aiofiles_mock(self, audio_data):
        """aiofiles.openのモックを作成するヘルパー"""
        mock_file_context = AsyncMock()
        mock_file_context.read = AsyncMock(return_value=audio_data)
        mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
        mock_file_context.__aexit__ = AsyncMock(return_value=None)

        mock_aiofiles_open = Mock(return_value=mock_file_context)
        return mock_aiofiles_open

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(
        self, transcription_service, mock_openai_client
    ):
        """文字起こし成功テスト"""
        audio_file_path = "/path/to/audio.wav"
        expected_transcription = "これはテスト用の音声文字起こし結果です。"

        # OpenAI APIの戻り値をモック
        mock_openai_client.audio.transcriptions.create.return_value = (
            expected_transcription
        )

        # ファイル読み込みをモック
        mock_audio_data = b"fake audio data"

        # aiofiles.openのモックを作成
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=mock_audio_data)
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)

        mock_aiofiles_open = Mock(return_value=mock_file)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):  # 1KB
                        with patch.object(
                            transcription_service, "client", mock_openai_client
                        ):
                            result = await transcription_service.transcribe_audio(
                                audio_file_path
                            )

                        # 結果確認
                        assert result == expected_transcription

                        # OpenAI API呼び出し確認
                        mock_openai_client.audio.transcriptions.create.assert_called_once_with(
                            model=settings.whisper_model,
                            file=("audio.wav", mock_audio_data, "audio/wav"),
                            language=settings.whisper_language,
                            response_format="text",
                        )

    @pytest.mark.asyncio
    async def test_transcribe_audio_empty_result(
        self, transcription_service, mock_openai_client
    ):
        """空の文字起こし結果のテスト"""
        audio_file_path = "/path/to/audio.wav"

        # 空の結果を返すようにモック
        mock_openai_client.audio.transcriptions.create.return_value = ""

        mock_audio_data = b"fake audio data"

        # aiofiles.openのモックを作成
        mock_aiofiles_open = self.create_aiofiles_mock(mock_audio_data)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(
                            transcription_service, "client", mock_openai_client
                        ):
                            with pytest.raises(RuntimeError) as exc_info:
                                await transcription_service.transcribe_audio(
                                    audio_file_path
                                )

                assert "文字起こし中にエラーが発生しました" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_audio_whitespace_only_result(
        self, transcription_service, mock_openai_client
    ):
        """空白のみの文字起こし結果のテスト"""
        audio_file_path = "/path/to/audio.wav"

        # 空白のみの結果を返すようにモック
        mock_openai_client.audio.transcriptions.create.return_value = "   \n\t  "

        mock_audio_data = b"fake audio data"

        # aiofiles.openのモックを作成
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=mock_audio_data)
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(
                            transcription_service, "client", mock_openai_client
                        ):
                            with pytest.raises(RuntimeError) as exc_info:
                                await transcription_service.transcribe_audio(
                                    audio_file_path
                                )

                assert "文字起こし中にエラーが発生しました" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_audio_api_error(
        self, transcription_service, mock_openai_client
    ):
        """OpenAI APIエラーのテスト"""
        audio_file_path = "/path/to/audio.wav"

        # API呼び出しでエラーを発生させる
        mock_openai_client.audio.transcriptions.create.side_effect = Exception(
            "API Error"
        )

        mock_audio_data = b"fake audio data"

        # aiofiles.openのモックを作成
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=mock_audio_data)
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(
                            transcription_service, "client", mock_openai_client
                        ):
                            with pytest.raises(RuntimeError) as exc_info:
                                await transcription_service.transcribe_audio(
                                    audio_file_path
                                )

                assert "文字起こし中にエラーが発生しました" in str(exc_info.value)
                assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_read_error(self, transcription_service):
        """ファイル読み込みエラーのテスト"""
        audio_file_path = "/path/to/nonexistent.wav"

        # ファイル読み込みエラーをシミュレート
        with patch("aiofiles.open", side_effect=FileNotFoundError("File not found")):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with pytest.raises(RuntimeError) as exc_info:
                            await transcription_service.transcribe_audio(
                                audio_file_path
                            )

            assert "文字起こし中にエラーが発生しました" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_success(
        self, transcription_service, mock_openai_client
    ):
        """タイムスタンプ付き文字起こし成功テスト"""
        audio_file_path = "/path/to/audio.wav"
        expected_response = {
            "text": "これはテスト用の音声文字起こし結果です。",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "これはテスト用の"},
                {"start": 2.5, "end": 5.0, "text": "音声文字起こし結果です。"},
            ],
        }

        # OpenAI APIの戻り値をモック
        mock_openai_client.audio.transcriptions.create.return_value = expected_response

        mock_audio_data = b"fake audio data"

        # aiofiles.openのモックを作成
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=mock_audio_data)
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(
                            transcription_service, "client", mock_openai_client
                        ):
                            result = (
                                await transcription_service.transcribe_with_timestamps(
                                    audio_file_path
                                )
                            )

                # 結果確認
                assert result == expected_response
                assert "text" in result
                assert "segments" in result

                # OpenAI API呼び出し確認
                mock_openai_client.audio.transcriptions.create.assert_called_once_with(
                    model=settings.whisper_model,
                    file=("audio.wav", mock_audio_data, "audio/wav"),
                    language=settings.whisper_language,
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                )

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_error(
        self, transcription_service, mock_openai_client
    ):
        """タイムスタンプ付き文字起こしエラーテスト"""
        audio_file_path = "/path/to/audio.wav"

        # API呼び出しでエラーを発生させる
        mock_openai_client.audio.transcriptions.create.side_effect = Exception(
            "Timestamp API Error"
        )

        mock_audio_data = b"fake audio data"

        # aiofiles.openのモックを作成
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=mock_audio_data)
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(
                            transcription_service, "client", mock_openai_client
                        ):
                            with pytest.raises(RuntimeError) as exc_info:
                                await transcription_service.transcribe_with_timestamps(
                                    audio_file_path
                                )

                assert "タイムスタンプ付き文字起こし中にエラーが発生しました" in str(
                    exc_info.value
                )
                assert "Timestamp API Error" in str(exc_info.value)

    def test_format_transcription_with_paragraphs(self, transcription_service):
        """文字起こしテキストの段落整形テスト"""
        input_text = "これは最初の文です。次は二番目の文です。三番目の文章です。四番目の文です。五番目の文章です。六番目の文です。"

        result = transcription_service.format_transcription_with_paragraphs(input_text)

        # 段落が適切に分かれていることを確認
        paragraphs = result.split("\n\n")
        assert len(paragraphs) == 2

        # 最初の段落が3文から構成されていることを確認
        first_paragraph = paragraphs[0]
        assert first_paragraph.count("。") == 3
        assert "これは最初の文です。" in first_paragraph
        assert "次は二番目の文です。" in first_paragraph
        assert "三番目の文章です。" in first_paragraph

        # 2番目の段落が残りの文から構成されていることを確認
        second_paragraph = paragraphs[1]
        assert "四番目の文です。" in second_paragraph
        assert "五番目の文章です。" in second_paragraph
        assert "六番目の文です。" in second_paragraph

    def test_format_transcription_with_paragraphs_short_text(
        self, transcription_service
    ):
        """短いテキストの段落整形テスト"""
        input_text = "短い文です。もう一つの短い文です。"

        result = transcription_service.format_transcription_with_paragraphs(input_text)

        # 1つの段落になることを確認
        paragraphs = result.split("\n\n")
        assert len(paragraphs) == 1
        assert result == "短い文です。もう一つの短い文です。"

    def test_format_transcription_with_paragraphs_empty_text(
        self, transcription_service
    ):
        """空のテキストの段落整形テスト"""
        input_text = ""

        result = transcription_service.format_transcription_with_paragraphs(input_text)

        # 空の結果になることを確認
        assert result == ""

    def test_format_transcription_with_paragraphs_no_periods(
        self, transcription_service
    ):
        """句点がないテキストの段落整形テスト"""
        input_text = "句点がないテキストです そのまま返されるはずです"

        result = transcription_service.format_transcription_with_paragraphs(input_text)

        # そのまま返されることを確認（句点で分割できない場合）
        assert result == "句点がないテキストです そのまま返されるはずです。"


class TestTranscriptionServiceConfiguration:
    """TranscriptionServiceの設定関連テスト"""

    def test_initialization_with_api_key(self):
        """API キーを使用した初期化テスト"""
        with patch("openai.AsyncOpenAI") as mock_openai:
            service = TranscriptionService()

            # OpenAI クライアントが正しいAPI キーで初期化されることを確認
            mock_openai.assert_called_once_with(api_key=settings.openai_api_key)

    @pytest.mark.asyncio
    async def test_transcribe_audio_uses_correct_settings(self):
        """文字起こしで正しい設定が使用されることのテスト"""
        service = TranscriptionService()
        audio_file_path = "/path/to/audio.wav"

        mock_client = Mock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value="test result")

        mock_audio_data = b"fake audio data"

        # aiofiles.openのモックを作成
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=mock_audio_data)
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles_open = Mock(return_value=mock_file)

        with patch("aiofiles.open", mock_aiofiles_open):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.isdir", return_value=False):
                    with patch("os.path.getsize", return_value=1024):
                        with patch.object(service, "client", mock_client):
                            await service.transcribe_audio(audio_file_path)

                # 正しい設定が使用されることを確認
                call_args = mock_client.audio.transcriptions.create.call_args
                assert call_args[1]["model"] == settings.whisper_model
                assert call_args[1]["language"] == settings.whisper_language
                assert call_args[1]["response_format"] == "text"
