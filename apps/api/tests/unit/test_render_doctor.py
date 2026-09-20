from __future__ import annotations

from pathlib import Path

import pytest
from camcat.rendering import doctor


def test_capability_profile_requires_renderer_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(doctor, "_first_line", lambda args: f"{args[0]} version test")
    monkeypatch.setattr(
        doctor,
        "_run",
        lambda args: "libx264 aac" if "-encoders" in args else "ass overlay xfade eq loudnorm amix",
    )
    checked = False

    def healthcheck() -> None:
        nonlocal checked
        checked = True

    result = doctor.inspect_capabilities(tmp_path / "runtime", object_store_healthcheck=healthcheck)

    assert result.encoders == ["libx264", "aac"]
    assert result.filters == ["ass", "overlay", "xfade", "eq", "loudnorm", "amix"]
    assert result.runtime_directory_writable
    assert result.object_store_reachable
    assert checked


def test_missing_filter_fails_before_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(doctor, "_first_line", lambda args: "version")
    monkeypatch.setattr(doctor, "_run", lambda args: "libx264 aac")

    with pytest.raises(doctor.CapabilityError, match="ass"):
        doctor.inspect_capabilities(tmp_path)
