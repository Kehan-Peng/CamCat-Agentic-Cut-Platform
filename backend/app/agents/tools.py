from collections.abc import Callable
from typing import Any


class UnknownToolError(ValueError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, tool: Callable[..., Any]) -> None:
        self._tools[name] = tool

    def call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise UnknownToolError(f"unknown tool: {name}")
        return self._tools[name](*args, **kwargs)

    def has_tool(self, name: str) -> bool:
        return name in self._tools
