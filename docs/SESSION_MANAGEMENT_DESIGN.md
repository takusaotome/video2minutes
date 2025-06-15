# セッション管理設計書

その他の設計ドキュメントは[README](README.md)をご覧ください。

## 課題
現在、すべてのユーザーが同じタスクストアを共有しており、異なるユーザーがお互いの議事録を見ることができてしまう。

## 解決方針

### Phase 1: セッションベースのタスク分離

#### 1. セッション管理の実装
- FastAPIのセッション機能を使用
- セッションIDをCookieで管理
- セッションごとにタスクを分離

#### 2. タスクストアの構造変更
```python
# 現在
tasks_store: Dict[str, MinutesTask] = {}

# 変更後
tasks_store: Dict[str, Dict[str, MinutesTask]] = {}
# session_id -> {task_id -> MinutesTask}
```

#### 3. API エンドポイントの変更
- すべてのAPIにセッション管理を追加
- セッションIDでタスクをフィルタリング
- WebSocket接続もセッション単位で管理

### Phase 2: ユーザー認証システム統合（将来）

#### 1. ユーザー管理
- ユーザーIDベースのタスク分離
- 永続的なユーザーセッション
- データベース統合

#### 2. 権限管理
- 管理者権限の追加
- タスク共有機能
- アクセス制御

## 実装詳細

### 1. セッション管理ミドルウェア

```python
from fastapi import Request, Response
from starlette.middleware.sessions import SessionMiddleware
import uuid

class SessionManager:
    @staticmethod
    def get_session_id(request: Request) -> str:
        session_id = request.session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session["session_id"] = session_id
        return session_id
```

### 2. セッションベースタスクストア

```python
class SessionTaskStore:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, MinutesTask]] = {}
    
    def get_tasks(self, session_id: str) -> List[MinutesTask]:
        return list(self.sessions.get(session_id, {}).values())
    
    def get_task(self, session_id: str, task_id: str) -> Optional[MinutesTask]:
        return self.sessions.get(session_id, {}).get(task_id)
    
    def add_task(self, session_id: str, task: MinutesTask):
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        self.sessions[session_id][task.task_id] = task
    
    def delete_task(self, session_id: str, task_id: str):
        if session_id in self.sessions and task_id in self.sessions[session_id]:
            del self.sessions[session_id][task_id]
```

### 3. API エンドポイントの更新

```python
@router.get("/tasks", response_model=TaskListResponse)
async def get_all_tasks(request: Request) -> TaskListResponse:
    session_id = SessionManager.get_session_id(request)
    tasks = session_task_store.get_tasks(session_id)
    tasks.sort(key=lambda x: x.upload_timestamp, reverse=True)
    return TaskListResponse(tasks=tasks)

@router.post("/upload", response_model=UploadResponse)
async def upload_media(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    session_id = SessionManager.get_session_id(request)
    # ... existing upload logic ...
    session_task_store.add_task(session_id, task)
    # ...
```

### 4. WebSocket接続の分離

```python
# セッション単位のWebSocket接続管理
websocket_connections: Dict[str, Dict[str, List[WebSocket]]] = {}
# session_id -> {task_id -> [WebSocket]}

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str, request: Request):
    session_id = SessionManager.get_session_id(request)
    # セッションのタスクのみWebSocket接続を許可
    if not session_task_store.get_task(session_id, task_id):
        await websocket.close(code=4004, reason="Task not found for session")
        return
    # ...
```

### 5. フロントエンドの対応

```javascript
// セッションCookieの自動管理
// axios設定でwithCredentials: trueを有効化
const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL,
  withCredentials: true, // Cookieを自動送信
});
```

## セキュリティ考慮事項

1. **セッションセキュリティ**
   - Secure Cookie フラグ
   - HttpOnly フラグ
   - SameSite 属性

2. **セッション有効期限**
   - タイムアウト設定
   - 非アクティブセッションの自動削除

3. **CSRF対策**
   - CSRFトークンの実装

## メリット

1. **データプライバシー**
   - ユーザー間のデータ分離
   - セッション単位のアクセス制御

2. **スケーラビリティ**
   - 将来的なマルチユーザー対応
   - 認証システムとの統合準備

3. **最小限の変更**
   - 既存のUIは変更不要
   - バックエンドAPIの小さな変更のみ

## 実装順序

1. セッション管理ミドルウェアの追加
2. セッションベースタスクストアの実装
3. APIエンドポイントの更新
4. WebSocket接続の分離
5. フロントエンドの設定変更
6. テストとデバッグ