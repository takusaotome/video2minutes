#!/usr/bin/env python3
"""
認証機能テストスクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.auth.api_key import api_key_auth

def test_auth_config():
    """認証設定をテスト"""
    print("🔍 認証設定の確認")
    print("=" * 50)
    
    print(f"認証有効: {settings.auth_enabled}")
    print(f"APIキー設定: {bool(settings.api_keys)}")
    print(f"マスターAPIキー設定: {bool(settings.master_api_key)}")
    print(f"デバッグモード: {settings.debug}")
    
    if settings.api_keys:
        keys = settings.api_keys.split(',')
        print(f"設定されたAPIキー数: {len(keys)}")
        for i, key in enumerate(keys, 1):
            print(f"  APIキー{i}: {key[:8]}...")
    
    if settings.master_api_key:
        print(f"マスターAPIキー: {settings.master_api_key[:8]}...")
    
    print()

def test_api_key_validation():
    """APIキー検証をテスト"""
    print("🔑 APIキー検証テスト")
    print("=" * 50)
    
    # 有効なAPIキーの数を確認
    valid_keys = len(api_key_auth.valid_api_keys)
    print(f"有効なAPIキー数: {valid_keys}")
    
    if valid_keys == 0:
        print("⚠️  有効なAPIキーが設定されていません")
        return
    
    # テスト用のAPIキー
    test_key = "meH_Xo77M3DVI8bIHP5e6HRlhz_DtQyS83ECjKKchYc"
    
    # 検証テスト
    is_valid = api_key_auth.verify_api_key(test_key)
    print(f"テストAPIキー検証結果: {is_valid}")
    
    # 無効なキーのテスト
    invalid_key = "invalid_key_12345"
    is_invalid = api_key_auth.verify_api_key(invalid_key)
    print(f"無効なAPIキー検証結果: {is_invalid}")
    
    print()

def test_environment_variables():
    """環境変数をテスト"""
    print("🌍 環境変数の確認")
    print("=" * 50)
    
    env_vars = [
        "AUTH_ENABLED",
        "API_KEYS", 
        "MASTER_API_KEY",
        "SESSION_SECRET_KEY",
        "DEBUG"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if "KEY" in var:
                print(f"{var}: {value[:8]}..." if len(value) > 8 else f"{var}: {value}")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: 未設定")
    
    print()

def main():
    """メイン関数"""
    print("🔒 Video2Minutes 認証機能テスト")
    print("=" * 60)
    print()
    
    test_environment_variables()
    test_auth_config()
    test_api_key_validation()
    
    # 推奨事項
    print("📝 推奨事項")
    print("=" * 50)
    
    if not settings.auth_enabled:
        print("⚠️  認証機能が無効です。本番環境では有効にしてください。")
    
    if not settings.api_keys and not settings.master_api_key:
        print("⚠️  APIキーが設定されていません。")
        print("   以下のコマンドでAPIキーを生成してください:")
        print("   python scripts/generate_api_key.py")
    
    if settings.session_secret_key == "your-secret-key-change-in-production":
        print("⚠️  セッション秘密鍵がデフォルト値です。")
        print("   本番環境では必ず変更してください。")
    
    if settings.debug:
        print("⚠️  デバッグモードが有効です。本番環境では無効にしてください。")

if __name__ == "__main__":
    main() 