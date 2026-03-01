---
description: 動画ファイルから文字起こしと議事録を自動生成
allowed-tools: Bash(python3:*), Bash(source:*), Bash(cat:*), Bash(ls:*)
argument-hint: <動画パス> --date <YYYY-MM-DD> --attendees <参加者>
---

# Video2Minutes - 動画から議事録生成

動画ファイルから文字起こしと議事録を自動生成します。

## 処理フロー

1. 音声抽出（FFmpeg）→ 文字起こし（Whisper API）→ 議事録生成（GPT-4.1）

## 実行コマンド

```bash
cd ~/PycharmProjects/video2minutes && source venv/bin/activate && python src/cli/video2minutes.py -i $ARGUMENTS
```

## 処理完了後

生成されたファイルを読み取って、ユーザーに以下を報告してください：

### 1. 文字起こし全文

```bash
ls -t ~/PycharmProjects/video2minutes/transcript/*.txt 2>/dev/null | head -1 | xargs cat
```

### 2. 議事録

```bash
ls -t ~/PycharmProjects/video2minutes/minutes/*.md 2>/dev/null | head -1 | xargs cat
```

## 使用例

```
/video2minutes ~/Downloads/meeting.mp4 --date 2025-12-25 --attendees "田中, 佐藤"
/video2minutes meeting.mp4 --date 2025-12-25 --attendees "A様, B様" --meeting-name "キックオフ"
/video2minutes meeting.mp4 --date 2025-12-25 --attendees "A様, B様" --context "本会議はXYZプロジェクトのフェーズ2開始に向けたキックオフ。クライアントはABC社。"
```

## オプション

- `--date` (必須): 会議日（YYYY-MM-DD）
- `--attendees` (必須): 参加者リスト
- `--meeting-name`: 会議名（デフォルト: ファイル名）
- `--context`: 会議の背景・コンテキスト（プロジェクト情報、目的、特別な指示など）
- `--model`: GPTモデル（デフォルト: gpt-4.1）
- `--language`: 言語コード（デフォルト: ja）
