# Video2Minutes デプロイメント・セキュリティ設計

関連ドキュメントの一覧は[README](README.md)をご参照ください。

## 概要

Video2Minutesアプリケーションを特定のユーザーのみにアクセス制限するため、OAuth2-Proxyを使用したアクセス制御システムを実装する。

## アーキテクチャ

### システム構成図

```
Internet
    ↓
OAuth2-Proxy (Render Public Service)
https://video2minutes-auth.onrender.com
    ↓ (認証済みユーザーのみ転送)
Video2Minutes App (Render Private Service)
http://video2minutes-app-private.onrender.com
```

### コンポーネント

| コンポーネント | 役割 | デプロイ先 | アクセス |
|---|---|---|---|
| **OAuth2-Proxy** | 認証・認可プロキシ | Render Public Service | インターネットから直接アクセス可能 |
| **Video2Minutes** | メインアプリケーション | Render Private Service | OAuth2-Proxy経由のみアクセス可能 |
| **Google OAuth** | 認証プロバイダー | Google Cloud Platform | OAuth2-Proxyから利用 |

## セキュリティ設計

### 認証フロー

1. **未認証ユーザー**がOAuth2-ProxyのURLにアクセス
2. **Google OAuth認証**画面にリダイレクト
3. ユーザーがGoogleアカウントでログイン
4. **許可リスト**（メールアドレス/ドメイン）との照合
5. 認証成功時、**セッションCookie**を発行
6. 以降のリクエストは**Video2Minutesアプリ**に透過的に転送

### アクセス制御

#### 許可設定方式
- **ドメイン単位**: `@yourdomain.com` 全体を許可
- **個別メール**: 特定のメールアドレスのみ許可
- **組織単位**: GitHub Organization単位での許可（GitHub OAuth使用時）

#### 設定例
```ini
# ドメイン全体を許可
email_domains = ["yourdomain.com", "partnerdomain.com"]

# 個別メールアドレスを許可
authenticated_emails_file = "/app/emails.txt"
```

## 実装仕様

### OAuth2-Proxy設定

#### 必須環境変数
| 環境変数 | 値（例） | 補足 |
|---|---|---|
| `OAUTH2_PROXY_PROVIDER` | `google` | GitHub なら `github` |
| `OAUTH2_PROXY_CLIENT_ID` | Google で発行した ID | |
| `OAUTH2_PROXY_CLIENT_SECRET` | Google で発行した Secret | |
| `OAUTH2_PROXY_COOKIE_SECRET` | `openssl rand -hex 16` で生成 | 32 byte 推奨 |
| `OAUTH2_PROXY_EMAIL_DOMAINS` | `example.com` | ドメイン単位で許可 |
| `OAUTH2_PROXY_UPSTREAMS` | `http://myapp-internal:8000/` | Private Service の内部 URL |
| `OAUTH2_PROXY_HTTP_ADDRESS` | `0.0.0.0:3000` | Proxy が LISTEN するポート |

#### 個別メールアドレス許可
```bash
# ドメイン制限の代わりに個別メールアドレスを許可
OAUTH2_PROXY_ALLOWED_EMAILS=user1@example.com,user2@gmail.com,user3@anotherdomain.com
```

#### 追加オプション設定
```bash
# ユーザー情報をアプリに渡す（オプション）
OAUTH2_PROXY_EXTRA_ARGS=--pass-basic-auth=true --set-xauthrequest=true
```

#### セキュリティ設定
```ini
# Cookie設定
cookie_secure = true      # HTTPS必須
cookie_httponly = true    # XSS対策
cookie_samesite = "lax"   # CSRF対策

# セッション設定
session_cookie_minimal = true
upstreams = ["http://private-service-url"]
```

### Private Service設定

#### Video2Minutesアプリケーション
- **Service Type**: Private Service
- **Internal URL**: `http://app-name-private.onrender.com`
- **External Access**: 不可（OAuth2-Proxy経由のみ）

## Google Cloud Platform設定

### OAuth2.0クライアント設定

#### 必須設定項目
- **Application Type**: Web Application
- **Authorized JavaScript Origins**: 
  ```
  https://video2minutes-auth.onrender.com
  ```
- **Authorized Redirect URIs**:
  ```
  https://video2minutes-auth.onrender.com/oauth2/callback
  ```

### API有効化
- Google+ API
- Google Identity Service

## デプロイメント手順

### Step-0. 事前準備

| 項目 | 内容 |
|---|---|
| カスタムドメイン | まだ不要（`.onrender.com` ドメインでまず動かす方が楽） |
| Render アカウント | Free プランで検証可能（Private Service は Starter 以上推奨） |
| OpenSSL | Cookie 暗号化キー生成に使用（`openssl rand -hex 16`） |

### Step-1. Google Cloud で OAuth クライアントを作成

1. **Google Cloud Console → APIs & Services → Credentials**
2. "OAuth Client ID" → "Web application" を選択
3. Authorized *JavaScript origin* と *Redirect URI* を下記で設定
   - `https://<proxy-service-slug>.onrender.com`
   - `https://<proxy-service-slug>.onrender.com/oauth2/callback`
4. 生成された **Client ID / Client Secret** を控える

> **GitHub を使う場合**: GitHub Developer Settings で同様に App を作成し、Callback URL を `/oauth2/callback` にします。

### Step-2. アプリ本体を Private Service としてデプロイ

1. Render ダッシュボード → **New + → Private Service**
2. レポジトリを選択し、必要に応じて **Dockerfile** または Build コマンドを指定
3. ポート番号（例: `8000`）を設定
4. 任意で環境変数を設定して "Create Service"
   - ここで生成されるホスト名 `myapp-internal` は同じ Render アカウント内からのみ解決可能

### Step-3. OAuth2-Proxy を Web Service としてデプロイ

Render ブログの **"Deploy to Render"** ボタンか、`render-examples/oauth2-proxy` のフォークを使います。

**ワンクリックデプロイ**: [Render OAuth2-Proxy Template](https://render.com/deploy?repo=https://github.com/render-examples/oauth2-proxy)

作成時に必須環境変数を入力：

| 環境変数 | 値（例） | 補足 |
|---|---|---|
| `OAUTH2_PROXY_PROVIDER` | `google` | GitHub なら `github` |
| `OAUTH2_PROXY_CLIENT_ID` | Google で発行した ID | |
| `OAUTH2_PROXY_CLIENT_SECRET` | Google で発行した Secret | |
| `OAUTH2_PROXY_COOKIE_SECRET` | `openssl rand -hex 16` で生成 | 32 byte 推奨 |
| `OAUTH2_PROXY_EMAIL_DOMAINS` | `example.com` | ドメイン単位で許可 |
| `OAUTH2_PROXY_UPSTREAMS` | `http://myapp-internal:8000/` | Private Service の内部 URL |
| `OAUTH2_PROXY_HTTP_ADDRESS` | `0.0.0.0:3000` | Proxy が LISTEN するポート |

**作成後 1‒2 分でデプロイ完了** → `https://<proxy-service>.onrender.com` にアクセスすると Google ログイン画面が出れば成功。

### Step-4. （任意）ユーザ情報をアプリに渡す

- `--pass-basic-auth=true --set-xauthrequest=true` を `OAUTH2_PROXY_EXTRA_ARGS` に追加すると `X-Forwarded-User / X-Forwarded-Email` ヘッダが Private Service に渡る
- FastAPI なら `request.headers.get('X-Forwarded-Email')` で取得可能

### Step-5. 動作確認

1. OAuth2-ProxyのURLにアクセス
2. Google認証フローを確認
3. 許可されたユーザーでのアクセス確認
4. 未許可ユーザーのアクセス拒否確認

## 運用管理

### ユーザー管理

#### 新規ユーザー追加
1. `OAUTH2_PROXY_ALLOWED_EMAILS` 環境変数にメールアドレス追加
2. Render ダッシュボードで "Manual deploy" を実行
3. ユーザーに認証URLを共有

#### ユーザー削除
1. `OAUTH2_PROXY_ALLOWED_EMAILS` 環境変数からメールアドレス削除
2. Render ダッシュボードで "Manual deploy" を実行
3. 必要に応じてセッション無効化

#### ドメイン単位での管理
- `OAUTH2_PROXY_EMAIL_DOMAINS=example.com` でドメイン全体を許可
- 個別メール管理よりも運用が楽

### モニタリング

#### 監視項目
- OAuth2-Proxyサービスの稼働状況
- Private Serviceへのアクセス状況
- 認証失敗ログ
- 不正アクセス試行

#### ログ管理
- OAuth2-Proxy認証ログ
- Video2Minutesアプリケーションログ
- Google OAuth監査ログ

## セキュリティ考慮事項

### 脅威分析

| 脅威 | 対策 | 実装方法 |
|---|---|---|
| 未認証アクセス | OAuth2認証必須化 | Private Service + OAuth2-Proxy |
| セッションハイジャック | Secure Cookie | HTTPS + HttpOnly + SameSite |
| CSRF攻撃 | SameSite Cookie | Cookie設定 |
| 不正ユーザー | 許可リスト制御 | emails.txt + domain制限 |

### ベストプラクティス

1. **定期的な許可リスト見直し**
   - 月次で不要ユーザーの削除
   - 離職者の即座の削除

2. **Cookie設定の強化**
   - Secure, HttpOnly, SameSite属性の設定
   - 適切な有効期限設定

3. **ログ監視**
   - 認証失敗の監視
   - 異常なアクセスパターンの検出

4. **バックアップ設定**
   - 許可リストのバージョン管理
   - 設定ファイルのバックアップ

## トラブルシューティング

### よくあるハマりどころ

| 症状 | 原因と対処 |
|---|---|
| Google で **"Error 400: redirect_uri_mismatch"** | Redirect URI が `https://..../oauth2/callback` と一致していない。Google Cloud Console で修正 |
| ログイン後に **無限リダイレクト** | Cookie Secret が 32 byte 未満、もしくは `OAUTH2_PROXY_COOKIE_DOMAIN` の値が不正 |
| Private Service が **タイムアウト (502)** | `OAUTH2_PROXY_UPSTREAMS` のホスト名 or ポート誤り / アプリ側が起動していない |
| ユーザーが認証後も **403 Forbidden** | `OAUTH2_PROXY_EMAIL_DOMAINS` または `OAUTH2_PROXY_ALLOWED_EMAILS` の設定漏れ |

### デバッグ方法

1. **OAuth2-Proxyログ確認**
   - Render ダッシュボード → OAuth2-Proxy サービス → Logs
   - 認証エラーの詳細が出力される

2. **Private Service接続確認**
   ```bash
   # OAuth2-Proxy コンテナ内から Private Service に疎通確認
   curl http://myapp-internal:8000/health
   ```

3. **Cookie確認**
   - ブラウザの開発者ツールで Cookie の内容を確認
   - `_oauth2_proxy` Cookie が適切に設定されているか

## 運用のポイント

### 仕上げ＆運用のベストプラクティス

| ポイント | やること |
|---|---|
| **HTTPS 強制** | Render が自動で TLS を付与。HTTP で来た場合はアプリ側で 301 リダイレクト推奨 |
| **.onrender.com を隠したい** | カスタムドメインを Render に追加し、Google の "Authorized domains" に追記 |
| **利用者追加/削除** | `OAUTH2_PROXY_ALLOWED_EMAILS` を編集 → "Manual deploy" で反映 |
| **コスト** | Proxy もアプリも Free インスタンスで起動可。ただしアイドル 15 分でスリープするので注意（有料プランなら常時起動） |
| **IaC 化** | Render Blueprint (`render.yaml`) で 2 サービスをコード管理すると再現性が担保できて便利 |

### セキュリティチェックリスト

- [ ] Private Service が外部から直接アクセスできないことを確認
- [ ] Google OAuth の Redirect URI が正しく設定されている
- [ ] Cookie Secret が 32 byte 以上のランダム文字列
- [ ] 許可するメールアドレス/ドメインが適切に設定されている
- [ ] HTTPS が強制されている
- [ ] 定期的な許可リストの見直し

## 費用見積もり

### Renderサービス費用
- **OAuth2-Proxy**: $7/月（Starter Plan）
- **Video2Minutes Private**: $7/月（Starter Plan）
- **合計**: $14/月

### 無料プランでの検証
- **OAuth2-Proxy**: 無料（15分アイドルでスリープ）
- **Video2Minutes Private**: 無料（15分アイドルでスリープ）
- **制限**: アイドル時のスリープあり

### Google Cloud Platform
- OAuth2.0利用: 無料（月100万リクエストまで）

## 代替案検討

| 方式 | メリット | デメリット | 推奨度 |
|---|---|---|---|
| **OAuth2-Proxy** | 完全分離、柔軟な設定 | 追加コスト | ⭐⭐⭐⭐⭐ |
| Basic認証 | 実装簡単、低コスト | ユーザー管理困難 | ⭐⭐⭐ |
| IP制限 | 実装簡単 | 柔軟性低い | ⭐⭐ |
| アプリ内認証 | カスタマイズ可能 | 開発コスト高 | ⭐⭐ |

## 結論

**OAuth2-Proxy + Private Service**構成は以下の理由で最適：

1. ✅ **完全なアクセス制御**: Private Serviceにより外部からの直接アクセスを完全遮断
2. ✅ **信頼できる認証**: Google/GitHubの認証基盤を活用
3. ✅ **柔軟なユーザー管理**: ドメイン単位・個別メール両方に対応
4. ✅ **低い運用負荷**: ユーザー追加は設定ファイル更新のみ
5. ✅ **適切なコスト**: 月$14でエンタープライズレベルのセキュリティ

チーム内のGoogleアカウントを持つメンバーのみにアクセスを制限する要件に最適な解決策である。