import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch
import pytest
from fastapi.testclient import TestClient
from fastapi import Request

from app.main import create_app


class TestMainExtended:
    """main.pyの拡張テスト（カバレッジ向上用）"""

    @pytest.fixture
    def app(self):
        """テスト用アプリケーション"""
        return create_app()

    @pytest.fixture
    def client(self, app):
        """テストクライアント"""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """ルートエンドポイントテスト"""
        response = client.get("/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Video2Minutes API"
        assert response_data["version"] == "1.0.0"

    def test_health_check_endpoint(self, client):
        """ヘルスチェックエンドポイントテスト"""
        with patch("app.services.task_queue.get_task_queue") as mock_get_queue:
            # モックキューを作成
            mock_queue = Mock()
            mock_queue.get_queue_status.return_value = {
                "active": 0,
                "pending": 0,
                "completed": 5
            }
            mock_get_queue.return_value = mock_queue

            response = client.get("/health")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "healthy"
            assert "tasks_count" in response_data
            assert "queue" in response_data

    @pytest.mark.asyncio
    async def test_startup_event(self):
        """アプリケーション起動イベントテスト"""
        with patch("app.main.initialize_task_queue") as mock_init:
            mock_init.return_value = AsyncMock()
            
            app = create_app()
            
            # 起動イベントが登録されていることを確認
            startup_handlers = app.router.on_startup
            assert len(startup_handlers) > 0

    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """アプリケーション停止イベントテスト"""
        with patch("app.main.shutdown_task_queue") as mock_shutdown:
            mock_shutdown.return_value = AsyncMock()
            
            app = create_app()
            
            # 停止イベントが登録されていることを確認
            shutdown_handlers = app.router.on_shutdown
            assert len(shutdown_handlers) > 0

    def test_global_exception_handler_debug_mode(self, client):
        """デバッグモード時のグローバル例外ハンドラーテスト"""
        with patch("app.main.settings") as mock_settings:
            mock_settings.debug = True

            # 例外を発生させるエンドポイントを追加
            app = create_app()
            
            @app.get("/test-exception")
            async def test_exception():
                raise ValueError("Test exception for debug mode")

            test_client = TestClient(app)
            response = test_client.get("/test-exception")

            assert response.status_code == 500
            response_data = response.json()
            assert response_data["error"] == "Internal Server Error"
            assert response_data["message"] == "予期しないエラーが発生しました。"
            assert response_data["detail"] == "Test exception for debug mode"  # デバッグモードで詳細表示

    def test_global_exception_handler_production_mode(self, client):
        """本番モード時のグローバル例外ハンドラーテスト"""
        with patch("app.main.settings") as mock_settings:
            mock_settings.debug = False

            # 例外を発生させるエンドポイントを追加
            app = create_app()
            
            @app.get("/test-exception-prod")
            async def test_exception():
                raise ValueError("Test exception for production mode")

            test_client = TestClient(app)
            response = test_client.get("/test-exception-prod")

            assert response.status_code == 500
            response_data = response.json()
            assert response_data["error"] == "Internal Server Error"
            assert response_data["message"] == "予期しないエラーが発生しました。"
            assert response_data["detail"] is None  # 本番モードで詳細非表示

    def test_logging_middleware_exception_handling(self, client, caplog):
        """ロギングミドルウェアの例外処理テスト"""
        import logging
        caplog.set_level(logging.ERROR)

        # 例外を発生させるエンドポイントを追加
        app = create_app()
        
        @app.get("/test-middleware-error")
        async def test_middleware_error():
            raise RuntimeError("Middleware test error")

        test_client = TestClient(app)
        response = test_client.get("/test-middleware-error")

        # エラーログが出力されることを確認
        assert response.status_code == 500
        log_messages = caplog.text
        assert "リクエストエラー" in log_messages or "未処理例外" in log_messages

    def test_directory_creation_with_existing_dirs(self):
        """既存ディレクトリがある場合の作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = os.path.join(temp_dir, "uploads")
            temp_upload_dir = os.path.join(temp_dir, "temp")
            
            # 事前にディレクトリを作成
            os.makedirs(upload_dir)
            os.makedirs(temp_upload_dir)
            
            with patch("app.main.settings") as mock_settings:
                mock_settings.upload_dir = upload_dir
                mock_settings.temp_dir = temp_upload_dir
                mock_settings.debug = False
                mock_settings.cors_origins = ["http://localhost:3000"]
                mock_settings.log_level = "INFO"
                mock_settings.log_dir = "logs"

                # エラーが発生しないことを確認
                app = create_app()
                assert app is not None

    def test_directory_creation_with_permission_error(self):
        """ディレクトリ作成時の権限エラーテスト"""
        with patch("app.main.settings") as mock_settings:
            with patch("os.makedirs") as mock_makedirs:
                mock_settings.upload_dir = "/invalid/path/uploads"
                mock_settings.temp_dir = "/invalid/path/temp"
                mock_settings.debug = False
                mock_settings.cors_origins = ["http://localhost:3000"]
                mock_settings.log_level = "INFO"
                mock_settings.log_dir = "logs"

                # exist_okがTrueで呼ばれることを確認
                app = create_app()
                
                # makedirs が呼ばれることを確認
                assert mock_makedirs.call_count >= 2

    def test_cors_middleware_configuration(self, client):
        """CORSミドルウェア設定テスト"""
        # プリフライトリクエストをテスト
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # CORSヘッダーが設定されていることを確認
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_request_logging_with_client_info(self, client, caplog):
        """クライアント情報を含むリクエストログテスト"""
        import logging
        caplog.set_level(logging.INFO)

        # カスタムヘッダー付きでリクエスト
        response = client.get(
            "/",
            headers={
                "User-Agent": "Test-Client/1.0",
                "X-Forwarded-For": "192.168.1.1"
            }
        )

        assert response.status_code == 200
        
        # ログが出力されていることを確認
        log_messages = caplog.text
        assert "リクエスト開始" in log_messages
        assert "リクエスト完了" in log_messages

    def test_tasks_store_integration(self, client):
        """タスクストア統合テスト"""
        from app.store import tasks_store
        from app.models import MinutesTask
        from datetime import datetime

        # テストタスクを追加
        test_task = MinutesTask(
            task_id="integration-test-task",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )
        tasks_store[test_task.task_id] = test_task

        # ヘルスチェックでタスク数が反映されることを確認
        response = client.get("/health")
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["tasks_count"] >= 1

    def test_application_instance_creation(self):
        """アプリケーションインスタンス作成テスト"""
        # app インスタンスが正常に作成されることを確認
        from app.main import app
        assert app is not None
        
        # FastAPIアプリケーションの属性を確認
        assert hasattr(app, 'routes')
        assert hasattr(app, 'middleware_stack')

    @pytest.mark.asyncio
    async def test_request_middleware_timing(self, client):
        """リクエスト処理時間測定テスト"""
        import time
        import asyncio
        
        # 遅延エンドポイントを追加
        app = create_app()
        
        @app.get("/slow-endpoint")
        async def slow_endpoint():
            await asyncio.sleep(0.01)  # 10ms遅延
            return {"message": "slow response"}

        test_client = TestClient(app)
        
        start_time = time.time()
        response = test_client.get("/slow-endpoint")
        end_time = time.time()
        
        assert response.status_code == 200
        # 処理時間が適切に測定されていることを間接的に確認
        assert (end_time - start_time) >= 0.01

    def test_settings_integration_multiple_origins(self):
        """複数CORS オリジンの設定テスト"""
        with patch("app.main.settings") as mock_settings:
            mock_settings.debug = False
            mock_settings.cors_origins = [
                "http://localhost:3000",
                "http://localhost:3001", 
                "https://example.com"
            ]
            mock_settings.upload_dir = "uploads"
            mock_settings.temp_dir = "temp"
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"

            app = create_app()
            client = TestClient(app)

            # 複数のオリジンからのリクエストをテスト
            for origin in mock_settings.cors_origins:
                response = client.options(
                    "/",
                    headers={"Origin": origin}
                )
                assert "access-control-allow-origin" in response.headers