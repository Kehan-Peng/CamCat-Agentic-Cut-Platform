# Nova Agent Platform 项目简介

## 项目目标

Nova Agent Platform 是一个面向视频内容理解、检索与创作的 **Agentic Multimodal Media Intelligence Platform**。它不是单一的视频搜索应用，也不是简单的视频 RAG Demo，而是一个以 **Agent Runtime Platform** 为底座、以 **MediaSegment** 为核心领域抽象、面向视频素材理解、片段检索、高光定位与创作建议生成的多模态智能平台。

Nova 的核心目标是支持用户上传视频、直播回放或游戏集锦，通过 ASR、OCR、视频抽帧、Scene/Shot Detection、Frame Caption、Motion Tagging、Embedding、Hybrid Retrieval、Rerank 与 LLM Agent，将原始视频转换为可搜索、可解释、可复用、可创作的结构化媒体资产。

系统由四个核心平台层组成：

* Agent Runtime Platform：负责 Planner、Query Rewrite、Tool Registry、Tool Calling、Session Memory、Long-term Memory、Vector Memory 与 Reflection。
* Multimodal Retrieval Engine：负责 BM25、Dense Retrieval、Hybrid Search、Metadata Filtering、Multi-hop Retrieval、Rerank 与 Evidence Grounding。
* Workflow Engine：负责 DAG、Async Queue、Task Orchestration、Retry、Task Status Tracking、Failure Recovery 与异步媒体处理任务编排。
* Multimodal Understanding Pipeline：负责 ASR、OCR、Scene Detection、Shot Detection、Frame Caption、Motion Tagging、Text Embedding、Visual Embedding、Highlight Scoring 与 Segment-level Indexing。

ToC 的 **AI Content Search Assistant** 与 ToB 的 **AI Media Workflow Copilot** 都应构建在这些平台能力之上。项目不是为两个场景分别写两套业务逻辑，而是通过统一的 `MediaSegment`、Retrieval Engine、Agent Engine 与 Workflow Engine 支撑不同应用形态。

Phase 0 的目标是先锁定规格、MVP 范围、架构、领域模型、模块边界、API 契约与 TDD 计划，然后再进入实现。整个项目开发过程应采用 AI Coding 工作流沉淀方法论：Spec First、Plan First、TDD First、Review First，并在每个阶段记录 AI 参与需求拆解、接口设计、测试生成、代码实现、重构审查与文档沉淀的过程。

Nova 最重要的领域抽象是 `MediaSegment`。长视频、直播录屏和游戏高光素材都应被转换成可搜索、可解释、可复用、可创作的 `MediaSegment` 单元。每个 `MediaSegment` 应包含时间边界、ASR 文本、OCR 文本、画面描述、视觉向量、文本向量、标签、运动分数、高光分数、元数据与可解释证据。

## 用户场景

### 场景 1：ToC AI Content Search Assistant

对标产品与场景包括 CapCut / 剪映、腾讯 IEG 内容工具、Insta360 / 影石内容工具、游戏集锦创作工具与短视频素材管理工具。

Demo 输入：

```text
帮我找适合做热血卡点的视频素材
```

期望系统行为：

* Agent 识别用户意图为“燃系 / 高能 / 快节奏 / 适合卡点剪辑”的素材搜索需求。
* Planner 将任务拆解为 Query Rewrite、Multi-hop Retrieval、Rerank、Creative Suggestion 与 Response Generation。
* Query Rewrite 扩展检索语义，例如：热血、燃系、高能、快节奏、动作强、镜头切换明显、beat 匹配、情绪爆发。
* Retrieval Engine 同时检索 ASR、OCR、Frame Caption、标签、元数据、Text Embedding 与 Visual Embedding。
* Rerank 结合语义相关性、视觉风格、运动强度、镜头切换频率、用户偏好与片段高光分数进行排序。
* Agent 输出结果时提供推荐理由，并说明证据来源。

期望输出：

* 推荐视频片段与时间戳。
* 高能片段、动作强片段、镜头切换明显片段。
* 推荐理由，并说明证据来自 ASR、OCR、画面描述、标签、运动分数、高光分数或向量相似度。
* 推荐 BGM 风格，例如 128-140 BPM 鼓点、电子燃曲、史诗感配乐等。
* 转场建议，例如闪白、速度拉伸、beat cut、match cut、镜头推近等。
* 可选的剪辑脚本，例如开头字幕、高潮段落文案、结尾引导语。

该场景的重点不是“返回几个视频”，而是返回可直接用于创作决策的片段级结果：

```text
片段时间：00:01:24 - 00:01:38
推荐理由：动作幅度大，镜头切换频率高，字幕中出现“冲刺”“最后一波”等高燃语义。
创作建议：适合放在高潮段落，搭配 130 BPM 电子鼓点，使用闪白 + 速度拉伸转场。
```

### 场景 2：ToB AI Media Workflow Copilot

对标场景包括企业 AI Workflow Agent、内容审核、素材管理、直播分析、营销素材生产、企业媒体资产自动分类与直播切片平台。

Demo 输入：

```text
自动分析今天直播录屏并生成高转化切片
```

期望系统行为：

* 对直播录屏运行视频入库 DAG。
* 使用 ASR 识别主播讲解、商品卖点、优惠信息与互动话术。
* 使用 OCR 识别画面中的商品名、价格、优惠券、活动信息、字幕与弹幕。
* 基于 ASR keywords、OCR keywords、frame captions、规则匹配、mock product catalog 与手工配置的 product dictionary 做 MVP 级商品识别。
* 结合语音强度、关键词密度、商品露出、互动话术、镜头变化与画面运动强度检测高光候选片段。
* 对片段进行自动分类与打标签，例如商品讲解、价格露出、优惠提醒、用户互动、主播强推荐、转化高光等。
* 生成直播摘要、商品维度摘要与候选短视频切片。
* 输出候选短视频 `ClipCandidate`，并给出推荐标题、封面文案、标签与剪辑建议。

期望输出：

```text
高转化切片 1：
时间：00:12:30 - 00:13:48
商品：XX 防晒霜
标签：限时优惠 / 主播强推荐 / 价格露出 / 用户互动高
摘要：主播重点讲解防晒指数、适用肤质和限时折扣。
建议标题：夏天通勤必备，这支防晒霜今天价格很香
建议封面文案：限时优惠 / 敏感肌可用 / SPF50+
```

生产级 SKU recognition、企业级商品库匹配、复杂商品检测、跨系统资产治理、内容合规审核规则引擎与实时直播流处理不属于 MVP，但系统架构应为这些能力预留扩展点。

## 核心价值主张

Nova 的价值是把不可直接操作的长视频转换成结构化媒体智能资产。用户不需要手动拖动时间线寻找素材；系统会把视频拆解成 `MediaSegment`，并通过多模态理解、混合检索、证据归因与 Agent 推理，把片段变成可搜索、可解释、可创作、可审核、可管理的单元。

核心价值包括：

* 片段级多模态理解：将视频拆解为带有 ASR、OCR、Frame Caption、视觉特征、运动特征、标签和高光分数的 `MediaSegment`。
* 多模态片段检索：结合语音、屏幕文字、画面描述、视觉 embedding、文本 embedding、运动强度、标签与元数据进行检索。
* Agentic Search：通过 Query Rewrite、Planning、Multi-hop Retrieval、Hybrid Fusion、Rerank、Evidence Grounding 与 Creative Suggestion 生成结构化答案。
* 创作导向输出：不仅返回搜索结果，还给出推荐理由、BGM 风格、转场建议、剪辑脚本与内容结构建议。
* 异步媒体工作流：长视频处理通过 DAG 与队列执行，支持任务状态追踪、失败重试、错误元数据记录与后续恢复。
* 双场景平台化：同一套 `MediaSegment` 与 Retrieval/Agent/Workflow 能力支撑 ToC 创作搜索和 ToB 媒体工作流。
* 工程可扩展性：MVP 可从单体服务起步，但架构上预留多用户 session、异步检索、streaming response、多级缓存、微服务拆分、模型服务化与可观测能力。
* 可量化评估：通过 recall@k、nDCG、MRR、retrieval latency、task success rate、tool accuracy、highlight hit rate、clip similarity 等指标验证系统效果。

Nova 的项目叙事应强调：

```text
用 Agent 把多模态理解、混合检索、视频切片和内容创作串成一个可执行工作流。
```

它既是多模态理解项目，也是检索推荐项目，也是 Agent Runtime 项目，同时也是 AI Coding 方法论沉淀项目。

## MVP 非目标

MVP 不应一次性实现完整平台。以下内容暂不做：

* 完整视频剪辑器时间线。
* 自动成片渲染、复杂转场与精确 BGM beat 对齐。
* 生产级 vLLM/SGLang 模型服务。
* 多个微服务独立部署。
* Go 版 retrieval service。
* 自训练 ASR/OCR/Embedding/Rerank 模型。
* 生产级 SKU recognition 与企业商品库匹配。
* 企业组织权限、计费、审计与资产治理后台。
* 实时直播流接入。
* 复杂内容审核策略引擎。
* 大规模分布式视频处理集群。
* 完整 Prometheus、Grafana、OpenTelemetry dashboard。
* 端到端自动生成可发布短视频成片。
* 大规模个性化推荐系统。

MVP 应优先完成第一条可演示的垂直闭环：

```text
上传视频
→ 提取音频与关键帧
→ Scene/Shot Detection
→ ASR/OCR/Frame Caption 的简单实现或 mock 实现
→ 构建 MediaSegment
→ 生成文本与视觉 embedding
→ 写入检索索引
→ 用户输入自然语言 query
→ Agent 进行 Query Rewrite
→ Hybrid Retrieval
→ Rerank
→ 返回片段时间戳、证据理由与创作建议
```

MVP 仍需要基础日志、workflow status tracking、task error metadata、retrieval latency records、benchmark hooks 与简单 evaluation scripts，以便后续扩展。

MVP 的判断标准不是功能数量，而是是否打通以下关键路径：

* 视频能被切成 `MediaSegment`。
* `MediaSegment` 能被多模态特征描述。
* 用户 query 能被 Agent 改写和规划。
* Retrieval Engine 能从多个信号中召回片段。
* Rerank 能给出排序依据。
* 系统能输出可解释的视频片段、时间戳和创作建议。
* 异步任务状态可追踪，失败信息可定位。
* 核心模块具备基础测试和可扩展的 benchmark 入口。
