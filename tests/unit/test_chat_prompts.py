"""チャットプロンプトのテスト"""
import pytest
from unittest.mock import Mock

from app.prompts.chat_prompts import (
    get_chat_system_prompt,
    get_edit_analysis_prompt,
    get_citation_extraction_prompt,
    build_chat_history_context,
    build_user_prompt,
    CHAT_SYSTEM_PROMPT,
    EDIT_ANALYSIS_PROMPT,
    CITATION_EXTRACTION_PROMPT
)


class TestChatPrompts:
    """チャットプロンプトのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.sample_transcription = """
        こんにちは、皆さん。今日の会議を始めます。
        まず、プロジェクトAの進捗について田中さんから報告をお願いします。
        田中: ありがとうございます。プロジェクトAは順調に進んでいます。
        来週までに設計書を完成させる予定です。
        """
        
        self.sample_minutes = """
# 会議議事録

## 参加者
- 田中さん（プロジェクトリーダー）
- 佐藤さん（開発担当）
- 山田さん（テスト担当）

## 議題
1. プロジェクトA進捗報告
2. 次期計画について

## アクションアイテム
- 設計書作成：田中さん、期限：来週
- テスト計画策定：山田さん、期限：今月末
"""

    def test_chat_system_prompt_constants(self):
        """チャットシステムプロンプト定数テスト"""
        assert isinstance(CHAT_SYSTEM_PROMPT, str)
        assert len(CHAT_SYSTEM_PROMPT) > 0
        assert "{transcription}" in CHAT_SYSTEM_PROMPT
        assert "{minutes}" in CHAT_SYSTEM_PROMPT
        assert "議事録" in CHAT_SYSTEM_PROMPT
        assert "文字起こし" in CHAT_SYSTEM_PROMPT

    def test_edit_analysis_prompt_constants(self):
        """編集解析プロンプト定数テスト"""
        assert isinstance(EDIT_ANALYSIS_PROMPT, str)
        assert len(EDIT_ANALYSIS_PROMPT) > 0
        assert "{current_minutes}" in EDIT_ANALYSIS_PROMPT
        assert "{edit_instruction}" in EDIT_ANALYSIS_PROMPT
        assert "replace_text" in EDIT_ANALYSIS_PROMPT
        assert "add_action_item" in EDIT_ANALYSIS_PROMPT

    def test_citation_extraction_prompt_constants(self):
        """引用抽出プロンプト定数テスト"""
        assert isinstance(CITATION_EXTRACTION_PROMPT, str)
        assert len(CITATION_EXTRACTION_PROMPT) > 0
        assert "{transcription}" in CITATION_EXTRACTION_PROMPT
        assert "{question}" in CITATION_EXTRACTION_PROMPT
        assert "{ai_response}" in CITATION_EXTRACTION_PROMPT

    def test_get_chat_system_prompt(self):
        """チャットシステムプロンプト取得テスト"""
        prompt = get_chat_system_prompt(self.sample_transcription, self.sample_minutes)
        
        assert isinstance(prompt, str)
        assert len(prompt) > len(CHAT_SYSTEM_PROMPT)
        assert self.sample_transcription in prompt
        assert self.sample_minutes in prompt
        assert "プロジェクトA" in prompt
        assert "田中さん" in prompt
        assert "{transcription}" not in prompt  # 置換済み
        assert "{minutes}" not in prompt  # 置換済み

    def test_get_chat_system_prompt_empty_inputs(self):
        """空の入力でのチャットシステムプロンプトテスト"""
        prompt = get_chat_system_prompt("", "")
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "{transcription}" not in prompt
        assert "{minutes}" not in prompt

    def test_get_edit_analysis_prompt(self):
        """編集解析プロンプト取得テスト"""
        edit_instruction = "田中さんを鈴木さんに変更してください"
        
        prompt = get_edit_analysis_prompt(self.sample_minutes, edit_instruction)
        
        assert isinstance(prompt, str)
        assert len(prompt) > len(EDIT_ANALYSIS_PROMPT)
        assert self.sample_minutes in prompt
        assert edit_instruction in prompt
        assert "田中さん" in prompt
        assert "{current_minutes}" not in prompt  # 置換済み
        assert "{edit_instruction}" not in prompt  # 置換済み

    def test_get_edit_analysis_prompt_complex_instruction(self):
        """複雑な編集指示でのプロンプトテスト"""
        complex_instruction = "プロジェクトAをプロジェクトBetaに変更し、新しいタスクとして品質チェックを追加"
        
        prompt = get_edit_analysis_prompt(self.sample_minutes, complex_instruction)
        
        assert complex_instruction in prompt
        assert "プロジェクトA" in prompt  # 議事録から
        assert "プロジェクトBeta" in prompt  # 指示から

    def test_get_citation_extraction_prompt(self):
        """引用抽出プロンプト取得テスト"""
        question = "プロジェクトAの進捗はどうですか？"
        ai_response = "プロジェクトAは順調に進んでいます。来週までに設計書が完成予定です。"
        
        prompt = get_citation_extraction_prompt(self.sample_transcription, question, ai_response)
        
        assert isinstance(prompt, str)
        assert len(prompt) > len(CITATION_EXTRACTION_PROMPT)
        assert self.sample_transcription in prompt
        assert question in prompt
        assert ai_response in prompt
        assert "{transcription}" not in prompt  # 置換済み
        assert "{question}" not in prompt  # 置換済み
        assert "{ai_response}" not in prompt  # 置換済み

    def test_build_chat_history_context_empty(self):
        """空のチャット履歴コンテキスト構築テスト"""
        context = build_chat_history_context([])
        
        assert context == ""

    def test_build_chat_history_context_single_message(self):
        """単一メッセージのチャット履歴コンテキスト構築テスト"""
        mock_message = Mock()
        mock_message.message = "プロジェクトの進捗は？"
        mock_message.response = "順調に進んでいます。"
        
        context = build_chat_history_context([mock_message])
        
        assert "【これまでの会話履歴】" in context
        assert "Q: プロジェクトの進捗は？" in context
        assert "A: 順調に進んでいます。" in context

    def test_build_chat_history_context_multiple_messages(self):
        """複数メッセージのチャット履歴コンテキスト構築テスト"""
        messages = []
        for i in range(3):
            mock_message = Mock()
            mock_message.message = f"質問{i}"
            mock_message.response = f"回答{i}"
            messages.append(mock_message)
        
        context = build_chat_history_context(messages)
        
        assert "【これまでの会話履歴】" in context
        assert "Q: 質問0" in context
        assert "A: 回答0" in context
        assert "Q: 質問2" in context
        assert "A: 回答2" in context

    def test_build_chat_history_context_max_messages_limit(self):
        """最大メッセージ数制限のテスト"""
        messages = []
        for i in range(10):
            mock_message = Mock()
            mock_message.message = f"質問{i}"
            mock_message.response = f"回答{i}"
            messages.append(mock_message)
        
        # デフォルトの最大5メッセージ
        context = build_chat_history_context(messages)
        
        assert "質問5" in context  # 最新5件に含まれる
        assert "質問9" in context  # 最新5件に含まれる
        assert "質問0" not in context  # 古いメッセージは除外
        assert "質問4" not in context  # 古いメッセージは除外

    def test_build_chat_history_context_custom_max_messages(self):
        """カスタム最大メッセージ数のテスト"""
        messages = []
        for i in range(5):
            mock_message = Mock()
            mock_message.message = f"質問{i}"
            mock_message.response = f"回答{i}"
            messages.append(mock_message)
        
        # カスタム最大2メッセージ
        context = build_chat_history_context(messages, max_messages=2)
        
        assert "質問3" in context  # 最新2件に含まれる
        assert "質問4" in context  # 最新2件に含まれる
        assert "質問0" not in context  # 古いメッセージは除外
        assert "質問2" not in context  # 古いメッセージは除外

    def test_build_user_prompt_without_history(self):
        """履歴なしのユーザープロンプト構築テスト"""
        message = "今日の会議の要点を教えてください"
        
        prompt = build_user_prompt(message)
        
        assert "【新しい質問】" in prompt
        assert message in prompt
        assert "【これまでの会話履歴】" not in prompt

    def test_build_user_prompt_with_history(self):
        """履歴ありのユーザープロンプト構築テスト"""
        message = "追加で質問があります"
        history_context = "【これまでの会話履歴】\nQ: 前の質問\nA: 前の回答"
        
        prompt = build_user_prompt(message, history_context)
        
        assert "【これまでの会話履歴】" in prompt
        assert "前の質問" in prompt
        assert "前の回答" in prompt
        assert "【新しい質問】" in prompt
        assert message in prompt

    def test_build_user_prompt_empty_message(self):
        """空メッセージのユーザープロンプト構築テスト"""
        message = ""
        
        prompt = build_user_prompt(message)
        
        assert "【新しい質問】" in prompt
        assert isinstance(prompt, str)

    def test_prompt_structure_consistency(self):
        """プロンプト構造一貫性テスト"""
        # 各プロンプトに必要な構造要素が含まれているかチェック
        
        # チャットシステムプロンプト
        chat_prompt = get_chat_system_prompt("テスト文字起こし", "テスト議事録")
        assert "【文字起こし内容】" in chat_prompt
        assert "【議事録内容】" in chat_prompt
        assert "【回答時の注意点】" in chat_prompt
        assert "【引用の書式】" in chat_prompt
        
        # 編集解析プロンプト
        edit_prompt = get_edit_analysis_prompt("テスト議事録", "テスト編集指示")
        assert "【編集指示の例】" in edit_prompt
        assert "【編集可能な操作】" in edit_prompt
        assert "【現在の議事録】" in edit_prompt
        assert "【編集指示】" in edit_prompt
        
        # 引用抽出プロンプト
        citation_prompt = get_citation_extraction_prompt("テスト文字起こし", "テスト質問", "テスト回答")
        assert "【文字起こし】" in citation_prompt
        assert "【質問】" in citation_prompt
        assert "【AI回答】" in citation_prompt
        assert "【抽出ルール】" in citation_prompt

    def test_prompt_examples_included(self):
        """プロンプト例示の包含テスト"""
        # チャットシステムプロンプトに例示が含まれている
        assert "【回答例】" in CHAT_SYSTEM_PROMPT
        assert "質問:" in CHAT_SYSTEM_PROMPT
        assert "回答:" in CHAT_SYSTEM_PROMPT
        
        # 編集解析プロンプトに編集例が含まれている
        assert "プロジェクトX" in EDIT_ANALYSIS_PROMPT
        assert "プロジェクトAlpha" in EDIT_ANALYSIS_PROMPT
        assert "田中さんに資料作成" in EDIT_ANALYSIS_PROMPT

    def test_japanese_text_handling(self):
        """日本語テキスト処理テスト"""
        japanese_transcription = "こんにちは。会議を開始します。"
        japanese_minutes = "# 議事録\n\n## 概要\n\n日本語での会議でした。"
        
        prompt = get_chat_system_prompt(japanese_transcription, japanese_minutes)
        
        # 日本語が正しく含まれていること
        assert "こんにちは" in prompt
        assert "会議を開始" in prompt
        assert "日本語での会議" in prompt

    def test_special_characters_handling(self):
        """特殊文字処理テスト"""
        special_transcription = "会議の内容：重要な決定事項（予算関連）について"
        special_minutes = "## 決定事項\n- 予算：1,000,000円\n- 期限：2024/12/31"
        
        prompt = get_chat_system_prompt(special_transcription, special_minutes)
        
        # 特殊文字が正しく含まれていること
        assert "：" in prompt
        assert "（" in prompt
        assert "）" in prompt
        assert "1,000,000円" in prompt
        assert "2024/12/31" in prompt

    def test_long_text_handling(self):
        """長文テキスト処理テスト"""
        long_transcription = "長い文字起こし内容。" * 100
        long_minutes = "# 長い議事録\n\n" + "詳細な内容。" * 50
        
        prompt = get_chat_system_prompt(long_transcription, long_minutes)
        
        # 長文が適切に処理されること
        assert len(prompt) > len(CHAT_SYSTEM_PROMPT)
        assert long_transcription in prompt
        assert long_minutes in prompt

    def test_build_chat_history_formatting(self):
        """チャット履歴フォーマットテスト"""
        mock_message1 = Mock()
        mock_message1.message = "最初の質問"
        mock_message1.response = "最初の回答"
        
        mock_message2 = Mock()
        mock_message2.message = "二番目の質問"
        mock_message2.response = "二番目の回答"
        
        context = build_chat_history_context([mock_message1, mock_message2])
        
        # 正しいフォーマットになっていること
        lines = context.split('\n')
        assert "【これまでの会話履歴】" in lines[0]
        assert lines[1].startswith("Q: ")
        assert lines[2].startswith("A: ")
        assert lines[3] == ""  # 空行
        assert lines[4].startswith("Q: ")
        assert lines[5].startswith("A: ")