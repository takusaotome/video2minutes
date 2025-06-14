import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch
import pytest
import aiofiles
from app.services.transcription import TranscriptionService


class TestTranscriptionServiceExtended:
    """TranscriptionServiceの拡張テスト（カバレッジ向上用）"""

    @pytest.fixture
    def transcription_service(self):
        """TranscriptionServiceインスタンス"""
        return TranscriptionService()

    @pytest.fixture
    def temp_audio_file(self):
        """一時的な音声ファイル"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio content")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def temp_chunks_dir(self):
        """一時的なチャンクディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        # チャンクファイルを作成
        for i in range(3):
            chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
            with open(chunk_path, 'wb') as f:
                f.write(b"fake chunk audio content")
        yield temp_dir
        # クリーンアップは自動で行われる（テスト内でrmtree）

    @pytest.mark.asyncio
    async def test_transcribe_audio_directory_path(self, transcription_service, temp_chunks_dir):
        """ディレクトリパスでの音声文字起こしテスト"""
        with patch.object(transcription_service, '_transcribe_chunked_audio') as mock_chunked:
            mock_chunked.return_value = "チャンク音声の文字起こし結果"

            result = await transcription_service.transcribe_audio(temp_chunks_dir)

            mock_chunked.assert_called_once_with(temp_chunks_dir)
            assert result == "チャンク音声の文字起こし結果"

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_not_found(self, transcription_service):
        """存在しないファイル/ディレクトリのテスト"""
        non_existent_path = "/path/to/non/existent/file.wav"

        with pytest.raises(FileNotFoundError, match="音声ファイルが見つかりません"):
            await transcription_service.transcribe_audio(non_existent_path)

    @pytest.mark.asyncio
    async def test_transcribe_single_file_large_file(self, transcription_service, temp_audio_file):
        """25MB超過ファイルのテスト"""
        with patch('os.path.getsize') as mock_getsize:
            # 30MBのファイルサイズを模擬
            mock_getsize.return_value = 30 * 1024 * 1024

            with pytest.raises(ValueError, match="音声ファイルが25MBを超えています"):
                await transcription_service._transcribe_single_file(temp_audio_file)

    @pytest.mark.asyncio
    async def test_transcribe_single_file_success_mp3(self, transcription_service):
        """MP3ファイルの文字起こし成功テスト"""
        temp_mp3_path = "/tmp/test_audio.mp3"
        
        with patch('os.path.getsize') as mock_getsize:
            with patch('aiofiles.open') as mock_aiofiles:
                with patch.object(transcription_service.client.audio.transcriptions, 'create') as mock_create:
                    # モック設定
                    mock_getsize.return_value = 1024 * 1024  # 1MB
                    
                    # aiofilesのモック
                    mock_file_context = AsyncMock()
                    mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
                    mock_file_context.__aexit__ = AsyncMock(return_value=None)
                    mock_file_context.read = AsyncMock(return_value=b"fake audio data")
                    mock_aiofiles.return_value = mock_file_context

                    # OpenAI APIのモック
                    mock_create.return_value = "これはMP3音声の文字起こし結果です。"

                    result = await transcription_service._transcribe_single_file(temp_mp3_path)

                    # MP3のMIMEタイプが使用されることを確認
                    mock_create.assert_called_once()
                    call_args = mock_create.call_args[1]
                    assert call_args['file'][0] == "audio.mp3"
                    assert call_args['file'][2] == "audio/mp3"
                    assert result == "これはMP3音声の文字起こし結果です。"

    @pytest.mark.asyncio
    async def test_transcribe_single_file_success_wav(self, transcription_service, temp_audio_file):
        """WAVファイルの文字起こし成功テスト"""
        with patch('os.path.getsize') as mock_getsize:
            with patch('aiofiles.open') as mock_aiofiles:
                with patch.object(transcription_service.client.audio.transcriptions, 'create') as mock_create:
                    # モック設定
                    mock_getsize.return_value = 1024 * 1024  # 1MB
                    
                    # aiofilesのモック
                    mock_file_context = AsyncMock()
                    mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
                    mock_file_context.__aexit__ = AsyncMock(return_value=None)
                    mock_file_context.read = AsyncMock(return_value=b"fake audio data")
                    mock_aiofiles.return_value = mock_file_context

                    # OpenAI APIのモック
                    mock_create.return_value = "これはWAV音声の文字起こし結果です。"

                    result = await transcription_service._transcribe_single_file(temp_audio_file)

                    # WAVのMIMEタイプが使用されることを確認
                    mock_create.assert_called_once()
                    call_args = mock_create.call_args[1]
                    assert call_args['file'][0] == "audio.wav"
                    assert call_args['file'][2] == "audio/wav"
                    assert result == "これはWAV音声の文字起こし結果です。"

    @pytest.mark.asyncio
    async def test_transcribe_single_file_empty_response(self, transcription_service, temp_audio_file):
        """空の文字起こし結果のテスト"""
        with patch('os.path.getsize') as mock_getsize:
            with patch('aiofiles.open') as mock_aiofiles:
                with patch.object(transcription_service.client.audio.transcriptions, 'create') as mock_create:
                    # モック設定
                    mock_getsize.return_value = 1024 * 1024  # 1MB
                    
                    # aiofilesのモック
                    mock_file_context = AsyncMock()
                    mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
                    mock_file_context.__aexit__ = AsyncMock(return_value=None)
                    mock_file_context.read = AsyncMock(return_value=b"fake audio data")
                    mock_aiofiles.return_value = mock_file_context

                    # 空の応答をモック
                    mock_create.return_value = ""

                    with pytest.raises(ValueError, match="文字起こし結果が空です"):
                        await transcription_service._transcribe_single_file(temp_audio_file)

    @pytest.mark.asyncio
    async def test_transcribe_single_file_api_error(self, transcription_service, temp_audio_file):
        """API呼び出しエラーのテスト"""
        with patch('os.path.getsize') as mock_getsize:
            with patch('aiofiles.open') as mock_aiofiles:
                with patch.object(transcription_service.client.audio.transcriptions, 'create') as mock_create:
                    # モック設定
                    mock_getsize.return_value = 1024 * 1024  # 1MB
                    
                    # aiofilesのモック
                    mock_file_context = AsyncMock()
                    mock_file_context.__aenter__ = AsyncMock(return_value=mock_file_context)
                    mock_file_context.__aexit__ = AsyncMock(return_value=None)
                    mock_file_context.read = AsyncMock(return_value=b"fake audio data")
                    mock_aiofiles.return_value = mock_file_context

                    # API エラーをモック
                    mock_create.side_effect = Exception("OpenAI API error")

                    with pytest.raises(RuntimeError, match="文字起こし中にエラーが発生しました"):
                        await transcription_service._transcribe_single_file(temp_audio_file)

    @pytest.mark.asyncio
    async def test_transcribe_chunked_audio_success(self, transcription_service, temp_chunks_dir):
        """分割音声ファイル処理成功テスト"""
        with patch.object(transcription_service, '_transcribe_single_file') as mock_transcribe:
            with patch('shutil.rmtree') as mock_rmtree:
                # 各チャンクの文字起こし結果をモック
                mock_transcribe.side_effect = [
                    "最初のチャンクです。",
                    "二番目のチャンクです。",
                    "最後のチャンクです。"
                ]

                result = await transcription_service._transcribe_chunked_audio(temp_chunks_dir)

                # 各チャンクが処理されることを確認
                assert mock_transcribe.call_count == 3
                
                # 結果が結合されることを確認
                assert result == "最初のチャンクです。 二番目のチャンクです。 最後のチャンクです。"
                
                # 一時ディレクトリが削除されることを確認
                mock_rmtree.assert_called_once_with(temp_chunks_dir)

    @pytest.mark.asyncio
    async def test_transcribe_chunked_audio_no_chunks(self, transcription_service):
        """チャンクファイルがない場合のテスト"""
        # 空のディレクトリを作成
        empty_dir = tempfile.mkdtemp()
        
        try:
            with pytest.raises(FileNotFoundError, match="処理する音声チャンクが見つかりません"):
                await transcription_service._transcribe_chunked_audio(empty_dir)
        finally:
            os.rmdir(empty_dir)

    @pytest.mark.asyncio
    async def test_transcribe_chunked_audio_with_empty_chunks(self, transcription_service, temp_chunks_dir):
        """空の文字起こし結果を含むチャンクのテスト"""
        with patch.object(transcription_service, '_transcribe_single_file') as mock_transcribe:
            with patch('shutil.rmtree') as mock_rmtree:
                # 一部が空の文字起こし結果をモック
                mock_transcribe.side_effect = [
                    "最初のチャンクです。",
                    "",  # 空の結果
                    "最後のチャンクです。"
                ]

                result = await transcription_service._transcribe_chunked_audio(temp_chunks_dir)

                # 空でない結果のみが結合されることを確認
                assert result == "最初のチャンクです。 最後のチャンクです。"

    @pytest.mark.asyncio
    async def test_transcribe_chunked_audio_error_cleanup(self, transcription_service, temp_chunks_dir):
        """チャンク処理エラー時のクリーンアップテスト"""
        with patch.object(transcription_service, '_transcribe_single_file') as mock_transcribe:
            with patch('shutil.rmtree') as mock_rmtree:
                with patch('os.path.exists') as mock_exists:
                    # エラーを発生させる
                    mock_transcribe.side_effect = Exception("Transcription error")
                    mock_exists.return_value = True

                    with pytest.raises(RuntimeError, match="分割音声処理エラー"):
                        await transcription_service._transcribe_chunked_audio(temp_chunks_dir)

                    # エラー時にディレクトリが削除されることを確認
                    mock_rmtree.assert_called_with(temp_chunks_dir)

    @pytest.mark.asyncio
    async def test_transcribe_chunked_audio_error_no_cleanup_needed(self, transcription_service, temp_chunks_dir):
        """ディレクトリが存在しない場合のエラーテスト"""
        with patch.object(transcription_service, '_transcribe_single_file') as mock_transcribe:
            with patch('shutil.rmtree') as mock_rmtree:
                with patch('os.path.exists') as mock_exists:
                    # エラーを発生させる
                    mock_transcribe.side_effect = Exception("Transcription error")
                    mock_exists.return_value = False  # ディレクトリが存在しない

                    with pytest.raises(RuntimeError, match="分割音声処理エラー"):
                        await transcription_service._transcribe_chunked_audio(temp_chunks_dir)

                    # 存在しないディレクトリは削除されない
                    mock_rmtree.assert_called_once()  # 最初の削除（成功時）のみ

    def test_different_chunk_file_extensions(self, transcription_service):
        """異なる拡張子のチャンクファイルテスト"""
        # 様々な拡張子のファイルを含むディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 有効なチャンクファイル
            valid_files = [
                "chunk_001.mp3",
                "chunk_002.wav",
                "chunk_003.mp3"
            ]
            
            # 無効なファイル
            invalid_files = [
                "not_chunk.mp3",  # chunk_で始まらない
                "chunk_004.txt",  # 無効な拡張子
                "other_file.wav"  # chunk_で始まらない
            ]
            
            # ファイルを作成
            for filename in valid_files + invalid_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(b"fake content")
            
            # チャンクファイルを取得
            chunk_files = []
            for filename in os.listdir(temp_dir):
                if filename.endswith((".mp3", ".wav")) and filename.startswith("chunk_"):
                    chunk_files.append(os.path.join(temp_dir, filename))
            
            # 有効なチャンクファイルのみが検出されることを確認
            assert len(chunk_files) == 3
            
            # ソートされることを確認
            chunk_files.sort()
            assert "chunk_001.mp3" in chunk_files[0]
            assert "chunk_002.wav" in chunk_files[1]
            assert "chunk_003.mp3" in chunk_files[2]
            
        finally:
            import shutil
            shutil.rmtree(temp_dir)