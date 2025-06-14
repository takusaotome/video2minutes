import asyncio
import uuid
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from enum import Enum

from app.utils.logger import LoggerMixin


class TaskQueueStatus(str, Enum):
    """タスクキューステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class QueuedTask:
    """キューに登録されるタスク"""
    
    def __init__(self, task_id: str, func: Callable, *args, **kwargs):
        self.id = str(uuid.uuid4())
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = TaskQueueStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.result: Any = None


class AsyncTaskQueue(LoggerMixin):
    """非同期タスクキュー"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, QueuedTask] = {}
        self.completed_tasks: Dict[str, QueuedTask] = {}
        self.workers: list = []
        self._shutdown = False
        
        self.logger.info(f"AsyncTaskQueue初期化: 最大同時実行数={max_concurrent_tasks}")
    
    async def start_workers(self):
        """ワーカータスクを開始"""
        if self.workers:
            self.logger.warning("ワーカーは既に開始されています")
            return
        
        self.logger.info(f"{self.max_concurrent_tasks}個のワーカーを開始")
        
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
    
    async def stop_workers(self):
        """ワーカータスクを停止"""
        self.logger.info("ワーカー停止開始")
        self._shutdown = True
        
        # 実行中のタスクを待機
        for task_id, task in self.running_tasks.items():
            self.logger.info(f"実行中タスクの完了を待機: {task_id}")
        
        # ワーカータスクをキャンセル
        for worker in self.workers:
            if not worker.done():
                worker.cancel()
        
        # すべてのワーカーの完了を待機
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        self.logger.info("ワーカー停止完了")
    
    async def add_task(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """タスクをキューに追加"""
        queued_task = QueuedTask(task_id, func, *args, **kwargs)
        
        await self.queue.put(queued_task)
        
        self.logger.info(f"タスクをキューに追加: {task_id} (キューID: {queued_task.id})")
        
        return queued_task.id
    
    async def _worker(self, worker_name: str):
        """ワーカータスク"""
        self.logger.info(f"ワーカー開始: {worker_name}")
        
        while not self._shutdown:
            try:
                # タスクを取得（タイムアウト付き）
                try:
                    queued_task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # タスクを実行
                await self._execute_task(worker_name, queued_task)
                
                # タスク完了をマーク
                self.queue.task_done()
                
            except asyncio.CancelledError:
                self.logger.info(f"ワーカーがキャンセルされました: {worker_name}")
                break
            except Exception as e:
                self.logger.error(f"ワーカーエラー {worker_name}: {str(e)}", exc_info=True)
                # ワーカーは継続
        
        self.logger.info(f"ワーカー終了: {worker_name}")
    
    async def _execute_task(self, worker_name: str, queued_task: QueuedTask):
        """タスクを実行"""
        task_id = queued_task.task_id
        queue_id = queued_task.id
        
        try:
            # 実行開始
            queued_task.status = TaskQueueStatus.RUNNING
            queued_task.started_at = datetime.now()
            self.running_tasks[queue_id] = queued_task
            
            self.logger.info(f"タスク実行開始: {task_id} (ワーカー: {worker_name})")
            
            # 関数を実行
            if asyncio.iscoroutinefunction(queued_task.func):
                result = await queued_task.func(*queued_task.args, **queued_task.kwargs)
            else:
                # 同期関数の場合は別スレッドで実行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    lambda: queued_task.func(*queued_task.args, **queued_task.kwargs)
                )
            
            # 成功
            queued_task.status = TaskQueueStatus.COMPLETED
            queued_task.completed_at = datetime.now()
            queued_task.result = result
            
            duration = (queued_task.completed_at - queued_task.started_at).total_seconds()
            self.logger.info(f"タスク実行完了: {task_id} ({duration:.2f}秒)")
            
        except Exception as e:
            # エラー
            queued_task.status = TaskQueueStatus.FAILED
            queued_task.completed_at = datetime.now()
            queued_task.error = str(e)
            
            duration = (queued_task.completed_at - queued_task.started_at).total_seconds()
            self.logger.error(f"タスク実行失敗: {task_id} ({duration:.2f}秒) - {str(e)}", exc_info=True)
        
        finally:
            # 実行中リストから削除し、完了リストに移動
            if queue_id in self.running_tasks:
                del self.running_tasks[queue_id]
            
            self.completed_tasks[queue_id] = queued_task
            
            # 完了したタスクの履歴を制限（最新100件のみ保持）
            if len(self.completed_tasks) > 100:
                oldest_tasks = sorted(self.completed_tasks.values(), key=lambda t: t.completed_at)
                for old_task in oldest_tasks[:-100]:
                    del self.completed_tasks[old_task.id]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """キューの状態を取得"""
        return {
            "queue_size": self.queue.qsize(),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "max_concurrent": self.max_concurrent_tasks,
            "workers": len(self.workers),
            "shutdown": self._shutdown
        }
    
    def get_task_status(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """特定タスクの状態を取得"""
        # 実行中のタスクを確認
        if queue_id in self.running_tasks:
            task = self.running_tasks[queue_id]
            return {
                "id": task.id,
                "task_id": task.task_id,
                "status": task.status,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "duration": (datetime.now() - task.started_at).total_seconds() if task.started_at else None
            }
        
        # 完了したタスクを確認
        if queue_id in self.completed_tasks:
            task = self.completed_tasks[queue_id]
            return {
                "id": task.id,
                "task_id": task.task_id,
                "status": task.status,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "duration": (task.completed_at - task.started_at).total_seconds() if task.started_at and task.completed_at else None,
                "error": task.error
            }
        
        return None


# グローバルタスクキューインスタンス
task_queue: Optional[AsyncTaskQueue] = None


def get_task_queue() -> AsyncTaskQueue:
    """タスクキューインスタンスを取得"""
    global task_queue
    if task_queue is None:
        from app.config import settings
        task_queue = AsyncTaskQueue(max_concurrent_tasks=settings.max_concurrent_tasks)
    return task_queue


async def initialize_task_queue():
    """タスクキューを初期化"""
    queue = get_task_queue()
    await queue.start_workers()


async def shutdown_task_queue():
    """タスクキューを停止"""
    global task_queue
    if task_queue:
        await task_queue.stop_workers()
        task_queue = None