from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class CapabilityError(RuntimeError):
    pass


class CapabilityProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    ffmpeg_version: str
    ffprobe_version: str
    encoders: list[str]
    filters: list[str]
    runtime_directory_writable: bool
    object_store_reachable: bool | None


def inspect_capabilities(
    runtime_directory: Path,
    *,
    object_store_healthcheck: Callable[[], None] | None = None,
) -> CapabilityProfile:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise CapabilityError("FFmpeg and FFprobe are required")
    ffmpeg_version = _first_line(["ffmpeg", "-version"])
    ffprobe_version = _first_line(["ffprobe", "-version"])
    encoders_output = _run(["ffmpeg", "-hide_banner", "-encoders"])
    filters_output = _run(["ffmpeg", "-hide_banner", "-filters"])
    required_encoders = ["libx264", "aac"]
    required_filters = ["subtitles", "xfade", "acrossfade", "eq", "loudnorm", "amix"]
    encoders = [item for item in required_encoders if item in encoders_output]
    filters = [item for item in required_filters if item in filters_output]
    missing = sorted(set(required_encoders) - set(encoders)) + sorted(
        set(required_filters) - set(filters)
    )
    if missing:
        raise CapabilityError(
            f"render backend is missing required capabilities: {', '.join(missing)}"
        )
    runtime_directory.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=runtime_directory):
            writable = True
    except OSError as exc:
        raise CapabilityError("runtime directory is not writable") from exc
    reachable: bool | None = None
    if object_store_healthcheck is not None:
        object_store_healthcheck()
        reachable = True
    return CapabilityProfile(
        ffmpeg_version=ffmpeg_version,
        ffprobe_version=ffprobe_version,
        encoders=encoders,
        filters=filters,
        runtime_directory_writable=writable,
        object_store_reachable=reachable,
    )


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise CapabilityError(f"capability command failed: {args[0]}")
    return result.stdout


def _first_line(args: list[str]) -> str:
    return _run(args).splitlines()[0]
