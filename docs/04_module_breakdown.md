# 模块拆分

## Backend Modules

建议包路径：`backend/app`。

* `api.routes.upload`：上传接口、文件校验、分片上传、object storage 写入、workflow 创建。
* `api.routes.search`：搜索接口、Agentic Search 编排、SSE streaming、搜索结果分页。
* `api.routes.segments`：片段详情、时间戳播放信息、证据查询、创作建议查询。
* `api.routes.workflows`：workflow status、retry、cancel、progress events。
* `api.routes.agent_runs`：Agent 执行记录、planner steps、tool calls、reflection 结果查询。
* `api.routes.assets`：视频资产列表、素材标签、素材状态、素材元数据。
* `api.routes.evaluations`：检索评估、Agent 评估、pipeline benchmark 查询。
* `core.config`：运行配置、mock mode、模型 adapter 配置、Redis、vector DB、storage、LLM serving、observability。
* `core.auth`：MVP 用户、session context、多用户隔离、简单 API key 或 mock auth。
* `core.errors`：统一错误码、业务异常、workflow 异常、tool 异常。
* `core.llm_gateway`：统一封装 Qwen、DeepSeek、Llama、vLLM、SGLang、本地 mock model。
* `domain.models`：Pydantic 领域模型与 DTO。
* `domain.enums`：视频状态、workflow 状态、segment 类型、tool 状态、检索通道类型。
* `db.repositories`：`Video`、`MediaSegment`、`SegmentEvidence`、`WorkflowRun`、`WorkflowTask`、`SearchQuery`、`AgentRun`、`AgentToolCall` 等仓储。
* `db.session`：数据库连接、事务管理、测试数据库 session。
* `db.migrations`：Alembic migrations。
* `storage.object_store`：MinIO/local object storage adapter，支持原视频、音频、抽帧图、缩略图、切片文件。
* `cache.redis_cache`：Redis cache、session cache、embedding cache key、retrieval cache key、workflow progress cache。
* `events.publisher`：workflow progress event、Agent streaming event、indexing event。
* `observability.logging`：basic logs、structured logs、task error metadata、retrieval latency records。
* `observability.metrics`：Prometheus metrics，记录 QPS、latency、cache hit rate、task failure rate。
* `observability.tracing`：OpenTelemetry trace，串联 upload、workflow、retrieval、agent、LLM 调用链路。

MVP 策略：

* Backend MVP 以 FastAPI 单体模块化结构开始，不急于拆微服务。
* 所有模块按未来微服务边界设计，后续可拆为 retrieval service、agent service、media pipeline service。
* MVP 必须保留 mock mode，保证没有 GPU、没有大模型服务时也能跑完整演示链路。
* 第一阶段优先保证：上传、workflow 状态、片段索引、搜索、片段详情、Agent 解释。

## Agent Runtime Modules

建议包路径：`backend/app/agents`。

* `agents.graph`：LangGraph 图定义，MVP 可先用确定性流程封装。
* `agents.state`：Agent state schema，保存 query、plan、tool calls、retrieval results、final answer。
* `agents.planner`：确定性 planner，避免一开始做完全自主多 Agent。
* `agents.query_rewrite`：中文创意查询改写与扩展。
* `agents.intent_parser`：识别 ToC 搜素材意图、ToB 直播分析意图、普通片段搜索意图。
* `agents.tool_registry`：注册 `ToolSpec`，维护工具名称、输入 schema、输出 schema、timeout、retry、cache policy。
* `agents.tool_calling`：执行 `AgentToolCall` 并记录输入输出、latency、error、retry 次数。
* `agents.tools.retrieval`：调用 Retrieval Engine。
* `agents.tools.segment_detail`：读取 `MediaSegment` 与 `SegmentEvidence`。
* `agents.tools.highlight`：调用高光检测结果与 highlight score。
* `agents.tools.creative_suggestion`：生成剪辑建议、BGM 风格、转场建议、短视频脚本。
* `agents.tools.workflow_copilot`：面向 ToB 的直播录屏分析、商品片段聚合、自动打 Tag、摘要生成。
* `agents.memory`：`MemoryItem` 存储，MVP 使用 Redis 或 PostgreSQL。
* `agents.memory.session_memory`：保存当前 session 查询历史、用户偏好、上下文。
* `agents.memory.vector_memory`：后续支持用户长期偏好向量化记忆。
* `agents.reflection`：检查时间戳、证据与理由是否完整，必要时修复。
* `agents.guardrails`：输出结构校验、工具结果一致性校验、避免无证据生成。
* `agents.response_streamer`：SSE streaming 输出，支持先返回检索进度，再返回候选片段和创作建议。
* `agents.schemas`：Agent 输入输出 schema。

MVP 策略：

* 从 deterministic planner + simple reflection 开始。
* 不从 fully autonomous multi-agent behavior 开始。
* Planner 第一版只支持三类任务：`creative_material_search`、`livestream_clip_generation`、`segment_detail_question`。
* Query Rewrite 对 `帮我找适合做热血卡点的视频素材` 扩展出热血、燃系、高能、快节奏、镜头切换明显、动作强、beat 匹配、团战、冲刺、反击、高潮片段等意图。
* Reflection 第一版只检查三件事：是否有片段、是否有时间戳、是否有证据支撑推荐理由。
* Creative Suggestion 第一版先用规则 + LLM 生成，不直接做真实 BGM 库检索。

## Retrieval Modules

建议包路径：`backend/app/retrieval`。

* `retrieval.schemas`：`SearchQuery`、`RetrievalCandidate`、`RetrievalResult`、`RerankResult`、`SegmentEvidence`。
* `retrieval.query_parser`：解析用户 query，生成结构化检索意图、过滤条件、召回通道配置。
* `retrieval.query_rewrite`：将自然语言 query 扩展为关键词 query、语义 query、视觉 query、标签 query。
* `retrieval.bm25`：Python BM25 或轻量 lexical index。
* `retrieval.sparse`：后续支持 Milvus sparse vector / BM25 function。
* `retrieval.dense`：Milvus/Qdrant adapter 与 in-memory test adapter。
* `retrieval.visual`：CLIP/SigLIP visual embedding 检索。
* `retrieval.metadata`：基于标签、视频来源、上传用户、时长、时间范围、商品名等 metadata 检索。
* `retrieval.multihop`：跨 ASR、OCR、caption、tags、embeddings 的多路召回。
* `retrieval.hybrid`：Hybrid Fusion 与候选去重。
* `retrieval.fusion`：weighted score fusion、reciprocal rank fusion、channel weight 配置。
* `retrieval.filters`：Metadata Filtering。
* `retrieval.rerank`：Rerank 接口与 MVP 简单 scorer，后续可替换为 cross-encoder reranker。
* `retrieval.personalization`：用户历史、内容热度、偏好标签加权，MVP 可先 mock。
* `retrieval.evidence`：Evidence Grounding，生成 `SegmentEvidence`，说明命中了 ASR、OCR、Caption、标签或视觉特征。
* `retrieval.explain`：基于证据生成中文理由。
* `retrieval.indexing`：MediaSegment index writer，负责写入 BM25 index、vector index、metadata index。
* `retrieval.index_lifecycle`：索引创建、更新、重建、删除、版本管理。
* `retrieval.cache`：retrieval cache key、TTL 与失效。
* `retrieval.evaluation`：recall@k、nDCG、MRR、latency 与 fixture evaluation。

MVP 选择：

* BM25 使用 Python 实现或轻量 index。
* OpenSearch 只作为未来替换选项。
* Dense retrieval 默认 in-memory adapter，后续启用 Milvus 或 Qdrant。
* Hybrid Fusion 可先使用 weighted score fusion 或 reciprocal rank fusion。
* Rerank 第一版使用规则打分：语义相关性、关键词命中、highlight score、motion score、shot change frequency。
* 检索结果必须返回 `segment_id`、`video_id`、`start_time`、`end_time`、`score`、`evidence`、`reason`。
* 不能只返回视频文件，必须返回片段级结果。

## Workflow Modules

建议包路径：`backend/app/workflows`。

* `workflows.dag`：DAG 定义。
* `workflows.orchestrator`：任务编排与状态推进。
* `workflows.tasks`：Celery task entry points。
* `workflows.retry`：重试策略、下游任务失效、幂等约束。
* `workflows.idempotency`：任务幂等 key、重复执行保护、部分失败恢复。
* `workflows.status`：面向 API 的状态聚合。
* `workflows.events`：进度事件。
* `workflows.dlq`：dead letter queue，记录无法自动恢复的失败任务。
* `workflows.compensation`：失败后的资源清理、索引回滚、临时文件清理。
* `workflows.scheduler`：后续支持批量任务、定时扫描直播录屏。
* `workflows.schemas`：`WorkflowRun`、`WorkflowTask`、`TaskStatus`、`TaskEvent` schema。

MVP workflow：

* `validate_media`
* `store_original_video`
* `extract_metadata`
* `extract_audio`
* `extract_frames`
* `segment_video`
* `run_asr`
* `run_ocr`
* `caption_frames`
* `detect_motion`
* `score_highlights`
* `build_segments`
* `embed_segments`
* `index_segments`
* `generate_video_summary`

MVP 策略：

* 使用 Celery + Redis 做异步任务队列。
* 每个 task 必须可重试、可记录状态、可追踪耗时。
* 每个 task 的输入输出尽量通过 object storage 和 DB 传递，避免大对象在队列中传输。
* DAG 第一版可以是固定流程，后续再支持动态 DAG。
* Workflow status 需要支持前端轮询或 SSE progress events。
* 对于 mock mode，ASR、OCR、Caption、Embedding task 必须能返回 deterministic fixture，便于 TDD。

## Multimodal Understanding Modules

建议包路径：`backend/app/media`。

* `media.ffmpeg`：音频、帧、缩略图与 metadata 抽取。
* `media.keyframes`：关键帧抽取策略，支持 fixed interval、scene boundary、shot boundary。
* `media.scene_detection`：PySceneDetect adapter 与 fixed-window fallback。
* `media.shot_detection`：更细粒度 shot boundary adapter。
* `media.asr`：Whisper/faster-whisper adapter 与 deterministic mock。
* `media.ocr`：PaddleOCR adapter 与 deterministic mock。
* `media.captioning`：Frame Caption adapter 与 deterministic mock。
* `media.embeddings.text`：bge-m3/jina adapter 与 deterministic mock。
* `media.embeddings.visual`：CLIP/SigLIP adapter 与 deterministic mock。
* `media.audio_features`：音量变化、节奏变化、能量峰值、静音区间。
* `media.motion`：motion score 与 motion tags。
* `media.highlights`：highlight scoring。
* `media.segment_builder`：构建 `MediaSegment`、`SegmentEvidence` 与 `ClipCandidate`。
* `media.segment_merger`：合并 ASR、OCR、Caption、Scene、Shot 的时间轴，形成统一片段。
* `media.product_matching`：ToB MVP 的 mock product catalog、product dictionary 与 rule-based matching。
* `media.tagging`：自动生成内容标签、风格标签、商品标签、场景标签。
* `media.summarization`：视频摘要、片段摘要、直播商品讲解摘要。
* `media.content_safety`：ToB 后续内容审核预留，MVP 可 mock。
* `media.schemas`：ASRResult、OCRResult、FrameCaption、SceneBoundary、ShotBoundary、MediaSegmentBuildResult。

MVP 策略：

* Scene Detection 优先使用 PySceneDetect，失败时使用 fixed-window fallback。
* ASR、OCR、Caption、Embedding 均需要提供 deterministic mock adapter。
* MediaSegment 构建必须以时间轴对齐为核心，而不是简单拼接文本。
* 第一版 highlight score 可用规则计算：motion score、shot change frequency、audio energy、关键词命中。
* ToB 商品识别第一版不做复杂视觉商品识别，先使用 OCR + ASR + 商品词典匹配。
* ToC 创作建议第一版基于 segment evidence、motion score、highlight score 和 LLM 生成。

## Model Serving Modules

建议包路径：`backend/app/serving`。

* `serving.model_gateway`：统一模型调用入口，屏蔽 Qwen、DeepSeek、Llama、mock model、remote API、本地 vLLM/SGLang。
* `serving.llm_client`：LLM chat completion、function calling、structured output。
* `serving.embedding_client`：文本 embedding、视觉 embedding 调用封装。
* `serving.rerank_client`：reranker model 调用封装。
* `serving.vllm_adapter`：vLLM adapter，支持 batch inference、streaming、prefix cache 配置。
* `serving.sglang_adapter`：SGLang adapter，作为后续高性能 serving 选项。
* `serving.prompt_templates`：Query Rewrite、Creative Suggestion、Summary、Reflection、Tagging prompt。
* `serving.output_parser`：JSON output parser、schema validation、fallback repair。
* `serving.rate_limit`：模型调用限流、并发控制。
* `serving.cost_tracker`：记录 token usage、latency、model provider。

MVP 策略：

* 第一版不强制部署 vLLM 或 SGLang，可以先使用 mock model 或远程 API。
* 所有模型能力必须通过统一 `ModelGateway` 调用，避免业务代码直接依赖具体模型。
* Prompt 必须版本化，放入 `prompts/` 或 `serving/prompt_templates`。
* Structured output 必须做 schema validation，失败时走 repair 或 fallback。

## Evaluation and Benchmark Modules

建议包路径：`backend/app/evaluation`。

* `evaluation.fixtures`：固定测试视频、mock ASR/OCR/Caption、标准 query、标准答案。
* `evaluation.retrieval_metrics`：recall@k、precision@k、nDCG、MRR。
* `evaluation.agent_metrics`：task success rate、tool selection accuracy、tool execution success rate、reflection correction rate。
* `evaluation.multimodal_metrics`：ASR WER、OCR accuracy、caption relevance、clip similarity、highlight hit rate。
* `evaluation.latency_metrics`：upload latency、workflow latency、retrieval latency、rerank latency、LLM latency、end-to-end latency。
* `evaluation.benchmark_runner`：一键运行 benchmark。
* `evaluation.reporter`：生成 markdown/json benchmark report。
* `evaluation.datasets`：小规模 demo dataset 与人工标注样例。
* `evaluation.human_review`：人工评审结果记录，适合创作建议质量评估。

MVP 策略：

* 第一版至少提供 5 条固定 query 和 1-2 个 demo 视频 fixture。
* Retrieval 必须能跑 recall@k、MRR、latency。
* Agent 必须能测试是否调用了正确工具、是否返回时间戳、是否生成了有证据的理由。
* Workflow 必须能测试 task retry、失败状态、重新执行。
* Benchmark 报告可作为项目 README 和简历展示材料。

## Frontend Modules

建议包路径：`apps/web`。

* `app/upload`：上传页面。
* `app/search`：搜索页面。
* `app/segments/[segmentId]`：片段详情。
* `app/workflows/[workflowId]`：处理进度。
* `app/assets`：素材库页面。
* `app/agent-runs/[agentRunId]`：Agent 执行链路详情，展示 planner、tool calls、reflection。
* `components/upload-dropzone`：上传控件。
* `components/workflow-status`：任务状态。
* `components/workflow-timeline`：DAG 处理进度时间线。
* `components/search-box`：查询输入。
* `components/search-mode-toggle`：ToC 内容搜索 / ToB 工作流 Copilot 模式切换。
* `components/segment-result`：片段结果卡片。
* `components/segment-player`：按时间戳播放片段。
* `components/evidence-list`：证据展示。
* `components/creative-suggestion-panel`：BGM、转场、脚本、封面文案建议。
* `components/highlight-score-badge`：高光分数、运动强度、节奏匹配展示。
* `components/agent-trace-panel`：展示 Query Rewrite、Retrieval、Rerank、Reflection。
* `components/asset-tag-list`：素材标签展示。
* `components/livestream-summary-panel`：ToB 直播摘要、商品列表、高转化切片候选。
* `lib/api-client`：类型化 API client。
* `lib/sse-client`：SSE streaming client。
* `lib/types`：前端类型。
* `lib/timecode`：时间戳格式化、片段跳转工具。

前端 MVP 应服务演示链路：上传、状态、搜索、片段详情。不做完整剪辑器。

MVP 策略：

* UI 风格参考 Perplexity + 剪映，但不做完整时间线剪辑器。
* 搜索页需要突出 Agentic Search，而不是普通搜索框。
* 结果卡片必须展示：视频片段、时间点、推荐理由、证据来源、创作建议。
* ToC Demo 页面重点展示“热血卡点素材搜索”。
* ToB Demo 页面重点展示“直播录屏自动分析与高转化切片生成”。
* Agent trace 面板是加分项，可以展示项目的 Agent Runtime Platform 能力。