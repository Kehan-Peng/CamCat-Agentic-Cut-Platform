# Nova Backend

Minimal FastAPI backend for Nova Agent Platform Phase 1 and Phase 2.

## Run Tests

Run tests through the `nova` conda environment:

```bash
conda run -n nova pytest -q
```

## Start Server

Start the FastAPI server with:

```bash
conda run -n nova uvicorn backend.app.main:app --reload
```

## Phase 1 Flow

Phase 1 implements a local vertical slice:

1. Upload a video through the API.
2. Store video and segment metadata in an in-memory repository.
3. Run deterministic mock media processing.
4. Retrieve video detail and segment detail.
5. Search locally across generated mock segment data.

## Phase 2 Flow

Phase 2 adds deterministic agentic search over the same mock processed segments:

1. Rewrite the user query.
2. Run hybrid retrieval and reranking.
3. Return ranked evidence-backed segments with creative suggestions.
4. Produce a grounded final answer and reflection result.

## Implemented APIs

- `GET /health`: service health check.
- `POST /api/v1/videos`: upload a video and create mock processed segments.
- `GET /api/v1/videos/{video_id}`: fetch video detail.
- `GET /api/v1/segments/{segment_id}`: fetch segment detail.
- `POST /api/v1/search`: run local retrieval over Phase 1 data.
- `POST /api/v1/search/agentic`: run Phase 2 query rewrite, hybrid retrieval, reranking, creative suggestion, final answer, and reflection.

## Mocks

Nova uses deterministic mock media processing instead of real ASR, OCR, captioning, or embedding generation. Search runs against the local in-memory data produced by that mock pipeline.

## Out Of Scope

The following are intentionally out of scope:

- Real ASR, OCR, captioning, and embedding.
- Milvus, Qdrant, and OpenSearch.
- LangGraph.
- Celery, Redis, and workflow engines.
- Frontend.
- LLM calls.
- External services.
