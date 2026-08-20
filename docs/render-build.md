# Immutable render builds

A render job is bound to one `session_id` and one `state_version`. The worker loads that exact
version, downloads every selected source, computes a media fingerprint, compiles the timeline,
and creates an immutable execution snapshot. Rendering never reads the latest editing session.

Each job owns `runtime/jobs/<job_id>/build/` containing:

```text
compiled-timeline.json
source-manifest.json
render-profile.json
build-manifest.json
subtitles.srt             # when subtitles exist
```

`build-manifest.json` records state and compiled hashes, source-manifest and profile hashes,
renderer version, creation time, every build file's size and SHA-256, and a build hash. The
worker also uploads these files beside the rendered artifact so the output retains complete
provenance after the local job directory expires.

## Media fingerprints

Every video or audio source is identified by media ID, storage key, SHA-256, byte size,
duration in microseconds, dimensions, and stream codecs. The local path is execution-only and
does not affect the deterministic compiled hash.

Fingerprint checks run after download, during build verification, and immediately before the
renderer consumes the build. A changed byte count, hash, or probed duration is artifact drift
and terminates the job. CamCat never recompiles an existing build against changed media.

## Retry and checkpoints

The existing PostgreSQL job remains the only task state machine. Render checkpoints are:

```text
state_loaded
sources_fingerprinted
timeline_compiled
compiled_verified
build_created
build_verified
render_started
encoded
decode_verified
artifact_uploaded
```

An existing build may be reused only inside the same job and only when its manifest and
compiled hash verify. Failure categories distinguish retryable infrastructure failures from
deterministic validation, unsupported execution, artifact drift, and output verification.
Only infrastructure failures retry automatically.

## Renderer boundary

`RendererBackend` accepts a verified `RenderBuild` and output path. `FFmpegRenderer` is the
production implementation. It consumes compiled frames, transitions, audio tracks, subtitles,
and the render profile; it contains no editing-plan policy. Adding another renderer must not
change semantic state or compilation.
