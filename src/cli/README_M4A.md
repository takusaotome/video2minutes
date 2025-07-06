# M4A音声ファイル処理スクリプト

長時間のM4AファイルをコンパクトなMP3ファイルに変換するためのコマンドラインスクリプトです。

## 機能

- M4Aファイルの詳細情報取得
- 目標ファイルサイズに基づく最適なビットレート自動計算
- MP3形式への変換（モノラル、16kHz、可変ビットレート）
- 変換前後の比較情報表示

## 前提条件

- Python 3.7以上
- ffmpegライブラリとffmpeg-pythonパッケージ
- ffmpegコマンドラインツール

### インストール

```bash
# ffmpegのインストール（macOS）
brew install ffmpeg

# ffmpegのインストール（Ubuntu）
sudo apt update
sudo apt install ffmpeg

# Pythonパッケージのインストール
pip install ffmpeg-python
```

## 使用方法

### 基本的な使用

```bash
# 基本的な変換（デフォルト設定: 15MB以下、128kbps以下）
python src/cli/process_m4a.py input.m4a

# 出力ファイル名を指定
python src/cli/process_m4a.py input.m4a -o compressed.mp3
```

### オプション指定

```bash
# 最大ファイルサイズを10MBに設定
python src/cli/process_m4a.py input.m4a --max-size 10

# 最大ビットレートを64kbpsに設定
python src/cli/process_m4a.py input.m4a --max-bitrate 64

# 最小ビットレートを16kbpsに設定（長時間音声用）
python src/cli/process_m4a.py input.m4a --min-bitrate 16

# 複数のオプションを組み合わせ
python src/cli/process_m4a.py input.m4a -o output.mp3 --max-size 15 --max-bitrate 96 --min-bitrate 12
```

### ヘルプ表示

```bash
python src/cli/process_m4a.py --help
```

## 出力例

```
入力ファイル: recording.m4a
出力ファイル: recording.mp3
入力ファイル情報:
  時間: 1800.0秒 (30.0分)
  サイズ: 23.4MB
  コーデック: aac
  サンプリングレート: 44100Hz
  チャンネル数: 2
  ビットレート: 128000bps
ビットレート計算:
  計算値: 68.3kbps
  最終値: 68kbps (制限: 8-128kbps)
  予想ファイルサイズ: 14.98MB
使用ビットレート: 68kbps
実行コマンド: ffmpeg -i recording.m4a -b:a 68k -ac 1 -acodec libmp3lame -ar 16000 -y recording.mp3
変換完了

出力ファイル情報:
  サイズ: 14.8MB
  圧縮率: 36.8%
  コーデック: mp3
  サンプリングレート: 16000Hz
  チャンネル数: 1

✅ 変換完了: recording.mp3
```

## 変換仕様

- **出力形式**: MP3
- **サンプリングレート**: 16kHz（Whisper AI推奨）
- **チャンネル数**: 1（モノラル）
- **ビットレート**: 自動計算（8-128kbps、デフォルト最小値: 8kbps）
- **エンコーダー**: libmp3lame

## OpenAI Whisper API制限について

このスクリプトはOpenAI Whisper APIでの使用を想定して設計されています。

### ファイルサイズ制限

- **公式制限**: 25MB
- **実用的な制限**: 15-16MB（推奨）
- **このスクリプトのデフォルト**: 15MB

**注意**: 公式には25MBまでサポートされていますが、実際には20MB以上のファイルで400エラーが発生するケースが報告されています。安全のため、15MBを上限として設定しています。

### 対応ファイル形式

Whisper APIは以下の形式をサポートしています：
- m4a, mp3, webm, mp4, mpga, wav, mpeg, flac, ogg

### 推奨設定

長時間録音の場合は以下の設定を推奨します：

```bash
# 長時間録音用（より小さなサイズ制限、低ビットレート）
python3 src/cli/process_m4a.py input.m4a --max-size 10 --max-bitrate 64 --min-bitrate 12

# 非常に長時間録音用（1時間以上）
python3 src/cli/process_m4a.py input.m4a --max-size 8 --max-bitrate 48 --min-bitrate 8

# 短時間・高品質用
python3 src/cli/process_m4a.py input.m4a --max-size 15 --max-bitrate 96
```

## トラブルシューティング

### ffmpegが見つからない場合

```bash
# ffmpegのインストール確認
ffmpeg -version

# パスの確認
which ffmpeg
```

### ファイルサイズが目標を超える場合

スクリプトが以下の警告を表示する場合：

```
⚠️ 警告: 予想サイズ(23.83MB)が目標サイズ(10MB)を超過しています
     目標サイズを達成するには13.1kbpsが必要です
```

これは長時間の音声ファイルで小さなサイズ制限を設定した場合に発生します。解決策：

1. **最小ビットレートを下げる**:
   ```bash
   python src/cli/process_m4a.py input.m4a --max-size 10 --min-bitrate 8
   ```

2. **より小さなサイズ制限を諦める**:
   ```bash
   python src/cli/process_m4a.py input.m4a --max-size 20
   ```

3. **音声を分割する**（手動で短い区間に分割）

### メモリ不足エラーの場合

大きなファイルを処理する際にメモリ不足が発生する場合は、より小さなファイルサイズ制限を設定してください：

```bash
python src/cli/process_m4a.py input.m4a --max-size 5 --max-bitrate 32
```

## 開発者向け情報

このスクリプトは `src/backend/app/services/video_processor.py` の機能を参考に、M4Aファイル専用として開発されました。将来的にはメインのVideoProcessorクラスに統合される予定です。 