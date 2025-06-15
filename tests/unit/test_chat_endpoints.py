"""チャットエンドポイントのテスト"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.models.chat import (
    ChatSession,
    ChatMessage,
    MessageType,
    MessageIntent,
    Citation,
    EditHistory,
    CreateChatSessionRequest,
    SendMessageRequest
)
from app.models import MinutesTask, TaskStatus


class TestChatEndpoints:
    """チャットエンドポイントのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.app = create_app()
        self.client = TestClient(self.app)
        self.task_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.message_id = str(uuid.uuid4())
        
        # モックタスクデータ
        self.mock_task = MinutesTask(
            task_id=self.task_id,
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
            status=TaskStatus.COMPLETED,
            transcription="テスト文字起こし内容",
            minutes="# テスト議事録\n\n内容"
        )
        
        # モックセッションデータ
        self.mock_session = ChatSession(
            task_id=self.task_id,
            transcription="テスト文字起こし",
            minutes="# テスト議事録",
            context_tokens=500
        )
        self.mock_session.session_id = self.session_id

    @patch('app.api.endpoints.chat.chat_store')
    @patch('app.api.endpoints.chat.session_task_store')
    @patch('app.api.endpoints.chat.SessionManager')
    def test_create_chat_session_success(self, mock_session_manager, mock_session_task_store, mock_chat_store):
        """チャットセッション作成成功テスト"""
        # モック設定
        mock_session_manager.get_session_id.return_value = "test-session-id"
        mock_session_task_store.get_task.return_value = self.mock_task
        mock_chat_store.create_session.return_value = None
        
        # リクエストデータ
        request_data = {
            "transcription": "テスト文字起こし",
            "minutes": "# テスト議事録"
        }
        
        # APIコール
        response = self.client.post(
            f"/api/v1/chat/{self.task_id}/sessions",
            json=request_data
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "context_tokens" in data
        assert data["context_tokens"] >= 100
        mock_chat_store.create_session.assert_called_once()

    @patch('app.api.endpoints.chat.session_task_store')
    @patch('app.api.endpoints.chat.SessionManager')
    def test_create_chat_session_task_not_found(self, mock_session_manager, mock_session_task_store):
        """タスクが見つからない場合のテスト"""
        # モック設定
        mock_session_manager.get_session_id.return_value = "test-session-id"
        mock_session_task_store.get_task.return_value = None
        
        with patch('app.store.tasks_store', {}):
            # APIコール
            response = self.client.post(
                f"/api/v1/chat/{self.task_id}/sessions",
                json={}
            )
            
            # 検証
            assert response.status_code == 404
            assert "タスクが見つかりません" in response.json()["detail"]

    @patch('app.api.endpoints.chat.session_task_store')
    @patch('app.api.endpoints.chat.SessionManager')
    def test_create_chat_session_task_not_completed(self, mock_session_manager, mock_session_task_store):
        """タスクが完了していない場合のテスト"""
        # 未完了タスクのモック
        incomplete_task = Mock()
        incomplete_task.status.value = "processing"
        
        # モック設定
        mock_session_manager.get_session_id.return_value = "test-session-id"
        mock_session_task_store.get_task.return_value = incomplete_task
        
        # APIコール
        response = self.client.post(
            f"/api/v1/chat/{self.task_id}/sessions",
            json={}
        )
        
        # 検証
        assert response.status_code == 400
        assert "タスクが完了していない" in response.json()["detail"]

    @patch('app.api.endpoints.chat.chat_store')
    def test_get_chat_history_success(self, mock_chat_store):
        """チャット履歴取得成功テスト"""
        # モックメッセージ
        mock_message = ChatMessage(
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
        
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.get_messages.return_value = [mock_message]
        
        # APIコール
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/messages"
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total_tokens" in data
        assert "session_info" in data
        assert len(data["messages"]) == 1
        assert data["total_tokens"] == 100

    @patch('app.api.endpoints.chat.chat_store')
    def test_get_chat_history_session_not_found(self, mock_chat_store):
        """セッションが見つからない場合のテスト"""
        # モック設定
        mock_chat_store.get_session.return_value = None
        
        # APIコール
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/messages"
        )
        
        # 検証
        assert response.status_code == 404
        assert "セッションが見つかりません" in response.json()["detail"]

    @patch('app.api.endpoints.chat.chat_store')
    def test_get_chat_history_access_denied(self, mock_chat_store):
        """アクセス権限がない場合のテスト"""
        # 別のタスクIDのセッション
        wrong_session = Mock()
        wrong_session.task_id = "different-task-id"
        
        # モック設定
        mock_chat_store.get_session.return_value = wrong_session
        
        # APIコール
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/messages"
        )
        
        # 検証
        assert response.status_code == 403
        assert "アクセス権限がありません" in response.json()["detail"]

    @patch('app.api.endpoints.chat.chat_store')
    def test_delete_chat_session_success(self, mock_chat_store):
        """チャットセッション削除成功テスト"""
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.delete_session.return_value = True
        
        # APIコール
        response = self.client.delete(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}"
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == self.session_id
        assert "正常に削除されました" in data["message"]
        mock_chat_store.delete_session.assert_called_once_with(self.session_id)

    @patch('app.api.endpoints.chat.chat_store')
    def test_delete_chat_session_failed(self, mock_chat_store):
        """チャットセッション削除失敗テスト"""
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.delete_session.return_value = False
        
        # APIコール
        response = self.client.delete(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}"
        )
        
        # 検証
        assert response.status_code == 500
        assert "削除に失敗しました" in response.json()["detail"]

    @patch('app.api.endpoints.chat.chat_store')
    @patch('app.api.endpoints.chat.session_task_store')
    @patch('app.api.endpoints.chat.SessionManager')
    def test_list_chat_sessions_success(self, mock_session_manager, mock_session_task_store, mock_chat_store):
        """チャットセッション一覧取得成功テスト"""
        # モック設定
        mock_session_manager.get_session_id.return_value = "test-session-id"
        mock_session_task_store.get_task.return_value = self.mock_task
        mock_chat_store.get_sessions_by_task.return_value = [self.mock_session]
        mock_chat_store.get_messages.return_value = []
        
        # APIコール
        response = self.client.get(f"/api/v1/chat/{self.task_id}/sessions")
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total_sessions" in data
        assert data["task_id"] == self.task_id
        assert len(data["sessions"]) == 1

    @patch('app.api.endpoints.chat.openai_service')
    @patch('app.api.endpoints.chat.citation_service')
    @patch('app.api.endpoints.chat.chat_store')
    @pytest.mark.asyncio
    async def test_send_chat_message_success(self, mock_chat_store, mock_citation_service, mock_openai_service):
        """チャットメッセージ送信成功テスト"""
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.get_messages.return_value = []
        mock_chat_store.add_message.return_value = None
        
        mock_citation = Citation(
            text="テスト引用",
            start_time="00:01:00",
            confidence=0.8,
            context="テスト文脈"
        )
        
        mock_openai_service.process_chat_message = AsyncMock(return_value={
            "response": "テスト回答",
            "citations": [mock_citation],
            "edit_actions": [],
            "tokens_used": 150,
            "processing_time": 2.0
        })
        
        mock_citation_service.extract_citations_from_response.return_value = []
        
        # リクエストデータ
        request_data = {
            "message": "テスト質問",
            "message_type": "user",
            "intent": "question"
        }
        
        # APIコール
        response = self.client.post(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/messages",
            json=request_data
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["response"] == "テスト回答"
        assert "citations" in data
        assert data["tokens_used"] == 150

    @patch('app.api.endpoints.chat.chat_store')
    def test_get_session_citations_success(self, mock_chat_store):
        """セッション引用取得成功テスト"""
        # モック引用データ
        mock_citation = Citation(
            text="テスト引用テキスト",
            start_time="00:02:30",
            confidence=0.9,
            context="引用の文脈"
        )
        
        mock_message = Mock()
        mock_message.message_id = self.message_id
        mock_message.citations = [mock_citation]
        
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.get_messages.return_value = [mock_message]
        
        # APIコール
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/citations"
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "citations" in data
        assert "total_citations" in data
        assert len(data["citations"]) == 1
        assert data["citations"][0]["text"] == "テスト引用テキスト"

    @patch('app.api.endpoints.chat.chat_store')
    def test_get_session_citations_specific_message(self, mock_chat_store):
        """特定メッセージの引用取得テスト"""
        # モック引用データ
        mock_citation = Citation(
            text="特定メッセージの引用",
            start_time="00:03:00",
            confidence=0.85,
            context="特定の文脈"
        )
        
        mock_message = Mock()
        mock_message.citations = [mock_citation]
        
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.get_message.return_value = mock_message
        
        # APIコール（message_idパラメータ付き）
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/citations?message_id={self.message_id}"
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "citations" in data
        assert "message_id" in data
        assert data["message_id"] == self.message_id
        assert len(data["citations"]) == 1

    @patch('app.api.endpoints.chat.citation_service')
    @patch('app.api.endpoints.chat.chat_store')
    def test_create_highlight_success(self, mock_chat_store, mock_citation_service):
        """ハイライト作成成功テスト"""
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_highlight_info = {
            "citation_id": "test-citation-id",
            "start_position": 10,
            "end_position": 50,
            "highlighted_text": "ハイライトテキスト",
            "timestamp": "00:01:30",
            "confidence": 0.9,
            "context": "ハイライト文脈",
            "created_at": datetime.now().isoformat()
        }
        mock_citation_service.create_highlight_info.return_value = mock_highlight_info
        
        # リクエストデータ
        highlight_data = {
            "start_position": 10,
            "end_position": 50,
            "highlighted_text": "ハイライトテキスト",
            "timestamp": "00:01:30",
            "confidence": 0.9
        }
        
        # APIコール
        response = self.client.post(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/highlights",
            json=highlight_data
        )
        
        # 検証
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "highlight_id" in data
        assert "highlight_info" in data

    @patch('app.api.endpoints.chat.chat_store')
    def test_create_highlight_missing_fields(self, mock_chat_store):
        """必須フィールド不足時のハイライト作成テスト"""
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        
        # 不完全なリクエストデータ
        highlight_data = {
            "start_position": 10
            # end_position と highlighted_text が不足
        }
        
        # APIコール
        response = self.client.post(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/highlights",
            json=highlight_data
        )
        
        # 検証
        assert response.status_code == 400
        assert "必須フィールドが不足" in response.json()["detail"]

    @patch('app.api.endpoints.chat.edit_intent_analyzer')
    @patch('app.api.endpoints.chat.chat_store')
    def test_analyze_edit_intent_success(self, mock_chat_store, mock_edit_analyzer):
        """編集インテント解析成功テスト"""
        # モック編集アクション
        mock_edit_action = Mock()
        mock_edit_action.action_type.value = "add_content"
        mock_edit_action.target = "議事録"
        mock_edit_action.replacement = None
        mock_edit_action.scope.value = "all"
        mock_edit_action.content = {"text": "新しい内容"}
        mock_edit_action.item_id = None
        mock_edit_action.updates = None
        mock_edit_action.description = "コンテンツ追加"
        
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_edit_analyzer.analyze_edit_intent.return_value = ([mock_edit_action], "解析説明")
        
        # リクエストデータ
        edit_instruction = "アクションアイテムを追加してください"
        
        # APIコール
        response = self.client.post(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/analyze-edit",
            json={"edit_instruction": edit_instruction}
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["edit_instruction"] == edit_instruction
        assert "explanation" in data
        assert "edit_actions" in data
        assert len(data["edit_actions"]) == 1

    @patch('app.api.endpoints.chat.edit_history_service')
    @patch('app.api.endpoints.chat.chat_store')
    def test_get_edit_history_success(self, mock_chat_store, mock_edit_history_service):
        """編集履歴取得成功テスト"""
        # モック編集履歴
        mock_edit_history = Mock()
        mock_edit_history.edit_id = "edit-123"
        mock_edit_history.task_id = self.task_id
        mock_edit_history.session_id = self.session_id
        mock_edit_history.message_id = self.message_id
        mock_edit_history.edit_actions = []
        mock_edit_history.original_minutes = "元の議事録"
        mock_edit_history.updated_minutes = "更新された議事録"
        mock_edit_history.timestamp = datetime.now()
        mock_edit_history.reverted = False
        
        mock_edit_entry = {
            "edit_id": "edit-123",
            "timestamp": mock_edit_history.timestamp.isoformat(),
            "changes_summary": "変更サマリー",
            "edit_type": "normal",
            "reverted": False
        }
        
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.get_edit_history.return_value = [mock_edit_history]
        mock_edit_history_service.create_edit_entry.return_value = mock_edit_entry
        mock_edit_history_service.create_comparison_data.return_value = {
            "versions": [],
            "timeline": []
        }
        
        # APIコール
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/edit-history"
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert "edit_history" in data
        assert "total_edits" in data
        assert len(data["edit_history"]) == 1

    @patch('app.api.endpoints.chat.chat_store')
    def test_get_edit_history_empty(self, mock_chat_store):
        """編集履歴が空の場合のテスト"""
        # モック設定
        mock_chat_store.get_session.return_value = self.mock_session
        mock_chat_store.get_edit_history.return_value = []
        
        # APIコール
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/edit-history"
        )
        
        # 検証
        assert response.status_code == 200
        data = response.json()
        assert data["edit_history"] == []
        assert data["total_edits"] == 0

    def test_estimate_tokens_function(self):
        """トークン数推定関数のテスト"""
        from app.api.endpoints.chat import _estimate_tokens
        
        # 日本語テキスト
        japanese_text = "これは日本語のテストです。"
        tokens_jp = _estimate_tokens(japanese_text)
        assert tokens_jp >= 100  # 最低トークン数
        
        # 英語テキスト
        english_text = "This is an English test."
        tokens_en = _estimate_tokens(english_text)
        assert tokens_en >= 100
        
        # 空文字列
        empty_text = ""
        tokens_empty = _estimate_tokens(empty_text)
        assert tokens_empty == 100  # 最低トークン数

    @patch('app.api.endpoints.chat.chat_store')
    def test_error_handling_internal_server_error(self, mock_chat_store):
        """内部サーバーエラーのハンドリングテスト"""
        # モック設定（例外を発生させる）
        mock_chat_store.get_session.side_effect = Exception("テストエラー")
        
        # APIコール
        response = self.client.get(
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/messages"
        )
        
        # 検証
        assert response.status_code == 500
        assert "failed" in response.json()["detail"] or "失敗" in response.json()["detail"]

    @patch('app.api.endpoints.chat.chat_store')
    def test_session_access_control(self, mock_chat_store):
        """セッションアクセス制御のテスト"""
        # 異なるタスクIDのセッション
        other_session = Mock()
        other_session.task_id = "other-task-id"
        
        # モック設定
        mock_chat_store.get_session.return_value = other_session
        
        # 複数のエンドポイントでアクセス制御をテスト
        endpoints = [
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/messages",
            f"/api/v1/chat/{self.task_id}/sessions/{self.session_id}/citations",
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 403
            assert "アクセス権限がありません" in response.json()["detail"]