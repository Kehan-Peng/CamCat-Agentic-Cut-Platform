# CamCat

CamCat 是一个可本机 Docker Compose 一键启动的多模态智能剪辑多智能体 Harness。它直接将视频片段、文本查询和图片查询送入同一个 Qwen3-VL 2048 维语义空间，以 Milvus 的稠密、BM25 和结构化三路召回配合真实多模态重排序；LangGraph 将需求理解、查询规划、素材检索、剪辑计划、字幕生成和补丁校验编排为可追踪节点。

项目不包含随机向量、假模型响应或静态 API fallback。未配置真实模型服务时会立即失败；测试也只会明确跳过外部服务用例，不会以 stub 代替。

## 主要能力

- 一个或多个用户原片采用 4 小时临时链路分析，不创建素材资产、不写 Milvus；Pixabay 授权素材才进入长期向量库。
- 原片镜头去重、真实画面质量评分、逻辑/节奏重排；外部 B-roll 默认硬限制为成片 25%，用户原片始终是主体。
- Qwen3-VL-Embedding-8B 使用 2048 维 MRL 输出；视频原片段以 multipart 直接上传到唯一网关合同，不抽帧、不平均多向量、不用 caption-only 替代。
- Milvus HNSW 稠密召回、Milvus 原生 BM25 稀疏召回、标签/事件/风险结构化召回，带来源分数与排名证据。
- 加权 RRF 与业务信号融合后，将候选视频和 caption 分批送入
  Qwen3-VL-Reranker-8B 做真实多模态重排序；混合图文 query 的两种模态都参与评分。
- LangGraph 多轮剪辑 Agent；PostgreSQL 保存 Graph Run、节点 Trace、素材、任务和完整状态历史。
- RFC 6902 风格 State Patch、`base_version` Compare-and-Swap 乐观锁、HTTP 409 冲突合同和补偿式回滚。
- 后台 Worker 使用真实 FFmpeg 完成五种画幅自适应、基础调色、片段端淡入淡出、字幕边距和 -14 LUFS 规范化，并以固定音量混合最多一条 BGM、环境声与音效。
- LangGraph 节点通过 SSE 逐步回传需求理解、素材召回、重排、字幕和补丁校验过程，任务轮询仍作为恢复真相源。
- 前端完整复用 `nova-front` 的设计语言，仅替换 CamCat 品牌与业务数据，并已接通上传、检索、编辑、回滚、冲突和导出链路。

## 一键启动（百炼托管 API）

不需要本地部署 Qwen 模型或 GPU。CamCat 会在 Compose 内启动一个轻量
`provider-gateway`，将统一的 CamCat multipart 合同转换为百炼托管 API。需要
Docker Desktop、百炼工作空间 API Host 和一枚未公开过的有效 API Key。复制配置并
填写所有 `change-me`：

```bash
cp .env.example .env
docker compose up --build
```

`CAMCAT_BAILIAN_API_HOST` 填工作空间根地址，例如
`https://<workspace-id>.cn-beijing.maas.aliyuncs.com`，不要加
`/compatible-mode/v1` 或 `/api/v1`；适配器会按模型选择正确路径。
`CAMCAT_PROVIDER_GATEWAY_API_KEY` 是你自行生成的 Compose 内部共享密钥，它不是百炼
key；四个 `*_API_KEY` 默认都应与它相同。`CAMCAT_BAILIAN_API_KEY` 才是百炼密钥。

百炼目前通过短时签名 URL 读取视频，因此完整视频链路还要求
`CAMCAT_OBJECT_STORE_PUBLIC_ENDPOINT` 是百炼可访问的 HTTPS 地址（例如指向本机
MinIO 的反向代理/隧道，或可公网访问的 S3-compatible 对象存储）。签名有效期
默认只有 10 分钟，上游请求结束后立即删除中转对象。

开发和生产模式会在启动时拒绝空值、`change-me`、`placeholder` 和 `.invalid` Provider
配置，避免带着假凭据进入运行态；只有不调用模型的 Compose integration test 使用隔离的
`CAMCAT_ENVIRONMENT=test`。

打开 <http://localhost:5173>。API 文档位于 <http://localhost:8000/docs>，MinIO Console 位于 <http://localhost:9001>。

外部模型网关的精确 multipart/JSON 合同与百炼映射见
[docs/provider-contract.md](docs/provider-contract.md)。整体数据流与并发模型见
[docs/architecture.md](docs/architecture.md)。

## 开放短素材与音频

默认使用覆盖面更广的 Pixabay API 导入不超过 20 秒的开放视频，同时同步 Mixkit 免费许可的 BGM、环境声和转场音效。每条素材保留来源页与许可证；没有 API Key 时只导入 Pixabay 官方 API 文档公开的真实短样片，不会用 stub：

```bash
docker compose exec api python scripts/seed_open_library.py --count 2 --max-duration 20
# 若需按关键词扩充小样本：
docker compose exec -e PIXABAY_API_KEY=... api \
  python scripts/seed_open_library.py --query "travel nature city" --count 3
```

用户原片通过 `/api/v1/source-media` 上传，最多 20 个，总大小受上传上限与用户配额约束。数据库引用和派生分析在精确 4 小时后由单一主维护任务脱敏；MinIO `temporary/` lifecycle 是对象删除真相源（S3 lifecycle 最小为整天粒度）。Worker 本地 job 目录每次都在 `finally` 中删除。

## MVP 能力边界

当前版本的镜头签名仍是 JPEG SHA-256，质量信号主要来自 `blurdetect`；转场为单片段淡入淡出而非 clip-to-clip `xfade`；音乐是固定音量 `amix`，尚不是 sidechain ducking；SFX 只使用首条并延迟 650ms；字幕在 ASR 提供时间戳时严格对齐，否则由 LLM 生成；安全区目前只是固定字幕边距。这些是明确的 MVP 限制，不宣称已实现感知哈希、`xfade`、sidechain ducking 或平台级安全区布局。

## TDD 与验证

Python 运行时固定为 3.12。首次本机开发可执行：

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cd apps/web && npm ci && cd ../..
```

然后运行：

```bash
make test                 # lint、类型、后端单测、前端合同测试和生产构建
make test-integration     # 在 Compose 网络内验证真实 PostgreSQL、Milvus、MinIO、FFmpeg
make test-external        # 真实文本/图片/视频 embedding、rerank、视频理解、ASR
make e2e                  # 真实浏览器上传→索引→检索→多轮编辑→回滚/冲突→渲染播放
```

外部服务测试还需要 `CAMCAT_EXTERNAL_TEST_VIDEO`；Playwright 需要 `CAMCAT_E2E_VIDEO` 与 `CAMCAT_E2E_IMAGE`。缺失时测试会以原因明确的 skip 结束。

## 代码入口

- `apps/api/camcat/api.py`：FastAPI 合同与错误模型。
- `apps/api/camcat/worker.py`：临时原片分析、长期素材摄取和成片渲染 Worker。
- `apps/api/camcat/agent/graph.py`：LangGraph 多智能体流程。
- `apps/api/camcat/retrieval/`：Milvus 多路召回、融合与重排序。
- `apps/api/camcat/domain/state_patch.py`：乐观锁补丁与回滚领域模型。
- `apps/web/CamCatWorkspacePage.tsx`：Nova 设计的 CamCat 工作台。
- `apps/web/e2e/camcat.spec.ts`：全链路浏览器 E2E。

工程约束与验收门槛以 [AGENTS.md](AGENTS.md) 为准。

## 开源许可

代码以 [MIT License](LICENSE) 开源。通过 Pixabay/Mixkit 导入的外部素材仍遵循各自
来源页面和许可证，不因本仓库的 MIT 许可而改变；具体记录见
[docs/media-licenses.json](docs/media-licenses.json) 与
[docs/open-audio-library.json](docs/open-audio-library.json)。
