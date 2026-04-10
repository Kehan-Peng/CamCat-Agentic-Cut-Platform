# Nova Agent Platform 项目简介

## 项目定位

Nova Agent Platform 是一个 **基于 LangGraph 的 Agentic Workflow 系统**，用于多模态内容搜索、检索、编辑规划和创意视频生成。

本项目不是通用的视频工具聊天包装器，也不是一次性的视频搜索演示。核心工程重点是设计面向生产的 Agent Workflows，协调检索、证据校验、编辑状态变更和安全的视频导出。

系统融合了两个原型方向：

1. **Nova** 提供多模态搜索、混合检索、证据校验的答案生成和基于 LangGraph 的 Agentic Search。
2. **VideoCutGPT** 贡献了编辑状态驱动的对话式编辑模型，用户对话变更持久化的编辑制品，而不是盲目重新生成整个视频计划。

最终架构不应过度使用”Lead Agent”或”多智能体组”术语。顶层协调器是 **LangGraph Coordinator Graph**。领域能力组织为 subgraphs、nodes、tools 和确定性服务。

## 核心架构

Nova 的核心研发重点是 **Agent 编排**，而非媒体数据建模。系统架构包括：

* **LangGraph Coordinator Graph**：顶层意图路由和状态转换
* **Intent Routing Layer**：意图分类和路由决策
* **Perception & Retrieval Subgraph**：多模态搜索和检索（8 个节点）
* **Editing Planning Subgraph**：编辑规划和状态变更（11 个节点）
* **Media Workflow Control Nodes**：触发和监控外部媒体处理
* **Export / Render Control Nodes**：渲染就绪检查和结果读取
* **Final Response Assembly**：最终响应组装
* **Editing Execution Service**（外部/非 Agent）：确定性渲染服务
* **Media Processing Workflow DAG**：重型媒体处理工作流
* **State Persistence Layer**：持久化状态管理

长视频、直播录屏和游戏高光素材都应被转换成可搜索、可解释、可复用、可创作的 `MediaSegment` 单元。每个 `MediaSegment` 保存时间边界、ASR 文本、OCR 文本、画面描述、标签、embedding 引用、运动分数、高光分数、元数据与 grounded evidence。

## 关键设计约束

### 复合路由机制

Coordinator Graph 必须支持复合意图路由，例如：

```text
帮我找热血片段，并剪成 30 秒短视频
```

应路由为：

```text
Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ FinalResponseNode
```

复合路由必须使用显式的 RouteSequenceControllerNode，而不是强制单一意图路由。

### MediaReadinessNode 重路由机制

MediaReadinessNode **不得直接调用** Media Workflow Control Nodes。

正确流程：
1. MediaReadinessNode 检查媒体就绪状态
2. 如果未就绪，写入 `route_request` / `readiness status` 到 AgentState
3. 让 Coordinator Graph 重新路由到 Media Workflow Control Nodes

### PlanDiffNode 语义

PlanDiffNode 必须生成 **最小 state patch**，而非全量重生成。

只有在用户明确要求"全部重来"时，才允许完整重新生成编辑计划。

### 渲染执行边界

**重度媒体处理和渲染不得直接在 LangGraph nodes 内运行。**

LangGraph nodes 可以：
- 触发外部 workflows/services
- 轮询状态
- 总结结果

但不能：
- 直接执行 FFmpeg
- 运行 ASR/OCR/Embedding
- 执行长时间媒体处理

## Perception & Retrieval Subgraph（8 个节点）

1. **MediaReadinessNode**：检查媒体是否已处理并可搜索
2. **QueryRewriteNode**：查询改写和意图扩展
3. **HybridRetrievalNode**：BM25 + Dense + Metadata 混合检索
4. **CandidateEvidenceAttachNode**：附加证据到候选结果
5. **RerankNode**：重排序候选结果
6. **FinalEvidenceGroundingNode**：最终证据校验
7. **SearchQualityCheckNode**：量化质量评估
8. **ConditionalRetryOrFinalize**：有界重试或完成

## Editing Planning Subgraph（11 个节点）

1. **IntentToEditTaskNode**：意图转换为编辑任务
2. **EditingStateReadNode**：读取编辑状态
3. **SegmentSelectionNode**：选择片段
4. **PlanDiffNode**：生成最小 state patch
5. **PatchValidationNode**：验证 patch
6. **SubtitleDraftNode**：字幕草稿生成
7. **ClipPlanNode**：剪辑计划生成
8. **TitleTagNode**：标题和标签生成
9. **ArtifactRefreshPlannerNode**：制品刷新规划
10. **EditingPlanValidationNode**：编辑计划验证
11. **EditingStateUpdateNode**：原子提交 + 版本检查

## Media Processing Workflow DAG

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

依赖关系：
- ASRTask 依赖 AudioExtractionTask
- OCRTask 和 CaptionTask 依赖 FrameExtractionTask
- SegmentBuilderTask 依赖 ASR/OCR/Caption/SceneShot 可用性
- TextEmbeddingTask 依赖 segment text
- VisualEmbeddingTask 依赖代表帧
- IndexingTask 依赖 segment + embeddings + metadata

## 核心价值主张

Nova 的价值是将不可直接操作的长视频转换成结构化媒体智能资产，并通过 LangGraph workflow 将查询理解、检索、编辑规划、证据校验和创作建议串成可追踪、可测试、可扩展的 Agentic Workflow。

核心价值包括：

* 基于 LangGraph 的生产级 Agent 编排，而非自研框架
* 复合意图路由和状态驱动的编辑规划
* 量化的检索质量评估和有界重试策略
* 最小 patch 驱动的编辑状态变更
* 外部确定性服务处理渲染和重型媒体处理
* Evidence Grounding，确保推荐理由只引用真实证据
* 可观测与可评估：`node_trace`、`AgentState` snapshot、`GraphRun` 记录
