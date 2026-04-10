# 领域模型

## 核心原则

本文件描述的是视频业务领域模型，不代表项目研发重点。**Nova 的研发重点是基于 LangGraph 的 Agent Workflow 编排**；MediaSegment 只是多模态视频场景中的核心业务对象，供 LangGraph nodes/tools 消费。

`MediaSegment` 是 Nova 最重要的领域抽象。长视频必须被转换为可搜索、可解释、可复用、可创作的 `MediaSegment`。LangGraph 不直接处理原始视频文件，而是通过 nodes/tools 消费 `MediaSegment`、`RetrievalResult`、`SegmentEvidence` 与 `AgentState`。

## AgentState

LangGraph 执行时状态，是核心状态模型。

核心字段：

* `graph_run_id`
* `thread_id`
* `user_id`
* `session_id`
* `query_text`
* `intent`
* `route_targets`
* `rewritten_query`
* `expanded_queries`
* `filters`
* `retrieved_segments: list[RetrievalResult]`
* `reranked_segments: list[RetrievalResult]`
* `creative_suggestions`
* `reflection_result`
* `final_answer`
* `node_trace`
* `errors`
* `top_k`
* `retrieval_mode`
* `search_scope`
* `agent_config`
* `route_request`（用于 MediaReadinessNode 触发重路由）
* `readiness_status`（用于媒体就绪状态）

规则：

* 每个 node 只读写自己负责的字段
* `state_snapshot` 可用于 API 响应、debug、checkpoint 和回放
* AgentState 是短暂的和可 checkpoint 的，不是持久化编辑的真实来源

## GlobalEditingState

编辑会话的持久化状态。

核心字段：

* `editing_session_id`
* `user_id`
* `video_id`
* `state_version`
* `current_goal`
* `selected_segments`
* `subtitle_draft`
* `editing_plan`
* `clip_segments`
* `title_candidates`
* `tag_candidates`
* `render_jobs`
* `artifact_status`
* `needs_refresh`
* `last_user_revision`
* `updated_at`

规则：

* `state_version` 用于乐观锁定
* `EditingStateUpdateNode` 必须执行原子提交和版本检查
* 状态冲突时触发 StateConflictRecoveryFlow

## Video

表示原始媒体资产。

核心字段：

* `video_id`
* `user_id`
* `workspace_id`
* `source_type`
* `filename`
* `storage_uri`
* `duration_seconds`
* `content_hash`
* `status`
* `metadata`
* `created_at`
* `updated_at`

规则：

* `Video` 不是检索最小单元
* 可搜索和可创作的最小单位是 `MediaSegment`

## MediaSegment

表示一个可检索、可解释、可复用、可创作的视频片段。

核心字段：

* `segment_id`
* `video_id`
* `user_id`
* `workspace_id`
* `start_time`
* `end_time`
* `asr_transcript`
* `asr_chunks`
* `ocr_text`
* `ocr_blocks`
* `frame_captions`
* `caption_frames`
* `representative_frame_uri`
* `visual_embedding_id`
* `text_embedding_id`
* `tags`
* `motion_score`
* `highlight_score`
* `rhythm_score`
* `commercial_value_score`
* `evidence_refs`
* `model_versions`
* `metadata`

规则：

* `end_time` 必须大于 `start_time`
* 推荐理由必须基于 ASR、OCR、caption、tags、scores 或 metadata 中真实存在的证据
* ToC 卡点剪辑主要关注 `motion_score`、`highlight_score`、`rhythm_score`
* ToB 直播切片主要关注商品证据、互动证据、`commercial_value_score`

## SegmentEvidence

表示 grounded evidence。

核心字段：

* `evidence_id`
* `segment_id`
* `video_id`
* `evidence_type`
* `text`
* `start_time`
* `end_time`
* `frame_uri`
* `bbox`
* `confidence`
* `source_model`
* `model_version`
* `metadata`

规则：

* Agent final answer、creative suggestion、rerank reason 都应优先引用 `SegmentEvidence`
* 不允许在没有证据的情况下声称 ASR、OCR、画面对象、商品或动作事实存在

## SegmentEmbedding

表示片段向量引用。

核心字段：

* `embedding_id`
* `segment_id`
* `video_id`
* `embedding_type`
* `embedding_scope`
* `model_name`
* `model_version`
* `dimension`
* `vector_collection`
* `vector_id`
* `content_hash`
* `metadata`

规则：

* 同一 `MediaSegment` 可以有 text、visual、audio、multimodal 多种 embedding
* 向量本体后续进入 Milvus/Qdrant，业务数据库只保存引用

## SearchQuery

表示一次搜索请求。

核心字段：

* `query_id`
* `user_id`
* `session_id`
* `query_text`
* `scenario`
* `query_rewrite`
* `expanded_queries`
* `filters`
* `top_k`
* `retrieval_mode`
* `include_agent_answer`
* `created_at`

规则：

* `query_text` 保留用户原始输入
* Agentic Search 中，`query_rewrite` 与 `expanded_queries` 由 `QueryRewriteNode` 写入 `AgentState`，并可回写到 `SearchQuery`

## RetrievalResult

表示排序后的片段结果。

核心字段：

* `result_id`
* `query_id`
* `segment_id`
* `video_id`
* `rank`
* `bm25_score`
* `dense_score`
* `metadata_score`
* `fusion_score`
* `rerank_score`
* `final_score`
* `matched_evidence_refs`
* `evidence`
* `reason`
* `debug_info`

规则：

* `reason` 必须基于 `matched_evidence_refs` 或 segment scores
* 多路召回应保存原始通道分数，避免不可解释

## GraphRun

表示一次 LangGraph workflow 执行。

核心字段：

* `graph_run_id`
* `thread_id`
* `user_id`
* `session_id`
* `graph_name`
* `graph_version`
* `status`
* `input`
* `state_snapshot`
* `node_trace`
* `error`
* `latency_ms`
* `created_at`
* `updated_at`

规则：

* `GraphRun` 是 LangGraph 执行的权威记录
* 替代过去以自研 `AgentRun` 作为唯一运行记录的设计

## NodeTrace

表示 LangGraph node 的执行记录。

核心字段：

* `node_trace_id`
* `graph_run_id`
* `node_name`
* `status`
* `input_summary`
* `output_summary`
* `error`
* `latency_ms`
* `started_at`
* `finished_at`

规则：

* `node_trace` 是 Agentic Search API 可观测性的核心
* 不在 trace 中输出敏感 token 或完整大对象

## WorkflowArtifactStatus

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

规则：

* `ArtifactRefreshPlannerNode` 决定哪些制品需要刷新
* `EditingStateUpdateNode` 更新制品状态

## MediaWorkflowRun

表示媒体处理工作流执行。

核心字段：

* `workflow_id`
* `video_id`
* `user_id`
* `workflow_type`
* `status`
* `progress`
* `metrics`
* `error`
* `created_at`
* `updated_at`

规则：

* Media Workflow Control Nodes 触发和监控此工作流
* 不在 LangGraph nodes 内直接执行重型媒体处理

## RenderJob

表示渲染作业。

核心字段：

* `render_job_id`
* `editing_session_id`
* `status`
* `input_clip_segments`
* `ffmpeg_args_ref`
* `sandbox_id`
* `output_uri`
* `error`
* `attempt`
* `created_at`
* `updated_at`

规则：

* Export / Render Control Nodes 触发和监控渲染作业
* 渲染在外部 Editing Execution Service 中执行，不在 LangGraph nodes 内

## ClipSegments

表示可执行的剪辑片段。

核心字段：

* `clip_segment_id`
* `editing_session_id`
* `source_segment_id`
* `start_time`
* `end_time`
* `order`
* `transition`
* `effects`
* `metadata`

规则：

* `ClipSegmentDeriver` 从编辑计划生成 ClipSegments
* `FFmpegCommandBuilder` 使用 ClipSegments 构建渲染命令

## EditedVideoArtifact

表示渲染输出制品。

核心字段：

* `edited_video_id`
* `editing_session_id`
* `render_job_id`
* `output_uri`
* `preview_uri`
* `duration_seconds`
* `checksum`
* `metadata`
* `created_at`

规则：

* `OutputVerifier` 验证渲染输出
* `ExportMetadataWriter` 持久化此制品

## EditingStatePatch

表示最小编辑状态变更。

核心字段：

* `patch_id`
* `base_state_version`
* `operations`
* `affected_artifacts`
* `needs_refresh`
* `requires_retrieval`
* `requires_render`

支持的操作：

```text
add_segment
remove_segment
replace_segment
reorder_segments
trim_segment
update_subtitle_style
update_title_style
update_bgm_style
update_transition_style
update_hook
update_clip_duration
mark_artifact_stale
```

规则：

* `PlanDiffNode` 生成最小 patch，非全量重生成
* 只有用户明确要求"全部重来"时才允许完整重新生成

## ReflectionResult

表示 ReflectionNode 的校验输出。

核心字段：

* `passed`
* `issues`
* `checked_segment_ids`
* `missing_evidence`
* `missing_timestamps`
* `ungrounded_reasons`
* `created_at`

规则：

* 只做 reflection-lite：校验 grounding、timestamps、evidence、answer completeness
* 不做复杂自主 repair loop

## SearchQualityMetrics

表示量化的检索质量评估。

核心字段：

* `quality_score`
* `result_count`
* `top_score`
* `avg_topk_score`
* `evidence_coverage`
* `timestamp_coverage`
* `diversity_score`
* `query_match_score`

规则：

* `SearchQualityCheckNode` 执行量化评估
* 不使用开放式 LLM 反思循环

## ClipCandidate

表示候选切片。

核心字段：

* `clip_candidate_id`
* `video_id`
* `user_id`
* `segment_ids`
* `start_time`
* `end_time`
* `clip_type`
* `score`
* `reason`
* `evidence_refs`
* `suggested_bgm_style`
* `transition_suggestions`
* `metadata`

规则：

* ToC 偏创作价值和节奏
* ToB 偏商品露出、讲解密度、互动强度和转化潜力
