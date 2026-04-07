# API 契约草案

## 通用约定

* Base path：`/api/v1`。
* 除上传外，请求与响应使用 JSON。
* 上传接口使用 `multipart/form-data`。
* 时间戳使用 ISO 8601。
* 媒体时间使用秒，类型为浮点数。
* 字段名保持 English，例如 `video_id`、`segment_id`、`query_text`、`workflow_id`。
* MVP 可使用开发态 `X-User-Id` header，后续替换为正式认证。
* 推荐所有写操作支持可选 `Idempotency-Key` header，避免重复上传、重复创建 workflow。
* 推荐所有响应返回 `request_id`，方便日志追踪、链路排查和 benchmark。
* 推荐所有异步任务返回 `workflow_id` 与 `status_url`，由前端轮询或订阅状态。
* MVP 阶段不返回原始 embedding 向量，只返回 `embedding_ref`、`embedding_model` 与 `index_version`。
* 所有分数默认归一化到 `0.0 - 1.0`，除非字段名明确表示原始分数，例如 `raw_bm25_score`。

通用状态枚举：

```text
queued
running
succeeded
failed
cancelled
partially_succeeded
```

通用错误响应：

```json
{
  "request_id": "req_01HZX0",
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "top_k must be between 1 and 50",
    "details": {
      "field": "top_k",
      "expected": "1 <= top_k <= 50"
    }
  }
}
```

常见错误码：

```text
INVALID_ARGUMENT
UNAUTHORIZED
FORBIDDEN
NOT_FOUND
UNSUPPORTED_MEDIA_TYPE
PAYLOAD_TOO_LARGE
WORKFLOW_ALREADY_RUNNING
WORKFLOW_TASK_FAILED
RETRIEVAL_INDEX_NOT_READY
MODEL_SERVICE_UNAVAILABLE
INTERNAL_ERROR
```

## Upload API

`POST /api/v1/videos`

说明：上传视频，创建 `Video` 与 `WorkflowRun`，并启动 upload-to-index workflow。

Request：

* Content type：`multipart/form-data`
* Headers：

  * `X-User-Id`：开发态用户标识。
  * `Idempotency-Key`：可选，用于避免重复上传。
* Fields：

  * `file`：视频文件。
  * `source_type`：`upload`、`livestream_recording` 或 `game_highlight`。
  * `metadata`：可选 JSON string。
  * `workflow_preset`：可选，`fast_index`、`full_multimodal_index` 或 `livestream_analysis`。
  * `language_hint`：可选，例如 `zh`、`en`、`auto`。

Example `metadata`：

```json
{
  "game": "Valorant",
  "language": "zh",
  "creator": "demo-user",
  "title": "Valorant ranked highlight demo",
  "tags": ["gameplay", "fps", "ranked"]
}
```

Response：

```json
{
  "request_id": "req_01HZX0",
  "video_id": "vid_01HZX4",
  "workflow_id": "wf_01HZX5",
  "status": "uploaded",
  "workflow_status": "queued",
  "storage_uri": "s3://nova-videos/vid_01HZX4/original.mp4",
  "status_url": "/api/v1/workflows/wf_01HZX5",
  "created_at": "2026-05-08T10:00:00Z"
}
```

说明：

* `workflow_preset=fast_index`：适合 MVP，只执行抽帧、ASR/OCR mock、caption mock、segment 构建与索引。
* `workflow_preset=full_multimodal_index`：执行完整 ASR、OCR、Scene Detection、Shot Detection、Caption、Embedding、Motion Tagging。
* `workflow_preset=livestream_analysis`：额外执行商品识别、高光检测、自动分类、Tag 生成与直播摘要。

## Search API

`POST /api/v1/search`

说明：执行 Agentic Search，返回排序后的 `MediaSegment` 与结构化创意建议。

Request：

```json
{
  "session_id": "sess_01HZX3",
  "scenario": "content_search",
  "query_text": "帮我找适合做热血卡点的视频素材",
  "top_k": 5,
  "retrieval_mode": "hybrid",
  "include_agent_answer": true,
  "search_scope": {
    "video_ids": ["vid_01HZX4"],
    "collection_ids": [],
    "only_indexed": true
  },
  "filters": {
    "source_type": "game_highlight",
    "tags": ["gameplay"],
    "min_highlight_score": 0.5,
    "min_motion_score": 0.4,
    "time_range": {
      "start_time": 0.0,
      "end_time": 600.0
    }
  },
  "retrieval_config": {
    "use_bm25": true,
    "use_dense": true,
    "use_visual_embedding": true,
    "use_metadata_filter": true,
    "use_rerank": true,
    "bm25_top_k": 100,
    "dense_top_k": 100,
    "visual_top_k": 50,
    "rerank_top_k": 20
  },
  "agent_config": {
    "enable_query_rewrite": true,
    "enable_multi_hop_retrieval": true,
    "enable_reflection": true,
    "enable_creative_suggestion": true,
    "response_language": "zh"
  }
}
```

字段说明：

* `scenario`：

  * `content_search`：ToC 内容搜索与创作建议。
  * `media_workflow`：ToB 直播分析、素材管理、自动切片。
* `retrieval_mode`：

  * `bm25`
  * `dense`
  * `visual`
  * `hybrid`
* `search_scope.video_ids`：限定在指定视频内搜索。
* `search_scope.collection_ids`：后续支持素材库、项目空间、企业资产集合。
* `retrieval_config`：用于控制多路召回和重排策略，方便后续做 ablation test。
* `agent_config`：用于控制 Agentic Search 的功能开关，方便 TDD 和 benchmark。

Response：

```json
{
  "request_id": "req_01HZX1",
  "query_id": "qry_01HZX6",
  "session_id": "sess_01HZX3",
  "scenario": "content_search",
  "agent_run_id": "run_01HZX7",
  "query_rewrite": "寻找热血、燃系、高能、快节奏、动作强、适合 beat 匹配的卡点视频片段",
  "expanded_queries": [
    "热血",
    "燃系",
    "高能",
    "快节奏",
    "镜头切换明显",
    "动作强",
    "beat 匹配",
    "团战",
    "冲刺",
    "反击",
    "高潮片段"
  ],
  "results": [
    {
      "segment_id": "seg_01HZX8",
      "video_id": "vid_01HZX4",
      "start_time": 42.5,
      "end_time": 57.2,
      "duration": 14.7,
      "rank": 1,
      "final_score": 0.92,
      "scores": {
        "bm25": 0.74,
        "dense": 0.82,
        "visual": 0.79,
        "rerank": 0.91,
        "highlight": 0.87,
        "motion": 0.78,
        "metadata": 0.65
      },
      "raw_scores": {
        "raw_bm25_score": 8.14
      },
      "evidence": {
        "matched_fields": ["asr", "ocr", "frame_caption", "tags", "visual_embedding"],
        "asr_chunks": [
          {
            "start_time": 45.1,
            "end_time": 49.8,
            "text": "这里一波团战直接反打成功",
            "confidence": 0.91
          }
        ],
        "ocr_blocks": [
          {
            "start_time": 51.2,
            "text": "ACE",
            "confidence": 0.93,
            "bbox": [120, 80, 260, 130]
          }
        ],
        "caption_frames": [
          {
            "time": 48.0,
            "frame_uri": "s3://nova-videos/vid_01HZX4/frames/frame_0048.jpg",
            "caption": "高速第一人称战斗画面，技能特效密集"
          }
        ],
        "tags": ["gameplay", "high_energy", "teamfight"],
        "scene_id": "scene_3",
        "shot_id": "shot_7"
      },
      "reason": "该片段包含团战反击语音、ACE 屏幕文字、高速战斗画面和较高 motion/highlight 分数，适合热血卡点剪辑。",
      "creative_suggestions": {
        "recommended_bgm_style": "高 BPM electronic / trap / phonk",
        "transition_suggestions": ["hit cut", "speed ramp", "flash transition"],
        "editing_notes": ["在 ACE 字样出现前做节奏加速", "击杀确认点匹配鼓点落点"]
      }
    }
  ],
  "answer": {
    "summary": "优先推荐 42.5s 到 57.2s 的团战反击片段，画面节奏快、动作强、高潮明确，适合作为热血卡点主段落。",
    "recommended_bgm_style": "高 BPM electronic / trap / phonk",
    "transition_suggestions": ["在击杀确认点做 hit cut", "ACE 字样出现前加入 speed ramp"],
    "editing_script": [
      {
        "segment_id": "seg_01HZX8",
        "timeline_start": 0.0,
        "timeline_end": 14.7,
        "note": "作为主高潮片段使用"
      }
    ]
  },
  "retrieval_trace": {
    "bm25_candidates": 38,
    "dense_candidates": 42,
    "visual_candidates": 17,
    "merged_candidates": 61,
    "reranked_candidates": 20,
    "returned_results": 5
  },
  "agent_trace": {
    "planner_steps": [
      "analyze_user_intent",
      "rewrite_query",
      "run_multi_channel_retrieval",
      "rerank_segments",
      "generate_creative_suggestions",
      "reflect_answer_quality"
    ],
    "tools_used": [
      "query_rewrite_tool",
      "bm25_search_tool",
      "dense_search_tool",
      "visual_search_tool",
      "rerank_tool",
      "creative_suggestion_tool"
    ],
    "reflection_result": {
      "passed": true,
      "reason": "结果包含片段、时间点、推荐理由、BGM 风格和转场建议，满足用户创作搜索意图。"
    }
  },
  "latency_ms": {
    "query_rewrite": 120,
    "retrieval": 280,
    "rerank": 190,
    "agent_answer": 850,
    "total": 1440
  }
}
```

## Streaming Search API

`POST /api/v1/search/stream`

说明：使用与 `POST /api/v1/search` 相同的 request body，通过 Server-Sent Events 返回检索与 Agent 生成过程。

Example event stream：

```text
event: search_started
data: {"request_id":"req_01HZX1","query_id":"qry_01HZX6","session_id":"sess_01HZX3"}

event: query_rewrite_completed
data: {"query_rewrite":"寻找热血、燃系、高能、快节奏、动作强、适合 beat 匹配的卡点视频片段"}

event: retrieval_started
data: {"query_id":"qry_01HZX6","retrieval_mode":"hybrid"}

event: candidate_found
data: {"segment_id":"seg_01HZX8","rank":1,"start_time":42.5,"end_time":57.2,"final_score":0.92}

event: rerank_completed
data: {"merged_candidates":61,"reranked_candidates":20,"returned_results":5}

event: agent_step
data: {"step":"generate_creative_suggestions","status":"running"}

event: agent_token
data: {"text":"优先推荐 42.5s 到 57.2s 的团战反击片段"}

event: agent_completed
data: {"agent_run_id":"run_01HZX7","status":"succeeded"}

event: search_completed
data: {"query_id":"qry_01HZX6","status":"succeeded","total_latency_ms":1440}
```

错误事件：

```text
event: error
data: {"code":"RETRIEVAL_INDEX_NOT_READY","message":"Video index is not ready yet","video_id":"vid_01HZX4"}
```

说明：

* `agent_token` 用于前端流式展示回答。
* `candidate_found` 用于前端尽早展示片段卡片。
* `rerank_completed` 用于展示检索进度与候选数量。
* `error` 事件应结束本次 stream。

## Segment Detail API

`GET /api/v1/segments/{segment_id}`

说明：返回片段详情、证据、代表帧、分数与模型版本。

Response：

```json
{
  "request_id": "req_01HZX2",
  "segment_id": "seg_01HZX8",
  "video_id": "vid_01HZX4",
  "start_time": 42.5,
  "end_time": 57.2,
  "duration": 14.7,
  "asr_transcript": "这里一波团战直接反打成功",
  "asr_chunks": [
    {
      "start_time": 45.1,
      "end_time": 49.8,
      "text": "这里一波团战直接反打成功",
      "confidence": 0.91
    }
  ],
  "ocr_text": "ACE",
  "ocr_blocks": [
    {
      "start_time": 51.2,
      "text": "ACE",
      "confidence": 0.93,
      "bbox": [120, 80, 260, 130]
    }
  ],
  "frame_captions": ["高速第一人称战斗画面，技能特效密集"],
  "caption_frames": [
    {
      "time": 48.0,
      "frame_uri": "s3://nova-videos/vid_01HZX4/frames/frame_0048.jpg",
      "caption": "高速第一人称战斗画面，技能特效密集"
    }
  ],
  "representative_frame_uri": "s3://nova-videos/vid_01HZX4/frames/frame_0048.jpg",
  "tags": ["gameplay", "high_energy", "teamfight"],
  "scores": {
    "motion_score": 0.78,
    "highlight_score": 0.87,
    "audio_energy_score": 0.69,
    "shot_change_score": 0.81,
    "semantic_density_score": 0.73
  },
  "embedding_refs": {
    "text_embedding_ref": "milvus://nova_segments/text/seg_01HZX8",
    "visual_embedding_ref": "milvus://nova_segments/visual/seg_01HZX8"
  },
  "model_versions": {
    "asr": "mock-asr-v1",
    "ocr": "mock-ocr-v1",
    "caption": "mock-caption-v1",
    "text_embedding": "mock-text-embedding-v1",
    "visual_embedding": "mock-visual-embedding-v1",
    "rerank": "mock-rerank-v1"
  },
  "index_versions": {
    "bm25_index": "bm25-index-v1",
    "vector_index": "milvus-index-v1"
  },
  "metadata": {
    "source_type": "game_highlight",
    "scene_id": "scene_3",
    "shot_id": "shot_7",
    "language": "zh",
    "game": "Valorant"
  },
  "created_at": "2026-05-08T10:03:00Z",
  "updated_at": "2026-05-08T10:03:30Z"
}
```

说明：

* `embedding_refs` 只暴露索引引用，不直接返回 embedding 向量。
* `scores` 中的分数可用于高光排序、检索重排和创作推荐。
* `metadata.scene_id` 与 `metadata.shot_id` 用于关联 Scene Detection / Shot Detection 结果。

## Workflow Status API

`GET /api/v1/workflows/{workflow_id}`

说明：查询 workflow 进度、任务状态、attempt 与错误信息。

Response：

```json
{
  "request_id": "req_01HZX9",
  "workflow_id": "wf_01HZX5",
  "video_id": "vid_01HZX4",
  "workflow_type": "upload_to_index",
  "workflow_preset": "full_multimodal_index",
  "status": "running",
  "progress": {
    "completed_tasks": 6,
    "total_tasks": 13,
    "percentage": 46
  },
  "dag": {
    "nodes": [
      "extract_metadata",
      "extract_audio",
      "scene_detect",
      "shot_detect",
      "sample_keyframes",
      "run_asr",
      "run_ocr",
      "caption_frames",
      "motion_tagging",
      "build_segments",
      "embed_segments",
      "write_index",
      "generate_video_summary"
    ],
    "current_nodes": ["caption_frames"]
  },
  "tasks": [
    {
      "task_id": "task_001",
      "task_type": "extract_audio",
      "status": "succeeded",
      "attempt": 1,
      "max_attempts": 3,
      "dependencies": ["extract_metadata"],
      "started_at": "2026-05-08T10:00:05Z",
      "finished_at": "2026-05-08T10:00:12Z",
      "duration_ms": 7000,
      "output_refs": {
        "audio_uri": "s3://nova-videos/vid_01HZX4/audio/audio.wav"
      },
      "can_retry": true,
      "error": null
    },
    {
      "task_id": "task_007",
      "task_type": "caption_frames",
      "status": "running",
      "attempt": 1,
      "max_attempts": 3,
      "dependencies": ["sample_keyframes"],
      "started_at": "2026-05-08T10:02:31Z",
      "finished_at": null,
      "duration_ms": null,
      "output_refs": {},
      "can_retry": true,
      "error": null
    }
  ],
  "artifacts": {
    "original_video_uri": "s3://nova-videos/vid_01HZX4/original.mp4",
    "audio_uri": "s3://nova-videos/vid_01HZX4/audio/audio.wav",
    "frames_prefix": "s3://nova-videos/vid_01HZX4/frames/",
    "segments_manifest_uri": null,
    "index_status": "not_ready"
  },
  "created_at": "2026-05-08T10:00:00Z",
  "updated_at": "2026-05-08T10:02:31Z"
}
```

任务类型建议：

```text
extract_metadata
extract_audio
scene_detect
shot_detect
sample_keyframes
run_asr
run_ocr
caption_frames
motion_tagging
build_segments
embed_segments
write_index
generate_video_summary
product_recognition
highlight_detection
auto_tagging
content_review
```

说明：

* MVP 可以先 mock `caption_frames`、`motion_tagging`、`product_recognition`。
* `write_index` 成功后，Search API 才能稳定检索该视频。
* `artifacts.index_status` 可取值：

  * `not_ready`
  * `building`
  * `ready`
  * `failed`

## Workflow Retry API

`POST /api/v1/workflows/{workflow_id}/retry`

说明：从指定任务开始重试，保留可复用的上游产物，并清理受影响的下游产物。

Request：

```json
{
  "from_task_type": "run_ocr",
  "retry_policy": {
    "reuse_upstream_artifacts": true,
    "clear_downstream_artifacts": true,
    "max_attempts": 3
  }
}
```

Response：

```json
{
  "request_id": "req_01HZX10",
  "workflow_id": "wf_01HZX5",
  "status": "queued",
  "retry_started_from": "run_ocr",
  "reused_tasks": [
    "extract_metadata",
    "extract_audio",
    "scene_detect",
    "shot_detect",
    "sample_keyframes",
    "run_asr"
  ],
  "invalidated_tasks": [
    "run_ocr",
    "caption_frames",
    "motion_tagging",
    "build_segments",
    "embed_segments",
    "write_index",
    "generate_video_summary"
  ],
  "status_url": "/api/v1/workflows/wf_01HZX5"
}
```

说明：

* 如果 `from_task_type` 为空，默认从第一个 failed task 开始重试。
* 如果 workflow 仍在 running，接口应返回 `WORKFLOW_ALREADY_RUNNING`。
* 如果指定任务不存在，接口应返回 `INVALID_ARGUMENT`。
* 重试逻辑必须保证任务幂等，避免重复写入 segment、embedding 和索引。