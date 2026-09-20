"""Build and verify an optional local editable draft from a CamCat RenderBuild."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from camcat.rendering.build import verify_render_build
from camcat.rendering.jianying_adapter import JianyingRendererAdapter
from camcat.rendering.materialization import MaterializedMedia


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="SOURCE_ID=PATH",
        help="materialized source path; repeat once for every source in the build",
    )
    parser.add_argument(
        "--command-json",
        required=True,
        help="JSON argument vector for the separately installed local draft builder",
    )
    args = parser.parse_args()
    command = json.loads(args.command_json)
    if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
        parser.error("--command-json must be a JSON array of strings")
    build = verify_render_build(args.build)
    source_paths: dict[str, Path] = {}
    for value in args.source:
        source_id, separator, raw_path = value.partition("=")
        if not separator or not source_id or not raw_path:
            parser.error("--source must use SOURCE_ID=/absolute/path syntax")
        source_paths[source_id] = Path(raw_path).resolve(strict=True)
    refs = {item.media_id: item for item in build.timeline.source_manifest}
    if set(source_paths) != set(refs):
        parser.error("--source identities must exactly match the render build source manifest")
    sources = {
        source_id: MaterializedMedia(ref=refs[source_id], local_path=path)
        for source_id, path in source_paths.items()
    }
    result = JianyingRendererAdapter(command).build_editable_draft(
        build, sources, args.out, name=args.name
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
