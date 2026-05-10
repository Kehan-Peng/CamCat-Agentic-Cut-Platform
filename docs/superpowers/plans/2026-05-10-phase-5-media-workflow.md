# Phase 5 Brief: Media Workflow Control and Processing DAG

## 目标

实现媒体工作流控制和处理 DAG，支持依赖关系验证和部分成功处理。

## 范围

### 核心数据模型
- `MediaWorkflowRun`: 媒体工作流运行
- `MediaWorkflowTask`: 媒体工作流任务

### Media Workflow Control 节点（LangGraph 节点）
1. `MediaWorkflowTriggerNode`: 触发媒体工作流
2. `MediaWorkflowStatusNode`: 查询工作流状态
3. `MediaWorkflowResultReadNode`: 读取工作流结果

### 处理任务存根（确定性服务）
- `MetadataExtractionTask`
- `AudioExtractionTask`
- `ASRTask`
- `FrameExtractionTask`
- `OCRTask`
- `CaptionTask`
- `SceneShotDetectionTask`
- `SegmentBuilderTask`
- `TextEmbeddingTask`
- `VisualEmbeddingTask`
- `IndexingTask`
- `SearchableStatusTask`

## 关键设计原则

1. **强制依赖关系**:
   - ASR 等待 AudioExtraction
   - OCR/Caption 等待 FrameExtraction
   - Indexing 等待 segment + embeddings + metadata

2. **DAG 依赖验证**: 在执行前验证依赖关系

3. **支持部分成功**:
   - `partially_searchable`
   - `searchable_with_missing_ocr`
   - `searchable_with_missing_caption`
   - `searchable_with_text_only_embedding`

## TDD 计划

### 第一轮：核心数据模型
1. 测试 `MediaWorkflowRun` 创建和序列化
2. 测试 `MediaWorkflowTask` 数据结构
3. 测试依赖关系字段

### 第二轮：DAG 依赖验证
1. 测试依赖关系验证逻辑
2. 测试循环依赖检测
3. 测试拓扑排序

### 第三轮：Control 节点
1. 测试 `MediaWorkflowTriggerNode` 创建工作流
2. 测试 `MediaWorkflowStatusNode` 状态查询
3. 测试 `MediaWorkflowResultReadNode` 结果读取

### 第四轮：任务存根
1. 测试各个任务的依赖关系定义
2. 测试部分成功场景

## 验收标准

- [ ] 所有数据模型测试通过
- [ ] DAG 依赖验证测试通过
- [ ] 所有 Control 节点测试通过
- [ ] 任务存根测试通过
- [ ] 支持部分成功
- [ ] 全量测试通过
- [ ] Phase 5 verifier 通过

## 非目标

- 不实现实际的媒体处理（使用存根）
- 不实现完整的任务调度器（Phase 7）
- 不实现 API 端点（Phase 6）
