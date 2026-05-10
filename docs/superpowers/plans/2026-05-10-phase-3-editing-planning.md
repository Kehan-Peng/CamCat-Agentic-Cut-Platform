# Phase 3 Brief: Editing State and Planning Subgraph

## 目标

实现 Editing Planning Subgraph，支持基于状态补丁的编辑规划，避免全量重新生成。

## 范围

### 核心数据模型
- `GlobalEditingState`: 全局编辑状态
- `EditingStatePatch`: 状态补丁
- `PatchOperation`: 补丁操作
- `WorkflowArtifactStatus`: 工作流产物状态

### Editing Planning Subgraph 节点
1. `IntentToEditTaskNode`: 意图转编辑任务
2. `EditingStateReadNode`: 读取编辑状态
3. `SegmentSelectionNode`: 片段选择
4. `PlanDiffNode`: 计划差异（输出最小补丁）
5. `PatchValidationNode`: 补丁验证
6. `SubtitleDraftNode`: 字幕草稿
7. `ClipPlanNode`: 剪辑计划
8. `TitleTagNode`: 标题标签
9. `ArtifactRefreshPlannerNode`: 产物刷新规划器
10. `EditingPlanValidationNode`: 编辑计划验证
11. `EditingStateUpdateNode`: 编辑状态更新（版本检查）

### State Conflict Recovery Flow
- `ReloadEditingStateNode`: 重新加载编辑状态
- `RebasePatchNode`: 变基补丁
- `ConflictResolutionNode`: 冲突解决

## 关键设计原则

1. **最小补丁优先**: `PlanDiffNode` 输出最小补丁，不是完整计划
2. **版本控制**: `EditingStateUpdateNode` 使用 `state_version` 检查
3. **无静默覆盖**: 冲突时必须显式处理
4. **显式 Fork/Join**: 并行任务必须显式声明

## TDD 计划

### 第一轮：核心数据模型
1. 测试 `GlobalEditingState` 创建和序列化
2. 测试 `EditingStatePatch` 操作
3. 测试 `PatchOperation` 验证
4. 测试 `WorkflowArtifactStatus` 状态转换

### 第二轮：核心节点
1. 测试 `IntentToEditTaskNode` 意图解析
2. 测试 `EditingStateReadNode` 状态加载
3. 测试 `SegmentSelectionNode` 片段选择
4. 测试 `PlanDiffNode` 最小补丁生成
5. 测试 `PatchValidationNode` 补丁验证

### 第三轮：产物生成节点
1. 测试 `SubtitleDraftNode` 字幕生成
2. 测试 `ClipPlanNode` 剪辑计划生成
3. 测试 `TitleTagNode` 标题标签生成
4. 测试 `ArtifactRefreshPlannerNode` 刷新决策

### 第四轮：状态更新和冲突处理
1. 测试 `EditingPlanValidationNode` 计划验证
2. 测试 `EditingStateUpdateNode` 版本检查和更新
3. 测试 `ReloadEditingStateNode` 状态重载
4. 测试 `RebasePatchNode` 补丁变基
5. 测试 `ConflictResolutionNode` 冲突解决

### 第五轮：集成测试
1. 测试完整的 Editing Planning Subgraph 流程
2. 测试与 Coordinator Graph 的集成
3. 测试冲突恢复流程

## 验收标准

- [ ] 所有数据模型测试通过
- [ ] 所有节点单元测试通过
- [ ] Editing Planning Subgraph 集成测试通过
- [ ] 与 Coordinator Graph 集成测试通过
- [ ] 冲突恢复流程测试通过
- [ ] `PlanDiffNode` 输出最小补丁（不是完整计划）
- [ ] `EditingStateUpdateNode` 强制版本检查
- [ ] 无静默覆盖
- [ ] 全量测试通过
- [ ] Phase 3 verifier 通过

## 非目标

- 不实现实际的 FFmpeg 渲染
- 不实现实际的媒体处理
- 不实现 API 端点（Phase 6）
- 不实现 E2E 测试（Phase 7）
