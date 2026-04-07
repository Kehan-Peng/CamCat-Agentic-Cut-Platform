# MVP 范围

## MVP 应包含的能力

MVP 应采用垂直切片，而不是一次性搭建所有模块。第一条可演示链路是：

```text
Upload video
→ extract frames/audio
→ ASR/OCR/caption mock or simple implementation
→ build MediaSegment
→ index into retrieval layer
→ search by user query
→ return segments with timestamps and reasons
````

MVP 包含：

* 通过 API 上传视频文件。
* 将原始视频存入 MinIO 或本地 MinIO-compatible object storage 抽象。
* 创建 `Video` 记录，包含 `user_id`、`source_type`、元数据与处理状态。
* 使用 FFmpeg 抽取音频、代表帧与基础媒体信息。
* 使用 fixed-window segmentation 作为默认分段策略；Scene Detection 与 Shot Detection 作为可插拔增强。
* fixed-window segmentation 默认支持固定窗口与可选 overlap，避免场景检测失败导致无法构建片段。
* 使用 Whisper/faster-whisper、PaddleOCR、caption model 的 adapter 接口；默认使用 deterministic mock adapters，保证 CI 与 TDD 稳定。
* Frame Caption 在 MVP 中可以默认使用 mock captioner 或人工 fixture captions，不要求接入真实 VLM；真实 VLM-based frame captioning 可在后续通过 adapter 启用。
* 从 ASR、OCR、frame captions、tags、motion score、highlight score 与 metadata 构建 `MediaSegment`。
* 为片段生成 text embedding 与 visual embedding；默认 mock embedding，可替换为 bge-m3、jina-embeddings-v3、CLIP 或 SigLIP。
* 检索层应通过 `VectorIndex` adapter 屏蔽底层向量库实现。
* Unit tests 与 CI 默认使用 in-memory vector index。
* 本地 Demo 可接入 Milvus 或 Qdrant。
* Milvus 作为后续生产化优先选项。
* 支持 BM25、Dense Retrieval、Hybrid Search、Metadata Filtering 与简单 Rerank。
* 支持 Agentic Search：Query Rewrite、Multi-hop Retrieval、Hybrid Fusion、Rerank、Evidence Grounding、Creative Suggestion、Optional Reflection 与 Structured Answer。
* MVP 阶段不实现完全自主多 Agent 行为。
* MVP 阶段的 Agentic Search 应采用 deterministic planner 与固定工具链，优先保证稳定性与可测试性。
* Agentic Search 的默认执行链路为：

```text
Query Rewrite
→ Multi-hop Retrieval
→ Hybrid Fusion
→ Rerank
→ Evidence Grounding
→ Creative Suggestion
→ Optional Reflection
→ Structured Answer
```

* 跟踪 upload-to-index workflow 的任务状态、错误信息与重试。
* 为后续前端提供 upload、workflow status、search 与 segment detail API。

## MVP 中的 ToC 范围

ToC Demo 查询使用：

```text
帮我找适合做热血卡点的视频素材
```

系统应返回：

* 推荐 `MediaSegment`。
* `start_time` 与 `end_time`。
* 推荐理由。
* 证据来源，例如 `asr_chunks`、`ocr_blocks`、`caption_frames`、`tags`、`motion_score` 与 `highlight_score`。
* 推荐 BGM 风格与转场建议。
* 可选剪辑脚本。

## MVP 中的 ToB 降级策略

ToB Demo 查询使用：

```text
分析今天直播录屏并生成高转化切片
```

MVP 不要求真实企业级商品识别。可使用：

* ASR keywords。
* OCR keywords。
* frame captions。
* rule-based matching。
* mock product catalog。
* 手工配置的 product dictionary。

生产级 SKU recognition、商品图像检测、跨品牌商品归一化、企业商品库同步与高精度转化预测全部推迟。

## 暂缓内容

以下能力推迟到 MVP 之后：

* 真实多 Agent 自主协作。
* 复杂 Reflection loop。
* 实时直播流处理。
* 生产级模型服务与 GPU 调度。
* 将 OpenSearch 纳入 MVP 运行依赖；MVP 使用 Python BM25 或轻量 lexical index，OpenSearch 作为未来替换选项。
* 完整 observability dashboard。
* 自动剪辑渲染与导出。
* 企业权限、审计、计费、资产审批流。

## MVP 成功标准

用户成功标准：

* 用户能上传一个短视频并看到 workflow 进度。
* 用户能搜索 `帮我找适合做热血卡点的视频素材`。
* 当索引中存在足够匹配候选时，系统至少返回 5 个排序后的片段候选。
* 如果匹配候选不足 5 个，系统应返回全部可用候选，并在响应中说明候选不足的原因。
* 每个结果包含 `video_id`、`segment_id`、`start_time`、`end_time`、证据、标签、分数与中文推荐理由。
* 支持按 `video_id`、`source_type`、`tags`、`min_highlight_score` 等 metadata filters 搜索。
* 失败任务可以重试，并保留结构化错误信息。

工程成功标准：

* 第一条垂直切片有 unit tests 与 integration tests。
* 所有模型能力都通过 adapter 暴露，并默认支持 deterministic mock mode。
* `MediaSegment` 是 ingestion、retrieval、agent 与 API 的共享契约。
* 评估脚本能计算 recall@k、nDCG、MRR、latency 与基础 retrieval accuracy。