# CamCat Engineering Contract

This file is the repository-wide source of truth for every human or AI contributor. Read it before changing code. More specific `AGENTS.md` files may add constraints but may not weaken this contract.

## Product Goal

CamCat is a multimodal intelligent video-editing multi-agent harness. A user uploads one or more raw source videos, describes a publishing goal, asks for an edit over multiple turns, reviews the evidence and timeline, and renders a real social-ready video with subtitles.

The completed local product must run through Docker Compose and cover this real path:

`transient user upload -> shot/quality analysis (no asset/vector persistence) + licensed library import -> direct multimodal embedding -> Milvus indexing -> supplemental retrieval/reranking -> LangGraph editing workflow -> versioned state patch -> subtitle/audio plan -> FFmpeg render -> browser playback/download`

## Non-negotiable Requirements

1. Preserve the visual design of the existing `nova-front/frontend` workspace. Only change the product name, logo, sample copy/data, and wire its controls to CamCat behavior. Do not redesign it.
2. Use Qwen3-VL-Embedding-8B with its MRL output fixed to 2048 dimensions as the canonical embedding model. Text, images, and video must be sent to the same multimodal encoder and stored in one semantic space. Do not replace visual input with caption-only embedding or average unrelated per-modality models.
3. Milvus is the production vector store. Search must combine at least dense multimodal retrieval, sparse/lexical retrieval, and scalar/tag/event filtering; deduplicate by segment ID, fuse routes, apply deterministic business scoring, then use a real reranker for the final candidates.
4. Use LangGraph to model separate nodes for requirement understanding, query planning, material retrieval, edit-plan generation, subtitle generation, validation, and persistence. State must be explicit and serializable.
5. Multi-turn editing must use optimistic locking and State Patch. Every mutation carries `base_version`; success atomically writes a new version plus an auditable patch, conflict returns HTTP 409 with the current version/diff, and rollback creates a new compensating version rather than deleting history.
6. External integrations may not be replaced by stubs, mock servers, random vectors, fake success responses, or hard-coded model outputs in production, integration, contract, or E2E paths. Unit tests may test pure functions in isolation, but they must not be presented as external-service verification.
7. Missing credentials must fail fast with a useful configuration error. Never silently fall back to a fake provider. Secrets live only in ignored `.env` files; commit `.env.example` with names and documentation only.
8. Rendering must invoke real FFmpeg/ffprobe. Generated subtitles must be real SRT/ASS artifacts included in the final render. Object storage and signed playback URLs must be real.
9. Only ingest media with a recorded source URL and license. Prefer short, openly licensed clips and trim long sources during ingestion. Do not commit downloaded binary media to Git.
10. The application is not complete until frontend and backend pass a browser E2E against the real Docker Compose stack and configured providers.
11. User-uploaded originals are transient job inputs retained for four hours. They must never become `Asset`/`Segment` library records or Milvus entities. Only licensed external library media is indexed for long-term retrieval.
12. User footage is always the primary story. External video defaults to at most 25% of the final duration unless the user explicitly asks otherwise. Output ratio is selected from 16:9, 9:16, 3:4, 4:3, or 1:1 using source shape and intent.
13. Every edit automatically applies shot deduplication, quality scoring, rhythm reordering, subtitles, transitions, loudness normalization, basic grading, and platform safe-area adaptation. Agent node progress must stream to the UI while retaining polling as recovery truth.

## Reference Decisions

The retrieval design follows the two project references supplied by the owner:

- `https://my.feishu.cn/wiki/GBUEwg6Q6iA1u8krAAKcp9FZnEf`
- `https://my.feishu.cn/wiki/TvhkweJgCiY5kgkpTAycH6o1nDe`

Apply their core decisions:

- Segment with fixed windows plus visual scene cuts; preserve 3–5 seconds of event context and avoid unfocused long clips.
- Store segment identity, source/time range, trigger/event type, tags, duration, structured metadata, license/source information, and the 2048-dimensional embedding.
- Run recall routes concurrently, union and deduplicate candidates, then fuse scores.
- Deterministic scoring begins from semantic similarity and can include risk/relevance, freshness, and compactness; keep weights configurable and test them.
- Rerank only the bounded candidate set with a real query-document or multimodal reranking service.

## Target Repository Layout

Keep the project understandable as a small monorepo:

```text
apps/
  api/          FastAPI application, domain services, LangGraph, workers
  web/          React/Vite/TypeScript app derived from nova-front/frontend
packages/
  contracts/    generated/shared API schema and frontend types when needed
tests/
  integration/  real Postgres, Milvus, MinIO, model-provider and FFmpeg checks
  e2e/          Playwright full browser journeys
infra/          compose/service configuration and bootstrap scripts
docs/           architecture, API, operations, licenses and ADRs
```

`nova-front/` and `nova界面设计/` are design sources. Do not destructively alter them; build the production web app in `apps/web` from the TypeScript reference implementation.

## Architecture Boundaries

### Backend

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2/Alembic, LangGraph, pytest.
- PostgreSQL is authoritative for assets, projects, edit sessions, state versions, patches, render jobs, and audit events.
- Milvus stores retrieval vectors and searchable scalar metadata. Database and Milvus IDs must be stable UUIDs; ingestion must be idempotent.
- MinIO/S3 stores original media, thumbnails, extracted clips, subtitles, and rendered artifacts.
- Long ingestion/render work executes through a real worker/queue path and exposes observable job state; API handlers must not pretend asynchronous work completed.
- All provider calls have typed clients, explicit timeouts, bounded retry for transient failures, correlation IDs, and structured errors. No fallback provider is implicit.
- Validate uploaded type/size and FFprobe metadata. Treat filenames and model output as untrusted input.

### Retrieval

- Persist a single canonical `multimodal_embedding` generated by Qwen3-VL-Embedding-8B visual input for each segment.
- Text query: direct text embedding. Image query: direct image embedding. Optional mixed query: direct combined multimodal request when provider supports it.
- Dense Milvus ANN, sparse/lexical recall, and scalar-filter recall run as independent named routes with traceable scores.
- Fuse using configurable weighted RRF or equivalent deterministic fusion; retain per-route rank/score provenance.
- Apply business scoring before a real reranker. Return both final rank and an explanation/provenance object to the UI.
- Indexing and querying must assert dimension/model/version compatibility; never mix embeddings from different models in one collection unnoticed.

### Agent Workflow

- Define a typed `CamCatState`; do not pass opaque dictionaries between nodes.
- Nodes are small, independently testable, and side effects are behind explicit service interfaces.
- Persist run ID, thread/session ID, node start/end/error, input/output hashes, provider usage, and artifacts.
- Human edits and agent edits both produce RFC 6902-style patches plus domain metadata.
- Patch application must validate allowed paths and invariants (nonnegative timecodes, source bounds, no invalid clip duration, ordered output timeline).
- Never overwrite a newer state. Use a database compare-and-swap update inside one transaction.

### Frontend

- React, Vite, TypeScript and Tailwind; retain Nova layout, sizing, colors, typography, panels, and interaction model.
- Rename all user-visible Nova branding to CamCat and replace the logo with a CamCat mark without changing the surrounding design system.
- Replace static seed behavior with typed API data for library, ingestion, search evidence, graph trace, plans, subtitles, versions/conflicts, render progress, playback, and export.
- Show actionable loading, empty, error, reconnect, conflict, and rollback states. Do not display fake completed steps while work is pending.
- Preserve accessibility: labeled controls, keyboard navigation, visible focus, semantic status/live regions, and sufficient contrast.

## API and State Semantics

- API prefix: `/api/v1`; publish OpenAPI and keep frontend types aligned.
- Mutating session endpoints require `base_version` in the JSON body or `If-Match` with an explicit version contract.
- Conflict response is HTTP 409 and includes `expected_version`, `current_version`, and enough patch metadata for the UI to refresh or rebase.
- Job endpoints expose `queued|running|succeeded|failed|cancelled`, timestamps, progress, and error details.
- Server-sent events or WebSocket updates may accelerate UI updates, but a polling endpoint must remain the recoverable source of truth.
- List endpoints are paginated and deterministically ordered.
- Errors use one envelope with `code`, `message`, `details`, and `request_id`.

## TDD Workflow (Mandatory)

Every behavior change follows red-green-refactor and leaves evidence in tests:

1. Write the smallest failing test that expresses the intended behavior or contract.
2. Run it and confirm it fails for the expected reason. A test that starts green does not prove the change.
3. Add the minimum implementation to make it pass.
4. Run the focused test, then the relevant suite.
5. Refactor only while green.
6. For an external integration, add a real integration/contract test against the configured service. Never satisfy it with a stub.
7. For a user journey, add or update Playwright E2E and run it against Docker Compose.

Required test layers:

- Unit: patch validation/application, version conflict rules, segmentation/fusion/scoring, timeline invariants, schemas and pure node routing.
- Backend API: request validation, persistence, 409 conflicts, rollback history, job transitions and error envelopes.
- Real integration: Postgres migrations/transactions, Milvus indexing/search, Qwen multimodal embeddings for text+image+video, reranker, object storage, and FFmpeg render/probe.
- Frontend component/API: loading/error/conflict/progress mapping and accessibility-critical interactions.
- Browser E2E: import a real short clip, wait for indexing, search by text, search by image, create and incrementally revise a plan, deliberately cause a version conflict, rollback, generate subtitles, render, play, and download the output.

Tests that require paid/provider credentials must be clearly marked `external` but remain first-class. They may be skipped only when the required environment variables are absent, with an explicit reason; the final acceptance run requires them and reports their results separately.

## Verification Gates

Before declaring work complete, run and report:

- formatting, lint, static typing, unit tests and builds for backend and frontend;
- clean database migration up and down/up verification where safe;
- real service health and integration tests;
- Playwright E2E against a freshly built Compose stack;
- FFprobe validation of the rendered media (duration, streams, codec and subtitle/burn-in expectation);
- a check that no secret, downloaded source media, generated artifact, cache, `node_modules`, or virtual environment is tracked;
- Docker Compose cold-start instructions verified from the repository root.

Never claim an external or E2E test passed if it was skipped, simulated, or used cached hard-coded output. Report missing credentials or unavailable infrastructure as a concrete blocker.

## Development Discipline

- Prefer small modules and explicit dependencies. Avoid framework abstractions that hide state transitions or provider calls.
- Use UTC in persistence and ISO-8601 at boundaries; use seconds as decimal numbers for media timecodes.
- Maintain deterministic IDs/idempotency keys for retryable ingestion and render commands.
- Log structured metadata, never media content, tokens, signed URLs, or secrets.
- Keep generated artifacts under ignored runtime directories.
- Update `README.md`, `.env.example`, Compose configuration, migrations, API docs, architecture notes, and media license manifest with the implementation.
- Preserve unrelated user changes. Do not rewrite the Nova design-source directories simply to make the production app cleaner.

## Definition of Done

CamCat is done only when the Docker Compose stack can be started from a clean checkout with documented credentials, all migrations and health checks succeed, a licensed short video completes real multimodal indexing, text and image queries return explainable reranked evidence, LangGraph creates and revises a persisted plan with demonstrated 409 conflict and rollback behavior, real subtitles and a playable FFmpeg output are produced, and the Nova-derived CamCat UI completes the entire journey in Playwright with all required tests passing.
