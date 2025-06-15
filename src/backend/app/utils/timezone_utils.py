import os
from datetime import datetime, timezone
from typing import Optional

import pytz

from app.config import settings


class TimezoneUtils:
    """タイムゾーン処理ユーティリティ"""
    
    @classmethod
    def get_timezone(cls) -> pytz.BaseTzInfo:
        """設定されたタイムゾーンを取得"""
        try:
            return pytz.timezone(settings.timezone)
        except pytz.UnknownTimeZoneError:
            # フォールバック: 日本時間
            return pytz.timezone("Asia/Tokyo")
    
    @classmethod
    def now(cls) -> datetime:
        """現在時刻を設定されたタイムゾーンで取得"""
        tz = cls.get_timezone()
        return datetime.now(tz)
    
    @classmethod
    def utc_now(cls) -> datetime:
        """現在時刻をUTCで取得"""
        return datetime.now(timezone.utc)
    
    @classmethod
    def to_local(cls, dt: datetime) -> datetime:
        """UTCまたはnaiveなdatetimeをローカルタイムゾーンに変換"""
        if dt is None:
            return None
            
        tz = cls.get_timezone()
        
        # naive datetimeの場合はUTCとして扱う
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # ローカルタイムゾーンに変換
        return dt.astimezone(tz)
    
    @classmethod
    def to_utc(cls, dt: datetime) -> datetime:
        """ローカルタイムゾーンのdatetimeをUTCに変換"""
        if dt is None:
            return None
            
        # naive datetimeの場合はローカルタイムゾーンとして扱う
        if dt.tzinfo is None:
            tz = cls.get_timezone()
            dt = tz.localize(dt)
        
        # UTCに変換
        return dt.astimezone(timezone.utc)
    
    @classmethod
    def format_local_datetime(cls, dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """datetimeをローカルタイムゾーンでフォーマット"""
        if dt is None:
            return ""
        
        local_dt = cls.to_local(dt)
        return local_dt.strftime(format_str)
    
    @classmethod
    def parse_iso_to_local(cls, iso_string: str) -> Optional[datetime]:
        """ISO形式の文字列をパースしてローカルタイムゾーンに変換"""
        try:
            # ISO形式をパース
            dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            return cls.to_local(dt)
        except (ValueError, TypeError):
            return None