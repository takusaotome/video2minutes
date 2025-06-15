#!/usr/bin/env python3
"""引用機能のテストスクリプト"""

import asyncio
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.citation_service import citation_service

# Import models directly to avoid circular import issue
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'models'))
from chat import ChatSession, Citation


def test_citation_extraction():
    """引用抽出のテスト"""
    print("=== 引用抽出テスト ===")
    
    # テスト用データ
    sample_transcription = """
    こんにちは、今日は新しいプロジェクトについて議論します。
    田中さんが提案した機能追加について検討しましょう。
    予算は来月までに確定する必要があります。
    スケジュールの調整が重要な課題です。
    """
    
    sample_ai_response = """
    ご質問について、「田中さんが提案した機能追加」に関して文字起こしを確認しました。
    また、「予算は来月までに確定する必要があります」という重要な発言もありました。
    """
    
    sample_session = ChatSession(
        task_id="test-task-123",
        transcription=sample_transcription,
        minutes="テスト議事録"
    )
    
    # 引用を抽出
    citations = citation_service.extract_citations_from_response(
        sample_ai_response,
        sample_transcription,
        sample_session
    )
    
    print(f"抽出された引用数: {len(citations)}")
    for i, citation in enumerate(citations):
        print(f"\n引用 {i+1}:")
        print(f"  テキスト: {citation.text}")
        print(f"  タイムスタンプ: {citation.start_time}")
        print(f"  信頼度: {citation.confidence}")
        print(f"  ハイライト位置: {citation.highlight_start}-{citation.highlight_end}")
        print(f"  文脈: {citation.context[:50]}...")


def test_text_position_finding():
    """テキスト位置検索のテスト"""
    print("\n=== テキスト位置検索テスト ===")
    
    source_text = "これは サンプル テキスト です。重要な 情報が 含まれています。"
    target_text = "重要な 情報"
    
    position = citation_service._find_text_position(target_text, source_text)
    print(f"検索対象: '{target_text}'")
    print(f"発見位置: {position}")
    
    if position is not None:
        found_text = source_text[position:position + len(target_text)]
        print(f"発見されたテキスト: '{found_text}'")


def test_similarity_calculation():
    """類似度計算のテスト"""
    print("\n=== 類似度計算テスト ===")
    
    words1 = ["田中", "さん", "提案", "機能"]
    words2 = ["田中", "さん", "が", "提案", "した", "機能"]
    
    similarity = citation_service._calculate_text_similarity(words1, words2)
    print(f"単語リスト1: {words1}")
    print(f"単語リスト2: {words2}")
    print(f"類似度: {similarity:.3f}")


def test_highlight_creation():
    """ハイライト作成のテスト"""
    print("\n=== ハイライト作成テスト ===")
    
    citation = Citation(
        text="重要な議論ポイント",
        start_time="00:05:30",
        confidence=0.9,
        context="この重要な議論ポイントについて詳細を確認しましょう",
        highlight_start=100,
        highlight_end=120
    )
    
    transcription = "会議の文字起こし内容..."
    
    highlight_info = citation_service.create_highlight_info(citation, transcription)
    
    print("ハイライト情報:")
    for key, value in highlight_info.items():
        print(f"  {key}: {value}")


def main():
    """メインテスト実行"""
    print("引用機能テスト開始\n")
    
    try:
        test_citation_extraction()
        test_text_position_finding()
        test_similarity_calculation()
        test_highlight_creation()
        
        print("\n✅ すべてのテストが完了しました")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()