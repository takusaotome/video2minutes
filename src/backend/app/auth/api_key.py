"""
APIキー認証機能
"""
import hashlib
import secrets
from typing import Optional

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.utils.logger import setup_logging

logger = setup_logging()

# HTTPBearer認証スキーム（OPTIONSリクエストでは自動認証しない）
security = HTTPBearer(auto_error=False)

class APIKeyAuth:
    """APIキー認証クラス"""
    
    def __init__(self):
        self.valid_api_keys = self._load_api_keys()
    
    def _load_api_keys(self) -> set:
        """有効なAPIキーを読み込み"""
        api_keys = set()
        
        # 環境変数からAPIキーを読み込み
        if settings.api_keys:
            for key in settings.api_keys.split(','):
                key = key.strip()
                if key:
                    # APIキーをハッシュ化して保存（セキュリティ向上）
                    hashed_key = hashlib.sha256(key.encode()).hexdigest()
                    api_keys.add(hashed_key)
        
        # デフォルトのマスターキー（開発用）
        if settings.debug and settings.master_api_key:
            hashed_master = hashlib.sha256(settings.master_api_key.encode()).hexdigest()
            api_keys.add(hashed_master)
        
        return api_keys
    
    def _hash_api_key(self, api_key: str) -> str:
        """APIキーをハッシュ化"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str) -> bool:
        """APIキーを検証"""
        if not api_key:
            return False
        
        hashed_key = self._hash_api_key(api_key)
        return hashed_key in self.valid_api_keys
    
    def generate_api_key(self) -> str:
        """新しいAPIキーを生成"""
        return secrets.token_urlsafe(32)

# グローバルインスタンス
api_key_auth = APIKeyAuth()

async def get_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> str:
    """
    APIキー認証依存関数
    
    Args:
        credentials: HTTP Bearer認証情報
        
    Returns:
        str: 検証済みAPIキー
        
    Raises:
        HTTPException: 認証失敗時
    """
    if not credentials:
        logger.warning("認証情報が提供されていません")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    
    if not api_key_auth.verify_api_key(api_key):
        logger.warning(f"無効なAPIキーでのアクセス試行: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なAPIキーです",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"APIキー認証成功: {api_key[:8]}...")
    return api_key

# オプショナル認証（一部のエンドポイント用）
async def get_optional_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    """
    オプショナルAPIキー認証
    
    Args:
        credentials: HTTP Bearer認証情報（オプション）
        
    Returns:
        Optional[str]: 検証済みAPIキー（認証情報がない場合はNone）
    """
    if not credentials:
        return None
    
    try:
        return await get_api_key(credentials)
    except HTTPException:
        return None 