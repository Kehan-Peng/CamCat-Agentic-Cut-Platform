# Phase 6 Brief: API Integration and Backward Compatibility

## 目标

实现 API 集成，通过 Coordinator Graph 提供 agentic search 端点，并保持向后兼容。

## 范围

### API 端点
- `/api/v1/search/agentic`: 通过 Coordinator Graph 的 agentic search

### 向后兼容响应字段
- `route_decision`: 路由决策
- `route_sequence`: 路由序列
- `state_snapshot`: 状态快照
- `node_trace`: 节点追踪
- `quality_check`: 质量检查
- `retry_history`: 重试历史

### 会话 APIs
- Editing Session APIs（基础实现）
- Workflow Status APIs（基础实现）
- Render / Export Status APIs（基础实现）

## 关键设计原则

1. **通过 Coordinator Graph**: 所有请求通过 Coordinator Graph 处理
2. **向后兼容**: 保持现有 API 响应格式
3. **状态追踪**: 提供完整的执行追踪信息

## TDD 计划

### 第一轮：API 端点
1. 测试 `/api/v1/search/agentic` 端点
2. 测试请求参数验证
3. 测试响应格式

### 第二轮：向后兼容
1. 测试响应字段完整性
2. 测试与现有 API 的兼容性

## 验收标准

- [ ] API 端点实现并测试通过
- [ ] 向后兼容响应字段完整
- [ ] 全量测试通过
- [ ] Phase 6 verifier 通过

## 非目标

- 不实现完整的认证授权（Phase 7）
- 不实现完整的错误处理（Phase 7）
