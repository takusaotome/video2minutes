import asyncio
import os

import ffmpeg
from fractions import Fraction

from app.config import settings
from app.utils.file_handler import FileHandler
from app.utils.logger import LoggerMixin


class VideoProcessor(LoggerMixin):
    """動画処理サービス"""

    async def process_audio_file(self, task_id: str) -> str:
        """音声ファイル（動画・M4A）から音声を抽出・処理"""
        
        self.logger.info(f"音声ファイル処理開始: {task_id}")
        
        # ファイルタイプを確認
        file_path = FileHandler.get_file_path(task_id)
        if not file_path:
            self.logger.error(f"ファイルが見つかりません: {task_id}")
            raise FileNotFoundError(f"タスク {task_id} のファイルが見つかりません")
        
        file_type = FileHandler.get_file_type(task_id)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        self.logger.info(f"ファイルタイプ: {file_type}, 拡張子: {file_ext}, パス: {file_path}")
        
        # M4Aファイルの場合は専用処理
        if file_ext == ".m4a":
            return await self._process_m4a_file(task_id, file_path)
        
        # その他の音声・動画ファイルは既存の処理
        return await self.extract_audio(task_id)

    async def _process_m4a_file(self, task_id: str, m4a_path: str) -> str:
        """M4Aファイル専用処理 - 大きなM4AファイルをコンパクトなMP3に変換"""
        
        self.logger.info(f"M4A処理開始: {task_id} - {m4a_path}")
        
        try:
            # M4Aファイルの情報を取得
            audio_info = await self._get_m4a_audio_info(m4a_path)
            self.logger.info(
                f"M4A情報: 時間={audio_info['duration']:.1f}秒, "
                f"サイズ={audio_info['size_mb']:.2f}MB, "
                f"コーデック={audio_info['codec']}"
            )
            
            # ファイルサイズチェック
            if audio_info['size_mb'] > settings.m4a_max_input_size_mb:
                raise RuntimeError(
                    f"M4Aファイルサイズが上限({settings.m4a_max_input_size_mb}MB)を超えています: {audio_info['size_mb']:.2f}MB"
                )
            
            # 出力音声ファイルパス（MP3形式）
            audio_path = FileHandler.get_audio_path(task_id).replace(".wav", ".mp3")
            
            # M4A圧縮が無効の場合、または小さなファイルの場合は通常の変換
            if (not settings.m4a_compression_enabled or 
                audio_info['size_mb'] <= settings.m4a_target_file_size_mb):
                self.logger.info("M4A圧縮をスキップし、通常変換を実行")
                await self._run_ffmpeg_m4a_to_mp3_simple(m4a_path, audio_path)
                return audio_path
            
            # 最適なビットレートを計算
            optimal_bitrate = self._calculate_m4a_optimal_bitrate(
                audio_info['duration'], 
                settings.m4a_target_file_size_mb
            )
            
            self.logger.info(f"M4A最適ビットレート: {optimal_bitrate}kbps")
            
            # M4AからMP3への変換を実行
            await self._run_ffmpeg_m4a_to_mp3_optimized(
                m4a_path, audio_path, optimal_bitrate
            )
            
            if not os.path.exists(audio_path):
                self.logger.error(f"M4A変換後のファイルが見つかりません: {audio_path}")
                raise RuntimeError("M4A音声変換に失敗しました")
            
            # 変換後のファイルサイズをチェック
            output_size = os.path.getsize(audio_path)
            output_size_mb = output_size / (1024 * 1024)
            compression_ratio = (1 - output_size_mb / audio_info['size_mb']) * 100
            
            self.logger.info(
                f"M4A変換完了: {task_id} - {audio_path} "
                f"({output_size_mb:.2f}MB, 圧縮率: {compression_ratio:.1f}%)"
            )
            
            # Whisper API制限チェック（25MB）
            if output_size > 25 * 1024 * 1024:
                self.logger.warning(
                    f"変換後のファイルサイズが制限を超過 ({output_size_mb:.2f}MB) - 分割処理を実行"
                )
                return await self._split_audio_file(audio_path, task_id)
            
            return audio_path
            
        except Exception as e:
            self.logger.error(f"M4A処理エラー: {task_id} - {str(e)}", exc_info=True)
            # エラー時は生成されたファイルを削除
            audio_path = FileHandler.get_audio_path(task_id).replace(".wav", ".mp3")
            if os.path.exists(audio_path):
                os.remove(audio_path)
                self.logger.warning(f"エラー時にファイル削除: {audio_path}")
            raise RuntimeError(f"M4A処理中にエラーが発生しました: {str(e)}")

    async def _get_m4a_audio_info(self, audio_path: str) -> dict:
        """M4A音声ファイルの情報を取得"""
        try:
            probe = ffmpeg.probe(audio_path)
            audio_info = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "audio"
                ),
                None,
            )
            
            duration = float(probe["format"]["duration"])
            size = int(probe["format"]["size"])
            
            return {
                "duration": duration,
                "size": size,
                "size_mb": size / (1024 * 1024),
                "codec": audio_info["codec_name"] if audio_info else None,
                "sample_rate": int(audio_info["sample_rate"]) if audio_info else None,
                "channels": int(audio_info["channels"]) if audio_info else None,
                "bitrate": int(audio_info.get("bit_rate", 0)) if audio_info else None,
            }
        except Exception as e:
            raise RuntimeError(f"M4A音声情報の取得に失敗しました: {str(e)}")

    def _calculate_m4a_optimal_bitrate(self, duration_seconds: float, target_size_mb: float) -> int:
        """M4A変換時の最適なビットレートを計算"""
        if duration_seconds <= 0:
            return settings.m4a_min_bitrate
        
        # ビットレート計算: (ファイルサイズMB * 8 * 1024) / 時間秒 = kbps
        calculated_bitrate = (target_size_mb * 8 * 1024) / duration_seconds
        
        # 最小・最大値でクランプ
        final_bitrate = max(
            min(int(calculated_bitrate), settings.m4a_max_bitrate), 
            settings.m4a_min_bitrate
        )
        
        # 予想ファイルサイズを計算
        estimated_size_mb = (final_bitrate * duration_seconds) / (8 * 1024)
        
        self.logger.info(
            f"M4Aビットレート計算: "
            f"計算値={calculated_bitrate:.1f}kbps, "
            f"最終値={final_bitrate}kbps, "
            f"予想サイズ={estimated_size_mb:.2f}MB"
        )
        
        # 目標サイズを超える場合の警告
        if estimated_size_mb > target_size_mb * 1.1:  # 10%の余裕を持たせる
            self.logger.warning(
                f"M4A予想サイズ({estimated_size_mb:.2f}MB)が目標サイズ({target_size_mb}MB)を超過。"
                f"目標達成には{calculated_bitrate:.1f}kbpsが必要"
            )
        
        return final_bitrate

    async def _run_ffmpeg_m4a_to_mp3_simple(self, input_path: str, output_path: str) -> None:
        """M4AからMP3への通常変換（圧縮なし）"""
        
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream,
            output_path,
            acodec="libmp3lame",  # MP3エンコーダー
            ac=1,  # モノラル
            ar=str(settings.m4a_sample_rate),  # サンプリングレート
            y=None,  # 既存ファイルを上書き
        )
        
        cmd = ffmpeg.compile(stream)
        
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "不明なエラー"
            self.logger.error(f"M4A通常変換エラー: {error_msg}")
            raise RuntimeError(f"M4A通常変換エラー: {error_msg}")
        
        self.logger.debug(f"M4A通常変換成功: {input_path} -> {output_path}")

    async def _run_ffmpeg_m4a_to_mp3_optimized(
        self, input_path: str, output_path: str, bitrate: int
    ) -> None:
        """M4AからMP3への最適化変換（圧縮あり）"""
        
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream,
            output_path,
            acodec="libmp3lame",  # MP3エンコーダー
            ac=1,  # モノラル
            ar=str(settings.m4a_sample_rate),  # サンプリングレート
            audio_bitrate=f"{bitrate}k",  # ビットレート
            y=None,  # 既存ファイルを上書き
        )
        
        cmd = ffmpeg.compile(stream)
        
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "不明なエラー"
            self.logger.error(f"M4A最適化変換エラー: {error_msg}")
            raise RuntimeError(f"M4A最適化変換エラー: {error_msg}")
        
        self.logger.debug(f"M4A最適化変換成功: {input_path} -> {output_path} (ビットレート: {bitrate}kbps)")

    async def extract_audio(self, task_id: str) -> str:
        """動画から音声を抽出（MP3形式、ファイルサイズ制限対応）"""

        self.logger.info(f"音声抽出開始: {task_id}")

        # 入力ファイルパスを取得
        video_path = FileHandler.get_file_path(task_id)
        if not video_path:
            self.logger.error(f"動画ファイルが見つかりません: {task_id}")
            raise FileNotFoundError(f"タスク {task_id} の動画ファイルが見つかりません")

        # 出力音声ファイルパス（MP3形式）
        audio_path = FileHandler.get_audio_path(task_id).replace(".wav", ".mp3")

        self.logger.info(f"ffmpeg音声抽出: {video_path} -> {audio_path}")

        try:
            # 動画情報を取得して適切なビットレートを決定
            video_info = self.get_video_info(video_path)
            duration = video_info.get("duration", 0)

            # ファイルサイズ制限（20MB）に基づいてビットレートを計算
            target_file_size_mb = settings.audio_max_file_size_mb  # 設定から取得
            max_bitrate = self._calculate_max_bitrate(duration, target_file_size_mb)
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
                chunk_path = os.path.join(chunks_dir, f"chunk_{chunk_index:03d}.mp3")

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
                    "fps": (
                        float(Fraction(video_info["r_frame_rate"]))
                        if video_info
                        else None
                    ),
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
