# Phase 1 Brief - LangGraph Coordinator Foundation

**日期：** 2026-05-10

## 目标

建立 LangGraph Coordinator Graph 基础架构，实现 Intent Routing Layer 和复合路由机制。

## 范围内任务

1. ✅ 确认 langgraph 依赖已安装
2. 定义 AgentState（backend/app/agents/state.py）
3. 实现 Intent Routing 契约（IntentClassificationResult, RouteDecision）
4. 实现 RouteSequenceControllerNode
5. 实现 FinalResponseNode 标准化响应模式
6. 构建 Coordinator Graph 骨架（带占位符 subgraph nodes）
7. 实现基础 node trace

## 范围外

- 不实现完整的 Perception & Retrieval Subgraph（Phase 2）
- 不实现 Editing Planning Subgraph（Phase 3）
- 不实现 Media Workflow Control（Phase 5）
- 不实现真实 LLM 调用（使用规则或 mock）
- 不引入外部服务依赖

## 文件变更

**新增：**
- `backend/app/agents/state.py` - AgentState 定义
- `backend/app/agents/intent_routing/` - Intent Routing Layer nodes
  - `__init__.py`
  - `state_load.py`
  - `intent_classification.py`
  - `route_decision.py`
  - `route_sequence_controller.py`
  - `final_response.py`
- `backend/app/agents/coordinator.py` - Coordinator Graph
- `tests/test_agent_state.py`
- `tests/test_route_sequence_controller.py`
- `tests/test_coordinator_graph.py`

**修改：**
- `pyproject.toml` 或 `requirements.txt`（如需添加 langgraph）

## TDD 计划

### 1. AgentState 测试
- ✅ 可序列化默认值
- ✅ route 字段存在
- ✅ retry budget 字段存在
- ✅ editing patch 字段存在
- ✅ 不存储重型媒体对象

### 2. RouteSequenceController 测试
- ✅ retrieval_only → [perception_retrieval]
- ✅ editing_only → [editing_planning]
- ✅ retrieval_then_editing → [perception_retrieval, editing_planning]
- ✅ export_only → [export_render_control]
- ✅ editing_then_export → [editing_planning, export_render_control]
- ✅ retrieval_then_editing_then_export → [perception_retrieval, editing_planning, export_render_control]
- ✅ clarification_required → [final_response]
- ✅ finalize_with_error → [final_response]
- ✅ route_sequence 不扁平化 subgraph 边界
- ✅ 模糊意图返回 clarification_required

### 3. FinalResponseNode 测试
- ✅ media not ready 响应
- ✅ render job running 响应
- ✅ low confidence result 响应
- ✅ state conflict 响应
- ✅ invalid argument 响应

### 4. Coordinator Graph 测试
- ✅ 简单 retrieval_only 路由
- ✅ 复合路由序列（带占位符）
- ✅ 生成 node_trace

## 验收标准

1. ✅ 所有测试通过（conda run -n nova pytest -q）
2. ✅ AgentState 包含所有必需字段
3. ✅ RouteSequenceControllerNode 正确展开 11 种路由
4. ✅ FinalResponseNode 支持 5 种响应状态
5. ✅ Coordinator Graph 可以执行简单和复合路由
6. ✅ node_trace 正确记录
7. ✅ 无外部服务依赖
8. ✅ 向后兼容现有测试

## 架构约束

- LangGraph nodes 必须是薄编排单元
- 不在 nodes 内运行重型处理
- export_only 必须路由到 export_render_control，不直接到 Editing Execution Service
- AgentState 是唯一运行时状态来源（backend/app/agents/state.py）
- 复合路由必须通过 RouteSequenceControllerNode 显式展开
