import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.main import create_app
from app.models import MinutesTask, ProcessingStepName, ProcessingStepStatus, TaskStatus


class TestMinutesEndpointsExtended:
    """Minutes API エンドポイントの拡張テスト（カバレッジ向上用）"""

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

    @pytest.fixture
    def processing_task(self):
        """処理中のタスク"""
        task = MinutesTask(
            task_id="processing-task-456",
            video_filename="processing_video.mp4",
            video_size=2048000,
            upload_timestamp=datetime.now(),
        )
        task.status = TaskStatus.PROCESSING
        return task

    def test_delete_task_success(self, client, sample_task):
        """タスク削除成功テスト"""
        # グローバルタスクストアにタスクを追加
        with patch("app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}):
            with patch("app.api.endpoints.minutes.FileHandler.cleanup_files") as mock_cleanup:
                with patch("app.api.endpoints.minutes.websocket_connections", {sample_task.task_id: []}):
                    
                    response = client.delete(f"/api/v1/minutes/{sample_task.task_id}")

                    assert response.status_code == 200
                    response_data = response.json()
                    assert f"タスク {sample_task.task_id} を削除しました" in response_data["message"]
                    
                    # ファイルクリーンアップが呼ばれることを確認
                    mock_cleanup.assert_called_once_with(sample_task.task_id)

    def test_delete_task_not_found(self, client):
        """存在しないタスクの削除テスト"""
        with patch("app.api.endpoints.minutes.tasks_store", {}):
            response = client.delete("/api/v1/minutes/non-existent-task")

            assert response.status_code == 404
            response_data = response.json()
            assert "指定されたタスクが見つかりません" in response_data["detail"]

    def test_delete_task_processing(self, client, processing_task):
        """処理中タスクの削除テスト"""
        with patch("app.api.endpoints.minutes.tasks_store", {processing_task.task_id: processing_task}):
            response = client.delete(f"/api/v1/minutes/{processing_task.task_id}")

            assert response.status_code == 400
            response_data = response.json()
            assert "処理中のタスクは削除できません" in response_data["detail"]

    def test_delete_task_cleanup_error(self, client, sample_task):
        """削除時のクリーンアップエラーテスト"""
        with patch("app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}):
            with patch("app.api.endpoints.minutes.FileHandler.cleanup_files") as mock_cleanup:
                # クリーンアップでエラーを発生させる
                mock_cleanup.side_effect = Exception("Cleanup failed")

                response = client.delete(f"/api/v1/minutes/{sample_task.task_id}")

                assert response.status_code == 500
                response_data = response.json()
                assert "タスクの削除中にエラーが発生しました" in response_data["detail"]

    def test_upload_video_file_handler_error(self, client):
        """ファイルハンドラーエラーテスト"""
        with patch("app.api.endpoints.minutes.FileHandler") as mock_file_handler:
            # FileHandlerでエラーを発生させる
            mock_file_handler.generate_task_id.side_effect = Exception("FileHandler error")

            # ファイルデータを準備
            test_file_content = b"fake video content"
            files = {"file": ("test_video.mp4", test_file_content, "video/mp4")}

            response = client.post("/api/v1/minutes/upload", files=files)

            assert response.status_code == 500
            response_data = response.json()
            assert "アップロード中にエラーが発生しました" in response_data["detail"]

    def test_get_task_result_missing_transcription(self, client, sample_task):
        """文字起こし結果がないタスクの結果取得テスト"""
        # 完了状態だが文字起こしがないタスクを作成
        sample_task.status = TaskStatus.COMPLETED
        sample_task.transcription = None
        sample_task.minutes = "議事録のみ存在"

        with patch("app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}):
            response = client.get(f"/api/v1/minutes/{sample_task.task_id}/result")

            assert response.status_code == 500
            response_data = response.json()
            assert "処理結果が見つかりません" in response_data["detail"]

    def test_get_task_result_missing_minutes(self, client, sample_task):
        """議事録がないタスクの結果取得テスト"""
        # 完了状態だが議事録がないタスクを作成
        sample_task.status = TaskStatus.COMPLETED
        sample_task.transcription = "文字起こしのみ存在"
        sample_task.minutes = None

        with patch("app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}):
            response = client.get(f"/api/v1/minutes/{sample_task.task_id}/result")

            assert response.status_code == 500
            response_data = response.json()
            assert "処理結果が見つかりません" in response_data["detail"]

    def test_websocket_connection_and_disconnect(self, client, sample_task):
        """WebSocket接続とディスコネクトテスト"""
        with patch("app.api.endpoints.minutes.websocket_connections", {}) as mock_connections:
            with client.websocket_connect(f"/api/v1/minutes/ws/{sample_task.task_id}") as websocket:
                # 接続が確立されることを確認
                assert sample_task.task_id in mock_connections
                assert len(mock_connections[sample_task.task_id]) == 1

    def test_websocket_disconnect_during_communication(self, client, sample_task):
        """WebSocket通信中のディスコネクトテスト"""
        with patch("app.api.endpoints.minutes.websocket_connections", {}) as mock_connections:
            try:
                with client.websocket_connect(f"/api/v1/minutes/ws/{sample_task.task_id}") as websocket:
                    # 強制的にディスコネクト
                    websocket.close()
            except WebSocketDisconnect:
                # ディスコネクトは正常な動作
                pass

    @pytest.mark.asyncio
    async def test_broadcast_progress_update_success(self, sample_task):
        """進捗更新ブロードキャスト成功テスト"""
        from app.api.endpoints.minutes import broadcast_progress_update
        
        # モックWebSocket接続を作成
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        with patch("app.api.endpoints.minutes.websocket_connections", {sample_task.task_id: [mock_websocket]}):
            await broadcast_progress_update(sample_task.task_id, sample_task)
            
            # WebSocketにメッセージが送信されることを確認
            mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_progress_update_websocket_error(self, sample_task):
        """WebSocket送信エラー時のテスト"""
        from app.api.endpoints.minutes import broadcast_progress_update
        
        # エラーを発生するモックWebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock(side_effect=Exception("WebSocket error"))
        
        with patch("app.api.endpoints.minutes.websocket_connections", {sample_task.task_id: [mock_websocket]}):
            # エラーが発生してもブロードキャストが継続されることを確認
            await broadcast_progress_update(sample_task.task_id, sample_task)

    @pytest.mark.asyncio
    async def test_broadcast_task_completed_success(self, sample_task):
        """タスク完了ブロードキャスト成功テスト"""
        from app.api.endpoints.minutes import broadcast_task_completed
        
        # モックWebSocket接続を作成
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        with patch("app.api.endpoints.minutes.websocket_connections", {sample_task.task_id: [mock_websocket]}):
            await broadcast_task_completed(sample_task.task_id, sample_task)
            
            # WebSocketにメッセージが送信されることを確認
            mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_task_failed_success(self, sample_task):
        """タスク失敗ブロードキャスト成功テスト"""
        from app.api.endpoints.minutes import broadcast_task_failed
        
        # モックWebSocket接続を作成
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        with patch("app.api.endpoints.minutes.websocket_connections", {sample_task.task_id: [mock_websocket]}):
            await broadcast_task_failed(sample_task.task_id, sample_task, "Test error message")
            
            # WebSocketにメッセージが送信されることを確認
            mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_video_task_video_processor_error(self, sample_task):
        """動画処理エラーテスト"""
        from app.api.endpoints.minutes import process_video_task
        
        with patch("app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}):
            with patch("app.api.endpoints.minutes.VideoProcessor") as mock_processor_class:
                with patch("app.api.endpoints.minutes.broadcast_progress_update") as mock_broadcast:
                    with patch("app.api.endpoints.minutes.broadcast_task_failed") as mock_broadcast_failed:
                        # VideoProcessorでエラーを発生
                        mock_processor = Mock()
                        mock_processor.extract_audio = AsyncMock(side_effect=Exception("Video processing error"))
                        mock_processor_class.return_value = mock_processor

                        await process_video_task(sample_task.task_id)

                        # タスク失敗がブロードキャストされることを確認
                        mock_broadcast_failed.assert_called_once()
                        assert sample_task.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_video_task_transcription_error(self, sample_task):
        """文字起こしエラーテスト"""
        from app.api.endpoints.minutes import process_video_task
        
        with patch("app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}):
            with patch("app.api.endpoints.minutes.VideoProcessor") as mock_processor_class:
                with patch("app.api.endpoints.minutes.TranscriptionService") as mock_transcription_class:
                    with patch("app.api.endpoints.minutes.broadcast_progress_update") as mock_broadcast:
                        with patch("app.api.endpoints.minutes.broadcast_task_failed") as mock_broadcast_failed:
                            # VideoProcessorは成功
                            mock_processor = Mock()
                            mock_processor.extract_audio = AsyncMock(return_value="/path/to/audio.wav")
                            mock_processor_class.return_value = mock_processor

                            # TranscriptionServiceでエラーを発生
                            mock_transcription = Mock()
                            mock_transcription.transcribe_audio = AsyncMock(side_effect=Exception("Transcription error"))
                            mock_transcription_class.return_value = mock_transcription

                            await process_video_task(sample_task.task_id)

                            # タスク失敗がブロードキャストされることを確認
                            mock_broadcast_failed.assert_called_once()
                            assert sample_task.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_video_task_minutes_generation_error(self, sample_task):
        """議事録生成エラーテスト"""
        from app.api.endpoints.minutes import process_video_task
        
        with patch("app.api.endpoints.minutes.tasks_store", {sample_task.task_id: sample_task}):
            with patch("app.api.endpoints.minutes.VideoProcessor") as mock_processor_class:
                with patch("app.api.endpoints.minutes.TranscriptionService") as mock_transcription_class:
                    with patch("app.api.endpoints.minutes.MinutesGeneratorService") as mock_minutes_class:
                        with patch("app.api.endpoints.minutes.broadcast_progress_update") as mock_broadcast:
                            with patch("app.api.endpoints.minutes.broadcast_task_failed") as mock_broadcast_failed:
                                # VideoProcessorは成功
                                mock_processor = Mock()
                                mock_processor.extract_audio = AsyncMock(return_value="/path/to/audio.wav")
                                mock_processor_class.return_value = mock_processor

                                # TranscriptionServiceは成功
                                mock_transcription = Mock()
                                mock_transcription.transcribe_audio = AsyncMock(return_value="文字起こし結果")
                                mock_transcription_class.return_value = mock_transcription

                                # MinutesGeneratorServiceでエラーを発生
                                mock_minutes = Mock()
                                mock_minutes.generate_minutes = AsyncMock(side_effect=Exception("Minutes generation error"))
                                mock_minutes_class.return_value = mock_minutes

                                await process_video_task(sample_task.task_id)

                                # タスク失敗がブロードキャストされることを確認
                                mock_broadcast_failed.assert_called_once()
                                assert sample_task.status == TaskStatus.FAILED

    def test_get_queue_status_success(self, client):
        """タスクキューステータス取得成功テスト"""
        with patch("app.api.endpoints.minutes.get_task_queue") as mock_get_queue:
            # モックキューを作成
            mock_queue = Mock()
            mock_queue.get_queue_status.return_value = {
                "active_tasks": 2,
                "pending_tasks": 5,
                "completed_tasks": 10
            }
            mock_get_queue.return_value = mock_queue

            response = client.get("/api/v1/minutes/queue/status")

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["active_tasks"] == 2
            assert response_data["pending_tasks"] == 5
            assert response_data["completed_tasks"] == 10

    def test_websocket_multiple_connections(self, client, sample_task):
        """複数WebSocket接続のテスト"""
        with patch("app.api.endpoints.minutes.websocket_connections", {}) as mock_connections:
            # 最初の接続
            with client.websocket_connect(f"/api/v1/minutes/ws/{sample_task.task_id}") as ws1:
                assert len(mock_connections[sample_task.task_id]) == 1
                
                # 2つ目の接続（同じタスクID）
                with client.websocket_connect(f"/api/v1/minutes/ws/{sample_task.task_id}") as ws2:
                    assert len(mock_connections[sample_task.task_id]) == 2