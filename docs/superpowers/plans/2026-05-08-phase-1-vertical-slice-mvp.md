# Phase 1 Compact Task Queue

## Task 1: Backend Skeleton and Health Check

- Create FastAPI app.
- Add pytest setup.
- Add `GET /health`.
- Add minimal README/test command if necessary.
- No business logic.

Do not implement:

- `Video` model.
- `MediaSegment` model.
- Upload API.
- Search API.
- Retrieval engine.
- Mock processing.
- Creative suggestions.
- Repository.
- Workflow logic.

## Task 2: Domain Models

- Implement Video.
- Implement MediaSegment.
- Implement SegmentEvidence.
- Implement SearchQuery.
- Implement RetrievalResult.
- Implement CreativeSuggestion if needed for response shape.
- Add validation tests.

## Task 3: In-Memory Repository and Mock Processing

- Store uploaded videos and generated segments in memory.
- Mock processing creates 3-5 `MediaSegment` objects.
- Mock ASR/OCR/caption/tags/motion_score/highlight_score.
- No real video processing.

## Task 4: Upload and Segment Detail APIs

- `POST /api/v1/videos`.
- `GET /api/v1/videos/{video_id}`.
- `GET /api/v1/segments/{segment_id}`.
- Upload synchronously triggers mock processing.

## Task 5: Local Retrieval and Search API

- Implement local lexical retrieval over ASR/OCR/caption/tags.
- Add simple scoring and rerank using `motion_score` / `highlight_score`.
- `POST /api/v1/search`.
- Return ranked segments with timestamps, scores, evidence-based reasons, and creative suggestions.

## Task 6: End-to-End Acceptance Test

- Test upload -> mock process -> search -> ranked segment response.
- Ensure reasons only reference existing segment evidence.
- Ensure tests pass.

## Controller Rules

- Existing Phase 0 docs are background only.
- Controller creates complete task packets dynamically for each fresh subagent.
- Implementation subagents must not read all project docs.
- Use one fresh implementer subagent per task.
- Run fresh spec compliance review first.
- Only if spec compliance passes, run fresh code quality review.
- Do not move to the next task until both reviews pass.
- Use TDD for every implementation task.

## Task 1 Packet

Goal: create only the backend skeleton, pytest setup, and health check.

Files to create:

```text
pyproject.toml
README.md
backend/__init__.py
backend/app/__init__.py
backend/app/main.py
backend/app/api/__init__.py
backend/app/api/routes.py
tests/__init__.py
tests/conftest.py
tests/test_health.py
```

Required behavior:

- `GET /health` returns:

```json
{"status": "ok", "service": "nova-backend"}
```

TDD steps:

- Write `tests/conftest.py` with a FastAPI `TestClient`.
- Write `tests/test_health.py::test_health_returns_ok`.
- Run the test and confirm it fails before implementation.
- Implement the smallest FastAPI app and route.
- Run the test and confirm it passes.

Task 1 non-goals:

- No domain models.
- No upload API.
- No search API.
- No repository.
- No mock processing.
- No retrieval.
- No creative suggestions.
- No workflow.
- No Celery, Milvus, Qdrant, LangGraph, vLLM, SGLang, Whisper, PaddleOCR, CLIP, SigLIP, frontend, or real model integrations.

## Task 1 Spec Compliance Review Criteria

- Only Task 1 files were created.
- `GET /health` exists and returns exactly `{"status": "ok", "service": "nova-backend"}`.
- pytest setup works.
- No business logic was added.
- No domain models were added.
- No upload/search/retrieval/mock processing/repository/workflow code was added.
- No forbidden infrastructure or real model dependency was introduced.
- Implementer was not asked to read all project docs.

## Task 1 Code Quality Review Criteria

- FastAPI app structure is simple and idiomatic.
- Route registration is easy to extend later.
- Tests are clear and behavior-focused.
- README/test command, if added, matches reality.
- No unnecessary abstractions.
- No global mutable business state.
- No hidden network calls, subprocesses, or heavy dependencies.

