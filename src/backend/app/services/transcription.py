import os
from typing import Optional

import aiofiles
import openai

from app.config import settings
from app.utils.logger import LoggerMixin


class TranscriptionService(LoggerMixin):
    """文字起こしサービス"""

    def __init__(self):
        """OpenAI クライアントを初期化"""
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.logger.info("TranscriptionService初期化完了")

    async def transcribe_audio(self, audio_file_path: str) -> str:
        """音声ファイルを文字起こし（分割ファイル対応）"""

        self.logger.info(f"文字起こし開始: {audio_file_path}")

        # ディレクトリかファイルかを判定
        if os.path.isdir(audio_file_path):
            # 分割された音声ファイルがある場合
            return await self._transcribe_chunked_audio(audio_file_path)
        elif os.path.isfile(audio_file_path):
            # 単一の音声ファイルの場合
            return await self._transcribe_single_file(audio_file_path)
        else:
            self.logger.error(f"音声ファイルが見つかりません: {audio_file_path}")
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_file_path}")

    async def _transcribe_single_file(self, audio_file_path: str) -> str:
        """単一の音声ファイルを文字起こし"""

        file_size = os.path.getsize(audio_file_path)
        self.logger.info(f"音声ファイルサイズ: {file_size} bytes")

        # ファイルサイズチェック
        if file_size > 25 * 1024 * 1024:
            self.logger.error(f"ファイルサイズが制限を超過: {file_size} bytes")
            raise ValueError("音声ファイルが25MBを超えています")

        try:
            # 音声ファイルを開いて文字起こし
            async with aiofiles.open(audio_file_path, "rb") as audio_file:
                # ファイル内容を読み込み
                audio_data = await audio_file.read()

                self.logger.info(
                    f"Whisper API呼び出し開始 - モデル: {settings.whisper_model}, 言語: {settings.whisper_language}"
                )

                # ファイル拡張子に基づいてMIMEタイプを決定
                file_ext = os.path.splitext(audio_file_path)[1].lower()
                mime_type = "audio/mp3" if file_ext == ".mp3" else "audio/wav"
                filename = f"audio{file_ext}"

                # OpenAI Whisper APIを呼び出し
                response = await self.client.audio.transcriptions.create(
                    model=settings.whisper_model,
                    file=(filename, audio_data, mime_type),
                    language=settings.whisper_language,
                    response_format="text",
                )

                if not response or not response.strip():
                    self.logger.warning("文字起こし結果が空でした")
                    raise ValueError("文字起こし結果が空です")

                result_length = len(response.strip())
                self.logger.info(f"文字起こし完了: {result_length}文字")

                return response.strip()

        except Exception as e:
            self.logger.error(
                f"文字起こしエラー: {audio_file_path} - {str(e)}", exc_info=True
            )
            raise RuntimeError(f"文字起こし中にエラーが発生しました: {str(e)}")

    async def _transcribe_chunked_audio(self, chunks_dir: str) -> str:
        """分割された音声ファイルを順次処理して結合"""

        self.logger.info(f"分割音声ファイル処理開始: {chunks_dir}")

        # チャンクファイルを取得してソート
        chunk_files = []
        for filename in os.listdir(chunks_dir):
            if filename.endswith((".mp3", ".wav")) and filename.startswith("chunk_"):
                chunk_files.append(os.path.join(chunks_dir, filename))

        chunk_files.sort()  # ファイル名順にソート

        if not chunk_files:
            self.logger.error(f"チャンクファイルが見つかりません: {chunks_dir}")
            raise FileNotFoundError("処理する音声チャンクが見つかりません")

        self.logger.info(f"チャンクファイル数: {len(chunk_files)}")

        try:
            # 各チャンクを順次処理
            transcriptions = []

            for i, chunk_file in enumerate(chunk_files):
                self.logger.info(
                    f"チャンク {i+1}/{len(chunk_files)} 処理中: {os.path.basename(chunk_file)}"
                )

                chunk_transcript = await self._transcribe_single_file(chunk_file)
                if chunk_transcript.strip():
                    transcriptions.append(chunk_transcript.strip())

                self.logger.debug(f"チャンク {i+1} 完了: {len(chunk_transcript)}文字")

            # 結果を結合
            full_transcript = " ".join(transcriptions)

            # 一時ディレクトリを削除
            import shutil

            shutil.rmtree(chunks_dir)
            self.logger.info(f"一時ディレクトリを削除: {chunks_dir}")

            total_length = len(full_transcript)
            self.logger.info(
                f"分割音声文字起こし完了: 総文字数={total_length}, チャンク数={len(chunk_files)}"
            )

            return full_transcript

        except Exception as e:
            # エラー時も一時ディレクトリを削除
            import shutil

            if os.path.exists(chunks_dir):
                shutil.rmtree(chunks_dir)
                self.logger.warning(f"エラー時に一時ディレクトリを削除: {chunks_dir}")

            self.logger.error(
                f"分割音声処理エラー: {chunks_dir} - {str(e)}", exc_info=True
            )
            raise RuntimeError(
                f"分割音声の文字起こし中にエラーが発生しました: {str(e)}"
            )

    async def transcribe_with_timestamps(self, audio_file_path: str) -> dict:
        """タイムスタンプ付きで文字起こし"""

        try:
            async with aiofiles.open(audio_file_path, "rb") as audio_file:
                audio_data = await audio_file.read()

                response = await self.client.audio.transcriptions.create(
                    model=settings.whisper_model,
                    file=("audio.wav", audio_data, "audio/wav"),
                    language=settings.whisper_language,
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                )

                return response

        except Exception as e:
            raise RuntimeError(
                f"タイムスタンプ付き文字起こし中にエラーが発生しました: {str(e)}"
            )

    def format_transcription_with_paragraphs(self, text: str) -> str:
        """文字起こしテキストを段落に整形"""

        # 簡単な段落分けルール
        sentences = text.split("。")
        paragraphs = []
        current_paragraph = []

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                current_paragraph.append(sentence + "。")

                # 3文ごとに段落を区切る
                if len(current_paragraph) >= 3:
                    paragraphs.append("".join(current_paragraph))
                    current_paragraph = []

        # 残りの文があれば追加
        if current_paragraph:
            paragraphs.append("".join(current_paragraph))

        return "\n\n".join(paragraphs)
