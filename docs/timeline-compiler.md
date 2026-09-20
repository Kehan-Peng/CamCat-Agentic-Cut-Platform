# Deterministic timeline compiler

CamCat persists semantic editing decisions in `StateVersion`. It does not persist output
timestamps or renderer filter expressions. The execution boundary is:

```text
Agent decision -> Domain edit command -> RFC 6902 State Patch -> StateVersion
              -> TimelineCompiler -> CompiledTimeline -> TimelineValidator
```

## Semantic state

Clips use stable `clip_id` values and contain source identity, source trim range, order, speed,
reason, and a `cut` or `dissolve` intent. Subtitles bind to a stable clip and source range. Audio
cues contain a stable cue identity, source identity, placement intention, level, and fade intent.
Speech workflows may attach source-bound ASR evidence and protected ranges.

The state validator rejects `output_start`, `output_end`, frame offsets, and target-bound
subtitles. Agent output never controls a final frame number or FFmpeg filter.

## Physical timeline

`TimelineCompiler` converts decimal-second input at the semantic boundary into integer
microseconds and frames. Frame duration calculations use integer rational arithmetic. The
render profile supplies the rational frame rate and the default dissolve duration; therefore
24, 25, 30, 50, 60, 30000/1001, and 60000/1001 timelines are explicit contracts rather than
renderer defaults.

The compiler emits `camcat-compiled-timeline/v1` with:

- ordered video segments with integer target frame boundaries;
- explicit transition-in and transition-out contracts;
- source-to-target projected subtitles and audio cues;
- integer `frame_count` and `duration_us`;
- a content-addressed source manifest, state hash, render-profile hash, and compiled hash.

The source manifest hash deliberately excludes the local job download path. The same state,
profile, and source fingerprints therefore compile to the same hash in different job folders.

## Projection and protection

`SourceTimeMapper` projects a source microsecond through trim, speed, reorder, and transition
placement into an output frame. A timestamp in deleted media is an error. `snap_next` and
`snap_previous` are available only when the semantic state explicitly selects one. Reusing a
source more than once requires `clip_id` to avoid ambiguous projection.

Protected source ranges are evidence-bearing spans, normally created from speech KEEP
decisions. Frame alignment may move a trim boundary only when every protected span remains
inside the compiled source interval. Compilation fails when no legal aligned cut exists.

## Invariants

Validation fails closed when any of these invariants is false:

- video boundaries contain a gap or undeclared overlap;
- an overlap is not represented by matching transition contracts on adjacent clips;
- a transition consumes an adjacent segment or lacks required source handles;
- subtitle or audio bounds leave the timeline;
- an audio fade exceeds its cue duration;
- frame count and microsecond duration disagree;
- a source-manifest or compiled-content hash differs.
