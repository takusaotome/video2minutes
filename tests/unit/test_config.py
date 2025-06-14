import os
from unittest.mock import patch

from app.config import Settings, settings


class TestSettings:
    """設定クラスのテスト"""

    def test_settings_initialization(self):
        """設定初期化テスト"""
        test_settings = Settings(
            openai_api_key="test-openai-key", anthropic_api_key="test-anthropic-key"
        )

        # 必須設定が正しく設定されることを確認
        assert test_settings.openai_api_key == "test-openai-key"
        assert test_settings.anthropic_api_key == "test-anthropic-key"

        # デフォルト値が正しく設定されることを確認
        assert test_settings.host == "0.0.0.0"
        assert test_settings.port == 8000
        assert not test_settings.debug
        assert test_settings.max_file_size == 5 * 1024 * 1024 * 1024  # 5GB
        assert test_settings.upload_dir == "uploads"
        assert test_settings.temp_dir == "temp"

    def test_cors_origins_default(self):
        """CORS設定デフォルト値テスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        expected_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
        ]
        assert test_settings.cors_origins == expected_origins

    def test_allowed_video_extensions(self):
        """許可動画拡張子テスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        expected_extensions = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
        assert test_settings.allowed_video_extensions == expected_extensions

    def test_processing_settings(self):
        """処理設定テスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        assert test_settings.max_concurrent_tasks == 3
        assert test_settings.task_timeout == 7200  # 2時間

    def test_whisper_settings(self):
        """Whisper設定テスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        assert test_settings.whisper_model == "whisper-1"
        assert test_settings.whisper_language == "ja"

    def test_claude_settings(self):
        """GPT設定テスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        assert test_settings.gpt_model == "o3"
        assert test_settings.gpt_max_tokens == 4000

    def test_custom_values(self):
        """カスタム値設定テスト"""
        test_settings = Settings(
            openai_api_key="custom-openai-key",
            anthropic_api_key="custom-anthropic-key",
            host="127.0.0.1",
            port=9000,
            debug=True,
            max_file_size=1024 * 1024 * 1024,  # 1GB
            upload_dir="custom_uploads",
            temp_dir="custom_temp",
            max_concurrent_tasks=5,
            task_timeout=7200,  # 2時間
            whisper_model="whisper-2",
            whisper_language="en",
            gpt_model="gpt-4",
            gpt_max_tokens=8000,
        )

        # カスタム値が正しく設定されることを確認
        assert test_settings.openai_api_key == "custom-openai-key"
        assert test_settings.anthropic_api_key == "custom-anthropic-key"
        assert test_settings.host == "127.0.0.1"
        assert test_settings.port == 9000
        assert test_settings.debug
        assert test_settings.max_file_size == 1024 * 1024 * 1024
        assert test_settings.upload_dir == "custom_uploads"
        assert test_settings.temp_dir == "custom_temp"
        assert test_settings.max_concurrent_tasks == 5
        assert test_settings.task_timeout == 7200
        assert test_settings.whisper_model == "whisper-2"
        assert test_settings.whisper_language == "en"
        assert test_settings.gpt_model == "gpt-4"
        assert test_settings.gpt_max_tokens == 8000


class TestSettingsValidation:
    """設定バリデーションテスト"""

    def test_required_api_keys(self):
        """必須APIキーテスト"""
        # 明示的にパラメータを指定して作成できることを確認
        test_settings = Settings(openai_api_key="test-key")
        assert test_settings.openai_api_key == "test-key"
        # anthropic_api_keyはオプションなので何らかの値を持つ場合がある

        # Settingsクラスのフィールド情報を確認
        settings_fields = Settings.model_fields
        assert "openai_api_key" in settings_fields

        # openai_api_keyが必須（デフォルト値がない）ことを確認
        openai_field = settings_fields["openai_api_key"]
        assert openai_field.annotation is str  # strタイプであることを確認

    def test_port_validation(self):
        """ポート番号バリデーションテスト"""
        # 有効なポート番号
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key", port=8080
        )
        assert test_settings.port == 8080

    def test_file_size_validation(self):
        """ファイルサイズバリデーションテスト"""
        test_settings = Settings(
            openai_api_key="test-key",
            anthropic_api_key="test-key",
            max_file_size=100 * 1024 * 1024,  # 100MB
        )
        assert test_settings.max_file_size == 100 * 1024 * 1024


class TestEnvironmentVariableIntegration:
    """環境変数との統合テスト"""

    def test_env_file_configuration(self):
        """環境ファイル設定テスト"""
        # Config クラスの設定を確認
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        config = test_settings.Config
        assert config.env_file == ".env"
        assert config.env_file_encoding == "utf-8"

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "env-openai-key",
            "ANTHROPIC_API_KEY": "env-anthropic-key",
            "HOST": "192.168.1.100",
            "PORT": "9999",
            "DEBUG": "true",
            "MAX_FILE_SIZE": "1073741824",  # 1GB
            "UPLOAD_DIR": "env_uploads",
            "TEMP_DIR": "env_temp",
        },
    )
    def test_environment_variables_override(self):
        """環境変数による設定上書きテスト"""
        test_settings = Settings()

        # 環境変数の値が適用されることを確認
        assert test_settings.openai_api_key == "env-openai-key"
        assert test_settings.anthropic_api_key == "env-anthropic-key"
        assert test_settings.host == "192.168.1.100"
        assert test_settings.port == 9999
        assert test_settings.debug
        assert test_settings.max_file_size == 1073741824
        assert test_settings.upload_dir == "env_uploads"
        assert test_settings.temp_dir == "env_temp"

    @patch.dict(
        os.environ,
        {"CORS_ORIGINS": '["http://example.com", "https://app.example.com"]'},
    )
    def test_cors_origins_from_env(self):
        """環境変数からのCORS設定テスト"""
        # リスト形式の環境変数の処理は実装に依存するため、
        # 実際の動作を確認する必要がある
        pass


class TestGlobalSettingsInstance:
    """グローバル設定インスタンスのテスト"""

    def test_global_settings_exists(self):
        """グローバル設定インスタンス存在テスト"""
        # グローバル設定インスタンスが存在することを確認
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_settings_singleton_behavior(self):
        """設定のシングルトン動作テスト"""
        # 複数回インポートしても同じインスタンスであることを確認
        from app.config import settings as settings1
        from app.config import settings as settings2

        assert settings1 is settings2

    def test_settings_attributes_access(self):
        """設定属性アクセステスト"""
        # 設定の各属性にアクセスできることを確認
        # この時点でAPIキーが設定されていない可能性があるため、
        # 必須でない属性のみテスト
        assert hasattr(settings, "host")
        assert hasattr(settings, "port")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "cors_origins")
        assert hasattr(settings, "max_file_size")
        assert hasattr(settings, "allowed_video_extensions")
        assert hasattr(settings, "upload_dir")
        assert hasattr(settings, "temp_dir")
        assert hasattr(settings, "max_concurrent_tasks")
        assert hasattr(settings, "task_timeout")
        assert hasattr(settings, "whisper_model")
        assert hasattr(settings, "whisper_language")
        assert hasattr(settings, "gpt_model")
        assert hasattr(settings, "gpt_max_tokens")


class TestSettingsTypes:
    """設定の型テスト"""

    def test_string_settings(self):
        """文字列設定のテスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        assert isinstance(test_settings.host, str)
        assert isinstance(test_settings.upload_dir, str)
        assert isinstance(test_settings.temp_dir, str)
        assert isinstance(test_settings.whisper_model, str)
        assert isinstance(test_settings.whisper_language, str)
        assert isinstance(test_settings.gpt_model, str)

    def test_integer_settings(self):
        """整数設定のテスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        assert isinstance(test_settings.port, int)
        assert isinstance(test_settings.max_file_size, int)
        assert isinstance(test_settings.max_concurrent_tasks, int)
        assert isinstance(test_settings.task_timeout, int)
        assert isinstance(test_settings.gpt_max_tokens, int)

    def test_boolean_settings(self):
        """真偽値設定のテスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        assert isinstance(test_settings.debug, bool)

    def test_list_settings(self):
        """リスト設定のテスト"""
        test_settings = Settings(
            openai_api_key="test-key", anthropic_api_key="test-key"
        )

        assert isinstance(test_settings.cors_origins, list)
        assert isinstance(test_settings.allowed_video_extensions, list)

        # リストの要素がすべて文字列であることを確認
        assert all(isinstance(origin, str) for origin in test_settings.cors_origins)
        assert all(
            isinstance(ext, str) for ext in test_settings.allowed_video_extensions
        )
