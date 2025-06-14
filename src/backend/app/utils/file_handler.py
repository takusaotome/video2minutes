import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import HTTPException, UploadFile

from app.config import settings
from app.utils.logger import get_logger


class FileHandler:
    """ファイル処理ユーティリティ"""

    logger = get_logger(__name__)

    @staticmethod
    def generate_task_id() -> str:
        """タスクIDを生成"""
        task_id = str(uuid.uuid4())
        logger = get_logger(__name__)
        logger.debug(f"タスクID生成: {task_id}")
        return task_id

    @staticmethod
    def validate_media_file(file: UploadFile) -> str:
        """動画・音声ファイルのバリデーション"""
        logger = get_logger(__name__)
        logger.debug(f"ファイルバリデーション開始: {file.filename}")

        if not file.filename:
            logger.warning("ファイル名が指定されていません")
            raise HTTPException(
                status_code=400, detail="ファイル名が指定されていません"
            )

        # ファイル拡張子チェック
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = settings.allowed_video_extensions + settings.allowed_audio_extensions
        
        if file_ext not in allowed_extensions:
            logger.warning(
                f"サポートされていないファイル形式: {file_ext} - {file.filename}"
            )
            video_exts = ', '.join(settings.allowed_video_extensions)
            audio_exts = ', '.join(settings.allowed_audio_extensions)
            raise HTTPException(
                status_code=400,
                detail=f"サポートされていないファイル形式です。\n対応動画形式: {video_exts}\n対応音声形式: {audio_exts}",
            )
        
        # ファイルサイズチェック（ここではContent-Lengthヘッダーをチェック）
        if hasattr(file, "size") and file.size and file.size > settings.max_file_size:
            file_size_gb = file.size / (1024 * 1024 * 1024)
            max_size_gb = settings.max_file_size / (1024 * 1024 * 1024)
            logger.warning(
                f"ファイルサイズ超過: {file.filename} ({file_size_gb:.2f}GB > {max_size_gb:.1f}GB)"
            )
            raise HTTPException(
                status_code=413,
                detail=f"ファイルサイズが上限（{max_size_gb:.1f}GB）を超えています。現在のファイルサイズ: {file_size_gb:.2f}GB",
            )
        
        # ファイルタイプを判定して返す
        if file_ext in settings.allowed_video_extensions:
            return "video"
        else:
            return "audio"

    @staticmethod
    async def save_uploaded_file(file: UploadFile, task_id: str) -> tuple[str, int]:
        """アップロードされたファイルを保存"""
        # アップロードディレクトリが存在することを確認
        os.makedirs(settings.upload_dir, exist_ok=True)

        # ファイルパスを生成
        file_ext = Path(file.filename).suffix.lower()
        saved_filename = f"{task_id}{file_ext}"
        file_path = os.path.join(settings.upload_dir, saved_filename)

        # ファイルを保存
        file_size = 0
        try:
            async with aiofiles.open(file_path, "wb") as f:
                while chunk := await file.read(
                    settings.upload_chunk_size
                ):  # 設定可能なチャンクサイズ
                    file_size += len(chunk)
                    await f.write(chunk)

                    # ファイルサイズチェック
                    if file_size > settings.max_file_size:
                        # ファイルを削除
                        await f.close()
                        os.remove(file_path)
                        file_size_gb = file_size / (1024 * 1024 * 1024)
                        max_size_gb = settings.max_file_size / \
                            (1024 * 1024 * 1024)
                        FileHandler.logger.warning(
                            f"アップロード中にファイルサイズ超過: {file.filename} ({file_size_gb:.2f}GB > {max_size_gb:.1f}GB)"
                        )
                        raise HTTPException(
                            status_code=413,
                            detail=f"ファイルサイズが上限（{max_size_gb:.1f}GB）を超えています。アップロードされたサイズ: {file_size_gb:.2f}GB",
                        )

            return file_path, file_size

        except Exception as e:
            # エラー時はファイルを削除
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

    @staticmethod
    def cleanup_files(task_id: str) -> None:
        """タスクに関連するファイルを削除"""
        # アップロードファイル（動画・音声両方）
        all_extensions = settings.allowed_video_extensions + settings.allowed_audio_extensions
        for ext in all_extensions:
            upload_path = os.path.join(settings.upload_dir, f"{task_id}{ext}")
            if os.path.exists(upload_path):
                os.remove(upload_path)

        # 一時ファイル（WAVとMP3両方）
        temp_audio_wav = os.path.join(settings.temp_dir, f"{task_id}.wav")
        temp_audio_mp3 = os.path.join(settings.temp_dir, f"{task_id}.mp3")

        if os.path.exists(temp_audio_wav):
            os.remove(temp_audio_wav)
        if os.path.exists(temp_audio_mp3):
            os.remove(temp_audio_mp3)

    @staticmethod
    def get_file_path(task_id: str) -> Optional[str]:
        """タスクIDからファイルパスを取得"""
        all_extensions = settings.allowed_video_extensions + settings.allowed_audio_extensions
        for ext in all_extensions:
            file_path = os.path.join(settings.upload_dir, f"{task_id}{ext}")
            if os.path.exists(file_path):
                return file_path
        return None

    @staticmethod
    def get_file_type(task_id: str) -> Optional[str]:
        """タスクIDからファイルタイプを取得"""
        file_path = FileHandler.get_file_path(task_id)
        if not file_path:
            return None
        
        file_ext = Path(file_path).suffix.lower()
        if file_ext in settings.allowed_video_extensions:
            return "video"
        elif file_ext in settings.allowed_audio_extensions:
            return "audio"
        return None

    @staticmethod
    def get_audio_path(task_id: str) -> str:
        """音声ファイルパス（MP3）を取得"""
        # 一時ディレクトリが存在することを確認
        os.makedirs(settings.temp_dir, exist_ok=True)
        return os.path.join(settings.temp_dir, f"{task_id}.mp3")
