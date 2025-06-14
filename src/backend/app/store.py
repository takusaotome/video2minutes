"""
グローバルデータストア
アプリケーション全体で共有されるデータを管理
"""

from typing import Dict
from app.models import MinutesTask

# グローバルタスクストア（本番環境ではRedisやDBを使用）
tasks_store: Dict[str, MinutesTask] = {}
