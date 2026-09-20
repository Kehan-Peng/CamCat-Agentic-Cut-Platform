# Optional local editable-draft adapter

`JianyingRendererAdapter` is an optional local backend for turning a verified CamCat
`RenderBuild` into an editable native draft package. It is intentionally outside the Docker
worker path: PostgreSQL, MinIO, and the FFmpeg production renderer do not depend on macOS or a
desktop editor installation.

The adapter keeps the same trust boundary as FFmpeg rendering:

```text
StateVersion -> CompiledTimeline -> verified RenderBuild
             -> JianyingRendererAdapter -> native plan
             -> external local builder -> verify-build -> editable draft package
```

The adapter invokes a separately installed builder through an explicit argument vector. It
runs `doctor`, `build`, and `verify-build`; it never runs publish, opens the editor, registers a
draft in the editor home screen, or exports a video. The result remains `native_ui_acceptance:
pending` until a person opens, plays, saves, and cold-reopens the draft.

## Timeline conversion

The native plan combines the persistent build with separately supplied, fingerprint-verified
runtime materializations. Machine-local paths are never persisted in the build. It uses integer
microseconds and one of the supported integer frame rates. V2 dissolve edges preserve semantic
duration and use the compiler's validated source handles.

Source-bound subtitles become editable text-track segments. BGM, ambient, and SFX cues become
audio tracks; overlapping cues are allocated to separate lanes. Explicit loop intent becomes
repeated source segments, and supported fades become editable linear volume keyframes. The
adapter rejects audio extracted from a video container, unknown subtitle style fields, trimmed
audio fades that the native keyframe contract cannot preserve, unsupported FPS, or any
unrepresentable feature. It does not silently flatten them.

## Local command

After creating a CamCat render build, run:

```bash
PYTHONPATH=apps/api python scripts/build_jianying_draft.py \
  --build /absolute/path/to/build \
  --out /absolute/path/to/new-output \
  --name "CamCat Editable" \
  --source source-id=/absolute/path/to/source.mp4 \
  --command-json '["python3","/absolute/path/to/local/headless_draft.py"]'
```

The output contains `jianying-plan.json`, the verified `native-build/`,
`verify-report.json`, and `adapter-manifest.json`. The adapter manifest binds the native files
to both the CamCat compiled-timeline hash and render-build hash.

Native UI acceptance remains future work and is not part of the V2 migration acceptance run.
