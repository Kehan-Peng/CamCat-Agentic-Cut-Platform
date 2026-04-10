# TDD 计划

## TDD 原则

实现阶段必须遵循 red-green-refactor。默认测试路径保持 deterministic、轻量、无外部模型依赖。真实 ASR、OCR、Caption、Embedding、Vector DB、LLM serving 测试使用 integration/nightly marker，不阻塞默认 CI。

核心测试重心：

```text
LangGraph Coordinator Graph tests
→ Intent Routing Layer tests
→ Perception & Retrieval Subgraph tests (8 nodes)
→ Editing Planning Subgraph tests (11 nodes)
→ Media Workflow Control tests
→ Export / Render Control tests
→ Editing Execution Service tests
→ Media Processing Workflow DAG tests
→ State Persistence tests
→ E2E tests
```

## Domain Model Tests

验证：

* `Video` 可创建、序列化，并保持用户隔离字段
* `MediaSegment.end_time > start_time`
* `MediaSegment.motion_score` 与 `highlight_score` 在 `0.0 - 1.0`
* `MediaSegment` 包含 ASR/OCR/caption/tags/evidence/model_versions
* `SegmentEvidence` 可表示 ASR、OCR、caption、tag、motion、highlight 证据
* `SearchQuery` 保存 query、filters、session、retrieval mode
* `RetrievalResult` 保存各通道分数、rank、reason、evidence
* `AgentState` 保存 LangGraph 执行状态并可稳定序列化
* `GlobalEditingState` 包含 state_version 和 artifact_status
* `EditingStatePatch` 包含 operations 和 base_state_version
* `GraphRun`、`NodeTrace`、`ReflectionResult`、`SearchQualityMetrics` 可序列化

## Intent Routing Layer Tests

### StateLoadNode

验证：

* 加载 `AgentState` 和可选的 `GlobalEditingState`
* 用户隔离正确
* 访问控制验证

### IntentClassificationNode

验证：

* 识别 retrieval_only、editing_only、retrieval_then_editing、media_processing_required、export_only、clarification_required
* 复合意图识别："帮我找热血片段，并剪成 30 秒短视频" → retrieval_then_editing
* 低置信度时路由到 clarification_required

### RouteDecisionNode

验证：

* 支持所有路由目标：retrieval_only、editing_only、retrieval_then_editing、media_processing_required、media_processing_then_retrieval、media_processing_then_editing、export_only、clarification_required、finalize_with_error
* 复合路由正确执行
* 路由决策记录在 node_trace

### FinalResponseNode

验证：

* 规范化成功、部分和失败的 subgraph 输出
* 聚合用户面向结果
* 保留向后兼容的 API 字段
* 不编造不可用的媒体、片段、证据或渲染制品

## Perception & Retrieval Subgraph Tests（8 个节点）

### MediaReadinessNode

验证：

* 检查视频或资产库是否已索引并可搜索
* 如果媒体未就绪，写入 `route_request` / `readiness status` 到 AgentState
* **不直接调用 Media Workflow Control Nodes**
* 返回 workflow_id、status 和 readiness metadata

### QueryRewriteNode

验证：

* 输入"帮我找适合做热血卡点的视频素材"会扩展出热血、燃系、高能、快节奏、镜头切换明显、动作强、beat 匹配、团战、冲刺、反击、高潮片段
* node 只写 `rewritten_query` 与 `expanded_queries`
* 空 query 返回 validation issue
* 不编造具体品牌、商品或视频来源

### HybridRetrievalNode

验证：

* 执行 BM25-like lexical search
* 执行 deterministic dense retrieval
* 应用 metadata filters
* 融合候选结果通过 hybrid score fusion
* 返回 retrieved_results 和 channel-level scores

### CandidateEvidenceAttachNode

验证：

* 附加 ASR、OCR、caption、tag、score、metadata 证据到候选结果
* 准备证据特征用于 reranking
* 不是最终答案 grounding 层

### RerankNode

验证：

* 对热血卡点 query，提升 `motion_score` / `highlight_score` 高的片段
* 使用 lexical score、dense score、evidence quality、tag match、motion score、highlight score、query intent 重排序
* 保留原始通道分数用于可解释性
* 排序稳定

### FinalEvidenceGroundingNode

验证：

* 构建最终 grounded evidence
* 确保 reasons 只引用真实证据
* 拒绝或标记 ungrounded explanations
* 证据来源：ASR chunks、OCR blocks、frame captions、tags、motion/highlight scores、metadata

### SearchQualityCheckNode

验证：

* **执行量化检索质量评估，不使用开放式 LLM 反思循环**
* 计算 quality_score、result_count、top_score、avg_topk_score、evidence_coverage、timestamp_coverage、diversity_score、query_match_score
* 最小质量指标：result_count >= min_results、top_score >= min_top_score、avg_topk_score >= min_avg_score、evidence_coverage >= min_evidence_coverage、timestamp_coverage == 1.0、grounding_passed == true
* 返回 passed、issues、retry_action、retry_reason

### ConditionalRetryOrFinalize

验证：

* **强制执行重试预算**
* 如果 passed，完成
* 如果 attempt_count >= max_retrieval_attempts，以部分结果或无结果解释完成
* 如果 latency_budget_exceeded，以最佳努力结果完成
* 如果 issue == no_results，放宽过滤器或重写查询
* 如果 issue == low_evidence_coverage，重新运行证据重检索或 grounding
* 如果 issue == low_semantic_match，重写查询
* 如果 issue == duplicate_results，多样性 rerank
* **不允许无界反思循环**

## Editing Planning Subgraph Tests（11 个节点）

### IntentToEditTaskNode

验证：

* 将用户指令转换为结构化编辑任务
* 区分 clip generation、subtitle editing、title/tag update、export request、style revision
* 示例指令："剪成 30 秒热血卡点短视频"、"把开头改得更抓人一点"、"第二段删掉"、"字幕更短"、"导出一个 TikTok 快节奏版本"

### EditingStateReadNode

验证：

* 加载 `GlobalEditingState`
* 加载 artifact statuses
* 加载 selected segments 和 previous editing decisions
* 验证用户所有权

### SegmentSelectionNode

验证：

* 选择候选片段进行编辑
* 重用检索结果（如果可用）
* 避免选择不可用或未授权的片段
* 返回 selected segment IDs、segment evidence summaries、selection reason

### PlanDiffNode

验证：

* **生成最小 state patch，不重新生成整个编辑计划**
* 输入用户指令："把开头改得更抓人一点，第二段删掉，字幕短一点"
* 输出 patch 包含：patch_id、base_state_version、operations、affected_artifacts、needs_refresh、requires_retrieval、requires_render
* 支持的操作：add_segment、remove_segment、replace_segment、reorder_segments、trim_segment、update_subtitle_style、update_title_style、update_bgm_style、update_transition_style、update_hook、update_clip_duration、mark_artifact_stale
* 只有用户明确要求"全部重来"时才允许完整重新生成，并标记 patch_type="full_regeneration"

### PatchValidationNode

验证：

* 验证操作模式
* 拒绝删除不存在的 clip segments
* 拒绝无效的 segment IDs
* 拒绝不安全或不支持的编辑操作
* 确保 `base_state_version` 存在

### SubtitleDraftNode

验证：

* 基于 selected segments 和 patch operations 生成或更新字幕草稿
* 尊重字幕样式约束

### ClipPlanNode

验证：

* 生成或更新镜头级编辑计划
* 将编辑意图转换为时间线级结构
* 当 patch 不影响时保留先前计划部分

### TitleTagNode

验证：

* 生成标题候选和标签
* 如果只依赖 selected segments，可与字幕草稿并行运行
* 如果依赖最终 clip 结构，必须等待 clip plan

### ArtifactRefreshPlannerNode

验证：

* 决定哪些制品需要刷新
* 避免不必要的重新计算
* 明确标记过时制品
* 制品：subtitle_draft、editing_plan、clip_segments、title_candidates、tag_candidates、edited_video、preview_video

### EditingPlanValidationNode

验证：

* 验证编辑计划一致性
* 确保 clip durations 有效
* 确保 segment boundaries 存在
* 确保引用指向可用的源媒体
* 确保可以生成 render job

### EditingStateUpdateNode

验证：

* **原子提交 patch 和刷新的制品**
* **通过 `state_version` 强制执行乐观锁定**
* 更新 artifact status 和 `needs_refresh` flags
* 必需的一致性检查：`base_state_version == current_state_version`
* 如果发生冲突：`state_conflict → ReloadStateNode → RebasePatchNode → Retry or AskUser`

## StateConflictRecoveryFlow Tests

验证：

* ReloadEditingStateNode 重新加载当前状态
* RebasePatchNode 尝试将 patch 变基到新版本
* ConflictResolutionNode 决定重试或请求用户输入
* 冲突解决后可以成功重试

## Media Workflow Control Tests

### MediaWorkflowTriggerNode

验证：

* 触发媒体处理工作流
* 返回 workflow_id 和初始状态
* **不直接执行重型媒体处理**

### MediaWorkflowStatusNode

验证：

* 读取工作流状态
* 返回 status、progress、metrics
* 支持部分成功状态

### MediaWorkflowResultReadNode

验证：

* 读取工作流结果
* 返回 searchable status 和 segment count
* 处理部分成功情况

## Export / Render Control Tests

### RenderReadinessNode

验证：

* 检查编辑计划是否可渲染
* 验证所有 clip segments 有效
* 验证源媒体可用

### RenderWorkflowTriggerNode

验证：

* 触发外部渲染作业
* 返回 render_job_id 和初始状态
* **不在 LangGraph node 内直接执行 FFmpeg**

### RenderWorkflowStatusNode

验证：

* 轮询渲染状态
* 返回 status、progress、error

### RenderWorkflowResultReadNode

验证：

* 读取渲染输出和元数据
* 返回 output_uri、preview_uri、duration、checksum

## Editing Execution Service Tests

### ClipSegmentDeriver

验证：

* 将验证的编辑计划转换为可执行 `ClipSegment` 记录
* 映射源时间线到输出时间线
* 确保 clip boundaries 有效

### FFmpegCommandBuilder

验证：

* 构建安全的 FFmpeg 参数列表
* **使用参数列表，不使用 shell 字符串**
* 验证所有输入和输出路径
* 限制过滤器到安全白名单
* 拒绝不安全的元数据

### RenderJobRunner

验证：

* 异步执行渲染作业
* 在隔离沙箱中运行
* 强制执行资源限制：timeout、CPU/memory limit、disk quota、output size limit
* 支持取消
* 支持重试策略

### OutputVerifier

验证：

* 验证渲染输出：file exists、file size > minimum threshold、duration matches expected range、codec readable、no zero-frame output、audio/video stream valid、checksum recorded、preview generation succeeded

### ExportMetadataWriter

验证：

* 持久化 `EditedVideoArtifact`
* 链接输出制品到 render job、editing session 和源媒体
* 更新 workflow artifact status

## Media Processing Workflow DAG Tests

验证：

* **任务依赖排序正确**
* **不在 embeddings 前运行 indexing**
* **不在 audio extraction 前运行 ASR**
* **不在 frame extraction 前运行 OCR/Caption**
* SegmentBuilderTask 依赖 ASR/OCR/Caption/SceneShot 可用性
* TextEmbeddingTask 依赖 segment text
* VisualEmbeddingTask 依赖代表帧
* IndexingTask 依赖 segment + embeddings + metadata
* 部分成功行为：partially_searchable、searchable_with_missing_ocr、searchable_with_missing_caption、searchable_with_text_only_embedding
* 重试和幂等性

## Retrieval Tests

验证：

* BM25-like lexical retrieval 支持中文 query
* Dense embedding interface 有 deterministic local implementation
* Hybrid fusion 合并 lexical 与 dense 候选
* Metadata filtering 支持 `video_id`、tags、min_highlight_score、min_motion_score
* Rerank 结合 lexical_score、dense_score、motion_score、highlight_score、tag match
* Evaluation utilities 计算 recall@k、MRR、nDCG

## Evidence Grounding Tests

验证：

* reason 只能引用存在的 ASR、OCR、caption、tag、score 或 metadata
* 没有 OCR evidence 时不能提到屏幕文字
* 没有 ASR evidence 时不能提到主播/角色说过某句话
* 没有高 motion score 时不能声称动作强
* Creative suggestion 必须能从 query intent 或 segment evidence 解释

## API Contract Tests

验证：

* `POST /api/v1/search/agentic` 返回 `graph_run_id`、`thread_id`、`state_snapshot`、`node_trace`、`intent`、`route_targets`、`rewritten_query`、`retrieved_segments`、`reranked_segments`、`search_quality_report`、`final_answer`、`creative_suggestions`
* `POST /api/v1/editing/sessions` 创建编辑会话
* `POST /api/v1/editing/sessions/{editing_session_id}/message` 发送编辑指令，返回 patch 和 node_trace
* `POST /api/v1/editing/sessions/{editing_session_id}/render` 触发渲染作业
* 缺失 `query_text` 返回 400
* 多用户隔离正确
* API 响应只返回可序列化结构，不暴露 embedding 向量本体
* 向后兼容性：不删除 Phase 2 客户端依赖的关键字段

## E2E Tests

### E2E Agentic Search with Composite Intent

验证：

* 上传视频
* 生成 `MediaSegment`
* 搜索"帮我找热血片段，并剪成 30 秒短视频"
* LangGraph Coordinator Graph 完整执行
* Intent 识别为 retrieval_then_editing
* Perception & Retrieval Subgraph 执行（8 个节点）
* Editing Planning Subgraph 执行（11 个节点）
* 返回非空 `reranked_segments`
* top result 与 high-energy/highlight 相关
* `search_quality_report.passed=true`
* `final_answer` 引用真实 segment id、timestamp、reason/evidence
* `editing_plan` 包含 clip_segments 和 artifact_status
* `GET /api/v1/segments/{segment_id}` 可读取返回片段

### E2E Editing Session with State Mutation

验证：

* 创建编辑会话
* 发送编辑指令："把开头改得更抓人一点，第二段删掉，字幕短一点"
* PlanDiffNode 生成最小 patch
* EditingStateUpdateNode 原子提交
* state_version 递增
* artifact_status 正确更新
* 发送第二条编辑指令
* 无状态冲突
* 模拟并发编辑导致状态冲突
* StateConflictRecoveryFlow 触发

### E2E Render Workflow

验证：

* 创建编辑会话
* 触发渲染作业
* RenderWorkflowTriggerNode 委托给外部服务
* 轮询渲染状态
* 渲染成功
* 读取渲染输出
* EditedVideoArtifact 持久化

### E2E Media Processing Workflow

验证：

* 上传未处理视频
* MediaReadinessNode 检测媒体未就绪
* 写入 route_request 到 AgentState
* Coordinator Graph 重新路由到 Media Workflow Control Nodes
* MediaWorkflowTriggerNode 触发媒体处理
* Media Processing Workflow DAG 按依赖顺序执行
* 所有任务成功
* 视频变为 searchable

## Test Execution Strategy

默认 CI：

* unit
* contract
* mock-backed integration
* retrieval evaluation small fixtures
* LangGraph Coordinator Graph tests
* Intent Routing Layer tests
* Perception & Retrieval Subgraph tests (8 nodes)
* Editing Planning Subgraph tests (11 nodes)
* Media Workflow Control tests
* Export / Render Control tests
* Editing Execution Service tests
* Media Processing Workflow DAG tests
* E2E mock vertical slice

Nightly / manual：

* real Whisper
* real PaddleOCR
* real CLIP/SigLIP
* Milvus/Qdrant
* Celery/Redis integration
* large video fixtures

MVP 完成标准：

* 默认 CI 全部通过
* E2E agentic search with composite intent 通过
* E2E editing session with state mutation 通过
* E2E render workflow 通过
* E2E media processing workflow 通过
* evidence hallucination rate = 0
* recall@k、MRR、nDCG 可本地运行
* SearchQualityCheckNode 执行量化评估，无开放式反思循环
* PlanDiffNode 生成最小 patch，非全量重生成
* 渲染在外部服务执行，不在 LangGraph nodes 内
* Media workflow 遵循 DAG 依赖
