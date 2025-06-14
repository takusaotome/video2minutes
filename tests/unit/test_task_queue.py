import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.task_queue import (
    AsyncTaskQueue,
    QueuedTask,
    TaskQueueStatus,
    get_task_queue,
    initialize_task_queue,
    shutdown_task_queue,
)


class TestQueuedTask:
    """QueuedTaskクラスのテスト"""

    def test_queued_task_initialization(self):
        """QueuedTask初期化テスト"""

        def sample_func(x, y):
            return x + y

        task = QueuedTask("test-task-123", sample_func, 1, 2, key="value")

        assert task.task_id == "test-task-123"
        assert task.func == sample_func
        assert task.args == (1, 2)
        assert task.kwargs == {"key": "value"}
        assert task.status == TaskQueueStatus.PENDING
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.error is None
        assert task.result is None
        assert isinstance(task.id, str)
        assert len(task.id) > 0


class TestAsyncTaskQueue:
    """AsyncTaskQueueクラスのテスト"""

    @pytest.fixture
    def task_queue(self):
        """テスト用タスクキューインスタンス"""
        return AsyncTaskQueue(max_concurrent_tasks=2)

    def test_task_queue_initialization(self, task_queue):
        """タスクキュー初期化テスト"""
        assert task_queue.max_concurrent_tasks == 2
        assert task_queue.queue.qsize() == 0
        assert len(task_queue.running_tasks) == 0
        assert len(task_queue.completed_tasks) == 0
        assert len(task_queue.workers) == 0
        assert task_queue._shutdown == False

    @pytest.mark.asyncio
    async def test_add_task(self, task_queue):
        """タスク追加テスト"""

        def sample_func(x):
            return x * 2

        queue_id = await task_queue.add_task("test-task", sample_func, 5)

        assert isinstance(queue_id, str)
        assert len(queue_id) > 0
        assert task_queue.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_start_workers(self, task_queue):
        """ワーカー開始テスト"""
        await task_queue.start_workers()

        assert len(task_queue.workers) == 2
        for worker in task_queue.workers:
            assert isinstance(worker, asyncio.Task)

        # クリーンアップ
        await task_queue.stop_workers()

    @pytest.mark.asyncio
    async def test_stop_workers(self, task_queue):
        """ワーカー停止テスト"""
        await task_queue.start_workers()
        assert len(task_queue.workers) == 2

        await task_queue.stop_workers()

        assert len(task_queue.workers) == 0
        assert task_queue._shutdown == True

    @pytest.mark.asyncio
    async def test_execute_sync_task_success(self, task_queue):
        """同期タスク実行成功テスト"""

        def sync_task(x, y):
            return x + y

        queued_task = QueuedTask("test-sync", sync_task, 3, 4)

        await task_queue._execute_task("test-worker", queued_task)

        assert queued_task.status == TaskQueueStatus.COMPLETED
        assert queued_task.result == 7
        assert queued_task.started_at is not None
        assert queued_task.completed_at is not None
        assert queued_task.error is None

    @pytest.mark.asyncio
    async def test_execute_async_task_success(self, task_queue):
        """非同期タスク実行成功テスト"""

        async def async_task(x, y):
            await asyncio.sleep(0.01)  # 短い遅延
            return x * y

        queued_task = QueuedTask("test-async", async_task, 3, 4)

        await task_queue._execute_task("test-worker", queued_task)

        assert queued_task.status == TaskQueueStatus.COMPLETED
        assert queued_task.result == 12
        assert queued_task.started_at is not None
        assert queued_task.completed_at is not None
        assert queued_task.error is None

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, task_queue):
        """タスク実行失敗テスト"""

        def failing_task():
            raise ValueError("Test error")

        queued_task = QueuedTask("test-fail", failing_task)

        await task_queue._execute_task("test-worker", queued_task)

        assert queued_task.status == TaskQueueStatus.FAILED
        assert queued_task.result is None
        assert queued_task.error == "Test error"
        assert queued_task.started_at is not None
        assert queued_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_execute_async_task_failure(self, task_queue):
        """非同期タスク実行失敗テスト"""

        async def failing_async_task():
            await asyncio.sleep(0.01)
            raise RuntimeError("Async test error")

        queued_task = QueuedTask("test-async-fail", failing_async_task)

        await task_queue._execute_task("test-worker", queued_task)

        assert queued_task.status == TaskQueueStatus.FAILED
        assert queued_task.result is None
        assert queued_task.error == "Async test error"
        assert queued_task.started_at is not None
        assert queued_task.completed_at is not None

    def test_get_queue_status(self, task_queue):
        """キューステータス取得テスト"""
        status = task_queue.get_queue_status()

        expected_keys = [
            "queue_size",
            "running_tasks",
            "completed_tasks",
            "max_concurrent",
            "workers",
            "shutdown",
        ]

        for key in expected_keys:
            assert key in status

        assert status["queue_size"] == 0
        assert status["running_tasks"] == 0
        assert status["completed_tasks"] == 0
        assert status["max_concurrent"] == 2
        assert status["workers"] == 0
        assert status["shutdown"] == False

    def test_get_task_status_not_found(self, task_queue):
        """存在しないタスクのステータス取得テスト"""
        result = task_queue.get_task_status("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_task_status_completed(self, task_queue):
        """完了タスクのステータス取得テスト"""

        def simple_task():
            return "completed"

        queued_task = QueuedTask("test-status", simple_task)
        await task_queue._execute_task("test-worker", queued_task)

        status = task_queue.get_task_status(queued_task.id)

        assert status is not None
        assert status["id"] == queued_task.id
        assert status["task_id"] == "test-status"
        assert status["status"] == TaskQueueStatus.COMPLETED
        assert "created_at" in status
        assert "started_at" in status
        assert "completed_at" in status
        assert "duration" in status
        assert status["error"] is None

    @pytest.mark.asyncio
    async def test_completed_tasks_limit(self, task_queue):
        """完了タスク履歴制限テスト"""
        # 102個のタスクを実行（制限は100）
        for i in range(102):

            def simple_task(x):
                return x

            queued_task = QueuedTask(f"test-{i}", simple_task, i)
            await task_queue._execute_task("test-worker", queued_task)

        # 最新100件のみ保持されていることを確認
        assert len(task_queue.completed_tasks) == 100

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self, task_queue):
        """タスクの完全なライフサイクルテスト"""
        await task_queue.start_workers()

        def test_task(x, y):
            return x + y

        # タスクを追加
        queue_id = await task_queue.add_task("lifecycle-test", test_task, 10, 20)

        # タスクの完了を待機
        max_wait = 5.0  # 最大5秒待機
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_wait:
            status = task_queue.get_task_status(queue_id)
            if status and status["status"] == TaskQueueStatus.COMPLETED:
                break
            await asyncio.sleep(0.1)

        # 結果確認
        final_status = task_queue.get_task_status(queue_id)
        assert final_status is not None
        assert final_status["status"] == TaskQueueStatus.COMPLETED

        # 完了タスクから実際の結果を確認
        completed_task = task_queue.completed_tasks[queue_id]
        assert completed_task.result == 30

        await task_queue.stop_workers()


class TestGlobalTaskQueueFunctions:
    """グローバルタスクキュー関数のテスト"""

    def test_get_task_queue_singleton(self):
        """get_task_queue シングルトン動作テスト"""
        # グローバル変数をリセット
        import app.services.task_queue

        app.services.task_queue.task_queue = None

        with patch("app.config.settings") as mock_settings:
            mock_settings.max_concurrent_tasks = 5

            queue1 = get_task_queue()
            queue2 = get_task_queue()

            # 同じインスタンスが返されることを確認
            assert queue1 is queue2
            assert queue1.max_concurrent_tasks == 5

    @pytest.mark.asyncio
    async def test_initialize_task_queue(self):
        """initialize_task_queue 関数テスト"""
        # グローバル変数をリセット
        import app.services.task_queue

        app.services.task_queue.task_queue = None

        with patch("app.config.settings") as mock_settings:
            mock_settings.max_concurrent_tasks = 2

            # 初期化実行
            await initialize_task_queue()

            # タスクキューが作成され、ワーカーが開始されていることを確認
            queue = get_task_queue()
            assert len(queue.workers) == 2

            # クリーンアップ
            await shutdown_task_queue()

    @pytest.mark.asyncio
    async def test_shutdown_task_queue(self):
        """shutdown_task_queue 関数テスト"""
        # グローバル変数をリセット
        import app.services.task_queue

        app.services.task_queue.task_queue = None

        with patch("app.config.settings") as mock_settings:
            mock_settings.max_concurrent_tasks = 2

            # 初期化してワーカーを開始
            await initialize_task_queue()
            queue = get_task_queue()
            assert len(queue.workers) == 2

            # 停止実行
            await shutdown_task_queue()

            # タスクキューがNoneになることを確認
            assert app.services.task_queue.task_queue is None


class TestTaskQueueIntegration:
    """タスクキュー統合テスト"""

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self):
        """並行タスク実行テスト"""
        task_queue = AsyncTaskQueue(max_concurrent_tasks=2)
        await task_queue.start_workers()

        async def slow_task(duration, task_id):
            await asyncio.sleep(duration)
            return f"completed-{task_id}"

        # 複数のタスクを同時に追加
        queue_ids = []
        for i in range(4):
            queue_id = await task_queue.add_task(f"concurrent-{i}", slow_task, 0.1, i)
            queue_ids.append(queue_id)

        # すべてのタスクの完了を待機
        max_wait = 2.0
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_wait:
            completed_count = sum(
                1
                for qid in queue_ids
                if task_queue.get_task_status(qid)
                and task_queue.get_task_status(qid)["status"]
                == TaskQueueStatus.COMPLETED
            )
            if completed_count == 4:
                break
            await asyncio.sleep(0.05)

        # すべてのタスクが完了していることを確認
        for i, queue_id in enumerate(queue_ids):
            status = task_queue.get_task_status(queue_id)
            assert status is not None
            assert status["status"] == TaskQueueStatus.COMPLETED

            completed_task = task_queue.completed_tasks[queue_id]
            assert completed_task.result == f"completed-{i}"

        await task_queue.stop_workers()

    @pytest.mark.asyncio
    async def test_error_handling_in_workers(self):
        """ワーカーでのエラーハンドリングテスト"""
        task_queue = AsyncTaskQueue(max_concurrent_tasks=1)
        await task_queue.start_workers()

        def error_task():
            raise ValueError("Intentional error")

        def success_task():
            return "success"

        # エラータスクを追加
        error_queue_id = await task_queue.add_task("error-task", error_task)

        # 成功タスクを追加（エラー後でも動作することを確認）
        success_queue_id = await task_queue.add_task("success-task", success_task)

        # 両方のタスクの完了を待機
        max_wait = 2.0
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_wait:
            error_status = task_queue.get_task_status(error_queue_id)
            success_status = task_queue.get_task_status(success_queue_id)

            if (
                error_status
                and error_status["status"] == TaskQueueStatus.FAILED
                and success_status
                and success_status["status"] == TaskQueueStatus.COMPLETED
            ):
                break

            await asyncio.sleep(0.05)

        # エラータスクが失敗していることを確認
        error_status = task_queue.get_task_status(error_queue_id)
        assert error_status["status"] == TaskQueueStatus.FAILED
        assert "Intentional error" in error_status["error"]

        # 成功タスクが正常に完了していることを確認
        success_status = task_queue.get_task_status(success_queue_id)
        assert success_status["status"] == TaskQueueStatus.COMPLETED

        success_task_obj = task_queue.completed_tasks[success_queue_id]
        assert success_task_obj.result == "success"

        await task_queue.stop_workers()


class TestTaskQueueConfiguration:
    """タスクキュー設定テスト"""

    def test_task_queue_with_different_concurrent_limits(self):
        """異なる並行実行数でのタスクキューテスト"""
        for max_concurrent in [1, 3, 5]:
            task_queue = AsyncTaskQueue(max_concurrent_tasks=max_concurrent)

            assert task_queue.max_concurrent_tasks == max_concurrent

            status = task_queue.get_queue_status()
            assert status["max_concurrent"] == max_concurrent

    @pytest.mark.asyncio
    async def test_worker_count_matches_configuration(self):
        """ワーカー数が設定と一致することのテスト"""
        for max_concurrent in [1, 2, 4]:
            task_queue = AsyncTaskQueue(max_concurrent_tasks=max_concurrent)
            await task_queue.start_workers()

            assert len(task_queue.workers) == max_concurrent

            status = task_queue.get_queue_status()
            assert status["workers"] == max_concurrent

            await task_queue.stop_workers()


class TestTaskQueueLogging:
    """タスクキューログ機能テスト"""

    @pytest.mark.asyncio
    async def test_task_queue_logging(self):
        """タスクキューのログ出力テスト"""
        task_queue = AsyncTaskQueue(max_concurrent_tasks=1)

        # LoggerMixinが正しく動作することを確認
        assert hasattr(task_queue, "logger")
        assert task_queue.logger is not None

        # ログメソッドが存在することを確認
        assert hasattr(task_queue.logger, "info")
        assert hasattr(task_queue.logger, "error")
        assert hasattr(task_queue.logger, "warning")
        assert hasattr(task_queue.logger, "debug")

    @pytest.mark.asyncio
    async def test_task_execution_logging(self):
        """タスク実行ログのテスト"""
        task_queue = AsyncTaskQueue(max_concurrent_tasks=1)

        def test_task():
            return "logged"

        with patch.object(task_queue.logger, "info") as mock_info:
            with patch.object(task_queue.logger, "error") as mock_error:
                queued_task = QueuedTask("log-test", test_task)
                await task_queue._execute_task("test-worker", queued_task)

                # 成功ログが出力されることを確認
                assert mock_info.call_count >= 2  # 開始と完了のログ
                mock_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_task_failure_logging(self):
        """タスク失敗ログのテスト"""
        task_queue = AsyncTaskQueue(max_concurrent_tasks=1)

        def failing_task():
            raise Exception("Log test error")

        with patch.object(task_queue.logger, "info") as mock_info:
            with patch.object(task_queue.logger, "error") as mock_error:
                queued_task = QueuedTask("log-fail-test", failing_task)
                await task_queue._execute_task("test-worker", queued_task)

                # エラーログが出力されることを確認
                mock_error.assert_called_once()
                assert mock_info.call_count >= 1  # 開始ログ
