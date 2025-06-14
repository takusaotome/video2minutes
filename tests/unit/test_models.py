from datetime import datetime

import pytest

from app.models import (
    ErrorResponse,
    MinutesTask,
    ProcessingStep,
    ProcessingStepName,
    ProcessingStepStatus,
    TaskListResponse,
    TaskResultResponse,
    TaskStatus,
    TaskStatusResponse,
    UploadResponse,
    WebSocketMessage,
)


class TestEnums:
    """Enumクラステスト"""

    def test_task_status_values(self):
        """TaskStatusの値テスト"""
        assert TaskStatus.QUEUED == "queued"
        assert TaskStatus.PROCESSING == "processing"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"

    def test_processing_step_status_values(self):
        """ProcessingStepStatusの値テスト"""
        assert ProcessingStepStatus.PENDING == "pending"
        assert ProcessingStepStatus.PROCESSING == "processing"
        assert ProcessingStepStatus.COMPLETED == "completed"
        assert ProcessingStepStatus.FAILED == "failed"

    def test_processing_step_name_values(self):
        """ProcessingStepNameの値テスト"""
        assert ProcessingStepName.UPLOAD == "upload"
        assert ProcessingStepName.AUDIO_EXTRACTION == "audio_extraction"
        assert ProcessingStepName.TRANSCRIPTION == "transcription"
        assert ProcessingStepName.MINUTES_GENERATION == "minutes_generation"


class TestProcessingStep:
    """ProcessingStepクラステスト"""

    def test_processing_step_initialization(self):
        """ProcessingStep初期化テスト"""
        step = ProcessingStep(name=ProcessingStepName.UPLOAD)

        assert step.name == ProcessingStepName.UPLOAD
        assert step.status == ProcessingStepStatus.PENDING
        assert step.progress == 0
        assert step.started_at is None
        assert step.completed_at is None
        assert step.error_message is None

    def test_processing_step_with_values(self):
        """ProcessingStep値設定テスト"""
        now = datetime.now()
        step = ProcessingStep(
            name=ProcessingStepName.TRANSCRIPTION,
            status=ProcessingStepStatus.PROCESSING,
            progress=50,
            started_at=now,
            error_message="テストエラー",
        )

        assert step.name == ProcessingStepName.TRANSCRIPTION
        assert step.status == ProcessingStepStatus.PROCESSING
        assert step.progress == 50
        assert step.started_at == now
        assert step.error_message == "テストエラー"

    def test_processing_step_progress_validation(self):
        """ProcessingStep進捗値バリデーションテスト"""
        # 正常範囲
        step = ProcessingStep(name=ProcessingStepName.UPLOAD, progress=0)
        assert step.progress == 0

        step = ProcessingStep(name=ProcessingStepName.UPLOAD, progress=100)
        assert step.progress == 100

        # 範囲外の値でエラーになることを確認
        with pytest.raises(ValueError):
            ProcessingStep(name=ProcessingStepName.UPLOAD, progress=-1)

        with pytest.raises(ValueError):
            ProcessingStep(name=ProcessingStepName.UPLOAD, progress=101)


class TestMinutesTask:
    """MinutesTaskクラステスト"""

    def test_minutes_task_initialization(self):
        """MinutesTask初期化テスト"""
        now = datetime.now()
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=now,
        )

        assert task.task_id == "test-123"
        assert task.status == TaskStatus.QUEUED
        assert task.video_filename == "test.mp4"
        assert task.video_size == 1024
        assert task.upload_timestamp == now
        assert task.current_step is None
        assert task.overall_progress == 0
        assert len(task.steps) == 4
        assert task.transcription is None
        assert task.minutes is None
        assert task.error_message is None

    def test_minutes_task_default_steps(self):
        """MinutesTaskデフォルトステップテスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        expected_steps = [
            ProcessingStepName.UPLOAD,
            ProcessingStepName.AUDIO_EXTRACTION,
            ProcessingStepName.TRANSCRIPTION,
            ProcessingStepName.MINUTES_GENERATION,
        ]

        assert len(task.steps) == 4
        for i, expected_name in enumerate(expected_steps):
            assert task.steps[i].name == expected_name
            assert task.steps[i].status == ProcessingStepStatus.PENDING

    def test_get_current_step_none(self):
        """get_current_step - 実行中ステップなしテスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        current_step = task.get_current_step()
        assert current_step is None

    def test_get_current_step_found(self):
        """get_current_step - 実行中ステップありテスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        # 1つのステップを処理中に設定
        task.steps[1].status = ProcessingStepStatus.PROCESSING

        current_step = task.get_current_step()
        assert current_step is not None
        assert current_step.name == ProcessingStepName.AUDIO_EXTRACTION
        assert current_step.status == ProcessingStepStatus.PROCESSING

    def test_update_step_status_processing(self):
        """update_step_status - 処理中設定テスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        # アップロードステップを処理中に設定
        task.update_step_status(
            ProcessingStepName.UPLOAD, ProcessingStepStatus.PROCESSING
        )

        upload_step = task.steps[0]
        assert upload_step.status == ProcessingStepStatus.PROCESSING
        assert upload_step.started_at is not None
        assert task.current_step == ProcessingStepName.UPLOAD

    def test_update_step_status_completed(self):
        """update_step_status - 完了設定テスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        # アップロードステップを完了に設定
        task.update_step_status(
            ProcessingStepName.UPLOAD, ProcessingStepStatus.COMPLETED, 100
        )

        upload_step = task.steps[0]
        assert upload_step.status == ProcessingStepStatus.COMPLETED
        assert upload_step.progress == 100
        assert upload_step.completed_at is not None

    def test_update_step_status_failed(self):
        """update_step_status - 失敗設定テスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        error_msg = "テストエラー"
        task.update_step_status(
            ProcessingStepName.UPLOAD,
            ProcessingStepStatus.FAILED,
            error_message=error_msg,
        )

        upload_step = task.steps[0]
        assert upload_step.status == ProcessingStepStatus.FAILED
        assert upload_step.error_message == error_msg
        assert upload_step.completed_at is not None
        assert task.status == TaskStatus.FAILED
        assert task.error_message == error_msg

    def test_update_overall_progress(self):
        """全体進捗更新テスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        # 各ステップを段階的に完了
        task.update_step_status(
            ProcessingStepName.UPLOAD, ProcessingStepStatus.COMPLETED, 100
        )
        assert task.overall_progress == 25  # 100/4 = 25

        task.update_step_status(
            ProcessingStepName.AUDIO_EXTRACTION, ProcessingStepStatus.COMPLETED, 100
        )
        assert task.overall_progress == 50  # 200/4 = 50

        task.update_step_status(
            ProcessingStepName.TRANSCRIPTION, ProcessingStepStatus.COMPLETED, 100
        )
        assert task.overall_progress == 75  # 300/4 = 75

        task.update_step_status(
            ProcessingStepName.MINUTES_GENERATION, ProcessingStepStatus.COMPLETED, 100
        )
        assert task.overall_progress == 100  # 400/4 = 100
        assert task.status == TaskStatus.COMPLETED
        assert task.current_step is None

    def test_partial_progress_calculation(self):
        """部分進捗計算テスト"""
        task = MinutesTask(
            task_id="test-123",
            video_filename="test.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )

        # 部分的な進捗
        task.update_step_status(
            ProcessingStepName.UPLOAD, ProcessingStepStatus.COMPLETED, 100
        )
        task.update_step_status(
            ProcessingStepName.AUDIO_EXTRACTION, ProcessingStepStatus.PROCESSING, 50
        )

        # (100 + 50 + 0 + 0) / 4 = 37.5 -> 37
        assert task.overall_progress == 37


class TestResponseModels:
    """レスポンスモデルテスト"""

    def test_upload_response(self):
        """UploadResponseテスト"""
        response = UploadResponse(task_id="test-123", status=TaskStatus.QUEUED)

        assert response.task_id == "test-123"
        assert response.status == TaskStatus.QUEUED
        assert (
            response.message
            == "ファイルのアップロードが完了しました。処理を開始します。"
        )

    def test_upload_response_custom_message(self):
        """UploadResponse カスタムメッセージテスト"""
        custom_message = "カスタムメッセージ"
        response = UploadResponse(
            task_id="test-123", status=TaskStatus.QUEUED, message=custom_message
        )

        assert response.message == custom_message

    def test_task_list_response(self):
        """TaskListResponseテスト"""
        task1 = MinutesTask(
            task_id="test-1",
            video_filename="test1.mp4",
            video_size=1024,
            upload_timestamp=datetime.now(),
        )
        task2 = MinutesTask(
            task_id="test-2",
            video_filename="test2.mp4",
            video_size=2048,
            upload_timestamp=datetime.now(),
        )

        response = TaskListResponse(tasks=[task1, task2])

        assert len(response.tasks) == 2
        assert response.tasks[0].task_id == "test-1"
        assert response.tasks[1].task_id == "test-2"

    def test_task_status_response(self):
        """TaskStatusResponseテスト"""
        now = datetime.now()
        response = TaskStatusResponse(
            task_id="test-123",
            status=TaskStatus.PROCESSING,
            current_step=ProcessingStepName.TRANSCRIPTION,
            overall_progress=50,
            steps=[ProcessingStep(name=ProcessingStepName.UPLOAD)],
            video_filename="test.mp4",
            upload_timestamp=now,
        )

        assert response.task_id == "test-123"
        assert response.status == TaskStatus.PROCESSING
        assert response.current_step == ProcessingStepName.TRANSCRIPTION
        assert response.overall_progress == 50
        assert len(response.steps) == 1
        assert response.video_filename == "test.mp4"
        assert response.upload_timestamp == now
        assert response.error_message is None

    def test_task_result_response(self):
        """TaskResultResponseテスト"""
        now = datetime.now()
        response = TaskResultResponse(
            task_id="test-123",
            video_filename="test.mp4",
            transcription="文字起こし結果",
            minutes="議事録結果",
            upload_timestamp=now,
        )

        assert response.task_id == "test-123"
        assert response.video_filename == "test.mp4"
        assert response.transcription == "文字起こし結果"
        assert response.minutes == "議事録結果"
        assert response.upload_timestamp == now

    def test_websocket_message(self):
        """WebSocketMessageテスト"""
        message = WebSocketMessage(
            type="progress_update",
            task_id="test-123",
            data={"progress": 50, "step": "transcription"},
        )

        assert message.type == "progress_update"
        assert message.task_id == "test-123"
        assert message.data["progress"] == 50
        assert message.data["step"] == "transcription"

    def test_error_response(self):
        """ErrorResponseテスト"""
        response = ErrorResponse(error="ValidationError", message="入力が無効です")

        assert response.error == "ValidationError"
        assert response.message == "入力が無効です"
        assert response.task_id is None

    def test_error_response_with_task_id(self):
        """ErrorResponse タスクID付きテスト"""
        response = ErrorResponse(
            error="ProcessingError",
            message="処理中にエラーが発生しました",
            task_id="test-123",
        )

        assert response.error == "ProcessingError"
        assert response.message == "処理中にエラーが発生しました"
        assert response.task_id == "test-123"
