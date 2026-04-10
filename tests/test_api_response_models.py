"""
测试 API 响应模型
"""
import pytest
from backend.app.api.response_models import AgenticSearchResponse


def test_agentic_search_response_creation():
    """测试 AgenticSearchResponse 创建"""
    response = AgenticSearchResponse(
        route_decision="retrieval_only",
        route_sequence=["perception_retrieval"],
        status="completed"
    )

    assert response.route_decision == "retrieval_only"
    assert response.route_sequence == ["perception_retrieval"]
    assert response.status == "completed"


def test_agentic_search_response_backward_compatible_fields():
    """测试向后兼容字段"""
    response = AgenticSearchResponse(
        route_decision="retrieval_only",
        route_sequence=["perception_retrieval"],
        node_trace=[{"node": "query_rewrite", "status": "completed"}],
        quality_check={"passed": True, "quality_score": 0.85},
        retry_history=[]
    )

    assert "node_trace" in response.model_dump()
    assert "quality_check" in response.model_dump()
    assert "retry_history" in response.model_dump()
