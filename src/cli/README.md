# Video2Minutes CLI Tool

コマンドライン版の議事録生成ツールです。

## 機能

- 動画ファイルから音声を抽出
- OpenAI Whisper APIを使用した文字起こし
- OpenAI GPT APIを使用した議事録の自動生成
- アクションアイテムの自動抽出と整理
- Markdown形式での議事録出力

## 必要条件

- Python 3.8以上
- FFmpeg
- OpenAI APIキー

## 使用するAIモデル

### 文字起こし（Whisper API）
- モデル: `whisper-1`
- 特徴:
  - 高精度な音声認識
  - 日本語を含む多言語対応
  - ノイズに強い
  - 話者の区別なし

### 議事録生成（Chat API）
- デフォルトモデル: `o3`（GPT-4.1）
- フォールバックモデル:
  1. `gpt-4.1`（優先）
  2. `gpt-4.1-mini`（バックアップ）
- 特徴:
  - 戦略系コンサルタントの視点で議事録を作成
  - アクションアイテムの自動抽出
  - 重要度の判定
  - 期限の推論
  - 決定事項の整理
  - 論点の構造化

> **注意**: モデルの選択は`--model`オプションで変更可能です。

## インストール

1. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```

2. OpenAI APIキーを設定:
```bash
# .envファイルを作成
echo "OPENAI_API_KEY=your-api-key" > .env
```

### OpenAI APIキーの取得方法

1. [OpenAI Platform](https://platform.openai.com/)にアクセス
2. アカウントを作成またはログイン
3. 右上のプロフィールアイコンをクリック
4. 「View API keys」を選択
5. 「Create new secret key」をクリック
6. APIキーをコピーし、`.env`ファイルに貼り付け

> **注意**: APIキーは秘密情報です。GitHubなどに公開しないよう注意してください。

## 使用方法

基本的な使用方法:
```bash
python video2minutes.py -i meeting.mp4 --date 2024-03-20 --attendees "田中, 佐藤, 鈴木"
```

### オプション

- `-i, --input`: 入力動画ファイル（必須）
- `--meeting-name`: 会議名（デフォルト: 入力ファイル名）
- `--date`: 会議日（YYYY-MM-DD形式、必須）
- `--attendees`: 出席者リスト（カンマ区切り、必須）
- `--transcript-dir`: 文字起こしファイルの出力ディレクトリ（デフォルト: transcript/）
- `--minutes-dir`: 議事録ファイルの出力ディレクトリ（デフォルト: minutes/）
- `--language`: 言語コード（デフォルト: ja）
- `--bitrate`: MP3ビットレート（デフォルト: 30kbps）
- `--model`: OpenAIモデル（デフォルト: o3）
- `--api-key`: OpenAI APIキー（環境変数/.envより優先）
- `--keep-audio`: 中間音声ファイルを保持

## 出力形式

生成される議事録は以下の形式で出力されます：

1. 会議情報
   - 会議名
   - 開催日
   - 出席者

2. アクションアイテム
   - タスク一覧（担当者、重要度、期限付き）

3. 議事内容の詳細
   - 決定事項
   - 主要議題と論点
   - 次回以降へのメモ

## 注意事項

- OpenAI APIの利用には料金が発生します
- 文字起こしの精度は音声の品質に依存します
- 機密情報を含む会議の録画には注意が必要です

## Webアプリケーション版

より使いやすいWebアプリケーション版も利用可能です：
- **URL**: https://video2minutes.onrender.com/
- **特徴**: ブラウザベース、リアルタイム進捗表示、ドラッグ&ドロップ対応 