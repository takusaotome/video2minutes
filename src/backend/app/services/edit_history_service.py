"""編集履歴管理サービス"""
import json
import difflib
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)

class EditHistoryService:
    """編集履歴管理と取り消し機能サービス"""
    
    def __init__(self):
        self.max_history_entries = 50  # 最大履歴保存数
    
    def create_edit_entry(
        self,
        task_id: str,
        session_id: str,
        message_id: str,
        edit_actions: List,
        original_minutes: str,
        updated_minutes: str,
        user_description: str = ""
    ) -> Dict:
        """
        新しい編集エントリを作成
        
        Args:
            task_id: タスクID
            session_id: セッションID
            message_id: メッセージID
            edit_actions: 編集アクション
            original_minutes: 編集前議事録
            updated_minutes: 編集後議事録
            user_description: ユーザー説明
        
        Returns:
            Dict: 編集履歴エントリ
        """
        # Import at runtime to avoid circular imports
        from app.models.chat import EditHistory
        import uuid
        
        # 変更内容を詳細分析
        changes_summary = self.analyze_changes(original_minutes, updated_minutes)
        
        # 編集統計を計算
        edit_stats = self.calculate_edit_statistics(
            original_minutes, updated_minutes, edit_actions
        )
        
        edit_history = EditHistory(
            task_id=task_id,
            session_id=session_id,
            message_id=message_id,
            edit_actions=edit_actions,
            changes_summary=changes_summary,
            original_minutes=original_minutes,
            updated_minutes=updated_minutes
        )
        
        # 追加のメタデータ
        edit_entry = {
            "edit_id": edit_history.edit_id,
            "task_id": task_id,
            "session_id": session_id,
            "message_id": message_id,
            "timestamp": edit_history.timestamp.isoformat(),
            "edit_actions": [self._serialize_edit_action(action) for action in edit_actions],
            "changes_summary": changes_summary,
            "original_minutes": original_minutes,
            "updated_minutes": updated_minutes,
            "user_description": user_description,
            "edit_statistics": edit_stats,
            "reverted": False,
            "parent_edit_id": None,  # 元の編集のID（取り消し時）
            "edit_type": "normal",   # normal, undo, redo
            "content_hash": self._calculate_content_hash(updated_minutes),
            "diff_html": self._generate_diff_html(original_minutes, updated_minutes)
        }
        
        logger.info(f"編集エントリ作成: {edit_history.edit_id[:8]}... ({len(changes_summary)}件の変更)")
        
        return edit_entry
    
    def analyze_changes(self, original: str, updated: str) -> List[str]:
        """
        変更内容を詳細分析
        
        Args:
            original: 元のテキスト
            updated: 更新後テキスト
        
        Returns:
            List[str]: 変更内容の要約
        """
        changes = []
        
        # 基本統計
        original_lines = original.split('\n')
        updated_lines = updated.split('\n')
        
        if len(updated_lines) > len(original_lines):
            added_lines = len(updated_lines) - len(original_lines)
            changes.append(f"{added_lines}行追加")
        elif len(updated_lines) < len(original_lines):
            removed_lines = len(original_lines) - len(updated_lines)
            changes.append(f"{removed_lines}行削除")
        
        # 文字数変化
        char_diff = len(updated) - len(original)
        if char_diff > 0:
            changes.append(f"{char_diff}文字追加")
        elif char_diff < 0:
            changes.append(f"{abs(char_diff)}文字削除")
        
        # 差分分析
        differ = difflib.unified_diff(
            original_lines, updated_lines, lineterm='', n=0
        )
        
        additions = 0
        deletions = 0
        modifications = 0
        
        for line in differ:
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
        
        if additions > 0:
            changes.append(f"内容追加: {additions}箇所")
        if deletions > 0:
            changes.append(f"内容削除: {deletions}箇所")
        
        # セクション変更検知
        section_changes = self._detect_section_changes(original, updated)
        changes.extend(section_changes)
        
        return changes if changes else ["軽微な変更"]
    
    def _detect_section_changes(self, original: str, updated: str) -> List[str]:
        """
        セクション単位の変更を検知
        
        Args:
            original: 元のテキスト
            updated: 更新後テキスト
        
        Returns:
            List[str]: セクション変更の詳細
        """
        import re
        
        section_pattern = r'^#+\s*(.+)$'
        
        original_sections = []
        updated_sections = []
        
        for line in original.split('\n'):
            match = re.match(section_pattern, line.strip())
            if match:
                original_sections.append(match.group(1).strip())
        
        for line in updated.split('\n'):
            match = re.match(section_pattern, line.strip())
            if match:
                updated_sections.append(match.group(1).strip())
        
        changes = []
        
        # 新しいセクション
        new_sections = set(updated_sections) - set(original_sections)
        if new_sections:
            changes.append(f"新規セクション追加: {', '.join(list(new_sections)[:3])}")
        
        # 削除されたセクション
        removed_sections = set(original_sections) - set(updated_sections)
        if removed_sections:
            changes.append(f"セクション削除: {', '.join(list(removed_sections)[:3])}")
        
        return changes
    
    def calculate_edit_statistics(
        self,
        original: str,
        updated: str,
        edit_actions: List
    ) -> Dict:
        """
        編集統計を計算
        
        Args:
            original: 元のテキスト
            updated: 更新後テキスト
            edit_actions: 編集アクション
        
        Returns:
            Dict: 編集統計
        """
        return {
            "original_length": len(original),
            "updated_length": len(updated),
            "character_change": len(updated) - len(original),
            "line_count_original": len(original.split('\n')),
            "line_count_updated": len(updated.split('\n')),
            "edit_actions_count": len(edit_actions),
            "edit_complexity": self._calculate_edit_complexity(edit_actions),
            "similarity_score": self._calculate_similarity(original, updated)
        }
    
    def _calculate_edit_complexity(self, edit_actions: List) -> str:
        """
        編集の複雑さを計算
        
        Args:
            edit_actions: 編集アクション
        
        Returns:
            str: 複雑さレベル
        """
        if len(edit_actions) == 0:
            return "none"
        elif len(edit_actions) == 1:
            return "simple"
        elif len(edit_actions) <= 3:
            return "moderate"
        else:
            return "complex"
    
    def _calculate_similarity(self, original: str, updated: str) -> float:
        """
        テキスト類似度を計算
        
        Args:
            original: 元のテキスト
            updated: 更新後テキスト
        
        Returns:
            float: 類似度 (0-1)
        """
        if not original or not updated:
            return 0.0
        
        # 単語レベルでの類似度計算
        original_words = set(original.split())
        updated_words = set(updated.split())
        
        if not original_words and not updated_words:
            return 1.0
        
        intersection = len(original_words & updated_words)
        union = len(original_words | updated_words)
        
        return intersection / union if union > 0 else 0.0
    
    def create_undo_entry(self, original_edit_entry: Dict) -> Dict:
        """
        取り消し用のエントリを作成
        
        Args:
            original_edit_entry: 元の編集エントリ
        
        Returns:
            Dict: 取り消し用編集エントリ
        """
        import uuid
        
        undo_entry = {
            "edit_id": str(uuid.uuid4()),
            "task_id": original_edit_entry["task_id"],
            "session_id": original_edit_entry["session_id"],
            "message_id": f"undo_{original_edit_entry['message_id']}",
            "timestamp": datetime.now().isoformat(),
            "edit_actions": [],  # 取り消しは逆操作
            "changes_summary": [f"編集を取り消し: {original_edit_entry['edit_id'][:8]}..."],
            "original_minutes": original_edit_entry["updated_minutes"],  # 逆転
            "updated_minutes": original_edit_entry["original_minutes"],  # 逆転
            "user_description": f"編集の取り消し: {original_edit_entry.get('user_description', '')}",
            "edit_statistics": self.calculate_edit_statistics(
                original_edit_entry["updated_minutes"],
                original_edit_entry["original_minutes"],
                []
            ),
            "reverted": False,
            "parent_edit_id": original_edit_entry["edit_id"],
            "edit_type": "undo",
            "content_hash": self._calculate_content_hash(original_edit_entry["original_minutes"]),
            "diff_html": self._generate_diff_html(
                original_edit_entry["updated_minutes"],
                original_edit_entry["original_minutes"]
            )
        }
        
        logger.info(f"取り消しエントリ作成: {undo_entry['edit_id'][:8]}... -> {original_edit_entry['edit_id'][:8]}...")
        
        return undo_entry
    
    def validate_undo_operation(self, edit_entry: Dict, current_minutes: str) -> Tuple[bool, str]:
        """
        取り消し操作の妥当性を検証
        
        Args:
            edit_entry: 取り消し対象の編集エントリ
            current_minutes: 現在の議事録
        
        Returns:
            Tuple[bool, str]: (妥当性, エラーメッセージ)
        """
        # 既に取り消し済みかチェック
        if edit_entry.get("reverted", False):
            return False, "この編集は既に取り消し済みです"
        
        # 現在の内容が編集後の内容と一致するかチェック
        current_hash = self._calculate_content_hash(current_minutes)
        expected_hash = edit_entry.get("content_hash")
        
        if current_hash != expected_hash:
            return False, "議事録が編集後から変更されているため、安全に取り消しできません"
        
        # 編集タイプのチェック
        if edit_entry.get("edit_type") == "undo":
            return False, "取り消し操作を取り消すことはできません（redo機能を使用してください）"
        
        return True, ""
    
    def create_comparison_data(self, edit_entries: List[Dict]) -> Dict:
        """
        編集履歴の比較データを作成
        
        Args:
            edit_entries: 編集エントリのリスト
        
        Returns:
            Dict: 比較データ
        """
        if not edit_entries:
            return {"versions": [], "timeline": []}
        
        # 時系列順にソート
        sorted_entries = sorted(edit_entries, key=lambda x: x["timestamp"])
        
        versions = []
        timeline = []
        
        for i, entry in enumerate(sorted_entries):
            version_data = {
                "version_number": i + 1,
                "edit_id": entry["edit_id"],
                "timestamp": entry["timestamp"],
                "changes_summary": entry["changes_summary"],
                "edit_type": entry.get("edit_type", "normal"),
                "user_description": entry.get("user_description", ""),
                "content_length": entry["edit_statistics"]["updated_length"],
                "similarity_to_previous": 0.0
            }
            
            if i > 0:
                # 前のバージョンとの類似度を計算
                prev_content = sorted_entries[i-1]["updated_minutes"]
                current_content = entry["updated_minutes"]
                version_data["similarity_to_previous"] = self._calculate_similarity(
                    prev_content, current_content
                )
            
            versions.append(version_data)
            
            # タイムライン用データ
            timeline_entry = {
                "timestamp": entry["timestamp"],
                "event_type": entry.get("edit_type", "edit"),
                "description": f"編集 #{i+1}: {', '.join(entry['changes_summary'][:2])}",
                "edit_id": entry["edit_id"]
            }
            timeline.append(timeline_entry)
        
        return {
            "versions": versions,
            "timeline": timeline,
            "total_versions": len(versions),
            "total_edits": len([e for e in sorted_entries if e.get("edit_type", "normal") == "normal"]),
            "total_undos": len([e for e in sorted_entries if e.get("edit_type") == "undo"])
        }
    
    def _serialize_edit_action(self, action) -> Dict:
        """
        編集アクションをシリアライズ
        
        Args:
            action: 編集アクション
        
        Returns:
            Dict: シリアライズされたアクション
        """
        return {
            "action_type": action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type),
            "target": action.target,
            "replacement": action.replacement,
            "scope": action.scope.value if hasattr(action, 'scope') and hasattr(action.scope, 'value') else None,
            "content": action.content,
            "item_id": action.item_id,
            "updates": action.updates,
            "description": action.description
        }
    
    def _calculate_content_hash(self, content: str) -> str:
        """
        コンテンツのハッシュを計算
        
        Args:
            content: コンテンツ
        
        Returns:
            str: ハッシュ値
        """
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _generate_diff_html(self, original: str, updated: str) -> str:
        """
        差分のHTML表示を生成
        
        Args:
            original: 元のテキスト
            updated: 更新後テキスト
        
        Returns:
            str: 差分HTML
        """
        differ = difflib.HtmlDiff()
        return differ.make_table(
            original.splitlines(),
            updated.splitlines(),
            fromdesc="編集前",
            todesc="編集後",
            context=True,
            numlines=3
        )
    
    def optimize_history_storage(self, edit_entries: List[Dict]) -> List[Dict]:
        """
        履歴ストレージを最適化
        
        Args:
            edit_entries: 編集エントリのリスト
        
        Returns:
            List[Dict]: 最適化された編集エントリ
        """
        if len(edit_entries) <= self.max_history_entries:
            return edit_entries
        
        # 時系列順にソート
        sorted_entries = sorted(edit_entries, key=lambda x: x["timestamp"])
        
        # 重要な編集を保持（大きな変更、最近の編集など）
        important_entries = []
        recent_entries = []
        
        # 最新のエントリは必ず保持
        recent_count = min(20, len(sorted_entries))
        recent_entries = sorted_entries[-recent_count:]
        
        # 重要な編集を選定
        for entry in sorted_entries[:-recent_count]:
            stats = entry.get("edit_statistics", {})
            
            # 大きな変更は保持
            if (stats.get("character_change", 0) > 500 or
                stats.get("edit_complexity") in ["complex"] or
                entry.get("edit_type") == "undo"):
                important_entries.append(entry)
        
        # 重要な編集と最近の編集を結合
        optimized_entries = important_entries + recent_entries
        
        # 重複削除
        seen_ids = set()
        final_entries = []
        for entry in optimized_entries:
            if entry["edit_id"] not in seen_ids:
                seen_ids.add(entry["edit_id"])
                final_entries.append(entry)
        
        logger.info(f"履歴最適化: {len(edit_entries)} -> {len(final_entries)}エントリ")
        
        return sorted(final_entries, key=lambda x: x["timestamp"])

# グローバルな編集履歴サービスインスタンス
edit_history_service = EditHistoryService()