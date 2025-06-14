import asyncio
import os
from typing import Optional

import ffmpeg
from fractions import Fraction

from app.config import settings
from app.utils.file_handler import FileHandler
from app.utils.logger import LoggerMixin


class VideoProcessor(LoggerMixin):
    """動画処理サービス"""

    async def extract_audio(self, task_id: str) -> str:
        """動画から音声を抽出（MP3形式、ファイルサイズ制限対応）"""

        self.logger.info(f"音声抽出開始: {task_id}")

        # 入力ファイルパスを取得
        video_path = FileHandler.get_file_path(task_id)
        if not video_path:
            self.logger.error(f"動画ファイルが見つかりません: {task_id}")
            raise FileNotFoundError(f"タスク {task_id} の動画ファイルが見つかりません")

        # 出力音声ファイルパス（MP3形式）
        audio_path = FileHandler.get_audio_path(
            task_id).replace(".wav", ".mp3")

        self.logger.info(f"ffmpeg音声抽出: {video_path} -> {audio_path}")

        try:
            # 動画情報を取得して適切なビットレートを決定
            video_info = self.get_video_info(video_path)
            duration = video_info.get("duration", 0)

            # ファイルサイズ制限（20MB）に基づいてビットレートを計算
            target_file_size_mb = settings.audio_max_file_size_mb  # 設定から取得
            max_bitrate = self._calculate_max_bitrate(
                duration, target_file_size_mb)
            bitrate = min(max_bitrate, settings.audio_bitrate_max)  # 設定から取得

            self.logger.info(
                f"動画時間: {duration:.1f}秒, 使用ビットレート: {bitrate}kbps"
            )

            # ffmpegでMP3音声抽出を実行
            await self._run_ffmpeg_extract_mp3(video_path, audio_path, bitrate)

            if not os.path.exists(audio_path):
                self.logger.error(f"音声ファイルの生成に失敗: {audio_path}")
                raise RuntimeError("音声ファイルの生成に失敗しました")

            # ファイルサイズをチェック
            file_size = os.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)

            self.logger.info(
                f"音声抽出完了: {task_id} - {audio_path} ({file_size_mb:.2f}MB)"
            )

            # ファイルサイズが25MBを超える場合は分割処理を実行
            if file_size > 25 * 1024 * 1024:
                self.logger.warning(
                    f"ファイルサイズが制限を超過 ({file_size_mb:.2f}MB) - 分割処理を実行"
                )
                return await self._split_audio_file(audio_path, task_id)

            return audio_path

        except Exception as e:
            # エラー時は生成されたファイルを削除
            if os.path.exists(audio_path):
                os.remove(audio_path)
                self.logger.warning(f"エラー時にファイル削除: {audio_path}")

            self.logger.error(f"音声抽出エラー: {task_id} - {str(e)}", exc_info=True)
            raise RuntimeError(f"音声抽出中にエラーが発生しました: {str(e)}")

    async def _run_ffmpeg_extract(self, input_path: str, output_path: str) -> None:
        """ffmpegで音声抽出を実行（非同期）"""

        # ffmpegコマンドを構築
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream,
            output_path,
            acodec="pcm_s16le",  # WAV形式
            ac=1,  # モノラル
            ar="16000",  # サンプリングレート 16kHz（Whisper推奨）
            y=None,  # 既存ファイルを上書き
        )

        # コマンドを非同期実行
        cmd = ffmpeg.compile(stream)

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "不明なエラー"
            self.logger.error(f"ffmpegコマンド実行エラー: {error_msg}")
            raise RuntimeError(f"ffmpegエラー: {error_msg}")

        self.logger.debug(f"ffmpegコマンド実行成功: {input_path} -> {output_path}")

    async def _run_ffmpeg_extract_mp3(
        self, input_path: str, output_path: str, bitrate: int
    ) -> None:
        """ffmpegでMP3音声抽出を実行（非同期）"""

        # ffmpegコマンドを構築（MP3形式）
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream,
            output_path,
            acodec="libmp3lame",  # MP3エンコーダー
            ac=1,  # モノラル
            ar="16000",  # サンプリングレート 16kHz（Whisper推奨）
            audio_bitrate=f"{bitrate}k",  # ビットレート
            y=None,  # 既存ファイルを上書き
        )

        # コマンドを非同期実行
        cmd = ffmpeg.compile(stream)

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "不明なエラー"
            self.logger.error(f"ffmpeg MP3変換エラー: {error_msg}")
            raise RuntimeError(f"ffmpeg MP3変換エラー: {error_msg}")

        self.logger.debug(f"ffmpeg MP3変換成功: {input_path} -> {output_path}")

    def _calculate_max_bitrate(
        self, duration_seconds: float, target_size_mb: float
    ) -> int:
        """目標ファイルサイズから最大ビットレートを計算"""
        if duration_seconds <= 0:
            return 32  # デフォルト値

        # ビットレート計算: (ファイルサイズMB * 8 * 1024) / 時間秒 = kbps
        max_bitrate = (target_size_mb * 8 * 1024) / duration_seconds
        return max(int(max_bitrate), 16)  # 最低16kbps

    async def _split_audio_file(self, audio_path: str, task_id: str) -> str:
        """音声ファイルを分割してマージしたファイルパスを返す"""

        self.logger.info(f"音声ファイル分割開始: {audio_path}")

        # 分割チャンク用のディレクトリを作成
        import tempfile

        chunks_dir = tempfile.mkdtemp(prefix=f"audio_chunks_{task_id}_")

        try:
            # 音声の総時間を取得
            probe = ffmpeg.probe(audio_path)
            duration = float(probe["format"]["duration"])

            # 設定されたファイルサイズに収まる時間を計算（安全マージン込み）
            file_size = os.path.getsize(audio_path)
            target_chunk_size = (
                (settings.audio_max_file_size_mb - 2) * 1024 * 1024
            )  # 2MB安全マージン
            chunk_duration = (duration * target_chunk_size) / file_size
            chunk_duration = min(
                chunk_duration, settings.audio_chunk_duration_max
            )  # 設定から最大時間を取得

            self.logger.info(
                f"分割設定: 総時間={duration:.1f}秒, チャンク時間={chunk_duration:.1f}秒"
            )

            # ファイルを分割
            chunk_files = []
            start_time = 0
            chunk_index = 0

            while start_time < duration:
                chunk_path = os.path.join(
                    chunks_dir, f"chunk_{chunk_index:03d}.mp3")

                # 分割コマンドを実行
                await self._split_audio_chunk(
                    audio_path, chunk_path, start_time, chunk_duration
                )

                if os.path.exists(chunk_path):
                    chunk_files.append(chunk_path)
                    self.logger.debug(f"チャンク作成: {chunk_path}")

                start_time += chunk_duration
                chunk_index += 1

            self.logger.info(f"分割完了: {len(chunk_files)}個のチャンクを作成")

            # 元のファイルを分割済みファイルのリストに置き換え
            # TranscriptionServiceが複数ファイルを処理できるように戻り値を調整
            return chunks_dir  # ディレクトリパスを返す

        except Exception as e:
            # エラー時は作成したファイルを削除
            import shutil

            if os.path.exists(chunks_dir):
                shutil.rmtree(chunks_dir)
            raise e

    async def _split_audio_chunk(
        self, input_path: str, output_path: str, start_time: float, duration: float
    ) -> None:
        """音声の一部を抽出"""

        stream = ffmpeg.input(input_path, ss=start_time, t=duration)
        stream = ffmpeg.output(stream, output_path, acodec="copy")

        cmd = ffmpeg.compile(stream)

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "不明なエラー"
            self.logger.error(f"音声分割エラー: {error_msg}")
            raise RuntimeError(f"音声分割エラー: {error_msg}")

    def get_video_info(self, video_path: str) -> dict:
        """動画の情報を取得"""
        try:
            probe = ffmpeg.probe(video_path)
            video_info = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "video"
                ),
                None,
            )
            audio_info = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "audio"
                ),
                None,
            )

            return {
                "duration": float(probe["format"]["duration"]),
                "size": int(probe["format"]["size"]),
                "video": {
                    "codec": video_info["codec_name"] if video_info else None,
                    "width": int(video_info["width"]) if video_info else None,
                    "height": int(video_info["height"]) if video_info else None,
                    "fps": float(Fraction(video_info["r_frame_rate"])) if video_info else None,
                },
                "audio": {
                    "codec": audio_info["codec_name"] if audio_info else None,
                    "sample_rate": (
                        int(audio_info["sample_rate"]) if audio_info else None
                    ),
                    "channels": int(audio_info["channels"]) if audio_info else None,
                },
            }
        except Exception as e:
            raise RuntimeError(f"動画情報の取得に失敗しました: {str(e)}")
