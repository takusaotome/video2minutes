# 🎬 Video2Minutes - AI議事録自動生成ツール

動画ファイルから自動的に文字起こしを行い、AI議事録を生成するWebアプリケーションです。会議録画から議事録作成までの作業を大幅に効率化できます。

## 🌟 主要機能

- **📤 動画アップロード**: ドラッグ&ドロップ対応、最大5GB
- **🎙️ 自動文字起こし**: OpenAI Whisper APIによる高精度音声認識
- **📝 AI議事録生成**: GPT-4による戦略コンサル視点の議事録作成
- **✅ アクションアイテム抽出**: 担当者・期限・重要度の自動判定
- **📊 リアルタイム進捗**: WebSocketによる処理状況の即座更新
- **📱 レスポンシブ対応**: PC・タブレット・スマホ全対応

## 🔗 アクセス情報

### 🌐 本番環境URL
**https://video2minutes.onrender.com/**

### 🔐 認証情報
- **現在**: ベーシック認証実装済み
- **将来**: Googleアカウント認証実装予定（より便利なアクセス）

## 💡 使い方

### 1️⃣ ファイルアップロード
1. 動画ファイル（MP4, MOV, AVI等）をドラッグ&ドロップ
2. または「ファイルを選択」ボタンからアップロード
3. リアルタイム進捗バーで処理状況を確認

### 2️⃣ 処理完了まで待機
- **文字起こし**: 10分動画で約2-3分
- **議事録生成**: 追加で1-2分
- **WebSocket**: 自動更新でブラウザ更新不要

### 3️⃣ 議事録確認・活用
- **サイドバー**: 文字起こし全文表示
- **メイン**: 構造化された議事録
- **アクションアイテム**: 担当者・期限付きタスク一覧
- **ダウンロード**: Markdown形式でエクスポート

## 🎯 活用シーン

- **📅 定例会議**: 週次・月次ミーティングの議事録作成
- **🤝 商談記録**: クライアント打ち合わせの要点整理
- **💼 プロジェクト会議**: 決定事項・アクションアイテムの明確化
- **📚 研修・セミナー**: 学習内容の要点まとめ
- **🔍 インタビュー**: ヒアリング内容の構造化

## 🛡️ 制限事項

- **ファイルサイズ**: 最大5GB
- **処理時間**: 最大2時間（タイムアウト）
- **データ保持**: 処理完了後24時間で自動削除
- **機密情報**: 重要な会議は事前に社内ガイドライン確認

## 🚀 今後の予定

- **🔐 認証機能**: Googleアカウント認証導入
- **🔗 タスク管理連携**: 抽出されたアクションアイテムの自動タスク登録
- **📈 分析機能**: 会議時間・参加者分析
- **🌍 多言語対応**: 英語等の議事録生成
- **📱 モバイルアプリ**: iOS/Android対応

## 🏗️ プロジェクト構成

```
video2minutes/
├── src/
│   ├── backend/          # FastAPI バックエンド
│   ├── frontend/         # Vue.js フロントエンド
│   └── cli/              # コマンドライン版ツール
├── docs/                 # ドキュメント
├── tests/                # テストファイル
└── README.md            # このファイル
```

## 🛠️ 開発者向け情報

### 技術スタック
- **フロントエンド**: Vue.js 3 + PrimeVue + Vite
- **バックエンド**: FastAPI + Python 3.9+
- **AI**: OpenAI Whisper + GPT-4
- **インフラ**: Render（PaaS）
- **リアルタイム**: WebSocket通信

### ローカル開発環境

#### バックエンド
```bash
pip install -r requirements.txt
cd src/backend
uvicorn app.main:app --reload
```
Render へのデプロイ時には `src/backend/requirements.txt` が読み込まれますが、この
ファイルはルートの `requirements.txt` を参照するだけの薄いラッパーです。ローカル
環境でも同じ依存関係を利用できます。

#### フロントエンド
```bash
cd src/frontend
npm install
npm run dev
```

### テストの実行
依存関係をインストールしてからテストを実行します。
```bash
pip install -r requirements.txt
npm run install:all
npm run test:all
```

### 依存関係のインストール

#### Python
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r src/backend/requirements.txt
```

#### Node.js
```bash
npm run install:all
```

### テスト実行
```bash
# Python単体テスト
npm run test:unit-python
# JavaScript単体テスト
npm run test:unit-js
# E2Eテスト
npm run test:e2e
```

### 静的解析
開発用ツールをインストールした上で `static-analysis.sh` を実行できます。

```bash
# Python側ツールの例
pip install black isort flake8 mypy pylint bandit safety autopep8

# Node.js側ツールは依存関係インストール時に入ります
npm run static-analysis
```

### CLI版ツール
コマンドライン版も利用可能です。詳細は [src/cli/README.md](src/cli/README.md) を参照してください。

## 📄 ライセンス

MIT Licenseの下で配布されています。[LICENSE](LICENSE)をご確認ください.

## 📚 詳細ドキュメント
- [ドキュメント総合案内](docs/README.md)
- [セキュリティガイド](docs/SECURITY.md)
- [デプロイメントセキュリティ設計](docs/DEPLOYMENT_SECURITY.md)
- [基本設計書](docs/DESIGN.md)
- [セッション管理設計書](docs/SESSION_MANAGEMENT_DESIGN.md)
- [議事録チャット機能設計書](docs/CHAT_FEATURE_DESIGN.md)
- [E2Eテストシナリオ](docs/E2E_TEST_SCENARIOS.md)
- [Slackメッセージテンプレート](docs/slack-message-template.md)
- [CONTRIBUTING ガイドライン](CONTRIBUTING.md)

## 📞 サポート・問い合わせ

- **GitHub**: [takusaotome/video2minutes](https://github.com/takusaotome/video2minutes)
- **Issues**: バグ報告・機能要望はGitHub Issuesまで

---

**💬 ぜひ実際の会議で試してみて、フィードバックをお聞かせください！** 
