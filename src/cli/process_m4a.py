#!/usr/bin/env python3
"""
M4AファイルをコンパクトなMP3ファイルに変換するスクリプト
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from fractions import Fraction

import ffmpeg


class M4AProcessor:
    """M4Aファイル処理クラス"""
    
    def __init__(self):
        self.max_file_size_mb = 15  # 最大ファイルサイズ（MB）- Whisper API安全制限
        self.max_bitrate = 128  # 最大ビットレート（kbps）
        self.min_bitrate = 8   # 最小ビットレート（kbps）- 長時間音声対応
        self.target_sample_rate = 16000  # サンプリングレート（Whisper推奨）
    
    def get_audio_info(self, audio_path: str) -> dict:
        """音声ファイルの情報を取得"""
        try:
            probe = ffmpeg.probe(audio_path)
            audio_info = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "audio"
                ),
                None,
            )
            
            duration = float(probe["format"]["duration"])
            size = int(probe["format"]["size"])
            
            return {
                "duration": duration,
                "size": size,
                "size_mb": size / (1024 * 1024),
                "codec": audio_info["codec_name"] if audio_info else None,
                "sample_rate": int(audio_info["sample_rate"]) if audio_info else None,
                "channels": int(audio_info["channels"]) if audio_info else None,
                "bitrate": int(audio_info.get("bit_rate", 0)) if audio_info else None,
            }
        except Exception as e:
            raise RuntimeError(f"音声情報の取得に失敗しました: {str(e)}")
    
    def calculate_optimal_bitrate(self, duration_seconds: float, target_size_mb: float) -> int:
        """最適なビットレートを計算"""
        if duration_seconds <= 0:
            return self.min_bitrate
        
        # ビットレート計算: (ファイルサイズMB * 8 * 1024) / 時間秒 = kbps
        calculated_bitrate = (target_size_mb * 8 * 1024) / duration_seconds
        
        # 最小・最大値でクランプ
        final_bitrate = max(min(int(calculated_bitrate), self.max_bitrate), self.min_bitrate)
        
        # 計算結果を表示
        print(f"ビットレート計算:")
        print(f"  計算値: {calculated_bitrate:.1f}kbps")
        print(f"  最終値: {final_bitrate}kbps (制限: {self.min_bitrate}-{self.max_bitrate}kbps)")
        
        # 予想ファイルサイズを計算
        estimated_size_mb = (final_bitrate * duration_seconds) / (8 * 1024)
        print(f"  予想ファイルサイズ: {estimated_size_mb:.2f}MB")
        
        # 目標サイズを超える場合の警告
        if estimated_size_mb > target_size_mb * 1.1:  # 10%の余裕を持たせる
            print(f"  ⚠️  警告: 予想サイズ({estimated_size_mb:.2f}MB)が目標サイズ({target_size_mb}MB)を超過しています")
            print(f"      目標サイズを達成するには{calculated_bitrate:.1f}kbpsが必要です")
        
        return final_bitrate
    
    async def process_m4a(self, input_path: str, output_path: str = None) -> str:
        """M4AファイルをコンパクトなMP3に変換"""
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")
        
        # 出力パスが指定されていない場合は自動生成
        if output_path is None:
            input_file = Path(input_path)
            output_path = str(input_file.with_suffix('.mp3'))
            if output_path == input_path:
                output_path = str(input_file.with_name(f"{input_file.stem}_processed.mp3"))
        
        print(f"入力ファイル: {input_path}")
        print(f"出力ファイル: {output_path}")
        
        # 入力ファイルの情報を取得
        audio_info = self.get_audio_info(input_path)
        print(f"入力ファイル情報:")
        print(f"  時間: {audio_info['duration']:.1f}秒 ({audio_info['duration']/60:.1f}分)")
        print(f"  サイズ: {audio_info['size_mb']:.2f}MB")
        print(f"  コーデック: {audio_info['codec']}")
        print(f"  サンプリングレート: {audio_info['sample_rate']}Hz")
        print(f"  チャンネル数: {audio_info['channels']}")
        print(f"  ビットレート: {audio_info['bitrate']}bps")
        
        # 最適なビットレートを計算
        optimal_bitrate = self.calculate_optimal_bitrate(
            audio_info['duration'], 
            self.max_file_size_mb
        )
        print(f"使用ビットレート: {optimal_bitrate}kbps")
        
        # ffmpegでMP3変換を実行
        await self._run_ffmpeg_conversion(input_path, output_path, optimal_bitrate)
        
        # 出力ファイルの情報を表示
        if os.path.exists(output_path):
            output_info = self.get_audio_info(output_path)
            print(f"\n出力ファイル情報:")
            print(f"  サイズ: {output_info['size_mb']:.2f}MB")
            print(f"  圧縮率: {(1 - output_info['size_mb'] / audio_info['size_mb']) * 100:.1f}%")
            print(f"  コーデック: {output_info['codec']}")
            print(f"  サンプリングレート: {output_info['sample_rate']}Hz")
            print(f"  チャンネル数: {output_info['channels']}")
        
        return output_path
    
    async def _run_ffmpeg_conversion(self, input_path: str, output_path: str, bitrate: int):
        """ffmpegで音声変換を実行"""
        
        # 出力ファイルが既に存在する場合は削除
        if os.path.exists(output_path):
            os.remove(output_path)
        
        # ffmpegコマンドを構築
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream,
            output_path,
            acodec="libmp3lame",  # MP3エンコーダー
            ac=1,  # モノラル
            ar=str(self.target_sample_rate),  # サンプリングレート
            audio_bitrate=f"{bitrate}k",  # ビットレート
            y=None,  # 既存ファイルを上書き
        )
        
        # コマンドを非同期実行
        cmd = ffmpeg.compile(stream)
        print(f"実行コマンド: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "不明なエラー"
            raise RuntimeError(f"ffmpeg変換エラー: {error_msg}")
        
        print("変換完了")


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="M4AファイルをコンパクトなMP3ファイルに変換")
    parser.add_argument("input_file", help="入力M4Aファイル")
    parser.add_argument("-o", "--output", help="出力MP3ファイル（省略時は自動生成）")
    parser.add_argument("--max-size", type=int, default=15, help="最大ファイルサイズ（MB、デフォルト: 15）")
    parser.add_argument("--max-bitrate", type=int, default=128, help="最大ビットレート（kbps、デフォルト: 128）")
    parser.add_argument("--min-bitrate", type=int, default=8, help="最小ビットレート（kbps、デフォルト: 8）")
    
    args = parser.parse_args()
    
    # プロセッサーを作成
    processor = M4AProcessor()
    processor.max_file_size_mb = args.max_size
    processor.max_bitrate = args.max_bitrate
    processor.min_bitrate = args.min_bitrate
    
    try:
        # 変換実行
        output_file = await processor.process_m4a(args.input_file, args.output)
        print(f"\n✅ 変換完了: {output_file}")
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 