"""
API 响应模型

定义 API 响应的数据结构，保持向后兼容。
"""
from typing import Any
from pydantic import BaseModel, Field


class AgenticSearchResponse(BaseModel):
    """Agentic Search API 响应"""
    # 向后兼容字段
    route_decision: str | None = None
    route_sequence: list[str] = Field(default_factory=list)
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    node_trace: list[dict[str, Any]] = Field(default_factory=list)
    quality_check: dict[str, Any] | None = None
    retry_history: list[dict[str, Any]] = Field(default_factory=list)

    # 核心响应字段
    reranked_segments: list[dict[str, Any]] = Field(default_factory=list)
    final_answer: dict[str, Any] | None = None
    status: str = "completed"  # completed, partial, failed
    error: str | None = None
