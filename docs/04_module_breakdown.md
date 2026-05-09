# 模块拆分
本项目的研发重点位于 Agent Orchestration Modules。Retrieval、Media、Storage 是 LangGraph tools/nodes 所调用的领域能力模块。
## Backend Modules

建议包路径：`backend/app`。

* `api.routes.upload`：上传、文件校验、创建 `Video` 与处理任务。
* `api.routes.search`：`POST /api/v1/search` 普通检索。
* `api.routes.agentic_search`：`POST /api/v1/search/agentic`，调用 LangGraph workflow。
* `api.routes.segments`：片段详情、证据、创作建议。
* `api.routes.workflows`：media workflow status、retry、cancel。
* `domain.models`：定义 Video、MediaSegment、SegmentEvidence、SearchQuery、RetrievalResult、GraphRun、NodeTrace、ReflectionResult 等通用领域对象与 API DTO。
* `repositories`：Video、Segment、GraphRun、WorkflowRun、SearchQuery 的仓储。
* `storage.object_store`：MinIO/local object storage adapter。
* `cache`：Redis cache、checkpoint cache、retrieval cache、embedding cache。
* `observability`：structured logs、latency records、trace IDs、benchmark hooks。

MVP 可保持 FastAPI 单体结构，但模块边界按后续服务化设计。

## Agent Orchestration Modules

建议包路径：`backend/app/agents`。Phase 3 后应以 LangGraph 为核心。

```text
backend/app/agents/
├── graph.py
├── state.py
├── checkpoint.py
├── trace.py
├── tools.py
└── nodes/
    ├── query_rewrite.py
    ├── retrieval.py
    ├── rerank.py
    ├── creative.py
    ├── reflection.py
    └── final_answer.py
```

模块职责：

* `agents.graph`：定义 `StateGraph`，连接 QueryRewrite、Retrieval、Rerank、CreativeSuggestion、Reflection、FinalAnswer。
* `agents.state`：定义 LangGraph 执行时 AgentState，是 graph runtime 的唯一 state schema；如需 API 序列化，可复用 domain 中的 DTO 类型，但不在 domain.models 中重复定义 AgentState。
* `agents.checkpoint`：封装 LangGraph checkpointer；MVP 可用 memory checkpointer，后续 Redis/PostgreSQL。
* `agents.trace`：把 LangGraph node execution 转换为 `node_trace`。
* `agents.tools`：封装可被 LangGraph nodes 调用的业务能力适配器，例如 Retrieval Tool、Rerank Tool、Creative Suggestion Tool、Segment Detail Tool；不实现独立于 LangGraph 的通用 Tool Registry Runtime。
* `agents.nodes.query_rewrite`：中文创意查询改写。
* `agents.nodes.retrieval`：调用 Retrieval Engine。
* `agents.nodes.rerank`：调用 rerank。
* `agents.nodes.creative`：生成 BGM、转场、剪辑建议。
* `agents.nodes.reflection`：校验 grounding、timestamps、evidence、answer completeness。
* `agents.nodes.final_answer`：生成结构化最终答案。

需要移除或停止扩展的方向：

* 不继续扩展自研 `agents.planner.py`、`agents.runtime.py` 作为长期 runtime。
* 不继续自研完整 Tool Registry / DAG Runner 来替代 LangGraph。
* 现有 deterministic runtime 可作为 Phase 1/2 过渡实现，在 Phase 3 被 LangGraph graph 包装或替换。

## Retrieval Modules

建议包路径：`backend/app/retrieval`。

* `retrieval.query_rewrite`：可被 `QueryRewriteNode` 调用。
* `retrieval.bm25` / `retrieval.local_index`：Python BM25 或轻量 lexical index。
* `retrieval.embeddings`：embedding interface 与 deterministic local embedding。
* `retrieval.dense`：dense retrieval adapter，后续接 Milvus/Qdrant。
* `retrieval.filters`：metadata filtering。
* `retrieval.hybrid`：BM25 + dense + metadata hybrid fusion。
* `retrieval.rerank`：rule-based rerank，后续替换为 model reranker。
* `retrieval.explain`：基于 evidence 生成中文 reason。
* `retrieval.evaluation`：recall@k、MRR、nDCG。

原则：

* Retrieval Engine 是独立业务能力，不塞进 LangGraph node 内部。
* LangGraph node 调用 Retrieval Engine，而不是重写 retrieval logic。

## Multimodal Pipeline Modules

建议包路径：`backend/app/media`。

* `media.contracts`：ASR/OCR/Caption/Embedding/Frame/Audio 输出契约。
* `media.interfaces`：replaceable extractor interfaces。
* `media.preprocessing`：deterministic media preprocessing stub；future ffmpeg command builder 只能纯构造命令，不在默认测试执行。
* `media.mock_pipeline`：deterministic mock media processing。
* `media.asr`：Whisper/faster-whisper adapter，后续启用。
* `media.ocr`：PaddleOCR adapter，后续启用。
* `media.captioning`：frame caption adapter，后续启用。
* `media.scene_detection`：PySceneDetect adapter 与 fixed-window fallback。
* `media.segment_builder`：构建 `MediaSegment` 与 `SegmentEvidence`。
* `media.product_matching`：ToB mock catalog / product dictionary。

## Workflow Modules

建议包路径：`backend/app/workflows`。

* `workflows.status`：workflow status projection。
* `workflows.tasks`：Celery task entry points，Phase 4 引入。
* `workflows.retry`：retry policy。
* `workflows.idempotency`：idempotency key。
* `workflows.events`：progress events。

原则：

* LangGraph 负责 Agent workflow。
* Celery/Redis 负责重型 media workflow。
* 不再自研通用 DAG Runner 与 LangGraph/Celery 重叠。

## API Response / Trace Modules

* `agents.trace` 输出 `node_trace`。
* `agents.state` 输出 `state_snapshot`。
* `api.routes.agentic_search` 返回 `graph_run_id`、`thread_id`、`state_snapshot`、`node_trace`。

## Evaluation Modules

建议包路径：`backend/app/evaluation`。

* `evaluation.retrieval_metrics`：recall@k、precision@k、MRR、nDCG。
* `evaluation.agent_metrics`：node success rate、tool accuracy、reflection pass rate。
* `evaluation.fixtures`：query → expected segments fixture。
* `evaluation.benchmark_runner`：本地 benchmark。

## Frontend Modules

建议包路径：`apps/web`。

* `app/upload`
* `app/search`
* `app/segments/[segmentId]`
* `components/agent-trace-panel`
* `components/evidence-list`
* `components/creative-suggestion-panel`
* `components/segment-player`

前端 MVP 不做完整剪辑器，重点展示 `MediaSegment`、evidence、creative suggestions 与 LangGraph node trace。
