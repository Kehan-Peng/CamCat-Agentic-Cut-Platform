"""
CandidateEvidenceAttachNode

附加 ASR、OCR、caption、tag、score 和元数据证据到候选结果。
准备证据特征用于重排序。
"""
from backend.app.agents.state import AgentState


def candidate_evidence_attach_node(state: AgentState) -> AgentState:
    """
    附加证据到候选结果

    Args:
        state: AgentState

    Returns:
        更新后的 AgentState
    """
    retrieved_segments = state.get("retrieved_segments", [])

    # 证据已经在 MediaSegment 中，这里只是确保它们被正确传递
    # 在实际实现中，这里可能需要从不同的数据源聚合证据
    # 但在当前的简化实现中，证据已经在 segment.evidence 中

    return {
        **state,
        "retrieved_segments": retrieved_segments
    }
