"""セッションベースのタスクストア"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.models import MinutesTask
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class SessionTaskStore:
    """セッション単位でタスクを管理するストア（永続化対応）"""

    def __init__(self, enable_persistence: bool = True):
        # session_id -> {task_id -> MinutesTask}
        self._sessions: Dict[str, Dict[str, MinutesTask]] = {}
        # セッションの最終アクセス時刻を記録
        self._session_last_access: Dict[str, datetime] = {}
        
        # 永続化設定
        self._enable_persistence = enable_persistence
        self._persistent_store = None
        
        if enable_persistence:
            try:
                from app.store.persistent_store import persistent_store
                self._persistent_store = persistent_store
                # 起動時に永続化データを復元
                self._restore_from_persistence()
                logger.info("永続化ストアとの連携を開始")
            except Exception as e:
                logger.warning(f"永続化ストアの初期化に失敗（メモリモードで継続）: {e}")
                self._enable_persistence = False

    def get_tasks(self, session_id: str) -> List[MinutesTask]:
        """
        指定されたセッションのタスク一覧を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            タスクのリスト
        """
        self._update_last_access(session_id)
        tasks = list(self._sessions.get(session_id, {}).values())
        logger.debug(f"セッション {session_id[:8]}... のタスク数: {len(tasks)}")
        return tasks

    def get_task(self, session_id: str, task_id: str) -> Optional[MinutesTask]:
        """
        指定されたセッションの特定タスクを取得
        
        Args:
            session_id: セッションID
            task_id: タスクID
            
        Returns:
            タスクオブジェクト、見つからない場合はNone
        """
        self._update_last_access(session_id)
        task = self._sessions.get(session_id, {}).get(task_id)
        if task:
            logger.debug(f"タスク取得成功: {session_id[:8]}... -> {task_id[:8]}...")
        else:
            logger.warning(f"タスクが見つかりません: {session_id[:8]}... -> {task_id[:8]}...")
        return task

    def add_task(self, session_id: str, task: MinutesTask) -> None:
        """
        指定されたセッションにタスクを追加
        
        Args:
            session_id: セッションID
            task: 追加するタスク
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
            logger.info(f"新しいセッションのタスクストアを作成: {session_id[:8]}...")

        self._sessions[session_id][task.task_id] = task
        self._update_last_access(session_id)
        
        # 永続化
        if self._enable_persistence and self._persistent_store:
            try:
                self._persistent_store.add_task(session_id, task)
            except Exception as e:
                logger.warning(f"タスクの永続化に失敗: {e}")
        
        logger.info(f"タスクを追加: {session_id[:8]}... -> {task.task_id[:8]}... ({task.video_filename})")

    def update_task(self, session_id: str, task: MinutesTask) -> None:
        """
        指定されたセッションのタスクを更新
        
        Args:
            session_id: セッションID
            task: 更新するタスク
        """
        if session_id not in self._sessions or task.task_id not in self._sessions[session_id]:
            logger.warning(f"更新対象のタスクが見つかりません: {session_id[:8]}... -> {task.task_id[:8]}...")
            return

        self._sessions[session_id][task.task_id] = task
        self._update_last_access(session_id)
        
        # 永続化
        if self._enable_persistence and self._persistent_store:
            try:
                self._persistent_store.update_task(session_id, task)
            except Exception as e:
                logger.warning(f"タスクの永続化更新に失敗: {e}")
        
        logger.debug(f"タスクを更新: {session_id[:8]}... -> {task.task_id[:8]}... (status: {task.status})")

    def delete_task(self, session_id: str, task_id: str) -> bool:
        """
        指定されたセッションからタスクを削除
        
        Args:
            session_id: セッションID
            task_id: 削除するタスクID
            
        Returns:
            削除に成功した場合True、タスクが見つからない場合False
        """
        if session_id not in self._sessions or task_id not in self._sessions[session_id]:
            logger.warning(f"削除対象のタスクが見つかりません: {session_id[:8]}... -> {task_id[:8]}...")
            return False

        del self._sessions[session_id][task_id]
        self._update_last_access(session_id)
        
        # 永続化から削除
        if self._enable_persistence and self._persistent_store:
            try:
                self._persistent_store.delete_task(session_id, task_id)
            except Exception as e:
                logger.warning(f"タスクの永続化削除に失敗: {e}")
        
        # セッションが空になった場合は削除
        if not self._sessions[session_id]:
            del self._sessions[session_id]
            del self._session_last_access[session_id]
            logger.info(f"空のセッションを削除: {session_id[:8]}...")
        
        logger.info(f"タスクを削除: {session_id[:8]}... -> {task_id[:8]}...")
        return True

    def has_task(self, session_id: str, task_id: str) -> bool:
        """
        指定されたセッションに特定のタスクが存在するかチェック
        
        Args:
            session_id: セッションID
            task_id: タスクID
            
        Returns:
            タスクが存在する場合True
        """
        return session_id in self._sessions and task_id in self._sessions[session_id]

    def get_session_count(self) -> int:
        """
        アクティブなセッション数を取得
        
        Returns:
            セッション数
        """
        return len(self._sessions)

    def get_total_task_count(self) -> int:
        """
        全セッション合計のタスク数を取得
        
        Returns:
            タスク総数
        """
        return sum(len(tasks) for tasks in self._sessions.values())

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        古いセッションをクリーンアップ
        
        Args:
            max_age_hours: セッションの最大保持時間（時間）
            
        Returns:
            削除されたセッション数
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_sessions = [
            session_id for session_id, last_access in self._session_last_access.items()
            if last_access < cutoff_time
        ]
        
        for session_id in old_sessions:
            if session_id in self._sessions:
                task_count = len(self._sessions[session_id])
                del self._sessions[session_id]
                del self._session_last_access[session_id]
                logger.info(f"古いセッションを削除: {session_id[:8]}... ({task_count}個のタスク)")
        
        if old_sessions:
            logger.info(f"セッションクリーンアップ完了: {len(old_sessions)}個のセッションを削除")
        
        return len(old_sessions)

    def _update_last_access(self, session_id: str) -> None:
        """
        セッションの最終アクセス時刻を更新
        
        Args:
            session_id: セッションID
        """
        self._session_last_access[session_id] = datetime.now()

    def get_session_stats(self) -> Dict[str, int]:
        """
        セッション統計情報を取得
        
        Returns:
            統計情報辞書
        """
        stats = {
            "total_sessions": len(self._sessions),
            "total_tasks": sum(len(tasks) for tasks in self._sessions.values()),
            "empty_sessions": sum(1 for tasks in self._sessions.values() if len(tasks) == 0)
        }
        
        if self._sessions:
            task_counts = [len(tasks) for tasks in self._sessions.values()]
            stats.update({
                "max_tasks_per_session": max(task_counts),
                "min_tasks_per_session": min(task_counts),
                "avg_tasks_per_session": sum(task_counts) / len(task_counts)
            })
        
        return stats

    def _restore_from_persistence(self) -> None:
        """永続化ストアからデータを復元"""
        if not self._persistent_store:
            return
            
        try:
            # 全タスクを取得
            all_tasks = self._persistent_store.get_all_tasks()
            
            # 各タスクをセッションごとに分類
            restored_count = 0
            for task_id, task in all_tasks.items():
                # タスクに関連するセッションを見つける
                for session_id in self._persistent_store._sessions_cache:
                    if task_id in self._persistent_store._sessions_cache[session_id]:
                        # メモリキャッシュに復元
                        if session_id not in self._sessions:
                            self._sessions[session_id] = {}
                        self._sessions[session_id][task_id] = task
                        self._update_last_access(session_id)
                        restored_count += 1
                        break
                        
            if restored_count > 0:
                logger.info(f"永続化ストアから{restored_count}件のタスクを復元")
                
        except Exception as e:
            logger.error(f"永続化データの復元に失敗: {e}", exc_info=True)


# グローバルなセッションタスクストアインスタンス
session_task_store = SessionTaskStore(enable_persistence=settings.enable_persistence)