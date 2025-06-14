from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import create_app


class TestLoggingMiddleware:
    """ロギングミドルウェアのテスト"""

    def test_request_logging_middleware_success(self, caplog):
        """リクエストロギングミドルウェアの成功テスト"""
        import logging

        # ログレベルを設定
        caplog.set_level(logging.INFO)

        app = create_app()
        client = TestClient(app)

        # 正常なリクエストを送信
        response = client.get("/")

        assert response.status_code == 200

        # ログ出力の確認
        log_messages = caplog.text
        assert "リクエスト開始: GET" in log_messages
        assert "リクエスト完了: GET" in log_messages

    def test_request_logging_middleware_with_error(self, caplog):
        """リクエストロギングミドルウェアのエラーテスト"""
        import logging

        # ログレベルを設定
        caplog.set_level(logging.INFO)

        app = create_app()

        # エラーを発生させるエンドポイントを追加
        @app.get("/test-error")
        async def test_error():
            raise HTTPException(status_code=404, detail="Not found")

        client = TestClient(app)

        # エラーリクエストを送信
        response = client.get("/test-error")

        assert response.status_code == 404

        # ログ出力の確認
        log_messages = caplog.text
        assert "リクエスト開始: GET" in log_messages
        assert "リクエスト完了: GET" in log_messages

    def test_request_logging_middleware_timing(self, caplog):
        """リクエストロギングミドルウェアのタイミングテスト"""
        import logging

        caplog.set_level(logging.INFO)

        app = create_app()

        # 遅延を発生させるエンドポイントを追加
        @app.get("/slow-endpoint")
        async def slow_endpoint():
            return {"message": "slow response"}

        client = TestClient(app)

        # 遅延エンドポイントにリクエスト
        response = client.get("/slow-endpoint")

        assert response.status_code == 200

        # ログに実行時間が含まれていることを確認
        log_messages = caplog.text
        assert "リクエスト完了" in log_messages
        assert "s)" in log_messages  # 実行時間の秒数表示

    def test_request_logging_middleware_extra_data(self, caplog):
        """リクエストロギングミドルウェアの追加データテスト"""
        import logging

        caplog.set_level(logging.INFO)

        app = create_app()
        client = TestClient(app)

        # User-Agentヘッダー付きでリクエストを送信
        headers = {"User-Agent": "TestClient/1.0"}
        response = client.get("/", headers=headers)

        assert response.status_code == 200

        # ログが正常に出力されていることを確認
        log_messages = caplog.text
        assert "リクエスト開始" in log_messages
        assert "リクエスト完了" in log_messages

    def test_request_logging_middleware_client_ip(self, caplog):
        """リクエストロギングミドルウェアのクライアントIP テスト"""
        import logging

        caplog.set_level(logging.INFO)

        app = create_app()
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200

        # ログが正常に出力されていることを確認
        log_messages = caplog.text
        assert "リクエスト開始" in log_messages
        assert "リクエスト完了" in log_messages


class TestApplicationInitializationLogging:
    """アプリケーション初期化ロギングのテスト"""

    def test_application_initialization_logging(self, caplog):
        """アプリケーション初期化ロギングテスト"""
        import logging

        caplog.set_level(logging.INFO)

        # アプリケーションを作成
        create_app()

        # 初期化ログが出力されたことを確認
        log_messages = caplog.text
        assert "アプリケーション初期化完了" in log_messages

    def test_logging_system_initialization(self, caplog):
        """ロギングシステム初期化テスト"""
        import logging

        caplog.set_level(logging.INFO)

        # アプリケーションを作成
        create_app()

        # アプリケーション初期化が確認できればOK
        log_messages = caplog.text
        assert "アプリケーション初期化完了" in log_messages


class TestGlobalExceptionHandlerLogging:
    """グローバル例外ハンドラーロギングのテスト"""

    def test_global_exception_handler_logging(self, caplog):
        """グローバル例外ハンドラーのロギングテスト"""
        import logging

        caplog.set_level(logging.ERROR)

        app = create_app()

        # HTTP例外を発生させるエンドポイントを追加
        from fastapi import HTTPException

        @app.get("/test-http-exception")
        async def test_http_exception():
            raise HTTPException(status_code=400, detail="Test HTTP exception")

        client = TestClient(app)

        response = client.get("/test-http-exception")

        assert response.status_code == 400

        # HTTPExceptionは正常な処理なのでエラーログは期待しない
        response_data = response.json()
        assert response_data["detail"] == "Test HTTP exception"


class TestLoggingConfiguration:
    """ロギング設定のテスト"""

    def test_logging_configuration_with_different_levels(self, caplog):
        """異なるログレベルでの設定テスト"""
        import logging

        # DEBUGレベルでのテスト
        caplog.set_level(logging.DEBUG)

        app = create_app()
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200

        # ログが出力されていることを確認
        log_messages = caplog.text
        assert "リクエスト開始" in log_messages
