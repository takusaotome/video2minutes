"""編集インテント解析サービス"""
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from app.models.chat import (
    EditAction,
    EditActionType,
    EditScope,
    MessageIntent
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

class EditIntentAnalyzer:
    """編集インテント解析エンジン"""
    
    def __init__(self):
        # 編集パターンの定義
        self.edit_patterns = {
            "replace_text": [
                r'(.+?)を(.+?)に(変更|修正|置換|書き換え)',
                r'(.+?)から(.+?)に(変更|修正|置換)',
                r'(.+?)の(.+?)を(.+?)に(変更|修正)',
                r'「(.+?)」を「(.+?)」に(変更|修正|置換)',
            ],
            "add_action_item": [
                r'(.+?)の?(タスク|アクションアイテム|TODO)を?追加',
                r'(.+?)に(.+?)の(タスク|作業)を(追加|割り当て)',
                r'(.+?)さんに(.+?)を(お願い|依頼|追加)',
                r'新しい(タスク|アクションアイテム)[：:]?(.+)',
            ],
            "update_action_item": [
                r'(.+?)の(担当者?|責任者?)を(.+?)に(変更|修正)',
                r'(.+?)の(期限|締切|デッドライン)を(.+?)に(変更|修正|延期)',
                r'(.+?)の(優先度|重要度)を(.+?)に(変更|修正)',
                r'(.+?)タスクの(.+?)を(.+?)に(変更|修正)',
            ],
            "add_content": [
                r'(.+?)に(.+?)を(追加|記載|記入)',
                r'(.+?)セクションに(.+?)を(追加|記載)',
                r'(.+?)の(内容|詳細)を(追加|補強)',
                r'(.+?)について(.+?)を(追記|記載)',
            ],
            "remove_content": [
                r'(.+?)を(削除|除去|消去)',
                r'(.+?)の(.+?)を(削除|除去)',
                r'(.+?)から(.+?)を(削除|除去)',
            ],
            "restructure": [
                r'(.+?)の(構成|構造|順序)を(変更|修正|整理)',
                r'(.+?)と(.+?)の(順番|位置)を(入れ替え|交換)',
                r'セクション(.+?)を(.+?)に(移動|変更)',
            ]
        }
        
        # 日本語の時間表現パターン
        self.time_patterns = {
            r'今日': datetime.now().strftime('%Y-%m-%d'),
            r'明日': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            r'来週': (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d'),
            r'今週金曜日?': self._get_next_friday().strftime('%Y-%m-%d'),
            r'来週金曜日?': (self._get_next_friday() + timedelta(weeks=1)).strftime('%Y-%m-%d'),
            r'今月末': self._get_month_end().strftime('%Y-%m-%d'),
            r'来月末': self._get_next_month_end().strftime('%Y-%m-%d'),
        }
        
        # 優先度キーワード
        self.priority_keywords = {
            "high": ["高", "急", "緊急", "重要", "優先", "至急"],
            "medium": ["中", "普通", "通常", "標準"],
            "low": ["低", "後回し", "余裕", "ゆっくり"]
        }
    
    def analyze_edit_intent(self, edit_instruction: str, current_minutes: str) -> Tuple[List[EditAction], str]:
        """
        編集指示を解析して編集アクションを生成
        
        Args:
            edit_instruction: 編集指示文
            current_minutes: 現在の議事録内容
        
        Returns:
            Tuple: (編集アクションリスト, 解析説明)
        """
        logger.info(f"編集インテント解析開始: {edit_instruction[:50]}...")
        
        edit_actions = []
        explanations = []
        
        # 各編集パターンをチェック
        for action_type, patterns in self.edit_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, edit_instruction, re.IGNORECASE)
                if match:
                    action, explanation = self._create_edit_action(
                        action_type, match, edit_instruction, current_minutes
                    )
                    if action:
                        edit_actions.append(action)
                        explanations.append(explanation)
                        break
        
        # 複合的な編集指示の処理
        if not edit_actions:
            # AIベースの解析にフォールバック
            edit_actions, explanations = self._analyze_with_fallback(
                edit_instruction, current_minutes
            )
        
        # 説明テキストを生成
        if explanations:
            explanation_text = "以下の編集を実行します：\n" + "\n".join([f"- {exp}" for exp in explanations])
        else:
            explanation_text = f"編集指示「{edit_instruction}」を解析しましたが、具体的なアクションを特定できませんでした。"
        
        logger.info(f"編集インテント解析完了: {len(edit_actions)}件のアクション生成")
        
        return edit_actions, explanation_text
    
    def _create_edit_action(
        self,
        action_type: str,
        match: re.Match,
        instruction: str,
        current_minutes: str
    ) -> Tuple[Optional[EditAction], str]:
        """
        マッチ結果から編集アクションを作成
        
        Args:
            action_type: アクションタイプ
            match: 正規表現マッチ結果
            instruction: 編集指示
            current_minutes: 現在の議事録
        
        Returns:
            Tuple: (編集アクション, 説明)
        """
        groups = match.groups()
        
        if action_type == "replace_text":
            target = groups[0].strip()
            replacement = groups[1].strip()
            
            # 置換対象が議事録に存在するかチェック
            if target in current_minutes:
                action = EditAction(
                    action_type=EditActionType.REPLACE_TEXT,
                    target=target,
                    replacement=replacement,
                    scope=EditScope.ALL,
                    description=f"「{target}」を「{replacement}」に置換"
                )
                explanation = f"「{target}」を「{replacement}」に置換"
                return action, explanation
            else:
                logger.warning(f"置換対象「{target}」が議事録に見つかりません")
                return None, ""
        
        elif action_type == "add_action_item":
            # アクションアイテム追加の詳細解析
            task_description = groups[0].strip()
            
            # 担当者の抽出
            assignee = self._extract_assignee(instruction)
            
            # 期限の抽出
            due_date = self._extract_due_date(instruction)
            
            # 優先度の抽出
            priority = self._extract_priority(instruction)
            
            action = EditAction(
                action_type=EditActionType.ADD_ACTION_ITEM,
                content={
                    "task": task_description,
                    "assignee": assignee,
                    "due_date": due_date,
                    "priority": priority
                },
                description=f"新規アクションアイテム「{task_description}」を追加（担当: {assignee}, 期限: {due_date}）"
            )
            explanation = f"アクションアイテム「{task_description}」を追加（担当: {assignee}, 期限: {due_date}）"
            return action, explanation
        
        elif action_type == "update_action_item":
            # 既存アクションアイテムの更新
            target_task = groups[0].strip()
            update_field = groups[1].strip()
            new_value = groups[2].strip()
            
            # 議事録から該当するアクションアイテムを特定
            item_id = self._find_action_item_id(target_task, current_minutes)
            
            updates = {}
            if "担当" in update_field:
                updates["assignee"] = new_value
            elif "期限" in update_field or "締切" in update_field:
                updates["due_date"] = self._normalize_date(new_value)
            elif "優先" in update_field:
                updates["priority"] = self._normalize_priority(new_value)
            
            action = EditAction(
                action_type=EditActionType.UPDATE_ACTION_ITEM,
                item_id=item_id,
                updates=updates,
                description=f"アクションアイテム「{target_task}」の{update_field}を「{new_value}」に変更"
            )
            explanation = f"「{target_task}」の{update_field}を「{new_value}」に変更"
            return action, explanation
        
        elif action_type == "add_content":
            # 内容追加
            target_section = groups[0].strip()
            content = groups[1].strip()
            
            action = EditAction(
                action_type=EditActionType.ADD_CONTENT,
                content={
                    "section": target_section,
                    "text": content
                },
                description=f"「{target_section}」に「{content}」を追加"
            )
            explanation = f"「{target_section}」に「{content}」を追加"
            return action, explanation
        
        return None, ""
    
    def _extract_assignee(self, instruction: str) -> str:
        """編集指示から担当者を抽出"""
        # 担当者パターン
        assignee_patterns = [
            r'担当[：:]?\s*(.+?)(?:[,、\s]|$)',
            r'(.+?)さんに',
            r'(.+?)が担当',
            r'責任者[：:]?\s*(.+?)(?:[,、\s]|$)',
        ]
        
        for pattern in assignee_patterns:
            match = re.search(pattern, instruction)
            if match:
                assignee = match.group(1).strip()
                # 敬語を除去
                assignee = re.sub(r'さん$', '', assignee)
                return assignee
        
        return "未定"
    
    def _extract_due_date(self, instruction: str) -> str:
        """編集指示から期限を抽出"""
        # 期限パターン
        due_patterns = [
            r'期限[：:]?\s*(.+?)(?:[,、\s]|$)',
            r'締切[：:]?\s*(.+?)(?:[,、\s]|$)',
            r'(.+?)まで',
            r'(.+?)期限',
        ]
        
        for pattern in due_patterns:
            match = re.search(pattern, instruction)
            if match:
                date_text = match.group(1).strip()
                return self._normalize_date(date_text)
        
        return "未定"
    
    def _extract_priority(self, instruction: str) -> str:
        """編集指示から優先度を抽出"""
        instruction_lower = instruction.lower()
        
        for priority, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword in instruction_lower:
                    return priority
        
        return "medium"
    
    def _normalize_date(self, date_text: str) -> str:
        """日付表現を正規化"""
        # 時間表現パターンをチェック
        for pattern, normalized_date in self.time_patterns.items():
            if re.search(pattern, date_text, re.IGNORECASE):
                return normalized_date
        
        # 数値形式の日付パターン
        date_patterns = [
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            r'(\d{1,2})月(\d{1,2})日',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                # 日付形式の正規化処理
                # 簡略化のため、元のテキストをそのまま返す
                return date_text
        
        return date_text
    
    def _normalize_priority(self, priority_text: str) -> str:
        """優先度を正規化"""
        priority_text_lower = priority_text.lower()
        
        for priority, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword in priority_text_lower:
                    return priority
        
        return "medium"
    
    def _find_action_item_id(self, task_description: str, current_minutes: str) -> str:
        """議事録内のアクションアイテムIDを検索"""
        # 簡単な実装: タスク説明に基づいてIDを生成
        # 実際の実装では、議事録の構造を解析してIDを特定
        import hashlib
        task_hash = hashlib.md5(task_description.encode('utf-8')).hexdigest()[:8]
        return f"task_{task_hash}"
    
    def _analyze_with_fallback(
        self,
        instruction: str,
        current_minutes: str
    ) -> Tuple[List[EditAction], List[str]]:
        """
        パターンマッチに失敗した場合のフォールバック解析
        """
        logger.info(f"フォールバック解析実行: {instruction}")
        
        # 基本的なキーワードベース解析
        actions = []
        explanations = []
        
        # 削除系の処理
        if any(keyword in instruction for keyword in ["削除", "除去", "消去", "取り除"]):
            # 削除対象を特定
            delete_patterns = [
                r'(.+?)を(削除|除去|消去)',
                r'(.+?)から(.+?)を(削除|除去)',
            ]
            
            for pattern in delete_patterns:
                match = re.search(pattern, instruction)
                if match:
                    target = match.group(1).strip()
                    action = EditAction(
                        action_type=EditActionType.REPLACE_TEXT,
                        target=target,
                        replacement="",
                        scope=EditScope.SPECIFIC,
                        description=f"「{target}」を削除"
                    )
                    actions.append(action)
                    explanations.append(f"「{target}」を削除")
                    break
        
        # 一般的な追加処理
        elif any(keyword in instruction for keyword in ["追加", "記載", "記入", "補強"]):
            action = EditAction(
                action_type=EditActionType.ADD_CONTENT,
                content={"text": instruction},
                description="内容を追加"
            )
            actions.append(action)
            explanations.append("指定された内容を追加")
        
        # 不明な場合はAI解析待ちとして記録
        if not actions:
            explanations.append("詳細な解析にはAI統合が必要です。基本的なテキスト編集として処理します。")
        
        return actions, explanations
    
    def _get_next_friday(self) -> datetime:
        """次の金曜日を取得"""
        today = datetime.now()
        days_ahead = 4 - today.weekday()  # 金曜日は4
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_month_end(self) -> datetime:
        """今月末を取得"""
        today = datetime.now()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        return next_month - timedelta(days=1)
    
    def _get_next_month_end(self) -> datetime:
        """来月末を取得"""
        today = datetime.now()
        if today.month == 11:
            next_next_month = today.replace(year=today.year + 1, month=1, day=1)
        elif today.month == 12:
            next_next_month = today.replace(year=today.year + 1, month=2, day=1)
        else:
            next_next_month = today.replace(month=today.month + 2, day=1)
        return next_next_month - timedelta(days=1)

# グローバルな編集インテント解析インスタンス
edit_intent_analyzer = EditIntentAnalyzer()