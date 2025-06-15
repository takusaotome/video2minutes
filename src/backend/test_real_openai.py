#!/usr/bin/env python3
"""実際のOpenAI APIテスト"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.openai_service import OpenAIService
from app.prompts.chat_prompts import get_chat_system_prompt
from app.config import settings

async def test_real_openai_api():
    """実際のOpenAI APIをテスト"""
    print("=== 実際のOpenAI APIテスト ===")
    
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
    
    print(f"モデル: {openai_service.model}")
    print(f"模擬モード: {openai_service.use_mock}")
    print(f"APIキー設定: {'***' + settings.openai_api_key[-4:] if settings.openai_api_key else 'なし'}")
    
    # システムプロンプトを生成
    system_prompt = get_chat_system_prompt(
        transcription=sample_transcription,
        minutes=sample_minutes
    )
    
    # テスト質問
    test_question = "技術担当者は誰ですか？"
    
    print(f"\n質問: {test_question}")
    print("OpenAI API呼び出し中...")
    
    try:
        # 直接_call_openai_apiメソッドを呼び出してテスト
        response_text, citations = await openai_service._call_openai_api(
            system_prompt=system_prompt,
            user_prompt=test_question,
            intent="question"
        )
        
        print(f"\n回答: {response_text}")
        print(f"引用数: {len(citations)}件")
        for i, citation in enumerate(citations, 1):
            print(f"  引用{i}: {citation.text}")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_openai_api())