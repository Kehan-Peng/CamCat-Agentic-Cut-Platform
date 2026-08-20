"""Build and verify an optional local editable draft from a CamCat RenderBuild."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from camcat.rendering.build import verify_render_build
from camcat.rendering.jianying_adapter import JianyingRendererAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--command-json",
        required=True,
        help="JSON argument vector for the separately installed local draft builder",
    )
    args = parser.parse_args()
    command = json.loads(args.command_json)
    if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
        parser.error("--command-json must be a JSON array of strings")
    result = JianyingRendererAdapter(command).build_editable_draft(
        verify_render_build(args.build), args.out, name=args.name
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
