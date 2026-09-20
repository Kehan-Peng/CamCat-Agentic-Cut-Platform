from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from camcat.timeline.schemas import BuildMediaRef


class MaterializedMedia(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    ref: BuildMediaRef
    local_path: Path


MaterializedSources = dict[str, MaterializedMedia]
