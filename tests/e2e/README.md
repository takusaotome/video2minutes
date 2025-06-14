# E2E テスト自動化 - Playwright

## 概要

このディレクトリには、video2minutes WebアプリケーションのE2Eテスト自動化スクリプトが含まれています。Playwrightを使用して、設計資料に基づいた包括的なテストシナリオを実装しています。

## テストファイル構成

```
tests/e2e/
├── README.md                    # このファイル
├── fixtures/                   # テスト用ファイル
│   ├── test-video-small.mp4    # 小サイズ動画（1MB）
│   ├── test-video-medium.mp4   # 中サイズ動画（10MB）
│   ├── test-japanese-名前.mp4   # 日本語ファイル名テスト用
│   └── test-invalid-file.txt   # 無効ファイル形式テスト用
├── utils/
│   └── test-helpers.js         # テストヘルパー関数
├── basic-flow.spec.js          # 基本機能テスト
├── parallel-processing.spec.js  # 並行処理テスト
├── error-handling.spec.js      # エラーハンドリングテスト
├── ui-interaction.spec.js      # UIインタラクション・レスポンシブテスト
├── global-setup.js             # グローバルセットアップ
└── global-teardown.js          # グローバルティアダウン
```

## セットアップ

### 1. 依存関係インストール

```bash
# プロジェクトルートで実行
npm install

# Playwrightブラウザをインストール
npx playwright install
```

### 2. 環境変数設定

テスト実行前に、以下の環境変数を設定してください：

```bash
# .env ファイルに設定
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# オプション（デフォルト値が使用されます）
BASE_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000
```

### 3. バックエンド・フロントエンドサーバーの起動

テストは自動的にサーバーを起動しますが、手動で起動する場合：

```bash
# バックエンド（ターミナル1）
cd src/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# フロントエンド（ターミナル2）
cd src/frontend
npm run dev
```

## テスト実行

### 基本的な実行方法

```bash
# すべてのテストを実行
npm test

# ヘッドありモードで実行（ブラウザを表示）
npm run test:headed

# UIモードで実行（インタラクティブ）
npm run test:ui

# デバッグモードで実行
npm run test:debug
```

### カテゴリ別実行

```bash
# 基本機能テストのみ実行
npm run test:basic

# エラーハンドリングテストのみ実行
npm run test:error

# 並行処理テストのみ実行
npm run test:parallel

# レスポンシブテストのみ実行
npm run test:responsive
```

### 特定のブラウザで実行

```bash
# Chromiumのみ
npx playwright test --project=chromium

# Firefoxのみ
npx playwright test --project=firefox

# WebKitのみ
npx playwright test --project=webkit

# モバイルブラウザ
npx playwright test --project="Mobile Chrome"
```

## テストシナリオ詳細

### 1. 基本機能テスト (`basic-flow.spec.js`)

- **シナリオ1**: 単一動画ファイルの正常処理
- **シナリオ8**: レスポンシブデザイン確認
- WebSocket接続テスト
- パフォーマンス測定

### 2. 並行処理テスト (`parallel-processing.spec.js`)

- **シナリオ2**: 複数ファイルの並行処理
- **シナリオ11**: 同時アクセス負荷テスト
- 大量ファイル処理性能テスト
- WebSocket並行接続テスト

### 3. エラーハンドリングテスト (`error-handling.spec.js`)

- **シナリオ4**: 無効なファイル形式
- **シナリオ5**: ファイルサイズ制限超過
- **シナリオ6**: API制限・エラー時の処理
- **シナリオ7**: ネットワーク中断時の処理
- サーバー障害、タイムアウト、WebSocketエラー処理

### 4. UIインタラクション・レスポンシブテスト (`ui-interaction.spec.js`)

- **シナリオ8**: レスポンシブデザイン（7種類のビューポート）
- **シナリオ9**: ブラウザ互換性
- キーボードナビゲーション
- アクセシビリティ標準準拠
- テーマ切り替え、言語切り替え
- アニメーション・トランジション

## テストヘルパー機能

`utils/test-helpers.js` には以下の便利な機能が含まれています：

### 主要メソッド

- `uploadFile(fileName, options)` - ファイルアップロード
- `waitForTaskCompletion(taskId, timeout)` - タスク完了待機
- `getTaskStatus(taskId)` - タスクステータス取得
- `waitForProgress(taskId, minProgress)` - 進捗監視
- `monitorWebSocketConnection()` - WebSocket監視
- `checkToastNotification(message, type)` - トースト通知確認
- `testResponsiveLayout(viewport)` - レスポンシブ表示テスト
- `uploadMultipleFiles(fileNames)` - 複数ファイルアップロード
- `measurePerformance()` - パフォーマンス指標測定

### 使用例

```javascript
const { TestHelpers } = require('./utils/test-helpers');

test('基本テスト', async ({ page }) => {
  const helpers = new TestHelpers(page);
  
  // ファイルアップロード
  await helpers.uploadFile('test-video-small.mp4');
  
  // 完了まで待機
  const taskId = 'extracted-task-id';
  await helpers.waitForTaskCompletion(taskId, 5 * 60 * 1000);
  
  // トースト通知確認
  await helpers.checkToastNotification('処理完了', 'success');
});
```

## 設定とカスタマイズ

### playwright.config.js の主要設定

```javascript
{
  testDir: './tests/e2e',
  timeout: 5 * 60 * 1000,  // 5分タイムアウト
  globalTimeout: 30 * 60 * 1000,  // 30分グローバルタイムアウト
  retries: process.env.CI ? 2 : 0,  // CI環境でのリトライ
  workers: process.env.CI ? 1 : undefined,  // 並行実行数
}
```

### カスタマイゼーション

1. **タイムアウトの調整**: 長時間処理に対応するため、適切なタイムアウトを設定
2. **リトライ設定**: 不安定なテストに対するリトライ戦略
3. **ブラウザ設定**: テスト対象ブラウザとデバイスの選択
4. **レポート設定**: HTML, JSON, JUnit形式での結果出力

## トラブルシューティング

### よくある問題と解決方法

1. **タイムアウトエラー**
   ```bash
   # タイムアウト時間を延長
   npx playwright test --timeout=600000
   ```

2. **APIキー設定エラー**
   ```bash
   # 環境変数を確認
   echo $OPENAI_API_KEY
   echo $ANTHROPIC_API_KEY
   ```

3. **サーバー起動エラー**
   ```bash
   # ポートの確認
   lsof -i :5173
   lsof -i :8000
   ```

4. **モックファイル作成失敗**
   ```bash
   # 手動でfixturesディレクトリを作成
   mkdir -p tests/e2e/fixtures
   ```

### デバッグ方法

1. **ヘッドありモードでの実行**
   ```bash
   npm run test:headed
   ```

2. **特定のテストをデバッグ**
   ```bash
   npx playwright test --debug basic-flow.spec.js
   ```

3. **スクリーンショット・ビデオの確認**
   ```bash
   # test-results/ ディレクトリ内を確認
   open test-results/
   ```

4. **トレースの使用**
   ```bash
   npx playwright show-trace test-results/trace.zip
   ```

## CI/CD統合

### GitHub Actions での実行例

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm install
      
      - name: Install Playwright
        run: npx playwright install --with-deps
      
      - name: Run E2E tests
        run: npm test
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: test-results/
```

## パフォーマンス考慮事項

- **並行実行**: CI環境では workers: 1 を推奨
- **リソース使用量**: 大きな動画ファイルは事前に最適化
- **キャッシュ**: グローバルセットアップでのファイル作成
- **クリーンアップ**: テスト後の一時ファイル削除

## 拡張・メンテナンス

### 新しいテストシナリオの追加

1. 適切なspecファイルを選択または新規作成
2. `TestHelpers` クラスを活用
3. 適切なタグ（@basic, @error, @parallel等）を付与
4. 必要に応じてfixtureファイルを追加

### テストデータの管理

- `fixtures/` ディレクトリにテスト用ファイルを配置
- ファイルサイズと内容を適切に設定
- 実際の動画ファイルではなく、モックファイルを使用を推奨

## 関連ドキュメント

- [E2Eテストシナリオ設計書](../docs/E2E_TEST_SCENARIOS.md)
- [アプリケーション設計書](../docs/DESIGN.md)
- [Playwright公式ドキュメント](https://playwright.dev/)

## サポート

テスト実行に関する質問や問題がある場合は、以下を確認してください：

1. このREADMEファイル
2. テストシナリオ設計書
3. Playwrightの公式ドキュメント
4. プロジェクトのIssueトラッカー