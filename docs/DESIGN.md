# 動画から議事録生成Webアプリケーション 設計書

## 1. システム概要

### 1.1 プロジェクト概要
動画ファイルをアップロードすると、自動的に文字起こしと議事録生成を行うWebアプリケーション。

### 1.2 主要機能
- 動画ファイルのアップロード
- 音声の文字起こし（Whisper API使用）
- AI議事録生成（Claude API使用）
- 生成された議事録のWeb表示・ダウンロード

### 1.3 技術スタック
- **バックエンド**: FastAPI (Python)
- **フロントエンド**: Vue.js 3 + PrimeVue
- **文字起こし**: OpenAI Whisper API
- **議事録生成**: Anthropic Claude API
- **デプロイ**: Render (Web Service + Static Site)

## 2. システムアーキテクチャ

### 2.1 全体構成
```
┌─────────────────────┐
│   クライアント      │
│  (Vue + PrimeVue)  │
└──────────┬──────────┘
           │ HTTP/HTTPS
           │
┌──────────▼──────────┐
│   FastAPI Server   │
│  (バックエンドAPI)  │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌────────┐   ┌────────┐
│Whisper │   │ Claude │
│  API   │   │  API   │
└────────┘   └────────┘
```

### 2.2 処理フロー
1. ユーザーが動画ファイルをアップロード
2. バックエンドで動画から音声を抽出
3. Whisper APIで文字起こし
4. Claude APIで議事録生成
5. 生成結果をフロントエンドに返却
6. ユーザーに表示・ダウンロード提供

## 3. バックエンド設計 (FastAPI)

### 3.1 ディレクトリ構造
```
video2minutes/
├── src/
│   └── backend/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py              # FastAPIアプリケーション
│       │   ├── config.py            # 設定管理
│       │   ├── models.py            # Pydanticモデル
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── video_processor.py    # 動画処理
│       │   │   ├── transcription.py      # 文字起こし
│       │   │   └── minutes_generator.py  # 議事録生成
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   └── endpoints/
│       │   │       ├── __init__.py
│       │   │       └── minutes.py        # APIエンドポイント
│       │   └── utils/
│       │       ├── __init__.py
│       │       └── file_handler.py       # ファイル処理
│       ├── tests/
│       ├── requirements.txt
│       └── Dockerfile
├── docs/
│   └── DESIGN.md
├── README.md
└── .gitignore
```

### 3.2 主要APIエンドポイント
```python
# POST /api/v1/minutes/upload
# 動画アップロード（即座にタスクIDを返却）
# Request: multipart/form-data
# Response: {"task_id": "uuid", "status": "queued"}

# GET /api/v1/minutes/tasks
# 全タスクの一覧と進行状況を取得
# Response: [{"task_id": "...", "filename": "...", "status": "...", "progress": 45, ...}]

# GET /api/v1/minutes/{task_id}/status
# 特定タスクの詳細状況確認
# Response: {
#   "task_id": "uuid",
#   "status": "processing",
#   "current_step": "transcribing",
#   "progress": 45,
#   "steps": [
#     {"name": "upload", "status": "completed", "progress": 100},
#     {"name": "audio_extraction", "status": "completed", "progress": 100},
#     {"name": "transcription", "status": "processing", "progress": 45},
#     {"name": "minutes_generation", "status": "pending", "progress": 0}
#   ]
# }

# GET /api/v1/minutes/{task_id}/result
# 生成結果取得（完了時のみ）

# WebSocket /api/v1/ws/{task_id}
# リアルタイム進捗通知用WebSocket接続
```

### 3.3 非同期処理設計

#### 3.3.1 タスクキュー構成
- **FastAPI BackgroundTasks** を使用（初期実装）
- 将来的にCelery + Redisへ移行可能な設計
- タスクは即座にキューに追加され、バックグラウンドで処理

#### 3.3.2 処理フロー
1. **アップロード完了時**
   - 即座にタスクIDを生成・返却
   - ファイルを一時ディレクトリに保存
   - バックグラウンドタスクをキューに追加
   
2. **バックグラウンド処理**
   - 音声抽出（ffmpeg使用）
   - Whisper API呼び出し（文字起こし）
   - Claude API呼び出し（議事録生成）
   - 各ステップで進捗を更新

3. **進捗通知**
   - WebSocket経由でリアルタイム通知
   - または定期的なポーリング（fallback）

#### 3.3.3 タスク管理
```python
# メモリ内タスク管理（初期実装）
tasks_store = {}  # task_id -> TaskStatus

# 将来的にはRedisやDBへ移行
```

### 3.4 エラーハンドリング
- ファイルサイズ制限（例: 500MB）
- サポート動画形式のバリデーション
- API制限・エラー時のリトライ処理

## 4. フロントエンド設計 (Vue.js + PrimeVue)

### 4.1 ディレクトリ構造
```
video2minutes/
├── src/
│   └── frontend/
│       ├── public/
│       ├── src/
│       │   ├── assets/
│       │   ├── components/
│       │   │   ├── FileUploader.vue      # ファイルアップロード
│       │   │   ├── TaskList.vue          # タスク一覧
│       │   │   ├── TaskDetailModal.vue  # タスク詳細モーダル
│       │   │   └── MinutesViewer.vue     # 議事録表示
│       │   ├── views/
│       │   │   ├── DashboardView.vue     # ダッシュボード
│       │   │   └── MinutesView.vue       # 議事録ページ
│       │   ├── services/
│       │   │   ├── api.js               # API通信
│       │   │   └── websocket.js         # WebSocket管理
│       │   ├── stores/
│       │   │   └── tasks.js             # タスク状態管理（Pinia）
│       │   ├── router/
│       │   │   └── index.js
│       │   ├── App.vue
│       │   └── main.js
│       ├── package.json
│       ├── vite.config.js
│       └── Dockerfile
```

### 4.2 主要画面設計

#### 4.2.1 ダッシュボード（メイン画面）
- **上部**: ファイルアップロードエリア
  - PrimeVueのFileUploadコンポーネント
  - ドラッグ&ドロップ対応
  - 複数ファイル同時アップロード対応
  
- **中央**: 処理中タスク一覧
  - DataTableコンポーネントで表示
  - カラム: ファイル名、ステータス、進捗、アップロード時刻、アクション
  - リアルタイム更新（1秒ごと or WebSocket）
  - ステータスバッジ（処理中/完了/エラー）
  
- **通知システム**
  - Toast通知（画面右上）
  - 処理完了時に自動表示
  - クリックで詳細画面へ遷移

#### 4.2.2 タスク詳細モーダル
- Dialogコンポーネントで実装
- 処理ステップごとの詳細進捗
- ProgressBarとTimelineで視覚化
- エラー時の詳細メッセージ表示
- 「議事録を見る」ボタン（完了時）

#### 4.2.3 議事録表示画面
- 左サイド: 文字起こし全文（折りたたみ可能）
- 右サイド: 生成された議事録
- アクションボタン:
  - ダウンロード（MD/PDF/DOCX）
  - コピー
  - 新規タスク作成

### 4.3 UIコンポーネント活用
- FileUpload: ファイルアップロード
- DataTable: タスク一覧表示
- ProgressBar: 進捗表示
- Timeline: 処理ステップ表示
- Badge: ステータス表示
- Card: コンテンツ表示
- Button: 各種アクション
- Toast: 通知メッセージ
- Dialog: モーダルダイアログ

### 4.4 状態管理とリアルタイム更新

#### 4.4.1 Pinia Store設計
```javascript
// stores/tasks.js
export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [],  // 全タスクリスト
    activeTaskId: null,
    pollingInterval: null,
    wsConnection: null
  }),
  
  actions: {
    async fetchTasks() { /* ... */ },
    async uploadFile(file) { /* ... */ },
    startPolling() { /* ... */ },
    connectWebSocket(taskId) { /* ... */ },
    showCompletionNotification(task) { /* ... */ }
  }
})
```

#### 4.4.2 リアルタイム更新戦略
1. **初期実装**: 1秒間隔のポーリング
2. **最適化版**: WebSocket接続（処理中タスクのみ）
3. **通知**: PrimeVue Toastで完了通知

## 5. データモデル設計

### 5.1 議事録タスクモデル
```python
class MinutesTask:
    id: str                    # タスクID
    status: str               # pending/processing/completed/failed
    video_filename: str       # アップロードファイル名
    video_size: int          # ファイルサイズ
    upload_timestamp: datetime
    processing_steps: List[ProcessingStep]
    transcription: str       # 文字起こし結果
    minutes: str            # 議事録
    error_message: str      # エラー時のメッセージ
    
class ProcessingStep:
    name: str               # ステップ名
    status: str            # pending/processing/completed/failed
    started_at: datetime
    completed_at: datetime
    progress: int          # 進捗（0-100）
```

## 6. セキュリティ設計

### 6.1 認証・認可
- 初期版：認証なし（パブリック利用）
- 将来版：JWT認証実装検討

### 6.2 ファイルセキュリティ
- アップロードファイルのウイルススキャン
- 一時ファイルの自動削除
- ファイルタイプ検証

### 6.3 API保護
- Rate Limiting実装
- CORS設定
- APIキーの環境変数管理

## 7. デプロイメント設計（Render）

### 7.1 構成
- **バックエンド**: Render Web Service
- **フロントエンド**: Render Static Site
- **環境変数**: Render環境変数管理

### 7.2 デプロイ設定

#### 7.2.1 プロジェクトルートの render.yaml
```yaml
services:
  - type: web
    name: video2minutes-api
    env: python
    rootDir: src/backend
    buildCommand: pip install -r ../../requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      
  - type: static
    name: video2minutes-frontend
    rootDir: src/frontend
    buildCommand: npm install && npm run build
    staticPublishPath: ./dist
    headers:
      - path: /*
        name: X-Frame-Options
        value: DENY
    envVars:
      - key: VITE_API_URL
        value: https://video2minutes-api.onrender.com
```

### 7.3 CI/CD
- GitHub連携による自動デプロイ
- mainブランチへのプッシュで自動ビルド・デプロイ

## 8. 性能・拡張性設計

### 8.1 性能要件
- 動画アップロード: 最大500MB
- 処理時間目安: 10分動画で3-5分
- 同時処理数: 10タスク

### 8.2 拡張性考慮
- Redisキューによるジョブ管理（将来）
- S3互換ストレージ対応（将来）
- マルチ言語対応

## 9. 開発スケジュール案

### Phase 1: MVP（2週間）
- 基本的なアップロード・処理機能
- シンプルなUI
- Render デプロイ

### Phase 2: 機能拡張（2週間）
- UIの改善
- エラーハンドリング強化
- パフォーマンス最適化

### Phase 3: 本番対応（2週間）
- セキュリティ強化
- モニタリング追加
- ドキュメント整備

## 10. ユーザー体験フロー

### 10.1 基本的な利用フロー
1. **ファイルアップロード**
   - ユーザーが動画をドラッグ&ドロップ
   - 即座に「アップロード完了」トースト表示
   - タスク一覧に新規行が追加される

2. **処理中の体験**
   - タスク一覧で進捗がリアルタイム更新
   - 詳細を見たい場合はクリックでモーダル表示
   - 他のタスクも並行してアップロード可能

3. **完了通知**
   - 画面右上にトースト通知
   - 「会議録_2025-01-13.mp4の議事録が完成しました」
   - トーストをクリックで議事録画面へ遷移

### 10.2 エラー時の対応
- エラー通知もトーストで表示
- タスク一覧でエラー状態を赤色バッジで表示
- 詳細モーダルでエラー内容と再試行ボタン提供

## 11. 今後の検討事項

- ユーザー認証機能
- 議事録の保存・管理機能
- 複数ファイルの一括処理
- リアルタイム文字起こし（ストリーミング）
- 議事録テンプレートのカスタマイズ
- 多言語対応
- プッシュ通知（ブラウザ通知API）
- バッチ処理の優先度設定