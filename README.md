# Nova AI-Cut Agent Platform

> 面向生产环境的 LangGraph-based Agentic Workflow 平台，用于多模态视频搜索、片段检索、编辑规划和 AI-assisted video creation。

一个**基于 LangGraph 的 Agentic Workflow 系统**，面向多模态内容搜索、视频片段检索、证据校验、编辑状态规划和创意视频生成。

---

## 目录

- [项目概览](#项目概览)
- [演示预览](#演示预览)
- [项目定位](#项目定位)
- [核心能力](#核心能力)
- [系统架构](#系统架构)
- [外部确定性服务](#外部确定性服务)
- [Media Processing Workflow DAG](#media-processing-workflow-dag)
- [状态持久化层](#状态持久化层)
- [复合路由机制](#复合路由机制)
- [核心设计原则](#核心设计原则)
- [MediaReadinessNode 重路由机制](#mediareadinessnode-重路由机制)
- [Editing Planning 并行语义](#editing-planning-并行语义)
- [状态冲突恢复](#状态冲突恢复)
- [开发路线](#开发路线)
- [生产基础设施路线](#生产基础设施路线)
- [生产架构](#生产架构)
- [快速开始](#快速开始)
- [生产环境启动](#生产环境启动)
- [API 概览](#api-概览)
- [测试](#测试)
- [文档](#文档)
- [开发规则](#开发规则)
- [项目价值](#项目价值)
- [License](#license)

---

## 项目概览

Nova AI-Cut Agent Platform 将长视频、直播回放、游戏集锦等非结构化媒体内容转换为可检索、可解释、可编辑、可导出的结构化媒体智能资产。

系统支持：

- 上传视频并触发媒体处理工作流。
- 从 ASR、OCR、Caption、Embedding、Metadata 中构建可检索片段。
- 使用 Hybrid Retrieval 检索视频片段。
- 使用 LangGraph Coordinator Graph 编排 Query Rewrite、Retrieval、Rerank、Evidence Grounding、Editing Planning、Render Control。
- 通过自然语言生成或修改视频剪辑计划。
- 使用最小 EditingStatePatch 更新编辑状态，而不是每轮对话重新生成完整计划。
- 通过 Celery / Redis 执行重型媒体任务和渲染任务。
- 使用 MinIO 存储原始视频、中间制品和导出结果。
- 使用 OpenSearch + Qdrant / Milvus 提供生产级全文检索和向量检索。
- 使用外部 LLM API，例如 OpenAI / DeepSeek / OpenAI-compatible 服务，完成复杂 Agent 推理任务。

---

## 演示预览

<img width="1672" height="941" alt="Nova AI-Cut Agent Platform Preview" src="https://github.com/user-attachments/assets/b6069057-c1a9-48b3-919a-aea26a1c462b" />

---

## 项目定位

Nova 融合了两个方向：

1. **LangGraph-based Multimodal Agentic Search**
   基于 LangGraph 的多模态 Agentic Search，负责意图路由、查询改写、混合检索、重排、证据校验和最终回答。

2. **Conversation-driven Video Editing Model**
   自然语言对话驱动的视频编辑模型。用户每轮对话不会盲目重建完整视频计划，而是生成最小状态变更 patch，并持久化到 `GlobalEditingState`。

### 参考项目：VideoCutGPT

- **用途**：参考编辑状态、工作流制品、剪辑计划、渲染流程和对话式剪辑状态管理。
- **约束**：不修改原项目；不复制代码；优先迁移可复用设计和最小必要实现。

顶层协调器是 **LangGraph Coordinator Graph**。领域能力组织为 subgraphs、nodes、tools 和确定性服务。

---

## 核心能力

### Agentic Workflow

- LangGraph Coordinator Graph
- Intent Routing Layer
- RouteSequenceControllerNode
- Composite route execution
- Node trace
- State snapshot
- Checkpoint / thread support

### Multimodal Retrieval

- ASR / OCR / Caption / Metadata indexing
- BM25 / lexical search
- Dense vector retrieval
- Hybrid retrieval
- Rerank
- Evidence grounding
- Search quality evaluation
- Bounded retry policy

### Conversation-driven Editing

- GlobalEditingState
- EditingStatePatch
- PatchValidationNode
- PlanningArtifactFork / PlanningArtifactJoinNode
- ArtifactRefreshPlannerNode
- EditingPlanValidationNode
- Atomic EditingStateUpdateNode
- StateConflictRecoveryFlow

### Production Media Workflow

- Media Processing Workflow DAG
- Celery / Redis task queue
- MinIO object storage
- Render job lifecycle
- FFmpeg command builder
- Render sandbox boundary
- Output verification

### Production Retrieval and Model Gateway

- OpenSearch for BM25 / full-text retrieval
- Qdrant / Milvus for vector retrieval
- ModelGateway abstraction
- OpenAI provider
- DeepSeek provider
- OpenAI-compatible provider
- Structured output parsing
- Provider error normalization

---

## 系统架构

Nova 的核心研发重点是 **Agent 编排**。

```text
Nova LangGraph Coordinator Graph
├── Intent Routing Layer (5 nodes)
│   ├── StateLoadNode
│   ├── IntentClassificationNode
│   ├── RouteDecisionNode
│   ├── RouteSequenceControllerNode
│   └── FinalResponseNode
│
├── Perception & Retrieval Subgraph (8 nodes)
│   ├── MediaReadinessNode
│   ├── QueryRewriteNode
│   ├── HybridRetrievalNode
│   ├── CandidateEvidenceAttachNode
│   ├── RerankNode
│   ├── FinalEvidenceGroundingNode
│   ├── SearchQualityCheckNode
│   └── ConditionalRetryOrFinalize
│
├── Editing Planning Subgraph (11 business nodes + 2 orchestration nodes)
│   ├── IntentToEditTaskNode
│   ├── EditingStateReadNode
│   ├── SegmentSelectionNode
│   ├── PlanDiffNode
│   ├── PatchValidationNode
│   ├── PlanningArtifactFork
│   ├── SubtitleDraftNode
│   ├── ClipPlanNode
│   ├── TitleTagNode
│   ├── PlanningArtifactJoinNode
│   ├── ArtifactRefreshPlannerNode
│   ├── EditingPlanValidationNode
│   └── EditingStateUpdateNode
│
├── Media Workflow Control Nodes (3 nodes)
│   ├── MediaWorkflowTriggerNode
│   ├── MediaWorkflowStatusNode
│   └── MediaWorkflowResultReadNode
│
├── Export / Render Control Nodes (4 nodes)
│   ├── RenderReadinessNode
│   ├── RenderWorkflowTriggerNode
│   ├── RenderWorkflowStatusNode
│   └── RenderWorkflowResultReadNode
│
└── Final Response Assembly
````

---

## 外部确定性服务

### Editing Execution Service

```text
Editing Execution Service
├── ClipSegmentDeriver
├── FFmpegCommandBuilder
├── RenderJobRunner
├── OutputVerifier
└── ExportMetadataWriter
```

Editing Execution Service 是外部确定性服务，不是 LangGraph Agent 节点。

LangGraph 只负责：

* 触发渲染任务。
* 查询渲染状态。
* 总结渲染结果。
* 将结果写回 AgentState / GlobalEditingState。

LangGraph 不得在 graph node 内直接执行 FFmpeg。

---

## Media Processing Workflow DAG

重型媒体处理必须建模为 DAG，而不是平铺任务列表。

```text
Media Processing Workflow DAG
├── MetadataExtractionTask
├── AudioExtractionTask → ASRTask
├── FrameExtractionTask → OCRTask / CaptionTask
├── SceneShotDetectionTask
├── SegmentBuilderTask
├── TextEmbeddingTask
├── VisualEmbeddingTask
├── IndexingTask
└── SearchableStatusTask
```

依赖关系：

* `ASRTask` 依赖 `AudioExtractionTask`。
* `OCRTask` 和 `CaptionTask` 依赖 `FrameExtractionTask`。
* `SegmentBuilderTask` 依赖 ASR / OCR / Caption / SceneShot 的可用性。
* `TextEmbeddingTask` 依赖 segment text。
* `VisualEmbeddingTask` 依赖代表帧。
* `IndexingTask` 依赖 segment、embeddings 和 metadata。

---

## 状态持久化层

```text
State Persistence Layer
├── AgentState
├── GlobalEditingState
├── WorkflowArtifactStatus
├── MediaWorkflowRun
├── RenderJob
├── ClipSegments
├── EditedVideoArtifact
├── GraphRun
└── NodeTrace
```

### AgentState

`AgentState` 是 LangGraph runtime state 的唯一来源，定义在：

```text
backend/app/agents/state.py
```

`domain.models` 不应重复定义 runtime `AgentState`。

`domain.models` 只定义 DTO，例如：

* Video
* MediaSegment
* SegmentEvidence
* RetrievalResult
* GraphRun
* NodeTrace
* GlobalEditingState
* EditingStatePatch
* WorkflowArtifactStatus
* RenderJob
* MediaWorkflowRun

---

## 复合路由机制

Coordinator Graph 必须支持复合意图。复合路由不得写死在某个 node 内部，由 `RouteSequenceControllerNode` 显式展开和推进。

支持的 route targets：

```text
retrieval_only
editing_only
retrieval_then_editing
media_processing_required
media_processing_then_retrieval
media_processing_then_editing
export_only
editing_then_export
retrieval_then_editing_then_export
clarification_required
finalize_with_error
```

### RouteSequenceControllerNode

`RouteSequenceControllerNode` 负责将复合路由展开为有序的 `route_sequence`，并推进执行。

`AgentState` 必须包含：

* `route_decision`
* `route_sequence`
* `current_route_step`
* `completed_route_steps`

### 示例：Retrieval then Editing

```text
User:
帮我找热血片段，并剪成 30 秒短视频

Flow:
StateLoadNode
→ IntentClassificationNode
→ RouteDecisionNode
→ RouteSequenceControllerNode
→ Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ FinalResponseNode
```

### 示例：Export Only

```text
User:
把当前剪辑导出成短视频

Flow:
StateLoadNode
→ IntentClassificationNode
→ RouteDecisionNode (export_only)
→ RouteSequenceControllerNode ([export_render_control])
→ RenderReadinessNode
→ RenderWorkflowTriggerNode
→ RenderWorkflowStatusNode / RenderWorkflowResultReadNode
→ FinalResponseNode
```

重要约束：

```text
export_only must route to Export / Render Control Nodes.
export_only must not directly route to Editing Execution Service.
```

### 示例：Retrieval + Editing + Export

```text
User:
帮我找热血片段，剪成 30 秒，并直接导出

Flow:
Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ Export / Render Control Nodes
→ FinalResponseNode
```

---

## 核心设计原则

### 1. LangGraph 是编排层

LangGraph 负责：

* Agent workflow orchestration
* state transition
* conditional routing
* checkpoint
* node trace

LangGraph 不负责重写检索、媒体处理或渲染逻辑。每个 node 读写 `AgentState`，然后调用领域服务。

---

### 2. 检索质量必须量化

检索 subgraph 不得使用开放式 LLM reflection loop。搜索质量必须通过显式指标和重试预算评估。

* `SearchQualityCheckNode` 执行量化质量评估。
* `ConditionalRetryOrFinalize` 执行有界重试或返回 best-effort 结果。

---

### 3. 编辑更新必须基于 patch

编辑规划 subgraph 不得为每个用户指令重新生成完整编辑计划。

* `PlanDiffNode` 将用户指令转换为最小 `EditingStatePatch`。
* `PatchValidationNode` 验证 patch。
* `PlanningArtifactFork` 显式分叉字幕、剪辑计划、标题标签等可并行规划任务。
* `PlanningArtifactJoinNode` 等待必要规划制品完成后再继续。
* `ArtifactRefreshPlannerNode` 决定哪些制品需要刷新。
* `EditingStateUpdateNode` 通过版本检查原子提交更新。

---

### 4. 渲染是确定性执行，不是 Agent 推理

FFmpeg 渲染、输出验证、元数据写入和沙箱执行属于 Editing Execution Service。

LangGraph 可以触发渲染作业、检查渲染状态和总结结果，但不得在 agent graph 中直接执行 FFmpeg。

---

### 5. 重型媒体处理是 DAG

关键帧提取、音频提取、ASR、OCR、字幕、embedding 和索引必须建模为依赖感知的 workflow DAG。

索引不得在 segment building 和 embeddings 可用之前运行。
ASR 不得在音频提取之前运行。
OCR 和字幕不得在帧提取之前运行。

---

## MediaReadinessNode 重路由机制

`MediaReadinessNode` 位于 Perception & Retrieval Subgraph 内部，但它不得直接调用 Media Workflow Control Nodes。

正确机制：

```text
MediaReadinessNode
→ writes route_request / readiness_status into AgentState
→ returns control to Coordinator Graph
→ RouteSequenceControllerNode reroutes by route_request
→ Media Workflow Control Nodes
```

这样可以避免子图内部越权调用 Coordinator 层节点，保持架构分层清晰。

---

## Editing Planning 并行语义

Editing Planning Subgraph 有 **11 个核心业务节点** + **2 个编排节点**。

编排节点：

* `PlanningArtifactFork`
* `PlanningArtifactJoinNode`

`SubtitleDraftNode`、`ClipPlanNode`、`TitleTagNode` 不是默认线性链。它们必须通过显式 fork / join 表达可并行关系。

```text
PatchValidationNode
→ PlanningArtifactFork
   ├── SubtitleDraftNode
   ├── ClipPlanNode
   └── TitleTagNode
→ PlanningArtifactJoinNode
→ ArtifactRefreshPlannerNode
→ EditingPlanValidationNode
→ EditingStateUpdateNode
```

规则：

* 如果 `TitleTagNode` 只依赖 selected segments，可以和字幕、剪辑计划并行。
* 如果 `TitleTagNode` 依赖最终 clip structure，则必须等待 `ClipPlanNode`。
* `PlanningArtifactJoinNode` 负责检查必要制品是否全部完成。

参考实现：

```text
backend/app/agents/editing_planning/planning_artifact_fork.py
backend/app/agents/editing_planning/planning_artifact_join.py
tests/test_planning_artifact_fork_join.py
```

---

## 状态冲突恢复

当 `EditingStateUpdateNode` 发现：

```text
base_state_version != current_state_version
```

必须进入 `StateConflictRecoveryFlow`。

```text
state_conflict
→ ReloadEditingStateNode
→ RebasePatchNode
→ ConflictResolutionNode
→ retry | ask_user
```

规则：

* 不得静默覆盖新的编辑状态。
* 安全 rebase 可以自动重试。
* 不安全冲突必须返回 `clarification_required` 或要求用户确认。

---

## 开发路线

目标路线以 `AGENTS.md` 和 `docs/` 中的 Phase 0-7 为准。

### Phase 0: Documentation Reset and Baseline Audit

目标：

* 确保所有规划文档反映 `AGENTS.md` 的最终架构决策。
* 删除所有 “LangGraph out of scope” 陈述。
* 删除所有 “self-built Agent Runtime is long-term architecture” 陈述。
* 明确复合路由机制和 `RouteSequenceControllerNode`。
* 明确 `MediaReadinessNode` 重路由机制。
* 明确 `PlanDiffNode` 最小 patch 语义。
* 明确渲染不在 LangGraph nodes 内运行。
* 明确 media workflow DAG 依赖关系。
* 明确 Editing Planning fork / join 结构。

### Phase 1: LangGraph Coordinator Foundation

目标：

* 建立 LangGraph Coordinator Graph 基础架构。
* 实现 Intent Routing Layer。
* 实现 `RouteSequenceControllerNode` 和复合路由展开。
* 支持 checkpoint / thread。
* 支持 graph trace。
* 实现 `FinalResponseNode` 标准化响应模式。

TDD 覆盖：

* RouteSequenceControllerNode 展开 route_sequence。
* `editing_then_export` 路由。
* `retrieval_then_editing_then_export` 路由。
* `export_only` 路由到 `export_render_control`。

### Phase 2: Perception & Retrieval Subgraph

目标：

* 实现 8 个节点的检索 subgraph。
* 实现 `SearchQualityCheckNode` 的量化质量评估。
* 实现 `ConditionalRetryOrFinalize` 的有界重试。
* 保证无开放式 LLM reflection loop。

### Phase 3: Editing State and Planning Subgraph

目标：

* 实现 Editing Planning Subgraph。
* 实现最小 patch 生成。
* 实现显式 `PlanningArtifactFork` / `PlanningArtifactJoinNode`。
* 实现原子状态更新。
* 实现 `StateConflictRecoveryFlow`。

TDD 覆盖：

* PlanningArtifactFork 分叉逻辑。
* PlanningArtifactJoinNode 等待逻辑。
* fork / join 不强制不必要的线性依赖。

### Phase 4: Export / Render Control and Editing Execution Service

目标：

* 实现 Export / Render Control Nodes。
* 实现 Editing Execution Service。
* 安全构建 FFmpeg 参数列表。
* 支持隔离沙箱渲染。
* 支持输出校验和导出元数据写入。

### Phase 5: Media Workflow Control and Processing DAG

目标：

* 实现 Media Workflow Control Nodes。
* 实现 Media Processing Workflow DAG。
* 支持依赖感知任务调度。
* 支持部分成功状态。

### Phase 6: API Integration and Backward Compatibility

目标：

* 迁移 `/api/v1/search/agentic` 到 Coordinator Graph。
* 保持既有关键响应字段兼容。
* 增加 Editing Session APIs。
* 增加 Workflow Status APIs。
* 增加 Render / Export Status APIs。

### Phase 7: E2E, Hardening, and Documentation

目标：

* 完整端到端测试。
* 安全性测试。
* 用户隔离测试。
* 渲染安全测试。
* 无界重试防护测试。
* 文档和 API 示例收口。

---

## 生产基础设施路线

Nova 正在向生产级 Agentic Multimodal Search & Creation Platform 演进。

### 已完成的生产基础设施

#### Phase P0-P3: Infrastructure and Retrieval Stack

* Docker Compose service configuration。
* Redis / MinIO / OpenSearch / Qdrant service profiles。
* Environment-driven configuration system。
* Object storage abstraction。
* MinIO production storage + local fallback。
* Hybrid retrieval backend。
* OpenSearch BM25 retrieval。
* Qdrant vector retrieval。
* Path generation and checksum calculation。

#### Phase P4: Production Async Workflow with Celery / Redis

* Celery application configuration。
* Media / render queues。
* Task status management with Redis。
* Redis distributed locks。
* Idempotency locks。
* Retry strategies。
* Async media and render tasks。
* Task callback mechanism。

#### Phase P5: Production Model Gateway with External LLM APIs

* Unified ModelGateway interface。
* Provider implementations：

  * OpenAI
  * DeepSeek
  * OpenAI-compatible
  * Fake provider for tests
* Error normalization。
* Structured output parsing。
* Versioned prompt templates。
* Request tracing with `request_id` and `graph_run_id`。

#### Phase P6: Production Integration and E2E Verification

* Service health check tests。
* Production workflow E2E tests。
* Production mode validation tests。
* Enhanced `make verify-production`。
* Pytest markers：

  * unit
  * integration
  * provider_integration
  * production_e2e

---

## 生产架构

```text
┌─────────────────────────────────────────────────────────────┐
│                     Nova AI-Cut Agent Platform              │
│              Agentic Multimodal Search & Creation           │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌────────────────┐
│   FastAPI    │───▶│  LangGraph   │───▶│  ModelGateway  │
│   API Layer  │    │  Workflow    │    │  LLM API Layer │
└──────────────┘    └──────────────┘    └────────────────┘
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐    ┌────────────────────┐
                    │    Celery    │    │ OpenAI / DeepSeek  │
                    │ Async Tasks  │    │ Compatible APIs    │
                    └──────────────┘    └────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    MinIO     │    │  OpenSearch  │    │    Qdrant    │
│ Object Store │    │ BM25 Search  │    │ Vector Store │
└──────────────┘    └──────────────┘    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │    Redis     │
                    │ Queue/Cache  │
                    └──────────────┘
```

---

## 快速开始

### 1. 创建并激活环境

```bash
conda activate nova
```

也可以使用：

```bash
conda run -n nova <command>
```

### 2. 安装依赖

```bash
pip install -e ".[dev]"
```

或者：

```bash
conda run -n nova pip install -e ".[dev]"
```

### 3. 运行测试

```bash
conda run -n nova pytest -q
```

运行指定测试文件：

```bash
conda run -n nova pytest tests/test_agentic_search.py -v
```

### 4. 启动开发服务器

```bash
conda run -n nova uvicorn backend.app.main:app --reload
```

指定端口：

```bash
conda run -n nova uvicorn backend.app.main:app --reload --port 8000
```

---

## 生产环境启动

### 1. 启动基础设施服务

```bash
make infra-up
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 并配置模型服务：

```env
NOVA_MODEL_PROVIDER=openai

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=
DEEPSEEK_MODEL=

OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_MODEL=
```

### 3. 启动 Celery workers

```bash
celery -A backend.app.workers.celery_app worker -Q media,render -l info
```

### 4. 启动 FastAPI

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 5. 验证生产就绪状态

```bash
make verify-production
```

---

## API 概览

### POST `/api/v1/search`

传统 Hybrid Retrieval 接口。

Request:

```json
{
  "query_text": "帮我找热血片段",
  "top_k": 5,
  "filters": {
    "video_id": "vid_001",
    "tags": ["gameplay"]
  }
}
```

---

### POST `/api/v1/search/agentic`

基于 LangGraph 的 Agentic Search 接口。

Request:

```json
{
  "request_id": "req_001",
  "thread_id": "thread_001",
  "session_id": "sess_001",
  "query_text": "帮我找热血片段，并剪成 30 秒短视频",
  "top_k": 5,
  "filters": {
    "video_id": "vid_001",
    "tags": ["gameplay"],
    "min_motion_score": 0.4,
    "min_highlight_score": 0.5
  },
  "agent_config": {
    "enable_checkpoint": true,
    "response_language": "zh"
  }
}
```

Response:

```json
{
  "graph_run_id": "graph_run_001",
  "thread_id": "thread_001",
  "intent": "retrieval_then_editing",
  "route_targets": ["perception_retrieval", "editing_planning"],
  "route_sequence": ["perception_retrieval", "editing_planning"],
  "state_snapshot": {},
  "node_trace": [],
  "rewritten_query": {},
  "retrieved_segments": [],
  "reranked_segments": [],
  "search_quality_report": {},
  "editing_plan": {},
  "final_answer": {},
  "creative_suggestions": {}
}
```

---

### POST `/api/v1/videos`

上传视频并触发 Media Processing Workflow DAG。

Request:

* Content type: `multipart/form-data`
* Fields:

  * `file`
  * `source_type`
  * `metadata`

Response:

```json
{
  "request_id": "req_001",
  "video_id": "vid_001",
  "workflow_id": "wf_001",
  "status": "uploaded",
  "workflow_status": "queued",
  "segment_count": 0,
  "status_url": "/api/v1/workflows/wf_001"
}
```

---

## 测试

### 本地单元测试

```bash
make test-unit
```

或者：

```bash
conda run -n nova pytest -q
```

### 集成测试

```bash
make test-integration
```

需要 Docker Compose services。

### Provider integration tests

```bash
make test-provider-integration
```

需要外部 API keys。

### 生产验证

```bash
make verify-production
```

`make verify-production` 是主要的生产就绪验证命令。

### Test markers

```text
unit
integration
provider_integration
production_e2e
slow
```

---

## 文档

文档优先级：

1. `AGENTS.md`：最高优先级架构规范。
2. `docs/`：从 `AGENTS.md` 派生的阶段级详细规划文档。
3. `README.md`：从 `AGENTS.md` 和 `docs/` 派生的项目总览。

如果文档之间存在冲突，以 `AGENTS.md` 为准。

项目文档：

```text
AGENTS.md
docs/00_project_brief.md
docs/01_mvp_scope.md
docs/02_system_architecture.md
docs/03_domain_model.md
docs/04_module_breakdown.md
docs/05_api_contract.md
docs/06_tdd_plan.md
docs/07_implementation_plan.md
```

---

## 开发规则

使用 AI coding agents 或 Superpowers-style development 时：

1. 优先遵循 `AGENTS.md`。
2. 不引入开放式 LLM 重试循环。
3. 不在 LangGraph nodes 内执行渲染。
4. 最小 patch 足够时，不重新生成完整 editing plan。
5. 不绕过 `PatchValidationNode`、`PlanningArtifactJoinNode` 或 `EditingPlanValidationNode`。
6. 不将 stale 或 invalid artifacts 写入 `GlobalEditingState`。
7. 不从 `MediaReadinessNode` 直接调用 Media Workflow Control Nodes。
8. 复合路由必须通过 `RouteSequenceControllerNode` 展开。
9. `export_only` 必须进入 Export / Render Control Nodes，不得直接进入 Editing Execution Service。
10. `AgentState` runtime source of truth 是 `backend/app/agents/state.py`。
11. 尽量保持 API 向后兼容。
12. 优先使用 thin nodes 和 domain services，避免 fat nodes。
13. 先写测试，再写生产代码。
14. 每个任务后运行完整测试。
15. 不提交 API keys、secrets、provider tokens 或私有凭证。

---

## 项目概述

* 基于 LangGraph 的生产级 Agent 编排。
* 复合意图路由和状态驱动的编辑规划。
* 量化的检索质量评估和有界重试策略。
* 最小 patch 驱动的编辑状态变更。
* 外部确定性服务处理渲染和重型媒体处理。
* Evidence Grounding，确保推荐理由只引用真实证据。
* OpenSearch + Qdrant / Milvus 支撑生产级检索。
* MinIO 支撑生产级对象存储。
* Celery / Redis 支撑生产级异步媒体和渲染工作流。
* ModelGateway 支撑 OpenAI / DeepSeek / OpenAI-compatible 外部模型服务。
* 可观测与可评估：`node_trace`、`AgentState` snapshot、`GraphRun`、workflow status、production verification。

---

## License

MIT

```
