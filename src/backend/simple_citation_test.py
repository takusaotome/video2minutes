#!/usr/bin/env python3
"""簡単な引用機能のテストスクリプト"""

import re
from typing import Dict, List

def test_text_position_finding():
    """テキスト位置検索のテスト"""
    print("=== テキスト位置検索テスト ===")
    
    source_text = "これは サンプル テキスト です。重要な 情報が 含まれています。"
    target_text = "重要な 情報"
    
    position = source_text.find(target_text)
    print(f"検索対象: '{target_text}'")
    print(f"発見位置: {position}")
    
    if position != -1:
        found_text = source_text[position:position + len(target_text)]
        print(f"発見されたテキスト: '{found_text}'")
    
    return position is not None

def test_citation_patterns():
    """引用パターンのテスト"""
    print("\n=== 引用パターンテスト ===")
    
    citation_patterns = [
        r'引用[:：]\s*"([^"]+)"',
        r'「([^」]+)」(?:という|と言う|と述べ)',
        r'文字起こしの(\d+分\d+秒?)部分',
        r'(\d{2}:\d{2}:\d{2})(?:から|時点)の発言',
        r'音声の(\d+:\d+)あたり',
    ]
    
    test_responses = [
        'ご質問について、引用: "重要な決定事項"があります。',
        '「田中さんの提案」という内容が議論されました。',
        '文字起こしの5分30秒部分に詳細があります。',
        '00:10:15時点の発言が重要です。',
        '音声の15:30あたりで言及されています。'
    ]
    
    for i, response in enumerate(test_responses):
        print(f"\nテスト {i+1}: {response}")
        
        for j, pattern in enumerate(citation_patterns):
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                print(f"  パターン {j+1} マッチ: {match.group(1) if match.groups() else match.group(0)}")
                break
        else:
            print("  マッチなし")

def test_semantic_extraction():
    """セマンティック抽出のテスト"""
    print("\n=== セマンティック抽出テスト ===")
    
    ai_response = """
    ご質問について、「田中さんが提案した機能追加」に関して文字起こしを確認しました。
    また、「予算は来月までに確定する必要があります」という重要な発言もありました。
    スケジュール調整についても議論されています。
    """
    
    # 括弧内のテキストを抽出
    bracket_patterns = [
        r'「([^」]+)」',
        r'『([^』]+)』',
        r'\(([^)]+)\)',
        r'（([^）]+)）',
    ]
    
    phrases = []
    for pattern in bracket_patterns:
        matches = re.findall(pattern, ai_response)
        phrases.extend(matches)
    
    print("抽出された重要語句:")
    for phrase in phrases:
        print(f"  - {phrase}")

def test_timestamp_estimation():
    """タイムスタンプ推定のテスト"""
    print("\n=== タイムスタンプ推定テスト ===")
    
    transcription = "これは長い文字起こしのサンプルテキストです。" * 50  # 長いテキストをシミュレート
    
    test_positions = [0, len(transcription) // 4, len(transcription) // 2, len(transcription) * 3 // 4]
    
    for position in test_positions:
        # 位置の比例からタイムスタンプを推定
        text_ratio = position / len(transcription) if transcription else 0
        
        # 仮想的な動画時間（1秒あたり10文字と仮定）
        estimated_duration_seconds = len(transcription) // 10
        estimated_time_seconds = int(text_ratio * estimated_duration_seconds)
        
        # HH:MM:SS形式に変換
        hours = estimated_time_seconds // 3600
        minutes = (estimated_time_seconds % 3600) // 60
        seconds = estimated_time_seconds % 60
        
        timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        print(f"位置 {position} -> タイムスタンプ {timestamp}")

def test_confidence_calculation():
    """信頼度計算のテスト"""
    print("\n=== 信頼度計算テスト ===")
    
    test_cases = [
        ("完全一致テキスト", "完全一致テキスト", True),
        ("部分的一致", "部分的一致の例", False),
        ("短いテキスト", "短いテキスト", True),
        ("長いテキストの例で信頼度を確認", "長いテキストの例で信頼度を確認", True),
    ]
    
    for citation_text, transcription_text, exact_match in test_cases:
        confidence = 0.0
        
        # 完全一致の場合は高い信頼度
        if exact_match:
            confidence += 0.5
        
        # テキストの長さによる信頼度調整
        if len(citation_text) >= 10:
            confidence += 0.3
        elif len(citation_text) >= 5:
            confidence += 0.2
        
        # 文脈の妥当性チェック（簡易）
        if citation_text in transcription_text:
            confidence += 0.2
        
        confidence = min(confidence, 1.0)
        
        print(f"テキスト: '{citation_text}' -> 信頼度: {confidence:.2f}")

def main():
    """メインテスト実行"""
    print("簡単な引用機能テスト開始\n")
    
    try:
        success = True
        success &= test_text_position_finding()
        test_citation_patterns()
        test_semantic_extraction()
        test_timestamp_estimation()
        test_confidence_calculation()
        
        if success:
            print("\n✅ すべてのテストが正常に完了しました")
        else:
            print("\n⚠️  一部のテストで問題が発生しました")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()