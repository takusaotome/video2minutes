# Video2Minutes Frontend

Vue.js 3 + PrimeVue フロントエンドアプリケーション

## 機能

- 動画ファイルのアップロード（ドラッグ&ドロップ対応）
- リアルタイム処理進捗表示
- タスク管理（一覧表示、詳細確認、再実行、削除）
- 議事録の表示・ダウンロード（Markdown、テキスト、PDF）
- レスポンシブデザイン（PC・タブレット・スマートフォン対応）

## 技術スタック

- **Vue.js 3** - プログレッシブJavaScriptフレームワーク
- **PrimeVue** - UIコンポーネントライブラリ
- **Pinia** - 状態管理
- **Vue Router** - ルーティング
- **Axios** - HTTP通信
- **Vite** - ビルドツール

## 開発環境のセットアップ

### 前提条件

- Node.js 16.0.0 以上
- npm または yarn

### インストール

```bash
# 依存関係のインストール
npm install

# 開発サーバーの起動
npm run dev

# ビルド
npm run build

# プレビュー
npm run preview
```

### 環境変数

`.env.example` をコピーして `.env` ファイルを作成し、必要な環境変数を設定してください。

```bash
cp .env.example .env
```

## ディレクトリ構造

```
src/
├── assets/          # 静的アセット
├── components/      # 再利用可能なコンポーネント
│   ├── FileUploader.vue
│   ├── TaskList.vue
│   ├── TaskDetailModal.vue
│   └── MinutesViewer.vue
├── views/           # ページコンポーネント
│   ├── DashboardView.vue
│   └── MinutesView.vue
├── services/        # API通信・WebSocket
│   ├── api.js
│   └── websocket.js
├── stores/          # Pinia状態管理
│   └── tasks.js
├── router/          # ルーティング設定
│   └── index.js
├── App.vue          # ルートコンポーネント
└── main.js          # エントリーポイント
```

## 主要機能

### ファイルアップロード

- ドラッグ&ドロップ対応
- 複数ファイル同時アップロード
- プログレスバー表示
- ファイルサイズ・形式バリデーション

### タスク管理

- リアルタイム進捗更新（WebSocket接続）
- タスク一覧表示（データテーブル）
- 詳細モーダル（処理ステップ表示）
- 再実行・削除機能

### 議事録表示

- サイドバー（文字起こし全文）
- メイン（生成された議事録）
- コピー・ダウンロード機能
- レスポンシブレイアウト

## API連携

バックエンドAPIとの通信は `services/api.js` で管理されています。

```javascript
// タスク一覧取得
const tasks = await minutesApi.getTasks()

// ファイルアップロード
const task = await minutesApi.uploadVideo(file, onProgress)

// タスク状況確認
const status = await minutesApi.getTaskStatus(taskId)
```

## 状態管理

Piniaを使用してアプリケーション状態を管理しています。

```javascript
// stores/tasks.js
const tasksStore = useTasksStore()

// タスク一覧取得
await tasksStore.fetchTasks()

// ファイルアップロード
await tasksStore.uploadFile(file, onProgress)
```

## スタイリング

- PrimeVueテーマ（Lara Light Blue）
- カスタムCSS（scoped styles）
- レスポンシブデザイン
- CSS Grid・Flexbox使用

## ビルド・デプロイ

### ローカルビルド

```bash
npm run build
```

### Renderデプロイ

環境変数を設定してGitHubリポジトリからデプロイ：

```yaml
# render.yaml
services:
  - type: static
    name: video2minutes-frontend
    rootDir: src/frontend
    buildCommand: npm install && npm run build
    staticPublishPath: ./dist
    envVars:
      - key: VITE_API_URL
        value: https://video2minutes-api.onrender.com
```

## 開発時の注意点

1. **API URL設定**: `.env`ファイルでバックエンドAPIのURLを正しく設定
2. **CORS設定**: バックエンド側でフロントエンドドメインを許可
3. **WebSocket接続**: 本番環境ではHTTPS/WSS使用
4. **ファイルサイズ制限**: アップロード制限をフロントエンド・バックエンド両方で設定

## トラブルシューティング

### よくある問題

1. **API接続エラー**
   - `.env`ファイルのVITE_API_URL設定を確認
   - バックエンドサーバーが起動しているか確認

2. **WebSocket接続失敗**
   - VITE_WS_URL設定を確認
   - ネットワーク・ファイアウォール設定を確認

3. **アップロードエラー**
   - ファイルサイズ制限を確認
   - サポートされているファイル形式か確認