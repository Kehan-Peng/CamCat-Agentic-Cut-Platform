"""
测试 AgentState 定义
"""
import pytest
from backend.app.agents.state import AgentState


def test_agent_state_has_required_fields():
    """测试 AgentState 包含所有必需字段"""
    state = AgentState()
    
    # 基础字段
    assert 'graph_run_id' in AgentState.__annotations__
    assert 'thread_id' in AgentState.__annotations__
    assert 'user_id' in AgentState.__annotations__
    assert 'session_id' in AgentState.__annotations__
    assert 'query_text' in AgentState.__annotations__
    
    # 路由字段
    assert 'route_decision' in AgentState.__annotations__
    assert 'route_sequence' in AgentState.__annotations__
    assert 'current_route_step' in AgentState.__annotations__
    assert 'completed_route_steps' in AgentState.__annotations__
    
    # 检索字段
    assert 'rewritten_query' in AgentState.__annotations__
    assert 'retrieved_segments' in AgentState.__annotations__
    assert 'reranked_segments' in AgentState.__annotations__
    assert 'evidence' in AgentState.__annotations__
    
    # 重试预算字段
    assert 'retry_budget' in AgentState.__annotations__
    assert 'retry_history' in AgentState.__annotations__
    
    # 编辑字段
    assert 'editing_session_id' in AgentState.__annotations__
    assert 'editing_patch' in AgentState.__annotations__
    
    # 响应字段
    assert 'final_answer' in AgentState.__annotations__
    assert 'node_trace' in AgentState.__annotations__
    assert 'errors' in AgentState.__annotations__


def test_agent_state_serializable_defaults():
    """测试 AgentState 默认值可序列化"""
    state = AgentState()
    
    # 确保可以转换为字典
    state_dict = dict(state)
    assert isinstance(state_dict, dict)


def test_agent_state_route_fields():
    """测试路由相关字段"""
    state = AgentState(
        route_decision="retrieval_then_editing",
        route_sequence=["perception_retrieval", "editing_planning"],
        current_route_step=0,
        completed_route_steps=[]
    )
    
    assert state['route_decision'] == "retrieval_then_editing"
    assert state['route_sequence'] == ["perception_retrieval", "editing_planning"]
    assert state['current_route_step'] == 0
    assert state['completed_route_steps'] == []


def test_agent_state_retry_budget_fields():
    """测试重试预算字段"""
    state = AgentState(
        retry_budget={
            'max_retrieval_attempts': 3,
            'retrieval_attempt_count': 0,
            'latency_budget_ms': 5000,
            'llm_call_budget': 5
        },
        retry_history=[]
    )
    
    assert state['retry_budget']['max_retrieval_attempts'] == 3
    assert state['retry_budget']['retrieval_attempt_count'] == 0
    assert isinstance(state['retry_history'], list)


def test_agent_state_editing_patch_fields():
    """测试编辑 patch 字段"""
    state = AgentState(
        editing_session_id="edit_001",
        editing_patch={
            'patch_id': 'patch_001',
            'operations': []
        }
    )
    
    assert state['editing_session_id'] == "edit_001"
    assert state['editing_patch']['patch_id'] == 'patch_001'
