"""
测试 RouteSequenceControllerNode
"""
import pytest
from backend.app.agents.intent_routing.route_sequence_controller import (
    RouteSequenceControllerNode,
    expand_route_sequence
)
from backend.app.agents.state import AgentState


def test_expand_retrieval_only():
    """测试 retrieval_only 路由展开"""
    sequence = expand_route_sequence("retrieval_only")
    assert sequence == ["perception_retrieval"]


def test_expand_editing_only():
    """测试 editing_only 路由展开"""
    sequence = expand_route_sequence("editing_only")
    assert sequence == ["editing_planning"]


def test_expand_retrieval_then_editing():
    """测试 retrieval_then_editing 复合路由展开"""
    sequence = expand_route_sequence("retrieval_then_editing")
    assert sequence == ["perception_retrieval", "editing_planning"]


def test_expand_export_only():
    """测试 export_only 路由到 export_render_control"""
    sequence = expand_route_sequence("export_only")
    assert sequence == ["export_render_control"]


def test_expand_editing_then_export():
    """测试 editing_then_export 复合路由"""
    sequence = expand_route_sequence("editing_then_export")
    assert sequence == ["editing_planning", "export_render_control"]


def test_expand_retrieval_then_editing_then_export():
    """测试 retrieval_then_editing_then_export 三步复合路由"""
    sequence = expand_route_sequence("retrieval_then_editing_then_export")
    assert sequence == ["perception_retrieval", "editing_planning", "export_render_control"]


def test_expand_media_processing_required():
    """测试 media_processing_required 路由"""
    sequence = expand_route_sequence("media_processing_required")
    assert sequence == ["media_workflow_control"]


def test_expand_media_processing_then_retrieval():
    """测试 media_processing_then_retrieval 复合路由"""
    sequence = expand_route_sequence("media_processing_then_retrieval")
    assert sequence == ["media_workflow_control", "perception_retrieval"]


def test_expand_media_processing_then_editing():
    """测试 media_processing_then_editing 复合路由"""
    sequence = expand_route_sequence("media_processing_then_editing")
    assert sequence == ["media_workflow_control", "editing_planning"]


def test_expand_clarification_required():
    """测试 clarification_required 路由"""
    sequence = expand_route_sequence("clarification_required")
    assert sequence == ["final_response"]


def test_expand_finalize_with_error():
    """测试 finalize_with_error 路由"""
    sequence = expand_route_sequence("finalize_with_error")
    assert sequence == ["final_response"]


def test_route_sequence_controller_node():
    """测试 RouteSequenceControllerNode 执行"""
    state = AgentState(
        route_decision="retrieval_then_editing",
        current_route_step=None,
        completed_route_steps=[]
    )
    
    controller = RouteSequenceControllerNode()
    result = controller(state)
    
    assert result['route_sequence'] == ["perception_retrieval", "editing_planning"]
    assert result['current_route_step'] == 0
    assert 'node_trace' in result


def test_route_sequence_does_not_flatten_subgraph_boundaries():
    """测试 route_sequence 不扁平化 subgraph 边界"""
    # 复合路由应该保持为有序列表，不应该合并成单个步骤
    sequence = expand_route_sequence("retrieval_then_editing_then_export")
    
    # 应该是 3 个独立步骤
    assert len(sequence) == 3
    assert sequence[0] == "perception_retrieval"
    assert sequence[1] == "editing_planning"
    assert sequence[2] == "export_render_control"
