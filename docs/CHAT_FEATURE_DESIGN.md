# 議事録チャット機能 設計書 v2.0

ドキュメント全体の目次は[README](README.md)を参照してください。

## 概要

議事録詳細画面に**フローティングチャット機能**を追加し、文字起こし全文をコンテキストとして活用したAI質問応答システムを実装する。初期表示では全文文字起こしを非表示にし、会議情報と議事録を横幅いっぱいに表示する新しいレイアウトを採用する。

## 新しいUI設計コンセプト

### レイアウト変更
- **初期状態**: 全文文字起こしは非表示、会議情報と議事録が横幅いっぱいに表示
- **フローティングチャット**: 画面右下にFAB（Floating Action Button）として配置
- **サイドパネル**: 全文文字起こしはメニューから呼び出し可能なサイドパネルとして表示

### ユーザーエクスペリエンス
1. **シンプルな初期表示**: 重要な情報（会議詳細・議事録）に集中
2. **オンデマンドアクセス**: 必要な時だけ文字起こしやチャット機能を利用
3. **非侵入的インターフェース**: メインコンテンツを邪魔しないフローティング設計

## 機能要件

### 基本機能

#### フローティングチャット機能
- **FABボタン**: 画面右下に固定配置されたチャットアイコンボタン
- **チャット展開**: クリックでチャットパネルが展開（オーバーレイまたはサイドパネル形式）
- **最小化・最大化**: チャット状態の切り替え機能
- **通知バッジ**: 新しい回答や重要な情報の通知表示

#### 質問応答機能
- **文字起こし内容に基づく質問応答**: 会議内容に関する質問に対して文字起こし全文を参照して回答
- **チャット履歴保存**: セッション中のやり取りを保持
- **コンテキスト理解**: 前回の質問・回答を踏まえた継続的な対話
- **引用表示**: 回答時に参照した文字起こしの該当箇所を表示

#### サイドパネル機能（全文文字起こし）
- **メニュートリガー**: ハンバーガーメニューまたは専用ボタンからアクセス
- **スライドイン表示**: 左側からスライドインするサイドパネル
- **検索・ハイライト**: 文字起こし内の検索とハイライト機能
- **時間軸ナビゲーション**: タイムスタンプによる内容ジャンプ

#### 議事録編集機能
- **誤字・脱字修正**: 間違った単語や表現の一括修正
- **アクションアイテム追加・編集**: 漏れていたタスクの追加や詳細情報の更新
- **内容補強**: 不足している情報の追記や詳細化
- **構造化改善**: 議事録の構成や見出しの最適化
- **リアルタイム反映**: 編集内容の即座画面更新

### 想定ユースケース

#### 質問応答（フローティングチャット）
1. **決定事項の確認**: "この会議でXXについてどんな結論になりましたか？"
2. **担当者の確認**: "タスクAの担当者は誰になりましたか？"
3. **期限の確認**: "プロジェクトの納期はいつでしたっけ？"
4. **詳細説明**: "XXについてもう少し詳しく教えてください"
5. **要約**: "今日の会議のポイントを3つ教えてください"

#### 議事録編集（チャット経由）
1. **誤字修正**: "議事録内の'プロジェクトX'を'プロジェクトAlpha'に修正して"
2. **アクションアイテム追加**: "田中さんに資料作成のタスクを追加して、期限は来週金曜日"
3. **担当者修正**: "タスクBの担当者を佐藤さんから山田さんに変更して"
4. **期限更新**: "システム改修タスクの期限を2月末に延期して"
5. **内容補強**: "決定事項に予算承認の件を追加して"
6. **優先度設定**: "セキュリティ対応タスクを高優先度に変更して"

#### サイドパネル利用
1. **詳細確認**: 議事録で気になった点の元発言を確認
2. **文脈理解**: 決定に至った議論の流れを把握
3. **引用作成**: 特定の発言を引用して報告書作成

## システム設計

### 新しいアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    フロントエンド                              │
│                                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│ │メインレイアウト│  │サイドパネル  │  │フローティングチャット │ │
│ │             │  │(文字起こし)  │  │                     │ │
│ │┌───────────┐│  │             │  │ ┌─────────────────┐ │ │
│ ││会議詳細   ││  │┌───────────┐│  │ │ FABボタン       │ │ │
│ │└───────────┘│  ││検索・ハイラ││  │ └─────────────────┘ │ │
│ │┌───────────┐│  ││イト機能   ││  │ ┌─────────────────┐ │ │
│ ││議事録     ││  │└───────────┘│  │ │ チャットパネル   │ │ │
│ │└───────────┘│  │┌───────────┐│  │ │ (展開時)        │ │ │
│ └─────────────┘  ││時間軸ナビ ││  │ └─────────────────┘ │ │
│                  │└───────────┘│  └─────────────────────┘ │
│                  └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    バックエンド                                │
│                                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│ │チャットAPI  │  │セッション   │  │議事録編集API        │ │
│ │             │  │ストレージ   │  │                     │ │
│ └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   OpenAI API                               │
│                                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│ │ GPT-4       │  │ 引用機能    │  │ 編集提案生成        │ │
│ │ 質問応答    │  │             │  │                     │ │
│ └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### データフロー

1. **初期化**
   - 議事録詳細画面で文字起こし全文を取得
   - メインレイアウト（会議詳細・議事録）を横幅いっぱいに表示
   - フローティングチャットボタンを右下に配置

2. **チャット開始**
   - FABボタンクリックでチャットパネル展開
   - チャットセッションを初期化
   - 文字起こし内容をコンテキストとして設定

3. **質問処理**
   - ユーザーの質問を受信
   - チャット履歴と文字起こし内容を組み合わせてプロンプト生成
   - OpenAI APIに送信

4. **回答生成**
   - AI回答を受信
   - 引用箇所があれば該当部分をハイライト
   - チャット履歴に追加して表示

5. **サイドパネル表示**
   - メニューボタンクリックでサイドパネル展開
   - 文字起こし全文を表示
   - 検索・ハイライト機能を提供

## 実装仕様

### フロントエンド

#### コンポーネント構成

```vue
<!-- MinutesViewer.vue (メインコンポーネント) -->
<template>
  <div class="minutes-viewer">
    <!-- メインコンテンツエリア -->
    <div class="main-content" :class="{ 'sidebar-open': showSidebar }">
      <!-- ヘッダー -->
      <div class="header">
        <button @click="toggleSidebar" class="sidebar-toggle">
          <i class="pi pi-bars"></i>
        </button>
        <h1>議事録詳細</h1>
      </div>
      
      <!-- 会議詳細・議事録エリア -->
      <div class="content-grid">
        <MeetingDetails :meeting="meeting" />
        <GeneratedMinutes :minutes="minutes" />
      </div>
    </div>
    
    <!-- サイドパネル（文字起こし全文） -->
    <TranscriptionSidebar 
      :show="showSidebar"
      :transcription="transcription"
      @close="closeSidebar"
    />
    
    <!-- フローティングチャット -->
    <FloatingChat 
      :task-id="taskId"
      :transcription="transcription"
      :minutes="minutes"
    />
  </div>
</template>
```

```vue
<!-- FloatingChat.vue -->
<template>
  <div class="floating-chat">
    <!-- FABボタン -->
    <button 
      v-if="!isExpanded"
      @click="expandChat"
      class="fab-button"
      :class="{ 'has-notification': hasNewMessage }"
    >
      <i class="pi pi-comments"></i>
      <span v-if="hasNewMessage" class="notification-badge">!</span>
    </button>
    
    <!-- チャットパネル -->
    <div 
      v-if="isExpanded"
      class="chat-panel"
      :class="{ 'minimized': isMinimized }"
    >
      <div class="chat-header">
        <h3>議事録について質問</h3>
        <div class="chat-controls">
          <button @click="toggleMinimize" class="minimize-btn">
            <i :class="isMinimized ? 'pi pi-window-maximize' : 'pi pi-window-minimize'"></i>
          </button>
          <button @click="closeChat" class="close-btn">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
      
      <div v-if="!isMinimized" class="chat-content">
        <ChatMessages :messages="messages" />
        <ChatInput @send="sendMessage" :loading="isLoading" />
      </div>
    </div>
  </div>
</template>
```

```vue
<!-- TranscriptionSidebar.vue -->
<template>
  <div class="transcription-sidebar" :class="{ 'show': show }">
    <div class="sidebar-header">
      <h3>文字起こし全文</h3>
      <button @click="$emit('close')" class="close-btn">
        <i class="pi pi-times"></i>
      </button>
    </div>
    
    <div class="sidebar-content">
      <!-- 検索機能 -->
      <div class="search-section">
        <input 
          v-model="searchQuery"
          placeholder="文字起こし内を検索..."
          class="search-input"
        />
      </div>
      
      <!-- 文字起こし内容 -->
      <div class="transcription-content">
        <div 
          v-for="(segment, index) in filteredSegments"
          :key="index"
          class="transcription-segment"
          :class="{ 'highlighted': segment.highlighted }"
        >
          <span class="timestamp">{{ segment.timestamp }}</span>
          <p class="text">{{ segment.text }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
```

#### スタイリング

```scss
// フローティングチャット
.floating-chat {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  
  .fab-button {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--primary-color);
    color: white;
    border: none;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    
    &:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    }
    
    &.has-notification {
      animation: pulse 2s infinite;
    }
    
    .notification-badge {
      position: absolute;
      top: -4px;
      right: -4px;
      width: 20px;
      height: 20px;
      background: var(--red-500);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: bold;
    }
  }
  
  .chat-panel {
    width: 400px;
    height: 600px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: all 0.3s ease;
    
    &.minimized {
      height: 60px;
      
      .chat-content {
        display: none;
      }
    }
    
    .chat-header {
      padding: 16px;
      background: var(--surface-100);
      border-bottom: 1px solid var(--surface-200);
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }
      
      .chat-controls {
        display: flex;
        gap: 8px;
        
        button {
          width: 32px;
          height: 32px;
          border: none;
          background: transparent;
          border-radius: 4px;
          cursor: pointer;
          
          &:hover {
            background: var(--surface-200);
          }
        }
      }
    }
    
    .chat-content {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
  }
}

// サイドパネル
.transcription-sidebar {
  position: fixed;
  top: 0;
  left: -400px;
  width: 400px;
  height: 100vh;
  background: white;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  transition: left 0.3s ease;
  z-index: 999;
  
  &.show {
    left: 0;
  }
  
  .sidebar-header {
    padding: 16px;
    background: var(--surface-100);
    border-bottom: 1px solid var(--surface-200);
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }
  
  .sidebar-content {
    height: calc(100vh - 73px);
    overflow-y: auto;
    
    .search-section {
      padding: 16px;
      border-bottom: 1px solid var(--surface-200);
      
      .search-input {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid var(--surface-300);
        border-radius: 6px;
        font-size: 14px;
      }
    }
    
    .transcription-content {
      padding: 16px;
      
      .transcription-segment {
        margin-bottom: 16px;
        padding: 12px;
        border-radius: 6px;
        
        &.highlighted {
          background: var(--yellow-100);
          border-left: 4px solid var(--yellow-500);
        }
        
        .timestamp {
          font-size: 12px;
          color: var(--text-color-secondary);
          font-weight: 500;
        }
        
        .text {
          margin: 4px 0 0 0;
          line-height: 1.5;
        }
      }
    }
  }
}

// メインコンテンツの調整
.main-content {
  transition: margin-left 0.3s ease;
  
  &.sidebar-open {
    margin-left: 400px;
  }
  
  .content-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    padding: 24px;
    
    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }
}

// アニメーション
@keyframes pulse {
  0% {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
  50% {
    box-shadow: 0 4px 12px rgba(var(--primary-color-rgb), 0.4);
  }
  100% {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
}
```

### バックエンド

#### APIエンドポイント

```python
# 新規チャットセッション作成
POST /api/v1/minutes/{task_id}/chat/sessions
{
  "transcription": "文字起こし全文",
  "minutes": "議事録内容"
}
→ {
  "session_id": "chat_session_uuid",
  "context_tokens": 1500
}

# 質問送信
POST /api/v1/minutes/{task_id}/chat/sessions/{session_id}/messages
{
  "message": "ユーザーの質問",
  "message_type": "user",
  "intent": "question"  # "question" | "edit_request"
}
→ {
  "message_id": "msg_uuid",
  "response": "AI回答",
  "citations": [
    {
      "text": "引用テキスト",
      "start_time": "00:15:30",
      "confidence": 0.95
    }
  ],
  "tokens_used": 450,
  "edit_actions": []  # 編集リクエストの場合のみ
}

# 議事録編集実行
POST /api/v1/minutes/{task_id}/edit
{
  "session_id": "chat_session_uuid",
  "message_id": "msg_uuid",
  "edit_actions": [
    {
      "action_type": "replace_text",
      "target": "プロジェクトX",
      "replacement": "プロジェクトAlpha",
      "scope": "all"  # "all" | "section" | "specific"
    },
    {
      "action_type": "add_action_item",
      "content": {
        "task": "資料作成",
        "assignee": "田中さん",
        "due_date": "2024-01-26",
        "priority": "medium"
      }
    },
    {
      "action_type": "update_action_item",
      "item_id": "action_item_uuid",
      "updates": {
        "assignee": "山田さん",
        "priority": "high"
      }
    }
  ]
}
→ {
  "edit_id": "edit_uuid",
  "success": true,
  "updated_minutes": "更新後の議事録全文",
  "changes_summary": [
    "プロジェクトX → プロジェクトAlpha (3箇所)",
    "新規アクションアイテム追加: 資料作成",
    "タスクBの担当者変更: 佐藤さん → 山田さん"
  ]
}

# チャット履歴取得
GET /api/v1/minutes/{task_id}/chat/sessions/{session_id}/messages
→ {
  "messages": [
    {
      "message_id": "msg_uuid",
      "message": "質問内容",
      "response": "回答内容",
      "timestamp": "2024-01-15T10:30:00Z",
      "citations": [...]
    }
  ]
}

# セッション削除
DELETE /api/v1/minutes/{task_id}/chat/sessions/{session_id}
```

#### データモデル

```python
class ChatSession(BaseModel):
    session_id: str
    task_id: str
    transcription: str
    minutes: str
    created_at: datetime
    last_activity: datetime
    context_tokens: int

class ChatMessage(BaseModel):
    message_id: str
    session_id: str
    message: str
    response: str
    message_type: str  # "user" | "assistant"
    intent: str  # "question" | "edit_request"
    timestamp: datetime
    citations: List[Citation]
    edit_actions: List[EditAction]  # 編集リクエストの場合のみ
    tokens_used: int
    processing_time: float

class EditAction(BaseModel):
    action_type: str  # "replace_text" | "add_action_item" | "update_action_item" | "add_content" | "restructure"
    target: Optional[str]  # 対象テキスト（置換の場合）
    replacement: Optional[str]  # 置換テキスト
    scope: Optional[str]  # "all" | "section" | "specific"
    content: Optional[Dict]  # 追加・更新内容
    item_id: Optional[str]  # 更新対象のID
    updates: Optional[Dict]  # 更新内容

class EditHistory(BaseModel):
    edit_id: str
    task_id: str
    session_id: str
    message_id: str
    edit_actions: List[EditAction]
    changes_summary: List[str]
    original_minutes: str
    updated_minutes: str
    timestamp: datetime
    reverted: bool  # 取り消しフラグ

class Citation(BaseModel):
    text: str
    start_time: Optional[str]  # タイムスタンプ（可能であれば）
    confidence: float
    context: str  # 前後の文脈
```

#### プロンプト設計

```python
CHAT_SYSTEM_PROMPT = """
あなたは会議の議事録と文字起こしの内容に詳しいアシスタントです。
質問への回答と議事録の編集依頼の両方に対応できます。

以下の会議内容に基づいて、ユーザーの質問に正確かつ有用な回答を提供するか、
議事録の編集指示を解析して適切な編集アクションを提案してください。

【会議の文字起こし】
{transcription}

【生成された議事録】
{minutes}

【質問回答時の注意点】
1. 文字起こしや議事録の内容に基づいて回答する
2. 内容にない情報は推測しない
3. 不明な点は「文字起こしからは確認できません」と正直に答える
4. 回答時は該当する文字起こしの部分を引用する
5. 日本語で分かりやすく回答する
6. 前回の質問・回答の文脈も考慮する

【編集指示解析時の注意点】
1. 編集の意図を正確に理解する
2. 具体的な編集アクションを提案する
3. 変更範囲を明確にする（全体／セクション／特定箇所）
4. 元の文脈を壊さないよう配慮する
5. アクションアイテムの追加・更新時は構造化されたデータで提案する

【編集可能な操作】
- replace_text: 文字・単語・フレーズの置換
- add_action_item: 新しいアクションアイテムの追加
- update_action_item: 既存アクションアイテムの更新
- add_content: 内容の追記・補強
- restructure: 構成・見出しの改善

【回答フォーマット - 質問の場合】
回答: [具体的な回答内容]
引用: "[該当する文字起こしの部分]"

【回答フォーマット - 編集指示の場合】
編集内容: [編集の概要説明]
提案アクション: [具体的な編集アクション]
確認: この編集を実行してよろしいですか？
"""

EDIT_SYSTEM_PROMPT = """
ユーザーからの編集指示を解析し、議事録に対する具体的な編集アクションを生成してください。

【編集指示の例】
- "プロジェクトXをプロジェクトAlphaに修正して"
- "田中さんに資料作成のタスクを追加、期限は来週金曜日"
- "タスクBの担当者を佐藤さんから山田さんに変更"

【出力形式】
JSON形式で編集アクションのリストを返してください。
{
  "edit_actions": [
    {
      "action_type": "replace_text",
      "target": "プロジェクトX",
      "replacement": "プロジェクトAlpha",
      "scope": "all"
    }
  ],
  "explanation": "編集内容の説明"
}
"""

CHAT_USER_PROMPT = """
【これまでの会話履歴】
{chat_history}

【新しい質問】
{user_question}
"""
```

## セキュリティ・パフォーマンス

### セキュリティ対策

1. **入力検証**: XSS攻撃対策、入力長制限
2. **レート制限**: 1ユーザーあたりの質問数制限（10回/分）
3. **セッション管理**: 6時間でセッション自動削除
4. **データ保護**: チャット履歴の暗号化保存

### パフォーマンス最適化

1. **トークン管理**: 
   - コンテキスト最大8000トークン
   - 超過時は古い履歴を削除
2. **キャッシュ**: よくある質問の回答キャッシュ
3. **非同期処理**: AI回答生成中のUI応答性確保
4. **バックグラウンド削除**: 期限切れセッションの自動削除

## 運用・監視

### ログ・監視項目

1. **利用統計**
   - 質問数/日
   - 平均応答時間
   - トークン使用量
2. **エラー監視**
   - API失敗率
   - タイムアウト発生率
3. **品質指標**
   - ユーザー満足度（フィードバック機能）
   - 引用精度

### コスト管理

- **OpenAI API**: GPT-4使用料金
- **推定コスト**: 1回答あたり約$0.03-0.10
- **月次上限**: ユーザーあたり$20/月

## 実装フェーズ

### フェーズ1: 基本機能（2週間）

- [ ] バックエンドAPI実装
- [ ] フロントエンドチャットUI
- [ ] 基本的な質問応答機能

### フェーズ2: 編集機能実装（2週間）

- [ ] 編集インテント解析機能
- [ ] 議事録編集API実装
- [ ] 編集モード切り替えUI
- [ ] 編集確認ダイアログ
- [ ] リアルタイム議事録更新

### フェーズ3: 高度な編集機能（1週間）

- [ ] 編集履歴管理
- [ ] 編集取り消し機能
- [ ] 複雑な編集パターン対応
- [ ] アクションアイテム構造化編集

### フェーズ4: 機能拡張（1週間）

- [ ] 引用機能
- [ ] チャット履歴保存
- [ ] セッション管理
- [ ] バッチ編集機能

### フェーズ5: 改善・最適化（1週間）

- [ ] UI/UX改善
- [ ] パフォーマンス最適化
- [ ] エラーハンドリング強化
- [ ] 編集精度向上

### フェーズ6: 監視・運用（継続）

- [ ] ログ・監視体制
- [ ] フィードバック収集
- [ ] 継続改善
- [ ] 編集パターン学習

## 成功指標

### 質問応答機能

1. **利用率**: 議事録閲覧者の30%以上がチャット機能を利用
2. **満足度**: ユーザー評価4.0/5.0以上
3. **効率性**: 平均応答時間3秒以下
4. **精度**: 引用の関連性90%以上

### 編集機能

1. **編集利用率**: チャット利用者の50%以上が編集機能を使用
2. **編集精度**: 編集インテント解析精度95%以上
3. **編集完了率**: 提案された編集の80%以上が実行される
4. **エラー率**: 編集実行時のエラー率5%以下
5. **時間削減**: 手動編集と比較して70%の時間短縮

## リスク・課題

### 技術リスク
- **API制限**: OpenAI APIの利用制限・価格変動
- **精度**: 長い文字起こしでの文脈理解精度
- **パフォーマンス**: 大量同時利用時の応答性

### 対策
- **APIフォールバック**: 複数AI APIの併用検討
- **チャンク分割**: 長文の効率的な処理
- **キューイング**: 高負荷時のリクエスト管理

## 将来拡張

### 編集機能の高度化

1. **音声入力編集**: 音声での編集指示機能
2. **バッチ編集**: 複数の議事録への一括編集適用
3. **テンプレート編集**: よく使う編集パターンのテンプレート化
4. **AI学習**: ユーザーの編集パターン学習による提案精度向上

### 他機能との連携

1. **多言語対応**: 英語議事録への編集対応
2. **バージョン管理**: Git風の編集履歴・ブランチ機能
3. **協調編集**: 複数人での同時編集・コメント機能
4. **統合**: 他のツール（Slack、Teams）との編集連携

### 高度なAI機能

1. **予測編集**: 内容から必要な編集を自動提案
2. **品質チェック**: 編集後の議事録品質自動評価
3. **カスタムルール**: 組織固有の編集ルール学習
4. **自動リライト**: 読みやすさ向上のための自動文章改善