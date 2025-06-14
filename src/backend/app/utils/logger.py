import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def setup_logging(
    log_level: str = "INFO", log_dir: str = "logs", app_name: str = "video2minutes"
) -> logging.Logger:
    """
    ロギング設定をセットアップ

    Args:
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: ログファイル保存ディレクトリ
        app_name: アプリケーション名

    Returns:
        設定済みロガー
    """
    # ログディレクトリを作成
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # ログファイル名（日付付き）
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_path / f"{app_name}_{today}.log"
    error_log_file = log_path / f"{app_name}_error_{today}.log"

    # ログ設定
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {"()": "app.utils.logger.JSONFormatter"},
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": str(log_file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": str(error_log_file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file", "error_file"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "file", "error_file"],
                "level": "ERROR",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "fastapi": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    # ロギング設定を適用
    logging.config.dictConfig(logging_config)

    # メインロガーを取得
    logger = logging.getLogger(app_name)

    logger.info(f"ロギングシステムが初期化されました - ログレベル: {log_level}")
    logger.info(f"ログファイル: {log_file}")
    logger.info(f"エラーログファイル: {error_log_file}")

    return logger


class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッター"""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 例外情報がある場合は追加
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 追加属性がある場合は追加
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得

    Args:
        name: ロガー名

    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)


class LoggerMixin:
    """ログ機能をクラスに追加するMixin"""

    @property
    def logger(self) -> logging.Logger:
        """クラス名を使用したロガーを取得"""
        return get_logger(self.__class__.__name__)
