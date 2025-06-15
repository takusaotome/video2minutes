#!/usr/bin/env python3
"""実際のOpenAI API回答テスト"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.openai_service import OpenAIService
from app.prompts.chat_prompts import get_chat_system_prompt

async def test_api_response():
    """実際のOpenAI API回答を確認"""
    print("=== OpenAI API回答テスト ===")
    
    # 実際の会議データ
    sample_transcription = """
    味があるなというふうに思いました わかりました ちょっとそこのデータの利活用みたいなところは 多分次のフェーズになるかもしれないんですが 一応そういう要望もあるというところは理解いたしました 今は基本的にExcelとかで物件を絞り込んだものを 内覧するときにこのお客さんにどの物件を紹介しようという 絞り込みをしているんですが
    
    新しい要望として、データの利活用について話が出ました。また、物件推薦システムの改善についても言及がありました。レポート機能の充実も要望として挙がっています。
    """
    
    sample_minutes = """
# 住宅部門CRM業務フロー確認会議

## 会議情報
- **会議名**: 住宅部門CRM業務フロー確認会議
- **開催日時**: （記載なし／要追記）
- **出席者**: 住宅部門関係者、IT

## 新しい要望・提案
### データ利活用の検討
- 次のフェーズでデータ利活用機能の検討
- 物件推薦システムの改善要望
- レポート機能の強化要望

### 現状の課題
- Excel による物件絞り込み作業の効率化
- 内覧時の物件紹介プロセス改善

## アクションアイテム
- レポート要件ヒアリング（住宅部門＋IT、次回会議まで）
- 標準レポート案提示後、追加要望を収集
- 物件情報管理の現行Excel業務フロー確認
    """
    
    openai_service = OpenAIService()
    
    print(f"モデル: {openai_service.model}")
    print(f"模擬モード: {openai_service.use_mock}")
    
    # システムプロンプトを生成
    system_prompt = get_chat_system_prompt(
        transcription=sample_transcription,
        minutes=sample_minutes
    )
    
    # テスト質問
    test_question = "今回の会議の中で出てきた新しい要望はなんですか"
    
    print(f"\n質問: {test_question}")
    print("\n--- APIの直接レスポンスを確認 ---")
    
    try:
        # 直接OpenAI APIを呼び出し
        from openai import AsyncOpenAI
        from app.config import settings
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_question}
        ]
        
        if openai_service.model.startswith('o3'):
            response = await client.chat.completions.create(
                model=openai_service.model,
                messages=messages,
                max_completion_tokens=4000
            )
        else:
            response = await client.chat.completions.create(
                model=openai_service.model,
                messages=messages,
                max_tokens=4000,
                temperature=0.3
            )
        
        api_response = response.choices[0].message.content
        print(f"直接API回答:\n{api_response}\n")
        
        # サービス経由でテスト
        print("--- サービス経由での回答 ---")
        service_response, citations = await openai_service._call_openai_api(
            system_prompt=system_prompt,
            user_prompt=test_question,
            intent="question"
        )
        
        print(f"サービス回答:\n{service_response}\n")
        print(f"引用数: {len(citations)}件")
        
        # 比較
        if api_response == service_response:
            print("✅ API回答とサービス回答が一致")
        else:
            print("❌ API回答とサービス回答が不一致")
            print("何らかの変換処理が行われている可能性があります")
        
    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_response())