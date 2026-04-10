# MVP 范围

## MVP 定位

Nova 的 MVP 目标是构建基于 LangGraph 的 Agentic Workflow 系统，用于多模态搜索和创作。MVP 应证明：

1. LangGraph Coordinator Graph 可以协调复合意图路由
2. Perception & Retrieval Subgraph 可以执行量化质量评估和有界重试
3. Editing Planning Subgraph 可以通过最小 patch 变更编辑状态
4. 外部确定性服务可以安全处理渲染和重型媒体处理
5. MediaReadinessNode 可以正确触发重路由而非直接调用媒体处理

Phase 0 的目标是完成架构对齐和文档重写，确保所有规划文档反映 AGENTS.md 的最终架构决策。

## MVP 核心能力范围

### Coordinator Graph 复合路由

支持的路由目标：

```text
retrieval_only
editing_only
retrieval_then_editing
media_processing_required
media_processing_then_retrieval
media_processing_then_editing
export_only
clarification_required
finalize_with_error
```

复合路由示例：

```text
帮我找热血片段，并剪成 30 秒短视频
→ Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ FinalResponseNode
```

### Perception & Retrieval Subgraph

必须包含的 8 个节点：

1. MediaReadinessNode（检查就绪，触发重路由）
2. QueryRewriteNode（查询改写）
3. HybridRetrievalNode（混合检索）
4. CandidateEvidenceAttachNode（附加证据）
5. RerankNode（重排序）
6. FinalEvidenceGroundingNode（证据校验）
7. SearchQualityCheckNode（量化质量评估）
8. ConditionalRetryOrFinalize（有界重试）

关键约束：
- SearchQualityCheckNode 必须执行量化质量评估，不得使用开放式 LLM 反思循环
- ConditionalRetryOrFinalize 必须强制执行重试预算
- MediaReadinessNode 不得直接调用 Media Workflow Control Nodes

### Editing Planning Subgraph

必须包含的 11 个节点：

1. IntentToEditTaskNode
2. EditingStateReadNode
3. SegmentSelectionNode
4. PlanDiffNode（生成最小 patch）
5. PatchValidationNode
6. SubtitleDraftNode
7. ClipPlanNode
8. TitleTagNode
9. ArtifactRefreshPlannerNode
10. EditingPlanValidationNode
11. EditingStateUpdateNode（原子提交 + 版本检查）

关键约束：
- PlanDiffNode 必须生成最小 state patch，非全量重生成
- EditingStateUpdateNode 必须执行原子提交和版本检查
- 状态冲突时触发 StateConflictRecoveryFlow

### Export / Render Control Nodes

必须包含：

1. RenderReadinessNode
2. RenderWorkflowTriggerNode
3. RenderWorkflowStatusNode
4. RenderWorkflowResultReadNode

关键约束：
- 渲染不得在 LangGraph nodes 内直接执行
- 必须委托给外部 Editing Execution Service

### Editing Execution Service（外部/非 Agent）

必须包含：

1. ClipSegmentDeriver
2. FFmpegCommandBuilder
3. RenderJobRunner
4. OutputVerifier
5. ExportMetadataWriter

关键约束：
- 这是确定性服务，不是 Agent 节点
- FFmpeg 执行必须在隔离沙箱中运行
- 必须强制执行资源限制和超时

### Media Processing Workflow DAG

必须遵循依赖关系：

```text
ASRTask 依赖 AudioExtractionTask
OCRTask/CaptionTask 依赖 FrameExtractionTask
SegmentBuilderTask 依赖 ASR/OCR/Caption/SceneShot
TextEmbeddingTask 依赖 segment text
VisualEmbeddingTask 依赖代表帧
IndexingTask 依赖 segment + embeddings + metadata
```

关键约束：
- 不得在 ASR 前运行 audio extraction
- 不得在 embeddings 前运行 indexing
- 必须支持部分成功状态

## MVP 非目标

明确不包含在 MVP 范围内：

* 完整视频剪辑器时间线
* 生产级 SKU recognition
* 实时直播流处理
* 大规模分布式视频处理集群
* vLLM/SGLang 生产部署
* Milvus/Qdrant/OpenSearch 作为必须运行依赖
* 完整 Prometheus/Grafana/OpenTelemetry dashboard
* 全自动成片渲染
* 复杂长期记忆系统

## MVP 成功标准

架构对齐标准：

* 所有规划文档反映 AGENTS.md 架构
* 删除所有”LangGraph out of scope”陈述
* 删除所有”self-built Agent Runtime is long-term architecture”陈述
* 明确复合路由机制
* 明确 MediaReadinessNode 重路由机制
* 明确 PlanDiffNode 最小 patch 语义
* 明确渲染不在 LangGraph nodes 内运行
* 明确 media workflow DAG 依赖关系

工程成功标准：

* Coordinator Graph 支持复合路由
* Perception & Retrieval Subgraph 包含 8 个节点
* Editing Planning Subgraph 包含 11 个节点
* SearchQualityCheckNode 执行量化评估
* PlanDiffNode 生成最小 patch
* 渲染委托给外部服务
* Media workflow 遵循 DAG 依赖
