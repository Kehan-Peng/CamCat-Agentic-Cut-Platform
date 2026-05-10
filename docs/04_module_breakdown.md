# 模块拆分

本项目的研发重点位于 **Agent Orchestration Modules**。Retrieval、Media、Storage 是 LangGraph tools/nodes 所调用的领域能力模块。

## Backend Modules

建议包路径：`backend/app`。

* `api.routes.upload`：上传、文件校验、创建 `Video` 与处理任务
* `api.routes.search`：`POST /api/v1/search` 普通检索
* `api.routes.agentic_search`：`POST /api/v1/search/agentic`，调用 LangGraph Coordinator Graph
* `api.routes.editing`：编辑会话 APIs
* `api.routes.segments`：片段详情、证据、创作建议
* `api.routes.workflows`：media workflow status、retry、cancel
* `domain.models`：定义 Video、MediaSegment、SegmentEvidence、SearchQuery、RetrievalResult、AgentState、GlobalEditingState、GraphRun、NodeTrace、EditingStatePatch、ReflectionResult 等通用领域对象与 API DTO
* `repositories`：Video、Segment、GraphRun、WorkflowRun、SearchQuery、EditingSession 的仓储
* `storage.object_store`：MinIO/local object storage adapter
* `cache`：Redis cache、checkpoint cache、retrieval cache、embedding cache
* `observability`：structured logs、latency records、trace IDs、benchmark hooks

MVP 可保持 FastAPI 单体结构，但模块边界按后续服务化设计。

## Agent Orchestration Modules

建议包路径：`backend/app/agents`。核心是 LangGraph Coordinator Graph。

```text
backend/app/agents/
├── coordinator_graph.py
├── state.py
├── checkpoint.py
├── trace.py
├── tools.py
├── intent_routing/
│   ├── state_load.py
│   ├── intent_classification.py
│   ├── route_decision.py
│   └── final_response.py
├── perception_retrieval/
│   ├── media_readiness.py
│   ├── query_rewrite.py
│   ├── hybrid_retrieval.py
│   ├── candidate_evidence_attach.py
│   ├── rerank.py
│   ├── final_evidence_grounding.py
│   ├── search_quality_check.py
│   └── conditional_retry_or_finalize.py
├── editing_planning/
│   ├── intent_to_edit_task.py
│   ├── editing_state_read.py
│   ├── segment_selection.py
│   ├── plan_diff.py
│   ├── patch_validation.py
│   ├── subtitle_draft.py
│   ├── clip_plan.py
│   ├── title_tag.py
│   ├── artifact_refresh_planner.py
│   ├── editing_plan_validation.py
│   └── editing_state_update.py
├── media_workflow_control/
│   ├── media_workflow_trigger.py
│   ├── media_workflow_status.py
│   └── media_workflow_result_read.py
└── export_render_control/
    ├── render_readiness.py
    ├── render_workflow_trigger.py
    ├── render_workflow_status.py
    └── render_workflow_result_read.py
```

模块职责：

* `agents.coordinator_graph`：定义 LangGraph Coordinator Graph，连接 Intent Routing、Perception & Retrieval、Editing Planning、Media Workflow Control、Export / Render Control
* `agents.state`：定义 LangGraph 执行时 AgentState 和 GlobalEditingState
* `agents.checkpoint`：封装 LangGraph checkpointer；MVP 可用 memory checkpointer，后续 Redis/PostgreSQL
* `agents.trace`：把 LangGraph node execution 转换为 `node_trace`
* `agents.tools`：封装可被 LangGraph nodes 调用的业务能力适配器

### Intent Routing Layer

* `state_load`：加载 AgentState 和 GlobalEditingState
* `intent_classification`：识别用户意图（retrieval、editing、media processing、export、clarification、combined）
* `route_decision`：决定路由目标（支持复合路由）
* `final_response`：规范化成功、部分和失败的 subgraph 输出

### Perception & Retrieval Subgraph（8 个节点）

* `media_readiness`：检查媒体就绪状态，写入 route_request 触发重路由（不直接调用 Media Workflow Control Nodes）
* `query_rewrite`：中文创意查询改写
* `hybrid_retrieval`：调用 Retrieval Engine
* `candidate_evidence_attach`：附加证据到候选结果
* `rerank`：调用 rerank
* `final_evidence_grounding`：构建最终 grounded evidence
* `search_quality_check`：执行量化质量评估（不使用开放式 LLM 反思循环）
* `conditional_retry_or_finalize`：有界重试或完成

### Editing Planning Subgraph（11 个节点）

* `intent_to_edit_task`：将用户指令转换为结构化编辑任务
* `editing_state_read`：加载 GlobalEditingState
* `segment_selection`：选择候选片段
* `plan_diff`：生成最小 state patch（非全量重生成）
* `patch_validation`：验证 patch
* `subtitle_draft`：生成或更新字幕草稿
* `clip_plan`：生成或更新镜头级编辑计划
* `title_tag`：生成标题候选和标签
* `artifact_refresh_planner`：决定哪些制品需要刷新
* `editing_plan_validation`：验证编辑计划一致性
* `editing_state_update`：原子提交 + 版本检查

### Media Workflow Control Nodes

* `media_workflow_trigger`：触发媒体处理工作流
* `media_workflow_status`：读取工作流状态
* `media_workflow_result_read`：读取工作流结果

关键约束：
- 不在 LangGraph nodes 内直接执行重型媒体处理
- 只触发、轮询、读取和总结工作流状态

### Export / Render Control Nodes

* `render_readiness`：检查编辑计划是否可渲染
* `render_workflow_trigger`：触发外部渲染作业
* `render_workflow_status`：轮询渲染状态
* `render_workflow_result_read`：读取渲染输出和元数据

关键约束：
- 渲染不在 LangGraph nodes 内直接执行
- 委托给外部 Editing Execution Service

## Retrieval Modules

建议包路径：`backend/app/retrieval`。

* `retrieval.query_rewrite`：可被 `QueryRewriteNode` 调用
* `retrieval.bm25` / `retrieval.local_index`：Python BM25 或轻量 lexical index
* `retrieval.embeddings`：embedding interface 与 deterministic local embedding
* `retrieval.dense`：dense retrieval adapter，后续接 Milvus/Qdrant
* `retrieval.filters`：metadata filtering
* `retrieval.hybrid`：BM25 + dense + metadata hybrid fusion
* `retrieval.rerank`：rule-based rerank，后续替换为 model reranker
* `retrieval.explain`：基于 evidence 生成中文 reason
* `retrieval.evaluation`：recall@k、MRR、nDCG

原则：

* Retrieval Engine 是独立业务能力，不塞进 LangGraph node 内部
* LangGraph node 调用 Retrieval Engine，而不是重写 retrieval logic

## Multimodal Pipeline Modules

建议包路径：`backend/app/media`。

* `media.contracts`：ASR/OCR/Caption/Embedding/Frame/Audio 输出契约
* `media.interfaces`：replaceable extractor interfaces
* `media.preprocessing`：deterministic media preprocessing stub
* `media.mock_pipeline`：deterministic mock media processing
* `media.asr`：Whisper/faster-whisper adapter，后续启用
* `media.ocr`：PaddleOCR adapter，后续启用
* `media.captioning`：frame caption adapter，后续启用
* `media.scene_detection`：PySceneDetect adapter 与 fixed-window fallback
* `media.segment_builder`：构建 `MediaSegment` 与 `SegmentEvidence`
* `media.product_matching`：ToB mock catalog / product dictionary

## Editing Execution Service Modules

建议包路径：`backend/app/editing_execution`。

这是外部确定性服务，不是 Agent 节点。

* `editing_execution.clip_segment_deriver`：将编辑计划转换为可执行 ClipSegment
* `editing_execution.ffmpeg_command_builder`：构建安全的 FFmpeg 参数列表
* `editing_execution.render_job_runner`：异步执行渲染作业，在隔离沙箱中运行
* `editing_execution.output_verifier`：验证渲染输出
* `editing_execution.export_metadata_writer`：持久化 EditedVideoArtifact

安全规则：

* 使用参数列表，不使用 shell 字符串
* 验证文件路径
* 限制输入/输出目录
* 转义或拒绝不安全的元数据
* 拒绝任意过滤器，除非在白名单中

## Workflow Modules

建议包路径：`backend/app/workflows`。

* `workflows.media_dag`：Media Processing Workflow DAG 定义和依赖管理
* `workflows.status`：workflow status projection
* `workflows.tasks`：Celery task entry points，Phase 4 引入
* `workflows.retry`：retry policy
* `workflows.idempotency`：idempotency key
* `workflows.events`：progress events

原则：

* LangGraph 负责 Agent workflow
* Celery/Redis 负责重型 media workflow
* Media Processing Workflow DAG 必须遵循依赖关系

## API Response / Trace Modules

* `agents.trace` 输出 `node_trace`
* `agents.state` 输出 `state_snapshot`
* `api.routes.agentic_search` 返回 `graph_run_id`、`thread_id`、`state_snapshot`、`node_trace`
* `api.routes.editing` 返回 `editing_session_id`、`state_version`、`artifact_status`

## Evaluation Modules

建议包路径：`backend/app/evaluation`。

* `evaluation.retrieval_metrics`：recall@k、precision@k、MRR、nDCG
* `evaluation.agent_metrics`：node success rate、tool accuracy、reflection pass rate
* `evaluation.fixtures`：query → expected segments fixture
* `evaluation.benchmark_runner`：本地 benchmark

## Frontend Modules

建议包路径：`apps/web`。

* `app/upload`
* `app/search`
* `app/editing/[sessionId]`
* `app/segments/[segmentId]`
* `components/agent-trace-panel`
* `components/evidence-list`
* `components/creative-suggestion-panel`
* `components/segment-player`
* `components/editing-state-viewer`
* `components/artifact-status-panel`

前端 MVP 不做完整剪辑器，重点展示 `MediaSegment`、evidence、creative suggestions、LangGraph node trace、editing state 和 artifact status。

## 需要移除或停止扩展的方向

* 不继续扩展自研 `agents.planner.py`、`agents.runtime.py` 作为长期 runtime
* 不继续自研完整 Tool Registry / DAG Runner 来替代 LangGraph
* 现有 deterministic runtime 可作为过渡实现，但新能力优先进入 LangGraph nodes/tools
