# Phase 2: Perception & Retrieval Subgraph

**日期**: 2026-05-10
**状态**: 进行中

---

## 目标

实现 Perception & Retrieval Subgraph，提供完整的媒体检索流程，包括媒体就绪检查、查询重写、混合检索、证据附加、重排序、证据基础化、质量检查和条件重试。

---

## 范围内

### 核心节点实现

1. **MediaReadinessNode**
   - 检查视频或资产库是否已索引和可搜索
   - 如果媒体未就绪，写入 `route_request` 和 `readiness_status`
   - 不直接执行媒体处理

2. **QueryRewriteNode** (已存在，需集成)
   - 转换用户查询为结构化检索意图
   - 扩展查询词
   - 保留原始查询

3. **HybridRetrievalNode** (已存在，需集成)
   - 执行 BM25 词法搜索
   - 执行确定性或生产密集检索
   - 应用元数据过滤器
   - 融合候选结果

4. **CandidateEvidenceAttachNode**
   - 附加 ASR、OCR、caption、tag、score 和元数据证据
   - 准备证据特征用于重排序

5. **RerankNode** (已存在，需集成)
   - 使用多种信号重新排序候选结果
   - 保留原始通道分数用于可解释性

6. **FinalEvidenceGroundingNode**
   - 为每个返回的片段构建最终基础证据
   - 确保原因仅引用真实证据
   - 拒绝或标记未基础的解释

7. **SearchQualityCheckNode**
   - 执行量化检索质量评估
   - 不是开放式 LLM 反思步骤
   - 使用指标：result_count、top_score、avg_topk_score、evidence_coverage、timestamp_coverage

8. **ConditionalRetryOrFinalize**
   - 决定是否完成、重试、请求澄清或返回尽力而为的结果
   - 强制执行重试预算

### 集成到 Coordinator Graph

- 将 Perception & Retrieval Subgraph 集成到 Coordinator Graph
- 替换 `perception_retrieval_placeholder` 占位符节点
- 确保条件路由正确工作

---

## 范围外

- 不实现实际的媒体处理工作流（Phase 5）
- 不实现编辑规划子图（Phase 3）
- 不实现导出/渲染控制（Phase 4）
- 不添加外部服务（Milvus、Qdrant、OpenSearch、Celery、Redis、MinIO）
- 不在 LangGraph 节点中运行重型媒体处理

---

## 可能变更的文件

### 新文件
- `backend/app/agents/perception/media_readiness.py`
- `backend/app/agents/perception/evidence_attach.py`
- `backend/app/agents/perception/evidence_grounding.py`
- `backend/app/agents/perception/quality_check.py`
- `backend/app/agents/perception/retry_or_finalize.py`
- `backend/app/agents/perception/__init__.py`

### 修改文件
- `backend/app/agents/coordinator.py` - 集成子图
- `backend/app/agents/state.py` - 可能添加字段

### 测试文件
- `tests/test_media_readiness_node.py`
- `tests/test_evidence_attach_node.py`
- `tests/test_evidence_grounding_node.py`
- `tests/test_quality_check_node.py`
- `tests/test_retry_or_finalize_node.py`
- `tests/test_perception_subgraph.py`

---

## TDD 计划

### 1. MediaReadinessNode
- **测试**: 媒体已就绪时返回 ready 状态
- **测试**: 媒体未就绪时写入 route_request 和 readiness_status
- **测试**: 不直接执行媒体处理
- **实现**: MediaReadinessNode

### 2. CandidateEvidenceAttachNode
- **测试**: 附加 ASR 证据到候选结果
- **测试**: 附加 OCR、caption、tag 证据
- **测试**: 附加 motion_score 和 highlight_score
- **实现**: CandidateEvidenceAttachNode

### 3. FinalEvidenceGroundingNode
- **测试**: 为每个片段构建基础证据
- **测试**: 拒绝未基础的解释
- **测试**: 仅引用真实证据源
- **实现**: FinalEvidenceGroundingNode

### 4. SearchQualityCheckNode
- **测试**: 计算质量指标（result_count、top_score、avg_topk_score）
- **测试**: 检查最小质量阈值
- **测试**: 返回 passed/failed 和 retry_action
- **实现**: SearchQualityCheckNode

### 5. ConditionalRetryOrFinalize
- **测试**: 质量通过时完成
- **测试**: 达到最大重试次数时完成
- **测试**: 超出延迟预算时完成
- **测试**: 强制执行重试预算
- **实现**: ConditionalRetryOrFinalize

### 6. Perception Subgraph 集成
- **测试**: 子图按正确顺序执行所有节点
- **测试**: 子图与 Coordinator Graph 正确集成
- **测试**: 条件路由正确工作
- **实现**: 集成到 Coordinator Graph

---

## 验收标准

1. ✅ 所有新节点已实现并通过单元测试
2. ✅ Perception & Retrieval Subgraph 已集成到 Coordinator Graph
3. ✅ 所有测试通过（包括现有测试）
4. ✅ MediaReadinessNode 不直接执行媒体处理
5. ✅ SearchQualityCheckNode 使用量化指标，不是开放式 LLM 反思
6. ✅ ConditionalRetryOrFinalize 强制执行重试预算
7. ✅ 没有引入禁止的基础设施
8. ✅ LangGraph 节点保持薄编排单元
9. ✅ 实现遵循 AGENTS.md

---

## 实现注意事项

- MediaReadinessNode 必须写入 `route_request` 和 `readiness_status` 到 AgentState，而不是直接调用 Media Workflow Control Nodes
- SearchQualityCheckNode 必须使用量化指标，不能是无界的 LLM 反思循环
- ConditionalRetryOrFinalize 必须强制执行重试预算，防止无限重试
- 所有节点必须记录 node_trace
- 保持向后兼容性
