# Nova Agent Platform

Nova Agent Platform 是基于 LangGraph 的 Agentic Multimodal Media Intelligence Platform，面向视频内容理解、片段级检索、高光定位和创作建议生成。

系统将上传的视频转换为可检索、可解释、可复用的 `MediaSegment`，再通过 Hybrid Retrieval、Rerank、Evidence Grounding 和 LangGraph Agent Workflow 返回带时间戳、证据和创作建议的结构化结果。

## 当前实现

当前代码已经实现一个可运行的后端闭环：

```text
Upload video
-> create Video record
-> mock multimodal processing
-> create MediaSegment objects
-> build local hybrid retrieval index
-> execute lexical / dense / hybrid search
-> rerank by relevance, motion_score, highlight_score, tags
-> run LangGraph agentic search workflow
-> return grounded answer and creative suggestions
```

已实现能力：

- FastAPI backend skeleton and route registration
- `Video`、`MediaSegment`、`SearchQuery`、`RetrievalResult` 等核心领域模型
- 用户隔离的 in-memory repository
- 确定性 mock 多模态处理管线
- 可替换的 media processing contracts
- deterministic media preprocessing adapter / stub
- 本地 BM25-like lexical retrieval
- deterministic local dense embedding stub
- metadata filtering
- hybrid score fusion
- rule-based rerank
- retrieval evaluation utilities: `recall@k`、`MRR`、`nDCG`
- LangGraph `AgentState` and `StateGraph`
- Query Rewrite、Retrieval、Rerank、Creative Suggestion、Final Answer、Reflection nodes
- in-memory checkpointer and `thread_id` support
- serializable `node_trace`
- backward-compatible normal search API
- LangGraph-backed agentic search API

## Architecture

```text
Nova Agent Platform
├── API Layer
│   └── FastAPI routes
├── Agent Orchestration Layer
│   ├── LangGraph StateGraph
│   ├── AgentState
│   ├── QueryRewriteNode
│   ├── RetrievalNode
│   ├── RerankNode
│   ├── CreativeSuggestionNode
│   ├── FinalAnswerNode
│   ├── ReflectionNode
│   ├── Checkpointer
│   └── Node Trace
├── Multimodal Pipeline
│   ├── media contracts
│   ├── mock processing pipeline
│   └── preprocessing adapter / stub
├── Retrieval Engine
│   ├── BM25-like lexical retrieval
│   ├── deterministic dense embedding
│   ├── metadata filtering
│   ├── hybrid fusion
│   ├── rerank
│   └── evaluation metrics
└── Storage
    └── in-memory repository
```

## API

All API requests that access user data require:

```text
X-User-Id: <user_id>
```

Implemented endpoints:

- `GET /health`
- `POST /api/v1/videos`
- `GET /api/v1/videos/{video_id}`
- `GET /api/v1/segments/{segment_id}`
- `POST /api/v1/search`
- `POST /api/v1/search/agentic`

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "nova-backend"
}
```

### Upload Video

```bash
curl -X POST http://127.0.0.1:8000/api/v1/videos \
  -H "X-User-Id: user_1" \
  -F "file=@sample.mp4"
```

The current implementation stores metadata in memory and synchronously creates deterministic mock `MediaSegment` objects.

### Normal Search

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user_1" \
  -d '{
    "query_text": "帮我找适合做热血卡点的视频素材",
    "top_k": 5
  }'
```

Response includes:

- `query_rewrite`
- `expanded_queries`
- `results`
- `answer`
- `creative_suggestion`

### Agentic Search

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search/agentic \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user_1" \
  -d '{
    "query_text": "帮我找适合做热血卡点的视频素材",
    "top_k": 5,
    "thread_id": "demo-thread-1"
  }'
```

`/api/v1/search/agentic` is executed by the LangGraph workflow.

Response includes:

- `graph_run_id`
- `thread_id`
- `state_snapshot`
- `node_trace`
- `plan`
- `rewritten_query`
- `retrieved_segments`
- `reranked_segments`
- `ranked_segments`
- `reflection_result`
- `final_answer`
- `creative_suggestions`

## Run Locally

Use the existing `nova` conda environment.

Install dependencies:

```bash
conda run -n nova python -m pip install -e ".[dev]"
```

Run tests:

```bash
conda run -n nova pytest -q
```

Start the API server:

```bash
conda run -n nova uvicorn backend.app.main:app --reload
```

Default local URL:

```text
http://127.0.0.1:8000
```

## Test Coverage

The test suite covers:

- health check
- domain model validation
- in-memory repository user scoping
- mock media processing
- media contracts and preprocessing stub
- upload and segment detail APIs
- normal search API
- hybrid retrieval
- rerank
- retrieval metrics
- agent planner and tools
- LangGraph node execution
- `AgentState` serialization
- checkpoint / thread behavior
- node trace serialization
- agentic search API
- Phase 2 and Phase 3 end-to-end flows

## Current Mocked Components

The project is intentionally deterministic in local tests:

- media decoding is stubbed
- ASR is mocked
- OCR is mocked
- frame captioning is mocked
- visual/text embedding uses deterministic local logic
- rerank is rule-based
- creative suggestions are rule-based
- storage is in memory
- checkpointing is in memory
- no external LLM call is made

## Planned But Not Yet Completed

The following work is planned but not implemented in the current local backend:

- real video frame/audio extraction with FFmpeg adapter
- production ASR adapter such as Whisper or faster-whisper
- production OCR adapter such as PaddleOCR
- production captioning and visual embedding adapters
- vector database integration such as Milvus or Qdrant
- production lexical index such as OpenSearch
- persistent metadata database
- object storage such as MinIO
- Celery / Redis async media workflow
- Prometheus / Grafana / OpenTelemetry observability
- frontend application
- streaming response
- external LLM or self-hosted LLM serving through vLLM / SGLang

## Development Notes

- Keep API response compatibility for `POST /api/v1/search`.
- Add new agentic behavior through LangGraph nodes and `AgentState`.
- Keep heavy model and infrastructure integrations behind adapters.
- Keep tests deterministic and runnable with `conda run -n nova pytest -q`.
