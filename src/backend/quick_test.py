#!/usr/bin/env python3
"""クイックテスト"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.openai_service import OpenAIService
from app.prompts.chat_prompts import get_chat_system_prompt

async def test_specific_question():
    """特定の質問のテスト"""
    
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
    
    openai_service = OpenAIService()
    system_prompt = get_chat_system_prompt(
        transcription=sample_transcription,
        minutes=sample_minutes
    )
    
    # 問題のあった質問をテスト
    question = "技術担当者を教えてください"
    
    print(f"質問: {question}")
    
    # キーワード抽出をテスト
    keywords = openai_service._extract_keywords(question)
    print(f"抽出されたキーワード: {keywords}")
    
    # 関連コンテンツ検索をテスト
    transcription = openai_service._extract_transcription_from_prompt(system_prompt)
    minutes = openai_service._extract_minutes_from_prompt(system_prompt)
    
    relevant_content = openai_service._find_relevant_content(question, transcription, minutes)
    print(f"関連コンテンツ:\n{relevant_content}")
    
    # 実際の回答をテスト
    response_text, citations = await openai_service._call_mock_api(
        system_prompt=system_prompt,
        user_prompt=question,
        intent="question"
    )
    
    print(f"\n回答:\n{response_text}")
    
    if citations:
        print(f"\n引用数: {len(citations)}件")
        for i, citation in enumerate(citations, 1):
            print(f"  引用{i}: {citation.text}")

if __name__ == "__main__":
    asyncio.run(test_specific_question())