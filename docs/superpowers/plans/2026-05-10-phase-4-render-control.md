# Phase 4 Brief: Export / Render Control and Editing Execution Service

## 目标

实现渲染控制节点和编辑执行服务，支持安全的视频渲染和导出。

## 范围

### Render Control 节点（LangGraph 节点）
1. `RenderReadinessNode`: 检查渲染就绪状态
2. `RenderWorkflowTriggerNode`: 触发渲染工作流（创建 RenderJob）
3. `RenderWorkflowStatusNode`: 查询渲染状态
4. `RenderWorkflowResultReadNode`: 读取渲染结果

### 核心数据模型
- `RenderJob`: 渲染任务
- `ClipSegment`: 剪辑片段
- `EditedVideoArtifact`: 编辑后的视频产物

### Editing Execution Service（确定性服务）
1. `ClipSegmentDeriver`: 将编辑计划转换为可执行的剪辑片段
2. `FFmpegCommandBuilder`: 构建安全的 FFmpeg 命令（参数列表）
3. `RenderJobRunner`: 异步执行渲染任务
4. `OutputVerifier`: 验证渲染输出
5. `ExportMetadataWriter`: 写入导出元数据

## 关键设计原则

1. **LangGraph 节点不执行 FFmpeg**: 节点只负责触发、查询和读取状态
2. **RenderWorkflowTriggerNode 只创建 RenderJob**: 不直接执行渲染
3. **FFmpegCommandBuilder 使用参数列表**: 不使用 shell 字符串
4. **禁止 shell=True**: 所有子进程调用使用参数列表
5. **默认测试 mock FFmpeg 执行**: 避免实际执行 FFmpeg

## TDD 计划

### 第一轮：核心数据模型
1. 测试 `RenderJob` 创建和序列化
2. 测试 `ClipSegment` 数据结构
3. 测试 `EditedVideoArtifact` 数据结构

### 第二轮：Render Control 节点
1. 测试 `RenderReadinessNode` 就绪检查
2. 测试 `RenderWorkflowTriggerNode` 创建 RenderJob
3. 测试 `RenderWorkflowStatusNode` 状态查询
4. 测试 `RenderWorkflowResultReadNode` 结果读取

### 第三轮：Editing Execution Service
1. 测试 `ClipSegmentDeriver` 转换逻辑
2. 测试 `FFmpegCommandBuilder` 参数列表构建
3. 测试 `RenderJobRunner` 异步执行（mock）
4. 测试 `OutputVerifier` 输出验证
5. 测试 `ExportMetadataWriter` 元数据写入

### 第四轮：安全性测试
1. 测试路径验证
2. 测试参数注入防护
3. 测试资源限制
4. 测试沙箱隔离

## 验收标准

- [ ] 所有数据模型测试通过
- [ ] 所有 Render Control 节点测试通过
- [ ] 所有 Editing Execution Service 测试通过
- [ ] FFmpegCommandBuilder 使用参数列表（不是 shell 字符串）
- [ ] 禁止 shell=True
- [ ] 路径验证和安全检查
- [ ] 全量测试通过
- [ ] Phase 4 verifier 通过

## 非目标

- 不实现实际的 FFmpeg 执行（使用 mock）
- 不实现完整的沙箱环境（Phase 7）
- 不实现 API 端点（Phase 6）
- 不实现 E2E 测试（Phase 7）
