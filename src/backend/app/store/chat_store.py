"""チャット機能の永続化ストア"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from app.models.chat import (
    ChatSession,
    ChatMessage,
    EditHistory,
    ChatStats,
    MessageType,
    MessageIntent
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChatPersistentStore:
    """チャット機能の永続化ストア（JSONファイルベース）"""

    def __init__(self, storage_dir: str = "storage/chat"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions_file = self.storage_dir / "sessions.json"
        self.messages_file = self.storage_dir / "messages.json"
        self.edit_history_file = self.storage_dir / "edit_history.json"
        self.stats_file = self.storage_dir / "stats.json"
        
        # メモリ内キャッシュ
        self._sessions_cache: Dict[str, ChatSession] = {}
        self._messages_cache: Dict[str, List[ChatMessage]] = {}  # session_id -> messages
        self._edit_history_cache: Dict[str, EditHistory] = {}  # edit_id -> edit_history
        self._stats_cache: ChatStats = ChatStats()
        
        # 起動時にデータをロード
        self._load_data()

    def _load_data(self) -> None:
        """ファイルからデータを読み込み"""
        try:
            # セッションデータの読み込み
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    
                for session_id, session_dict in sessions_data.items():
                    try:
                        session = ChatSession(**session_dict)
                        self._sessions_cache[session_id] = session
                    except Exception as e:
                        logger.warning(f"セッションの復元に失敗: {session_id} - {e}")
                        
                logger.info(f"チャットセッションデータを読み込み: {len(self._sessions_cache)}件")

            # メッセージデータの読み込み
            if self.messages_file.exists():
                with open(self.messages_file, 'r', encoding='utf-8') as f:
                    messages_data = json.load(f)
                    
                for session_id, messages_list in messages_data.items():
                    try:
                        messages = [ChatMessage(**msg_dict) for msg_dict in messages_list]
                        self._messages_cache[session_id] = messages
                    except Exception as e:
                        logger.warning(f"メッセージの復元に失敗: {session_id} - {e}")
                        
                total_messages = sum(len(msgs) for msgs in self._messages_cache.values())
                logger.info(f"チャットメッセージデータを読み込み: {total_messages}件")

            # 編集履歴データの読み込み
            if self.edit_history_file.exists():
                with open(self.edit_history_file, 'r', encoding='utf-8') as f:
                    edit_history_data = json.load(f)
                    
                for edit_id, edit_dict in edit_history_data.items():
                    try:
                        edit_history = EditHistory(**edit_dict)
                        self._edit_history_cache[edit_id] = edit_history
                    except Exception as e:
                        logger.warning(f"編集履歴の復元に失敗: {edit_id} - {e}")
                        
                logger.info(f"編集履歴データを読み込み: {len(self._edit_history_cache)}件")

            # 統計データの読み込み
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)
                    self._stats_cache = ChatStats(**stats_data)
                    
                logger.info(f"統計データを読み込み完了")
                
        except Exception as e:
            logger.error(f"チャットデータ読み込みエラー: {e}", exc_info=True)

    def _save_data(self) -> None:
        """データをファイルに保存"""
        try:
            # セッションデータの保存
            sessions_data = {}
            for session_id, session in self._sessions_cache.items():
                try:
                    sessions_data[session_id] = session.dict()
                except Exception as e:
                    logger.warning(f"セッションの保存に失敗: {session_id} - {e}")
                    
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2, default=str)

            # メッセージデータの保存
            messages_data = {}
            for session_id, messages in self._messages_cache.items():
                try:
                    messages_data[session_id] = [msg.dict() for msg in messages]
                except Exception as e:
                    logger.warning(f"メッセージの保存に失敗: {session_id} - {e}")
                    
            with open(self.messages_file, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, ensure_ascii=False, indent=2, default=str)

            # 編集履歴データの保存
            edit_history_data = {}
            for edit_id, edit_history in self._edit_history_cache.items():
                try:
                    edit_history_data[edit_id] = edit_history.dict()
                except Exception as e:
                    logger.warning(f"編集履歴の保存に失敗: {edit_id} - {e}")
                    
            with open(self.edit_history_file, 'w', encoding='utf-8') as f:
                json.dump(edit_history_data, f, ensure_ascii=False, indent=2, default=str)

            # 統計データの保存
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self._stats_cache.dict(), f, ensure_ascii=False, indent=2, default=str)
                
            logger.debug(f"チャットデータを保存: {len(self._sessions_cache)}セッション, {sum(len(msgs) for msgs in self._messages_cache.values())}メッセージ")
            
        except Exception as e:
            logger.error(f"チャットデータ保存エラー: {e}", exc_info=True)

    # セッション管理

    def create_session(self, session: ChatSession) -> None:
        """チャットセッションを作成"""
        self._sessions_cache[session.session_id] = session
        self._messages_cache[session.session_id] = []
        
        # 統計を更新
        self._stats_cache.total_sessions += 1
        self._stats_cache.active_sessions += 1
        
        self._save_data()
        logger.info(f"チャットセッションを作成: {session.session_id[:8]}... (タスク: {session.task_id[:8]}...)")

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """チャットセッションを取得"""
        session = self._sessions_cache.get(session_id)
        if session:
            # 最終アクティビティを更新
            session.last_activity = datetime.now()
            self._save_data()
        return session

    def update_session(self, session: ChatSession) -> None:
        """チャットセッションを更新"""
        if session.session_id in self._sessions_cache:
            self._sessions_cache[session.session_id] = session
            self._save_data()
            logger.debug(f"チャットセッションを更新: {session.session_id[:8]}...")

    def delete_session(self, session_id: str) -> bool:
        """チャットセッションを削除"""
        if session_id in self._sessions_cache:
            del self._sessions_cache[session_id]
            
            # 関連メッセージも削除
            if session_id in self._messages_cache:
                del self._messages_cache[session_id]
            
            # 統計を更新
            self._stats_cache.active_sessions = max(0, self._stats_cache.active_sessions - 1)
            
            self._save_data()
            logger.info(f"チャットセッションを削除: {session_id[:8]}...")
            return True
        return False

    def get_sessions_by_task(self, task_id: str) -> List[ChatSession]:
        """タスクIDに関連するセッション一覧を取得"""
        return [session for session in self._sessions_cache.values() if session.task_id == task_id]

    # メッセージ管理

    def add_message(self, message: ChatMessage) -> None:
        """チャットメッセージを追加"""
        if message.session_id not in self._messages_cache:
            self._messages_cache[message.session_id] = []
            
        self._messages_cache[message.session_id].append(message)
        
        # セッションの情報を更新
        if message.session_id in self._sessions_cache:
            session = self._sessions_cache[message.session_id]
            session.last_activity = datetime.now()
            session.total_messages += 1
            
        # 統計を更新
        self._stats_cache.total_messages += 1
        if message.intent == MessageIntent.QUESTION:
            self._stats_cache.total_questions += 1
        elif message.intent == MessageIntent.EDIT_REQUEST:
            self._stats_cache.total_edit_requests += 1
            
        self._stats_cache.total_tokens_used += message.tokens_used
        
        # 応答時間の平均を更新
        if message.processing_time > 0:
            current_avg = self._stats_cache.average_response_time
            total_responses = self._stats_cache.total_questions + self._stats_cache.total_edit_requests
            if total_responses > 1:
                self._stats_cache.average_response_time = (
                    (current_avg * (total_responses - 1) + message.processing_time) / total_responses
                )
            else:
                self._stats_cache.average_response_time = message.processing_time
        
        self._save_data()
        logger.debug(f"チャットメッセージを追加: {message.session_id[:8]}... -> {message.message_id[:8]}...")

    def get_messages(self, session_id: str) -> List[ChatMessage]:
        """セッションのメッセージ一覧を取得"""
        return self._messages_cache.get(session_id, [])

    def get_message(self, session_id: str, message_id: str) -> Optional[ChatMessage]:
        """特定のメッセージを取得"""
        messages = self._messages_cache.get(session_id, [])
        for message in messages:
            if message.message_id == message_id:
                return message
        return None

    # 編集履歴管理

    def add_edit_history(self, edit_history: EditHistory) -> None:
        """編集履歴を追加"""
        self._edit_history_cache[edit_history.edit_id] = edit_history
        self._save_data()
        logger.info(f"編集履歴を追加: {edit_history.edit_id[:8]}...")

    def get_edit_history_by_edit_id(self, edit_id: str) -> Optional[EditHistory]:
        """編集IDで編集履歴を取得"""
        return self._edit_history_cache.get(edit_id)

    def get_edit_history_by_task(self, task_id: str) -> List[EditHistory]:
        """タスクの編集履歴一覧を取得"""
        return [edit for edit in self._edit_history_cache.values() if edit.task_id == task_id]
    
    def get_edit_history(self, session_id: str, limit: int = 20) -> List[EditHistory]:
        """セッションの編集履歴一覧を取得"""
        edits = [edit for edit in self._edit_history_cache.values() if edit.session_id == session_id]
        # 時系列順（新しい順）でソート
        edits.sort(key=lambda x: x.timestamp, reverse=True)
        return edits[:limit]
    
    def get_edit_history_by_id(self, edit_id: str) -> Optional[EditHistory]:
        """IDで編集履歴を取得"""
        return self._edit_history_cache.get(edit_id)
    
    def update_edit_history(self, edit_history: EditHistory) -> None:
        """編集履歴を更新"""
        if edit_history.edit_id in self._edit_history_cache:
            self._edit_history_cache[edit_history.edit_id] = edit_history
            self._save_data()
            logger.debug(f"編集履歴を更新: {edit_history.edit_id[:8]}...")

    def revert_edit(self, edit_id: str) -> bool:
        """編集を取り消し"""
        if edit_id in self._edit_history_cache:
            edit_history = self._edit_history_cache[edit_id]
            edit_history.reverted = True
            self._save_data()
            logger.info(f"編集を取り消し: {edit_id[:8]}...")
            return True
        return False

    # 統計・クリーンアップ

    def get_stats(self) -> ChatStats:
        """統計情報を取得"""
        # リアルタイム統計を更新
        self._stats_cache.total_sessions = len(self._sessions_cache)
        self._stats_cache.active_sessions = sum(1 for s in self._sessions_cache.values() if s.is_active)
        
        return self._stats_cache

    def cleanup_old_sessions(self, max_age_hours: int = 6) -> int:
        """古いセッションをクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_session_ids = []
        
        for session_id, session in self._sessions_cache.items():
            if session.last_activity < cutoff_time:
                old_session_ids.append(session_id)
                
        # 古いセッションを削除
        for session_id in old_session_ids:
            self.delete_session(session_id)
            
        if old_session_ids:
            logger.info(f"古いチャットセッションをクリーンアップ: {len(old_session_ids)}件")
            
        return len(old_session_ids)

    def cleanup_old_edit_history(self, max_age_days: int = 30) -> int:
        """古い編集履歴をクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        old_edit_ids = []
        
        for edit_id, edit_history in self._edit_history_cache.items():
            if edit_history.timestamp < cutoff_time:
                old_edit_ids.append(edit_id)
                
        # 古い編集履歴を削除
        for edit_id in old_edit_ids:
            del self._edit_history_cache[edit_id]
            
        if old_edit_ids:
            self._save_data()
            logger.info(f"古い編集履歴をクリーンアップ: {len(old_edit_ids)}件")
            
        return len(old_edit_ids)


# グローバルなチャット永続化ストアインスタンス
chat_store = ChatPersistentStore()