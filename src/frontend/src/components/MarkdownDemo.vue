<template>
  <div class="markdown-demo">
    <Card>
      <template #title>
        <div class="demo-header">
          <i class="pi pi-file"></i>
          議事録マークダウン表示デモ
        </div>
      </template>
      
      <template #content>
        <MarkdownRenderer 
          :content="sampleMarkdown"
          :show-toc="true"
          @word-count="onWordCount"
        />
        
        <div class="demo-info">
          <p><strong>文字数:</strong> {{ wordCount }}文字</p>
          <p><strong>機能:</strong> マークダウン形式の議事録を美しくフォーマット表示</p>
        </div>
      </template>
    </Card>
  </div>
</template>

<script>
import { ref } from 'vue'
import Card from 'primevue/card'
import MarkdownRenderer from './MarkdownRenderer.vue'

export default {
  name: 'MarkdownDemo',
  components: {
    Card,
    MarkdownRenderer
  },
  setup() {
    const wordCount = ref(0)
    
    const sampleMarkdown = `# 会議議事録

**日時:** 2024年1月15日 14:00-15:30
**参加者:** 山田太郎、佐藤花子、田中次郎
**場所:** 会議室A

## 討議内容

### 1. プロジェクト進捗報告

#### 開発チーム
- **フロントエンド**: Vue.js 3の導入が完了
- **バックエンド**: FastAPI のAPI設計が8割完了
- **インフラ**: Renderでのデプロイ環境構築中

#### 課題
- データベース設計の見直しが必要
- セキュリティ要件の詳細化

### 2. 今後のスケジュール

| 項目 | 担当者 | 期限 |
|------|--------|------|
| UI/UXデザイン | 佐藤 | 1/20 |
| API実装 | 田中 | 1/25 |
| テスト実装 | 山田 | 1/30 |

### 3. 決定事項

1. **技術スタック確定**
   - フロントエンド: Vue.js 3 + PrimeVue
   - バックエンド: FastAPI + SQLAlchemy
   - データベース: PostgreSQL

2. **開発フロー**
   - GitHubフロー採用
   - PR時の自動テスト実行
   - 週次デプロイ

### 4. アクションアイテム

- [ ] データベース設計書の更新（田中、1/18まで）
- [ ] セキュリティ要件書の作成（山田、1/20まで）
- [ ] プロトタイプのデモ準備（佐藤、1/22まで）

## 次回会議

**日時:** 2024年1月22日 14:00-15:00
**議題:** プロトタイプデモ・セキュリティ要件確認

---

> この議事録は自動生成されたものです。内容に間違いがある場合は修正してください。

### コードサンプル

\`\`\`javascript
// Vue.js コンポーネントの例
export default {
  name: 'SampleComponent',
  data() {
    return {
      message: 'Hello World!'
    }
  },
  methods: {
    handleClick() {
      console.log('Button clicked')
    }
  }
}
\`\`\`

### 重要なポイント

> **注意:** このプロジェクトは機密情報を含むため、*外部への共有は禁止*されています。

### リンク

詳細な仕様書は[こちら](https://example.com/specs)をご確認ください。

**この議事録の承認者:** 山田太郎`

    const onWordCount = (count) => {
      wordCount.value = count
    }

    return {
      sampleMarkdown,
      wordCount,
      onWordCount
    }
  }
}
</script>

<style scoped>
.markdown-demo {
  max-width: 1000px;
  margin: 0 auto;
}

.demo-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #495057;
  font-size: 1.25rem;
}

.demo-info {
  margin-top: 2rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.demo-info p {
  margin: 0.5rem 0;
  color: #495057;
}
</style>