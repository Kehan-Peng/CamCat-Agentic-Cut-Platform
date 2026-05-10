# 系统架构

## 高层架构

Nova Agent Platform 是基于 LangGraph 的 Agentic Workflow 系统，用于多模态内容搜索、检索、编辑规划和创意视频生成。核心研发重点是 **Agent 编排**，而非媒体数据建模。

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

外部确定性服务：

```text
Editing Execution Service
├── ClipSegmentDeriver
├── FFmpegCommandBuilder
├── RenderJobRunner
├── OutputVerifier
└── ExportMetadataWriter
```

重型媒体工作流：

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

状态持久化层：

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

## 核心架构原则

### LangGraph 是编排层

LangGraph 负责 Agent workflow 编排、状态转换、条件路由、checkpoint 和 node trace。

LangGraph **不应成为**重写检索、媒体处理或渲染逻辑的地方。每个 node 应该是一个薄编排单元，读写 `AgentState`，然后调用现有的领域服务。

### 检索质量必须量化

检索 subgraph 不得使用开放式反思循环。搜索质量通过显式指标和重试预算评估。

`SearchQualityCheckNode` 执行量化质量评估。

`ConditionalRetryOrFinalize` 执行有界重试或以最佳努力结果退出。

### 编辑应通过 patch 变更状态

编辑规划 subgraph 不得为每个用户指令重新生成完整编辑计划。

`PlanDiffNode` 将新用户指令转换为最小 `EditingStatePatch`。

`PatchValidationNode` 验证 patch。

`ArtifactRefreshPlannerNode` 决定哪些制品需要刷新。

`EditingStateUpdateNode` 通过版本检查原子提交更新。

### 渲染是确定性执行，非 Agent 推理

FFmpeg 渲染、输出验证、元数据写入和沙箱执行属于 Editing Execution Service。这些不是 LangGraph 推理节点。

LangGraph 可以触发渲染作业、检查渲染状态和总结结果。它不得在 agent graph 中直接执行 FFmpeg。

### 重型媒体处理是 DAG

关键帧提取、音频提取、ASR、OCR、字幕、embedding 和索引必须建模为依赖感知的工作流 DAG，而不是平面任务列表。

索引不得在 segment building 和 embeddings 可用之前运行。ASR 不得在音频提取之前运行。OCR 和字幕不得在帧提取之前运行。

## Coordinator Graph 条件路由

Coordinator Graph 不是线性链。它是条件 LangGraph workflow。

主流程：

```text
START
→ StateLoadNode
→ IntentClassificationNode
→ RouteDecisionNode
→ RouteSequenceControllerNode
→ conditional route
```

`RouteDecisionNode` 必须返回以下路由目标之一（11 种）：

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

`RouteSequenceControllerNode` 负责将复合路由展开为有序的 `route_sequence`，并推进执行。

AgentState 必须包含：
- `route_decision`：路由决策结果
- `route_sequence`：展开后的路由序列（如 `["perception_retrieval", "editing_planning"]`）
- `current_route_step`：当前执行步骤
- `completed_route_steps`：已完成步骤

参考实现：
- `backend/app/agents/intent_routing/route_sequence_controller.py`
- `tests/test_route_sequence_controller.py`

条件边（通过 RouteSequenceControllerNode 展开）：

```text
RouteSequenceControllerNode
├── retrieval_only → [perception_retrieval] → Perception & Retrieval Subgraph
├── editing_only → [editing_planning] → Editing Planning Subgraph
├── retrieval_then_editing → [perception_retrieval, editing_planning]
├── media_processing_required → [media_workflow_control] → Media Workflow Control Nodes
├── media_processing_then_retrieval → [media_workflow_control, perception_retrieval]
├── media_processing_then_editing → [media_workflow_control, editing_planning]
├── export_only → [export_render_control] → Export / Render Control Nodes
├── editing_then_export → [editing_planning, export_render_control]
├── retrieval_then_editing_then_export → [perception_retrieval, editing_planning, export_render_control]
├── clarification_required → [final_response] → FinalResponseNode
└── finalize_with_error → [final_response] → FinalResponseNode
```

**重要约束：**
- `export_only` 必须路由到 Export / Render Control Nodes，**不得直接路由到 Editing Execution Service**。
- Export / Render Control Nodes 负责触发、轮询和总结渲染作业，Editing Execution Service 是外部确定性服务。

Coordinator Graph 必须支持复合意图。例如：

```text
帮我找热血片段，并剪成 30 秒短视频
```

应路由为：

```text
Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ FinalResponseNode
```

而不是强制单一意图路由。

## Media Workflow Control Node 路由

Media Workflow Control Nodes 是 Coordinator Graph 的一部分，但它们不直接执行重型媒体处理。

它们负责：

- 检查视频是否已处理并可搜索
- 如果需要，触发媒体处理工作流
- 读取工作流状态
- 向 Coordinator Graph 返回延迟、部分或就绪状态

它们可以通过两种方式到达：

1. 当用户意图需要未处理的媒体时，直接从 `RouteDecisionNode` 到达
2. 当检索或编辑需要未就绪的制品时，从 `MediaReadinessNode` 间接到达

规则：

- LangGraph nodes 不得直接运行 ASR、OCR、embedding、ffmpeg 或渲染
- 重型处理必须委托给 `Media Processing Workflow DAG`
- Coordinator Graph 只触发、轮询、读取和总结工作流状态

## MediaReadinessNode 重路由机制

**MediaReadinessNode 不得直接调用 Media Workflow Control Nodes。**

正确流程：

1. MediaReadinessNode 检查请求的视频或资产库是否已索引并可搜索
2. 如果媒体未就绪，写入 `route_request` / `readiness status` 到 AgentState
3. 返回，让 Coordinator Graph 重新路由到 Media Workflow Control Nodes

此节点不得直接执行关键帧提取、ASR、OCR、字幕、embedding 或索引。

## Perception & Retrieval Subgraph

8 个节点：

1. **MediaReadinessNode**：检查媒体就绪状态，触发重路由
2. **QueryRewriteNode**：将用户查询转换为结构化检索意图
3. **HybridRetrievalNode**：执行 BM25 + dense + metadata 混合检索
4. **CandidateEvidenceAttachNode**：附加 ASR、OCR、caption、tag、score 证据
5. **RerankNode**：使用 lexical、dense、evidence、tag、motion、highlight 重排序
6. **FinalEvidenceGroundingNode**：构建最终 grounded evidence
7. **SearchQualityCheckNode**：执行量化检索质量评估
8. **ConditionalRetryOrFinalize**：决定完成、重试或返回最佳努力结果

关键约束：

- SearchQualityCheckNode 必须执行量化质量评估，不得使用开放式 LLM 反思循环
- ConditionalRetryOrFinalize 必须强制执行重试预算
- 不允许无界反思循环

## Editing Planning Subgraph

**11 个核心业务节点 + 2 个编排节点：**

核心业务节点：
1. **IntentToEditTaskNode**：将用户指令转换为结构化编辑任务
2. **EditingStateReadNode**：加载 `GlobalEditingState` 和制品状态
3. **SegmentSelectionNode**：选择候选片段进行编辑
4. **PlanDiffNode**：将用户指令转换为最小 state patch
5. **PatchValidationNode**：验证操作模式、拒绝无效操作
6. **SubtitleDraftNode**：生成或更新字幕草稿
7. **ClipPlanNode**：生成或更新镜头级编辑计划
8. **TitleTagNode**：生成标题候选和标签
9. **ArtifactRefreshPlannerNode**：决定哪些制品需要刷新
10. **EditingPlanValidationNode**：验证编辑计划一致性
11. **EditingStateUpdateNode**：原子提交 patch 和刷新的制品

编排节点：
- **PlanningArtifactFork**：显式分叉可并行规划任务（SubtitleDraftNode、ClipPlanNode、TitleTagNode）
- **PlanningArtifactJoinNode**：等待必要制品完成后再继续

流程：

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

参考实现：
- `backend/app/agents/editing_planning/planning_artifact_fork.py`
- `backend/app/agents/editing_planning/planning_artifact_join.py`
- `tests/test_planning_artifact_fork_join.py`

关键约束：

- PlanDiffNode 必须生成最小 state patch，除非用户明确要求完全重新开始
- EditingStateUpdateNode 必须通过 `state_version` 强制执行乐观锁定
- 如果发生冲突：`state_conflict → ReloadStateNode → RebasePatchNode → Retry or AskUser`

## StateConflictRecoveryFlow

当状态版本冲突发生时：

1. **ReloadEditingStateNode**：重新加载当前状态
2. **RebasePatchNode**：尝试将 patch 变基到新版本
3. **ConflictResolutionNode**：决定重试或请求用户输入

## Export / Render Control Nodes

4 个节点：

1. **RenderReadinessNode**：检查编辑计划是否可渲染
2. **RenderWorkflowTriggerNode**：触发外部渲染作业
3. **RenderWorkflowStatusNode**：轮询渲染状态
4. **RenderWorkflowResultReadNode**：读取渲染输出和元数据

关键约束：

- 渲染不得在 LangGraph nodes 内直接执行
- 必须委托给外部 Editing Execution Service

## Editing Execution Service（外部/非 Agent）

确定性服务组件：

1. **ClipSegmentDeriver**：将验证的编辑计划转换为可执行 `ClipSegment` 记录
2. **FFmpegCommandBuilder**：构建安全的 FFmpeg 参数列表
3. **RenderJobRunner**：异步执行渲染作业，在隔离沙箱中运行
4. **OutputVerifier**：验证渲染输出（文件存在、大小、时长、编解码器）
5. **ExportMetadataWriter**：持久化 `EditedVideoArtifact`

安全规则：

- 使用参数列表，不使用 shell 字符串
- 验证文件路径
- 限制输入/输出目录
- 转义或拒绝不安全的元数据
- 拒绝任意过滤器，除非在白名单中

资源控制：

- 超时
- CPU / 内存限制
- 磁盘配额
- 输出大小限制
- 沙箱工作目录
- 取消
- 重试策略
- 作业租约 / 心跳

## Media Processing Workflow DAG

依赖关系：

```text
Upload / StoreOriginal
        ↓
MetadataExtractionTask
        ↓
 ┌───────────────┬─────────────────┐
 │               │                 │
AudioExtraction  FrameExtraction   SceneShotDetection
 │               │                 │
ASRTask          OCRTask            SegmentBoundaryTask
                 CaptionTask        │
 │               │                 │
 └───────────────┴───────────────┬─┘
                                 ↓
                         SegmentBuilderTask
                                 ↓
              ┌──────────────────┴──────────────────┐
              │                                     │
        TextEmbeddingTask                    VisualEmbeddingTask
              │                                     │
              └──────────────────┬──────────────────┘
                                 ↓
                         IndexingTask
                                 ↓
                         SearchableStatusTask
```

依赖约束：

- ASRTask 依赖 AudioExtractionTask
- OCRTask 和 CaptionTask 依赖 FrameExtractionTask
- SegmentBuilderTask 依赖 ASR/OCR/Caption/SceneShot 可用性
- TextEmbeddingTask 依赖 segment text
- VisualEmbeddingTask 依赖代表帧
- IndexingTask 依赖 segment + embeddings + metadata

工作流必须支持部分成功：

```text
partially_searchable
searchable_with_missing_ocr
searchable_with_missing_caption
searchable_with_text_only_embedding
```

## 状态模型

### AgentState

LangGraph 执行的运行时状态。

推荐字段：

```text
graph_run_id
thread_id
user_id
session_id
query_text
intent
route_targets
retrieval_state
editing_state_ref
node_trace
errors
final_response
```

AgentState 是短暂的和可 checkpoint 的。它不是持久化编辑的真实来源。

### GlobalEditingState

编辑会话的持久化状态。

推荐字段：

```text
editing_session_id
user_id
video_id
state_version
current_goal
selected_segments
subtitle_draft
editing_plan
clip_segments
title_candidates
tag_candidates
render_jobs
artifact_status
needs_refresh
last_user_revision
updated_at
```

### WorkflowArtifactStatus

跟踪制品是否就绪、过时、阻塞、失败、可导出或缺失。

建议状态：

```text
missing
requested
running
ready
stale
blocked
failed
exportable
```

## 可观测性

MVP 必须支持：

- 基本结构化日志
- `graph_run_id`、`thread_id`、`node_trace`
- 检索延迟记录
- reflection issue 记录
- benchmark hooks
- 简单评估脚本

后续生产化再引入 Prometheus、Grafana、OpenTelemetry。

## 非协商设计原则

1. **LangGraph 是编排层**：不在 LangGraph node 内重写检索、媒体处理或渲染逻辑
2. **检索质量必须量化**：使用显式指标和有界重试，不使用开放式反思循环
3. **编辑应通过 patch 变更状态**：生成最小 state patch，不盲目重新生成
4. **渲染是确定性执行**：FFmpeg 渲染属于外部服务，不在 agent graph 中
5. **重型媒体处理是 DAG**：建模为依赖感知工作流，不是平面任务列表
