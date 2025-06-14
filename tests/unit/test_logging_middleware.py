import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import create_app


class TestLoggingMiddleware:
    """ロギングミドルウェアのテスト"""

    @patch("app.main.setup_logging")
    def test_request_logging_middleware_success(self, mock_setup_logging):
        """リクエストロギングミドルウェアの成功テスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"
            mock_settings.debug = False
            mock_settings.upload_dir = "uploads"
            mock_settings.temp_dir = "temp"
            mock_settings.cors_origins = ["http://localhost:3000"]

            app = create_app()
            client = TestClient(app)

            # 正常なリクエストを送信
            response = client.get("/")

            assert response.status_code == 200

            # ロガーが呼び出されたことを確認
            assert mock_logger.info.call_count >= 2  # 開始と完了のログ

            # リクエスト開始のログを確認
            start_call = mock_logger.info.call_args_list[0]
            assert "リクエスト開始" in start_call[0][0]
            assert "GET" in start_call[0][0]

            # リクエスト完了のログを確認
            completion_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "リクエスト完了" in call[0][0]
            ]
            assert len(completion_calls) > 0

    @patch("app.main.setup_logging")
    def test_request_logging_middleware_with_error(self, mock_setup_logging):
        """リクエストロギングミドルウェアのエラーテスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"
            mock_settings.debug = False
            mock_settings.upload_dir = "uploads"
            mock_settings.temp_dir = "temp"
            mock_settings.cors_origins = ["http://localhost:3000"]

            app = create_app()

            # エラーを発生させるエンドポイントを追加
            @app.get("/test-error")
            async def test_error():
                raise HTTPException(status_code=404, detail="Not found")

            client = TestClient(app)

            # エラーリクエストを送信
            response = client.get("/test-error")

            assert response.status_code == 404

            # エラーログが出力されたことを確認
            error_calls = [
                call
                for call in mock_logger.error.call_args_list
                if "リクエストエラー" in call[0][0]
            ]
            assert len(error_calls) > 0

    @patch("app.main.setup_logging")
    def test_request_logging_middleware_timing(self, mock_setup_logging):
        """リクエストロギングミドルウェアのタイミングテスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"
            mock_settings.debug = False
            mock_settings.upload_dir = "uploads"
            mock_settings.temp_dir = "temp"
            mock_settings.cors_origins = ["http://localhost:3000"]

            app = create_app()

            # 遅延を発生させるエンドポイントを追加
            @app.get("/slow-endpoint")
            async def slow_endpoint():
                # 実際の遅延の代わりにモックを使用
                return {"message": "slow response"}

            client = TestClient(app)

            # 時間計測をモック
            with patch("time.time") as mock_time:
                mock_time.side_effect = [1000.0, 1000.5]  # 0.5秒の処理時間

                response = client.get("/slow-endpoint")

                assert response.status_code == 200

                # 処理時間がログに含まれていることを確認
                completion_calls = [
                    call
                    for call in mock_logger.info.call_args_list
                    if "リクエスト完了" in call[0][0]
                ]
                assert len(completion_calls) > 0

                # 処理時間の情報が含まれていることを確認
                completion_log = completion_calls[0][0][0]
                assert "0.500s" in completion_log

    @patch("app.main.setup_logging")
    def test_request_logging_middleware_extra_data(self, mock_setup_logging):
        """リクエストロギングミドルウェアの追加データテスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"
            mock_settings.debug = False
            mock_settings.upload_dir = "uploads"
            mock_settings.temp_dir = "temp"
            mock_settings.cors_origins = ["http://localhost:3000"]

            app = create_app()
            client = TestClient(app)

            # User-Agentヘッダー付きでリクエストを送信
            headers = {"User-Agent": "TestClient/1.0"}
            response = client.get("/", headers=headers)

            assert response.status_code == 200

            # extraパラメータに必要な情報が含まれていることを確認
            info_calls = mock_logger.info.call_args_list

            # 開始ログのextraパラメータを確認
            start_call = info_calls[0]
            if len(start_call) > 1 and "extra" in start_call[1]:
                extra_data = start_call[1]["extra"]
                assert extra_data["method"] == "GET"
                assert "url" in extra_data
                assert extra_data["user_agent"] == "TestClient/1.0"

    @patch("app.main.setup_logging")
    def test_request_logging_middleware_client_ip(self, mock_setup_logging):
        """リクエストロギングミドルウェアのクライアントIP テスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"
            mock_settings.debug = False
            mock_settings.upload_dir = "uploads"
            mock_settings.temp_dir = "temp"
            mock_settings.cors_origins = ["http://localhost:3000"]

            app = create_app()
            client = TestClient(app)

            response = client.get("/")

            assert response.status_code == 200

            # クライアントIP情報がログに含まれていることを確認
            info_calls = mock_logger.info.call_args_list

            # ログ呼び出しがあることを確認
            assert len(info_calls) > 0

            # 最初のログ呼び出し（リクエスト開始）でextraパラメータを確認
            if len(info_calls[0]) > 1 and "extra" in info_calls[0][1]:
                extra_data = info_calls[0][1]["extra"]
                # TestClientの場合、client.hostはNoneになる可能性がある
                assert "client_ip" in extra_data


class TestApplicationInitializationLogging:
    """アプリケーション初期化ロギングのテスト"""

    @patch("app.main.setup_logging")
    def test_application_initialization_logging(self, mock_setup_logging):
        """アプリケーション初期化ロギングテスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"
            mock_settings.debug = True
            mock_settings.upload_dir = "test_uploads"
            mock_settings.temp_dir = "test_temp"
            mock_settings.cors_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
            ]

            with patch("os.makedirs"):
                create_app()

                # 初期化ログが出力されたことを確認
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]

                # 期待されるログメッセージが含まれていることを確認
                assert any("アプリケーション初期化完了" in msg for msg in info_calls)
                assert any("test_uploads" in msg for msg in info_calls)
                assert any("test_temp" in msg for msg in info_calls)
                assert any("デバッグモード: True" in msg for msg in info_calls)

    @patch("app.main.setup_logging")
    def test_logging_system_initialization(self, mock_setup_logging):
        """ロギングシステム初期化テスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "DEBUG"
            mock_settings.log_dir = "custom_logs"

            # setup_loggingが正しいパラメータで呼び出されることを確認
            create_app()

            mock_setup_logging.assert_called_once_with(
                log_level="DEBUG", log_dir="custom_logs", app_name="video2minutes"
            )


class TestGlobalExceptionHandlerLogging:
    """グローバル例外ハンドラーロギングのテスト"""

    @patch("app.main.setup_logging")
    def test_global_exception_handler_logging(self, mock_setup_logging):
        """グローバル例外ハンドラーのロギングテスト"""
        # モックロガーを設定
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("app.main.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_dir = "logs"
            mock_settings.debug = True
            mock_settings.upload_dir = "uploads"
            mock_settings.temp_dir = "temp"
            mock_settings.cors_origins = ["http://localhost:3000"]

            app = create_app()

            # 例外を発生させるエンドポイントを追加
            @app.get("/test-exception")
            async def test_exception():
                raise ValueError("Test exception message")

            client = TestClient(app)

            response = client.get("/test-exception")

            assert response.status_code == 500

            # エラーログが出力されたことを確認
            error_calls = mock_logger.error.call_args_list

            # 未処理例外のログが出力されていることを確認
            exception_logs = [
                call for call in error_calls if "未処理例外" in call[0][0]
            ]
            assert len(exception_logs) > 0

            # 例外の詳細が含まれていることを確認
            exception_log = exception_logs[0][0][0]
            assert "ValueError" in exception_log
            assert "Test exception message" in exception_log

            # exc_info=Trueが設定されていることを確認
            if len(exception_logs[0]) > 1:
                kwargs = exception_logs[0][1]
                assert kwargs.get("exc_info") is True


class TestLoggingConfiguration:
    """ロギング設定のテスト"""

    @patch("app.main.setup_logging")
    def test_logging_configuration_with_different_levels(self, mock_setup_logging):
        """異なるログレベルでの設定テスト"""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        test_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

        for level in test_levels:
            with patch("app.main.settings") as mock_settings:
                mock_settings.log_level = level
                mock_settings.log_dir = f"logs_{level.lower()}"
                mock_settings.debug = False
                mock_settings.upload_dir = "uploads"
                mock_settings.temp_dir = "temp"
                mock_settings.cors_origins = []

                with patch("os.makedirs"):
                    create_app()

                    # setup_loggingが正しいログレベルで呼び出されることを確認
                    mock_setup_logging.assert_called_with(
                        log_level=level,
                        log_dir=f"logs_{level.lower()}",
                        app_name="video2minutes",
                    )

            mock_setup_logging.reset_mock()
