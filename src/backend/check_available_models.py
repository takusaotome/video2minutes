#!/usr/bin/env python3
"""利用可能なOpenAIモデルを確認"""

import asyncio
import openai
from app.config import settings

async def check_available_models():
    """利用可能なモデルを確認"""
    try:
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        
        # モデル一覧を取得
        models = await client.models.list()
        
        print("=== 利用可能なモデル一覧 ===")
        
        # チャット系モデルのみフィルタリング
        chat_models = []
        for model in models.data:
            model_id = model.id
            if any(keyword in model_id.lower() for keyword in ['gpt-4', 'gpt-3.5', 'o1', 'o3']):
                chat_models.append(model_id)
        
        # ソートして表示
        chat_models.sort()
        for model in chat_models:
            print(f"- {model}")
            
        print(f"\n総モデル数: {len(chat_models)}件")
        
        # 特定のモデルをテスト
        test_models = ['o3', 'gpt-4.1', 'gpt-4o', 'gpt-4-turbo', 'gpt-4']
        
        print("\n=== 特定モデルのテスト ===")
        for model in test_models:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                print(f"✅ {model}: 利用可能")
            except openai.NotFoundError as e:
                print(f"❌ {model}: 利用不可 - {e.body.get('error', {}).get('message', str(e))}")
            except Exception as e:
                print(f"⚠️ {model}: エラー - {str(e)}")
                
    except Exception as e:
        print(f"モデル確認エラー: {e}")

if __name__ == "__main__":
    asyncio.run(check_available_models())