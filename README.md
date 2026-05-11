# Nova Workspace

Nova Workspace 是一个使用 React、Vite 和 Tailwind CSS 搭建的前端原型页面，展示了一个 AI 视频剪辑工作台界面：素材证据、工作流状态、视频预览、时间线和右侧 Agent Chat 面板。

## 功能概览

- 顶部品牌栏，包含像素小猫 Nova 标识、项目名称、分享和导出入口。
- 左侧素材与工作流面板，展示 Evidence、Route / State、Trace 和 Artifacts。
- 中央视频编辑区，包含预览画面、播放控制、剪辑计划和多轨时间线。
- 右侧 Agent Chat 面板，展示任务执行过程和最终导出结果。
- 响应式布局，在较窄屏幕下隐藏侧边辅助栏，保留核心编辑区。

## 技术栈

- React 18
- Vite 5
- TypeScript
- Tailwind CSS
- lucide-react

## 本地运行

安装依赖：

```bash
npm install
```

启动开发服务器：

```bash
npm run dev
```

默认访问地址：

```text
http://127.0.0.1:5173
```

构建生产版本：

```bash
npm run build
```

预览生产构建：

```bash
npm run preview
```

## 主要文件

- `NovaWorkspacePage.tsx`：页面主体组件和界面数据。
- `src/main.tsx`：React 应用入口。
- `src/styles.css`：Tailwind 引入和全局基础样式。
- `index.html`：Vite HTML 入口。
- `tailwind.config.js`：Tailwind 扫描配置。

## 说明

页面中的素材、日志、时间线片段和导出信息目前都是静态模拟数据，适合作为视觉原型或后续接入真实接口的前端基础。
