from langgraph.checkpoint.memory import InMemorySaver


def build_in_memory_checkpointer() -> InMemorySaver:
    return InMemorySaver()
