# 議事録チャット機能 設計書

## 概要

議事録詳細画面に対話型チャット機能を追加し、文字起こし全文をコンテキストとして活用したAI質問応答システムを実装する。

## 機能要件

### 基本機能
- **文字起こし内容に基づく質問応答**: 会議内容に関する質問に対して文字起こし全文を参照して回答
- **チャット履歴保存**: セッション中のやり取りを保持
- **コンテキスト理解**: 前回の質問・回答を踏まえた継続的な対話
- **引用表示**: 回答時に参照した文字起こしの該当箇所を表示

### 想定ユースケース
1. **決定事項の確認**: "この会議でXXについてどんな結論になりましたか？"
2. **担当者の確認**: "タスクAの担当者は誰になりましたか？"
3. **期限の確認**: "プロジェクトの納期はいつでしたっけ？"
4. **詳細説明**: "XXについてもう少し詳しく教えてください"
5. **要約**: "今日の会議のポイントを3つ教えてください"

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
  "message_type": "user"
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
  "tokens_used": 450
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
    timestamp: datetime
    citations: List[Citation]
    tokens_used: int
    processing_time: float

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

以下の会議内容に基づいて、ユーザーの質問に正確かつ有用な回答を提供してください。

【会議の文字起こし】
{transcription}

【生成された議事録】
{minutes}

【回答時の注意点】
1. 文字起こしや議事録の内容に基づいて回答する
2. 内容にない情報は推測しない
3. 不明な点は「文字起こしからは確認できません」と正直に答える
4. 回答時は該当する文字起こしの部分を引用する
5. 日本語で分かりやすく回答する
6. 前回の質問・回答の文脈も考慮する

【回答フォーマット】
回答: [具体的な回答内容]
引用: "[該当する文字起こしの部分]"
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
          <ChatInput 
            @send-message="handleSendMessage"
            :disabled="isLoading"
            placeholder="会議内容について質問してください..."
          />
        </div>
        
        <!-- 使用状況 -->
        <div class="chat-usage">
          <small>
            質問数: {{ messages.length }} / トークン: {{ totalTokens }}
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
      isLoading: false,
      totalTokens: 0,
      highlightedText: null
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

### フェーズ2: 機能拡張（1週間）
- [ ] 引用機能
- [ ] チャット履歴保存
- [ ] セッション管理

### フェーズ3: 改善・最適化（1週間）
- [ ] UI/UX改善
- [ ] パフォーマンス最適化
- [ ] エラーハンドリング強化

### フェーズ4: 監視・運用（継続）
- [ ] ログ・監視体制
- [ ] フィードバック収集
- [ ] 継続改善

## 成功指標

1. **利用率**: 議事録閲覧者の30%以上がチャット機能を利用
2. **満足度**: ユーザー評価4.0/5.0以上
3. **効率性**: 平均応答時間3秒以下
4. **精度**: 引用の関連性90%以上

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

1. **音声入力**: 音声での質問機能
2. **多言語対応**: 英語議事録への対応
3. **学習機能**: ユーザーフィードバックからの改善
4. **統合**: 他のツール（Slack、Teams）との連携