from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from camcat.rendering.build import RenderBuild


class RenderResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    output: Path
    renderer: str
    command: list[str]


class RendererBackend(Protocol):
    def render(self, build: RenderBuild, output: Path) -> RenderResult: ...
