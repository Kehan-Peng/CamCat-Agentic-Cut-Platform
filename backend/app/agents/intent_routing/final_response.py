"""
FinalResponseNode

负责标准化最终响应，支持 5 种响应状态。
"""
from typing import Dict
from backend.app.agents.state import AgentState


class FinalResponseNode:
    """
    FinalResponseNode
    
    职责：
    - 标准化成功、部分、延迟、失败、需要澄清的响应
    - 聚合用户可见结果
    - 保留向后兼容的 API 字段
    - 报告工作流状态
    - 返回下一步可操作步骤
    """
    
    def __call__(self, state: AgentState) -> Dict:
        """
        生成最终响应
        
        Args:
            state: AgentState
            
        Returns:
            包含 final_answer 的字典
        """
        # 检查错误
        errors = state.get('errors', [])
        if errors:
            return self._handle_error_response(state, errors)
        
        # 检查媒体就绪状态
        readiness_status = state.get('readiness_status', {})
        if readiness_status.get('status') == 'not_ready':
            return self._handle_media_not_ready(state, readiness_status)
        
        # 检查渲染作业状态
        render_job = state.get('render_job', {})
        if render_job.get('status') == 'running':
            return self._handle_render_job_running(state, render_job)
        
        # 检查质量
        quality_check = state.get('quality_check', {})
        if quality_check and not quality_check.get('passed', True):
            return self._handle_low_confidence(state, quality_check)
        
        # 成功响应
        return self._handle_success(state)
    
    def _handle_error_response(self, state: AgentState, errors: list) -> Dict:
        """处理错误响应"""
        error = errors[0]
        error_type = error.get('type', 'unknown_error')
        
        return {
            'final_answer': {
                'status': 'failed',
                'reason_code': error_type,
                'message': error.get('message', 'An error occurred'),
                'errors': errors
            }
        }
    
    def _handle_media_not_ready(self, state: AgentState, readiness_status: dict) -> Dict:
        """处理媒体未就绪响应"""
        return {
            'final_answer': {
                'status': 'deferred',
                'reason_code': 'media_not_ready',
                'message': '媒体正在处理中，请稍后重试',
                'workflow_id': readiness_status.get('workflow_id'),
                'workflow_status': readiness_status.get('workflow_status'),
                'next_actions': ['poll_workflow_status']
            }
        }
    
    def _handle_render_job_running(self, state: AgentState, render_job: dict) -> Dict:
        """处理渲染作业运行中响应"""
        return {
            'final_answer': {
                'status': 'deferred',
                'reason_code': 'render_job_running',
                'message': '视频正在渲染中，请稍后查询结果',
                'render_job_id': render_job.get('render_job_id'),
                'render_status': render_job.get('status'),
                'next_actions': ['poll_render_status']
            }
        }
    
    def _handle_low_confidence(self, state: AgentState, quality_check: dict) -> Dict:
        """处理低置信度响应"""
        return {
            'final_answer': {
                'status': 'partial',
                'reason_code': 'low_confidence',
                'message': '检索结果质量较低，建议调整查询或过滤条件',
                'quality_score': quality_check.get('quality_score'),
                'issues': quality_check.get('issues', []),
                'retrieved_segments': state.get('reranked_results', []),
                'next_actions': ['refine_query', 'adjust_filters']
            }
        }
    
    def _handle_success(self, state: AgentState) -> Dict:
        """处理成功响应"""
        return {
            'final_answer': {
                'status': 'succeeded',
                'reranked_segments': state.get('reranked_results', []),
                'evidence': state.get('evidence', []),
                'creative_suggestions': state.get('creative_suggestions', []),
                'rewritten_query': state.get('rewritten_query'),
            }
        }
