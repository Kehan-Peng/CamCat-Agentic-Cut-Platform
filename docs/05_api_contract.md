# API 契约草案

## 通用约定

* Base path：`/api/v1`。
* 字段名保持 English，例如 `video_id`、`segment_id`、`query_text`、`workflow_id`、`graph_run_id`。
* MVP 可使用开发态 `X-User-Id` header。
* 媒体时间使用秒，类型为 float。
* Agentic Search 内部由 LangGraph workflow 执行。
* 所有推荐理由必须基于 returned evidence。

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

说明：上传视频，创建 `Video`，触发 mock/simple media processing 或后续 media workflow。

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
  "segment_count": 0
  "status_url": "/api/v1/workflows/wf_001"
}
```
Phase 4 异步 Celery/Redis 模式下返回 workflow_status="queued" 与 status_url。

## Search API

`POST /api/v1/search`

说明：Phase 3 迁移后，/api/v1/search/agentic 可以新增 graph_run_id、state_snapshot、node_trace 等字段，但不得删除 Phase 2 客户端依赖的 results / final_answer / creative_suggestions 关键字段。

Request：

```json
{
  "session_id": "sess_001",
  "query_text": "帮我找适合做热血卡点的视频素材",
  "top_k": 5,
  "retrieval_mode": "hybrid",
  "filters": {
    "video_id": "vid_001",
    "tags": ["gameplay"],
    "min_highlight_score": 0.5
  }
}
```

Response：

```json
{
  "query_rewrite": {
    "original_query": "帮我找适合做热血卡点的视频素材",
    "normalized_query": "热血 燃系 高能 快节奏 卡点 团战 冲刺 反击 高潮片段",
    "expanded_queries": ["热血", "燃系", "高能", "快节奏", "beat 匹配", "团战", "冲刺", "反击"]
  },
  "results": [
    {
      "segment_id": "seg_001",
      "video_id": "vid_001",
      "start_time": 42.5,
      "end_time": 57.2,
      "score": 0.92,
      "reason": "该片段包含团战反击语音、ACE 屏幕文字、高速战斗画面和较高高光分数，适合热血卡点剪辑。",
      "evidence": [
        {
          "evidence_type": "asr",
          "text": "最后一波团战开启，反打成功，全场沸腾",
          "start_time": 45.1,
          "end_time": 49.8
        }
      ],
      "creative_suggestion": {
        "recommended_bgm_style": "高 BPM electronic / trap / phonk",
        "transition_suggestions": ["hit cut", "speed ramp", "flash transition"],
        "editing_notes": ["在 ACE 字样出现前做节奏加速"]
      }
    }
  ],
  "answer": {
    "summary": "优先推荐 42.5s 到 57.2s 的团战反击片段，画面节奏快、动作强、高潮明确，适合作为热血卡点主段落。"
  }
}
```

## Agentic Search API

`POST /api/v1/search/agentic`

说明：Agentic Search 接口。内部必须由 LangGraph workflow 执行，使用 `AgentState` 与 `StateGraph` 编排 Query Rewrite、Retrieval、Rerank、Creative Suggestion、Reflection 与 Final Answer。

Request：

```json
{
  "request_id": "req_001",
  "thread_id": "thread_001",
  "session_id": "sess_001",
  "query_text": "帮我找适合做热血卡点的视频素材",
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
  "state_snapshot": {
    "query_text": "帮我找适合做热血卡点的视频素材",
    "rewritten_query": "热血 燃系 高能 快节奏 镜头切换明显 动作强 beat 匹配 团战 冲刺 反击 高潮片段",
    "expanded_queries": ["热血", "燃系", "高能", "快节奏", "镜头切换明显", "动作强", "beat 匹配", "团战", "冲刺", "反击", "高潮片段"],
    "retrieved_count": 20,
    "reranked_count": 5,
    "reflection_passed": true
  },
  "node_trace": [
    {
      "node_name": "QueryRewriteNode",
      "status": "succeeded",
      "latency_ms": 12
    },
    {
      "node_name": "RetrievalNode",
      "status": "succeeded",
      "latency_ms": 35
    },
    {
      "node_name": "RerankNode",
      "status": "succeeded",
      "latency_ms": 8
    },
    {
      "node_name": "CreativeSuggestionNode",
      "status": "succeeded",
      "latency_ms": 6
    },
    {
      "node_name": "ReflectionNode",
      "status": "succeeded",
      "latency_ms": 4
    },
    {
      "node_name": "FinalAnswerNode",
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
  "reflection_result": {
    "passed": true,
    "issues": []
  },
  "final_answer": {
    "summary": "推荐 42.5s 到 57.2s 的团战反击片段作为热血卡点主段落。",
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
