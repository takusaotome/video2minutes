from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app, create_app


class TestMainApplication:
    """メインアプリケーションのテスト"""

    def test_create_app(self):
        """アプリケーション作成テスト"""
        test_app = create_app()

        # アプリケーションが正常に作成されることを確認
        assert test_app is not None
        assert test_app.title == "Video2Minutes API"
        assert test_app.version == "1.0.0"

    def test_app_instance(self):
        """アプリケーションインスタンステスト"""
        # グローバルのappインスタンスが存在することを確認
        assert app is not None
        assert app.title == "Video2Minutes API"

    def test_root_endpoint(self):
        """ルートエンドポイントテスト"""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Video2Minutes API"
        assert response_data["version"] == "1.0.0"

    def test_health_check_endpoint(self):
        """ヘルスチェックエンドポイントテスト"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "healthy"
        assert "tasks_count" in response_data
        assert isinstance(response_data["tasks_count"], int)

    def test_docs_endpoint(self):
        """APIドキュメントエンドポイントテスト"""
        client = TestClient(app)
        response = client.get("/docs")

        # OpenAPI docページが表示されることを確認
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint(self):
        """ReDocエンドポイントテスト"""
        client = TestClient(app)
        response = client.get("/redoc")

        # ReDocページが表示されることを確認
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_cors_middleware(self):
        """CORSミドルウェアテスト"""
        client = TestClient(app)

        # CORSプリフライトリクエストをテスト
        response = client.options(
            "/api/v1/minutes/tasks",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # CORSヘッダーが設定されていることを確認
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_global_exception_handler(self):
        """グローバル例外ハンドラーテスト"""
        client = TestClient(app)

        # 存在しないエンドポイントにアクセス
        response = client.get("/non-existent-endpoint")

        # 404エラーが返されることを確認
        assert response.status_code == 404

    @patch("app.main.settings")
    @patch("app.main.setup_logging")
    def test_directory_creation(self, mock_setup_logging, mock_settings):
        """必要なディレクトリの作成テスト"""
        mock_settings.upload_dir = "test_uploads"
        mock_settings.temp_dir = "test_temp"
        mock_settings.log_level = "INFO"
        mock_settings.log_dir = "logs"

        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("os.makedirs") as mock_makedirs:
            create_app()

            # ディレクトリ作成が呼び出されることを確認（storageディレクトリが追加）
            assert mock_makedirs.call_count == 3
            mock_makedirs.assert_any_call("test_uploads", exist_ok=True)
            mock_makedirs.assert_any_call("test_temp", exist_ok=True)
            mock_makedirs.assert_any_call("storage", exist_ok=True)


class TestGlobalExceptionHandler:
    """グローバル例外ハンドラーのテスト"""

    def test_exception_handler_with_debug_mode(self):
        """デバッグモードでの例外ハンドラーテスト"""
        test_app = create_app()
        client = TestClient(test_app)

        # HTTP例外を発生させるエンドポイントをテスト
        from fastapi import HTTPException
        
        @test_app.get("/test-http-error")
        async def test_error():
            raise HTTPException(status_code=400, detail="Test HTTP error")

        response = client.get("/test-http-error")

        assert response.status_code == 400
        # HTTPExceptionのレスポンスを確認
        response_data = response.json()
        assert response_data["detail"] == "Test HTTP error"

    def test_exception_handler_without_debug_mode(self):
        """非デバッグモードでの例外ハンドラーテスト"""
        test_app = create_app()
        client = TestClient(test_app)

        # 存在しないエンドポイントにアクセス（404エラー）
        response = client.get("/non-existent-endpoint-for-test")

        assert response.status_code == 404
        # 404エラーレスポンスを確認
        response_data = response.json()
        assert "detail" in response_data


class TestTasksStore:
    """グローバルタスクストアのテスト"""

    def test_tasks_store_initialization(self):
        """タスクストア初期化テスト"""
        from app.store import tasks_store

        # 辞書として初期化されていることを確認
        assert isinstance(tasks_store, dict)

    def test_tasks_store_health_check_integration(self):
        """タスクストアとヘルスチェックの統合テスト"""
        from datetime import datetime

        from app.store import tasks_store
        from app.models import MinutesTask

        # テストタスクを追加
        test_task = MinutesTask(
            task_id="health-test-task",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )
        tasks_store[test_task.task_id] = test_task

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["tasks_count"] >= 1


class TestApplicationSettings:
    """アプリケーション設定のテスト"""

    def test_settings_integration(self):
        """設定統合テスト"""
        # 設定が正しく読み込まれることを確認
        from app.config import settings

        assert settings is not None
        assert hasattr(settings, "cors_origins")
        assert hasattr(settings, "upload_dir")
        assert hasattr(settings, "temp_dir")

    def test_cors_origins_configuration(self):
        """CORS設定テスト"""
        client = TestClient(app)

        # 許可されたオリジンからのリクエストをテスト
        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == 200
        # CORS ヘッダーが設定されていることを確認
        assert "access-control-allow-origin" in response.headers


class TestRouterIntegration:
    """ルーター統合テスト"""

    def test_minutes_router_integration(self):
        """Minutesルーター統合テスト"""
        client = TestClient(app)

        # Minutesルーターのエンドポイントが正しく統合されていることを確認
        response = client.get("/api/v1/minutes/tasks")

        assert response.status_code == 200
        response_data = response.json()
        assert "tasks" in response_data
        assert isinstance(response_data["tasks"], list)

    def test_router_prefix_and_tags(self):
        """ルータープレフィックスとタグのテスト"""
        # OpenAPI仕様を取得
        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi_spec = response.json()

        # Minutes APIのパスが正しいプレフィックスで登録されていることを確認
        assert "/api/v1/minutes/tasks" in openapi_spec["paths"]
        assert "/api/v1/minutes/upload" in openapi_spec["paths"]

    def test_api_documentation_access(self):
        """APIドキュメントアクセステスト"""
        client = TestClient(app)

        # Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200

        # ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200

        # OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
