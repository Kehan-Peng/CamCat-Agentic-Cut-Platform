# TDD 计划

## TDD 原则

实现阶段必须遵循 red-green-refactor。有行为的 production code 应先写失败测试，再写最小实现，再在测试保护下重构。MVP 默认使用 deterministic mock adapters，保证 ASR、OCR、caption、embedding、vector search、object storage 与 queue 在 CI 中可重复。

TDD 的目标不是为所有外部模型写重型测试，而是先锁定核心业务行为、数据契约、模块边界与第一条 vertical slice：

上传视频 → 抽取音频与关键帧 → 生成 ASR/OCR/caption mock evidence → 构建 `MediaSegment` → 写入检索索引 → 搜索片段 → Agent 返回时间戳、证据、推荐理由与创作建议。

默认 CI 只运行快速、确定性的测试。真实 ASR、OCR、caption、embedding、LLM serving 与 vector database 测试应放入 `model`、`integration` 或 `nightly` marker，不作为 MVP 默认阻塞项。

所有 Agent 输出必须满足 evidence-grounded 原则：

* 片段时间戳必须来自真实 `MediaSegment`。
* 推荐理由必须引用已有 ASR、OCR、caption、tag、score 或 metadata。
* BGM、转场和脚本建议可以由 LLM 生成，但必须与检索到的片段风格、motion score、highlight score 或 tags 有可解释关联。
* 不允许编造不存在的视频、片段、商品、SKU、字幕、屏幕文字或用户历史偏好。

所有 API、domain model、tool schema 与 workflow state machine 应优先通过 contract test 锁定，再进入模块实现。

## Unit Test Plan

### Domain Model Tests

验证：

* `Video` 必须包含 `video_id`、`user_id`、`source_type`、`storage_uri`、`status`、`duration`、`created_at`。
* `Video.status` 只能在 `uploaded`、`processing`、`indexed`、`searchable`、`failed` 等合法状态之间转换。
* `MediaSegment` 必须包含 `segment_id`、`video_id`、`start_time`、`end_time`。
* `end_time` 必须大于 `start_time`。
* `segment_id` 在同一 `video_id` 下必须唯一。
* `motion_score` 与 `highlight_score` 必须在 0 到 1。
* `asr_chunks`、`ocr_blocks`、`caption_frames` 可以保存 timestamped evidence。
* `representative_frame_uri`、`evidence_refs`、`model_versions` 能正确序列化。
* `SegmentEvidence` 能表示 ASR、OCR、caption、tag、motion、highlight 与 metadata 证据。
* `ClipCandidate` 能引用多个 `segment_ids` 并保存中文 reason。
* `SearchQuery` 能保存原始 query、query rewrite、expanded queries、filters、retrieval mode 与 user context。
* `RetrievalResult` 必须包含 `segment_id`、score、rank、evidence sources 与 reason。
* `AgentRun` 必须保存 planner steps、tool calls、final answer、status、latency 与 error。
* `WorkflowTask` 必须保存 task name、status、attempts、max_attempts、dependency list、input hash、output ref 与 error。
* 所有核心对象必须支持稳定 JSON 序列化与反序列化。

### API Contract Tests

验证：

* `POST /api/videos/upload` 能接收视频上传请求并返回 `video_id`、`workflow_run_id` 与初始状态。
* Upload API 对缺失文件、非法文件类型、超大文件、缺失 `user_id` 返回明确 validation error。
* `GET /api/videos/{video_id}` 返回视频 metadata、处理状态、duration、segment count 与 searchable 状态。
* `GET /api/workflows/{workflow_run_id}` 返回 workflow status、task statuses、attempts、errors 与 progress。
* `POST /api/search` 接收 query、filters、top_k、retrieval mode 与 session id。
* Search API 返回 `query_rewrite`、`expanded_queries`、`results`、`agent_answer` 与 `trace_id`。
* `GET /api/segments/{segment_id}` 返回 segment detail、时间戳、ASR/OCR/caption evidence、scores 与 frame preview。
* 所有 API 响应必须包含稳定的 error schema。
* 多用户场景下，用户 A 不能读取用户 B 的 `video_id`、`segment_id`、workflow 或 retrieval cache。
* API contract 测试应优先于具体 service 实现，用于锁定前后端协作边界。

### Query Rewrite Tests

验证：

* 中文查询 `帮我找适合做热血卡点的视频素材` 会扩展出热血、燃系、高能、快节奏、镜头切换明显、动作强、beat 匹配、团战、冲刺、反击、高潮片段。
* `query_rewrite` 保留原始创意意图，而不是只做关键词拆分。
* Query Rewrite 输出必须符合结构化 schema，包括 `intent`、`style_terms`、`visual_terms`、`motion_terms`、`audio_terms`、`filters` 与 `expanded_queries`。
* 空查询或过短查询返回明确 validation error。
* 无意义 query 应返回低置信度或 clarification-needed 状态，而不是强行扩写。
* Query Rewrite 输出可被记录到 `SearchQuery.query_rewrite` 与 `SearchQuery.expanded_queries`。
* ToB 查询 `自动分析今天直播录屏并生成高转化切片` 应识别为 livestream workflow intent，而不是普通素材搜索 intent。
* Query Rewrite 不应把用户未提到的具体品牌、商品、BGM 名称或视频来源编造进检索条件。

### Multimodal Adapter Tests

验证：

* FFmpeg adapter 能从 fixture video 中抽取音频文件路径。
* FFmpeg adapter 能按固定间隔抽取关键帧。
* frame sampling 在相同输入、相同配置下输出稳定。
* Scene Detection adapter 能返回 scene boundary list。
* Shot Detection adapter 能返回 shot boundary list。
* Scene / shot boundary 必须满足 `start_time < end_time`。
* Scene / shot boundary 不能超过视频 duration。
* Mock ASR adapter 返回 timestamped transcript chunks。
* Mock OCR adapter 返回 timestamped OCR blocks、bbox 与 confidence。
* Mock caption adapter 返回 frame-level captions。
* Mock motion adapter 返回 deterministic motion score。
* Mock embedding adapter 对相同输入返回稳定 embedding。
* 所有 adapter 失败时必须返回结构化错误，不允许静默吞掉异常。
* 所有 adapter 输出必须能被 `SegmentBuilder` 消费。

### Segment Builder Tests

验证：

* fixed-window segmentation 生成预期边界。
* scene-aware segmentation 能基于 scene boundary 生成片段。
* shot-aware metadata 能保存到对应 `MediaSegment`。
* ASR chunks 按时间重叠分配给对应片段。
* OCR blocks 按时间与帧分配给对应片段。
* caption frames 附着到最近片段。
* motion score 与 highlight score 在相同输入下稳定。
* `MediaSegment` 的 embedding text 以稳定顺序组合 ASR、OCR、caption 与 tags。
* 空 ASR、空 OCR 或空 caption 时仍能构建可检索 segment。
* 超短片段、重叠片段、跨边界 evidence 应按明确规则处理。
* Segment Builder 应保存每个 segment 的 `representative_frame_uri`。
* Segment Builder 不应在没有 evidence 的情况下生成虚假 tags。

### Retrieval Tests

验证：

* BM25 能返回中文 lexical match。
* Dense retrieval 返回最近向量。
* Multi-hop retrieval 能分别覆盖 ASR、OCR、captions、tags 与 embeddings。
* Hybrid Fusion 能去重同一 `segment_id` 的候选。
* Hybrid Fusion 分数排序稳定，并能解释 BM25 与 dense 分数来源。
* Metadata Filtering 能排除不匹配的 `source_type`、`video_id`、tags 与 `min_highlight_score`。
* Rerank 对热血卡点类查询能提升 `highlight_score` 与 `motion_score` 高的结果。
* Retrieval result ordering 在相关性接近时受 `highlight_score` 与 `motion_score` 合理影响。
* Retrieval result 必须保留各路召回来源，例如 `bm25`、`dense_text`、`visual_embedding`、`tag_match`、`metadata_filter`。
* Retrieval cache key 包含 `user_id`、`query_text`、filters 与 retrieval mode。
* Retrieval cache key 不允许跨用户复用私有素材结果。
* 新片段索引后，同用户或同视频相关 retrieval cache 能失效。
* 当 BM25 无结果时，dense retrieval 仍可返回语义相关候选。
* 当 dense retrieval 无结果时，BM25 与 metadata filtering 仍可返回候选。
* 当所有召回为空时，系统返回空结果与可解释原因，而不是生成虚假片段。

### Evidence Grounding Tests

验证：

* 推荐理由只能引用存在于 `asr_chunks`、`ocr_blocks`、`caption_frames`、tags、scores 或 metadata 的证据。
* 当没有 OCR 证据时，reason 不能提到屏幕文字。
* 当没有 ASR 证据时，reason 不能提到主播说过某句话。
* 当没有 caption evidence 时，reason 不能声称画面中出现了某个具体对象。
* 当没有高 motion score 时，reason 不能声称动作强。
* 当没有 high shot-change frequency 时，reason 不能声称镜头切换密集。
* 每个 `RetrievalResult` 至少包含一个 evidence source。
* Agent 生成的 BGM 风格必须能从 motion、highlight、tags 或 query intent 中解释。
* Agent 生成的转场建议必须能从 scene/shot/motion 特征中解释。
* Agent 生成的 editing script 不能引用不存在的画面、字幕、人物、商品或剧情。

### Agent Tests

验证：

* Planner 对创意搜索请求先调用 Query Rewrite，再调用 retrieval tool。
* Planner 对直播切片请求应调用 workflow status、segment retrieval、highlight detection 与 summary/tagging tools。
* Tool Registry 会拒绝未知工具。
* Tool Registry 能根据 schema 校验 tool input 与 output。
* Tool Calling 会记录 `AgentToolCall.input`、`output`、`status`、latency 与错误。
* Agent 对 ToC 查询输出 BGM 风格、转场建议与可选 editing script。
* Agent 对 ToB 查询输出高转化切片候选、商品识别、标签、摘要与置信度。
* Reflection 在缺少 timestamps、evidence 或 reasons 时触发 repair。
* Reflection 修复后仍不能编造不存在的 evidence。
* Agent 输出中的 `segment_id` 必须来自 retrieval tool 返回值。
* Agent 输出中的时间戳必须来自 `MediaSegment.start_time` 与 `MediaSegment.end_time`。
* Agent 在 tool failure 时应降级返回部分结果与错误说明，而不是整体崩溃。
* Agent 在 retrieval 结果为空时应说明无匹配片段，并给出可执行的搜索建议。
* Session memory 只能影响当前用户的个性化排序，不能污染其他用户结果。
* Long-term memory 在 MVP 中默认关闭或使用 mock，避免不可控状态影响测试稳定性。

### ToB Livestream Tests

使用 mock product catalog 与 product dictionary。

验证：

* 查询 `自动分析今天直播录屏并生成高转化切片` 会使用 livestream 相关 filters 或 workflow context。
* 商品识别可基于 ASR keywords、OCR keywords、frame captions 与 rule-based matching。
* 未命中 mock catalog 时应返回低置信度或未知商品，而不是编造 SKU。
* 同一商品在多个片段中出现时，系统能聚合商品相关 clips。
* 高转化切片应综合商品提及、价格/优惠 OCR、主播强调语气、互动词与 highlight score。
* 输出 `ClipCandidate`，包含 `segment_ids`、时间戳、reason 与 metadata。
* 自动分类应输出稳定 category，例如 `product_intro`、`discount_highlight`、`qa_interaction`、`call_to_action`。
* 自动打 Tag 不应包含无法从 evidence 推出的标签。
* Summary 必须基于 ASR/OCR/caption evidence 生成。
* 内容审核相关 mock rule 能标记敏感词、违规价格表达或低置信度片段。

### Workflow Tests

验证：

* DAG 顺序尊重依赖关系。
* 任务失败后按 `max_attempts` 重试。
* 成功的上游任务在 retry 时不重复执行，除非下游失效需要。
* 从指定任务 retry 会清理受影响的下游输出。
* Workflow status 正确聚合 task statuses、attempts 与 errors。
* 幂等任务在相同输入下产生相同输出。
* 每个 task 的 input hash 相同时可以跳过重复执行。
* 每个 task 的 output ref 必须可追踪到 object storage 或 database。
* Async queue worker 收到重复消息时不会重复创建 segment 或重复写索引。
* Workflow cancellation 能把未开始任务标记为 skipped。
* Workflow timeout 能写入结构化 error。
* WorkflowRun 完成后必须触发 index-ready 或 searchable 状态更新。

### Storage and Cache Tests

验证：

* Object storage adapter 能保存原始视频、音频、关键帧与中间结果 URI。
* 相同文件 hash 重复上传时可以复用已有 object 或返回明确去重行为。
* Metadata database 能保存 Video、MediaSegment、WorkflowRun、WorkflowTask 与 AgentRun。
* Embedding cache key 包含 model name、model version、input text hash 与 modality。
* Retrieval cache key 包含 user scope、query rewrite、filters、top_k、retrieval mode 与 index version。
* Agent response cache 不应缓存包含未授权私有视频的结果。
* 新增、删除或重新索引 segment 后，相关 cache 应失效。
* Redis 不可用时，系统应降级到无缓存模式，核心流程仍能运行。

### Observability Tests

验证：

* 每次 upload、workflow、search 与 agent run 都生成 `trace_id`。
* structured log 包含 `trace_id`、`user_id`、`video_id`、`workflow_run_id`、`agent_run_id`。
* Retrieval latency、rerank latency、agent latency、workflow task latency 能被记录。
* Prometheus metrics 能暴露 request count、error count、latency histogram、queue length 与 cache hit rate。
* Tool Calling 失败时 metrics 能记录 tool name、error type 与 retry count。
* 不允许在 log 中输出原始密钥、完整 token 或敏感用户数据。

### Frontend Component Tests

验证：

* Upload 页面能展示上传进度、处理状态与失败原因。
* Search 页面能输入中文 query 并展示 streaming 状态。
* 搜索结果卡片必须显示视频片段、时间戳、reason、score 与 evidence。
* 片段详情面板能展示 ASR、OCR、caption、tags 与 representative frame。
* ToC 输出区域能展示 BGM 风格、转场建议与 editing script。
* ToB 输出区域能展示商品、标签、摘要与 ClipCandidate。
* 空结果页面应展示可执行的改写建议。
* Workflow status 页面能展示 DAG task 状态。
* 前端不应展示用户无权限访问的视频或片段。

## Integration Test Plan

### Upload-to-Index Integration

使用 tiny fixture video 与 mock adapters。

验证：

* Upload API 创建 `Video` 与 `WorkflowRun`。
* Workflow 抽取音频与帧。
* Scene Detection 与 Shot Detection 产生 mock boundaries。
* Segment builder 至少创建一个 `MediaSegment`。
* Mock ASR/OCR/caption 产出 timestamped evidence。
* Mock motion adapter 产出 motion score。
* Mock embedding 产出 text/visual embeddings。
* BM25 与 dense index 收到片段。
* Metadata database 保存 Video、MediaSegment 与 WorkflowRun。
* Object storage 保存原视频、音频、frame 与中间结果。
* `Video.status` 最终变为 `searchable`。
* Workflow trace 中能看到每个 DAG node 的开始、结束与耗时。

### Search-to-Answer Integration

验证：

* Search API 接收 `帮我找适合做热血卡点的视频素材`。
* 返回 `query_rewrite` 与 `expanded_queries`。
* Multi-hop retrieval 覆盖 ASR、OCR、captions、tags 与 embeddings。
* Hybrid Fusion 与 Rerank 返回排序稳定的片段。
* Agent answer 引用真实 `segment_id`。
* Response 包含时间戳、证据、分数、中文 reason 与中文 summary。
* Response 包含 BGM 风格、转场建议与可选 editing script。
* Streaming search 事件顺序为 query_rewrite、retrieval、candidate、rerank、agent token、completion。
* Streaming 中断时服务端能释放资源并记录 trace。
* 空结果时返回明确原因与改写建议，不生成虚假片段。

### ToB Workflow Integration

使用 mock livestream video、mock product catalog 与 mock adapters。

验证：

* Search 或 workflow API 接收 `自动分析今天直播录屏并生成高转化切片`。
* 系统识别 livestream workflow intent。
* Workflow 能复用已有 searchable segments，避免重复跑完整视频处理。
* 商品识别输出 product candidates、confidence 与 evidence。
* Highlight detection 输出 candidate clips。
* Auto tagging 输出稳定 tags。
* Summary generation 基于 evidence。
* 最终返回高转化切片候选、时间戳、商品、标签、摘要与 reason。
* 未命中商品 catalog 时不编造 SKU。
* 输出结果可被前端切片卡片消费。

### Workflow Retry Integration

使用一次失败、二次成功的 mock task。

验证：

* 失败写入结构化 `error`。
* retry 增加 attempt。
* workflow 最终达到 `succeeded`。
* retry 成功后下游任务继续执行。
* 已成功且未失效的上游任务不会重复执行。
* 多次失败超过 `max_attempts` 后 workflow 进入 `failed`。
* 用户可以从失败 task 继续 retry。
* retry 后相关 cache 与下游 output ref 按规则失效。

### Multi-user Session Integration

验证：

* 用户 A 上传的视频不会出现在用户 B 的搜索结果中。
* 用户 A 的 retrieval cache 不会被用户 B 命中。
* 用户 A 的 session memory 不影响用户 B 的 rerank。
* 同一个用户在不同 session 中可以保留 session-specific context。
* API、workflow、agent run 与 logs 都能正确记录 user/session scope。

### End-to-End MVP Acceptance Test

使用一个 tiny fixture video 与 deterministic mock adapters。

验证完整闭环：

* 上传视频。
* Workflow 完成处理。
* 生成至少一个 `MediaSegment`。
* Segment 包含 ASR、OCR、caption、motion score、highlight score 与 embedding。
* Segment 被写入 BM25 与 dense index。
* 用户搜索 `帮我找适合做热血卡点的视频素材`。
* 系统返回至少一个片段。
* 返回结果包含 `segment_id`、`video_id`、`start_time`、`end_time`、score、reason 与 evidence。
* Agent 返回中文 summary、推荐 BGM 风格、转场建议与可选 editing script。
* 所有 reason 均通过 evidence grounding check。
* 整个流程在本地 mock 环境中可重复运行。

## Retrieval Evaluation Plan

构建小型标注 fixture：

* 10 到 30 个短视频或 synthetic `MediaSegment`。
* 查询覆盖热血卡点、燃系游戏、商品提及、OCR-heavy moment、直播卖点、高能片段、低运动文本片段与无结果查询。
* 每个 query 标注相关 `segment_id` 与 relevance grade。
* 每个 query 标注主要依赖 modality，例如 ASR、OCR、caption、visual embedding、tag 或 metadata。
* 每个 query 至少包含一个 hard negative，用于测试 rerank 与 evidence grounding。
* 标注文件使用稳定 JSONL 格式，便于 CI 和离线 benchmark 复用。

指标：

* recall@k。
* precision@k。
* nDCG。
* MRR。
* retrieval latency p50/p95。
* rerank latency p50/p95。
* ASR/OCR/caption/tag/embedding 分 modality accuracy。
* clip similarity。
* evidence coverage rate。
* hallucination rate。
* cache hit rate。

MVP 初始阈值：

* recall@5 >= 0.70。
* MRR >= 0.60。
* nDCG@5 >= 0.65。
* evidence coverage rate = 1.00。
* hallucination rate = 0。
* 本地 fixture p95 retrieval latency < 2s。
* mock-backed search-to-answer p95 latency < 5s。
* 每个返回结果至少有一个 evidence source。

评估对比实验：

* BM25 only。
* Dense only。
* BM25 + dense hybrid。
* Hybrid + metadata filtering。
* Hybrid + rerank。
* Hybrid + rerank + highlight/motion feature。

每次改动 Retrieval Engine、Query Rewrite、Rerank 或 Segment Builder 时，必须至少运行一次小型 retrieval benchmark，防止 recall、MRR 或 evidence coverage 回退。

## Test Execution Strategy

推荐 pytest markers：

* `unit`：无外部服务。
* `contract`：API schema、domain schema、tool schema 与 response schema。
* `integration`：本地容器或 in-memory adapters。
* `workflow`：DAG、queue、retry、status 与 idempotency。
* `retrieval`：BM25、dense、hybrid、rerank 与 benchmark fixture。
* `agent`：planner、tool calling、reflection 与 evidence grounding。
* `model`：真实 ASR/OCR/caption/embedding 模型。
* `frontend`：前端组件与交互测试。
* `e2e`：完整 upload-to-index 与 search-to-answer。
* `nightly`：真实模型、真实向量库、较大 fixture 与性能测试。

默认 CI 只跑：

* `unit`
* `contract`
* mock-backed `integration`
* mock-backed `workflow`
* mock-backed `retrieval`
* mock-backed `agent`

真实模型测试、真实 Milvus/Qdrant、真实 vLLM/SGLang、真实视频处理与较大 benchmark 手动或 nightly 执行。

推荐测试顺序：

1. Domain model tests。
2. API contract tests。
3. Adapter mock tests。
4. Segment builder tests。
5. Retrieval tests。
6. Evidence grounding tests。
7. Agent tests。
8. Workflow tests。
9. Upload-to-index integration。
10. Search-to-answer integration。
11. End-to-end MVP acceptance test。
12. Retrieval benchmark。

MVP 完成标准：

* 所有默认 CI 测试通过。
* E2E MVP Acceptance Test 通过。
* retrieval benchmark 达到初始阈值。
* Agent 输出无 evidence hallucination。
* 上传、处理、检索、推荐建议的第一条 vertical slice 可在本地稳定复现。
