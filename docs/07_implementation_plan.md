# 实施计划

## AI Coding Workflow

每个 milestone 都遵循：

```text
Spec → Plan → Tests → Implementation → Review → Refactor → Docs
```

核心路线：

* Phase 1/2 的 deterministic local implementation 作为 vertical slice 与测试基线。
* Phase 3 迁移到 LangGraph，不继续扩展自研 Agent Runtime。
* Phase 4 再进入生产检索、异步媒体工作流和真实模型基础设施。

## Phase 1：Vertical Slice MVP

状态：已完成。

目标：

```text
Upload video
→ create Video
→ create MediaSegment
→ mock multimodal metadata
→ local retrieval
→ search
→ return timestamps, evidence reasons, creative suggestions
```

价值：

* 证明 `MediaSegment` 抽象成立。
* 证明本地可测试 vertical slice 成立。
* 为后续 LangGraph migration 提供可复用 query rewrite、retrieval、rerank、creative、reflection 函数。

## Phase 2：Multimodal Retrieval & Agentic Search Upgrade

状态：已完成。

目标：

* 建立 replaceable media contracts/interfaces。
* 添加 deterministic preprocessing stub。
* 升级 hybrid retrieval：BM25-like lexical、deterministic dense embedding、metadata filtering、hybrid fusion、rerank。
* 添加 evaluation utilities：recall@k、MRR、nDCG。
* 添加 agentic search runtime lite 与 `POST /api/v1/search/agentic`。
* 添加 Phase 2 E2E acceptance coverage。

注意：

* Phase 2 的 runtime lite 是过渡层，不是最终 Agent Orchestration Layer。
* 后续不应继续把它扩展成完整自研框架。

## Phase 3：LangGraph Migration

目标：

Phase 3 的研发重点是将 Nova 从 deterministic agent runtime lite 升级为 LangGraph-based Agent Orchestration System。

本阶段的核心产物：
* AgentState contract
* LangGraph StateGraph
* QueryRewrite / Retrieval / Rerank / Creative / Reflection / FinalAnswer nodes
* checkpoint / thread state
* node_trace
* /api/v1/search/agentic 的 LangGraph execution path

### Task 1：Add LangGraph Dependency

范围：

* 添加 `langgraph` 依赖。
* 保持默认测试轻量。
* 不引入外部 LLM 调用。

验收：

* pyproject.toml 添加 langgraph 运行依赖；在 nova conda environment 中执行 pip install -e ".[dev]" 后，conda run -n nova pytest -q 通过。
* `conda run -n nova pytest -q` 通过。

### Task 2：Define AgentState

文件：

* `backend/app/agents/state.py`
* `tests/test_agent_state.py`

内容：

* 定义 `AgentState`。
* 字段包含 `graph_run_id`、`thread_id`、`user_id`、`session_id`、`query_text`、`rewritten_query`、`expanded_queries`、`retrieved_segments`、`reranked_segments`、`creative_suggestions`、`reflection_result`、`final_answer`、`node_trace`、`errors`、`top_k`、`retrieval_mode`、`search_scope`、`agent_config`。

验收：

* state 可序列化。
* 默认值稳定。
* 不包含重型不可序列化对象。

### Task 3：Wrap Existing Functions As Nodes

文件：

```text
backend/app/agents/nodes/query_rewrite.py
backend/app/agents/nodes/retrieval.py
backend/app/agents/nodes/rerank.py
backend/app/agents/nodes/creative.py
backend/app/agents/nodes/reflection.py
backend/app/agents/nodes/final_answer.py
```

要求：

* node 调用现有模块，不复制业务逻辑。
* node 输入/输出为 `AgentState`。
* 每个 node 有 unit test。

验收：

* QueryRewriteNode 写入 rewritten query。
* RetrievalNode 写入 retrieved segments。
* RerankNode 写入 reranked segments。
* CreativeSuggestionNode 写入 creative suggestions。
* ReflectionNode 写入 reflection result。
* FinalAnswerNode 写入 grounded final answer。

### Task 4：Build StateGraph

文件：

* `backend/app/agents/graph.py`
* `tests/test_agent_graph.py`

要求：

```text
START
→ QueryRewriteNode
→ RetrievalNode
→ RerankNode
→ CreativeSuggestionNode
→ ReflectionNode
→ FinalAnswerNode
→ END
```

验收：

* graph integration test 通过。
* 节点顺序稳定。
* state transition 符合预期。

### Task 5：Checkpoint / Thread Support

文件：

* `backend/app/agents/checkpoint.py`
* `tests/test_agent_checkpoint.py`

要求：

* MVP 使用 LangGraph memory checkpointer。
* 预留 Redis/PostgreSQL checkpointer adapter。
* 支持 `thread_id`。

验收：

* 同一 `thread_id` 可恢复 state。
* 不同用户/thread 不互相污染。

### Task 6：Graph Trace

文件：

* `backend/app/agents/trace.py`
* `tests/test_agent_trace.py`

要求：

* 将 LangGraph node execution 转换为 `node_trace`。
* 记录 node name、status、latency、error。

验收：

* API 可返回稳定 `node_trace`。
* node failure 有结构化 error。

### Task 7：Replace `/api/v1/search/agentic` Internals

文件：

* `backend/app/api/routes.py` 或 `backend/app/api/routes/agentic_search.py`
* `tests/test_agentic_search_api.py`

要求：

* API 路径不变。
* response shape 升级为 LangGraph 语义。
* 返回 `graph_run_id`、`thread_id`、`state_snapshot`、`node_trace`、`rewritten_query`、`retrieved_segments`、`reranked_segments`、`reflection_result`、`final_answer`、`creative_suggestions`。

验收：

* 旧客户端关键字段兼容，或明确版本化。
* E2E agentic search 通过。

### Task 8：Remove Long-term Self-built Runtime Expansion Path

要求：

* 标记旧 `AgentSearchRuntime` 为 Phase 2 compatibility layer。
* 不继续给旧 runtime 添加 planner/memory/tool orchestration 能力。
* 新能力优先进入 LangGraph nodes/tools。

验收：

* 文档和模块注释清晰。
* 测试覆盖 LangGraph graph，而不是只测旧 runtime。

## Phase 4：Production Retrieval & Workflow

目标：

在 LangGraph Agentic Workflow 稳定后，再引入生产检索、异步媒体处理和真实模型。

范围：

* Milvus 或 Qdrant。
* Celery + Redis。
* MinIO。
* PostgreSQL。
* real ASR/OCR/Caption/Embedding adapters。
* Prometheus/Grafana/OpenTelemetry。
* batch media workflow。
* retrieval cache / embedding cache。

原则：

* 不在 Phase 3 同时引入重型基础设施，避免迁移风险叠加。
* 每个外部依赖都必须有 deterministic mock path。

## Phase 5：Frontend And Demo Packaging

目标：

* 展示 upload、segment search、agentic search、node trace、evidence、creative suggestions。
* 不做完整剪辑器。
* 输出 ToC/ToB demo scripts、README、architecture diagram、evaluation report。

## Risks And Tradeoffs

### 架构漂移风险

风险：继续扩展自研 runtime，导致项目看起来像闭门造系统。

缓解：Phase 3 明确迁移到 LangGraph，所有新 Agent 能力优先进 `StateGraph` nodes/tools。

### 依赖引入风险

风险：一次性引入 LangGraph、Celery、Redis、Milvus、真实模型导致复杂度失控。

缓解：Phase 3 只引入 LangGraph；Phase 4 再引入生产基础设施。

### 测试不稳定风险

风险：真实模型和外部服务让 CI 不稳定。

缓解：默认测试使用 deterministic mock adapters；真实模型进入 integration/nightly。

### Agent 输出幻觉风险

风险：final answer 编造不存在证据。

缓解：ReflectionNode 强制校验 timestamps、evidence、reasons、answer completeness。

## Review Gate

在以下文档完成复审并被接受之前，不得开始下一轮代码实现：

* `docs/00_project_brief.md`
* `docs/01_mvp_scope.md`
* `docs/02_system_architecture.md`
* `docs/03_domain_model.md`
* `docs/04_module_breakdown.md`
* `docs/05_api_contract.md`
* `docs/06_tdd_plan.md`
* `docs/07_implementation_plan.md`

复审标准：

* 项目定位明确为基于 LangGraph 的 Agentic Multimodal Media Intelligence Platform。
* LangGraph 位于 Agent Orchestration Layer，不替代 Retrieval、Media Pipeline、Storage、Celery/Redis。
* `MediaSegment` 仍是核心领域抽象。
* `/api/v1/search/agentic` 明确由 LangGraph workflow 执行。
* Phase 3 是 LangGraph Migration。
* Phase 4 才是 Production Retrieval & Workflow。
* 不再把自研 Agent Runtime 作为长期主线。
