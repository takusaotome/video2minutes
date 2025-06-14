import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import MinutesTask, TaskStatus


class TestMinutesEndpoints:
    """Minutes API エンドポイントのテスト"""

    @pytest.fixture
    def client(self):
        """テストクライアント"""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def sample_task(self):
        """サンプルタスクデータ"""
        task = MinutesTask(
            task_id="test-task-123",
            video_filename="test_video.mp4",
            video_size=1024000,
            upload_timestamp=datetime.now(),
        )
        task.transcription = "これはテスト用の文字起こし結果です。"
        task.minutes = "## 会議議事録\n\n### 要約\nテスト会議の内容です。"
        return task

    def test_upload_video_success(self, client):
        """動画アップロード成功テスト"""
        # FileHandlerの各メソッドをモック
        with patch("app.api.endpoints.minutes.FileHandler") as mock_file_handler:
            mock_file_handler.generate_task_id.return_value = "test-task-123"
            mock_file_handler.save_uploaded_file = AsyncMock(
                return_value=("/path/to/file.mp4", 1024000)
            )

            # バックグラウンドタスクをモック
            with patch("app.api.endpoints.minutes.process_video_task"):

                # ファイルデータを準備
                test_file_content = b"fake video content"
                files = {"file": ("test_video.mp4", test_file_content, "video/mp4")}

                response = client.post("/api/v1/minutes/upload", files=files)

                # レスポンス確認
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["task_id"] == "test-task-123"
                assert response_data["status"] == TaskStatus.QUEUED
                assert "アップロードが完了しました" in response_data["message"]

                # ファイル処理が呼び出されたことを確認
                mock_file_handler.save_uploaded_file.assert_called_once()

    def test_upload_video_validation_error(self, client):
        """動画アップロードバリデーションエラーテスト"""
        with patch("app.api.endpoints.minutes.FileHandler") as mock_file_handler:
            # バリデーションエラーを発生させる
            from fastapi import HTTPException

            mock_file_handler.validate_video_file.side_effect = HTTPException(
                status_code=400, detail="サポートされていないファイル形式です"
            )

            # 無効なファイル
            files = {"file": ("test_file.txt", b"not a video", "text/plain")}

            response = client.post("/api/v1/minutes/upload", files=files)

            # エラーレスポンス確認
            assert response.status_code == 400
            assert "サポートされていないファイル形式" in response.json()["detail"]

    def test_get_all_tasks_empty(self, client):
        """タスク一覧取得（空）テスト"""
        response = client.get("/api/v1/minutes/tasks")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["tasks"] == []

    def test_get_all_tasks_with_data(self, client, sample_task):
        """タスク一覧取得（データ有り）テスト"""
        # グローバルタスクストアに手動でタスクを追加
        with patch(
            "app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}
        ):
            response = client.get("/api/v1/minutes/tasks")

            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["tasks"]) == 1
            assert response_data["tasks"][0]["task_id"] == sample_task.task_id
            assert (
                response_data["tasks"][0]["video_filename"]
                == sample_task.video_filename
            )

    def test_get_task_status_success(self, client, sample_task):
        """タスクステータス取得成功テスト"""
        with patch(
            "app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}
        ):
            response = client.get(f"/api/v1/minutes/{sample_task.task_id}/status")

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["task_id"] == sample_task.task_id
            assert response_data["status"] == sample_task.status
            assert response_data["video_filename"] == sample_task.video_filename
            assert "steps" in response_data

    def test_get_task_status_not_found(self, client):
        """タスクステータス取得（見つからない）テスト"""
        response = client.get("/api/v1/minutes/non-existent-task/status")

        assert response.status_code == 404
        assert "指定されたタスクが見つかりません" in response.json()["detail"]

    def test_get_task_result_success(self, client, sample_task):
        """タスク結果取得成功テスト"""
        # タスクを完了状態に設定
        sample_task.status = TaskStatus.COMPLETED

        with patch(
            "app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}
        ):
            response = client.get(f"/api/v1/minutes/{sample_task.task_id}/result")

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["task_id"] == sample_task.task_id
            assert response_data["video_filename"] == sample_task.video_filename
            assert response_data["transcription"] == sample_task.transcription
            assert response_data["minutes"] == sample_task.minutes

    def test_get_task_result_not_completed(self, client, sample_task):
        """タスク結果取得（未完了）テスト"""
        # タスクを処理中状態に設定
        sample_task.status = TaskStatus.PROCESSING

        with patch(
            "app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}
        ):
            response = client.get(f"/api/v1/minutes/{sample_task.task_id}/result")

            assert response.status_code == 400
            assert "タスクがまだ完了していません" in response.json()["detail"]

    def test_get_task_result_missing_data(self, client, sample_task):
        """タスク結果取得（データ不足）テスト"""
        # タスクを完了状態にするが結果データを削除
        sample_task.status = TaskStatus.COMPLETED
        sample_task.transcription = None
        sample_task.minutes = None

        with patch(
            "app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}
        ):
            response = client.get(f"/api/v1/minutes/{sample_task.task_id}/result")

            assert response.status_code == 500
            assert "処理結果が見つかりません" in response.json()["detail"]


class TestProcessVideoTask:
    """process_video_task関数のテスト"""

    @pytest.fixture
    def sample_task(self):
        """サンプルタスク"""
        return MinutesTask(
            task_id="test-task-123",
            video_filename="test_video.mp4",
            video_size=1024000,
            upload_timestamp=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_process_video_task_success(self, sample_task):
        """動画処理タスク成功テスト"""
        # 必要なサービスをモック
        with patch("app.api.endpoints.minutes.VideoProcessor") as mock_video_processor:
            with patch(
                "app.api.endpoints.minutes.TranscriptionService"
            ) as mock_transcription:
                with patch(
                    "app.api.endpoints.minutes.MinutesGeneratorService",
                    create=True,
                ) as mock_minutes:
                    with patch("app.api.endpoints.minutes.FileHandler"):
                        with patch(
                            "app.api.endpoints.minutes.broadcast_progress_update"
                        ):
                            with patch(
                                "app.api.endpoints.minutes.broadcast_task_completed"
                            ) as mock_completed:

                                # サービスのモック設定
                                mock_video_instance = mock_video_processor.return_value
                                mock_video_instance.extract_audio = AsyncMock(
                                    return_value="/path/to/audio.wav"
                                )

                                mock_transcription_instance = (
                                    mock_transcription.return_value
                                )
                                mock_transcription_instance.transcribe_audio = (
                                    AsyncMock(return_value="文字起こし結果")
                                )

                                mock_minutes_instance = mock_minutes.return_value
                                mock_minutes_instance.generate_minutes = AsyncMock(
                                    return_value="議事録結果"
                                )

                                # タスクストアをモック
                                tasks_store = {sample_task.task_id: sample_task}

                                with patch(
                                    "app.api.endpoints.minutes.tasks_store", tasks_store
                                ):
                                    # 関数をインポートして実行
                                    from app.api.endpoints.minutes import (
                                        process_video_task,
                                    )

                                    await process_video_task(sample_task.task_id)

                                    # 処理が正しく実行されたことを確認
                                    mock_video_instance.extract_audio.assert_called_once()
                                    mock_transcription_instance.transcribe_audio.assert_called_once()
                                    mock_minutes_instance.generate_minutes.assert_called_once()
                                    mock_completed.assert_called_once()

                                    # タスクの結果が設定されたことを確認
                                    assert sample_task.transcription == "文字起こし結果"
                                    assert sample_task.minutes == "議事録結果"

    @pytest.mark.asyncio
    async def test_process_video_task_error(self, sample_task):
        """動画処理タスクエラーテスト"""
        with patch("app.api.endpoints.minutes.VideoProcessor") as mock_video_processor:
            with patch("app.api.endpoints.minutes.FileHandler") as mock_file_handler:
                with patch("app.api.endpoints.minutes.broadcast_progress_update"):
                    with patch(
                        "app.api.endpoints.minutes.broadcast_task_failed"
                    ) as mock_failed:

                        # 音声抽出でエラーを発生させる
                        mock_video_instance = mock_video_processor.return_value
                        mock_video_instance.extract_audio = AsyncMock(
                            side_effect=Exception("音声抽出エラー")
                        )

                        # タスクストアをモック
                        tasks_store = {sample_task.task_id: sample_task}

                        with patch(
                            "app.api.endpoints.minutes.tasks_store", tasks_store
                        ):
                            from app.api.endpoints.minutes import process_video_task

                            await process_video_task(sample_task.task_id)

                            # エラー処理が正しく実行されたことを確認
                            assert sample_task.status == TaskStatus.FAILED
                            assert "音声抽出エラー" in sample_task.error_message
                            mock_failed.assert_called_once()
                            mock_file_handler.cleanup_files.assert_called_once()


class TestWebSocketEndpoints:
    """WebSocket エンドポイントのテスト"""

    def test_websocket_connection(self, client):
        """WebSocket接続テスト"""
        task_id = "test-websocket-task"

        # WebSocket接続をテスト
        with client.websocket_connect(f"/api/v1/minutes/ws/{task_id}") as websocket:
            # 接続が成功することを確認
            assert websocket is not None

            # メッセージ送信テスト
            websocket.send_text("test message")


class TestBroadcastFunctions:
    """WebSocket配信関数のテスト"""

    @pytest.mark.asyncio
    async def test_broadcast_progress_update(self, sample_task):
        """進捗更新配信テスト"""
        task_id = sample_task.task_id

        # WebSocket接続をモック
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        websocket_connections = {task_id: [mock_websocket]}

        with patch(
            "app.api.endpoints.minutes.websocket_connections", websocket_connections
        ):
            from app.api.endpoints.minutes import broadcast_progress_update

            await broadcast_progress_update(task_id, sample_task)

            # WebSocketにメッセージが送信されたことを確認
            mock_websocket.send_text.assert_called_once()

            # 送信されたメッセージの内容を確認
            call_args = mock_websocket.send_text.call_args[0][0]
            message = json.loads(call_args)
            assert message["type"] == "progress_update"
            assert message["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_broadcast_task_completed(self, sample_task):
        """タスク完了配信テスト"""
        task_id = sample_task.task_id

        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        websocket_connections = {task_id: [mock_websocket]}

        with patch(
            "app.api.endpoints.minutes.websocket_connections", websocket_connections
        ):
            from app.api.endpoints.minutes import broadcast_task_completed

            await broadcast_task_completed(task_id, sample_task)

            mock_websocket.send_text.assert_called_once()

            call_args = mock_websocket.send_text.call_args[0][0]
            message = json.loads(call_args)
            assert message["type"] == "task_completed"
            assert message["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_broadcast_task_failed(self, sample_task):
        """タスク失敗配信テスト"""
        task_id = sample_task.task_id
        error_message = "テストエラー"

        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        websocket_connections = {task_id: [mock_websocket]}

        with patch(
            "app.api.endpoints.minutes.websocket_connections", websocket_connections
        ):
            from app.api.endpoints.minutes import broadcast_task_failed

            await broadcast_task_failed(task_id, sample_task, error_message)

            mock_websocket.send_text.assert_called_once()

            call_args = mock_websocket.send_text.call_args[0][0]
            message = json.loads(call_args)
            assert message["type"] == "task_failed"
            assert message["task_id"] == task_id
            assert message["data"]["error_message"] == error_message
