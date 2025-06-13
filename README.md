# Video2Minutes

動画ファイルから自動的に文字起こしを行い、AI議事録を生成するツールです。

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

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/yourusername/video2minutes.git
cd video2minutes
```

2. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```

3. OpenAI APIキーを設定:
```bash
echo "OPENAI_API_KEY=your-api-key" > .env
```

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

## ライセンス

MIT License

## 注意事項

- OpenAI APIの利用には料金が発生します
- 文字起こしの精度は音声の品質に依存します
- 機密情報を含む会議の録画には注意が必要です 