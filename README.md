# Nova AI-Cut Agent Platform

Nova Agent Platform 是一个**基于 LangGraph 的 Agentic Workflow 系统**，用于多模态内容搜索、检索、编辑规划和创意视频生成。

本项目核心工程重点是设计面向生产的 Agent Workflows，协调检索、证据校验、编辑状态变更和安全的视频导出。

## 项目定位

系统融合两个原型方向：

1. 基于 LangGraph 的多模态 Agentic Search。
2. 自然语言对话驱动的视频编辑模型。

<img width="1672" height="941" alt="Image26:5:10" src="https://github.com/user-attachments/assets/b6069057-c1a9-48b3-919a-aea26a1c462b" />

### 参考项目 VideoCutGPT

- **用途**：参考编辑状态、工作流制品、剪辑计划、渲染流程和对话式剪辑状态管理。
- **约束**：不修改原项目；不复制代码；优先迁移可复用设计和最小必要实现。

顶层协调器是 **LangGraph Coordinator Graph**。领域能力组织为 subgraphs、nodes、tools 和确定性服务。

## 核心架构

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
├── Editing Planning Subgraph (11 业务节点 + 2 编排节点)
│   ├── IntentToEditTaskNode
│   ├── EditingStateReadNode
│   ├── SegmentSelectionNode
│   ├── PlanDiffNode
│   ├── PatchValidationNode
│   ├── PlanningArtifactFork (编排节点)
│   ├── SubtitleDraftNode
│   ├── ClipPlanNode
│   ├── TitleTagNode
│   ├── PlanningArtifactJoinNode (编排节点)
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

```

### 外部确定性服务

```text
Editing Execution Service
├── ClipSegmentDeriver
├── FFmpegCommandBuilder
├── RenderJobRunner
├── OutputVerifier
└── ExportMetadataWriter
```

Editing Execution Service 是外部确定性服务，不是 LangGraph Agent 节点。LangGraph 只负责触发渲染任务、查询渲染状态和总结结果；不得在 graph node 内直接执行 FFmpeg。

### 重型媒体工作流

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

* ASRTask 依赖 AudioExtractionTask。
* OCRTask 和 CaptionTask 依赖 FrameExtractionTask。
* SegmentBuilderTask 依赖 ASR/OCR/Caption/SceneShot 可用性。
* TextEmbeddingTask 依赖 segment text。
* VisualEmbeddingTask 依赖代表帧。
* IndexingTask 依赖 segment、embeddings 和 metadata。

### 状态持久化层

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

## 复合路由机制

Coordinator Graph 必须支持复合意图。复合路由不得写死在某个 node 内部，必须由 `RouteSequenceControllerNode` 显式展开和推进。

支持的 route targets（11 种）：

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

**RouteSequenceControllerNode** 负责将复合路由展开为有序的 route_sequence，并推进执行。

AgentState 必须包含：
- `route_decision`：路由决策结果
- `route_sequence`：展开后的路由序列
- `current_route_step`：当前执行步骤
- `completed_route_steps`：已完成步骤

示例：

```text
用户查询：
帮我找热血片段，并剪成 30 秒短视频

路由流程：
StateLoadNode
→ IntentClassificationNode
→ RouteDecisionNode
→ RouteSequenceControllerNode
→ Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ FinalResponseNode
```

导出示例（export_only 必须路由到 Export / Render Control Nodes）：

```text
用户查询：
把当前剪辑导出成短视频

路由流程：
StateLoadNode
→ IntentClassificationNode
→ RouteDecisionNode (返回 export_only)
→ RouteSequenceControllerNode (展开为 [export_render_control])
→ RenderReadinessNode
→ RenderWorkflowTriggerNode
→ RenderWorkflowStatusNode / RenderWorkflowResultReadNode
→ FinalResponseNode

注意：export_only 不得直接路由到 Editing Execution Service，必须经过 Export / Render Control Nodes。
```

完整复合示例：

```text
用户查询：
帮我找热血片段，剪成 30 秒，并直接导出

路由流程：
Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ Export / Render Control Nodes
→ FinalResponseNode
```

## 核心设计原则

### 1. LangGraph 是编排层

LangGraph 负责 Agent workflow 编排、状态转换、条件路由、checkpoint 和 node trace。

LangGraph **不应成为**重写检索、媒体处理或渲染逻辑的地方。每个 node 应该是一个薄编排单元，读写 `AgentState`，然后调用现有领域服务。

### 2. 检索质量必须量化

检索 subgraph 不得使用开放式反思循环。搜索质量通过显式指标和重试预算评估。

* `SearchQualityCheckNode` 执行量化质量评估。
* `ConditionalRetryOrFinalize` 执行有界重试或以最佳努力结果退出。

### 3. 编辑应通过 patch 变更状态

编辑规划 subgraph 不得为每个用户指令重新生成完整编辑计划。

* `PlanDiffNode` 将新用户指令转换为最小 `EditingStatePatch`。
* `PatchValidationNode` 验证 patch。
* `PlanningArtifactFork` 显式分叉字幕、剪辑计划、标题标签等可并行规划任务。
* `PlanningArtifactJoinNode` 等待必要规划制品完成后再继续。
* `ArtifactRefreshPlannerNode` 决定哪些制品需要刷新。
* `EditingStateUpdateNode` 通过版本检查原子提交更新。

### 4. 渲染是确定性执行，非 Agent 推理

FFmpeg 渲染、输出验证、元数据写入和沙箱执行属于 Editing Execution Service。这些不是 LangGraph 推理节点。

LangGraph 可以触发渲染作业、检查渲染状态和总结结果。它不得在 agent graph 中直接执行 FFmpeg。

### 5. 重型媒体处理是 DAG

关键帧提取、音频提取、ASR、OCR、字幕、embedding 和索引必须建模为依赖感知的工作流 DAG，而不是平面任务列表。

索引不得在 segment building 和 embeddings 可用之前运行。ASR 不得在音频提取之前运行。OCR 和字幕不得在帧提取之前运行。

## MediaReadinessNode 重路由机制

`MediaReadinessNode` 位于 Perception & Retrieval Subgraph 内部，但它不得直接调用 Media Workflow Control Nodes。

正确机制：

```text
MediaReadinessNode
→ 写入 route_request / readiness_status 到 AgentState
→ 返回 Coordinator Graph
→ RouteSequenceControllerNode 根据 route_request 重新路由
→ Media Workflow Control Nodes
```

这样可以避免子图内部越权调用 Coordinator 层节点，保持架构分层清晰。

## Editing Planning 并行语义

Editing Planning Subgraph 有 **11 个核心业务节点** + **2 个编排节点**：

**编排节点：**
- `PlanningArtifactFork`：显式分叉可并行规划任务
- `PlanningArtifactJoinNode`：等待必要制品完成后再继续

`SubtitleDraftNode`、`ClipPlanNode`、`TitleTagNode` 不是默认线性链。它们必须通过显式 fork/join 表达可并行关系。

```text
PatchValidationNode
→ PlanningArtifactFork (编排节点)
   ├── SubtitleDraftNode (可并行)
   ├── ClipPlanNode (可并行)
   └── TitleTagNode (可并行)
→ PlanningArtifactJoinNode (编排节点)
→ ArtifactRefreshPlannerNode
→ EditingPlanValidationNode
→ EditingStateUpdateNode
```

规则：

* 如果 `TitleTagNode` 只依赖 selected segments，可以和字幕、剪辑计划并行。
* 如果 `TitleTagNode` 依赖最终 clip structure，则必须等待 `ClipPlanNode`。
* `PlanningArtifactJoinNode` 负责检查必要制品是否全部完成。

参考实现：
- `backend/app/agents/editing_planning/planning_artifact_fork.py`
- `backend/app/agents/editing_planning/planning_artifact_join.py`
- `tests/test_planning_artifact_fork_join.py`

## 状态冲突恢复

当 `EditingStateUpdateNode` 发现 `base_state_version != current_state_version` 时，必须进入 StateConflictRecoveryFlow。

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

## 当前实施 / 原型状态

当前仓库处于 **架构重置和迁移阶段**。

历史原型已包含部分能力，例如：

* FastAPI 后端骨架。
* 本地 mock 视频处理。
* 混合检索与重排原型。
* LangGraph Agentic Search 原型。
* 基础 node trace / state snapshot 原型。

新的目标路线以 `AGENTS.md` 和 `docs/` 中的 Phase 0-7 为准。旧实现可作为迁移基础，但不是最终架构的完整实现。

## Phase 0-7 开发路线

### Phase 0：Documentation Reset and Baseline Audit

目标：

* 确保所有规划文档反映 AGENTS.md 的最终架构决策。
* 删除所有 “LangGraph out of scope” 陈述。
* 删除所有 “self-built Agent Runtime is long-term architecture” 陈述。
* 明确复合路由机制和 `RouteSequenceControllerNode`。
* 明确 `MediaReadinessNode` 重路由机制。
* 明确 `PlanDiffNode` 最小 patch 语义。
* 明确渲染不在 LangGraph nodes 内运行。
* 明确 media workflow DAG 依赖关系。
* 明确 Editing Planning fork/join 结构。

### Phase 1：LangGraph Coordinator Foundation

目标：

* 建立 LangGraph Coordinator Graph 基础架构。
* 实现 Intent Routing Layer（5 个节点）。
* 实现 `RouteSequenceControllerNode` 和复合路由展开。
* 支持 checkpoint / thread。
* 支持 Graph Trace。
* 实现 `FinalResponseNode` 标准化响应模式。

TDD 覆盖：
- RouteSequenceControllerNode 展开 route_sequence
- editing_then_export 路由
- retrieval_then_editing_then_export 路由
- export_only 路由到 export_render_control

### Phase 2：Perception & Retrieval Subgraph

目标：

* 实现 8 个节点的检索 subgraph。
* 实现 `SearchQualityCheckNode` 的量化质量评估。
* 实现 `ConditionalRetryOrFinalize` 的有界重试。
* 保证无开放式 LLM 反思循环。

### Phase 3：Editing State and Planning Subgraph

目标：

* 实现 Editing Planning Subgraph（11 业务节点 + 2 编排节点）。
* 实现最小 patch 生成。
* 实现显式 `PlanningArtifactFork` / `PlanningArtifactJoinNode`。
* 实现原子状态更新。
* 实现 StateConflictRecoveryFlow。

TDD 覆盖：
- PlanningArtifactFork 分叉逻辑
- PlanningArtifactJoinNode 等待逻辑
- fork/join 不强制不必要的线性依赖

### Phase 4：Export / Render Control and Editing Execution Service

目标：

* 实现 Export / Render Control Nodes（4 个节点）。
* 实现 Editing Execution Service（5 个组件）。
* 安全构建 FFmpeg 参数列表。
* 支持隔离沙箱渲染。
* 支持输出校验和导出元数据写入。

### Phase 5：Media Workflow Control and Processing DAG

目标：

* 实现 Media Workflow Control Nodes（3 个节点）。
* 实现 Media Processing Workflow DAG（11 个任务）。
* 支持依赖感知任务调度。
* 支持部分成功状态。

### Phase 6：API Integration and Backward Compatibility

目标：

* 迁移 `/api/v1/search/agentic` 到 Coordinator Graph。
* 保持既有关键响应字段兼容。
* 增加 Editing Session APIs。
* 增加 Workflow Status APIs。
* 增加 Render / Export Status APIs。

### Phase 7：E2E, Hardening, and Documentation

目标：

* 完整端到端测试。
* 安全性测试。
* 用户隔离测试。
* 渲染安全测试。
* 无界重试防护测试。
* 文档和 API 示例收口。

## 快速开始

### 环境设置

```bash
conda activate nova
```

或：

```bash
conda run -n nova <command>
```

### 安装依赖

```bash
pip install -e ".[dev]"
```

或：

```bash
conda run -n nova pip install -e ".[dev]"
```

### 运行测试

```bash
conda run -n nova pytest -q
```

运行特定测试：

```bash
conda run -n nova pytest tests/test_agentic_search.py -v
```

### 运行服务器

```bash
conda run -n nova uvicorn backend.app.main:app --reload
```

指定端口：

```bash
conda run -n nova uvicorn backend.app.main:app --reload --port 8000
```

## 当前 API 草案

### POST /api/v1/search

传统混合检索接口。

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

### POST /api/v1/search/agentic

基于 LangGraph Coordinator Graph 的 Agentic Search 接口。

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

### POST /api/v1/videos

上传视频，创建 Video，触发 Media Processing Workflow DAG。

Request:

* Content type：`multipart/form-data`
* Fields：`file`、`source_type`、`metadata`

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

## 完成中...

默认测试依赖：

* Milvus / Qdrant / OpenSearch 生产部署。
* Celery / Redis 生产队列。
* MinIO 生产对象存储。
* vLLM / SGLang 生产部署。
* Prometheus / Grafana / OpenTelemetry dashboard。
* 真实大模型推理作为默认测试依赖。
* 完整视频剪辑器前端。


## 文档

**文档优先级：**

1. **AGENTS.md**：最高优先级，完整架构规范，唯一真理来源。
2. **docs/**：从 AGENTS.md 派生的详细规划文档。
3. **README.md**：从 AGENTS.md 和 docs/ 派生的项目概览。

**如果文档冲突，AGENTS.md 获胜。**

完整架构和实施文档位于：

* `AGENTS.md`：完整架构规范，**最高优先级文档**。
* `docs/00_project_brief.md`：项目简介。
* `docs/01_mvp_scope.md`：MVP 范围。
* `docs/02_system_architecture.md`：系统架构。
* `docs/03_domain_model.md`：领域模型。
* `docs/04_module_breakdown.md`：模块分解。
* `docs/05_api_contract.md`：API 契约。
* `docs/06_tdd_plan.md`：TDD 计划。
* `docs/07_implementation_plan.md`：实施计划。

## 开发规则

当使用 AI 编码代理或 Superpowers 风格开发时：

1. **遵循 `AGENTS.md` 中的当前架构**（最高优先级文档）。
2. 不引入开放式 LLM 重试循环。
3. 不在 LangGraph nodes 内实现渲染。
4. 不在最小 patch 足够时重新生成整个编辑计划。
5. 不绕过 `PatchValidationNode`、`PlanningArtifactJoinNode` 或 `EditingPlanValidationNode`。
6. 不将过时或无效的制品写入 `GlobalEditingState`。
7. 不直接从 `MediaReadinessNode` 调用 Media Workflow Control Nodes。
8. **复合路由必须通过 `RouteSequenceControllerNode` 显式展开**。
9. **导出路由（export_only）必须进入 Export / Render Control Nodes，不得直接指向 Editing Execution Service**。
10. **AgentState 的唯一运行时来源是 `backend/app/agents/state.py`**，domain.models 只定义 DTOs。
11. 保持测试确定性。
12. 保持 API 向后兼容性。
13. 优先使用薄节点和领域服务，而非胖节点。
14. 在生产代码之前添加测试。
15. 每个任务后运行完整测试。

## 核心价值主张

Nova 的价值是将不可直接操作的长视频转换成结构化媒体智能资产，并通过 LangGraph workflow 将查询理解、检索、编辑规划、证据校验和创作建议串成可追踪、可测试、可扩展的 Agentic Workflow。

核心价值包括：

* 基于 LangGraph 的生产级 Agent 编排，而非自研 Agent 框架。
* 复合意图路由和状态驱动的编辑规划。
* 量化的检索质量评估和有界重试策略。
* 最小 patch 驱动的编辑状态变更。
* 外部确定性服务处理渲染和重型媒体处理。
* Evidence Grounding，确保推荐理由只引用真实证据。
* 可观测与可评估：`node_trace`、`AgentState` snapshot、`GraphRun` 记录。

## License

MIT
