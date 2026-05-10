"""
测试 Media Workflow 数据模型
"""
import pytest
from backend.app.domain.media_workflow import (
    MediaWorkflowRun,
    MediaWorkflowTask,
)


def test_media_workflow_run_creation():
    """测试 MediaWorkflowRun 创建"""
    workflow = MediaWorkflowRun(
        workflow_id="workflow_001",
        user_id="user_001",
        video_id="video_001",
        status="running",
        tasks=[]
    )

    assert workflow.workflow_id == "workflow_001"
    assert workflow.user_id == "user_001"
    assert workflow.video_id == "video_001"
    assert workflow.status == "running"
    assert workflow.tasks == []


def test_media_workflow_task_creation():
    """测试 MediaWorkflowTask 创建"""
    task = MediaWorkflowTask(
        task_id="task_001",
        workflow_id="workflow_001",
        task_type="MetadataExtraction",
        status="pending",
        depends_on=[]
    )

    assert task.task_id == "task_001"
    assert task.workflow_id == "workflow_001"
    assert task.task_type == "MetadataExtraction"
    assert task.status == "pending"
    assert task.depends_on == []


def test_media_workflow_task_with_dependencies():
    """测试 MediaWorkflowTask 包含依赖关系"""
    task = MediaWorkflowTask(
        task_id="task_002",
        workflow_id="workflow_001",
        task_type="ASR",
        status="pending",
        depends_on=["task_audio_extraction"]
    )

    assert task.depends_on == ["task_audio_extraction"]


def test_media_workflow_run_with_tasks():
    """测试 MediaWorkflowRun 包含任务列表"""
    workflow = MediaWorkflowRun(
        workflow_id="workflow_002",
        user_id="user_001",
        video_id="video_001",
        status="running",
        tasks=["task_001", "task_002", "task_003"]
    )

    assert len(workflow.tasks) == 3
    assert "task_001" in workflow.tasks


def test_media_workflow_task_partial_success():
    """测试 MediaWorkflowTask 部分成功状态"""
    task = MediaWorkflowTask(
        task_id="task_003",
        workflow_id="workflow_001",
        task_type="Indexing",
        status="partially_completed",
        depends_on=["task_segment_builder", "task_text_embedding"]
    )

    assert task.status == "partially_completed"
