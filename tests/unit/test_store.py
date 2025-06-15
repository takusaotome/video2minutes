"""ストアのテスト"""
import pytest
from datetime import datetime

from app.store import tasks_store
from app.models import MinutesTask


class TestTasksStore:
    """タスクストアのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        # テスト前にストアをクリア
        tasks_store.clear()

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        # テスト後にストアをクリア
        tasks_store.clear()

    def test_tasks_store_initialization(self):
        """タスクストア初期化テスト"""
        # 初期状態では空
        assert len(tasks_store) == 0
        assert isinstance(tasks_store, dict)

    def test_tasks_store_add_task(self):
        """タスク追加テスト"""
        task = MinutesTask(
            task_id="test-task-1",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now()
        )
        
        tasks_store["test-task-1"] = task
        
        assert len(tasks_store) == 1
        assert "test-task-1" in tasks_store
        assert tasks_store["test-task-1"].task_id == "test-task-1"
        assert tasks_store["test-task-1"].video_filename == "test.mp4"

    def test_tasks_store_get_task(self):
        """タスク取得テスト"""
        task = MinutesTask(
            task_id="test-task-2",
            video_filename="test2.mp4",
            video_size=2048,
            upload_timestamp=datetime.now()
        )
        
        tasks_store["test-task-2"] = task
        retrieved_task = tasks_store.get("test-task-2")
        
        assert retrieved_task is not None
        assert retrieved_task.task_id == "test-task-2"
        assert retrieved_task.video_filename == "test2.mp4"
        assert retrieved_task.video_size == 2048

    def test_tasks_store_get_nonexistent_task(self):
        """存在しないタスク取得テスト"""
        retrieved_task = tasks_store.get("nonexistent-task")
        
        assert retrieved_task is None

    def test_tasks_store_delete_task(self):
        """タスク削除テスト"""
        task = MinutesTask(
            task_id="test-task-3",
            video_filename="test3.mp4",
            video_size=3072,
            upload_timestamp=datetime.now()
        )
        
        tasks_store["test-task-3"] = task
        assert "test-task-3" in tasks_store
        
        del tasks_store["test-task-3"]
        assert "test-task-3" not in tasks_store
        assert len(tasks_store) == 0

    def test_tasks_store_multiple_tasks(self):
        """複数タスク管理テスト"""
        task1 = MinutesTask(
            task_id="task-1",
            video_filename="video1.mp4",
            video_size=1024,
            upload_timestamp=datetime.now()
        )
        
        task2 = MinutesTask(
            task_id="task-2",
            video_filename="video2.mp4",
            video_size=2048,
            upload_timestamp=datetime.now()
        )
        
        task3 = MinutesTask(
            task_id="task-3",
            video_filename="video3.mp4",
            video_size=3072,
            upload_timestamp=datetime.now()
        )
        
        tasks_store["task-1"] = task1
        tasks_store["task-2"] = task2
        tasks_store["task-3"] = task3
        
        assert len(tasks_store) == 3
        assert all(task_id in tasks_store for task_id in ["task-1", "task-2", "task-3"])
        
        # 各タスクの取得テスト
        assert tasks_store["task-1"].video_filename == "video1.mp4"
        assert tasks_store["task-2"].video_filename == "video2.mp4"
        assert tasks_store["task-3"].video_filename == "video3.mp4"

    def test_tasks_store_update_task(self):
        """タスク更新テスト"""
        task = MinutesTask(
            task_id="update-task",
            video_filename="original.mp4",
            video_size=1024,
            upload_timestamp=datetime.now()
        )
        
        tasks_store["update-task"] = task
        
        # ステータス更新
        updated_task = tasks_store["update-task"]
        updated_task.status = "processing"
        tasks_store["update-task"] = updated_task
        
        assert tasks_store["update-task"].status == "processing"

    def test_tasks_store_clear(self):
        """ストアクリアテスト"""
        # 複数のタスクを追加
        for i in range(5):
            task = MinutesTask(
                task_id=f"clear-task-{i}",
                video_filename=f"video{i}.mp4",
                video_size=1024 * (i + 1),
                upload_timestamp=datetime.now()
            )
            tasks_store[f"clear-task-{i}"] = task
        
        assert len(tasks_store) == 5
        
        # ストアをクリア
        tasks_store.clear()
        
        assert len(tasks_store) == 0
        assert not tasks_store

    def test_tasks_store_keys(self):
        """ストアキー取得テスト"""
        task_ids = ["key-test-1", "key-test-2", "key-test-3"]
        
        for task_id in task_ids:
            task = MinutesTask(
                task_id=task_id,
                video_filename=f"{task_id}.mp4",
                video_size=1024,
                upload_timestamp=datetime.now()
            )
            tasks_store[task_id] = task
        
        store_keys = list(tasks_store.keys())
        
        assert len(store_keys) == 3
        assert all(task_id in store_keys for task_id in task_ids)

    def test_tasks_store_values(self):
        """ストア値取得テスト"""
        task_ids = ["value-test-1", "value-test-2"]
        
        for task_id in task_ids:
            task = MinutesTask(
                task_id=task_id,
                video_filename=f"{task_id}.mp4",
                video_size=1024,
                upload_timestamp=datetime.now()
            )
            tasks_store[task_id] = task
        
        store_values = list(tasks_store.values())
        
        assert len(store_values) == 2
        assert all(isinstance(task, MinutesTask) for task in store_values)
        assert all(task.task_id in task_ids for task in store_values)

    def test_tasks_store_items(self):
        """ストアアイテム取得テスト"""
        task_id = "items-test"
        task = MinutesTask(
            task_id=task_id,
            video_filename="items-test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now()
        )
        
        tasks_store[task_id] = task
        
        store_items = list(tasks_store.items())
        
        assert len(store_items) == 1
        assert store_items[0][0] == task_id
        assert store_items[0][1] == task
        assert isinstance(store_items[0][1], MinutesTask)

    def test_tasks_store_len(self):
        """ストア長さテスト"""
        assert len(tasks_store) == 0
        
        # タスクを順次追加
        for i in range(10):
            task = MinutesTask(
                task_id=f"len-test-{i}",
                video_filename=f"len-test-{i}.mp4",
                video_size=1024,
                upload_timestamp=datetime.now()
            )
            tasks_store[f"len-test-{i}"] = task
            assert len(tasks_store) == i + 1

    def test_tasks_store_bool(self):
        """ストア真偽値テスト"""
        # 空の場合はFalse
        assert not tasks_store
        
        # タスクがある場合はTrue
        task = MinutesTask(
            task_id="bool-test",
            video_filename="bool-test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now()
        )
        tasks_store["bool-test"] = task
        
        assert tasks_store

    def test_tasks_store_pop(self):
        """ストアpopテスト"""
        task = MinutesTask(
            task_id="pop-test",
            video_filename="pop-test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now()
        )
        
        tasks_store["pop-test"] = task
        assert len(tasks_store) == 1
        
        popped_task = tasks_store.pop("pop-test")
        
        assert popped_task.task_id == "pop-test"
        assert len(tasks_store) == 0
        assert "pop-test" not in tasks_store

    def test_tasks_store_pop_default(self):
        """ストアpopデフォルト値テスト"""
        default_value = "default"
        
        result = tasks_store.pop("nonexistent", default_value)
        
        assert result == default_value

    def test_tasks_store_setdefault(self):
        """ストアsetdefaultテスト"""
        task = MinutesTask(
            task_id="setdefault-test",
            video_filename="setdefault-test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now()
        )
        
        # 存在しないキーに対してsetdefault
        result = tasks_store.setdefault("setdefault-test", task)
        
        assert result == task
        assert "setdefault-test" in tasks_store
        assert tasks_store["setdefault-test"] == task
        
        # 既存のキーに対してsetdefault
        another_task = MinutesTask(
            task_id="another-task",
            video_filename="another.mp4",
            video_size=2048,
            upload_timestamp=datetime.now()
        )
        
        result = tasks_store.setdefault("setdefault-test", another_task)
        
        # 既存の値が返される
        assert result == task
        assert tasks_store["setdefault-test"] == task

    def test_tasks_store_concurrent_access_simulation(self):
        """同時アクセスシミュレーションテスト"""
        import threading
        import time
        
        results = []
        
        def add_task(task_id):
            task = MinutesTask(
                task_id=task_id,
                video_filename=f"{task_id}.mp4",
                video_size=1024,
                upload_timestamp=datetime.now()
            )
            tasks_store[task_id] = task
            results.append(task_id)
        
        # 複数スレッドでタスク追加
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_task, args=(f"concurrent-{i}",))
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 結果確認
        assert len(results) == 5
        assert len(tasks_store) == 5
        assert all(f"concurrent-{i}" in tasks_store for i in range(5))