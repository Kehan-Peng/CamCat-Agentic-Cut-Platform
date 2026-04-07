# 实施计划

## AI Coding Workflow

每个 milestone 都必须遵循：

```text
Spec → Plan → Tests → Implementation → Review → Refactor → Docs
```

本阶段只完成 Spec 与 Plan。Implementation 必须等文档复审通过后再开始。

实现策略：

* MVP 默认使用 deterministic mock adapters。
* 真实 ASR/OCR/Embedding/Caption 模型是 adapter implementations，可后续启用。
* 不从 fully autonomous multi-agent behavior 开始。
* Agent 从 deterministic planner、Query Rewrite、Tool Registry、Tool Calling 与 simple reflection 开始。
* MVP 不拆分大量微服务。
* 先在一个 backend repo 内保持模块边界，再按需要拆分服务。
* 所有核心模块必须先定义 interface、schema、fixture 与失败测试，再实现最小可用代码。
* 所有视频处理任务必须具备 status tracking、error metadata、retry 与幂等设计。
* `MediaSegment` 是 ingestion、retrieval、agent、workflow、API 与 frontend 的核心契约。

## Milestones

### Milestone 0：Repository Foundation

目标：

* 建立最小 monorepo 结构、测试框架与本地开发配置。
* 保证项目可以被新开发者一条命令启动。
* 为后续 Spec、Plan、TDD、Review 提供稳定工程基础。

流程：

```text
Spec → Plan → Tests → Implementation → Review → Refactor → Docs
```

输出：

* FastAPI skeleton。
* pytest 配置。
* 基础配置系统。
* health endpoint。
* `docker-compose.yml` 本地开发环境。
* `.env.example`。
* Makefile 或 task runner。
* pre-commit 配置。
* 基础 CI 草案。
* Redis、PostgreSQL、MinIO、Milvus/Qdrant 的本地配置草案。
* backend、frontend、docs、scripts、tests 的目录结构。
* `README.md` 本地启动说明。

验收标准：

* 本地可以启动 FastAPI。
* `/health` 返回正常状态。
* pytest 可以运行并通过基础测试。
* docker-compose 可以启动 Redis、PostgreSQL、MinIO 与向量数据库占位服务。
* 新开发者可以通过 README 完成项目启动。

### Milestone 1：Domain And Storage Foundation

目标：

* 实现核心领域模型与持久化边界。
* 明确 `MediaSegment` 作为视频理解、检索、Agent 输出与创作建议的统一核心对象。
* 建立数据库 schema、repository interface 与 object storage adapter。

输出：

* `Video`。
* `MediaSegment`。
* `SegmentEvidence`。
* `SegmentEmbedding`。
* `SegmentIndexRecord`。
* `SearchQuery`。
* `RetrievalResult`。
* `WorkflowRun`。
* `WorkflowTask`。
* `AgentRun`。
* `ToolSpec`。
* `AgentToolCall`。
* `MemoryItem`。
* `ClipCandidate`。
* `CreativeSuggestion`。
* `ProductMention`。
* `HighlightSignal`。
* Object storage adapter。
* Repository interfaces。
* 数据库迁移草案。
* Pydantic schema 与 ORM model 边界。
* 测试 fixtures。

核心设计约束：

* `MediaSegment` 必须包含 `video_id`、`segment_id`、`start_time`、`end_time`、ASR、OCR、caption、tags、motion score、highlight score、metadata 与 evidence。
* `SegmentEvidence` 用于保存 ASR/OCR/Caption/Metadata/Visual signal 的来源、置信度和时间范围。
* `SegmentEmbedding` 不直接耦合某个向量数据库，实现上通过 adapter 写入 Milvus/Qdrant 或 in-memory store。
* `WorkflowTask` 必须记录 task name、status、input、output、error、attempt、started_at、finished_at。
* 所有对象必须可以序列化为 API response，避免后续 frontend 接口反复修改。

验收标准：

* 核心领域模型测试通过。
* Repository interface 测试通过。
* Object storage adapter mock 测试通过。
* `MediaSegment` 可以从 fixture 构建并序列化。
* `WorkflowRun` 与 `WorkflowTask` 可以记录完整任务状态。
* 数据模型可以支持第一条垂直切片。

### Milestone 2：Upload-to-Segment Vertical Slice

目标：

* 将上传视频转换为 `MediaSegment`，默认使用 mock/simple adapters。
* 打通 Upload video → extract frames/audio → build MediaSegment 的最小链路。
* 保证视频处理链路可追踪、可重试、可恢复。

输出：

* Upload API。
* Video metadata extraction。
* FFmpeg metadata/audio/frame extraction。
* Fixed-window segmentation。
* Mock ASR。
* Mock OCR。
* Mock Frame Caption。
* Motion Tagging。
* Highlight Scoring。
* `MediaSegment` 与 `SegmentEvidence` builder。
* Workflow status tracking 与 task error metadata。
* 文件 checksum。
* Upload idempotency key。
* Segment provenance metadata。
* Task retry 与 partial failure handling。
* Fixture video 处理测试。

实现边界：

* MVP 使用 fixed-window segmentation，不强制先做 Scene Detection 与 Shot Detection。
* Scene/Shot Detection 作为增强 adapter 预留接口。
* Mock ASR/OCR/Caption 必须 deterministic，保证测试稳定。
* Motion Tagging 可以先基于帧差分或 mock signal。
* Highlight Scoring 可以先使用规则分数，不依赖真实模型。
* 视频文件存储在 MinIO 或本地 object storage adapter。
* 不在该 milestone 内实现完整 retrieval，只生成可索引的 `MediaSegment`。

验收标准：

* 上传一个 fixture video 后可以创建 `Video` 与 `WorkflowRun`。
* workflow 可以生成至少一个 `MediaSegment`。
* 每个 segment 包含 start/end timestamp、mock ASR、mock OCR、mock caption、motion score、highlight score 与 evidence。
* 失败任务可以记录 error metadata。
* 重复上传同一文件可以通过 checksum 或 idempotency key 处理。
* 所有输出可以被 Milestone 3 的 retrieval indexer 消费。

### Milestone 3：Retrieval Vertical Slice

目标：

* 将 `MediaSegment` 索引并可检索。
* 实现第一版片段级 hybrid retrieval。
* 支持用户用中文自然语言检索视频片段，并返回时间点、证据和推荐理由。

输出：

* Python BM25 / lightweight lexical index。
* In-memory dense retrieval test adapter。
* Milvus/Qdrant adapter interface。
* Multi-hop retrieval over ASR、OCR、captions、tags、embeddings。
* Hybrid Fusion。
* Metadata Filtering。
* Rerank simple scorer。
* Evidence Grounding。
* 中文 reason generation。
* Retrieval latency records 与 benchmark hooks。
* Indexing service。
* Retrieval cache key 设计。
* Embedding cache key 设计。
* Search result schema。
* Segment detail query。
* Evaluation fixture queries。

核心检索流程：

```text
SearchQuery
→ Query Normalize
→ Lexical Recall
→ Dense Recall
→ Metadata Filtering
→ Multi-hop Retrieval
→ Hybrid Fusion
→ Rerank
→ Evidence Grounding
→ Chinese Reason Generation
→ RetrievalResult
```

实现边界：

* MVP 可以先使用 Python BM25 与 in-memory dense adapter。
* Milvus/Qdrant 先实现 adapter interface 与本地配置，不强制接入生产级部署。
* Dense embedding 可以先使用 deterministic mock embedding，后续替换 bge-m3、jina-embeddings-v3、CLIP 或 SigLIP。
* Rerank 先使用 rule-based scorer。
* Evidence Grounding 必须指出命中来自 ASR、OCR、caption、tag 还是 visual signal。
* 中文 reason generation 必须 deterministic 或 snapshot-testable。

验收标准：

* 给定 fixture segments，可以通过 BM25 检索命中目标片段。
* 给定 semantic query，可以通过 dense adapter 命中目标片段。
* Hybrid Fusion 可以合并 lexical 与 dense 结果。
* Metadata Filtering 可以按 video_id、tag、time range、source type 过滤。
* Rerank 可以输出稳定排序。
* Search result 必须包含 segment_id、video_id、start_time、end_time、score、evidence、reason。
* recall@k、nDCG、MRR 的 evaluation hooks 可以运行。

### Milestone 4：Agentic Search Slice

目标：

* 用确定性 Agent Runtime 包装 retrieval，生成结构化创意建议。
* 实现 ToC 与 ToB 两条可演示 Agent workflow。
* 保持 Agent 行为可控、可测、可解释。

输出：

* Deterministic Planner。
* Query Rewrite。
* Tool Registry。
* Tool Calling。
* Retrieval Tool。
* Segment Detail Tool。
* Memory interface。
* Simple Reflection。
* ToC structured answer。
* ToB mock product catalog workflow answer。
* Creative Suggestion Generator。
* BGM Style Recommender。
* Transition Suggestion Generator。
* Editing Script Generator。
* Product Matching Tool。
* ClipCandidate Generator。
* AgentRun trace。
* ToolCall trace。
* Agent output schema。
* Agent snapshot tests。

ToC Agent 流程：

```text
User Query
→ Planner
→ Query Rewrite
→ Retrieval Tool
→ Segment Detail Tool
→ Rerank / Result Validation
→ Creative Suggestion Generator
→ Simple Reflection
→ Structured Answer
```

ToB Agent 流程：

```text
User Query
→ Planner
→ Workflow Status / Segment Query
→ Product Matching Tool
→ Highlight Candidate Retrieval
→ ClipCandidate Generator
→ Auto Tagging
→ Summary Generator
→ Simple Reflection
→ Structured Answer
```

实现边界：

* 不实现 fully autonomous multi-agent。
* Planner 使用 deterministic routing。
* Query Rewrite 输出结构化 query，不直接自由发挥。
* Tool Registry 使用显式 `ToolSpec`。
* Tool Calling 必须校验 input schema 与 output schema。
* Memory interface 先实现 session memory 与 mock vector memory。
* Reflection 只检查结果是否满足用户意图、是否有 evidence、是否有时间点和推荐理由。
* ToB 商品识别使用 mock product catalog、OCR keywords、ASR keywords 与 rule-based matching。

验收标准：

* 输入“帮我找适合做热血卡点的视频素材”，Agent 可以返回片段、时间点、推荐理由、BGM 风格、转场建议与剪辑脚本。
* 输入“自动分析今天直播录屏并生成高转化切片”，Agent 可以返回候选切片、商品信息、标签、摘要与推荐理由。
* 每次 AgentRun 可以追踪 planner decision、tool calls、retrieval results 与 reflection result。
* Tool Calling 失败时可以返回可解释错误。
* Agent 输出结构稳定，可被 frontend 渲染。
* 所有 Agent 行为可以通过 snapshot tests 验证。

### Milestone 5：Minimal Frontend

目标：

* 提供可演示的上传、状态、搜索与片段详情界面。
* UI 风格参考 Perplexity + 剪映，突出视频搜索、时间点定位、证据解释与创作建议。
* 不追求完整剪辑器，但必须能支撑 ToC 与 ToB Demo。

输出：

* Upload page。
* Workflow status page。
* Search page。
* Segment result list。
* Segment detail view。
* Evidence list。
* Video preview player。
* Timestamp jump。
* Agent reasoning panel。
* Creative suggestion panel。
* ToB clip candidate list。
* Basic frontend smoke tests。

界面结构：

```text
Left Panel: video library / uploaded files
Center Panel: search results / segment timeline / video preview
Right Panel: Agent answer / evidence / creative suggestions
Bottom Area: segment timestamps / clip candidates
```

实现边界：

* MVP 不实现完整视频剪辑时间线。
* 不实现真实 BGM 库。
* BGM 与 transition 先作为建议文本输出。
* 视频预览只需要支持跳转到 segment timestamp。
* 前端重点展示：片段、时间点、证据、推荐理由和创作建议。

验收标准：

* 用户可以上传视频。
* 用户可以查看 workflow 状态。
* 用户可以输入中文 query 并查看搜索结果。
* 用户可以点击结果跳转到对应时间点。
* 用户可以查看 ASR/OCR/Caption/tag evidence。
* 用户可以查看 ToC 创作建议与 ToB 切片建议。
* 前端 smoke tests 通过。

### Milestone 6：Evaluation And Hardening

目标：

* 建立第一条垂直切片的质量与可靠性检查。
* 让项目从 Demo 走向可量化评估。
* 为后续真实模型替换、向量数据库接入与性能优化建立 baseline。

输出：

* Retrieval evaluation fixtures。
* recall@k、nDCG、MRR。
* Latency records。
* Workflow retry tests。
* Basic logs。
* Simple evaluation scripts。
* Benchmark hooks。
* Agent task success fixtures。
* Tool accuracy fixtures。
* Cache hit rate 统计占位。
* P95 latency 统计占位。
* Error taxonomy。
* Demo dataset 说明。

搜索评估：

```text
query
→ expected segment ids
→ retrieved segment ids
→ recall@k
→ nDCG
→ MRR
```

Agent 评估：

```text
user task
→ expected tool sequence
→ actual tool sequence
→ expected answer fields
→ actual answer fields
→ task success
→ tool accuracy
```

Workflow 评估：

```text
task
→ expected retry behavior
→ actual retry behavior
→ status transition
→ error metadata
→ idempotency result
```

完整 Prometheus、Grafana 与 OpenTelemetry dashboard 推迟到 MVP 之后。

验收标准：

* 至少有一组 retrieval evaluation fixtures。
* recall@k、nDCG、MRR 可以本地运行。
* Agent tool sequence 可以测试。
* Workflow retry 与 error metadata 可以测试。
* latency records 可以输出到日志或 benchmark 文件。
* Review 阶段可以基于评估结果判断是否进入下一阶段。

### Milestone 7：Demo Packaging And Documentation

目标：

* 将 MVP 包装成可展示、可讲解、可写进简历和项目报告的完整闭环。
* 输出稳定 Demo 脚本、架构说明、AI Coding 方法论沉淀。

输出：

* ToC Demo script。
* ToB Demo script。
* Architecture diagram。
* Data flow diagram。
* README 更新。
* API usage examples。
* Evaluation report。
* AI Coding retrospective。
* Known limitations。
* Future roadmap。
* 简历项目描述初稿。

ToC Demo 脚本：

```text
Input:
“帮我找适合做热血卡点的视频素材”

Output:
- 视频片段
- 高能时间点
- 推荐理由
- 推荐 BGM 风格
- 转场建议
- 剪辑脚本
```

ToB Demo 脚本：

```text
Input:
“自动分析今天直播录屏并生成高转化切片”

Output:
- 候选切片
- 商品识别结果
- 自动标签
- 高光原因
- 摘要
- 标题建议
```

验收标准：

* 新用户可以根据 README 跑通 Demo。
* Demo 数据、Demo query 与期望输出稳定。
* 项目文档能解释系统设计、模块边界、评估指标和取舍。
* AI Coding 方法论有过程记录，而不是只写结论。

## Step-by-Step Implementation Order

1. 初始化 repo 结构与测试工具。
2. 创建 docker-compose、`.env.example`、Makefile 与基础 CI 草案。
3. 编写 health endpoint 失败测试。
4. 实现 FastAPI skeleton、配置系统与 health endpoint。
5. 编写领域模型失败测试。
6. 实现领域模型最小代码。
7. 编写 repository、database migration 与 object storage adapter 测试。
8. 实现 repository interface、migration 草案与 storage adapter。
9. 编写 upload API 测试。
10. 实现 upload API 与 `WorkflowRun` 创建。
11. 编写 upload idempotency、checksum 与重复上传测试。
12. 实现 checksum、idempotency key 与 object storage 写入。
13. 编写 workflow DAG 与 retry 测试。
14. 实现 workflow orchestration、status tracking 与 retry。
15. 编写 FFmpeg adapter fixture 测试。
16. 实现 metadata、audio、frames extraction。
17. 编写 segment builder 测试。
18. 实现 fixed-window segmentation 与 mock ASR/OCR/caption。
19. 实现 motion tagging、highlight scoring、`MediaSegment` builder。
20. 编写 embedding adapter 测试。
21. 实现 mock text/visual embeddings 与 cache key。
22. 编写 indexing service 测试。
23. 实现 segment indexing interface。
24. 编写 BM25、dense retrieval 与 metadata filtering 测试。
25. 实现 Python BM25、in-memory dense retrieval 与 filters。
26. 编写 multi-hop retrieval、hybrid fusion 与 rerank 测试。
27. 实现 multi-hop retrieval、Hybrid Fusion、Rerank。
28. 编写 evidence grounding 与 reason generation 测试。
29. 实现 `SegmentEvidence` 聚合与中文 reason。
30. 编写 Query Rewrite 与 creative Chinese query 测试。
31. 实现 deterministic Query Rewrite。
32. 编写 Agent Planner、Tool Registry 与 Tool Calling 测试。
33. 实现 deterministic Planner、Tool Registry 与 Tool Calling。
34. 编写 Reflection 与 AgentRun trace 测试。
35. 实现 simple reflection、AgentRun trace 与 ToolCall trace。
36. 编写 Search API integration test。
37. 实现 Search API 与 optional SSE streaming。
38. 编写 ToC creative suggestion 测试。
39. 实现 BGM style、transition suggestion 与 editing script generator。
40. 编写 ToB mock product catalog 测试。
41. 实现 ToB rule-based product matching 与 `ClipCandidate` 输出。
42. 编写 frontend smoke tests。
43. 实现最小 upload/search/status/detail UI。
44. 实现 video preview、timestamp jump、evidence panel 与 creative suggestion panel。
45. 编写 retrieval evaluation scripts 测试。
46. 实现 evaluation fixtures、metrics 与 benchmark hooks。
47. 编写 demo script 与 documentation checklist。
48. 整理 ToC / ToB Demo、README、架构图、评估报告与 AI Coding retrospective。
49. Review、Refactor、更新 Docs。

## First Vertical Slice

第一条垂直切片固定为：

```text
Upload video
→ extract frames/audio
→ ASR/OCR/caption mock or simple implementation
→ build MediaSegment
→ index into retrieval layer
→ search by user query
→ return segments with timestamps and reasons
```

边界：

* 默认 deterministic mock adapters。
* fixed-window segmentation 优先，Scene/Shot Detection 作为增强。
* Retrieval 先用 Python BM25 与 in-memory dense adapter。
* OpenSearch 不作为 MVP 必需组件。
* Agent 使用 deterministic planner，不做完全自主多 Agent。
* `MediaSegment` 是 ingestion、retrieval、agent、workflow、API 的核心契约。
* ToC Demo 优先于 ToB Demo，但 ToB 数据模型和输出 schema 需要提前预留。
* 所有输出必须带 evidence，不能只返回 LLM 生成文本。
* 所有耗时任务必须能通过 workflow status 查询。
* 所有 mock adapter 必须 deterministic，保证测试、评估与 Demo 可复现。

第一条垂直切片的最小用户体验：

```text
用户上传一个视频
→ 系统显示处理状态
→ 处理完成后生成若干 MediaSegments
→ 用户输入“帮我找适合做热血卡点的视频素材”
→ 系统返回相关片段、时间点、命中证据、推荐理由和创作建议
→ 用户点击片段可以跳转到视频对应时间点
```

## Risks And Tradeoffs

### 模型质量风险

Mock adapters 无法代表真实模型效果。缓解方式：使用 curated fixture videos，并通过 adapter 接口平滑替换真实模型。

### Retrieval 复杂度风险

Hybrid Search、Multi-hop Retrieval 与 Rerank 容易过早复杂化。缓解方式：先用 BM25、in-memory dense、metadata filters、简单 fusion 与简单 rerank，等 evaluation fixture 稳定后再增强。

### Workflow 可靠性风险

视频处理慢且容易失败。缓解方式：每个 task 记录 status、input、output、error、attempt、started_at、finished_at，并测试 retry、幂等与 partial failure recovery。

### 架构过度设计风险

平台目标是 microservice-friendly，但 MVP 不应拆成很多服务。缓解方式：先在一个 backend repo 内保持模块边界，保留 service interface，等性能瓶颈明确后再拆分。

### ToB 准确率风险

生产级商品识别难度高。缓解方式：MVP 使用 ASR keywords、OCR keywords、frame captions、rule-based matching、mock product catalog 与 product dictionary；生产级 SKU recognition 推迟。

### Agent 行为不稳定风险

全自主 Agent 可能不可控。缓解方式：MVP 使用 deterministic planner、显式 ToolSpec、受控 Tool Calling、schema validation 与 simple reflection。

### 前端复杂度风险

如果一开始实现完整剪辑器，会显著拖慢 MVP。缓解方式：前端只做上传、状态、搜索、视频预览、时间点跳转、证据展示与创作建议展示。

### 数据闭环风险

没有 evaluation fixtures 时，检索和 Agent 效果无法判断。缓解方式：从 Milestone 3 开始维护 query → expected segment 的小型评估集，并在 Milestone 6 固化指标。

### 性能风险

视频处理、embedding 与 retrieval 都可能造成较高延迟。缓解方式：MVP 先记录 latency hooks，使用 Redis cache、embedding cache 与 retrieval cache 的接口设计，完整性能优化推迟到 baseline 建立之后。

## Review Gate

在以下文档完成复审并被接受之前，不得开始实现代码。

Implementation must not begin until these documents are reviewed and accepted:

* `docs/00_project_brief.md`
* `docs/01_mvp_scope.md`
* `docs/02_system_architecture.md`
* `docs/03_domain_model.md`
* `docs/04_module_breakdown.md`
* `docs/05_api_contract.md`
* `docs/06_tdd_plan.md`
* `docs/07_implementation_plan.md`

复审标准：

* MVP 边界清晰，没有过度承诺真实模型效果。
* 第一条 vertical slice 可以在有限时间内完成。
* `MediaSegment` 作为核心契约贯穿 ingestion、retrieval、agent、workflow、API 与 frontend。
* 每个 milestone 都有可测试输出和验收标准。
* Agent 行为可控、可追踪、可评估。
* Retrieval 有明确 evaluation hooks。
* Workflow 有 status、retry、error metadata 与幂等设计。
* ToC Demo 与 ToB Demo 都可以基于同一底座解释。
* AI Coding Workflow 可以被 Superpowers 按 Spec、Plan、Tests、Implementation、Review、Refactor、Docs 执行。