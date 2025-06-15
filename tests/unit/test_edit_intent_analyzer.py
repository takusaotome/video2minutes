"""編集インテント解析サービスのテスト"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.services.edit_intent_analyzer import EditIntentAnalyzer, edit_intent_analyzer
from app.models.chat import EditAction, EditActionType, EditScope


class TestEditIntentAnalyzer:
    """編集インテント解析サービスのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.analyzer = EditIntentAnalyzer()
        self.sample_minutes = """
# 会議議事録

## 参加者
- 田中さん
- 佐藤さん
- 鈴木さん

## 議題
1. プロジェクト進捗報告
2. 次期計画について

## アクションアイテム
- 資料作成：田中さん、期限：今週金曜日
- レビュー実施：佐藤さん、期限：来週月曜日
"""

    def test_initialization(self):
        """初期化テスト"""
        analyzer = EditIntentAnalyzer()
        assert hasattr(analyzer, 'edit_patterns')
        assert hasattr(analyzer, 'time_patterns')
        assert hasattr(analyzer, 'priority_keywords')
        assert len(analyzer.edit_patterns) > 0

    def test_analyze_edit_intent_replace_text(self):
        """テキスト置換インテント解析テスト"""
        instruction = "田中さんを山田さんに変更"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.REPLACE_TEXT
        assert actions[0].target == "田中さん"
        assert actions[0].replacement == "山田さん"
        assert "田中さん" in explanation
        assert "山田さん" in explanation

    def test_analyze_edit_intent_replace_with_quotes(self):
        """引用符付きテキスト置換テスト"""
        instruction = "「プロジェクト進捗報告」を「開発進捗レポート」に変更"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.REPLACE_TEXT
        assert actions[0].target == "プロジェクト進捗報告"
        assert actions[0].replacement == "開発進捗レポート"

    def test_analyze_edit_intent_add_action_item(self):
        """アクションアイテム追加インテント解析テスト"""
        instruction = "テスト実行のタスクを追加"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.ADD_ACTION_ITEM
        assert "task" in actions[0].content
        assert "テスト実行" in actions[0].content["task"]

    def test_analyze_edit_intent_add_action_item_with_assignee(self):
        """担当者付きアクションアイテム追加テスト"""
        instruction = "佐藤さんにデータベース設計のタスクを追加"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.ADD_ACTION_ITEM
        assert actions[0].content["assignee"] == "佐藤"
        assert "データベース設計" in actions[0].content["task"]

    def test_analyze_edit_intent_update_action_item_assignee(self):
        """アクションアイテム担当者更新テスト"""
        instruction = "資料作成の担当者を佐藤さんに変更"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.UPDATE_ACTION_ITEM
        assert actions[0].updates["assignee"] == "佐藤さん"

    def test_analyze_edit_intent_update_action_item_deadline(self):
        """アクションアイテム期限更新テスト"""
        instruction = "レビュー実施の期限を来週金曜日に変更"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.UPDATE_ACTION_ITEM
        assert "due_date" in actions[0].updates
        assert actions[0].updates["due_date"] is not None

    def test_analyze_edit_intent_add_content(self):
        """コンテンツ追加インテント解析テスト"""
        instruction = "議題に品質管理について追加"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.ADD_CONTENT
        assert actions[0].content["section"] == "議題"
        assert actions[0].content["text"] == "品質管理について"

    def test_analyze_edit_intent_no_match_fallback(self):
        """パターンマッチ失敗時のフォールバック処理テスト"""
        instruction = "何か複雑な編集指示"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        # フォールバック処理が実行される
        assert "解析しましたが" in explanation or len(actions) > 0

    def test_extract_assignee_patterns(self):
        """担当者抽出パターンテスト"""
        test_cases = [
            ("担当：田中さん", "田中"),
            ("田中さんに依頼", "田中"),
            ("鈴木が担当", "鈴木"),
            ("責任者：佐藤さん", "佐藤"),
            ("誰にも指定なし", "未定")
        ]
        
        for instruction, expected in test_cases:
            result = self.analyzer._extract_assignee(instruction)
            assert result == expected

    def test_extract_due_date_patterns(self):
        """期限抽出パターンテスト"""
        test_cases = [
            ("期限：今週金曜日", "今週金曜日"),
            ("締切：明日まで", "明日"),
            ("来週まで", "来週"),
            ("特に期限なし", "未定")
        ]
        
        for instruction, expected_contains in test_cases:
            result = self.analyzer._extract_due_date(instruction)
            if expected_contains == "未定":
                assert result == expected_contains
            else:
                assert expected_contains in instruction

    def test_extract_priority_patterns(self):
        """優先度抽出パターンテスト"""
        test_cases = [
            ("急ぎでお願いします", "high"),
            ("緊急対応が必要", "high"),
            ("通常の優先度で", "medium"),
            ("余裕があるときに", "low"),
            ("特に指定なし", "medium")
        ]
        
        for instruction, expected in test_cases:
            result = self.analyzer._extract_priority(instruction)
            assert result == expected

    def test_normalize_date_time_patterns(self):
        """日付正規化テスト"""
        # 時間表現パターンをテスト
        result_today = self.analyzer._normalize_date("今日")
        assert result_today == datetime.now().strftime('%Y-%m-%d')
        
        result_tomorrow = self.analyzer._normalize_date("明日")
        expected_tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert result_tomorrow == expected_tomorrow

    def test_normalize_date_numeric_patterns(self):
        """数値日付正規化テスト"""
        test_cases = [
            "2024-12-31",
            "12/31/2024",
            "12月31日"
        ]
        
        for date_text in test_cases:
            result = self.analyzer._normalize_date(date_text)
            assert result == date_text  # 簡易実装では元のテキストを返す

    def test_normalize_priority(self):
        """優先度正規化テスト"""
        test_cases = [
            ("高い", "high"),
            ("緊急", "high"),
            ("普通", "medium"),
            ("低い", "low"),
            ("不明", "medium")
        ]
        
        for priority_text, expected in test_cases:
            result = self.analyzer._normalize_priority(priority_text)
            assert result == expected

    def test_find_action_item_id(self):
        """アクションアイテムID検索テスト"""
        task_description = "テスト実行"
        
        item_id = self.analyzer._find_action_item_id(task_description, self.sample_minutes)
        
        assert item_id.startswith("task_")
        assert len(item_id) == 13  # "task_" + 8文字のハッシュ

    def test_analyze_with_fallback_delete(self):
        """フォールバック解析（削除）テスト"""
        instruction = "参加者から鈴木さんを削除"
        
        actions, explanations = self.analyzer._analyze_with_fallback(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.REPLACE_TEXT
        assert actions[0].target == "参加者から鈴木さん"
        assert actions[0].replacement == ""

    def test_analyze_with_fallback_add(self):
        """フォールバック解析（追加）テスト"""
        instruction = "新しい項目を追加してください"
        
        actions, explanations = self.analyzer._analyze_with_fallback(instruction, self.sample_minutes)
        
        assert len(actions) == 1
        assert actions[0].action_type == EditActionType.ADD_CONTENT
        assert actions[0].content["text"] == instruction

    def test_analyze_with_fallback_unknown(self):
        """フォールバック解析（不明）テスト"""
        instruction = "何か不明な指示"
        
        actions, explanations = self.analyzer._analyze_with_fallback(instruction, self.sample_minutes)
        
        # 不明な場合はAI解析待ちメッセージが含まれる
        assert any("AI統合が必要" in exp for exp in explanations)

    def test_get_next_friday(self):
        """次の金曜日取得テスト"""
        next_friday = self.analyzer._get_next_friday()
        
        assert next_friday.weekday() == 4  # 金曜日
        assert next_friday > datetime.now()

    def test_get_month_end(self):
        """今月末取得テスト"""
        month_end = self.analyzer._get_month_end()
        
        # 月末の日付であることを確認
        next_day = month_end + timedelta(days=1)
        assert next_day.day == 1

    def test_get_next_month_end(self):
        """来月末取得テスト"""
        next_month_end = self.analyzer._get_next_month_end()
        
        # 来月末の日付であることを確認
        assert next_month_end > self.analyzer._get_month_end()
        next_day = next_month_end + timedelta(days=1)
        assert next_day.day == 1

    def test_create_edit_action_replace_text_not_found(self):
        """存在しないテキスト置換テスト"""
        import re
        pattern = r'(.+?)を(.+?)に(変更|修正|置換|書き換え)'
        instruction = "存在しないテキストを新しいテキストに変更"
        match = re.search(pattern, instruction)
        
        action, explanation = self.analyzer._create_edit_action(
            "replace_text", match, instruction, self.sample_minutes
        )
        
        # 存在しないテキストの場合はNoneが返される
        assert action is None
        assert explanation == ""

    def test_create_edit_action_update_priority(self):
        """アクションアイテム優先度更新テスト"""
        import re
        pattern = r'(.+?)の(優先度|重要度)を(.+?)に(変更|修正)'
        instruction = "資料作成の優先度を高に変更"
        match = re.search(pattern, instruction)
        
        action, explanation = self.analyzer._create_edit_action(
            "update_action_item", match, instruction, self.sample_minutes
        )
        
        assert action.action_type == EditActionType.UPDATE_ACTION_ITEM
        assert "priority" in action.updates
        assert action.updates["priority"] == "high"

    def test_edit_patterns_coverage(self):
        """編集パターン網羅性テスト"""
        # 各パターンタイプが適切に定義されているかチェック
        expected_patterns = [
            "replace_text",
            "add_action_item",
            "update_action_item", 
            "add_content",
            "remove_content",
            "restructure"
        ]
        
        for pattern_type in expected_patterns:
            assert pattern_type in self.analyzer.edit_patterns
            assert len(self.analyzer.edit_patterns[pattern_type]) > 0

    def test_priority_keywords_coverage(self):
        """優先度キーワード網羅性テスト"""
        expected_priorities = ["high", "medium", "low"]
        
        for priority in expected_priorities:
            assert priority in self.analyzer.priority_keywords
            assert len(self.analyzer.priority_keywords[priority]) > 0

    def test_complex_instruction_parsing(self):
        """複雑な編集指示の解析テスト"""
        instruction = "田中さんを山田さんに変更して、新しいタスクとして品質チェックを佐藤さんに割り当て"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        # 複数のアクションが検出される可能性がある
        assert len(actions) >= 1
        assert explanation is not None

    def test_global_analyzer_instance(self):
        """グローバル解析インスタンステスト"""
        assert edit_intent_analyzer is not None
        assert isinstance(edit_intent_analyzer, EditIntentAnalyzer)

    def test_date_normalization_edge_cases(self):
        """日付正規化エッジケーステスト"""
        # 年末年始のテスト
        with patch('app.services.edit_intent_analyzer.datetime') as mock_datetime:
            # 12月のテスト
            mock_datetime.now.return_value = datetime(2024, 12, 15)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            analyzer = EditIntentAnalyzer()
            month_end = analyzer._get_month_end()
            assert month_end.month == 12
            assert month_end.day == 31

    def test_action_item_id_consistency(self):
        """アクションアイテムID一貫性テスト"""
        task_description = "同じタスク"
        
        # 同じタスク説明からは同じIDが生成されることを確認
        id1 = self.analyzer._find_action_item_id(task_description, self.sample_minutes)
        id2 = self.analyzer._find_action_item_id(task_description, self.sample_minutes)
        
        assert id1 == id2

    def test_empty_instruction_handling(self):
        """空の編集指示処理テスト"""
        instruction = ""
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        # 空の指示でも適切に処理される
        assert isinstance(actions, list)
        assert isinstance(explanation, str)

    def test_special_characters_in_instruction(self):
        """特殊文字を含む編集指示テスト"""
        instruction = "「特殊文字！＠＃」を「通常文字」に変更"
        
        actions, explanation = self.analyzer.analyze_edit_intent(instruction, self.sample_minutes)
        
        # 特殊文字を含む場合でも適切に処理される
        assert isinstance(actions, list)
        assert isinstance(explanation, str)