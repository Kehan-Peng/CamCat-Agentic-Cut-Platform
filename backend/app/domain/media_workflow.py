"""
Media Workflow 数据模型

定义媒体工作流运行和任务。
"""
from typing import Any
from pydantic import BaseModel, Field


class MediaWorkflowTask(BaseModel):
    """媒体工作流任务"""
    task_id: str
    workflow_id: str
    task_type: str  # MetadataExtraction, AudioExtraction, ASR, etc.
    status: str  # pending, running, completed, failed, partially_completed
    depends_on: list[str] = Field(default_factory=list)
    attempt: int = 0
    max_attempts: int = 3
    input_hash: str | None = None
    output_ref: str | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaWorkflowRun(BaseModel):
    """媒体工作流运行"""
    workflow_id: str
    user_id: str
    video_id: str
    status: str  # pending, running, completed, failed, partially_completed
    tasks: list[str]  # task_ids
    searchable_status: str | None = None  # fully_searchable, partially_searchable, etc.
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
