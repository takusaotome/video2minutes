import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils.logger import JSONFormatter, LoggerMixin, get_logger, setup_logging


class TestSetupLogging:
    """setup_logging関数のテスト"""

    def test_setup_logging_creates_log_directory(self):
        """ログディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "test_logs")

            logger = setup_logging(log_dir=log_dir, app_name="test_app")

            # ディレクトリが作成されていることを確認
            assert os.path.exists(log_dir)
            assert isinstance(logger, logging.Logger)

    def test_setup_logging_creates_log_files(self):
        """ログファイル作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "test_logs")
            app_name = "test_app"

            logger = setup_logging(log_dir=log_dir, app_name=app_name)

            # ログファイルパスを確認
            today = datetime.now().strftime("%Y-%m-%d")
            expected_log_file = Path(log_dir) / f"{app_name}_{today}.log"
            expected_error_log_file = Path(log_dir) / f"{app_name}_error_{today}.log"

            # ファイルが作成されているかは、実際にログを出力した後に確認
            logger.info("Test log message")
            logger.error("Test error message")

            # ログファイルが存在することを確認
            assert expected_log_file.exists()
            assert expected_error_log_file.exists()

    def test_setup_logging_with_different_log_levels(self):
        """異なるログレベルでの設定テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                log_dir = os.path.join(temp_dir, f"logs_{level}")

                logger = setup_logging(
                    log_level=level, log_dir=log_dir, app_name="test"
                )

                # ロガーのレベルが設定されていることを確認
                assert logger.level <= getattr(logging, level)

    def test_setup_logging_returns_configured_logger(self):
        """設定されたロガーの戻り値テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_name = "test_app"
            logger = setup_logging(log_dir=temp_dir, app_name=app_name)

            # 正しいロガーが返されることを確認
            assert isinstance(logger, logging.Logger)
            assert logger.name == app_name

    def test_setup_logging_handlers_configuration(self):
        """ハンドラー設定テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_dir=temp_dir, app_name="test")

            # ルートロガーにハンドラーが設定されていることを確認
            root_logger = logging.getLogger()
            handler_types = [type(handler).__name__ for handler in root_logger.handlers]

            # 期待されるハンドラーが含まれているかを確認
            assert "StreamHandler" in handler_types
            assert "RotatingFileHandler" in handler_types

    @patch("app.utils.logger.datetime")
    def test_setup_logging_log_file_naming(self, mock_datetime):
        """ログファイル命名テスト"""
        # 固定の日付を設定
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01"

        with tempfile.TemporaryDirectory() as temp_dir:
            app_name = "test_app"
            logger = setup_logging(log_dir=temp_dir, app_name=app_name)

            # ファイル名が正しいフォーマットであることを確認
            expected_log_file = Path(temp_dir) / f"{app_name}_2024-01-01.log"
            expected_error_log_file = (
                Path(temp_dir) / f"{app_name}_error_2024-01-01.log"
            )

            # 実際にログを出力してファイルを作成
            logger.info("Test message")
            logger.error("Test error")

            assert expected_log_file.exists()
            assert expected_error_log_file.exists()


class TestGetLogger:
    """get_logger関数のテスト"""

    def test_get_logger_returns_logger_instance(self):
        """ロガーインスタンス取得テスト"""
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_get_logger_with_different_names(self):
        """異なる名前でのロガー取得テスト"""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        assert logger1.name == "logger1"
        assert logger2.name == "logger2"
        assert logger1 != logger2

    def test_get_logger_same_name_returns_same_instance(self):
        """同じ名前での同一インスタンス取得テスト"""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")

        assert logger1 is logger2


class TestLoggerMixin:
    """LoggerMixin クラスのテスト"""

    def test_logger_mixin_provides_logger_property(self):
        """LoggerMixinのロガープロパティテスト"""

        class TestClass(LoggerMixin):
            pass

        instance = TestClass()
        logger = instance.logger

        assert isinstance(logger, logging.Logger)
        assert logger.name == "TestClass"

    def test_logger_mixin_different_classes_get_different_loggers(self):
        """異なるクラスでの異なるロガー取得テスト"""

        class TestClass1(LoggerMixin):
            pass

        class TestClass2(LoggerMixin):
            pass

        instance1 = TestClass1()
        instance2 = TestClass2()

        assert instance1.logger.name == "TestClass1"
        assert instance2.logger.name == "TestClass2"
        assert instance1.logger != instance2.logger

    def test_logger_mixin_inheritance(self):
        """LoggerMixin継承テスト"""

        class BaseClass(LoggerMixin):
            def log_message(self, message):
                self.logger.info(message)

        class DerivedClass(BaseClass):
            pass

        instance = DerivedClass()

        # 継承されたクラスでも正しいロガー名が取得されることを確認
        assert instance.logger.name == "DerivedClass"

        # メソッドが正常に動作することを確認
        with patch.object(instance.logger, "info") as mock_info:
            instance.log_message("test message")
            mock_info.assert_called_once_with("test message")


class TestJSONFormatter:
    """JSONFormatter クラスのテスト"""

    def test_json_formatter_basic_format(self):
        """基本的なJSONフォーマットテスト"""
        formatter = JSONFormatter()

        # テスト用のログレコードを作成
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # 必要なフィールドが含まれていることを確認
        assert "timestamp" in log_data
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["line"] == 42

    def test_json_formatter_with_exception(self):
        """例外情報付きJSONフォーマットテスト"""
        formatter = JSONFormatter()

        # 例外を発生させてキャプチャ
        import sys

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
        else:
            exc_info = None

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # 例外情報が含まれていることを確認
        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
        assert "Test exception" in log_data["exception"]

    def test_json_formatter_with_extra_attributes(self):
        """追加属性付きJSONフォーマットテスト"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # 追加属性を設定
        record.custom_field = "custom_value"
        record.request_id = "12345"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # 追加属性が含まれていることを確認
        assert log_data["custom_field"] == "custom_value"
        assert log_data["request_id"] == "12345"

    def test_json_formatter_timestamp_format(self):
        """タイムスタンプフォーマットテスト"""
        formatter = JSONFormatter()

        # 固定時刻を設定
        fixed_time = 1640995200.0  # 2022-01-01 00:00:00 UTC

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = fixed_time

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # ISO形式のタイムスタンプであることを確認
        timestamp = log_data["timestamp"]
        assert isinstance(timestamp, str)
        # ISO形式の基本的な構造を確認
        assert "T" in timestamp or "-" in timestamp


class TestLoggingIntegration:
    """ロギング統合テスト"""

    def test_logging_integration_with_services(self):
        """サービスクラスとの統合テスト"""

        # LoggerMixinを使用するサービスクラスを模擬
        class MockService(LoggerMixin):
            def __init__(self):
                self.logger.info("サービス初期化完了")

            def process(self):
                self.logger.debug("処理開始")
                self.logger.info("処理完了")

        # ログキャプチャを設定
        with patch.object(logging.getLogger("MockService"), "info") as mock_info:
            with patch.object(logging.getLogger("MockService"), "debug") as mock_debug:
                service = MockService()
                service.process()

                # ログが正しく呼び出されたことを確認
                mock_info.assert_any_call("サービス初期化完了")
                mock_info.assert_any_call("処理完了")
                mock_debug.assert_called_once_with("処理開始")

    def test_logging_configuration_persistence(self):
        """ログ設定の永続性テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 最初にロギングを設定
            setup_logging(log_dir=temp_dir, app_name="test", log_level="DEBUG")

            # 新しいロガーを取得し、ハンドラー設定を確認
            get_logger("test_module")
            logging.getLogger("another_module")

            # 両方のロガーが設定されたハンドラーを使用していることを確認
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0

            # ログレベルが正しく設定されていることを確認
            assert root_logger.level <= logging.DEBUG


class TestLoggingErrorHandling:
    """ロギングエラーハンドリングテスト"""

    def test_json_formatter_handles_non_serializable_objects(self):
        """非シリアライズ可能オブジェクトの処理テスト"""
        formatter = JSONFormatter()

        # 非シリアライズ可能なオブジェクトを含むレコード
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # 非シリアライズ可能なオブジェクトを追加
        record.non_serializable = object()

        # エラーが発生しないことを確認
        try:
            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            # オブジェクトが文字列として変換されていることを確認
            assert "non_serializable" in log_data
            assert isinstance(log_data["non_serializable"], str)
        except Exception:
            pytest.fail(
                "JSONFormatter should handle non-serializable objects gracefully"
            )

    def test_setup_logging_with_invalid_directory_permissions(self):
        """権限のないディレクトリでのログ設定テスト"""
        # このテストは実行環境によって結果が変わる可能性があるため、
        # モックを使用してエラー処理をテスト
        with patch(
            "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
        ):
            with pytest.raises(PermissionError):
                setup_logging(log_dir="/invalid/path", app_name="test")
