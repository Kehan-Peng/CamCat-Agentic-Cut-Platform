# Nova Frontend

Nova Frontend 是一个基于 React、Vite、Tailwind CSS 和 lucide-react 的前端界面原型。当前页面展示的是 Nova 视频工作台：左侧素材与流程状态，中间视频预览和时间线，右侧 Agent Chat 与导出信息。

## 环境要求

- Node.js 18 或更高版本
- npm

当前已安装依赖，可以直接运行。如果换到另一台电脑或删除了 `node_modules`，先执行安装命令。

## 安装依赖

```bash
npm install
```

## 本地运行

```bash
npm run dev
```

默认会启动 Vite 开发服务器，通常地址是：

```text
http://127.0.0.1:5173/
```

如果 5173 被占用，Vite 会自动切换到 5174、5175 等端口，终端会显示实际地址。

## 构建检查

```bash
npm run build
```

这个命令会检查前端代码能否正常打包，并生成 `dist/` 目录。修改代码后建议先跑一次，确认没有 JSX、依赖或样式构建错误。

## 预览构建结果

```bash
npm run preview
```

这个命令用于预览 `npm run build` 生成的生产版本页面。

## 主要文件

- `src/App.jsx`：Nova 工作台主界面，绝大多数页面结构和交互都在这里。
- `src/main.jsx`：React 应用入口，把 `App.jsx` 挂载到页面。
- `src/styles.css`：Tailwind 引入和少量全局样式。
- `index.html`：Vite 页面入口。
- `package.json`：项目脚本和依赖列表。
- `tailwind.config.js`：Tailwind 扫描配置。
- `postcss.config.js`：Tailwind/PostCSS 配置。

## 常见修改位置

- 修改页面文字：编辑 `src/App.jsx` 中对应的 JSX 文本。
- 修改左侧素材列表：搜索 `EvidenceItem` 或 `ArtifactItem`。
- 修改流程状态：搜索 `StateNode` 或 `TraceItem`。
- 修改中间视频预览文案：搜索 `深层去污`、`Seaways`。
- 修改时间线片段：搜索 `ClipBlock`。
- 修改右侧聊天和导出信息：搜索 `AGENT CHAT` 或 `ToolCard`。

## 注意事项

- 页面里的视频、图片和导出链接目前是静态展示，不会真正调用后端接口。
- `Math.random()` 用于模拟音频波形，每次刷新高度会变化，这是正常现象。
- 当前使用 Tailwind class 编写样式，新增样式优先写在 JSX 的 `className` 中。
