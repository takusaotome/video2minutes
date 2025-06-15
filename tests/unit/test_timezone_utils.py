"""タイムゾーンユーティリティのテスト"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytz

from app.utils.timezone_utils import TimezoneUtils


class TestTimezoneUtils:
    """タイムゾーンユーティリティのテスト"""

    def test_get_timezone_default(self):
        """デフォルトタイムゾーン取得テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            tz = TimezoneUtils.get_timezone()
            
            assert isinstance(tz, pytz.BaseTzInfo)
            assert str(tz) == "Asia/Tokyo"

    def test_get_timezone_custom(self):
        """カスタムタイムゾーン取得テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "America/New_York"
            
            tz = TimezoneUtils.get_timezone()
            
            assert isinstance(tz, pytz.BaseTzInfo)
            assert str(tz) == "America/New_York"

    def test_get_timezone_unknown_fallback(self):
        """不明なタイムゾーンの場合のフォールバックテスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Invalid/Timezone"
            
            tz = TimezoneUtils.get_timezone()
            
            # フォールバックでAsia/Tokyoが返される
            assert str(tz) == "Asia/Tokyo"

    def test_now(self):
        """現在時刻取得テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            now = TimezoneUtils.now()
            
            assert isinstance(now, datetime)
            assert now.tzinfo is not None
            assert str(now.tzinfo) == "Asia/Tokyo"

    def test_utc_now(self):
        """UTC現在時刻取得テスト"""
        utc_now = TimezoneUtils.utc_now()
        
        assert isinstance(utc_now, datetime)
        assert utc_now.tzinfo == timezone.utc

    def test_to_local_from_utc(self):
        """UTCからローカル時間への変換テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            # UTC時間を作成
            utc_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            
            local_time = TimezoneUtils.to_local(utc_time)
            
            assert isinstance(local_time, datetime)
            assert local_time.tzinfo is not None
            assert str(local_time.tzinfo) == "Asia/Tokyo"
            # 日本時間は UTC+9 なので21時になる
            assert local_time.hour == 21

    def test_to_local_from_naive(self):
        """naive datetimeからローカル時間への変換テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            # naive datetimeを作成
            naive_time = datetime(2024, 1, 15, 12, 0, 0)
            
            local_time = TimezoneUtils.to_local(naive_time)
            
            assert isinstance(local_time, datetime)
            assert local_time.tzinfo is not None
            assert str(local_time.tzinfo) == "Asia/Tokyo"

    def test_to_local_none_input(self):
        """None入力の場合のテスト"""
        result = TimezoneUtils.to_local(None)
        
        assert result is None

    def test_to_utc_from_local(self):
        """ローカル時間からUTCへの変換テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            # 日本時間（naive）を作成
            local_time = datetime(2024, 1, 15, 21, 0, 0)
            
            utc_time = TimezoneUtils.to_utc(local_time)
            
            assert isinstance(utc_time, datetime)
            assert utc_time.tzinfo == timezone.utc
            # 日本時間21時はUTC12時
            assert utc_time.hour == 12

    def test_to_utc_from_aware_datetime(self):
        """タイムゾーン付きdatetimeからUTCへの変換テスト"""
        # New York時間を作成
        ny_tz = pytz.timezone("America/New_York")
        ny_time = ny_tz.localize(datetime(2024, 1, 15, 12, 0, 0))
        
        utc_time = TimezoneUtils.to_utc(ny_time)
        
        assert isinstance(utc_time, datetime)
        assert utc_time.tzinfo == timezone.utc
        # New York時間12時は UTC17時（EST: UTC-5）
        assert utc_time.hour == 17

    def test_to_utc_none_input(self):
        """None入力の場合のテスト"""
        result = TimezoneUtils.to_utc(None)
        
        assert result is None

    def test_format_local_datetime_default_format(self):
        """デフォルトフォーマットでの日時フォーマットテスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            # UTC時間を作成
            utc_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            
            formatted = TimezoneUtils.format_local_datetime(utc_time)
            
            assert isinstance(formatted, str)
            assert "2024-01-15" in formatted
            assert "21:00:00" in formatted  # 日本時間

    def test_format_local_datetime_custom_format(self):
        """カスタムフォーマットでの日時フォーマットテスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            # UTC時間を作成
            utc_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            
            formatted = TimezoneUtils.format_local_datetime(utc_time, "%Y/%m/%d %H:%M")
            
            assert isinstance(formatted, str)
            assert "2024/01/15" in formatted
            assert "21:00" in formatted

    def test_format_local_datetime_none_input(self):
        """None入力の場合のフォーマットテスト"""
        formatted = TimezoneUtils.format_local_datetime(None)
        
        assert formatted == ""

    def test_parse_iso_to_local_valid_iso(self):
        """有効なISO文字列のパーステスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            iso_string = "2024-01-15T12:00:00Z"
            
            parsed = TimezoneUtils.parse_iso_to_local(iso_string)
            
            assert isinstance(parsed, datetime)
            assert parsed.tzinfo is not None
            assert str(parsed.tzinfo) == "Asia/Tokyo"
            assert parsed.hour == 21  # UTC 12:00 -> JST 21:00

    def test_parse_iso_to_local_with_timezone(self):
        """タイムゾーン付きISO文字列のパーステスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            iso_string = "2024-01-15T12:00:00+05:00"
            
            parsed = TimezoneUtils.parse_iso_to_local(iso_string)
            
            assert isinstance(parsed, datetime)
            assert parsed.tzinfo is not None
            assert str(parsed.tzinfo) == "Asia/Tokyo"

    def test_parse_iso_to_local_invalid_format(self):
        """無効なフォーマットのISO文字列テスト"""
        iso_string = "invalid-date-format"
        
        parsed = TimezoneUtils.parse_iso_to_local(iso_string)
        
        assert parsed is None

    def test_parse_iso_to_local_none_input(self):
        """None入力の場合のパーステスト"""
        parsed = TimezoneUtils.parse_iso_to_local(None)
        
        assert parsed is None

    def test_parse_iso_to_local_empty_string(self):
        """空文字列の場合のパーステスト"""
        parsed = TimezoneUtils.parse_iso_to_local("")
        
        assert parsed is None

    def test_timezone_consistency(self):
        """タイムゾーン一貫性テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Europe/London"
            
            # 現在時刻を取得
            now = TimezoneUtils.now()
            
            # UTCに変換してから再度ローカルに変換
            utc_time = TimezoneUtils.to_utc(now)
            back_to_local = TimezoneUtils.to_local(utc_time)
            
            # 元の時刻とほぼ同じになることを確認（秒以下の差は許容）
            time_diff = abs((now - back_to_local).total_seconds())
            assert time_diff < 1.0

    def test_dst_handling(self):
        """夏時間処理テスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "America/New_York"
            
            # 夏時間期間（7月）
            summer_utc = datetime(2024, 7, 15, 16, 0, 0, tzinfo=timezone.utc)
            summer_local = TimezoneUtils.to_local(summer_utc)
            
            # 標準時間期間（1月）
            winter_utc = datetime(2024, 1, 15, 17, 0, 0, tzinfo=timezone.utc)
            winter_local = TimezoneUtils.to_local(winter_utc)
            
            # 夏時間と標準時間で適切に変換されることを確認
            assert summer_local.hour == 12  # EDT: UTC-4
            assert winter_local.hour == 12  # EST: UTC-5

    def test_edge_case_year_boundary(self):
        """年境界エッジケーステスト"""
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            # 年末UTC時間
            utc_new_year = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            local_new_year = TimezoneUtils.to_local(utc_new_year)
            
            # 日本時間では1月1日の9時
            assert local_new_year.hour == 9
            assert local_new_year.day == 1
            assert local_new_year.month == 1
            assert local_new_year.year == 2024

    def test_format_different_timezones(self):
        """異なるタイムゾーンでのフォーマットテスト"""
        utc_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        # 複数のタイムゾーンでテスト
        timezones = ["Asia/Tokyo", "America/New_York", "Europe/London"]
        
        for tz_name in timezones:
            with patch('app.utils.timezone_utils.settings') as mock_settings:
                mock_settings.timezone = tz_name
                
                formatted = TimezoneUtils.format_local_datetime(utc_time)
                
                assert isinstance(formatted, str)
                assert "2024-06-15" in formatted
                assert len(formatted) > 10  # 日付と時刻が含まれている

    def test_class_methods_independence(self):
        """クラスメソッドの独立性テスト"""
        # 異なるメソッドが互いに独立して動作することを確認
        with patch('app.utils.timezone_utils.settings') as mock_settings:
            mock_settings.timezone = "Asia/Tokyo"
            
            now = TimezoneUtils.now()
            utc_now = TimezoneUtils.utc_now()
            tz = TimezoneUtils.get_timezone()
            
            # それぞれが適切な型を返すことを確認
            assert isinstance(now, datetime)
            assert isinstance(utc_now, datetime)
            assert isinstance(tz, pytz.BaseTzInfo)
            
            # タイムゾーン情報が適切であることを確認
            assert now.tzinfo is not None
            assert utc_now.tzinfo == timezone.utc
            assert str(tz) == "Asia/Tokyo"