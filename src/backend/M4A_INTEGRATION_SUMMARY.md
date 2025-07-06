# M4A音声ファイル処理機能統合完了

## 概要

100MB以上の大容量M4Aファイルから議事録を作成できるように、バックエンドシステムにM4A専用処理機能を統合しました。

## 実装された機能

### 1. 設定追加 (`src/backend/app/config.py`)

```python
# M4A処理専用設定
m4a_target_file_size_mb: int = 15  # Whisper API安全制限
m4a_max_bitrate: int = 128        # 最大ビットレート (kbps)
m4a_min_bitrate: int = 8          # 最小ビットレート (kbps) - 長時間音声対応
m4a_sample_rate: int = 16000      # サンプリングレート (Hz) - Whisper推奨
m4a_max_input_size_mb: int = 500  # 入力ファイル最大サイズ (MB)
m4a_compression_enabled: bool = True  # 自動圧縮の有効/無効
```

### 2. VideoProcessorクラス拡張 (`src/backend/app/services/video_processor.py`)

- `process_audio_file()`: 音声ファイル（M4A含む）の統合処理
- `_get_m4a_audio_info()`: M4A音声情報取得
- `_calculate_m4a_optimal_bitrate()`: 最適ビットレート計算
- `_process_m4a_file()`: M4A→MP3変換処理

### 3. APIエンドポイント統合 (`src/backend/app/api/endpoints/minutes.py`)

`process_audio_task()`関数を更新：
- M4Aファイル検出時に専用処理パイプラインを実行
- 音声抽出ステップでM4A圧縮処理を実行
- 進捗状況のリアルタイム更新

### 4. コマンドラインツール (`src/cli/process_m4a.py`)

独立したM4A処理ツールも提供：
```bash
python3 src/cli/process_m4a.py input.m4a --max-size 15 --max-bitrate 128 --min-bitrate 8
```

## 技術仕様

### 音声変換仕様

- **入力形式**: M4A (AAC コーデック)
- **出力形式**: MP3 (libmp3lame)
- **サンプリングレート**: 16kHz (Whisper API推奨)
- **チャンネル数**: 1 (モノラル)
- **ビットレート**: 8-128kbps (自動計算)

### ファイルサイズ制限対応

| ファイルサイズ | 処理方式 | 説明 |
|---------------|----------|------|
| ≤ 15MB | 直接処理 | そのまま転送 |
| 15-500MB | 自動圧縮 | 15MB以下に圧縮 |
| > 500MB | エラー | ファイルサイズ制限 |

### Whisper API制限対応

- **公式制限**: 25MB
- **実用制限**: 15MB（400エラー回避）
- **推奨サイズ**: 10-12MB（安全マージン）

## 圧縮性能

### 実測値

| 入力 | 出力 | 圧縮率 | 時間 |
|------|------|--------|------|
| 30秒, 475KB | 88KB | 81.5% | 音声のみ |
| 10分, 9.28MB | 1.72MB | 81.5% | 音声のみ |

### 長時間音声の例

104分のM4Aファイル (元サイズ不明) → 約10-12MBのMP3に圧縮可能

## フロー図

```
M4Aファイル
    ↓
ファイル検証 (.m4a拡張子)
    ↓
音声情報取得 (ffmpeg probe)
    ↓
最適ビットレート計算
    ↓
MP3変換 (ffmpeg)
    ↓ 
ファイルサイズ確認
    ↓
Whisper API転送
    ↓
文字起こし
    ↓
議事録生成
```

## 動作テスト済み

- ✅ M4A音声情報取得
- ✅ ビットレート計算ロジック
- ✅ M4A → MP3変換
- ✅ ファイルサイズ圧縮（81.5%圧縮率達成）
- ✅ APIエンドポイント統合
- ✅ 進捗更新機能

## 使用方法

### 1. バックエンドAPI経由

通常のファイルアップロードと同じ：
```bash
POST /api/minutes/upload
Content-Type: multipart/form-data
# M4Aファイルをアップロード
```

### 2. コマンドライン経由

```bash
# 基本的な圧縮
python3 src/cli/process_m4a.py recording.m4a

# カスタム設定
python3 src/cli/process_m4a.py recording.m4a --max-size 10 --min-bitrate 12
```

## 設定のカスタマイズ

`.env`ファイルで設定変更可能：

```env
# M4A処理設定
M4A_TARGET_FILE_SIZE_MB=15
M4A_MAX_BITRATE=128
M4A_MIN_BITRATE=8
M4A_SAMPLE_RATE=16000
M4A_MAX_INPUT_SIZE_MB=500
M4A_COMPRESSION_ENABLED=true
```

## エラーハンドリング

### 一般的なエラーと対処法

1. **ファイルサイズ超過**: 500MB制限を超過
   - 対処: ファイルを分割するか、他の形式で保存

2. **変換後サイズ超過**: 15MB制限達成不可
   - 対処: より低いビットレート設定、または手動分割

3. **ffmpeg エラー**: 音声変換失敗
   - 対処: ファイル形式・コーデック確認

## 今後の改善点

- [ ] 自動チャンク分割（長時間音声用）
- [ ] バッチ処理機能
- [ ] 進捗状況の詳細化
- [ ] エラーログの強化
- [ ] 複数ファイル同時処理

## 関連ファイル

- `src/backend/app/config.py` - 設定
- `src/backend/app/services/video_processor.py` - M4A処理ロジック
- `src/backend/app/api/endpoints/minutes.py` - API統合
- `src/cli/process_m4a.py` - コマンドラインツール
- `src/cli/README_M4A.md` - CLI使用方法 