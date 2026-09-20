# Domain Command V2

The public mutation endpoint is `POST /api/v1/editing/sessions/{session_id}/commands`. An `EditCommandBatch` carries `base_version`, a reason, and typed commands. Supported commands cover initialization, source registration, canvas updates, track lifecycle, stable-anchor segment insertion/movement/removal, trim/split/media replacement, static transform, text/audio updates, transitions, title, and goal.

The reducer validates commands against the current `EditingProjectV2`, returns a new immutable project, validates all project invariants, and deterministically derives the internal RFC 6902 audit diff. The repository alone performs compare-and-swap persistence and appends `StateVersion`, patch, and audit rows. External clients and the agent cannot supply patch paths or complete replacement timelines. Rollback creates a compensating new version.
