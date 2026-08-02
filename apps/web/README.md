# CamCat Web

该前端从仓库内 `nova-front/frontend` 机械复制并保持其布局、配色、间距、字体与交互语言，只替换了平台名称、Logo 和 CamCat 业务接线。

当前工作台已连接真实后端链路：视频上传与索引任务、文本/图片多模态检索、Evidence/Route/Trace、Editing Session、多轮 Agent State Patch、版本冲突、补偿式回滚、FFmpeg 渲染、成片播放与下载。静态内容仅用于尚无数据时的视觉空状态，不会作为 API fallback。

```bash
npm ci
npm test
npm run build
npm run e2e
```

开发环境变量：

```bash
VITE_CAMCAT_API_BASE=http://127.0.0.1:8000
VITE_CAMCAT_USER_ID=camcat-local-user
```

Playwright 全链路要求已经启动完整 Docker Compose，并设置 `CAMCAT_E2E_VIDEO` 和 `CAMCAT_E2E_IMAGE` 指向真实本地媒体文件。
