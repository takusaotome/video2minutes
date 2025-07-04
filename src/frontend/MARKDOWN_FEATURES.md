# マークダウン表示機能

Video2Minutesでは、生成された議事録をマークダウン形式で美しく表示できます。

## 🌟 主要機能

### ✅ 実装済み機能

1. **フォーマット対応**
   - 見出し（H1-H6）
   - 段落・改行
   - **太字**・*斜体*
   - リスト（箇条書き・番号付き）
   - テーブル
   - 引用文
   - 水平線
   - リンク（外部リンク自動検出）

2. **コードハイライト**
   - インラインコード: `const example = 'code'`
   - コードブロック（シンタックスハイライト付き）
   - コピーボタン付き
   - 40+言語対応

3. **目次自動生成**
   - 見出しから自動生成
   - スムーズスクロール
   - ハイライト表示

4. **セキュリティ**
   - XSS攻撃防止（DOMPurify使用）
   - 安全なHTMLサニタイゼーション

## 🛠️ 技術仕様

### 使用ライブラリ

- **marked**: マークダウンパーサー
- **DOMPurify**: HTMLサニタイゼーション
- **highlight.js**: シンタックスハイライト

### コンポーネント構成

```
MarkdownRenderer.vue
├── 目次表示（Card）
├── メインコンテンツ（Card）
└── マークダウンスタイル（CSS）
```

### API

```javascript
// 基本的な使用方法
<MarkdownRenderer 
  :content="markdownText"
  :show-toc="true"
  @word-count="handleWordCount"
/>
```

## 🎨 スタイル特徴

### デザインシステム

- **カラーパレット**: PrimeVueテーマに統一
- **タイポグラフィ**: 日本語最適化フォント
- **レスポンシブ**: PC・タブレット・スマホ対応

### 特別なスタイリング

1. **見出し**: グラデーション下線付き
2. **引用文**: 左側アクセントバー
3. **コードブロック**: ダークテーマ
4. **テーブル**: ホバー効果付き
5. **リンク**: 外部リンクアイコン付き

## 📱 レスポンシブ対応

- **PC（1024px+）**: サイドバー目次 + メインコンテンツ
- **タブレット（768-1024px）**: 縦積みレイアウト
- **スマホ（768px以下）**: モバイル最適化

## 🔧 使用例

### 基本的な議事録

```markdown
# 会議議事録

**日時:** 2024年1月15日
**参加者:** 山田、佐藤、田中

## 討議内容

### 進捗報告
- [ ] タスク1（完了）
- [ ] タスク2（進行中）

### 決定事項
> 重要な決定事項はこのように表示されます

### コード例
\`\`\`javascript
const result = await api.fetchData()
\`\`\`
```

### 表示結果

- 美しくフォーマットされた見出し
- カラフルなシンタックスハイライト
- インタラクティブな目次
- コピー可能なコードブロック

## 🚀 パフォーマンス

- **初期ロード**: ~50kb（gzip圧縮後）
- **レンダリング**: 1000文字未満で瞬時
- **メモリ使用量**: 軽量（最適化済み）

## 🔜 今後の拡張予定

1. **エクスポート機能強化**
   - PDF生成（styled-components使用）
   - Word文書出力
   - PowerPoint出力

2. **編集機能**
   - インライン編集
   - プレビューモード
   - バージョン管理

3. **コラボレーション**
   - コメント機能
   - 変更履歴
   - 承認ワークフロー

## 📚 開発者向け情報

### カスタマイズ

```javascript
// マークダウンレンダラーのカスタマイズ
import { parseMarkdown } from '@/utils/markdown'

const customOptions = {
  enableSyntaxHighlight: true,
  sanitize: true,
  breaks: true
}

const html = parseMarkdown(markdown, customOptions)
```

### スタイルカスタマイズ

```css
/* グローバルマークダウンスタイルの上書き */
.markdown-content .markdown-h1 {
  color: #custom-color;
  font-size: 2.5rem;
}
```

この機能により、Video2Minutesで生成される議事録は、従来のプレーンテキストよりもはるかに読みやすく、プロフェッショナルな外観を持つことができます。