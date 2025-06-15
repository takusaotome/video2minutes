#!/usr/bin/env python3
"""
APIキー生成スクリプト
"""
import secrets
import hashlib
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.auth.api_key import APIKeyAuth

def generate_api_key() -> str:
    """新しいAPIキーを生成"""
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """APIキーをハッシュ化"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def main():
    """メイン関数"""
    print("🔑 Video2Minutes APIキー生成ツール")
    print("=" * 50)
    
    # 新しいAPIキーを生成
    api_key = generate_api_key()
    hashed_key = hash_api_key(api_key)
    
    print(f"✅ 新しいAPIキーを生成しました:")
    print(f"   APIキー: {api_key}")
    print(f"   ハッシュ: {hashed_key}")
    print()
    
    print("📝 使用方法:")
    print("1. 環境変数に設定:")
    print(f"   export API_KEYS=\"{api_key}\"")
    print("   または")
    print(f"   export MASTER_API_KEY=\"{api_key}\"")
    print()
    
    print("2. .envファイルに追加:")
    print(f"   API_KEYS={api_key}")
    print("   または")
    print(f"   MASTER_API_KEY={api_key}")
    print()
    
    print("3. HTTPリクエストで使用:")
    print("   curl -H \"Authorization: Bearer " + api_key + "\" \\")
    print("        https://video2minutes-api.onrender.com/api/v1/minutes/tasks")
    print()
    
    print("⚠️  セキュリティ注意事項:")
    print("   - APIキーは安全な場所に保管してください")
    print("   - 定期的にAPIキーをローテーションしてください")
    print("   - 本番環境では複数のAPIキーを使用することを推奨します")

if __name__ == "__main__":
    main() 