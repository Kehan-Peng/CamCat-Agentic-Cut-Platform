# 实施计划

## 核心路线

Nova 的实施路线基于 AGENTS.md 定义的最终架构：

* **Phase 0**：架构对齐和文档重写
* **Phase 1**：LangGraph Coordinator Graph 基础
* **Phase 2**：Perception & Retrieval Subgraph（8 个节点）
* **Phase 3**：Editing Planning Subgraph（11 个节点）
* **Phase 4**：Media Processing Workflow DAG 和 Editing Execution Service
* **Phase 5**：生产基础设施和优化

## Phase 0：架构对齐和文档重写

状态：进行中。

目标：

* 确保所有规划文档反映 AGENTS.md 的最终架构决策
* 删除所有"LangGraph out of scope"陈述
* 删除所有"self-built Agent Runtime is long-term architecture"陈述
* 明确复合路由机制
* 明确 MediaReadinessNode 重路由机制
* 明确 PlanDiffNode 最小 patch 语义
* 明确渲染不在 LangGraph nodes 内运行
* 明确 media workflow DAG 依赖关系

### Task 0.1：Read and Understand AGENTS.md

验收：

* 理解 LangGraph Coordinator Graph 架构
* 理解 Perception & Retrieval Subgraph（8 个节点）
* 理解 Editing Planning Subgraph（11 个节点）
* 理解 Media Processing Workflow DAG 依赖关系
* 理解关键设计约束

### Task 0.2：Rewrite Planning Docs

验收：

* docs/00_project_brief.md 反映 AGENTS.md 架构
* docs/01_mvp_scope.md 反映 AGENTS.md 架构
* docs/02_system_architecture.md 反映 AGENTS.md 架构
* docs/03_domain_model.md 反映 AGENTS.md 架构
* docs/04_module_breakdown.md 反映 AGENTS.md 架构
* docs/05_api_contract.md 反映 AGENTS.md 架构
* docs/06_tdd_plan.md 反映 AGENTS.md 架构
* docs/07_implementation_plan.md 反映 AGENTS.md 架构

### Task 0.3：Review and Validate

验收：

* 所有文档一致性检查通过
* 所有关键约束明确记录
* 所有复合路由机制明确记录
* 所有 DAG 依赖关系明确记录

## Phase 1：LangGraph Coordinator Graph 基础

目标：

建立 LangGraph Coordinator Graph 基础架构，包括 Intent Routing Layer 和条件路由机制。

### Task 1.1：Add LangGraph Dependency

范围：

* 添加 `langgraph` 依赖到 pyproject.toml
* 保持默认测试轻量
* 不引入外部 LLM 调用

验收：

* `conda run -n nova pytest -q` 通过

### Task 1.2：Define AgentState and GlobalEditingState

文件：

* `backend/app/agents/state.py`
* `tests/test_agent_state.py`

内容：

* 定义 `AgentState`，包含 `graph_run_id`、`thread_id`、`user_id`、`session_id`、`query_text`、`intent`、`route_targets`、`rewritten_query`、`expanded_queries`、`retrieved_segments`、`reranked_segments`、`creative_suggestions`、`reflection_result`、`final_answer`、`node_trace`、`errors`、`route_request`、`readiness_status`
* 定义 `GlobalEditingState`，包含 `editing_session_id`、`user_id`、`video_id`、`state_version`、`current_goal`、`selected_segments`、`subtitle_draft`、`editing_plan`、`clip_segments`、`title_candidates`、`tag_candidates`、`render_jobs`、`artifact_status`、`needs_refresh`

验收：

* state 可序列化
* 默认值稳定
* 不包含重型不可序列化对象

### Task 1.3：Build Intent Routing Layer

文件：

```text
backend/app/agents/intent_routing/state_load.py
backend/app/agents/intent_routing/intent_classification.py
backend/app/agents/intent_routing/route_decision.py
backend/app/agents/intent_routing/final_response.py
tests/test_intent_routing.py
```

要求：

* StateLoadNode 加载 AgentState 和可选的 GlobalEditingState
* IntentClassificationNode 识别 retrieval_only、editing_only、retrieval_then_editing、media_processing_required、export_only、clarification_required
* RouteDecisionNode 支持所有路由目标，包括复合路由
* FinalResponseNode 规范化成功、部分和失败的 subgraph 输出

验收：

* 复合意图识别正确："帮我找热血片段，并剪成 30 秒短视频" → retrieval_then_editing
* 路由决策支持所有目标
* 用户隔离正确

### Task 1.4：Build Coordinator Graph

文件：

* `backend/app/agents/coordinator_graph.py`
* `tests/test_coordinator_graph.py`

要求：

```text
START
→ StateLoadNode
→ IntentClassificationNode
→ RouteDecisionNode
→ conditional route
```

验收：

* graph integration test 通过
* 条件路由正确执行
* state transition 符合预期

### Task 1.5：Checkpoint / Thread Support

文件：

* `backend/app/agents/checkpoint.py`
* `tests/test_agent_checkpoint.py`

要求：

* MVP 使用 LangGraph memory checkpointer
* 预留 Redis/PostgreSQL checkpointer adapter
* 支持 `thread_id`

验收：

* 同一 `thread_id` 可恢复 state
* 不同用户/thread 不互相污染

### Task 1.6：Graph Trace

文件：

* `backend/app/agents/trace.py`
* `tests/test_agent_trace.py`

要求：

* 将 LangGraph node execution 转换为 `node_trace`
* 记录 node name、status、latency、error

验收：

* API 可返回稳定 `node_trace`
* node failure 有结构化 error

## Phase 2：Perception & Retrieval Subgraph（8 个节点）

目标：

实现 Perception & Retrieval Subgraph，包括量化质量评估和有界重试。

### Task 2.1：MediaReadinessNode

文件：

* `backend/app/agents/perception_retrieval/media_readiness.py`
* `tests/test_media_readiness.py`

要求：

* 检查视频或资产库是否已索引并可搜索
* 如果媒体未就绪，写入 `route_request` / `readiness status` 到 AgentState
* **不直接调用 Media Workflow Control Nodes**

验收：

* 媒体就绪时返回 ready
* 媒体未就绪时写入 route_request
* 不直接触发媒体处理

### Task 2.2：QueryRewriteNode

文件：

* `backend/app/agents/perception_retrieval/query_rewrite.py`
* `tests/test_query_rewrite.py`

要求：

* 中文创意查询改写
* 扩展查询词用于 text、visual、motion、tag、editing needs
* 保留原始查询

验收：

* "帮我找适合做热血卡点的视频素材" 扩展为热血、燃系、高能、快节奏、镜头切换明显、动作强、beat 匹配、团战、冲刺、反击、高潮片段
* 不编造具体品牌、商品或视频来源

### Task 2.3：HybridRetrievalNode

文件：

* `backend/app/agents/perception_retrieval/hybrid_retrieval.py`
* `tests/test_hybrid_retrieval.py`

要求：

* 执行 BM25-like lexical search
* 执行 deterministic dense retrieval
* 应用 metadata filters
* 融合候选结果通过 hybrid score fusion

验收：

* 返回 retrieved_results 和 channel-level scores
* 支持中文查询

### Task 2.4：CandidateEvidenceAttachNode

文件：

* `backend/app/agents/perception_retrieval/candidate_evidence_attach.py`
* `tests/test_candidate_evidence_attach.py`

要求：

* 附加 ASR、OCR、caption、tag、score、metadata 证据到候选结果
* 准备证据特征用于 reranking

验收：

* 证据正确附加
* 不是最终答案 grounding 层

### Task 2.5：RerankNode

文件：

* `backend/app/agents/perception_retrieval/rerank.py`
* `tests/test_rerank.py`

要求：

* 使用 lexical score、dense score、evidence quality、tag match、motion score、highlight score、query intent 重排序
* 保留原始通道分数用于可解释性

验收：

* 对热血卡点 query，提升 motion_score / highlight_score 高的片段
* 排序稳定

### Task 2.6：FinalEvidenceGroundingNode

文件：

* `backend/app/agents/perception_retrieval/final_evidence_grounding.py`
* `tests/test_final_evidence_grounding.py`

要求：

* 构建最终 grounded evidence
* 确保 reasons 只引用真实证据
* 拒绝或标记 ungrounded explanations

验收：

* 证据来源：ASR chunks、OCR blocks、frame captions、tags、motion/highlight scores、metadata
* 没有证据幻觉

### Task 2.7：SearchQualityCheckNode

文件：

* `backend/app/agents/perception_retrieval/search_quality_check.py`
* `tests/test_search_quality_check.py`

要求：

* **执行量化检索质量评估，不使用开放式 LLM 反思循环**
* 计算 quality_score、result_count、top_score、avg_topk_score、evidence_coverage、timestamp_coverage、diversity_score、query_match_score
* 最小质量指标：result_count >= min_results、top_score >= min_top_score、avg_topk_score >= min_avg_score、evidence_coverage >= min_evidence_coverage、timestamp_coverage == 1.0、grounding_passed == true

验收：

* 返回 passed、issues、retry_action、retry_reason
* 不使用 LLM 反思

### Task 2.8：ConditionalRetryOrFinalize

文件：

* `backend/app/agents/perception_retrieval/conditional_retry_or_finalize.py`
* `tests/test_conditional_retry_or_finalize.py`

要求：

* **强制执行重试预算**
* 决定完成、重试或返回最佳努力结果
* 重试策略：no_results → relax_filters or rewrite query、low_evidence_coverage → rerun evidence-heavy retrieval、low_semantic_match → rewrite query、duplicate_results → diversity rerank

验收：

* 重试预算强制执行
* **不允许无界反思循环**

### Task 2.9：Integrate Perception & Retrieval Subgraph

文件：

* `backend/app/agents/coordinator_graph.py`（更新）
* `tests/test_perception_retrieval_subgraph.py`

要求：

* 将 8 个节点集成到 Coordinator Graph
* 支持 retrieval_only 和 retrieval_then_editing 路由

验收：

* E2E retrieval subgraph test 通过
* SearchQualityCheckNode 执行量化评估
* ConditionalRetryOrFinalize 强制执行重试预算

## Phase 3：Editing Planning Subgraph（11 个节点）

目标：

实现 Editing Planning Subgraph，包括最小 patch 生成和原子状态更新。

### Task 3.1：IntentToEditTaskNode

文件：

* `backend/app/agents/editing_planning/intent_to_edit_task.py`
* `tests/test_intent_to_edit_task.py`

要求：

* 将用户指令转换为结构化编辑任务
* 区分 clip generation、subtitle editing、title/tag update、export request、style revision

验收：

* 示例指令正确识别

### Task 3.2：EditingStateReadNode

文件：

* `backend/app/agents/editing_planning/editing_state_read.py`
* `tests/test_editing_state_read.py`

要求：

* 加载 `GlobalEditingState`
* 加载 artifact statuses
* 验证用户所有权

验收：

* 状态正确加载
* 用户隔离正确

### Task 3.3：SegmentSelectionNode

文件：

* `backend/app/agents/editing_planning/segment_selection.py`
* `tests/test_segment_selection.py`

要求：

* 选择候选片段进行编辑
* 重用检索结果（如果可用）
* 避免选择不可用或未授权的片段

验收：

* 返回 selected segment IDs、segment evidence summaries、selection reason

### Task 3.4：PlanDiffNode

文件：

* `backend/app/agents/editing_planning/plan_diff.py`
* `tests/test_plan_diff.py`

要求：

* **生成最小 state patch，不重新生成整个编辑计划**
* 支持的操作：add_segment、remove_segment、replace_segment、reorder_segments、trim_segment、update_subtitle_style、update_title_style、update_bgm_style、update_transition_style、update_hook、update_clip_duration、mark_artifact_stale
* 只有用户明确要求"全部重来"时才允许完整重新生成

验收：

* 输入"把开头改得更抓人一点，第二段删掉，字幕短一点"生成最小 patch
* patch 包含 patch_id、base_state_version、operations、affected_artifacts、needs_refresh
* 不全量重生成

### Task 3.5：PatchValidationNode

文件：

* `backend/app/agents/editing_planning/patch_validation.py`
* `tests/test_patch_validation.py`

要求：

* 验证操作模式
* 拒绝删除不存在的 clip segments
* 拒绝无效的 segment IDs
* 确保 `base_state_version` 存在

验收：

* 无效 patch 被拒绝

### Task 3.6：SubtitleDraftNode, ClipPlanNode, TitleTagNode

文件：

* `backend/app/agents/editing_planning/subtitle_draft.py`
* `backend/app/agents/editing_planning/clip_plan.py`
* `backend/app/agents/editing_planning/title_tag.py`
* `tests/test_editing_artifacts.py`

要求：

* SubtitleDraftNode 生成或更新字幕草稿
* ClipPlanNode 生成或更新镜头级编辑计划
* TitleTagNode 生成标题候选和标签

验收：

* 制品正确生成
* 当 patch 不影响时保留先前部分

### Task 3.7：ArtifactRefreshPlannerNode

文件：

* `backend/app/agents/editing_planning/artifact_refresh_planner.py`
* `tests/test_artifact_refresh_planner.py`

要求：

* 决定哪些制品需要刷新
* 避免不必要的重新计算
* 明确标记过时制品

验收：

* 制品刷新决策正确

### Task 3.8：EditingPlanValidationNode

文件：

* `backend/app/agents/editing_planning/editing_plan_validation.py`
* `tests/test_editing_plan_validation.py`

要求：

* 验证编辑计划一致性
* 确保 clip durations 有效
* 确保 segment boundaries 存在
* 确保可以生成 render job

验收：

* 无效计划被拒绝

### Task 3.9：EditingStateUpdateNode

文件：

* `backend/app/agents/editing_planning/editing_state_update.py`
* `tests/test_editing_state_update.py`

要求：

* **原子提交 patch 和刷新的制品**
* **通过 `state_version` 强制执行乐观锁定**
* 更新 artifact status 和 `needs_refresh` flags
* 必需的一致性检查：`base_state_version == current_state_version`

验收：

* 原子提交成功
* 状态冲突时触发 StateConflictRecoveryFlow

### Task 3.10：StateConflictRecoveryFlow

文件：

* `backend/app/agents/editing_planning/state_conflict_recovery.py`
* `tests/test_state_conflict_recovery.py`

要求：

* ReloadEditingStateNode 重新加载当前状态
* RebasePatchNode 尝试将 patch 变基到新版本
* ConflictResolutionNode 决定重试或请求用户输入

验收：

* 冲突解决后可以成功重试

### Task 3.11：Integrate Editing Planning Subgraph

文件：

* `backend/app/agents/coordinator_graph.py`（更新）
* `tests/test_editing_planning_subgraph.py`

要求：

* 将 11 个节点集成到 Coordinator Graph
* 支持 editing_only 和 retrieval_then_editing 路由

验收：

* E2E editing planning subgraph test 通过
* PlanDiffNode 生成最小 patch
* EditingStateUpdateNode 原子提交

## Phase 4：Media Processing Workflow DAG 和 Editing Execution Service

目标：

实现 Media Processing Workflow DAG 和 Editing Execution Service，确保依赖关系正确和渲染安全。

### Task 4.1：Media Workflow Control Nodes

文件：

* `backend/app/agents/media_workflow_control/media_workflow_trigger.py`
* `backend/app/agents/media_workflow_control/media_workflow_status.py`
* `backend/app/agents/media_workflow_control/media_workflow_result_read.py`
* `tests/test_media_workflow_control.py`

要求：

* MediaWorkflowTriggerNode 触发媒体处理工作流
* MediaWorkflowStatusNode 读取工作流状态
* MediaWorkflowResultReadNode 读取工作流结果
* **不在 LangGraph nodes 内直接执行重型媒体处理**

验收：

* 只触发、轮询、读取和总结工作流状态

### Task 4.2：Media Processing Workflow DAG

文件：

* `backend/app/workflows/media_dag.py`
* `tests/test_media_dag.py`

要求：

* 定义 DAG 依赖关系：ASRTask 依赖 AudioExtractionTask、OCRTask/CaptionTask 依赖 FrameExtractionTask、SegmentBuilderTask 依赖 ASR/OCR/Caption/SceneShot、TextEmbeddingTask 依赖 segment text、VisualEmbeddingTask 依赖代表帧、IndexingTask 依赖 segment + embeddings + metadata
* 支持部分成功状态

验收：

* **任务依赖排序正确**
* **不在 embeddings 前运行 indexing**
* **不在 audio extraction 前运行 ASR**
* **不在 frame extraction 前运行 OCR/Caption**

### Task 4.3：Export / Render Control Nodes

文件：

* `backend/app/agents/export_render_control/render_readiness.py`
* `backend/app/agents/export_render_control/render_workflow_trigger.py`
* `backend/app/agents/export_render_control/render_workflow_status.py`
* `backend/app/agents/export_render_control/render_workflow_result_read.py`
* `tests/test_export_render_control.py`

要求：

* RenderReadinessNode 检查编辑计划是否可渲染
* RenderWorkflowTriggerNode 触发外部渲染作业
* RenderWorkflowStatusNode 轮询渲染状态
* RenderWorkflowResultReadNode 读取渲染输出和元数据
* **渲染不在 LangGraph nodes 内直接执行**

验收：

* 委托给外部 Editing Execution Service

### Task 4.4：Editing Execution Service

文件：

* `backend/app/editing_execution/clip_segment_deriver.py`
* `backend/app/editing_execution/ffmpeg_command_builder.py`
* `backend/app/editing_execution/render_job_runner.py`
* `backend/app/editing_execution/output_verifier.py`
* `backend/app/editing_execution/export_metadata_writer.py`
* `tests/test_editing_execution_service.py`

要求：

* ClipSegmentDeriver 将编辑计划转换为可执行 ClipSegment
* FFmpegCommandBuilder 构建安全的 FFmpeg 参数列表（使用参数列表，不使用 shell 字符串）
* RenderJobRunner 异步执行渲染作业，在隔离沙箱中运行
* OutputVerifier 验证渲染输出
* ExportMetadataWriter 持久化 EditedVideoArtifact

验收：

* FFmpeg 命令安全构建
* 渲染在隔离沙箱中执行
* 资源限制强制执行

### Task 4.5：Integrate Media and Render Workflows

文件：

* `backend/app/agents/coordinator_graph.py`（更新）
* `tests/test_media_render_workflows.py`

要求：

* 集成 Media Workflow Control Nodes
* 集成 Export / Render Control Nodes
* 支持 media_processing_required、media_processing_then_retrieval、media_processing_then_editing、export_only 路由

验收：

* E2E media processing workflow test 通过
* E2E render workflow test 通过

## Phase 5：生产基础设施和优化

目标：

引入生产检索、异步媒体处理和真实模型。

范围：

* Milvus 或 Qdrant
* Celery + Redis
* MinIO
* PostgreSQL
* real ASR/OCR/Caption/Embedding adapters
* Prometheus/Grafana/OpenTelemetry
* batch media workflow
* retrieval cache / embedding cache

原则：

* 每个外部依赖都必须有 deterministic mock path
* 不在 Phase 4 同时引入重型基础设施

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

* 项目定位明确为基于 LangGraph 的 Agentic Workflow 系统
* LangGraph Coordinator Graph 是顶层协调器
* Perception & Retrieval Subgraph 包含 8 个节点
* Editing Planning Subgraph 包含 11 个节点
* SearchQualityCheckNode 执行量化评估，不使用开放式 LLM 反思循环
* ConditionalRetryOrFinalize 强制执行重试预算
* MediaReadinessNode 不直接调用 Media Workflow Control Nodes
* PlanDiffNode 生成最小 patch，非全量重生成
* EditingStateUpdateNode 执行原子提交和版本检查
* 渲染在外部 Editing Execution Service 执行，不在 LangGraph nodes 内
* Media Processing Workflow DAG 遵循依赖关系
* 不再把自研 Agent Runtime 作为长期主线

## Risks And Tradeoffs

### 架构复杂度风险

风险：LangGraph Coordinator Graph 包含多个 subgraphs 和复杂路由。

缓解：
* 每个 subgraph 独立测试
* 条件路由有明确测试覆盖
* node trace 提供可观测性

### 状态一致性风险

风险：编辑状态并发变更导致冲突。

缓解：
* EditingStateUpdateNode 强制执行乐观锁定
* StateConflictRecoveryFlow 处理冲突
* state_version 追踪所有变更

### 渲染安全风险

风险：FFmpeg 命令注入或资源耗尽。

缓解：
* FFmpegCommandBuilder 使用参数列表，不使用 shell 字符串
* RenderJobRunner 在隔离沙箱中运行
* 强制执行资源限制：timeout、CPU/memory limit、disk quota

### 媒体处理依赖风险

风险：Media Processing Workflow DAG 依赖关系错误导致失败。

缓解：
* 明确定义 DAG 依赖关系
* 测试覆盖所有依赖约束
* 支持部分成功状态

### 检索质量风险

风险：开放式反思循环导致延迟和成本失控。

缓解：
* SearchQualityCheckNode 执行量化评估
* ConditionalRetryOrFinalize 强制执行重试预算
* 不允许无界反思循环
