"""編集実行エンジン"""
import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from app.models.chat import EditAction, EditActionType, EditScope
from app.utils.logger import get_logger

logger = get_logger(__name__)

class EditExecutor:
    """高度な編集実行エンジン"""
    
    def __init__(self):
        # マークダウンセクション解析パターン
        self.section_patterns = {
            "action_items": [
                r'#+\s*(?:アクション|action|todo|タスク|課題)(?:アイテム|item)?\s*',
                r'#+\s*今後の(?:作業|予定|課題)\s*',
                r'#+\s*(?:決定|決定事項|今後の対応)\s*'
            ],
            "decisions": [
                r'#+\s*(?:決定|決定事項|結論|合意事項)\s*',
                r'#+\s*(?:決まったこと|確定事項)\s*'
            ],
            "discussion": [
                r'#+\s*(?:議論|討議|話し合い|検討事項)\s*',
                r'#+\s*(?:議論内容|討議内容)\s*'
            ]
        }
    
    def execute_edit_actions(
        self,
        original_minutes: str,
        edit_actions: List[EditAction]
    ) -> Tuple[str, List[str]]:
        """
        編集アクションを実行
        
        Args:
            original_minutes: 元の議事録
            edit_actions: 編集アクションリスト
        
        Returns:
            Tuple: (更新後の議事録, 変更内容サマリー)
        """
        logger.info(f"編集実行開始: {len(edit_actions)}件のアクション")
        
        updated_minutes = original_minutes
        changes_summary = []
        
        # アクションを種類別に分類して実行順序を最適化
        sorted_actions = self._sort_actions_by_priority(edit_actions)
        
        for action in sorted_actions:
            try:
                result, summary = self._execute_single_action(updated_minutes, action)
                if result != updated_minutes:  # 変更があった場合
                    updated_minutes = result
                    changes_summary.append(summary)
                    logger.debug(f"編集実行: {summary}")
                else:
                    logger.warning(f"編集実行失敗: {action.description}")
                    
            except Exception as e:
                logger.error(f"編集実行エラー: {action.description} - {e}", exc_info=True)
                changes_summary.append(f"編集失敗: {action.description}")
        
        logger.info(f"編集実行完了: {len(changes_summary)}件の変更適用")
        return updated_minutes, changes_summary
    
    def _sort_actions_by_priority(self, actions: List[EditAction]) -> List[EditAction]:
        """編集アクションを実行優先度でソート"""
        priority_order = {
            EditActionType.REPLACE_TEXT: 1,      # テキスト置換は最初
            EditActionType.UPDATE_ACTION_ITEM: 2, # 既存アイテム更新
            EditActionType.ADD_CONTENT: 3,       # 内容追加
            EditActionType.ADD_ACTION_ITEM: 4,   # 新規アイテム追加
            EditActionType.RESTRUCTURE: 5       # 構造変更は最後
        }
        
        return sorted(actions, key=lambda x: priority_order.get(x.action_type, 999))
    
    def _execute_single_action(
        self,
        minutes: str,
        action: EditAction
    ) -> Tuple[str, str]:
        """
        単一の編集アクションを実行
        
        Args:
            minutes: 現在の議事録
            action: 編集アクション
        
        Returns:
            Tuple: (更新後の議事録, 変更サマリー)
        """
        if action.action_type == EditActionType.REPLACE_TEXT:
            return self._execute_replace_text(minutes, action)
        
        elif action.action_type == EditActionType.ADD_ACTION_ITEM:
            return self._execute_add_action_item(minutes, action)
        
        elif action.action_type == EditActionType.UPDATE_ACTION_ITEM:
            return self._execute_update_action_item(minutes, action)
        
        elif action.action_type == EditActionType.ADD_CONTENT:
            return self._execute_add_content(minutes, action)
        
        elif action.action_type == EditActionType.RESTRUCTURE:
            return self._execute_restructure(minutes, action)
        
        else:
            logger.warning(f"未対応の編集タイプ: {action.action_type}")
            return minutes, f"未対応の編集: {action.description}"
    
    def _execute_replace_text(
        self,
        minutes: str,
        action: EditAction
    ) -> Tuple[str, str]:
        """テキスト置換を実行"""
        if not action.target or action.replacement is None:
            return minutes, "置換対象または置換テキストが不正"
        
        original_count = minutes.count(action.target)
        if original_count == 0:
            return minutes, f"置換対象「{action.target}」が見つかりません"
        
        if action.scope == EditScope.ALL:
            # 全体置換
            updated_minutes = minutes.replace(action.target, action.replacement)
            return updated_minutes, f"「{action.target}」→「{action.replacement}」({original_count}箇所)"
        
        elif action.scope == EditScope.SPECIFIC:
            # 最初の1箇所のみ置換
            updated_minutes = minutes.replace(action.target, action.replacement, 1)
            return updated_minutes, f"「{action.target}」→「{action.replacement}」(1箇所)"
        
        else:
            # デフォルトは全体置換
            updated_minutes = minutes.replace(action.target, action.replacement)
            return updated_minutes, f"「{action.target}」→「{action.replacement}」({original_count}箇所)"
    
    def _execute_add_action_item(
        self,
        minutes: str,
        action: EditAction
    ) -> Tuple[str, str]:
        """アクションアイテム追加を実行"""
        if not action.content or "task" not in action.content:
            return minutes, "アクションアイテムの内容が不正"
        
        task = action.content.get("task", "")
        assignee = action.content.get("assignee", "未定")
        due_date = action.content.get("due_date", "未定")
        priority = action.content.get("priority", "medium")
        
        # 優先度を日本語に変換
        priority_jp = {"high": "高", "medium": "中", "low": "低"}.get(priority, "中")
        
        # アクションアイテム形式を生成
        new_item = f"- **{task}** (担当: {assignee}, 期限: {due_date}, 優先度: {priority_jp})"
        
        # アクションアイテムセクションを探す
        action_section_start = self._find_action_items_section(minutes)
        
        if action_section_start is not None:
            # 既存のアクションアイテムセクションに追加
            lines = minutes.split('\n')
            insert_pos = action_section_start + 1
            
            # セクション内の最後の位置を探す
            for i in range(insert_pos, len(lines)):
                if lines[i].strip() == "" or lines[i].startswith('#'):
                    insert_pos = i
                    break
            
            lines.insert(insert_pos, new_item)
            updated_minutes = '\n'.join(lines)
            
        else:
            # アクションアイテムセクションが存在しない場合は作成
            new_section = f"\n\n## アクションアイテム\n\n{new_item}"
            updated_minutes = minutes + new_section
        
        return updated_minutes, f"アクションアイテム追加: {task} (担当: {assignee})"
    
    def _execute_update_action_item(
        self,
        minutes: str,
        action: EditAction
    ) -> Tuple[str, str]:
        """アクションアイテム更新を実行"""
        if not action.item_id and not action.updates:
            return minutes, "更新対象または更新内容が不正"
        
        # 議事録内のアクションアイテムを検索・更新
        lines = minutes.split('\n')
        updated_lines = []
        found = False
        
        for line in lines:
            if self._is_action_item_line(line):
                # アクションアイテムの行を更新
                updated_line = self._update_action_item_line(line, action.updates)
                if updated_line != line:
                    found = True
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        
        if found:
            updated_minutes = '\n'.join(updated_lines)
            changes = ", ".join([f"{k}: {v}" for k, v in action.updates.items()])
            return updated_minutes, f"アクションアイテム更新: {changes}"
        else:
            return minutes, "更新対象のアクションアイテムが見つかりません"
    
    def _execute_add_content(
        self,
        minutes: str,
        action: EditAction
    ) -> Tuple[str, str]:
        """内容追加を実行"""
        if not action.content or "text" not in action.content:
            return minutes, "追加する内容が不正"
        
        content_to_add = action.content["text"]
        section_name = action.content.get("section", "")
        
        if section_name:
            # 指定されたセクションに追加
            section_pos = self._find_section_position(minutes, section_name)
            if section_pos is not None:
                lines = minutes.split('\n')
                # セクション内の適切な位置に挿入
                insert_pos = self._find_section_end_position(lines, section_pos)
                lines.insert(insert_pos, f"\n{content_to_add}")
                updated_minutes = '\n'.join(lines)
                return updated_minutes, f"「{section_name}」セクションに内容追加"
        
        # セクション指定がない場合は末尾に追加
        updated_minutes = minutes + f"\n\n{content_to_add}"
        return updated_minutes, "内容を末尾に追加"
    
    def _execute_restructure(
        self,
        minutes: str,
        action: EditAction
    ) -> Tuple[str, str]:
        """構造変更を実行"""
        # 構造変更は複雑なため、基本的な実装のみ
        logger.info("構造変更は基本実装のみ対応")
        return minutes, "構造変更: 基本実装"
    
    def _find_action_items_section(self, minutes: str) -> Optional[int]:
        """アクションアイテムセクションの開始行を探す"""
        lines = minutes.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in self.section_patterns["action_items"]:
                if re.search(pattern, line, re.IGNORECASE):
                    return i
        
        return None
    
    def _find_section_position(self, minutes: str, section_name: str) -> Optional[int]:
        """指定されたセクションの位置を探す"""
        lines = minutes.split('\n')
        
        # セクション名の候補パターン
        patterns = [
            rf'#+\s*{re.escape(section_name)}\s*',
            rf'#+\s*.*{re.escape(section_name)}.*',
        ]
        
        for i, line in enumerate(lines):
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return i
        
        return None
    
    def _find_section_end_position(self, lines: List[str], section_start: int) -> int:
        """セクションの終了位置を探す"""
        for i in range(section_start + 1, len(lines)):
            line = lines[i].strip()
            # 新しいセクション（#で始まる）または空行の連続で終了
            if line.startswith('#') or (line == "" and i < len(lines) - 1 and lines[i + 1].startswith('#')):
                return i
        
        return len(lines)
    
    def _is_action_item_line(self, line: str) -> bool:
        """行がアクションアイテムかどうか判定"""
        line_stripped = line.strip()
        return (line_stripped.startswith('- ') or 
                line_stripped.startswith('* ') or
                line_stripped.startswith('+ ') or
                re.match(r'^\d+\.\s', line_stripped))
    
    def _update_action_item_line(self, line: str, updates: Dict) -> str:
        """アクションアイテム行を更新"""
        updated_line = line
        
        for field, new_value in updates.items():
            if field == "assignee":
                # 担当者を更新
                updated_line = re.sub(
                    r'(担当[:：]\s*)([^,）\s]+)',
                    rf'\1{new_value}',
                    updated_line
                )
            elif field == "due_date":
                # 期限を更新
                updated_line = re.sub(
                    r'(期限[:：]\s*)([^,）\s]+)',
                    rf'\1{new_value}',
                    updated_line
                )
            elif field == "priority":
                # 優先度を更新
                priority_jp = {"high": "高", "medium": "中", "low": "低"}.get(new_value, new_value)
                updated_line = re.sub(
                    r'(優先度[:：]\s*)([^,）\s]+)',
                    rf'\1{priority_jp}',
                    updated_line
                )
        
        return updated_line

# グローバルな編集実行エンジンインスタンス
edit_executor = EditExecutor()