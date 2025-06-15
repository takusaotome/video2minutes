"""永続化タスクストア"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from app.models import MinutesTask, TaskStatus, ProcessingStepName, ProcessingStepStatus, ProcessingStep
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PersistentTaskStore:
    """タスクの永続化ストア（JSONファイルベース）"""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.tasks_file = self.storage_dir / "tasks.json"
        self.sessions_file = self.storage_dir / "sessions.json"
        
        # メモリ内キャッシュ
        self._tasks_cache: Dict[str, MinutesTask] = {}
        self._sessions_cache: Dict[str, Dict[str, str]] = {}  # session_id -> {task_id -> task_id}
        
        # 起動時にデータをロード
        self._load_data()

    def _load_data(self) -> None:
        """ファイルからデータを読み込み"""
        try:
            # タスクデータの読み込み
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                    
                for task_id, task_dict in tasks_data.items():
                    try:
                        task = self._dict_to_task(task_dict)
                        self._tasks_cache[task_id] = task
                    except Exception as e:
                        logger.warning(f"タスクの復元に失敗: {task_id} - {e}")
                        
                logger.info(f"タスクデータを読み込み: {len(self._tasks_cache)}件")

            # セッションデータの読み込み
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    self._sessions_cache = json.load(f)
                    
                logger.info(f"セッションデータを読み込み: {len(self._sessions_cache)}個のセッション")
                
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}", exc_info=True)

    def _save_data(self) -> None:
        """データをファイルに保存"""
        try:
            # タスクデータの保存
            tasks_data = {}
            for task_id, task in self._tasks_cache.items():
                try:
                    tasks_data[task_id] = self._task_to_dict(task)
                except Exception as e:
                    logger.warning(f"タスクの保存に失敗: {task_id} - {e}")
                    
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, ensure_ascii=False, indent=2, default=str)

            # セッションデータの保存
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self._sessions_cache, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"データを保存: {len(self._tasks_cache)}件のタスク, {len(self._sessions_cache)}個のセッション")
            
        except Exception as e:
            logger.error(f"データ保存エラー: {e}", exc_info=True)

    def _task_to_dict(self, task: MinutesTask) -> dict:
        """MinutesTaskを辞書に変換"""
        return {
            "task_id": task.task_id,
            "video_filename": task.video_filename,
            "video_size": task.video_size,
            "upload_timestamp": task.upload_timestamp.isoformat(),
            "status": task.status.value,
            "current_step": task.current_step.value if task.current_step else None,
            "overall_progress": task.overall_progress,
            "transcription": task.transcription,
            "minutes": task.minutes,
            "error_message": task.error_message,
            "processing_duration": getattr(task, 'processing_duration', None),
            "steps": [
                {
                    "name": step.name.value,
                    "status": step.status.value,
                    "progress": step.progress,
                    "error_message": step.error_message
                }
                for step in task.steps
            ]
        }

    def _dict_to_task(self, data: dict) -> MinutesTask:
        """辞書からMinutesTaskを復元"""
        task = MinutesTask(
            task_id=data["task_id"],
            video_filename=data["video_filename"],
            video_size=data["video_size"],
            upload_timestamp=datetime.fromisoformat(data["upload_timestamp"])
        )
        
        task.status = TaskStatus(data["status"])
        task.current_step = ProcessingStepName(data["current_step"]) if data["current_step"] else None
        task.overall_progress = data["overall_progress"]
        task.transcription = data.get("transcription")
        task.minutes = data.get("minutes")
        task.error_message = data.get("error_message")
        # processing_duration field doesn't exist in MinutesTask model - skip it
        
        # ステップの復元
        task.steps = []
        for step_data in data.get("steps", []):
            step = ProcessingStep(
                name=ProcessingStepName(step_data["name"]),
                status=ProcessingStepStatus(step_data["status"]),
                progress=step_data["progress"],
                error_message=step_data.get("error_message")
            )
            task.steps.append(step)
            
        return task

    def add_task(self, session_id: str, task: MinutesTask) -> None:
        """タスクを追加"""
        self._tasks_cache[task.task_id] = task
        
        if session_id not in self._sessions_cache:
            self._sessions_cache[session_id] = {}
        self._sessions_cache[session_id][task.task_id] = task.task_id
        
        self._save_data()
        logger.info(f"タスクを永続化ストアに追加: {session_id[:8]}... -> {task.task_id[:8]}...")

    def update_task(self, session_id: str, task: MinutesTask) -> None:
        """タスクを更新"""
        if task.task_id in self._tasks_cache:
            self._tasks_cache[task.task_id] = task
            self._save_data()
            logger.debug(f"タスクを永続化ストアで更新: {session_id[:8]}... -> {task.task_id[:8]}...")

    def get_task(self, session_id: str, task_id: str) -> Optional[MinutesTask]:
        """タスクを取得"""
        if session_id in self._sessions_cache and task_id in self._sessions_cache[session_id]:
            return self._tasks_cache.get(task_id)
        return None

    def get_tasks(self, session_id: str) -> List[MinutesTask]:
        """セッションのタスク一覧を取得"""
        if session_id not in self._sessions_cache:
            return []
            
        tasks = []
        for task_id in self._sessions_cache[session_id].keys():
            if task_id in self._tasks_cache:
                tasks.append(self._tasks_cache[task_id])
                
        return tasks

    def delete_task(self, session_id: str, task_id: str) -> bool:
        """タスクを削除"""
        if session_id in self._sessions_cache and task_id in self._sessions_cache[session_id]:
            del self._sessions_cache[session_id][task_id]
            
            # セッションが空になった場合は削除
            if not self._sessions_cache[session_id]:
                del self._sessions_cache[session_id]
                
            # タスク自体を削除
            if task_id in self._tasks_cache:
                del self._tasks_cache[task_id]
                
            self._save_data()
            logger.info(f"タスクを永続化ストアから削除: {session_id[:8]}... -> {task_id[:8]}...")
            return True
            
        return False

    def has_task(self, session_id: str, task_id: str) -> bool:
        """タスクの存在確認"""
        return (session_id in self._sessions_cache and 
                task_id in self._sessions_cache[session_id] and
                task_id in self._tasks_cache)

    def get_all_tasks(self) -> Dict[str, MinutesTask]:
        """全タスクを取得"""
        return self._tasks_cache.copy()

    def cleanup_old_tasks(self, max_age_hours: int = 72) -> int:
        """古いタスクをクリーンアップ"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_task_ids = []
        
        for task_id, task in self._tasks_cache.items():
            if task.upload_timestamp < cutoff_time:
                old_task_ids.append(task_id)
                
        # 古いタスクを削除
        for task_id in old_task_ids:
            # セッションからも削除
            for session_id, session_tasks in list(self._sessions_cache.items()):
                if task_id in session_tasks:
                    del session_tasks[task_id]
                    if not session_tasks:
                        del self._sessions_cache[session_id]
                        
            # タスク自体を削除
            del self._tasks_cache[task_id]
            
        if old_task_ids:
            self._save_data()
            logger.info(f"古いタスクをクリーンアップ: {len(old_task_ids)}件")
            
        return len(old_task_ids)


# グローバルな永続化ストアインスタンス
persistent_store = PersistentTaskStore()