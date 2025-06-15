#!/usr/bin/env python3
"""完全なチャット機能テスト"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.openai_service import OpenAIService
from app.models.chat import ChatSession, MessageIntent

async def test_full_chat_flow():
    """完全なチャット機能のテスト"""
    print("=== 完全なチャット機能テスト ===")
    
    # 実際の会議データ
    transcription = """
    味があるなというふうに思いました わかりました ちょっとそこのデータの利活用みたいなところは 多分次のフェーズになるかもしれないんですが 一応そういう要望もあるというところは理解いたしました 今は基本的にExcelとかで物件を絞り込んだものを 内覧するときにこのお客さんにどの物件を紹介しようという 絞り込みをしているんですが
    
    新しい要望として、データの利活用について話が出ました。また、物件推薦システムの改善についても言及がありました。レポート機能の充実も要望として挙がっています。
    """
    
    minutes = """
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
    
    # セッション作成
    session = ChatSession(
        session_id="test_session_001",
        task_id="test_task_001",
        transcription=transcription,
        minutes=minutes
    )
    
    openai_service = OpenAIService()
    
    # テスト質問リスト
    test_questions = [
        "今回の会議の中で出てきた新しい要望はなんですか",
        "データ利活用について詳しく教えてください",
        "現在の物件管理の課題は何ですか",
        "レポート機能について何が話し合われましたか"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n【質問 {i}】: {question}")
        print("-" * 50)
        
        try:
            # チャットメッセージを処理
            result = await openai_service.process_chat_message(
                session=session,
                message=question,
                intent=MessageIntent.QUESTION,
                chat_history=[]
            )
            
            print(f"回答: {result['response']}")
            
            if result['citations']:
                print(f"\n参照箇所 ({len(result['citations'])}件):")
                for j, citation in enumerate(result['citations'], 1):
                    print(f"  {j}. {citation.text} (信頼度: {citation.confidence:.2f})")
                    if citation.start_time:
                        print(f"     時刻: {citation.start_time}")
            
            print(f"\nトークン使用量: {result['tokens_used']}")
            print(f"処理時間: {result['processing_time']:.2f}秒")
            
        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()
        
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_full_chat_flow())