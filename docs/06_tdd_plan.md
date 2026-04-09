# TDD 计划

## TDD 原则

实现阶段必须遵循 red-green-refactor。默认测试路径保持 deterministic、轻量、无外部模型依赖。真实 ASR、OCR、Caption、Embedding、Vector DB、LLM serving 测试使用 integration/nightly marker，不阻塞默认 CI。

Phase 3 后，Agentic Search 的测试重心从“自研 runtime 单函数测试”升级为：

```text
LangGraph node unit tests
→ AgentState transition tests
→ StateGraph integration tests
→ Checkpoint/thread tests
→ Reflection grounding tests
→ Backward compatibility tests
→ E2E agentic search tests
```

## Domain Model Tests

验证：

* `Video` 可创建、序列化，并保持用户隔离字段。
* `MediaSegment.end_time > start_time`。
* `MediaSegment.motion_score` 与 `highlight_score` 在 `0.0 - 1.0`。
* `MediaSegment` 包含 ASR/OCR/caption/tags/evidence/model_versions。
* `SegmentEvidence` 可表示 ASR、OCR、caption、tag、motion、highlight 证据。
* `SearchQuery` 保存 query、filters、session、retrieval mode。
* `RetrievalResult` 保存各通道分数、rank、reason、evidence。
* `AgentState` 保存 LangGraph 执行状态并可稳定序列化。
* `GraphRun`、`NodeTrace`、`ReflectionResult` 可序列化。

## LangGraph Node Unit Tests

### QueryRewriteNode

验证：

* 输入“帮我找适合做热血卡点的视频素材”会扩展出热血、燃系、高能、快节奏、镜头切换明显、动作强、beat 匹配、团战、冲刺、反击、高潮片段。
* node 只写 `rewritten_query` 与 `expanded_queries`。
* 空 query 返回 validation issue。
* 不编造具体品牌、商品或视频来源。

### RetrievalNode

验证：

* 从 `AgentState` 读取 rewritten query、filters、top_k。
* 调用 Retrieval Engine，而不是在 node 内实现检索逻辑。
* 返回 `retrieved_segments`。
* 用户 A 不会检索到用户 B 的 segment。

### RerankNode

验证：

* 对热血卡点 query，提升 `motion_score` / `highlight_score` 高的片段。
* 保留 lexical/dense/fusion/rerank 分数。
* 排序稳定。

### CreativeSuggestionNode

验证：

* 根据 top segments 的 evidence、tags、motion/highlight scores 生成 BGM、转场、editing notes。
* 不引用不存在的画面、字幕、人物、商品。

### ReflectionNode

验证：

* 缺少时间戳时 `passed=false`。
* 缺少 evidence 时 `passed=false`。
* reason 提到 OCR 但 segment 没有 OCR evidence 时失败。
* final answer 未覆盖返回片段时失败。
* reflection-lite 只返回 pass/fail/issues，不做复杂自主 repair。

### FinalAnswerNode

验证：

* 只基于 reranked segments 与 evidence 生成 final answer。
* final answer 包含 segment id、timestamp、reason/evidence。
* 空结果时返回明确无结果原因，而不是编造片段。

## LangGraph Graph Integration Tests

验证完整 `StateGraph`：

* Graph 节点顺序为 QueryRewriteNode → RetrievalNode → RerankNode → CreativeSuggestionNode → ReflectionNode → FinalAnswerNode。
* 每个 node 更新 `AgentState` 的预期字段。
* `node_trace` 记录 node name、status、latency、error。
* `graph_run_id` 与 `thread_id` 存在。
* 普通 grounded 查询 `reflection_result.passed=true`。
* 无结果查询不会生成虚假 segment。
* node failure 时 graph 返回结构化 error。

## Checkpoint / Session Tests

验证：

* 同一 `thread_id` 可恢复 state。
* 新一轮 query 可读取上一轮 session context，但不污染其他用户。
* checkpoint 中不保存敏感 token。
* MemorySaver 或 Redis/PostgreSQL checkpointer 可通过相同接口替换。

## Retrieval Tests

验证：

* BM25-like lexical retrieval 支持中文 query。
* Dense embedding interface 有 deterministic local implementation。
* Hybrid fusion 合并 lexical 与 dense 候选。
* Metadata filtering 支持 `video_id`、tags、min_highlight_score、min_motion_score。
* Rerank 结合 lexical_score、dense_score、motion_score、highlight_score、tag match。
* Evaluation utilities 计算 recall@k、MRR、nDCG。

## Evidence Grounding Tests

验证：

* reason 只能引用存在的 ASR、OCR、caption、tag、score 或 metadata。
* 没有 OCR evidence 时不能提到屏幕文字。
* 没有 ASR evidence 时不能提到主播/角色说过某句话。
* 没有高 motion score 时不能声称动作强。
* Creative suggestion 必须能从 query intent 或 segment evidence 解释。

## API Contract Tests

验证：

* `POST /api/v1/search` 保持 backward compatible。
* `POST /api/v1/search/agentic` 返回 `graph_run_id`、`thread_id`、`state_snapshot`、`node_trace`、`rewritten_query`、`retrieved_segments`、`reranked_segments`、`reflection_result`、`final_answer`、`creative_suggestions`。
* 缺失 `query_text` 返回 400。
* 多用户隔离正确。
* API 响应只返回可序列化结构，不暴露 embedding 向量本体。

## E2E Agentic Search Tests

验证：

* 上传视频。
* 生成 `MediaSegment`。
* 搜索“帮我找适合做热血卡点的视频素材”。
* LangGraph workflow 完整执行。
* 返回非空 `reranked_segments`。
* top result 与 high-energy/highlight 相关。
* `reflection_result.passed=true`。
* `final_answer` 引用真实 segment id、timestamp、reason/evidence。
* `GET /api/v1/segments/{segment_id}` 可读取返回片段。

## ToB Livestream Tests

使用 mock product catalog 与 product dictionary。

验证：

* 查询“自动分析今天直播录屏并生成高转化切片”识别为 livestream workflow intent。
* 商品识别基于 ASR keywords、OCR keywords、frame captions 与 rule-based matching。
* 未命中 mock catalog 时返回 unknown/low confidence，不编造 SKU。
* 输出 `ClipCandidate`，包含 segment ids、timestamps、reason、evidence。

## Test Execution Strategy

默认 CI：

* unit。
* contract。
* mock-backed integration。
* retrieval evaluation small fixtures。
* LangGraph node/graph tests。
* E2E mock vertical slice。

Nightly / manual：

* real Whisper。
* real PaddleOCR。
* real CLIP/SigLIP。
* Milvus/Qdrant。
* Celery/Redis integration。
* large video fixtures。

MVP 完成标准：

* 默认 CI 全部通过。
* E2E agentic search 通过。
* evidence hallucination rate = 0。
* recall@k、MRR、nDCG 可本地运行。
