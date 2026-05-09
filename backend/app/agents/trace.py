from collections.abc import Callable
from time import perf_counter

from backend.app.agents.state import AgentState


def trace_node(node_name: str, node: Callable[[AgentState], AgentState]) -> Callable[[AgentState], AgentState]:
    def traced(state: AgentState) -> AgentState:
        started_at = perf_counter()
        try:
            updated = node(state)
        except Exception as exc:
            state.node_trace.append(_trace_entry(node_name, "error", started_at, str(exc)))
            raise

        updated.node_trace.append(_trace_entry(node_name, "ok", started_at, None))
        return updated

    return traced


def _trace_entry(node_name: str, status: str, started_at: float, error: str | None) -> dict:
    return {
        "node_name": node_name,
        "status": status,
        "latency_ms": round((perf_counter() - started_at) * 1000, 3),
        "error": error,
    }
