# Editing State V2

`camcat-editing-project/v2` is CamCat's only authoritative editing state. It contains canvas geometry and rational frame rate, a logical source registry, typed video/audio/text tracks, boundary transitions, speech review evidence, and metadata.

All semantic time values are non-negative integer microseconds. Track, segment, source, transition, and evidence identities are stable strings; list positions only determine ordering. Video/audio segments reference registered sources. The first video track is continuous from zero, tracks cannot overlap, and transition endpoints must be adjacent video segments. Speech evidence binds an exact `segment_id`, `source_id`, and source range.

Existing development databases containing earlier JSON documents must be reset. Production code contains no V1 translator and responses contain no compatibility fields.
