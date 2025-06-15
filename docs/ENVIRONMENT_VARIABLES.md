# 環境変数一覧

バックエンド(`src/backend/env.example`)とフロントエンド(`src/frontend/env.example`)で利用する主な環境変数をまとめます。

## バックエンド

| 変数名 | 用途 | 必須/任意 | 例 |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI APIキー | 必須 | `your_openai_api_key_here` |
| `AUTH_ENABLED` | API認証の有効化 | 任意 | `true` |
| `API_KEYS` | 許可するAPIキー(カンマ区切り) | 任意※ | `your_api_key_1,your_api_key_2` |
| `MASTER_API_KEY` | 開発用マスターキー | 任意 | `your_master_api_key_for_development` |
| `SESSION_SECRET_KEY` | セッション署名鍵 | 必須 | `your_very_secure_session_secret_key_change_in_production` |
| `HOST` | サーバーホスト | 任意 | `0.0.0.0` |
| `PORT` | サーバーポート | 任意 | `8000` |
| `DEBUG` | デバッグモード | 任意 | `false` |
| `CORS_ORIGINS` | 許可するCORSオリジン | 任意 | `["https://yourdomain.com","https://www.yourdomain.com"]` |
| `LOG_LEVEL` | ログレベル | 任意 | `INFO` |
| `LOG_DIR` | ログ保存ディレクトリ | 任意 | `logs` |
| `TIMEZONE` | タイムゾーン | 任意 | `Asia/Tokyo` |

※ `AUTH_ENABLED` が `true` の場合は `API_KEYS` が必須です。

## フロントエンド

| 変数名 | 用途 | 必須/任意 | 例 |
| --- | --- | --- | --- |
| `VITE_API_URL` | バックエンドAPIのURL | 任意 | `https://video2minutes-api.onrender.com` |
| `VITE_API_KEY` | APIアクセスキー | 任意 | `your_api_key_here` |

`.env` ファイルを作成する際は、上記を参考に値を設定してください。
