# Nova Agent Platform 项目简介

## 项目目标

Nova Agent Platform 是一个 **基于 LangGraph 的 Agentic Multimodal Media Intelligence Platform**，面向视频素材理解、片段级检索、高光定位和创作建议生成。系统将多模态处理、Hybrid Retrieval、Rerank、Evidence Grounding 封装为 LangGraph nodes/tools，通过 `AgentState` 与 `StateGraph` 编排 Query Rewrite、Retrieval、Rerank、Creative Suggestion、Reflection 与 Final Answer 生成。

Nova 的核心卖点不再是“自研 Agent 框架”，而是：

```text
基于 LangGraph 做业务化二次开发，把视频理解和检索能力封装成可编排 Agent Workflow。
```

项目的工程定位是：

* 用 LangGraph 构建 Agent Orchestration Layer，将 Query Rewrite、Retrieval、Rerank、Creative Suggestion、Reflection 与 Final Answer 组织成可追踪 workflow。
* `MediaSegment` 是视频场景下的领域数据载体，用于承接多模态证据和检索结果。
* 用 Retrieval Engine 承载 BM25、Dense Retrieval、Metadata Filtering、Hybrid Fusion 与 Rerank。
* 用 Multimodal Pipeline 承载 ASR、OCR、Frame Caption、Scene/Shot Detection、Embedding 与 Highlight Scoring。
* 用 FastAPI 提供 API 层，后续用 Celery/Redis 承载重型媒体处理任务。

长视频、直播录屏和游戏高光素材都应被转换成可搜索、可解释、可复用、可创作的 `MediaSegment` 单元。每个 `MediaSegment` 保存时间边界、ASR 文本、OCR 文本、画面描述、标签、embedding 引用、运动分数、高光分数、元数据与 grounded evidence。

## 用户场景

### 场景 1：ToC AI Content Search Assistant

对标产品与场景包括 CapCut / 剪映、腾讯 IEG 内容工具、Insta360 / 影石内容工具、游戏集锦创作工具与短视频素材管理工具。

Demo 输入：

```text
帮我找适合做热血卡点的视频素材
```

LangGraph workflow 应执行：

```text
User Query
→ QueryRewriteNode
→ RetrievalNode
→ RerankNode
→ CreativeSuggestionNode
→ ReflectionNode
→ FinalAnswerNode
```

`QueryRewriteNode` 应将意图扩展为：热血、燃系、高能、快节奏、镜头切换明显、动作强、beat 匹配、团战、冲刺、反击、高潮片段。

期望输出：

* 推荐 `MediaSegment` 与 `start_time` / `end_time`。
* 高能片段、动作强片段、镜头切换明显片段。
* 基于 ASR、OCR、frame captions、tags、motion_score、highlight_score 的推荐理由。
* 推荐 BGM 风格、BPM 范围、转场建议与可选剪辑脚本。
* `node_trace` 与 `reflection_result`，用于展示 Agent Workflow 的可解释执行过程。

### 场景 2：ToB AI Media Workflow Copilot

对标场景包括企业 AI workflow agent、内容审核、素材管理、直播分析、营销素材生产和企业媒体资产自动分类。

Demo 输入：

```text
自动分析今天直播录屏并生成高转化切片
```

MVP 不要求真实企业级商品识别。可使用 ASR keywords、OCR keywords、frame captions、rule-based matching、mock product catalog 与手工配置 product dictionary。生产级 SKU recognition、企业商品库同步、复杂视觉商品检测和高精度转化预测后置。

期望输出：

* 候选短视频 `ClipCandidate`。
* 商品提及、价格/优惠信息、主播话术与互动证据。
* 自动分类、自动标签、直播摘要、标题建议、封面文案与剪辑建议。
* LangGraph `graph_run_id`、`thread_id`、`state_snapshot` 与 `node_trace`，便于复盘和调试。

## 核心平台层

Nova 由五个清晰平台层组成：

* API Layer：FastAPI，提供 upload、search、agentic search、segment detail、workflow status 等接口。
* Agent Orchestration Layer：LangGraph，负责 `AgentState`、`StateGraph`、nodes/tools、checkpointer、thread state 与 trace。
* Multimodal Pipeline：ASR Adapter、OCR Adapter、Caption Adapter、Embedding Adapter、Scene/Shot Adapter、Motion/Highlight Adapter。
* Retrieval Engine：BM25、Dense Retrieval、Metadata Filtering、Hybrid Fusion、Rerank、Evidence Grounding。
* Storage / Workflow Layer：Metadata DB、Object Storage、Vector DB；重型媒体任务后续由 Celery/Redis 执行。

LangGraph 放在 Agent Orchestration Layer。它不替代 Retrieval Engine、Multimodal Pipeline、Storage 或重型异步任务系统，而是编排这些能力。

## 核心价值主张

Nova 的价值是把不可直接操作的长视频转换成结构化媒体智能资产，并通过 LangGraph workflow 将查询理解、检索、重排、证据校验和创作建议串成可追踪、可测试、可扩展的 Agentic Workflow。

核心价值包括：

* 基于 `MediaSegment` 的片段级多模态理解。
* 基于 BM25 + dense + metadata + rerank 的多模态 Hybrid Retrieval。
* 基于 LangGraph 的 Agentic Search，而不是手写不可扩展的自研 Runtime。
* Evidence Grounding，确保推荐理由只引用真实证据。
* 创作导向输出：BGM、转场、脚本、标题、封面文案。
* ToC 与 ToB 共用同一套媒体理解、检索和 Agent Workflow 底座。
* 可观测与可评估：`node_trace`、`AgentState` snapshot、recall@k、MRR、nDCG、task success rate、tool accuracy、latency。

## MVP 非目标

MVP 与近期路线不做：

* 完整视频剪辑器时间线。
* 生产级 SKU recognition 与企业商品库匹配。
* 实时直播流处理。
* 大规模分布式视频处理集群。
* vLLM/SGLang 生产部署。
* Milvus/Qdrant/OpenSearch 作为必须运行依赖。
* 完整 Prometheus/Grafana/OpenTelemetry dashboard。
* 全自动成片渲染。
* 复杂长期记忆系统，例如长期用户偏好画像、跨会话 vector memory、自动个性化策略；Phase 3 仅支持 LangGraph thread/checkpoint 级别的轻量状态延续。

Phase 1/2 保留 deterministic local implementation 作为可测试垂直切片；Phase 3 将 Agentic Search 内部执行迁移到 LangGraph，用 AgentState 与 StateGraph 替换自研 agent execution path，并将现有 query rewrite、retrieval、rerank、creative suggestion、reflection 封装为 LangGraph nodes/tools。
