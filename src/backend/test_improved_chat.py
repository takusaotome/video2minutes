#!/usr/bin/env python3
"""改善されたチャット機能のテストスクリプト"""

import asyncio
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.openai_service import OpenAIService
from app.prompts.chat_prompts import get_chat_system_prompt


async def test_improved_chat_responses():
    """改善されたチャット回答のテスト"""
    print("=== 改善されたチャット機能テスト ===")
    
    # テスト用データ
    sample_transcription = """
    こんにちは、今日は新しいプロジェクトAlphaについて議論します。
    プロジェクトの予算は500万円で、期間は6ヶ月を予定しています。
    田中さんがプロジェクトマネージャーを担当し、来週までに詳細な計画書を作成していただきます。
    佐藤さんには技術検討をお願いし、2週間後までに技術仕様書を提出していただく予定です。
    また、来月の15日までに初期設計レビューを実施することが決定されました。
    """
    
    sample_minutes = """
# プロジェクトAlpha キックオフ会議

## 会議概要
- 日時: 2024年1月15日 14:00-15:00
- 参加者: 田中、佐藤、山田

## 議論内容
### プロジェクト概要
- プロジェクト名: Alpha
- 予算: 500万円
- 期間: 6ヶ月

### 担当者決定
- プロジェクトマネージャー: 田中さん
- 技術担当: 佐藤さん

## アクションアイテム
- 田中さん: 詳細計画書作成（期限: 来週）
- 佐藤さん: 技術仕様書作成（期限: 2週間後）

## 決定事項
- 初期設計レビュー実施日: 来月15日
    """
    
    # OpenAIサービスのインスタンス作成
    openai_service = OpenAIService()
    
    # システムプロンプトを生成
    system_prompt = get_chat_system_prompt(
        transcription=sample_transcription,
        minutes=sample_minutes
    )
    
    # テスト質問
    test_questions = [
        "プロジェクトの予算はいくらですか？",
        "田中さんの担当は何ですか？",
        "アクションアイテムを教えてください",
        "初期設計レビューはいつ実施されますか？",
        "プロジェクトの期間はどのくらいですか？",
        "参加者は誰ですか？",
        "技術担当者を教えてください",
        "存在しない情報について質問します"
    ]
    
    print(f"システムプロンプト作成完了 (長さ: {len(system_prompt)}文字)")
    print(f"文字起こし長さ: {len(sample_transcription)}文字")
    print(f"議事録長さ: {len(sample_minutes)}文字\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"【テスト {i}】質問: {question}")
        
        try:
            # 模擬API呼び出しをテスト
            response_text, citations = await openai_service._call_mock_api(
                system_prompt=system_prompt,
                user_prompt=question,
                intent="question"
            )
            
            print(f"回答: {response_text}")
            
            if citations:
                print(f"引用数: {len(citations)}件")
                for j, citation in enumerate(citations, 1):
                    print(f"  引用{j}: {citation.text} (信頼度: {citation.confidence:.2f})")
            else:
                print("引用: なし")
                
        except Exception as e:
            print(f"エラー: {e}")
        
        print("-" * 50)


async def test_keyword_extraction():
    """キーワード抽出のテスト"""
    print("\n=== キーワード抽出テスト ===")
    
    openai_service = OpenAIService()
    
    test_questions = [
        "プロジェクトAlphaの予算について教えてください",
        "田中さんの役割は何ですか？",
        "設計レビューの日程を確認したい",
        "技術仕様書の担当者は誰ですか？",
        "アクションアイテムの期限を教えて"
    ]
    
    for question in test_questions:
        keywords = openai_service._extract_keywords(question)
        print(f"質問: {question}")
        print(f"抽出キーワード: {keywords}")
        print()


async def test_content_search():
    """コンテンツ検索のテスト"""
    print("=== コンテンツ検索テスト ===")
    
    sample_text = """
    プロジェクトAlphaは重要な新規事業です。
    予算は500万円で、6ヶ月の期間を想定しています。
    田中さんがプロジェクトマネージャーとして全体を統括し、
    佐藤さんが技術面を担当します。
    来週までに詳細計画の策定が必要です。
    """
    
    openai_service = OpenAIService()
    
    test_keywords = ["プロジェクト", "田中", "予算", "期間"]
    
    for keyword in test_keywords:
        context = openai_service._get_context_around_keyword(keyword, sample_text, 50)
        print(f"キーワード: {keyword}")
        print(f"コンテキスト: {context}")
        print()


async def main():
    """メインテスト実行"""
    print("改善されたチャット機能テスト開始\n")
    
    try:
        await test_improved_chat_responses()
        await test_keyword_extraction()
        await test_content_search()
        
        print("\n✅ すべてのテストが完了しました")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())