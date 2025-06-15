# 🔒 Video2Minutes セキュリティガイド

## 概要

Video2Minutes APIのセキュリティ機能と設定方法について説明します。

## 🔑 APIキー認証

### 1. 認証の有効化

環境変数で認証機能を有効にします：

```bash
export AUTH_ENABLED=true
```

### 2. APIキーの生成

APIキー生成スクリプトを使用：

```bash
cd src/backend
python scripts/generate_api_key.py
```

### 3. APIキーの設定

#### 環境変数での設定

```bash
# 単一のAPIキー
export API_KEYS="your_generated_api_key_here"

# 複数のAPIキー（カンマ区切り）
export API_KEYS="key1,key2,key3"

# 開発用マスターキー
export MASTER_API_KEY="your_master_key_for_development"
```

#### .envファイルでの設定

```env
AUTH_ENABLED=true
API_KEYS=your_api_key_1,your_api_key_2
MASTER_API_KEY=your_master_key_for_development
```

### 4. APIの使用方法

#### cURLでの例

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -X POST \
     -F "file=@video.mp4" \
     https://video2minutes-api.onrender.com/api/v1/minutes/upload
```

#### JavaScriptでの例

```javascript
const response = await fetch('https://video2minutes-api.onrender.com/api/v1/minutes/tasks', {
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  }
});
```

## 🛡️ セキュリティ設定

### 1. セッション設定

```env
SESSION_SECRET_KEY=your_very_secure_session_secret_key_change_in_production
SESSION_MAX_AGE=86400  # 24時間
```

### 2. CORS設定

本番環境では特定のドメインのみ許可：

```env
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]
```

### 3. HTTPS設定

本番環境では必ずHTTPSを使用：

```env
DEBUG=false  # HTTPSを強制
```

## 🚨 セキュリティベストプラクティス

### 1. APIキー管理

- ✅ APIキーは安全な場所に保管
- ✅ 定期的なAPIキーローテーション
- ✅ 複数のAPIキーを使用（用途別）
- ❌ APIキーをコードにハードコーディングしない
- ❌ APIキーをGitリポジトリにコミットしない

### 2. 環境設定

- ✅ 本番環境では`DEBUG=false`
- ✅ 強力なセッション秘密鍵を使用
- ✅ CORS設定を適切に制限
- ✅ ログレベルを適切に設定

### 3. ネットワークセキュリティ

- ✅ HTTPSを使用
- ✅ ファイアウォール設定
- ✅ レート制限の実装
- ✅ 不要なポートを閉じる

## 🔍 セキュリティ監査

### 1. ログ監視

認証失敗やアクセス試行をログで監視：

```bash
tail -f logs/video2minutes.log | grep "認証"
```

### 2. アクセス制御確認

```bash
# 認証なしでアクセス（失敗するはず）
curl https://video2minutes-api.onrender.com/api/v1/minutes/tasks

# 無効なAPIキーでアクセス（失敗するはず）
curl -H "Authorization: Bearer invalid_key" \
     https://video2minutes-api.onrender.com/api/v1/minutes/tasks
```

## 🆘 セキュリティインシデント対応

### 1. APIキー漏洩時の対応

1. 漏洩したAPIキーを無効化
2. 新しいAPIキーを生成
3. 全てのクライアントアプリケーションを更新
4. ログを確認して不正アクセスをチェック

### 2. 不正アクセス検知時の対応

1. 該当IPアドレスをブロック
2. ログを詳細に分析
3. 必要に応じてAPIキーをローテーション
4. セキュリティ設定を見直し

## 📞 サポート

セキュリティに関する質問や問題がある場合は、開発チームまでお問い合わせください。 