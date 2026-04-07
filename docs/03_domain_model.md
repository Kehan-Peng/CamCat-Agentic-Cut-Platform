# 领域模型

## 核心原则

`MediaSegment` 是 Nova Agent Platform 最重要的领域抽象。系统应把长视频转换成可搜索、可解释、可复用、可创作的 `MediaSegment` 单元。Agent、Retrieval、Workflow、API 与前端都围绕 `MediaSegment` 工作。

核心原则：

* 以 `MediaSegment` 为最小检索与创作单元，而不是以完整视频为最小单元。
* 所有 ASR、OCR、Caption、Embedding、Tag、Highlight、Rerank 结果都应尽量落到 `MediaSegment` 上。
* 所有推荐理由、创作建议和 Agent 输出都必须能够追溯到 `SegmentEvidence`。
* Workflow 负责任务编排与状态追踪，Agent 负责意图理解、工具调用、结果整合与自我修正。
* Retrieval Engine 应同时支持文本检索、向量检索、多模态检索、metadata filtering 与 rerank。
* MVP 可以先实现轻量版本，但领域模型需要为后续 ToC 创作助手与 ToB 工作流 Copilot 预留扩展空间。

## Video

表示上传的原始媒体资产。

字段：

* `video_id`：唯一标识。
* `user_id`：所属用户。
* `workspace_id`：所属工作区，可为空；ToB 场景用于企业、团队或项目隔离。
* `source_type`：`upload`、`livestream_recording` 或 `game_highlight`。
* `title`：视频标题，可由用户提供或系统生成。
* `filename`：原始文件名。
* `storage_uri`：对象存储地址。
* `thumbnail_uri`：视频封面地址，可为空。
* `duration_seconds`：视频时长。
* `width`：视频宽度。
* `height`：视频高度。
* `fps`：帧率。
* `codec`：编码信息。
* `language`：主要语言，例如 `zh-CN`、`en-US`。
* `content_hash`：文件内容 hash，用于去重、缓存与幂等处理。
* `status`：`uploaded`、`processing`、`searchable`、`failed` 或 `deleted`。
* `ingest_workflow_id`：关联的视频入库 workflow。
* `error`：结构化错误信息，可为空。
* `metadata`：游戏、直播日期、语言、创作者、活动、商品、频道等 JSON 元数据。
* `created_at`：创建时间。
* `updated_at`：更新时间。

规则：

* `Video` 只表示原始媒体资产，不直接承担检索粒度。
* 可搜索、可推荐、可创作的最小单位应是 `MediaSegment`。
* `content_hash` 应作为视频级缓存与重复上传检测的重要依据。

## MediaAsset

表示从视频中派生出来的媒体文件或中间产物，例如音频、关键帧、缩略图、预览切片等。

字段：

* `asset_id`：唯一标识。
* `video_id`：所属视频。
* `segment_id`：所属片段，可为空。
* `asset_type`：`audio`、`frame`、`keyframe`、`thumbnail`、`preview_clip`、`subtitle` 或 `transcoded_video`。
* `storage_uri`：对象存储地址。
* `timestamp`：对应视频时间点，单位秒；对帧类资产有效。
* `start_time`：开始时间，单位秒；对音频或切片类资产有效。
* `end_time`：结束时间，单位秒；对音频或切片类资产有效。
* `width`：宽度，可为空。
* `height`：高度，可为空。
* `mime_type`：文件类型。
* `content_hash`：内容 hash。
* `metadata`：抽帧策略、转码参数、采样率等 JSON。
* `created_at`：创建时间。

规则：

* FFmpeg、PySceneDetect、OCR、Caption 等 Pipeline 产生的中间文件应落到 `MediaAsset`。
* `MediaSegment.representative_frame_uri` 可以引用 `MediaAsset` 中的关键帧地址。

## Scene

表示视频中的场景片段，通常由 Scene Detection 产生。

字段：

* `scene_id`：唯一标识。
* `video_id`：所属视频。
* `start_time`：场景开始时间。
* `end_time`：场景结束时间。
* `scene_index`：场景序号。
* `detection_method`：检测方法，例如 `pyscenedetect_content`。
* `confidence`：置信度。
* `metadata`：阈值、平均亮度、颜色变化等 JSON。
* `created_at`：创建时间。

规则：

* `Scene` 是视频结构理解结果，不一定直接用于检索。
* 一个 `Scene` 可以包含多个 `Shot` 与多个 `MediaSegment`。

## Shot

表示视频中的镜头片段，通常比 `Scene` 更细粒度。

字段：

* `shot_id`：唯一标识。
* `video_id`：所属视频。
* `scene_id`：所属场景，可为空。
* `start_time`：镜头开始时间。
* `end_time`：镜头结束时间。
* `shot_index`：镜头序号。
* `representative_frame_uri`：镜头代表帧地址。
* `motion_score`：0 到 1 的运动强度。
* `cut_score`：镜头切换强度。
* `metadata`：镜头变化、光流、画面节奏等 JSON。
* `created_at`：创建时间。

规则：

* `Shot` 用于支撑卡点、节奏、镜头变化和高光判断。
* `MediaSegment` 可以由一个或多个 `Shot` 聚合而成。

## MediaSegment

表示一个可检索、可解释、可复用、可创作的视频片段单元。

字段：

* `segment_id`：唯一标识。
* `video_id`：所属视频。
* `user_id`：所属用户，用于权限与过滤。
* `workspace_id`：所属工作区，可为空。
* `scene_id`：关联场景，可为空。
* `shot_ids`：关联镜头列表，可为空。
* `start_time`：片段开始时间，单位秒。
* `end_time`：片段结束时间，单位秒。
* `duration_seconds`：片段时长。
* `segment_type`：`scene_segment`、`shot_segment`、`fixed_window`、`highlight_candidate` 或 `manual_clip`。
* `asr_transcript`：片段级语音文本。
* `asr_chunks`：带时间戳的 ASR 证据块。
* `ocr_text`：片段级屏幕文字汇总。
* `ocr_blocks`：带时间戳、位置与置信度的 OCR 证据块。
* `frame_captions`：片段代表帧描述。
* `caption_frames`：带时间戳与 `frame_uri` 的画面描述证据。
* `representative_frame_uri`：片段代表帧地址。
* `preview_clip_uri`：片段预览视频地址，可为空。
* `visual_embedding_id`：视觉 embedding 引用。
* `text_embedding_id`：文本 embedding 引用。
* `multimodal_embedding_id`：多模态 embedding 引用，可为空。
* `tags`：标准化标签，例如 `gameplay`、`high_energy`、`product_demo`、`teamfight`。
* `motion_score`：0 到 1 的运动强度。
* `highlight_score`：0 到 1 的高光概率。
* `rhythm_score`：0 到 1 的节奏匹配度，用于卡点剪辑。
* `commercial_value_score`：0 到 1 的商业转化潜力，用于 ToB 直播切片。
* `evidence_refs`：指向 `SegmentEvidence` 的证据引用。
* `model_versions`：ASR、OCR、caption、embedding、rerank、highlight 等模型版本。
* `metadata`：source channel、product ids、language、game mode、event type 等 JSON。
* `created_at`：创建时间。
* `updated_at`：更新时间。

规则：

* 内部模块与 API 尽量传递 `MediaSegment` 或 `MediaSegmentRef`，避免散落的裸时间戳。
* 推荐理由必须基于 `asr_chunks`、`ocr_blocks`、`caption_frames`、tags、scores 或 metadata 中真实存在的证据。
* `highlight_score` 主要服务高光定位，`rhythm_score` 主要服务卡点剪辑，`commercial_value_score` 主要服务直播切片与转化分析。
* MVP 阶段可以先实现 `asr_transcript`、`ocr_text`、`frame_captions`、`text_embedding_id`、`tags` 和 `highlight_score` 的轻量版本。

## MediaSegmentRef

表示对 `MediaSegment` 的轻量引用。

字段：

* `segment_id`：片段唯一标识。
* `video_id`：所属视频。
* `start_time`：片段开始时间。
* `end_time`：片段结束时间。
* `representative_frame_uri`：代表帧地址，可为空。
* `title`：片段标题或系统生成摘要，可为空。

规则：

* API、Agent Tool、Retrieval Result 与前端列表页可以优先使用 `MediaSegmentRef`。
* 需要完整证据、embedding、metadata 或创作建议时，再读取完整 `MediaSegment`。

## SegmentEvidence

表示一个片段中可被引用的 grounded evidence。

字段：

* `evidence_id`：唯一标识。
* `segment_id`：所属片段。
* `video_id`：所属视频。
* `evidence_type`：`asr`、`ocr`、`caption`、`tag`、`motion`、`highlight`、`product`、`audio` 或 `metadata`。
* `text`：可展示证据文本。
* `start_time`：证据开始时间，可为空。
* `end_time`：证据结束时间，可为空。
* `frame_uri`：相关帧地址，可为空。
* `bbox`：OCR 或视觉检测位置，可为空。
* `confidence`：置信度。
* `source_model`：来源模型或规则。
* `model_version`：模型版本。
* `metadata`：额外证据信息，例如商品 ID、关键词、检测类别等 JSON。
* `created_at`：创建时间。

规则：

* 所有 Agent 推荐理由、Rerank 解释和创作建议都应优先引用 `SegmentEvidence`。
* 前端展示“为什么推荐这个片段”时，应从 `SegmentEvidence` 中取证据，而不是直接展示模型幻觉文本。

## SegmentEmbedding

表示片段的向量表示。

字段：

* `embedding_id`：唯一标识。
* `segment_id`：所属片段。
* `video_id`：所属视频。
* `embedding_type`：`text`、`visual`、`audio` 或 `multimodal`。
* `embedding_scope`：`segment`、`frame`、`caption`、`asr` 或 `ocr`。
* `model_name`：例如 `bge-m3`、`jina-embeddings-v3`、`clip`、`siglip`。
* `model_version`：模型版本。
* `dimension`：向量维度。
* `vector_collection`：向量库 collection 名称。
* `vector_id`：向量数据库中的主键或引用。
* `vector_uri`：向量数据库引用，可为空。
* `content_hash`：embedding cache key。
* `normalized`：是否已归一化。
* `metadata`：embedding 参数、截断策略、输入摘要等 JSON。
* `created_at`：创建时间。

规则：

* 同一个 `MediaSegment` 可以有多个 embedding，例如文本向量、视觉向量、多模态向量。
* `content_hash` 应由模型名、模型版本、输入内容和预处理参数共同决定，用于 embedding cache。
* 向量本体不建议直接存入业务数据库，应存储在 Milvus、Qdrant 等向量数据库中。

## SearchQuery

表示一次用户搜索请求。

字段：

* `query_id`：唯一标识。
* `user_id`：所属用户。
* `workspace_id`：所属工作区，可为空。
* `session_id`：交互会话。
* `query_text`：原始查询。
* `query_intent`：查询意图，例如 `material_search`、`highlight_search`、`clip_generation`、`asset_management`。
* `query_rewrite`：改写后的主查询。
* `expanded_queries`：扩展查询列表。
* `target_modalities`：目标检索模态，例如 `asr`、`ocr`、`caption`、`visual`、`tag`。
* `filters`：metadata filters。
* `top_k`：返回数量。
* `retrieval_mode`：`bm25`、`dense`、`visual`、`multimodal` 或 `hybrid`。
* `retrieval_plan`：Agent 或规则生成的检索计划。
* `rerank_enabled`：是否启用 rerank。
* `include_agent_answer`：是否生成 Agent 答案。
* `created_at`：创建时间。

规则：

* `query_text` 保留用户原始表达，不应被覆盖。
* `query_rewrite` 用于主检索，`expanded_queries` 用于多路召回。
* `target_modalities` 用于控制检索通道，例如只搜字幕、只搜画面、或同时搜 ASR/OCR/Caption/Embedding。
* Agentic Search 场景下，`retrieval_plan` 应记录 Query Rewrite、Multi-hop Retrieval 与 Rerank 的计划。

## RetrievalResult

表示一个排序后的搜索结果。

字段：

* `result_id`：唯一标识。
* `query_id`：所属查询。
* `segment_id`：命中的片段。
* `video_id`：所属视频。
* `rank`：最终排序。
* `bm25_score`：关键词检索分数。
* `dense_score`：文本向量检索分数。
* `visual_score`：视觉向量检索分数。
* `metadata_score`：metadata filtering 或业务规则分数。
* `fusion_score`：多路召回融合分数。
* `rerank_score`：重排分数。
* `highlight_score`：片段高光分数。
* `motion_score`：片段运动分数。
* `rhythm_score`：节奏匹配分数。
* `commercial_value_score`：商业转化潜力分数。
* `matched_evidence_refs`：命中的 `SegmentEvidence` 引用。
* `evidence`：`SegmentEvidence` 列表或摘要。
* `reason`：基于证据的中文推荐理由。
* `debug_info`：召回通道、融合权重、rerank 特征等调试信息，可为空。
* `created_at`：创建时间。

规则：

* `reason` 必须基于 `matched_evidence_refs` 或 segment scores 生成。
* `debug_info` 默认不返回给普通用户，但可用于开发、评估和 review。
* 多路召回场景下，必须保留各通道分数，避免只保存最终分数导致不可解释。

## RerankTrace

表示一次 rerank 的特征、权重与排序过程。

字段：

* `rerank_trace_id`：唯一标识。
* `query_id`：所属查询。
* `rerank_model`：重排模型或规则名称。
* `rerank_version`：重排版本。
* `features`：使用的特征列表，例如语义相关、视觉风格、运动强度、节奏匹配、用户偏好等。
* `weights`：特征权重。
* `input_result_ids`：rerank 前的候选结果。
* `output_result_ids`：rerank 后的结果。
* `latency_ms`：耗时。
* `created_at`：创建时间。

规则：

* MVP 阶段可以用规则 rerank，但仍应记录 `RerankTrace`。
* 后续切换到 cross-encoder 或 LLM rerank 时，不应影响上层 API。

## WorkflowRun

表示一次 workflow 执行。

字段：

* `workflow_id`：唯一标识。
* `video_id`：关联视频。
* `user_id`：所属用户。
* `workspace_id`：所属工作区，可为空。
* `workflow_type`：例如 `upload_to_index`、`livestream_to_clips`、`reindex_video`。
* `dag_version`：DAG 版本。
* `trigger_type`：`user_upload`、`manual`、`scheduled` 或 `api`。
* `status`：`pending`、`running`、`succeeded`、`failed` 或 `cancelled`。
* `progress`：完成任务数、总任务数与百分比。
* `idempotency_key`：幂等键，用于防止重复执行。
* `metrics`：耗时、任务数、失败数、重试数等 JSON。
* `error`：结构化错误信息，可为空。
* `created_at`：创建时间。
* `updated_at`：更新时间。

规则：

* 视频上传、直播分析、重新索引都应通过 `WorkflowRun` 管理。
* `dag_version` 用于保证历史任务可追踪。
* `idempotency_key` 用于重复上传、重试和任务恢复。

## WorkflowTask

表示 DAG 中的一个异步任务。

字段：

* `task_id`：唯一标识。
* `workflow_id`：所属 workflow。
* `video_id`：关联视频。
* `segment_id`：关联片段，可为空。
* `task_type`：例如 `extract_audio`、`detect_scene`、`sample_frames`、`run_asr`、`run_ocr`、`generate_caption`、`build_segments`、`create_embeddings`、`index_segments`。
* `status`：`pending`、`queued`、`running`、`succeeded`、`failed`、`retrying` 或 `skipped`。
* `queue_name`：队列名称，例如 `video`、`asr`、`ocr`、`embedding`、`indexing`。
* `worker_type`：执行该任务的 worker 类型。
* `attempt`：当前尝试次数。
* `max_attempts`：最大重试次数。
* `depends_on`：上游任务。
* `input`：JSON 输入。
* `output`：JSON 输出。
* `cache_key`：任务缓存键，可为空。
* `idempotency_key`：任务幂等键。
* `error`：结构化错误信息。
* `metrics`：耗时、输入大小、输出大小、模型耗时等 JSON。
* `started_at`：开始时间。
* `finished_at`：结束时间。

规则：

* 每个 `WorkflowTask` 应尽量设计为幂等任务。
* 对 ASR、OCR、Embedding 等高成本任务，应支持 cache key。
* 失败任务必须保留结构化错误，便于前端展示、重试与 Grafana 观测。

## AgentRun

表示一次 Agent Runtime 执行。

字段：

* `agent_run_id`：唯一标识。
* `user_id`：所属用户。
* `workspace_id`：所属工作区，可为空。
* `session_id`：会话。
* `query_id`：关联查询。
* `agent_type`：例如 `content_search_agent`、`media_workflow_copilot`。
* `status`：`pending`、`running`、`succeeded`、`failed` 或 `cancelled`。
* `planner_trace`：规划步骤。
* `tool_calls`：`AgentToolCall` 列表。
* `memory_refs`：使用的 `MemoryItem` 引用。
* `reflection`：质量检查或修复记录。
* `output`：结构化答案。
* `final_answer`：面向用户展示的最终回答。
* `latency_ms`：端到端耗时。
* `token_usage`：输入、输出、总 token 数。
* `created_at`：创建时间。
* `updated_at`：更新时间。

规则：

* Agent 不直接处理视频文件，应通过 Tool 调用 Retrieval、Workflow、Segment、Clip 等能力。
* `planner_trace` 应保留任务拆解、工具选择和中间决策。
* `reflection` 用于记录 Agent 对结果质量的自检，例如证据是否充分、是否需要补检索、是否存在空结果。

## ToolSpec

表示 Agent 可调用工具的规格。

字段：

* `tool_name`：工具名。
* `tool_version`：工具版本。
* `description`：工具描述。
* `category`：`retrieval`、`workflow`、`multimodal`、`creation`、`memory` 或 `utility`。
* `input_schema`：输入 JSON schema。
* `output_schema`：输出 JSON schema。
* `timeout_seconds`：超时时间。
* `side_effects`：是否有副作用。
* `idempotent`：是否幂等。
* `cache_policy`：缓存策略。
* `retry_policy`：重试策略。
* `required_permissions`：所需权限。
* `observability_tags`：可观测标签。
* `enabled`：是否启用。

规则：

* Tool Registry 应基于 `ToolSpec` 管理工具，而不是在 Agent prompt 中硬编码工具。
* 有副作用的工具，例如创建 workflow、生成切片、写入标签，必须显式声明 `side_effects`。
* 高成本工具，例如 ASR、OCR、Embedding，应配置 cache 与 timeout。

## AgentToolCall

表示 Agent 的一次工具调用。

字段：

* `tool_call_id`：唯一标识。
* `agent_run_id`：所属 Agent run。
* `tool_name`：工具名。
* `tool_version`：工具版本。
* `input`：调用输入。
* `output`：调用输出。
* `status`：`pending`、`running`、`succeeded`、`failed` 或 `timeout`。
* `error`：错误信息。
* `latency_ms`：调用耗时。
* `retry_count`：重试次数。
* `created_at`：创建时间。
* `started_at`：开始时间。
* `finished_at`：结束时间。

规则：

* 每次工具调用都应可追踪、可复现、可评估。
* Tool calling 测试应覆盖工具选择是否正确、输入 schema 是否正确、异常是否被 Agent 正确处理。

## MemoryItem

表示会话或用户记忆。

字段：

* `memory_id`：唯一标识。
* `user_id`：所属用户。
* `workspace_id`：所属工作区，可为空。
* `session_id`：会话，可为空。
* `memory_type`：`preference`、`recent_query`、`retrieval_context`、`workflow_context` 或 `creative_style`。
* `content`：记忆内容。
* `embedding_id`：记忆向量引用，可为空。
* `importance`：重要性分数。
* `source`：记忆来源，例如用户显式设置、历史搜索、Agent 总结。
* `created_at`：创建时间。
* `updated_at`：更新时间。
* `expires_at`：过期时间，可为空。

规则：

* `session_id` 为空时表示长期用户记忆或工作区记忆。
* MVP 阶段可以先实现 session memory，后续再扩展 long-term memory 与 vector memory。
* 用户偏好类记忆应可被检索和覆盖，避免长期污染搜索结果。

## ClipCandidate

表示可用于创作或工作流输出的候选切片。

字段：

* `clip_candidate_id`：唯一标识。
* `video_id`：所属视频。
* `user_id`：所属用户。
* `workspace_id`：所属工作区，可为空。
* `segment_ids`：包含的片段列表。
* `start_time`：开始时间。
* `end_time`：结束时间。
* `duration_seconds`：切片时长。
* `clip_type`：`hot_cut`、`product_clip`、`game_highlight`、`summary_clip` 或 `manual_clip`。
* `score`：候选切片分数。
* `highlight_score`：高光分数。
* `commercial_value_score`：商业转化潜力分数。
* `reason`：推荐原因。
* `evidence_refs`：支撑该切片的证据引用。
* `suggested_bgm_style`：推荐 BGM 风格，可为空。
* `transition_suggestions`：转场建议。
* `target_platform`：目标平台，例如 `douyin`、`kuaishou`、`bilibili`、`xiaohongshu`，可为空。
* `metadata`：用途、商品、活动、分类等 JSON。
* `created_at`：创建时间。
* `updated_at`：更新时间。

规则：

* `ClipCandidate` 可以由一个或多个连续或相近的 `MediaSegment` 组成。
* ToC 场景中，`ClipCandidate` 更偏向创作价值、节奏和视觉风格。
* ToB 场景中，`ClipCandidate` 更偏向商品露出、讲解密度、互动强度和转化潜力。

## CreationSuggestion

表示面向内容创作的建议结果。

字段：

* `suggestion_id`：唯一标识。
* `clip_candidate_id`：关联候选切片，可为空。
* `segment_id`：关联片段，可为空。
* `suggestion_type`：`bgm`、`transition`、`script`、`title`、`cover_text`、`tag` 或 `summary`。
* `content`：建议内容。
* `reason`：生成该建议的原因。
* `evidence_refs`：支撑该建议的证据引用。
* `style`：创作风格，例如 `燃系`、`快节奏`、`高转化`、`讲解型`。
* `target_platform`：目标平台，可为空。
* `created_by`：`agent`、`rule` 或 `user`。
* `model_version`：生成模型版本，可为空。
* `created_at`：创建时间。

规则：

* BGM、转场、标题、封面文案、脚本建议不应散落在 `ClipCandidate.metadata` 中，正式输出应落到 `CreationSuggestion`。
* 每条建议都应尽量引用 `SegmentEvidence`，保证创作建议可解释。
* MVP 阶段可以先实现 `script`、`title`、`transition` 和 `bgm` 四类建议。

## TagDefinition

表示系统中的标准化标签定义。

字段：

* `tag_id`：唯一标识。
* `tag_name`：标签名。
* `tag_type`：`content`、`style`、`motion`、`product`、`risk`、`platform` 或 `business`。
* `description`：标签描述。
* `parent_tag_id`：父标签，可为空。
* `created_at`：创建时间。
* `updated_at`：更新时间。

规则：

* ToB 素材管理、自动分类和内容审核场景应使用标准化标签。
* 标签体系应支持层级结构，例如 `product` 下可细分为商品品类。

## TagAssignment

表示标签被分配到视频、片段或切片上的记录。

字段：

* `assignment_id`：唯一标识。
* `tag_id`：标签 ID。
* `target_type`：`video`、`segment` 或 `clip_candidate`。
* `target_id`：目标对象 ID。
* `confidence`：置信度。
* `source`：`rule`、`model`、`agent` 或 `user`。
* `evidence_refs`：证据引用。
* `created_at`：创建时间。

规则：

* `MediaSegment.tags` 可以保存常用标签快照，但正式标签分配记录应落到 `TagAssignment`。
* 人工修改标签时，应保留 `source=user` 的记录，便于后续评估自动打标质量。

## ProductMention

表示直播、带货或企业素材中的商品识别结果。

字段：

* `product_mention_id`：唯一标识。
* `video_id`：所属视频。
* `segment_id`：所属片段。
* `product_id`：商品 ID，可为空。
* `product_name`：商品名称。
* `brand`：品牌，可为空。
* `category`：商品类目，可为空。
* `price_text`：识别到的价格文本，可为空。
* `source`：`asr`、`ocr`、`vision`、`metadata` 或 `manual`。
* `evidence_refs`：证据引用。
* `confidence`：置信度。
* `created_at`：创建时间。

规则：

* ToB 直播切片场景中，商品识别结果应独立建模，避免只塞进 `metadata`。
* 商品相关切片的 `commercial_value_score` 应参考 `ProductMention`、主播讲解密度、优惠信息和互动信号。

## EvaluationRecord

表示一次评估记录。

字段：

* `evaluation_id`：唯一标识。
* `evaluation_type`：`retrieval`、`rerank`、`agent`、`workflow`、`multimodal` 或 `creation`。
* `target_id`：被评估对象 ID，例如 query、agent_run、workflow、segment 或 clip。
* `metrics`：评估指标，例如 recall@k、nDCG、MRR、task success rate、tool accuracy、latency、clip similarity 等 JSON。
* `dataset_name`：评估数据集名称，可为空。
* `model_versions`：相关模型版本。
* `created_at`：创建时间。

规则：

* Benchmark 不应只写在文档里，应有可落库的评估记录。
* MVP 阶段可以先对 SearchQuery 和 RetrievalResult 做离线评估，后续扩展到 Agent 与 Workflow。