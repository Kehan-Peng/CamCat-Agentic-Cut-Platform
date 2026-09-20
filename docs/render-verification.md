# Render and output verification

Build verification and output verification are separate gates. A render cannot start until the
compiled timeline, complete file manifest, render profile, source fingerprints, and provenance
hashes all verify.

`FFmpegRenderer` builds one filter graph from the compiled timeline. It performs source trim,
speed adjustment, profile-controlled scale/crop/FPS conversion, real temporal `xfade`,
ASS text-track burn-in, cue placement, fades, mixing, and encoding. Cut transitions use
concat; a dissolve is never approximated by independent fades.

## Output verifier

After encoding, `OutputVerifier` requires:

- a non-empty readable container and a video stream;
- profile width, height, and rational frame rate;
- exact equality between expected and decoded frame count;
- expected versus measured duration and the recorded delta;
- the profile-required audio stream;
- a successful full decode using FFmpeg error escalation;
- output byte size and SHA-256.

A mismatch fails the job instead of becoming a warning. Successful technical verification
returns `editorial_qc_pending`; it does not claim that the story, pacing, factual meaning, or cut
choice is editorially correct.

The validation levels are deliberately distinct:

```text
STRUCTURAL_VALID -> DECODE_VALID -> TIMELINE_VALID -> EDITORIAL_QC_PENDING
                                                   -> EDITORIAL_QC_PASSED
```

Only a later human or editorial-QC workflow may advance the final level.

## Capability inspection

Worker bootstrap runs a backend doctor before accepting work. It verifies FFmpeg and FFprobe
versions, `libx264` and `aac` encoders, `ass`, `overlay`, `xfade`, `eq`, `loudnorm`, and `amix`
filters, runtime
directory write access, and object-store reachability. Missing capabilities fail early rather
than surfacing halfway through a render.
