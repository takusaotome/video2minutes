# 議事録チャット機能 設計書

## 概要

議事録詳細画面に対話型チャット機能を追加し、文字起こし全文をコンテキストとして活用したAI質問応答システムを実装する。

## 機能要件

### 基本機能

#### 質問応答機能
- **文字起こし内容に基づく質問応答**: 会議内容に関する質問に対して文字起こし全文を参照して回答
- **チャット履歴保存**: セッション中のやり取りを保持
- **コンテキスト理解**: 前回の質問・回答を踏まえた継続的な対話
- **引用表示**: 回答時に参照した文字起こしの該当箇所を表示

#### 議事録編集機能
- **誤字・脱字修正**: 間違った単語や表現の一括修正
- **アクションアイテム追加・編集**: 漏れていたタスクの追加や詳細情報の更新
- **内容補強**: 不足している情報の追記や詳細化
- **構造化改善**: 議事録の構成や見出しの最適化
- **リアルタイム反映**: 編集内容の即座画面更新

### 想定ユースケース

#### 質問応答
1. **決定事項の確認**: "この会議でXXについてどんな結論になりましたか？"
2. **担当者の確認**: "タスクAの担当者は誰になりましたか？"
3. **期限の確認**: "プロジェクトの納期はいつでしたっけ？"
4. **詳細説明**: "XXについてもう少し詳しく教えてください"
5. **要約**: "今日の会議のポイントを3つ教えてください"

#### 議事録編集
1. **誤字修正**: "議事録内の'プロジェクトX'を'プロジェクトAlpha'に修正して"
2. **アクションアイテム追加**: "田中さんに資料作成のタスクを追加して、期限は来週金曜日"
3. **担当者修正**: "タスクBの担当者を佐藤さんから山田さんに変更して"
4. **期限更新**: "システム改修タスクの期限を2月末に延期して"
5. **内容補強**: "決定事項に予算承認の件を追加して"
6. **優先度設定**: "セキュリティ対応タスクを高優先度に変更して"

## システム設計

### アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   フロントエンド   │    │   バックエンド     │    │   OpenAI API    │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │チャットコンポ│ │◄──►│ │チャットAPI  │ │◄──►│ │ GPT-4       │ │
│ │ーネント      │ │    │ │             │ │    │ │             │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │                 │
│ │議事録詳細    │ │    │ │セッション   │ │    │                 │
│ │コンポーネント│ │    │ │ストレージ   │ │    │                 │
│ └─────────────┘ │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### データフロー

1. **初期化**
   - 議事録詳細画面で文字起こし全文を取得
   - チャットセッションを初期化
   - 文字起こし内容をコンテキストとして設定

2. **質問処理**
   - ユーザーの質問を受信
   - チャット履歴と文字起こし内容を組み合わせてプロンプト生成
   - OpenAI APIに送信

3. **回答生成**
   - AI回答を受信
   - 引用箇所があれば該当部分をハイライト
   - チャット履歴に追加して表示

## 実装仕様

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

### フロントエンド

#### コンポーネント構成

```
MinutesView.vue
├── LeftPanel.vue (新規 - 文字起こし+チャット統合パネル)
│   ├── TranscriptionSection.vue (既存を改修)
│   ├── ResizeHandle.vue (新規)
│   └── ChatSection.vue (新規)
│       ├── ChatMessages.vue
│       ├── ChatInput.vue
│       └── CitationHighlight.vue
└── MinutesContent.vue (既存)
```

#### LeftPanel.vue 設計

```vue
<template>
  <div class="left-panel">
    <!-- 文字起こしセクション -->
    <div class="transcription-section" :style="{ height: transcriptionHeight }">
      <TranscriptionSection 
        :transcription="transcription"
        :highlighted-text="highlightedText"
        @text-select="handleTextSelect"
      />
    </div>
    
    <!-- リサイズハンドル -->
    <ResizeHandle 
      @resize="handleResize"
      :min-height="200"
      :max-height="600"
    />
    
    <!-- チャットセクション -->
    <div class="chat-section" :style="{ height: chatHeight }">
      <div class="chat-header" @click="toggleChatCollapse">
        <h4>
          <i class="pi pi-comments"></i>
          会議内容について質問
        </h4>
        <Button 
          :icon="chatCollapsed ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          class="p-button-text p-button-sm"
        />
      </div>
      
      <div v-if="!chatCollapsed" class="chat-content">
        <!-- チャット履歴 -->
        <div class="chat-messages" ref="messagesContainer">
          <ChatMessages 
            :messages="messages" 
            :loading="isLoading"
            @citation-click="highlightTranscription"
          />
        </div>
        
        <!-- 入力エリア -->
        <div class="chat-input-area">
          <div class="input-mode-selector">
            <ToggleButton 
              v-model="isEditMode"
              onLabel="編集モード"
              offLabel="質問モード"
              onIcon="pi pi-pencil"
              offIcon="pi pi-question-circle"
            />
          </div>
          <ChatInput 
            @send-message="handleSendMessage"
            :disabled="isLoading"
            :placeholder="isEditMode ? '議事録の編集指示を入力してください...' : '会議内容について質問してください...'"
            :edit-mode="isEditMode"
          />
        </div>
        
        <!-- 編集履歴（編集モード時のみ） -->
        <div v-if="isEditMode && editHistory.length > 0" class="edit-history">
          <h5>編集履歴</h5>
          <div 
            v-for="edit in editHistory" 
            :key="edit.edit_id"
            class="edit-history-item"
          >
            <div class="edit-summary">{{ edit.changes_summary.join(', ') }}</div>
            <div class="edit-actions">
              <Button 
                label="取り消し"
                class="p-button-text p-button-sm"
                @click="revertEdit(edit.edit_id)"
                :disabled="edit.reverted"
              />
            </div>
          </div>
        </div>
        
        <!-- 使用状況 -->
        <div class="chat-usage">
          <small>
            質問数: {{ questionCount }} / 編集数: {{ editCount }} / トークン: {{ totalTokens }}
          </small>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      transcriptionHeight: '60%',
      chatHeight: '40%',
      chatCollapsed: false,
      messages: [],
      editHistory: [],
      isLoading: false,
      isEditMode: false,  // 質問モード/編集モード切り替え
      totalTokens: 0,
      highlightedText: null
    }
  },

  computed: {
    questionCount() {
      return this.messages.filter(m => m.intent === 'question').length
    },
    editCount() {
      return this.messages.filter(m => m.intent === 'edit_request').length
    }
  },
  
  methods: {
    handleResize({ transcriptionRatio, chatRatio }) {
      this.transcriptionHeight = `${transcriptionRatio * 100}%`
      this.chatHeight = `${chatRatio * 100}%`
    },
    
    toggleChatCollapse() {
      this.chatCollapsed = !this.chatCollapsed
      if (this.chatCollapsed) {
        this.transcriptionHeight = '100%'
        this.chatHeight = '40px'  // ヘッダーのみ
      } else {
        this.transcriptionHeight = '60%'
        this.chatHeight = '40%'
      }
    },
    
    highlightTranscription(citation) {
      this.highlightedText = citation.text
      // 3秒後にハイライト解除
      setTimeout(() => {
        this.highlightedText = null
      }, 3000)
    },

    async handleSendMessage(message) {
      const intent = this.isEditMode ? 'edit_request' : 'question'
      
      try {
        this.isLoading = true
        
        // メッセージ送信
        const response = await this.sendChatMessage(message, intent)
        
        if (intent === 'edit_request' && response.edit_actions.length > 0) {
          // 編集確認ダイアログ表示
          const confirmed = await this.confirmEdit(response.edit_actions)
          if (confirmed) {
            await this.executeEdit(response.message_id, response.edit_actions)
          }
        }
      } catch (error) {
        console.error('Chat message error:', error)
      } finally {
        this.isLoading = false
      }
    },

    async confirmEdit(editActions) {
      return new Promise((resolve) => {
        this.$confirm.require({
          message: `以下の編集を実行しますか？\n${editActions.map(a => a.description).join('\n')}`,
          header: '編集確認',
          acceptLabel: '実行',
          rejectLabel: 'キャンセル',
          accept: () => resolve(true),
          reject: () => resolve(false)
        })
      })
    },

    async executeEdit(messageId, editActions) {
      try {
        const response = await this.editMinutes(messageId, editActions)
        
        // 編集履歴に追加
        this.editHistory.unshift({
          edit_id: response.edit_id,
          changes_summary: response.changes_summary,
          timestamp: new Date(),
          reverted: false
        })
        
        // 議事録コンテンツを更新
        this.$emit('minutes-updated', response.updated_minutes)
        
        this.$toast.add({
          severity: 'success',
          summary: '編集完了',
          detail: `${response.changes_summary.length}件の変更を適用しました`,
          life: 3000
        })
      } catch (error) {
        this.$toast.add({
          severity: 'error',
          summary: '編集エラー',
          detail: error.message,
          life: 5000
        })
      }
    },

    async revertEdit(editId) {
      try {
        const response = await this.revertMinutesEdit(editId)
        
        // 編集履歴を更新
        const editIndex = this.editHistory.findIndex(e => e.edit_id === editId)
        if (editIndex !== -1) {
          this.editHistory[editIndex].reverted = true
        }
        
        // 議事録コンテンツを更新
        this.$emit('minutes-updated', response.reverted_minutes)
        
        this.$toast.add({
          severity: 'info',
          summary: '編集を取り消しました',
          life: 3000
        })
      } catch (error) {
        this.$toast.add({
          severity: 'error',
          summary: '取り消しエラー',
          detail: error.message,
          life: 5000
        })
      }
    }
  }
}
</script>
```

#### ChatMessages.vue 設計

```vue
<template>
  <div class="chat-messages-list">
    <div 
      v-for="message in messages" 
      :key="message.message_id"
      class="message-pair"
    >
      <!-- ユーザーメッセージ -->
      <div class="user-message">
        <div class="message-content">{{ message.message }}</div>
        <div class="message-time">{{ formatTime(message.timestamp) }}</div>
      </div>
      
      <!-- AI回答 -->
      <div class="assistant-message">
        <div class="message-content">
          {{ message.response }}
          
          <!-- 引用箇所 -->
          <div v-if="message.citations.length > 0" class="citations">
            <h5>参照箇所:</h5>
            <div 
              v-for="citation in message.citations"
              :key="citation.text"
              class="citation-item"
              @click="$emit('citation-click', citation)"
            >
              <blockquote>{{ citation.text }}</blockquote>
              <small v-if="citation.start_time">
                時刻: {{ citation.start_time }}
              </small>
            </div>
          </div>
        </div>
        <div class="message-time">{{ formatTime(message.timestamp) }}</div>
      </div>
    </div>
    
    <!-- ローディング -->
    <div v-if="loading" class="loading-message">
      <ProgressSpinner size="small" />
      <span>回答を生成中...</span>
    </div>
  </div>
</template>
```

### UI/UX設計

#### レイアウト

```
┌─────────────────────────────────────────────────────────────┐
│                     議事録詳細画面                            │
├─────────────────┬───────────────────────────────────────────┤
│                 │                                           │
│  文字起こし      │              議事録内容                    │
│  パネル(60%)    │                                           │
│                 │  ┌───────────────────────────────────┐   │
│ [文字起こし全文] │  │      構造化された議事録             │   │
│                 │  │                                   │   │
│ スクロール可能   │  │  1. 会議の目的                     │   │
│                 │  │  2. 議論内容                       │   │
├─────────────────┤  │  3. 決定事項                       │   │
│                 │  │  4. アクションアイテム               │   │
│ チャット機能     │  │                                   │   │
│    (40%)       │  └───────────────────────────────────┘   │
│                 │                                           │
│ ┌─────────────┐ │  ┌───────────────────────────────────┐   │
│ │Q: 結論は？   │ │  │  アクションアイテム一覧            │   │
│ │A: プロジェクト│ │  │  □ タスクA (田中) - 1/20期限      │   │
│ │  Aを...     │ │  │  □ タスクB (佐藤) - 1/25期限      │   │
│ ├─────────────┤ │  └───────────────────────────────────┘   │
│ │ [質問入力]   │ │                                           │
│ └─────────────┘ │  [Markdownダウンロード] [PDFエクスポート]  │
└─────────────────┴───────────────────────────────────────────┘
```

#### レイアウトの特徴

1. **上下分割型レイアウト**
   - 文字起こしパネルを上下に分割
   - 上部60%: 文字起こし全文表示
   - 下部40%: チャット機能
   - 境界線はドラッグでリサイズ可能

2. **文脈の連続性**
   - 文字起こしを読む → 疑問が生じる → すぐ下で質問
   - 自然な視線の流れを実現

3. **効率的なスペース活用**
   - 既存の空白スペースを有効活用
   - 画面幅を広げることなく機能追加
   - 2カラム構成を維持

#### インタラクション設計

1. **パネルリサイズ**
   ```javascript
   // ドラッグ可能な境界線
   const resizeHandle = {
     minChatHeight: 200,  // 最小200px
     maxChatHeight: 600,  // 最大600px
     defaultRatio: 0.4    // デフォルト40%
   }
   ```

2. **チャット展開/折りたたみ**
   - ヘッダーをクリックで折りたたみ可能
   - 折りたたみ時はチャットアイコンのみ表示
   - バッジで未読メッセージ数を表示

3. **引用連携**
   - チャット内の引用をクリック
   - 文字起こしパネルの該当箇所へ自動スクロール
   - ハイライト表示（3秒間）

#### レスポンシブ対応

- **デスクトップ（1200px以上）**: 2カラム＋上下分割レイアウト
- **タブレット（768px-1199px）**: 
  - 横向き: デスクトップと同じ
  - 縦向き: 文字起こし/チャットをタブ切り替え
- **スマホ（767px以下）**: 
  - アコーディオン形式
  - 議事録 → 文字起こし → チャットの順

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