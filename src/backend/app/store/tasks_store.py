"""
タスクストア
議事録生成タスクの管理
"""

from typing import Dict
from ..models import MinutesTask

# グローバルタスクストア（本番環境ではRedisやDBを使用）
tasks_store: Dict[str, MinutesTask] = {}