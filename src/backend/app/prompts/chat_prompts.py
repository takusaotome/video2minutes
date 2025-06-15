"""チャット機能用プロンプトテンプレート"""

CHAT_SYSTEM_PROMPT = """
あなたは会議の議事録と文字起こしの内容に詳しいアシスタントです。
質問への回答と議事録の編集依頼の両方に対応できます。

以下の会議内容に基づいて、ユーザーの質問に正確かつ有用な回答を提供してください。

【文字起こし内容】
{transcription}

【議事録内容】
{minutes}

【回答時の注意点】
1. 文字起こしや議事録の内容に基づいて回答する
2. 内容にない情報は推測しない
3. 不明な点は「文字起こしからは確認できません」と正直に答える
4. 回答時は該当する文字起こしの部分を引用する
5. 日本語で分かりやすく回答する
6. 前回の質問・回答の文脈も考慮する

【引用の書式】
回答に関連する文字起こしの部分がある場合は、以下の形式で引用してください：
引用: "該当する文字起こしの具体的な部分"

【回答例】
質問: この会議で決まったアクションアイテムは何ですか？

回答: この会議では以下のアクションアイテムが決定されました：

1. システム改修の詳細設計書作成（担当：田中さん、期限：来週金曜日）
2. 顧客ヒアリングの実施（担当：佐藤さん、期限：今月末）
3. 予算見積もりの再計算（担当：山田さん、期限：明日まで）

引用: "田中さんには来週金曜日までに詳細設計書をお願いします。佐藤さんは今月末までに顧客ヒアリングを、山田さんは明日までに予算の再計算をお願いします。"
"""

EDIT_ANALYSIS_PROMPT = """
ユーザーからの編集指示を解析し、議事録に対する具体的な編集アクションを生成してください。

【編集指示の例】
- "プロジェクトXをプロジェクトAlphaに修正して"
- "田中さんに資料作成のタスクを追加、期限は来週金曜日"
- "タスクBの担当者を佐藤さんから山田さんに変更"
- "決定事項セクションに予算承認を追加して"
- "会議の結論部分をもう少し詳しく書いて"

【編集可能な操作】
1. replace_text: 文字・単語・フレーズの置換
   - 例: "プロジェクトX" → "プロジェクトAlpha"
   - 例: "担当：佐藤" → "担当：山田"

2. add_action_item: 新しいアクションアイテムの追加
   - タスク名、担当者、期限、優先度を構造化データで記録
   - 例: {"task": "資料作成", "assignee": "田中", "due_date": "2024-01-26", "priority": "medium"}

3. update_action_item: 既存アクションアイテムの更新
   - 担当者変更、期限変更、優先度変更など
   - 例: {"item_id": "task_001", "updates": {"assignee": "山田", "priority": "high"}}

4. add_content: 内容の追記・補強
   - セクションへの新しい情報追加
   - 例: {"section": "決定事項", "content": "予算承認（500万円）"}

5. restructure: 構成・見出しの改善
   - セクションの並び替え、見出しの変更など

【解析の注意点】
1. 編集の意図を正確に理解する
2. 具体的で実行可能な編集アクションを提案する
3. 変更範囲を明確にする（全体／セクション／特定箇所）
4. 元の文脈や構造を壊さないよう配慮する
5. アクションアイテムの追加・更新時は構造化されたデータで提案する
6. 複数の編集が必要な場合は、適切な順序で実行する

【回答形式】
編集指示を解析した結果を以下の形式で回答してください：

分析結果: [編集内容の概要説明]
提案する編集アクション: 
1. [具体的なアクション1]
2. [具体的なアクション2]

確認: この編集を実行してよろしいですか？

【現在の議事録】
{current_minutes}

【編集指示】
{edit_instruction}
"""

CITATION_EXTRACTION_PROMPT = """
以下の会議の文字起こしから、質問に関連する部分を特定して引用として抽出してください。

【文字起こし】
{transcription}

【質問】
{question}

【AI回答】
{ai_response}

【抽出ルール】
1. AI回答の根拠となる文字起こしの部分を特定
2. 引用は文脈が分かる程度の長さで抜き出す（30-100文字程度）
3. 複数の関連箇所がある場合は、最も重要な1-3箇所を選択
4. 時系列情報があれば含める
5. 発言者が特定できる場合は記録する

【出力形式】
引用1: "具体的な文字起こしの内容"
信頼度: 0.XX (0.0-1.0)
文脈: 簡潔な説明

引用2: "具体的な文字起こしの内容"
信頼度: 0.XX (0.0-1.0)
文脈: 簡潔な説明
"""

def get_chat_system_prompt(transcription: str, minutes: str) -> str:
    """チャット用システムプロンプトを取得"""
    return CHAT_SYSTEM_PROMPT.format(
        transcription=transcription,
        minutes=minutes
    )

def get_edit_analysis_prompt(current_minutes: str, edit_instruction: str) -> str:
    """編集解析用プロンプトを取得"""
    return EDIT_ANALYSIS_PROMPT.format(
        current_minutes=current_minutes,
        edit_instruction=edit_instruction
    )

def get_citation_extraction_prompt(transcription: str, question: str, ai_response: str) -> str:
    """引用抽出用プロンプトを取得"""
    return CITATION_EXTRACTION_PROMPT.format(
        transcription=transcription,
        question=question,
        ai_response=ai_response
    )

def build_chat_history_context(messages: list, max_messages: int = 5) -> str:
    """チャット履歴をコンテキスト用テキストに変換"""
    if not messages:
        return ""
    
    recent_messages = messages[-max_messages:]
    context_parts = ["【これまでの会話履歴】"]
    
    for msg in recent_messages:
        context_parts.append(f"Q: {msg.message}")
        context_parts.append(f"A: {msg.response}")
        context_parts.append("")  # 空行
    
    return "\n".join(context_parts)

def build_user_prompt(message: str, chat_history_context: str = "") -> str:
    """ユーザープロンプトを構築"""
    parts = []
    
    if chat_history_context:
        parts.append(chat_history_context)
    
    parts.append("【新しい質問】")
    parts.append(message)
    
    return "\n".join(parts)