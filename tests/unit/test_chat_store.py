"""チャットストアのテスト"""
import pytest
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from app.store.chat_store import ChatPersistentStore, chat_store
from app.models.chat import (
    ChatSession,
    ChatMessage,
    EditHistory,
    ChatStats,
    MessageType,
    MessageIntent,
    Citation,
    EditAction,
    EditActionType
)


class TestChatPersistentStore:
    """チャット永続化ストアのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.store = ChatPersistentStore(storage_dir=self.temp_dir)
        
        # テストデータ
        self.session_id = "test-session-123"
        self.task_id = "test-task-456"
        self.message_id = "test-message-789"
        self.edit_id = "test-edit-abc"
        
        self.test_session = ChatSession(
            task_id=self.task_id,
            transcription="テスト文字起こし",
            minutes="# テスト議事録",
            context_tokens=500
        )
        self.test_session.session_id = self.session_id

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        # 一時ディレクトリを削除
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """初期化テスト"""
        store = ChatPersistentStore(storage_dir=self.temp_dir)
        
        # ディレクトリとファイルが作成されること
        assert store.storage_dir.exists()
        assert isinstance(store._sessions_cache, dict)
        assert isinstance(store._messages_cache, dict)
        assert isinstance(store._edit_history_cache, dict)
        assert isinstance(store._stats_cache, ChatStats)

    def test_create_session(self):
        """セッション作成テスト"""
        self.store.create_session(self.test_session)
        
        # キャッシュに追加されること
        assert self.session_id in self.store._sessions_cache
        assert self.session_id in self.store._messages_cache
        assert len(self.store._messages_cache[self.session_id]) == 0
        
        # 統計が更新されること
        assert self.store._stats_cache.total_sessions == 1
        assert self.store._stats_cache.active_sessions == 1

    def test_get_session(self):
        """セッション取得テスト"""
        self.store.create_session(self.test_session)
        
        retrieved_session = self.store.get_session(self.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == self.session_id
        assert retrieved_session.task_id == self.task_id

    def test_get_session_not_found(self):
        """存在しないセッション取得テスト"""
        retrieved_session = self.store.get_session("nonexistent-session")
        
        assert retrieved_session is None

    def test_update_session(self):
        """セッション更新テスト"""
        self.store.create_session(self.test_session)
        
        # セッションを更新
        updated_session = self.store.get_session(self.session_id)
        updated_session.context_tokens = 1000
        
        self.store.update_session(updated_session)
        
        # 更新が反映されること
        retrieved_session = self.store.get_session(self.session_id)
        assert retrieved_session.context_tokens == 1000

    def test_delete_session(self):
        """セッション削除テスト"""
        self.store.create_session(self.test_session)
        
        # 削除前は存在すること
        assert self.store.get_session(self.session_id) is not None
        
        # 削除
        result = self.store.delete_session(self.session_id)
        
        assert result is True
        assert self.store.get_session(self.session_id) is None
        assert self.session_id not in self.store._sessions_cache
        assert self.session_id not in self.store._messages_cache

    def test_delete_session_not_found(self):
        """存在しないセッション削除テスト"""
        result = self.store.delete_session("nonexistent-session")
        
        assert result is False

    def test_get_sessions_by_task(self):
        """タスク別セッション取得テスト"""
        # 複数のセッションを作成
        session1 = ChatSession(
            task_id=self.task_id,
            transcription="文字起こし1",
            minutes="議事録1",
            context_tokens=100
        )
        session2 = ChatSession(
            task_id="other-task",
            transcription="文字起こし2", 
            minutes="議事録2",
            context_tokens=200
        )
        session3 = ChatSession(
            task_id=self.task_id,
            transcription="文字起こし3",
            minutes="議事録3",
            context_tokens=300
        )
        
        self.store.create_session(session1)
        self.store.create_session(session2)
        self.store.create_session(session3)
        
        # 特定タスクのセッションを取得
        task_sessions = self.store.get_sessions_by_task(self.task_id)
        
        assert len(task_sessions) == 2
        assert all(session.task_id == self.task_id for session in task_sessions)

    def test_add_message(self):
        """メッセージ追加テスト"""
        self.store.create_session(self.test_session)
        
        message = ChatMessage(
            session_id=self.session_id,
            message="テスト質問",
            response="テスト回答",
            message_type=MessageType.USER,
            intent=MessageIntent.QUESTION,
            citations=[],
            edit_actions=[],
            tokens_used=100,
            processing_time=1.5
        )
        
        self.store.add_message(message)
        
        # メッセージが追加されること
        messages = self.store.get_messages(self.session_id)
        assert len(messages) == 1
        assert messages[0].message == "テスト質問"
        
        # セッション情報が更新されること
        session = self.store.get_session(self.session_id)
        assert session.total_messages == 1
        
        # 統計が更新されること
        assert self.store._stats_cache.total_messages == 1
        assert self.store._stats_cache.total_questions == 1
        assert self.store._stats_cache.total_tokens_used == 100

    def test_add_edit_request_message(self):
        """編集リクエストメッセージ追加テスト"""
        self.store.create_session(self.test_session)
        
        message = ChatMessage(
            session_id=self.session_id,
            message="議事録を編集",
            response="編集完了",
            message_type=MessageType.USER,
            intent=MessageIntent.EDIT_REQUEST,
            citations=[],
            edit_actions=[],
            tokens_used=150,
            processing_time=2.0
        )
        
        self.store.add_message(message)
        
        # 編集リクエスト統計が更新されること
        assert self.store._stats_cache.total_edit_requests == 1
        assert self.store._stats_cache.average_response_time == 2.0

    def test_get_messages(self):
        """メッセージ一覧取得テスト"""
        self.store.create_session(self.test_session)
        
        # 複数のメッセージを追加
        for i in range(3):
            message = ChatMessage(
                session_id=self.session_id,
                message=f"質問{i}",
                response=f"回答{i}",
                message_type=MessageType.USER,
                intent=MessageIntent.QUESTION,
                citations=[],
                edit_actions=[],
                tokens_used=50,
                processing_time=1.0
            )
            self.store.add_message(message)
        
        messages = self.store.get_messages(self.session_id)
        
        assert len(messages) == 3
        assert messages[0].message == "質問0"
        assert messages[2].message == "質問2"

    def test_get_messages_empty_session(self):
        """空セッションのメッセージ取得テスト"""
        messages = self.store.get_messages("nonexistent-session")
        
        assert messages == []

    def test_get_message(self):
        """特定メッセージ取得テスト"""
        self.store.create_session(self.test_session)
        
        message = ChatMessage(
            session_id=self.session_id,
            message="特定の質問",
            response="特定の回答",
            message_type=MessageType.USER,
            intent=MessageIntent.QUESTION,
            citations=[],
            edit_actions=[],
            tokens_used=75,
            processing_time=1.2
        )
        message.message_id = self.message_id
        
        self.store.add_message(message)
        
        retrieved_message = self.store.get_message(self.session_id, self.message_id)
        
        assert retrieved_message is not None
        assert retrieved_message.message_id == self.message_id
        assert retrieved_message.message == "特定の質問"

    def test_get_message_not_found(self):
        """存在しないメッセージ取得テスト"""
        self.store.create_session(self.test_session)
        
        retrieved_message = self.store.get_message(self.session_id, "nonexistent-message")
        
        assert retrieved_message is None

    def test_add_edit_history(self):
        """編集履歴追加テスト"""
        edit_history = EditHistory(
            task_id=self.task_id,
            session_id=self.session_id,
            message_id=self.message_id,
            edit_actions=[],
            changes_summary="テスト編集",
            original_minutes="元の議事録",
            updated_minutes="更新された議事録"
        )
        edit_history.edit_id = self.edit_id
        
        self.store.add_edit_history(edit_history)
        
        assert self.edit_id in self.store._edit_history_cache
        retrieved_edit = self.store.get_edit_history_by_edit_id(self.edit_id)
        assert retrieved_edit.changes_summary == "テスト編集"

    def test_get_edit_history_by_task(self):
        """タスク別編集履歴取得テスト"""
        # 複数の編集履歴を追加
        for i in range(2):
            edit_history = EditHistory(
                task_id=self.task_id,
                session_id=self.session_id,
                message_id=f"message-{i}",
                edit_actions=[],
                changes_summary=f"編集{i}",
                original_minutes="元",
                updated_minutes=f"更新{i}"
            )
            self.store.add_edit_history(edit_history)
        
        # 別タスクの編集履歴も追加
        other_edit = EditHistory(
            task_id="other-task",
            session_id="other-session",
            message_id="other-message",
            edit_actions=[],
            changes_summary="別タスク編集",
            original_minutes="元",
            updated_minutes="更新"
        )
        self.store.add_edit_history(other_edit)
        
        task_edits = self.store.get_edit_history_by_task(self.task_id)
        
        assert len(task_edits) == 2
        assert all(edit.task_id == self.task_id for edit in task_edits)

    def test_get_edit_history(self):
        """セッション別編集履歴取得テスト"""
        # 複数の編集履歴を追加（時系列で）
        for i in range(5):
            edit_history = EditHistory(
                task_id=self.task_id,
                session_id=self.session_id,
                message_id=f"message-{i}",
                edit_actions=[],
                changes_summary=f"編集{i}",
                original_minutes="元",
                updated_minutes=f"更新{i}"
            )
            # タイムスタンプを調整
            edit_history.timestamp = datetime.now() + timedelta(minutes=i)
            self.store.add_edit_history(edit_history)
        
        # 制限付きで取得
        edits = self.store.get_edit_history(self.session_id, limit=3)
        
        assert len(edits) == 3
        # 新しい順に並んでいることを確認
        assert edits[0].changes_summary == "編集4"
        assert edits[2].changes_summary == "編集2"

    def test_update_edit_history(self):
        """編集履歴更新テスト"""
        edit_history = EditHistory(
            task_id=self.task_id,
            session_id=self.session_id,
            message_id=self.message_id,
            edit_actions=[],
            changes_summary="元の編集",
            original_minutes="元",
            updated_minutes="更新"
        )
        edit_history.edit_id = self.edit_id
        
        self.store.add_edit_history(edit_history)
        
        # 編集履歴を更新
        edit_history.changes_summary = "更新された編集"
        self.store.update_edit_history(edit_history)
        
        retrieved_edit = self.store.get_edit_history_by_edit_id(self.edit_id)
        assert retrieved_edit.changes_summary == "更新された編集"

    def test_revert_edit(self):
        """編集取り消しテスト"""
        edit_history = EditHistory(
            task_id=self.task_id,
            session_id=self.session_id,
            message_id=self.message_id,
            edit_actions=[],
            changes_summary="取り消し対象編集",
            original_minutes="元",
            updated_minutes="更新"
        )
        edit_history.edit_id = self.edit_id
        
        self.store.add_edit_history(edit_history)
        
        # 編集を取り消し
        result = self.store.revert_edit(self.edit_id)
        
        assert result is True
        retrieved_edit = self.store.get_edit_history_by_edit_id(self.edit_id)
        assert retrieved_edit.reverted is True

    def test_revert_edit_not_found(self):
        """存在しない編集の取り消しテスト"""
        result = self.store.revert_edit("nonexistent-edit")
        
        assert result is False

    def test_get_stats(self):
        """統計情報取得テスト"""
        # セッションとメッセージを追加
        self.store.create_session(self.test_session)
        
        message = ChatMessage(
            session_id=self.session_id,
            message="統計テスト",
            response="統計回答",
            message_type=MessageType.USER,
            intent=MessageIntent.QUESTION,
            citations=[],
            edit_actions=[],
            tokens_used=100,
            processing_time=1.5
        )
        self.store.add_message(message)
        
        stats = self.store.get_stats()
        
        assert stats.total_sessions == 1
        assert stats.active_sessions == 1
        assert stats.total_messages == 1
        assert stats.total_questions == 1
        assert stats.total_tokens_used == 100

    def test_cleanup_old_sessions(self):
        """古いセッションクリーンアップテスト"""
        # 新しいセッションと古いセッションを作成
        new_session = ChatSession(
            task_id="new-task",
            transcription="新しい文字起こし",
            minutes="新しい議事録",
            context_tokens=100
        )
        
        old_session = ChatSession(
            task_id="old-task",
            transcription="古い文字起こし",
            minutes="古い議事録",
            context_tokens=200
        )
        # 古いセッションの最終アクティビティを過去に設定
        old_session.last_activity = datetime.now() - timedelta(hours=10)
        
        self.store.create_session(new_session)
        self.store.create_session(old_session)
        
        # 6時間以上古いセッションをクリーンアップ
        cleaned_count = self.store.cleanup_old_sessions(max_age_hours=6)
        
        assert cleaned_count == 1
        assert len(self.store._sessions_cache) == 1
        assert new_session.session_id in self.store._sessions_cache

    def test_cleanup_old_edit_history(self):
        """古い編集履歴クリーンアップテスト"""
        # 新しい編集履歴と古い編集履歴を作成
        new_edit = EditHistory(
            task_id="new-task",
            session_id="new-session",
            message_id="new-message",
            edit_actions=[],
            changes_summary="新しい編集",
            original_minutes="元",
            updated_minutes="更新"
        )
        
        old_edit = EditHistory(
            task_id="old-task",
            session_id="old-session", 
            message_id="old-message",
            edit_actions=[],
            changes_summary="古い編集",
            original_minutes="元",
            updated_minutes="更新"
        )
        # 古い編集履歴のタイムスタンプを過去に設定
        old_edit.timestamp = datetime.now() - timedelta(days=60)
        
        self.store.add_edit_history(new_edit)
        self.store.add_edit_history(old_edit)
        
        # 30日以上古い編集履歴をクリーンアップ
        cleaned_count = self.store.cleanup_old_edit_history(max_age_days=30)
        
        assert cleaned_count == 1
        assert len(self.store._edit_history_cache) == 1
        assert new_edit.edit_id in self.store._edit_history_cache

    def test_persistence_session_data(self):
        """セッションデータ永続化テスト"""
        self.store.create_session(self.test_session)
        
        # 新しいストアインスタンスを作成（データをロード）
        new_store = ChatPersistentStore(storage_dir=self.temp_dir)
        
        # データが復元されること
        assert self.session_id in new_store._sessions_cache
        retrieved_session = new_store.get_session(self.session_id)
        assert retrieved_session.task_id == self.task_id

    def test_persistence_message_data(self):
        """メッセージデータ永続化テスト"""
        self.store.create_session(self.test_session)
        
        message = ChatMessage(
            session_id=self.session_id,
            message="永続化テスト",
            response="永続化回答",
            message_type=MessageType.USER,
            intent=MessageIntent.QUESTION,
            citations=[],
            edit_actions=[],
            tokens_used=50,
            processing_time=1.0
        )
        self.store.add_message(message)
        
        # 新しいストアインスタンスを作成
        new_store = ChatPersistentStore(storage_dir=self.temp_dir)
        
        # メッセージが復元されること
        messages = new_store.get_messages(self.session_id)
        assert len(messages) == 1
        assert messages[0].message == "永続化テスト"

    @patch('app.store.chat_store.logger')
    def test_error_handling_in_load_data(self, mock_logger):
        """データロード時のエラーハンドリングテスト"""
        # 不正なJSONファイルを作成
        sessions_file = Path(self.temp_dir) / "sessions.json"
        with open(sessions_file, 'w') as f:
            f.write("invalid json content")
        
        # エラーが適切にログに記録されること
        new_store = ChatPersistentStore(storage_dir=self.temp_dir)
        mock_logger.error.assert_called()

    def test_average_response_time_calculation(self):
        """平均応答時間計算テスト"""
        self.store.create_session(self.test_session)
        
        # 複数のメッセージで応答時間をテスト
        processing_times = [1.0, 2.0, 3.0]
        
        for i, time in enumerate(processing_times):
            message = ChatMessage(
                session_id=self.session_id,
                message=f"質問{i}",
                response=f"回答{i}",
                message_type=MessageType.USER,
                intent=MessageIntent.QUESTION,
                citations=[],
                edit_actions=[],
                tokens_used=50,
                processing_time=time
            )
            self.store.add_message(message)
        
        # 平均応答時間が正しく計算されること
        expected_avg = sum(processing_times) / len(processing_times)
        assert abs(self.store._stats_cache.average_response_time - expected_avg) < 0.01

    def test_global_chat_store_instance(self):
        """グローバルチャットストアインスタンステスト"""
        assert chat_store is not None
        assert isinstance(chat_store, ChatPersistentStore)

    def test_session_last_activity_update(self):
        """セッション最終アクティビティ更新テスト"""
        self.store.create_session(self.test_session)
        
        original_activity = self.test_session.last_activity
        
        # 少し待ってからセッションを取得
        import time
        time.sleep(0.1)
        
        retrieved_session = self.store.get_session(self.session_id)
        
        # 最終アクティビティが更新されていること
        assert retrieved_session.last_activity > original_activity