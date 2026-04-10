"""
Coordinator Graph

LangGraph Coordinator Graph 骨架，支持条件路由。
"""
from langgraph.graph import StateGraph, END
from backend.app.agents.state import AgentState
from backend.app.agents.intent_routing.route_sequence_controller import RouteSequenceControllerNode
from backend.app.agents.intent_routing.final_response import FinalResponseNode
from backend.app.agents.perception.subgraph import create_perception_subgraph
from backend.app.domain.models import MediaSegment


def create_coordinator_graph(segments: list[MediaSegment] = None):
    """
    创建 Coordinator Graph

    Args:
        segments: 可用的媒体片段列表（用于 Perception Subgraph）

    Returns:
        编译后的 LangGraph
    """
    if segments is None:
        segments = []

    # 创建 StateGraph
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("route_sequence_controller", RouteSequenceControllerNode())
    workflow.add_node("final_response", FinalResponseNode())

    # Phase 2: 集成 Perception & Retrieval Subgraph
    perception_subgraph = create_perception_subgraph(segments)
    workflow.add_node("perception_retrieval", perception_subgraph)
    workflow.add_node("editing_planning_placeholder", lambda state: {
        'node_trace': state.get('node_trace', []) + [{'node': 'editing_planning_placeholder'}]
    })
    workflow.add_node("export_render_control_placeholder", lambda state: {
        'node_trace': state.get('node_trace', []) + [{'node': 'export_render_control_placeholder'}]
    })
    workflow.add_node("media_workflow_control_placeholder", lambda state: {
        'node_trace': state.get('node_trace', []) + [{'node': 'media_workflow_control_placeholder'}]
    })
    
    # 设置入口点
    workflow.set_entry_point("route_sequence_controller")
    
    # 添加条件边
    def route_to_next_step(state: AgentState) -> str:
        """根据 route_sequence 决定下一步"""
        route_sequence = state.get('route_sequence', [])
        current_step = state.get('current_route_step', 0)
        
        if current_step >= len(route_sequence):
            return "final_response"
        
        next_target = route_sequence[current_step]
        
        # 映射到实际节点
        node_map = {
            'perception_retrieval': 'perception_retrieval',  # Phase 2: 已集成
            'editing_planning': 'editing_planning_placeholder',
            'export_render_control': 'export_render_control_placeholder',
            'media_workflow_control': 'media_workflow_control_placeholder',
            'final_response': 'final_response'
        }
        
        return node_map.get(next_target, 'final_response')
    
    workflow.add_conditional_edges(
        "route_sequence_controller",
        route_to_next_step
    )
    
    # 占位符节点完成后继续路由
    def advance_route_step(state: AgentState) -> dict:
        """推进路由步骤"""
        current_step = state.get('current_route_step', 0)
        completed = state.get('completed_route_steps', [])
        route_sequence = state.get('route_sequence', [])
        
        if current_step < len(route_sequence):
            completed.append(route_sequence[current_step])
        
        return {
            'current_route_step': current_step + 1,
            'completed_route_steps': completed
        }
    
    # Phase 2: Perception Subgraph 完成后继续路由
    workflow.add_node("perception_retrieval_advance", advance_route_step)
    workflow.add_edge("perception_retrieval", "perception_retrieval_advance")
    workflow.add_conditional_edges(
        "perception_retrieval_advance",
        route_to_next_step
    )

    # 为其他占位符节点添加后续路由
    for placeholder in ['editing_planning_placeholder',
                        'export_render_control_placeholder', 'media_workflow_control_placeholder']:
        workflow.add_node(f"{placeholder}_advance", advance_route_step)
        workflow.add_edge(placeholder, f"{placeholder}_advance")
        workflow.add_conditional_edges(
            f"{placeholder}_advance",
            route_to_next_step
        )
    
    # final_response 结束
    workflow.add_edge("final_response", END)
    
    # 编译
    return workflow.compile()
