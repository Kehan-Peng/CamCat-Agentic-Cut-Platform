# 领域模型

## 核心原则
本文件描述的是视频业务领域模型，不代表项目研发重点。Nova 的研发重点是基于 LangGraph 的 Agent Workflow 编排；MediaSegment 只是多模态视频场景中的核心业务对象，供 LangGraph nodes/tools 消费。`MediaSegment` 是 Nova 最重要的领域抽象。长视频必须被转换为可搜索、可解释、可复用、可创作的 `MediaSegment`。LangGraph 不直接处理原始视频文件，而是通过 nodes/tools 消费 `MediaSegment`、`RetrievalResult`、`SegmentEvidence` 与 `AgentState`。

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

* `Video` 不是检索最小单元。
* 可搜索和可创作的最小单位是 `MediaSegment`。

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

* `end_time` 必须大于 `start_time`。
* 推荐理由必须基于 ASR、OCR、caption、tags、scores 或 metadata 中真实存在的证据。
* ToC 卡点剪辑主要关注 `motion_score`、`highlight_score`、`rhythm_score`。
* ToB 直播切片主要关注商品证据、互动证据、`commercial_value_score`。

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

* Agent final answer、creative suggestion、rerank reason 都应优先引用 `SegmentEvidence`。
* 不允许在没有证据的情况下声称 ASR、OCR、画面对象、商品或动作事实存在。

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

* 同一 `MediaSegment` 可以有 text、visual、audio、multimodal 多种 embedding。
* 向量本体后续进入 Milvus/Qdrant，业务数据库只保存引用。

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

* `query_text` 保留用户原始输入。
* Agentic Search 中，`query_rewrite` 与 `expanded_queries` 由 `QueryRewriteNode` 写入 `AgentState`，并可回写到 `SearchQuery`。

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

* `reason` 必须基于 `matched_evidence_refs` 或 segment scores。
* 多路召回应保存原始通道分数，避免不可解释。

## AgentState

LangGraph 执行时状态，是 Phase 3 的核心状态模型。

核心字段：

* `graph_run_id`
* `thread_id`
* `user_id`
* `session_id`
* `query_text`
* `scenario`
* `filters`
* `rewritten_query`
* `expanded_queries`
* `retrieved: list[RetrievalResult]`
* `reranked: list[RetrievalResult]`
* `creative_suggestions`
* `reflection_result`
* `final_answer`
* `node_trace`
* `errors`
* `top_k`
* `retrieval_mode`
* `search_scope`
* `agent_config`

规则：

* 每个 node 只读写自己负责的字段。
* `state_snapshot` 可用于 API 响应、debug、checkpoint 和回放。

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

* `GraphRun` 替代过去以自研 `AgentRun` 作为唯一运行记录的设计，LangGraph 执行事实应以 `GraphRun` / `node_trace` 为准。

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

* `node_trace` 是 Agentic Search API 可观测性的核心。
* 不在 trace 中输出敏感 token 或完整大对象。

## ToolSpec

表示 LangGraph node/tool 可调用能力的规格。

核心字段：

* `tool_name`
* `tool_version`
* `description`
* `category`
* `input_schema`
* `output_schema`
* `timeout_seconds`
* `side_effects`
* `idempotent`
* `cache_policy`
* `required_permissions`

规则：

* Tool 应包装 Retrieval、Segment Detail、Creative Suggestion、Workflow Status 等业务能力。
* 有副作用的工具必须声明 `side_effects`。

## AgentToolCall

表示一次工具调用。

核心字段：

* `tool_call_id`
* `graph_run_id`
* `node_name`
* `tool_name`
* `input`
* `output`
* `status`
* `error`
* `latency_ms`

规则：

* Phase 3 中 tool calls 应挂在 `GraphRun` / `NodeTrace` 下。

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

* Phase 3 只做 reflection-lite：校验 grounding、timestamps、evidence、answer completeness。
* 不做复杂自主 repair loop。

## WorkflowRun / WorkflowTask

表示重型媒体任务执行。

`WorkflowRun` 字段：

* `workflow_id`
* `video_id`
* `user_id`
* `workflow_type`
* `status`
* `progress`
* `metrics`
* `error`

`WorkflowTask` 字段：

* `task_id`
* `workflow_id`
* `task_type`
* `status`
* `attempt`
* `max_attempts`
* `input`
* `output`
* `error`
* `metrics`

规则：

* LangGraph 用于 Agent workflow。
* Celery/Redis 后续用于重型 media workflow。

## MemoryItem

表示 session 或用户偏好记忆。

核心字段：

* `memory_id`
* `user_id`
* `session_id`
* `memory_type`
* `content`
* `embedding_id`
* `importance`
* `expires_at`

规则：

* MVP 可只支持 request-local/session-lite。
* 长期记忆后置，避免不可控状态污染测试。

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

* ToC 偏创作价值和节奏。
* ToB 偏商品露出、讲解密度、互动强度和转化潜力。
