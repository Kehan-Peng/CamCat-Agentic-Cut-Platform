"""
测试 Coordinator Graph
"""
import pytest
from backend.app.agents.coordinator import create_coordinator_graph
from backend.app.agents.state import AgentState


def test_coordinator_graph_simple_retrieval_only():
    """测试简单 retrieval_only 路由"""
    graph = create_coordinator_graph()
    
    initial_state = AgentState(
        route_decision="retrieval_only",
        node_trace=[]
    )
    
    result = graph.invoke(initial_state)
    
    assert 'route_sequence' in result
    assert result['route_sequence'] == ["perception_retrieval"]
    assert 'final_answer' in result
    assert len(result.get('node_trace', [])) > 0


def test_coordinator_graph_composite_route():
    """测试复合路由序列"""
    graph = create_coordinator_graph()
    
    initial_state = AgentState(
        route_decision="retrieval_then_editing",
        node_trace=[]
    )
    
    result = graph.invoke(initial_state)
    
    assert result['route_sequence'] == ["perception_retrieval", "editing_planning"]
    assert result['current_route_step'] == 2  # 完成两步
    assert len(result['completed_route_steps']) == 2


def test_coordinator_graph_produces_node_trace():
    """测试 node_trace 生成"""
    graph = create_coordinator_graph()
    
    initial_state = AgentState(
        route_decision="export_only",
        node_trace=[]
    )
    
    result = graph.invoke(initial_state)
    
    node_trace = result.get('node_trace', [])
    assert len(node_trace) > 0
    
    # 应该包含 RouteSequenceControllerNode
    node_names = [trace['node'] for trace in node_trace]
    assert 'RouteSequenceControllerNode' in node_names


def test_coordinator_graph_three_step_composite():
    """测试三步复合路由"""
    graph = create_coordinator_graph()
    
    initial_state = AgentState(
        route_decision="retrieval_then_editing_then_export",
        node_trace=[]
    )
    
    result = graph.invoke(initial_state)
    
    assert result['route_sequence'] == ["perception_retrieval", "editing_planning", "export_render_control"]
    assert result['current_route_step'] == 3
    assert len(result['completed_route_steps']) == 3
