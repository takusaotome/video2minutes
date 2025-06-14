# Video2Minutes テストスイート

## 概要

video2minutes アプリケーションの包括的なテストスイートです。以下の3種類のテストが含まれています：

```
tests/
├── unit/                # Python単体テスト (バックエンド)
├── unit-js/            # JavaScript単体テスト (フロントエンド)
├── e2e/                # E2Eテスト (Playwright)
├── integration/        # 統合テスト (将来用)
├── fixtures/           # 共通テストデータ
└── README.md          # このファイル
```

## クイックスタート

### 1. 全ての依存関係をインストール

```bash
npm run install:all
```

### 2. 全テストを実行

```bash
npm run test:all
```

### 3. 特定のテストのみ実行

```bash
# Python単体テスト
npm run test:unit-python

# JavaScript単体テスト
npm run test:unit-js

# E2Eテスト
npm run test:e2e
```

## テスト種別詳細

### 🐍 Python単体テスト (`tests/unit/`)

**対象**: FastAPIバックエンド、API、サービス層

**フレームワーク**: pytest + pytest-asyncio

**実行方法**:
```bash
# 仮想環境内で実行
source venv/bin/activate
python -m pytest tests/unit/ -v

# またはnpmスクリプト
npm run test:unit-python
```

**テスト内容**:
- API エンドポイント
- 設定管理
- エラーハンドリング
- ファイル処理
- ログ機能
- 動画プロセッサー
- 文字起こしサービス
- 議事録生成
- タスクキュー

**カバレッジ**: pytest-cov でHTMLレポート生成

### 🟨 JavaScript単体テスト (`tests/unit-js/`)

**対象**: Vue.js フロントエンド、コンポーネント、ストア、サービス

**フレームワーク**: Vitest + Vue Test Utils

**実行方法**:
```bash
cd tests/unit-js
npm test

# ウォッチモード
npm run test:watch

# カバレッジ付き
npm run test:coverage

# UI モード
npm run test:ui
```

**テスト内容**:
- Vue.js コンポーネント (FileUploader, TaskList, など)
- Pinia ストア (tasks.js)
- API サービス (api.js)
- WebSocket サービス
- ユーティリティ関数

**主要テストファイル**:
- `components/FileUploader.test.js` - ファイルアップロードコンポーネント
- `stores/tasks.test.js` - タスク管理ストア
- `services/api.test.js` - API通信サービス

### 🎭 E2Eテスト (`tests/e2e/`)

**対象**: 統合されたWebアプリケーション全体

**フレームワーク**: Playwright

**実行方法**:
```bash
npx playwright test

# ヘッド付きモード
npm run test:e2e:headed

# デバッグモード
npm run test:e2e:debug

# 特定シナリオ
npm run test:e2e:basic
npm run test:e2e:error
npm run test:e2e:parallel
npm run test:e2e:responsive
```

**テスト内容**:
- 基本的なファイルアップロード・処理フロー
- 複数ファイル並行処理
- エラーハンドリング
- UIインタラクション・レスポンシブ対応
- WebSocket リアルタイム更新
- クロスブラウザ対応

## テスト実行環境

### 必要なソフトウェア

- **Python**: 3.9+
- **Node.js**: 18+
- **FFmpeg**: 音声処理用

### 環境変数

```bash
# .env ファイルに設定
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# テスト環境用（オプション）
VITE_API_URL=http://localhost:8000
```

### ブラウザサポート

- Chromium
- Firefox  
- WebKit (Safari)
- Mobile Chrome
- Mobile Safari
- Microsoft Edge
- Google Chrome

## 詳細なテスト実行

### Python単体テスト

```bash
# 全テスト実行
python -m pytest tests/unit/ -v

# 特定のテストファイル
python -m pytest tests/unit/test_api_endpoints.py -v

# カバレッジ付き
python -m pytest tests/unit/ --cov=src/backend/app --cov-report=html

# マーカー指定
python -m pytest tests/unit/ -m "not slow"

# 失敗時のデバッグ
python -m pytest tests/unit/ -v --tb=long --pdb
```

### JavaScript単体テスト

```bash
cd tests/unit-js

# 全テスト実行
npm test

# 特定のテストファイル
npx vitest run components/FileUploader.test.js

# ウォッチモード（開発中）
npm run test:watch

# カバレッジレポート
npm run test:coverage

# UIモード（インタラクティブ）
npm run test:ui

# デバッグモード
npx vitest --reporter=verbose --run=false
```

### E2Eテスト

```bash
# 全ブラウザで実行
npx playwright test

# 特定ブラウザ
npx playwright test --project=chromium
npx playwright test --project=firefox

# 特定テストファイル
npx playwright test basic-flow.spec.js

# 特定シナリオ（grep）
npx playwright test --grep="ファイルアップロード"

# ヘッド付きモード（ブラウザ表示）
npx playwright test --headed

# デバッグモード（ステップ実行）
npx playwright test --debug

# UIモード（テスト選択・実行）
npx playwright test --ui

# レポート表示
npx playwright show-report
```

## テストデータとモック

### 共通テストデータ (`tests/fixtures/`)

```
fixtures/
├── sample-video.mp4      # テスト用動画ファイル
├── sample-audio.wav      # テスト用音声ファイル
├── sample-transcript.txt # テスト用文字起こし
└── sample-minutes.md     # テスト用議事録
```

### モック戦略

- **API呼び出し**: axios-mock-adapter, vi.mock()
- **ファイルシステム**: テンポラリディレクトリ
- **WebSocket**: モックサーバー
- **外部サービス**: OpenAI/Anthropic APIモック

## カバレッジレポート

### Python

```bash
python -m pytest tests/unit/ --cov=src/backend/app --cov-report=html
open htmlcov/index.html
```

### JavaScript

```bash
cd tests/unit-js
npm run test:coverage
open coverage/index.html
```

## CI/CD統合

### GitHub Actions

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Python tests
        run: npm run test:unit-python

  javascript-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run JavaScript tests
        run: npm run test:unit-js

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run E2E tests
        run: npm run test:e2e
```

## トラブルシューティング

### よくある問題

1. **Pythonテストでのimportエラー**
   ```bash
   # 仮想環境の確認
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **JavaScriptテストでのモジュールエラー**
   ```bash
   cd tests/unit-js
   npm install
   ```

3. **E2Eテストでのブラウザエラー**
   ```bash
   npx playwright install
   ```

4. **APIキー設定エラー**
   ```bash
   cp .env.example .env
   # APIキーを設定
   ```

### デバッグ方法

1. **Pythonテストデバッグ**
   ```bash
   python -m pytest tests/unit/test_example.py::test_function -v --pdb
   ```

2. **JavaScriptテストデバッグ**
   ```bash
   cd tests/unit-js
   npx vitest --reporter=verbose
   ```

3. **E2Eテストデバッグ**
   ```bash
   npx playwright test --debug
   npx playwright test --headed --slowMo=1000
   ```

## ベストプラクティス

### テスト作成

1. **命名規則**
   - テストファイル: `*.test.js`, `test_*.py`
   - テスト関数: `test_*`, `it('説明')`

2. **テスト構造**
   - Arrange（準備）
   - Act（実行）
   - Assert（検証）

3. **モック使用**
   - 外部依存性は必ずモック
   - APIキーは環境変数

4. **テスト分離**
   - 各テストは独立して実行可能
   - 共有状態は避ける

### パフォーマンス

1. **並行実行**
   - Pythonテスト: pytest-xdist
   - E2Eテスト: Playwright workers

2. **キャッシュ活用**
   - node_modules キャッシュ
   - pip キャッシュ

## 参考資料

- [Pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [Vue Test Utils](https://test-utils.vuejs.org/)
- [Playwright Documentation](https://playwright.dev/)
- [E2Eテストシナリオ設計書](../docs/E2E_TEST_SCENARIOS.md)