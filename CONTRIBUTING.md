# 🤝 コントリビューションガイドライン

このリポジトリへの貢献を歓迎します。プルリクエストを送る前に、以下の手順に従って開発環境を整え、テストと静的解析を実行してください。
バグ報告や機能提案はまず [Issues](https://github.com/takusaotome/video2minutes/issues) でご相談ください。

## 基本的な流れ
1. リポジトリを fork してローカルに clone します。
2. ブランチを作成し変更を加えてください。
3. `npm run test:all` と `./static-analysis.sh` を実行し、問題がないか確認します。
4. Pull Request を作成してお知らせください。

気軽に参加していただけると嬉しいです。

## 🛠 開発環境のセットアップ

### Python
1. Python 3.9 以上をインストールします。
2. 仮想環境を作成して依存関係をインストールします。
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Node.js
1. Node.js 18 以上を推奨します。
2. 依存関係をまとめてインストールします。
   ```bash
   npm run install:all
   ```

## ✅ テスト実行方法

全てのテストを実行するには以下を使用します。
```bash
npm run test:all
```
個別のテストスクリプトも用意されています。
- Python 単体テスト: `npm run test:unit-python`
- JavaScript 単体テスト: `npm run test:unit-js`
- E2E テスト: `npm run test:e2e`

テストの詳細については [tests/README.md](tests/README.md) を参照してください。

## 🚀 PR 作成時のルール
1. 変更点に対するテストを追加し、全テストがパスすることを確認してください。
2. `./static-analysis.sh` もしくは `npm run static-analysis` を実行し、lint / 静的解析を通してください。
3. 1 つの PR では 1 つの機能・修正に絞り、分かりやすい説明を添えてください。
4. CI で失敗しないことを確認してから PR を作成してください。

皆さまの貢献をお待ちしています！