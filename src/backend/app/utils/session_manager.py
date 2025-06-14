"""セッション管理ユーティリティ"""
import uuid
from typing import Optional
from fastapi import Request

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """セッション管理クラス"""

    @staticmethod
    def get_session_id(request: Request) -> str:
        """
        リクエストからセッションIDを取得、存在しない場合は新規作成
        
        Args:
            request: FastAPIリクエストオブジェクト
            
        Returns:
            セッションID (UUID4文字列)
        """
        session_id = request.session.get("session_id")
        
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session["session_id"] = session_id
            logger.info(f"新しいセッションを作成: {session_id[:8]}...")
        else:
            logger.debug(f"既存のセッションを使用: {session_id[:8]}...")
            
        return session_id

    @staticmethod
    def get_user_info(request: Request) -> Optional[dict]:
        """
        セッションからユーザー情報を取得
        
        Args:
            request: FastAPIリクエストオブジェクト
            
        Returns:
            ユーザー情報辞書 (将来の拡張用)
        """
        return request.session.get("user_info")

    @staticmethod
    def set_user_info(request: Request, user_info: dict) -> None:
        """
        セッションにユーザー情報を設定
        
        Args:
            request: FastAPIリクエストオブジェクト
            user_info: ユーザー情報辞書
        """
        request.session["user_info"] = user_info
        session_id = SessionManager.get_session_id(request)
        logger.info(f"ユーザー情報を設定: {session_id[:8]}... - {user_info.get('username', 'unknown')}")

    @staticmethod
    def clear_session(request: Request) -> None:
        """
        セッションをクリア
        
        Args:
            request: FastAPIリクエストオブジェクト
        """
        session_id = request.session.get("session_id", "unknown")
        request.session.clear()
        logger.info(f"セッションをクリア: {session_id[:8] if session_id != 'unknown' else 'unknown'}...")