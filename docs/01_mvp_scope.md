# MVP 范围

## MVP 定位

Nova 的 MVP 不是“从零自研 Agent Runtime”，而是先打通可演示的媒体理解与检索 vertical slice，再迁移到 LangGraph 编排。MVP 应证明两件事：

1. 长视频可以被转换为可搜索、可解释、可复用、可创作的 MediaSegment。
2. Query Rewrite、Retrieval、Rerank、Reflection 与 Final Answer 的业务函数已经具备稳定输入输出，能够在 Phase 3 被包装为 LangGraph nodes/tools。

Phase 3 的目标是将这些稳定函数迁移到 LangGraph StateGraph 中执行。

第一条 vertical slice：

```text
Upload video
→ mock/simple media processing
→ build MediaSegment
→ local hybrid retrieval
→ search by user query
→ return ranked segments with timestamps, evidence reasons, and creative suggestions
```

Phase 3 开始，`POST /api/v1/search/agentic` 的内部执行应迁移为 LangGraph `StateGraph`。

## MVP 应包含的能力

### MediaSegment 与多模态 Pipeline

* 上传视频并创建 `Video` 记录。
* 使用 deterministic mock adapters 或轻量 adapter 生成 ASR、OCR、frame captions、tags、motion_score、highlight_score。
* 构建 `MediaSegment` 与 `SegmentEvidence`。
* 预留 ASR/OCR/Caption/Embedding/Scene/Shot/Motion/Highlight adapters，后续可替换为 Whisper、PaddleOCR、VLM、bge-m3、CLIP/SigLIP、PySceneDetect。
* 保证默认测试路径轻量、确定性、无需 GPU 和外部模型服务。

### Retrieval Engine

* Python BM25 / lightweight lexical retrieval。
* Deterministic local dense embedding stub。
* Metadata filtering。
* Hybrid score fusion。
* Rule-based rerank。
* Evidence-based reason generation。
* Evaluation utilities：recall@k、MRR、nDCG。
* Milvus/Qdrant/OpenSearch 作为未来替换选项，不是 MVP 必需运行依赖。

### Agentic Search

MVP 先允许 deterministic implementation，但目标结构必须对齐 LangGraph：

```text
AgentState
→ QueryRewriteNode
→ RetrievalNode
→ RerankNode
→ CreativeSuggestionNode
→ ReflectionNode
→ FinalAnswerNode
```

Phase 3 迁移后，`/api/v1/search/agentic` 应由 LangGraph workflow 内部执行，并返回 `graph_run_id`、`thread_id`、`state_snapshot` 与 `node_trace`。

### API

* `POST /api/v1/videos`
* `GET /api/v1/videos/{video_id}`
* `GET /api/v1/segments/{segment_id}`
* `POST /api/v1/search`
* `POST /api/v1/search/agentic`

`POST /api/v1/search` 保持普通检索兼容；`POST /api/v1/search/agentic` 表达 LangGraph agentic workflow 语义。

## ToC MVP 范围

Demo query：

```text
帮我找适合做热血卡点的视频素材
```

系统应返回：

* 推荐 `MediaSegment`。
* `start_time` / `end_time`。
* 中文推荐理由。
* grounded evidence。
* 推荐 BGM 风格、转场建议、剪辑 notes。
* Phase 1/2 返回 deterministic tool trace；Phase 3 迁移后返回 LangGraph node_trace / state_snapshot。

## ToB MVP 降级策略

Demo query：

```text
自动分析今天直播录屏并生成高转化切片
```

MVP 使用：

* ASR keywords。
* OCR keywords。
* frame captions。
* rule-based matching。
* mock product catalog。
* 手工配置 product dictionary。

推迟：

* 生产级 SKU recognition。
* 企业商品库同步。
* 复杂商品视觉检测。
* 高精度转化预测。
* 企业权限、审计、审批流。

## 暂缓内容

* 完整 LangGraph checkpoint 持久化可在 Phase 3 后半段完成。
* Celery/Redis 重型异步媒体任务在 Phase 4 引入。
* Milvus/Qdrant/OpenSearch 在 Phase 4 引入。
* vLLM/SGLang、真实 Whisper、PaddleOCR、CLIP/SigLIP 不作为默认测试依赖。
* 前端与完整剪辑器不属于当前 MVP 核心。

## MVP 成功标准

用户成功标准：

* 用户能上传视频并生成多个 `MediaSegment`。
* 用户能搜索“帮我找适合做热血卡点的视频素材”。
* 系统返回排序片段、时间戳、证据、推荐理由和创作建议。
* Agentic Search 响应体现 query rewrite、retrieval、rerank、reflection 与 final answer。
* 多用户访问隔离正确。

工程成功标准：

* 所有核心能力有 deterministic tests。
* `MediaSegment` 是 ingestion、retrieval、agent、API 的共享契约。
* Retrieval evaluation 能计算 recall@k、MRR、nDCG。
* Phase 3 LangGraph migration 有明确路径：现有函数被包装成 nodes/tools，而不是继续扩展自研 runtime。
