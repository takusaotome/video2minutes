# API リファレンス

このドキュメントでは、`video2minutes` サービスの主なREST APIを説明します。ベースURLは `/api/v1` です。

## 参考: 設計書より抜粋

`docs/DESIGN.md` では主要エンドポイントのサンプルレスポンスが示されています。

```
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
```

## エンドポイント一覧

### 1. アップロード

- **URL**: `/api/v1/minutes/upload`
- **メソッド**: `POST`
- **内容**: 動画または音声ファイルをアップロードして処理を開始します。
- **パラメータ**
  - `file` (form-data, 必須): アップロードするメディアファイル。
- **レスポンス例**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued"
}
```

### 2. タスク一覧取得

- **URL**: `/api/v1/minutes/tasks`
- **メソッド**: `GET`
- **内容**: 現在のセッションで扱う全タスクの一覧を取得します。
- **レスポンス例**
```json
{
  "tasks": [
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "video_filename": "meeting.mp4",
      "status": "processing",
      "overall_progress": 45
    }
  ]
}
```

### 3. タスクステータス取得

- **URL**: `/api/v1/minutes/{task_id}/status`
- **メソッド**: `GET`
- **内容**: 指定したタスクの現在の処理状況を返します。
- **パラメータ**
  - `task_id` (path, 必須): 取得対象のタスクID。
- **レスポンス例**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "current_step": "transcription",
  "overall_progress": 45,
  "steps": [
    {"name": "upload", "status": "completed", "progress": 100},
    {"name": "audio_extraction", "status": "completed", "progress": 100},
    {"name": "transcription", "status": "processing", "progress": 45},
    {"name": "minutes_generation", "status": "pending", "progress": 0}
  ],
  "video_filename": "meeting.mp4",
  "upload_timestamp": "2023-01-01T12:00:00Z"
}
```

### 4. 結果取得

- **URL**: `/api/v1/minutes/{task_id}/result`
- **メソッド**: `GET`
- **内容**: 処理が完了したタスクの文字起こしと議事録を取得します。
- **パラメータ**
  - `task_id` (path, 必須): 対象タスクID。
- **レスポンス例**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "video_filename": "meeting.mp4",
  "transcription": "...文字起こし全文...",
  "minutes": "...生成された議事録...",
  "upload_timestamp": "2023-01-01T12:00:00Z"
}
```

### 5. タスク削除

- **URL**: `/api/v1/minutes/{task_id}`
- **メソッド**: `DELETE`
- **内容**: 指定したタスクを削除します。
- **パラメータ**
  - `task_id` (path, 必須): 削除するタスクID。
- **レスポンス例**
```json
{}
```

以上が基本的なAPIエンドポイントです。その他の詳細は `api_spec.json` を参照してください。
