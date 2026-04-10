# API 契约

## 通用约定

* Base path：`/api/v1`
* 字段名保持 English，例如 `video_id`、`segment_id`、`query_text`、`workflow_id`、`graph_run_id`、`editing_session_id`
* MVP 可使用开发态 `X-User-Id` header
* 媒体时间使用秒，类型为 float
* Agentic Search 内部由 LangGraph Coordinator Graph 执行
* 所有推荐理由必须基于 returned evidence

通用错误响应：

```json
{
  "request_id": "req_001",
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "query_text is required",
    "details": {
      "field": "query_text"
    }
  }
}
```

## Upload API

`POST /api/v1/videos`

说明：上传视频，创建 `Video`，触发 Media Processing Workflow DAG。

Request：

* Content type：`multipart/form-data`
* Headers：
  * `X-User-Id`
  * `Idempotency-Key` 可选
* Fields：
  * `file`
  * `source_type`
  * `metadata` 可选 JSON string

Response：

```json
{
  "request_id": "req_001",
  "video_id": "vid_001",
  "workflow_id": "wf_001",
  "status": "uploaded",
  "workflow_status": "queued",
  "segment_count": 0,
  "status_url": "/api/v1/workflows/wf_001"
}
```

Phase 4 异步 Celery/Redis 模式下返回 workflow_status="queued" 与 status_url。

## Agentic Search API

`POST /api/v1/search/agentic`

说明：Agentic Search 接口。内部必须由 LangGraph Coordinator Graph 执行，使用 `AgentState` 编排 Intent Routing、Perception & Retrieval、Editing Planning、Media Workflow Control、Export / Render Control。

Request：

```json
{
  "request_id": "req_001",
  "thread_id": "thread_001",
  "session_id": "sess_001",
  "query_text": "帮我找热血片段，并剪成 30 秒短视频",
  "top_k": 5,
  "filters": {
    "video_id": "vid_001",
    "tags": ["gameplay"],
    "min_motion_score": 0.4,
    "min_highlight_score": 0.5
  },
  "agent_config": {
    "enable_checkpoint": true,
    "enable_reflection": true,
    "response_language": "zh"
  }
}
```

Response：

```json
{
  "graph_run_id": "graph_run_001",
  "thread_id": "thread_001",
  "session_id": "sess_001",
  "intent": "retrieval_then_editing",
  "route_targets": ["perception_retrieval", "editing_planning"],
  "state_snapshot": {
    "query_text": "帮我找热血片段，并剪成 30 秒短视频",
    "rewritten_query": "热血 燃系 高能 快节奏 镜头切换明显 动作强 beat 匹配 团战 冲刺 反击 高潮片段",
    "expanded_queries": ["热血", "燃系", "高能", "快节奏", "镜头切换明显", "动作强", "beat 匹配", "团战", "冲刺", "反击", "高潮片段"],
    "retrieved_count": 20,
    "reranked_count": 5,
    "reflection_passed": true,
    "editing_session_id": "edit_001",
    "state_version": 1
  },
  "node_trace": [
    {
      "node_name": "StateLoadNode",
      "status": "succeeded",
      "latency_ms": 5
    },
    {
      "node_name": "IntentClassificationNode",
      "status": "succeeded",
      "latency_ms": 8
    },
    {
      "node_name": "RouteDecisionNode",
      "status": "succeeded",
      "latency_ms": 2
    },
    {
      "node_name": "MediaReadinessNode",
      "status": "succeeded",
      "latency_ms": 10
    },
    {
      "node_name": "QueryRewriteNode",
      "status": "succeeded",
      "latency_ms": 12
    },
    {
      "node_name": "HybridRetrievalNode",
      "status": "succeeded",
      "latency_ms": 35
    },
    {
      "node_name": "CandidateEvidenceAttachNode",
      "status": "succeeded",
      "latency_ms": 8
    },
    {
      "node_name": "RerankNode",
      "status": "succeeded",
      "latency_ms": 8
    },
    {
      "node_name": "FinalEvidenceGroundingNode",
      "status": "succeeded",
      "latency_ms": 6
    },
    {
      "node_name": "SearchQualityCheckNode",
      "status": "succeeded",
      "latency_ms": 4
    },
    {
      "node_name": "ConditionalRetryOrFinalizeNode",
      "status": "succeeded",
      "latency_ms": 2
    },
    {
      "node_name": "IntentToEditTaskNode",
      "status": "succeeded",
      "latency_ms": 10
    },
    {
      "node_name": "EditingStateReadNode",
      "status": "succeeded",
      "latency_ms": 5
    },
    {
      "node_name": "SegmentSelectionNode",
      "status": "succeeded",
      "latency_ms": 8
    },
    {
      "node_name": "PlanDiffNode",
      "status": "succeeded",
      "latency_ms": 15
    },
    {
      "node_name": "PatchValidationNode",
      "status": "succeeded",
      "latency_ms": 3
    },
    {
      "node_name": "ClipPlanNode",
      "status": "succeeded",
      "latency_ms": 12
    },
    {
      "node_name": "EditingPlanValidationNode",
      "status": "succeeded",
      "latency_ms": 5
    },
    {
      "node_name": "EditingStateUpdateNode",
      "status": "succeeded",
      "latency_ms": 8
    },
    {
      "node_name": "FinalResponseNode",
      "status": "succeeded",
      "latency_ms": 5
    }
  ],
  "rewritten_query": {
    "normalized_query": "热血 燃系 高能 快节奏 镜头切换明显 动作强 beat 匹配 团战 冲刺 反击 高潮片段",
    "expanded_queries": ["热血", "燃系", "高能", "快节奏", "镜头切换明显", "动作强", "beat 匹配", "团战", "冲刺", "反击", "高潮片段"]
  },
  "retrieved_segments": [
    {
      "segment_id": "seg_001",
      "video_id": "vid_001",
      "start_time": 42.5,
      "end_time": 57.2,
      "score": 0.81
    }
  ],
  "reranked_segments": [
    {
      "segment_id": "seg_001",
      "video_id": "vid_001",
      "start_time": 42.5,
      "end_time": 57.2,
      "score": 0.92,
      "reason": "该片段包含团战反击语音、ACE 屏幕文字和 high_energy 标签，适合热血卡点剪辑。",
      "evidence": [
        {
          "evidence_type": "asr",
          "text": "最后一波团战开启，反打成功，全场沸腾",
          "start_time": 45.1,
          "end_time": 49.8
        }
      ]
    }
  ],
  "search_quality_report": {
    "passed": true,
    "quality_score": 0.82,
    "metrics": {
      "result_count": 5,
      "top_score": 0.92,
      "avg_topk_score": 0.77,
      "evidence_coverage": 1.0,
      "timestamp_coverage": 1.0,
      "diversity_score": 0.64
    }
  },
  "editing_plan": {
    "editing_session_id": "edit_001",
    "state_version": 1,
    "clip_segments": [
      {
        "clip_segment_id": "clip_001",
        "source_segment_id": "seg_001",
        "start_time": 42.5,
        "end_time": 57.2,
        "order": 1
      }
    ],
    "target_duration": 30.0,
    "artifact_status": {
      "clip_segments": "ready",
      "subtitle_draft": "ready",
      "edited_video": "missing"
    }
  },
  "final_answer": {
    "summary": "已找到热血片段并生成 30 秒剪辑计划。推荐 42.5s 到 57.2s 的团战反击片段作为主段落。",
    "segments": ["seg_001"],
    "grounding": ["最后一波团战开启，反打成功，全场沸腾"]
  },
  "creative_suggestions": {
    "recommended_bgm_style": "高 BPM electronic / trap / phonk",
    "transition_suggestions": ["hit cut", "speed ramp", "flash transition"],
    "editing_notes": ["在 ACE 字样出现前做节奏加速"]
  }
}
```

## Editing Session APIs

### Create Editing Session

`POST /api/v1/editing/sessions`

Request：

```json
{
  "video_id": "vid_001",
  "initial_goal": "剪成 30 秒热血卡点短视频",
  "selected_segment_ids": ["seg_001", "seg_002"]
}
```

Response：

```json
{
  "editing_session_id": "edit_001",
  "state_version": 1,
  "artifact_status": {
    "clip_segments": "ready",
    "subtitle_draft": "ready",
    "edited_video": "missing"
  }
}
```

### Get Editing Session

`GET /api/v1/editing/sessions/{editing_session_id}`

Response：

```json
{
  "editing_session_id": "edit_001",
  "user_id": "user_001",
  "video_id": "vid_001",
  "state_version": 3,
  "current_goal": "剪成 30 秒热血卡点短视频",
  "selected_segments": ["seg_001", "seg_002"],
  "clip_segments": [
    {
      "clip_segment_id": "clip_001",
      "source_segment_id": "seg_001",
      "start_time": 42.5,
      "end_time": 57.2,
      "order": 1
    }
  ],
  "artifact_status": {
    "clip_segments": "ready",
    "subtitle_draft": "ready",
    "edited_video": "stale"
  },
  "needs_refresh": {
    "edited_video": true
  }
}
```

### Send Editing Message

`POST /api/v1/editing/sessions/{editing_session_id}/message`

说明：发送编辑指令，触发 Editing Planning Subgraph。

Request：

```json
{
  "message": "把开头改得更抓人一点，第二段删掉，字幕短一点"
}
```

Response：

```json
{
  "graph_run_id": "graph_run_002",
  "editing_session_id": "edit_001",
  "state_version": 4,
  "patch_id": "patch_008",
  "operations": [
    {
      "op": "update_intro_style",
      "target": "editing_plan.hook",
      "value": "stronger_opening"
    },
    {
      "op": "remove_clip_segment",
      "target": "clip_segments",
      "clip_segment_id": "clip_2"
    },
    {
      "op": "update_subtitle_style",
      "target": "subtitle_draft",
      "value": {
        "max_chars_per_line": 12,
        "style": "shorter"
      }
    }
  ],
  "affected_artifacts": [
    "editing_plan",
    "clip_segments",
    "subtitle_draft",
    "edited_video"
  ],
  "artifact_status": {
    "clip_segments": "ready",
    "subtitle_draft": "ready",
    "edited_video": "stale"
  },
  "node_trace": [
    {
      "node_name": "IntentToEditTaskNode",
      "status": "succeeded",
      "latency_ms": 10
    },
    {
      "node_name": "EditingStateReadNode",
      "status": "succeeded",
      "latency_ms": 5
    },
    {
      "node_name": "PlanDiffNode",
      "status": "succeeded",
      "latency_ms": 15
    },
    {
      "node_name": "PatchValidationNode",
      "status": "succeeded",
      "latency_ms": 3
    },
    {
      "node_name": "ArtifactRefreshPlannerNode",
      "status": "succeeded",
      "latency_ms": 5
    },
    {
      "node_name": "EditingStateUpdateNode",
      "status": "succeeded",
      "latency_ms": 8
    }
  ]
}
```

### Render Editing Session

`POST /api/v1/editing/sessions/{editing_session_id}/render`

说明：触发渲染作业，委托给外部 Editing Execution Service。

Request：

```json
{
  "output_format": "mp4",
  "quality": "high"
}
```

Response：

```json
{
  "render_job_id": "render_001",
  "editing_session_id": "edit_001",
  "status": "queued",
  "status_url": "/api/v1/editing/sessions/edit_001/render-jobs/render_001"
}
```

### Get Render Job Status

`GET /api/v1/editing/sessions/{editing_session_id}/render-jobs/{render_job_id}`

Response：

```json
{
  "render_job_id": "render_001",
  "editing_session_id": "edit_001",
  "status": "succeeded",
  "output_uri": "s3://bucket/outputs/render_001.mp4",
  "preview_uri": "s3://bucket/previews/render_001_preview.mp4",
  "duration_seconds": 30.5,
  "created_at": "2026-05-10T10:00:00Z",
  "updated_at": "2026-05-10T10:02:30Z"
}
```

### Get Exported Video

`GET /api/v1/editing/sessions/{editing_session_id}/exported-video`

Response：

```json
{
  "edited_video_id": "edited_001",
  "editing_session_id": "edit_001",
  "render_job_id": "render_001",
  "output_uri": "s3://bucket/outputs/render_001.mp4",
  "preview_uri": "s3://bucket/previews/render_001_preview.mp4",
  "duration_seconds": 30.5,
  "checksum": "sha256:abc123...",
  "created_at": "2026-05-10T10:02:30Z"
}
```

## Segment Detail API

`GET /api/v1/segments/{segment_id}`

说明：返回 `MediaSegment` 详情、证据、分数、代表帧与模型版本。

Response：

```json
{
  "segment_id": "seg_001",
  "video_id": "vid_001",
  "start_time": 42.5,
  "end_time": 57.2,
  "asr_transcript": "最后一波团战开启，反打成功，全场沸腾",
  "ocr_text": "ACE / 胜利 / 高能时刻",
  "frame_captions": ["快节奏战斗", "冲刺"],
  "tags": ["gameplay", "high_energy", "hot_blooded", "highlight"],
  "motion_score": 0.91,
  "highlight_score": 0.89,
  "evidence": [
    {
      "evidence_type": "ocr",
      "text": "ACE / 胜利 / 高能时刻",
      "start_time": 50.0
    }
  ],
  "model_versions": {
    "asr": "mock-asr-v1",
    "ocr": "mock-ocr-v1",
    "caption": "mock-caption-v1"
  }
}
```

## Workflow Status API

`GET /api/v1/workflows/{workflow_id}`

说明：查询媒体处理任务状态。Phase 4 后由 Celery/Redis 驱动重型任务；MVP 可返回同步/mock workflow 状态。

Response：

```json
{
  "workflow_id": "wf_001",
  "video_id": "vid_001",
  "workflow_type": "media_processing",
  "status": "completed",
  "progress": 1.0,
  "tasks": [
    {
      "task_type": "metadata_extraction",
      "status": "completed"
    },
    {
      "task_type": "audio_extraction",
      "status": "completed"
    },
    {
      "task_type": "asr",
      "status": "completed"
    },
    {
      "task_type": "frame_extraction",
      "status": "completed"
    },
    {
      "task_type": "ocr",
      "status": "completed"
    },
    {
      "task_type": "caption",
      "status": "completed"
    },
    {
      "task_type": "scene_detection",
      "status": "completed"
    },
    {
      "task_type": "segment_builder",
      "status": "completed"
    },
    {
      "task_type": "text_embedding",
      "status": "completed"
    },
    {
      "task_type": "visual_embedding",
      "status": "completed"
    },
    {
      "task_type": "indexing",
      "status": "completed"
    }
  ],
  "created_at": "2026-05-10T09:00:00Z",
  "updated_at": "2026-05-10T09:05:00Z"
}
```

## Event Stream API

`GET /api/v1/editing/sessions/{editing_session_id}/events`

说明：SSE 事件流，用于实时推送编辑会话事件。

SSE 事件类型：

```text
turn_started
intent_classified
state_loaded
retrieval_started
retrieval_quality_checked
editing_patch_created
editing_patch_validated
artifact_refresh_planned
editing_state_updated
render_job_created
render_job_running
render_job_succeeded
render_job_failed
turn_completed
```

示例事件：

```text
event: editing_patch_created
data: {"patch_id": "patch_008", "operations_count": 3}

event: editing_state_updated
data: {"state_version": 4, "artifact_status": {"edited_video": "stale"}}

event: render_job_created
data: {"render_job_id": "render_001", "status": "queued"}
```

## 向后兼容性

Phase 3 迁移后，`/api/v1/search/agentic` 可以新增 `graph_run_id`、`state_snapshot`、`node_trace`、`intent`、`route_targets` 等字段，但不得删除 Phase 2 客户端依赖的 `rewritten_query`、`retrieved_segments`、`reranked_segments`、`final_answer`、`creative_suggestions` 关键字段。

如果需要破坏性变更，必须版本化 API（例如 `/api/v2/search/agentic`）。
