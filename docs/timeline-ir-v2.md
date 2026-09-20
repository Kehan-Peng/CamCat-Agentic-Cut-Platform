# Timeline IR V2

`TimelineCompilerV2` consumes `EditingProjectV2` directly and emits `camcat-compiled-timeline/v2`. One centralized rational conversion maps semantic microseconds to integer frames at 24, 25, 30, 30000/1001, 50, 60, or 60000/1001 fps.

The IR retains typed video, audio, and text tracks, stable occurrence identity, explicit transition edges, a persistent source manifest, and state/profile/source/compiled hashes. Dissolves preserve semantic duration: visible ranges remain unchanged while render ranges acquire validated source handles. Missing handles fail closed.

Persistent builds contain no machine-local paths. Runtime `MaterializedMedia` binds a `BuildMediaRef` to a local path only for execution. `build_input_digest` identifies logical inputs and renderer capabilities; `build_instance_hash` identifies a concrete build. The FFmpeg backend requires exact frame equality and preserves failed-job evidence for TTL cleanup.
