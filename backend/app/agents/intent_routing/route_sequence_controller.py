"""
RouteSequenceControllerNode

负责将复合路由展开为有序的 route_sequence，并推进执行。
"""
from typing import Dict, List
from backend.app.agents.state import AgentState


# 路由映射表
ROUTE_SEQUENCE_MAP = {
    "retrieval_only": ["perception_retrieval"],
    "editing_only": ["editing_planning"],
    "retrieval_then_editing": ["perception_retrieval", "editing_planning"],
    "media_processing_required": ["media_workflow_control"],
    "media_processing_then_retrieval": ["media_workflow_control", "perception_retrieval"],
    "media_processing_then_editing": ["media_workflow_control", "editing_planning"],
    "export_only": ["export_render_control"],
    "editing_then_export": ["editing_planning", "export_render_control"],
    "retrieval_then_editing_then_export": ["perception_retrieval", "editing_planning", "export_render_control"],
    "clarification_required": ["final_response"],
    "finalize_with_error": ["final_response"],
}


def expand_route_sequence(route_decision: str) -> List[str]:
    """
    将路由决策展开为有序的路由序列
    
    Args:
        route_decision: 路由决策（如 "retrieval_then_editing"）
        
    Returns:
        展开后的路由序列（如 ["perception_retrieval", "editing_planning"]）
    """
    return ROUTE_SEQUENCE_MAP.get(route_decision, ["final_response"])


class RouteSequenceControllerNode:
    """
    RouteSequenceControllerNode
    
    职责：
    - 将复合路由展开为有序的 route_sequence
    - 初始化 current_route_step
    - 记录 node trace
    """
    
    def __call__(self, state: AgentState) -> Dict:
        """
        执行路由序列控制
        
        Args:
            state: AgentState
            
        Returns:
            更新后的状态字段
        """
        route_decision = state.get('route_decision', 'clarification_required')
        
        # 展开路由序列
        route_sequence = expand_route_sequence(route_decision)
        
        # 初始化路由步骤
        current_route_step = 0
        completed_route_steps = state.get('completed_route_steps', [])
        
        # 记录 node trace
        node_trace = state.get('node_trace', [])
        node_trace.append({
            'node': 'RouteSequenceControllerNode',
            'route_decision': route_decision,
            'route_sequence': route_sequence,
            'current_route_step': current_route_step
        })
        
        return {
            'route_sequence': route_sequence,
            'current_route_step': current_route_step,
            'completed_route_steps': completed_route_steps,
            'node_trace': node_trace
        }
