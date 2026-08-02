from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_generator() -> ModuleType:
    path = Path(__file__).resolve().parents[4] / "scripts" / "generate_openapi_contracts.py"
    spec = importlib.util.spec_from_file_location("camcat_contract_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_check_detects_missing_and_stale_generated_files(tmp_path: Path) -> None:
    generator = _load_generator()
    generator.ROOT = tmp_path

    assert generator.main(["--check"]) == 1
    assert generator.main([]) == 0
    assert generator.main(["--check"]) == 0

    generated = tmp_path / "apps" / "web" / "src" / "generated" / "api.ts"
    generated.write_text("stale\n", encoding="utf-8")
    assert generator.main(["--check"]) == 1
