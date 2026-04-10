"""
测试 FinalResponseNode
"""
import pytest
from backend.app.agents.intent_routing.final_response import FinalResponseNode
from backend.app.agents.state import AgentState


def test_final_response_media_not_ready():
    """测试 media not ready 响应"""
    state = AgentState(
        readiness_status={'status': 'not_ready', 'workflow_id': 'wf_001'}
    )
    
    node = FinalResponseNode()
    result = node(state)
    
    assert result['final_answer']['status'] == 'deferred'
    assert result['final_answer']['reason_code'] == 'media_not_ready'
    assert 'workflow_id' in result['final_answer']


def test_final_response_render_job_running():
    """测试 render job running 响应"""
    state = AgentState(
        render_job={'status': 'running', 'render_job_id': 'rj_001'}
    )
    
    node = FinalResponseNode()
    result = node(state)
    
    assert result['final_answer']['status'] == 'deferred'
    assert result['final_answer']['reason_code'] == 'render_job_running'
    assert 'render_job_id' in result['final_answer']


def test_final_response_low_confidence():
    """测试 low confidence result 响应"""
    state = AgentState(
        quality_check={'passed': False, 'quality_score': 0.3}
    )
    
    node = FinalResponseNode()
    result = node(state)
    
    assert result['final_answer']['status'] == 'partial'
    assert result['final_answer']['reason_code'] == 'low_confidence'


def test_final_response_state_conflict():
    """测试 state conflict 响应"""
    state = AgentState(
        errors=[{'type': 'state_conflict', 'message': 'Version mismatch'}]
    )
    
    node = FinalResponseNode()
    result = node(state)
    
    assert result['final_answer']['status'] == 'failed'
    assert result['final_answer']['reason_code'] == 'state_conflict'


def test_final_response_invalid_argument():
    """测试 invalid argument 响应"""
    state = AgentState(
        errors=[{'type': 'invalid_argument', 'message': 'Missing required field'}]
    )
    
    node = FinalResponseNode()
    result = node(state)
    
    assert result['final_answer']['status'] == 'failed'
    assert result['final_answer']['reason_code'] == 'invalid_argument'


def test_final_response_succeeded():
    """测试成功响应"""
    state = AgentState(
        reranked_results=[{'segment_id': 'seg_001', 'score': 0.95}],
        evidence=[{'type': 'asr', 'content': 'test'}]
    )
    
    node = FinalResponseNode()
    result = node(state)
    
    assert result['final_answer']['status'] == 'succeeded'
    assert 'reranked_segments' in result['final_answer']
