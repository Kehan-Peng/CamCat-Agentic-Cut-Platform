# AGENTS.md

## 1. Project Positioning

Nova Agent Platform is a LangGraph-based agentic workflow system for multimodal content search, retrieval, editing planning, and creative video generation.

This project is not a generic chat wrapper around video tools, and it is not a one-shot video search demo. The core engineering focus is the design of production-oriented agent workflows that coordinate retrieval, evidence grounding, editing-state mutation, and safe video export.

The system combines two prototype directions:

1. **Nova** provides multimodal search, hybrid retrieval, evidence-grounded answer generation, and LangGraph-backed agentic search.
2. **VideoCutGPT** contributes an editing-state-driven conversational editing model, where user dialogue mutates durable editing artifacts instead of blindly regenerating the whole video plan.

The final architecture should not overuse the term “Lead Agent” or “multi-agent group.” The top-level coordinator is the **LangGraph Coordinator Graph**. Domain capabilities are organized as subgraphs, nodes, tools, and deterministic services.

---

## 2. Core Architecture

```text
Nova LangGraph Coordinator Graph
├── Intent Routing Layer
│   ├── StateLoadNode
│   ├── IntentClassificationNode
│   ├── RouteDecisionNode
│   └── FinalResponseNode
│
├── Perception & Retrieval Subgraph
│   ├── MediaReadinessNode
│   ├── QueryRewriteNode
│   ├── HybridRetrievalNode
│   ├── CandidateEvidenceAttachNode
│   ├── RerankNode
│   ├── FinalEvidenceGroundingNode
│   ├── SearchQualityCheckNode
│   └── ConditionalRetryOrFinalize
│
├── Editing Planning Subgraph
│   ├── IntentToEditTaskNode
│   ├── EditingStateReadNode
│   ├── SegmentSelectionNode
│   ├── PlanDiffNode
│   ├── PatchValidationNode
│   ├── SubtitleDraftNode
│   ├── ClipPlanNode
│   ├── TitleTagNode
│   ├── ArtifactRefreshPlannerNode
│   ├── EditingPlanValidationNode
│   └── EditingStateUpdateNode
│
├── Media Workflow Control Nodes
│   ├── MediaWorkflowTriggerNode
│   ├── MediaWorkflowStatusNode
│   └── MediaWorkflowResultReadNode
│
└── Final Response Assembly
```

External deterministic services:

```text
Editing Execution Service
├── ClipSegmentDeriver
├── FFmpegCommandBuilder
├── RenderJobRunner
├── OutputVerifier
└── ExportMetadataWriter
```

Heavy media workflow:

```text
Media Processing Workflow DAG
├── MetadataExtractionTask
├── AudioExtractionTask → ASRTask
├── FrameExtractionTask → OCRTask / CaptionTask
├── SceneShotDetectionTask
├── SegmentBuilderTask
├── TextEmbeddingTask
├── VisualEmbeddingTask
├── IndexingTask
└── SearchableStatusTask
```

State persistence layer:

```text
State Persistence Layer
├── AgentState
├── GlobalEditingState
├── WorkflowArtifactStatus
├── MediaWorkflowRun
├── RenderJob
├── ClipSegments
├── EditedVideoArtifact
├── GraphRun
└── NodeTrace
```



### 2.1 Coordinator Graph Conditional Routing

The Coordinator Graph is not a linear chain. It is a conditional LangGraph workflow.

Primary flow:

```text
START
→ StateLoadNode
→ IntentClassificationNode
→ RouteDecisionNode
→ conditional route
```

`RouteDecisionNode` must return one of the following route targets:

```text
retrieval_only
editing_only
retrieval_then_editing
media_processing_required
media_processing_then_retrieval
media_processing_then_editing
export_only
clarification_required
finalize_with_error
```

Conditional edges:

```text
RouteDecisionNode
├── retrieval_only → Perception & Retrieval Subgraph
├── editing_only → Editing Planning Subgraph
├── retrieval_then_editing → Perception & Retrieval Subgraph → Editing Planning Subgraph
├── media_processing_required → Media Workflow Control Nodes
├── media_processing_then_retrieval → Media Workflow Control Nodes → Perception & Retrieval Subgraph
├── media_processing_then_editing → Media Workflow Control Nodes → Editing Planning Subgraph
├── export_only → Editing Execution Service trigger/status flow
├── clarification_required → FinalResponseNode
└── finalize_with_error → FinalResponseNode
```

The Coordinator Graph must support composite intents. For example:

```text
帮我找热血片段，并剪成 30 秒短视频
```

should route through:

```text
Perception & Retrieval Subgraph
→ Editing Planning Subgraph
→ FinalResponseNode
```

rather than forcing a single-intent route.

### 2.2 Media Workflow Control Node Routing

Media Workflow Control Nodes are part of the Coordinator Graph, but they do not execute heavy media processing directly.

They are responsible for:

- checking whether a video is already processed and searchable;
- triggering media processing workflow if required;
- reading workflow status;
- returning a deferred, partial, or ready state to the Coordinator Graph.

They may be reached in two ways:

1. directly from `RouteDecisionNode` when the user intent requires unprocessed media;
2. indirectly from `MediaReadinessNode` when retrieval or editing requires artifacts that are not ready.

Rules:

- LangGraph nodes must not run ASR, OCR, embedding, ffmpeg, or rendering directly.
- Heavy processing must be delegated to the `Media Processing Workflow DAG`.
- The Coordinator Graph only triggers, polls, reads, and summarizes workflow state.

---

## 3. Non-Negotiable Design Principles

### 3.1 LangGraph is the orchestration layer

LangGraph is responsible for agent workflow orchestration, state transition, conditional routing, checkpointing, and node trace.

LangGraph must not become a place where retrieval, media processing, or rendering logic is rewritten. Each node should be a thin orchestration unit that reads and writes `AgentState`, then calls an existing domain service.

### 3.2 Retrieval quality must be quantified

The retrieval subgraph must not use open-ended reflection loops. Search quality is evaluated through explicit metrics and retry budgets.

`SearchQualityCheckNode` performs quantified quality evaluation.

`ConditionalRetryOrFinalize` performs bounded retry or exits with best-effort results.

### 3.3 Editing should mutate state through patches

The editing planning subgraph must not regenerate the full editing plan for every user instruction.

`PlanDiffNode` converts a new user instruction into a minimal `EditingStatePatch`.

`PatchValidationNode` validates the patch.

`ArtifactRefreshPlannerNode` decides which artifacts need refresh.

`EditingStateUpdateNode` commits the update atomically with version checks.

### 3.4 Rendering is deterministic execution, not agent reasoning

FFmpeg rendering, output verification, metadata writing, and sandboxed execution belong to the Editing Execution Service. These are not LangGraph reasoning nodes.

LangGraph may trigger render jobs, inspect render status, and summarize results. It must not directly execute FFmpeg in the agent graph.

### 3.5 Heavy media processing is a DAG

Keyframe extraction, audio extraction, ASR, OCR, captioning, embedding, and indexing must be modeled as a dependency-aware workflow DAG, not as a flat task list.

Indexing must not run before segment building and embeddings are available. ASR must not run before audio extraction. OCR and captioning must not run before frame extraction.

---

## 4. Intent Routing Layer

### 4.1 StateLoadNode

Responsibilities:

- Load `AgentState` from request input and checkpoint if available.
- Load user/session context.
- Load relevant `GlobalEditingState` when the request belongs to an editing session.
- Ensure user-scoped access control.

Inputs:

- `user_id`
- `session_id`
- `thread_id`
- `query_text`
- optional `editing_session_id`
- optional `video_id`

Outputs:

- initialized `AgentState`
- optional `GlobalEditingState`
- access-control metadata

Non-goals:

- Do not classify user intent.
- Do not run retrieval.
- Do not mutate persistent editing state.

### 4.2 IntentClassificationNode

Responsibilities:

- Identify whether the user wants retrieval, editing, media processing, export, clarification, or a combined flow.
- Produce a route decision with confidence.

Production rule:

Use a rule-based fast path first. Use an LLM or model-based classifier only for ambiguous requests.

Output schema:

```json
{
  "intent": "retrieval_then_editing",
  "confidence": 0.86,
  "route_targets": ["perception_retrieval", "editing_planning"],
  "requires_clarification": false,
  "reason": "User asks to find clips and create an edited short video."
}
```

Latency and cost controls:

- Rule fast path should be the default.
- LLM fallback must have a latency budget.
- Low-confidence classification should route to clarification rather than unsafe execution.
- Classification outputs must be logged in `node_trace`.

### 4.3 RouteDecisionNode

Supported routes:

```text
retrieval_only
editing_only
retrieval_then_editing
media_processing_then_retrieval
media_processing_then_editing
export_only
clarification_required
```

Routing must support multi-step composite requests, such as:

```text
帮我找热血片段，并剪成 30 秒短视频
```

This should route through retrieval first, then editing planning.

### 4.4 FinalResponseNode

Responsibilities:

- Normalize successful, partial, and failed subgraph outputs.
- Aggregate user-facing results.
- Preserve key backward-compatible API fields.
- Report workflow status when results are not ready.
- Return next actionable steps.

Final response should never fabricate unavailable media, segments, evidence, or render artifacts.

---

## 5. Perception & Retrieval Subgraph

```text
Perception & Retrieval Subgraph
├── MediaReadinessNode
├── QueryRewriteNode
├── HybridRetrievalNode
├── CandidateEvidenceAttachNode
├── RerankNode
├── FinalEvidenceGroundingNode
├── SearchQualityCheckNode
└── ConditionalRetryOrFinalize
```

### 5.1 MediaReadinessNode

Responsibilities:

- Check whether the requested video or asset library is indexed and searchable.
- If media is not ready, trigger or reference the media processing workflow.
- Return `workflow_id`, `status`, and readiness metadata.

This node must not perform keyframe extraction, ASR, OCR, captioning, embedding, or indexing directly.

### 5.2 QueryRewriteNode

Responsibilities:

- Convert user query into structured retrieval intent.
- Expand query terms for text, visual, motion, tag, and editing needs.
- Preserve the original query.

Example input:

```text
帮我找适合做热血卡点的视频素材
```

Example expansions:

```text
热血, 燃系, 高能, 快节奏, 镜头切换明显, 动作强, beat 匹配, 团战, 冲刺, 反击, 高潮片段
```

Non-goals:

- Do not invent specific brands, products, BGM names, people, scenes, or facts not present in user input or evidence.

### 5.3 HybridRetrievalNode

Responsibilities:

- Execute BM25-like lexical search.
- Execute deterministic or production dense retrieval through adapter interfaces.
- Apply metadata filters.
- Fuse candidates through hybrid score fusion.

Inputs:

- `rewritten_query`
- `expanded_queries`
- `filters`
- `search_scope`
- `top_k`
- `retrieval_mode`

Outputs:

- `retrieved_results`
- channel-level scores
- retrieval debug info

### 5.4 CandidateEvidenceAttachNode

Responsibilities:

- Attach available ASR, OCR, caption, tag, score, and metadata evidence to candidates.
- Prepare evidence features for reranking.

This node provides evidence for ranking. It is not the final answer grounding layer.

### 5.5 RerankNode

Responsibilities:

- Reorder candidates using lexical score, dense score, evidence quality, tag match, motion score, highlight score, and query intent.
- Preserve original channel scores for explainability.

Outputs:

- `reranked_results`
- rerank score breakdown

### 5.6 FinalEvidenceGroundingNode

Responsibilities:

- Build final grounded evidence for each returned segment.
- Ensure reasons only reference real evidence.
- Reject or mark ungrounded explanations.

Evidence sources:

- ASR chunks
- OCR blocks
- frame captions
- tags
- motion/highlight scores
- metadata

### 5.7 SearchQualityCheckNode

Responsibilities:

Perform quantified retrieval quality evaluation. This node must not be an open-ended LLM reflection step.

Inputs:

```text
query_text
rewritten_query
expanded_queries
retrieval_results
reranked_results
evidence
filters
top_k
attempt_count
latency_so_far_ms
cost_so_far
```

Outputs:

```json
{
  "passed": true,
  "quality_score": 0.82,
  "issues": [],
  "retry_action": "finalize",
  "retry_reason": null,
  "metrics": {
    "result_count": 5,
    "top_score": 0.91,
    "avg_topk_score": 0.77,
    "evidence_coverage": 1.0,
    "timestamp_coverage": 1.0,
    "diversity_score": 0.64,
    "query_match_score": 0.83
  }
}
```

Minimum quality metrics:

```text
result_count >= min_results
top_score >= min_top_score
avg_topk_score >= min_avg_score
evidence_coverage >= min_evidence_coverage
timestamp_coverage == 1.0
grounding_passed == true
```

Optional advanced metrics:

```text
diversity_score
modality_coverage
query_intent_match_score
rerank_confidence
duplicate_ratio
```

### 5.8 ConditionalRetryOrFinalize

Responsibilities:

- Decide whether to finalize, retry with a bounded action, ask for clarification, or return best-effort results.
- Enforce retry budgets.

Required budget fields:

```text
retrieval_attempt_count
max_retrieval_attempts
latency_budget_ms
llm_call_budget
retry_history
```

Retry policy:

```text
if passed:
    finalize
elif attempt_count >= max_retrieval_attempts:
    finalize with partial result or no-result explanation
elif latency_budget_exceeded:
    finalize with best-effort result
elif issue == no_results:
    relax_filters or rewrite query
elif issue == low_evidence_coverage:
    rerun evidence-heavy retrieval or grounding
elif issue == low_semantic_match:
    rewrite query
elif issue == duplicate_results:
    diversity rerank
else:
    finalize with explanation
```

No unbounded reflection loops are allowed.

---

## 6. Editing Planning Subgraph

```text
Editing Planning Subgraph
├── IntentToEditTaskNode
├── EditingStateReadNode
├── SegmentSelectionNode
├── PlanDiffNode
├── PatchValidationNode
├── SubtitleDraftNode
├── ClipPlanNode
├── TitleTagNode
├── ArtifactRefreshPlannerNode
├── EditingPlanValidationNode
└── EditingStateUpdateNode
```

### 6.1 IntentToEditTaskNode

Responsibilities:

- Convert user instruction into a structured editing task.
- Distinguish between clip generation, subtitle editing, title/tag update, export request, or style revision.

Example instructions:

```text
剪成 30 秒热血卡点短视频
把开头改得更抓人一点
第二段删掉
字幕更短
导出一个 TikTok 快节奏版本
```

### 6.2 EditingStateReadNode

Responsibilities:

- Load `GlobalEditingState`.
- Load artifact statuses.
- Load selected segments and previous editing decisions.
- Validate user ownership.

### 6.3 SegmentSelectionNode

Responsibilities:

- Select candidate segments for editing.
- Reuse retrieval results when available.
- Avoid selecting unavailable or unauthorized segments.

Outputs:

- selected segment IDs
- segment evidence summaries
- selection reason

### 6.4 PlanDiffNode

Responsibilities:

Convert user instruction into a minimal state patch. It must not regenerate the entire editing plan unless the user explicitly requests a full restart.

Input:

```json
{
  "editing_session_id": "edit_001",
  "user_instruction": "把开头改得更抓人一点，第二段删掉，字幕短一点",
  "previous_global_editing_state": {
    "selected_segments": ["seg_1", "seg_2", "seg_3"],
    "subtitle_draft": "...",
    "editing_plan": "...",
    "clip_segments": ["clip_1", "clip_2", "clip_3"],
    "title_candidates": ["..."],
    "artifact_status": {
      "subtitle_draft": "ready",
      "clip_segments": "ready",
      "edited_video": "stale"
    },
    "state_version": 7
  },
  "available_segments": [],
  "current_render_jobs": []
}
```

Output:

```json
{
  "patch_id": "patch_008",
  "base_state_version": 7,
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
  "needs_refresh": {
    "editing_plan": true,
    "clip_segments": true,
    "subtitle_draft": true,
    "edited_video": true,
    "title_candidates": false
  },
  "requires_retrieval": false,
  "requires_render": true
}
```

Supported patch operations:

```text
add_segment
remove_segment
replace_segment
reorder_segments
trim_segment
update_subtitle_style
update_title_style
update_bgm_style
update_transition_style
update_hook
update_clip_duration
mark_artifact_stale
```

Full regeneration is allowed only when the user explicitly asks for it, such as:

```text
全部重来，换一个风格
```

In that case, the patch must explicitly mark:

```json
{
  "patch_type": "full_regeneration",
  "reason": "user explicitly requested complete rewrite",
  "requires_user_confirmation": true
}
```

### 6.5 PatchValidationNode

Responsibilities:

- Validate operation schema.
- Reject deletion of nonexistent clip segments.
- Reject invalid segment IDs.
- Reject unsafe or unsupported edit operations.
- Ensure `base_state_version` is present.

### 6.6 SubtitleDraftNode

Responsibilities:

- Generate or update subtitle drafts based on selected segments and patch operations.
- Respect subtitle style constraints.

### 6.7 ClipPlanNode

Responsibilities:

- Generate or update shot-level editing plan.
- Convert editing intent into timeline-level structure.
- Preserve previous plan sections when patch does not affect them.

### 6.8 TitleTagNode

Responsibilities:

- Generate title candidates and tags.
- May run in parallel with subtitle drafting if it only depends on selected segments.
- Must wait for clip plan if title/tag generation depends on final clip structure.

### 6.9 ArtifactRefreshPlannerNode

Responsibilities:

- Decide which artifacts need refresh.
- Avoid unnecessary recomputation.
- Mark stale artifacts explicitly.

Artifacts:

```text
subtitle_draft
editing_plan
clip_segments
title_candidates
tag_candidates
edited_video
preview_video
```

### 6.10 EditingPlanValidationNode

Responsibilities:

- Validate editing plan consistency.
- Ensure clip durations are valid.
- Ensure segment boundaries exist.
- Ensure references point to available source media.
- Ensure render job can be generated.

### 6.11 EditingStateUpdateNode

Responsibilities:

- Atomically commit patch and refreshed artifacts.
- Enforce optimistic locking with `state_version`.
- Update artifact status and `needs_refresh` flags.

Required consistency check:

```text
base_state_version == current_state_version
```

If conflict occurs:

```text
state_conflict → ReloadStateNode → RebasePatchNode → Retry or AskUser
```

---

## 7. Editing Execution Service

The Editing Execution Service is an external deterministic service, not an agent node.

### 7.1 ClipSegmentDeriver

Responsibilities:

- Convert validated editing plan into executable `ClipSegment` records.
- Map source timeline to output timeline.
- Ensure clip boundaries are valid.

### 7.2 FFmpegCommandBuilder

Responsibilities:

- Build safe FFmpeg argument lists.
- Never build shell strings from raw user input.
- Validate all input and output paths.
- Restrict filters to a safe whitelist.

Security rules:

```text
use argument list, not shell string
validate file paths
restrict input/output directories
escape or reject unsafe metadata
deny arbitrary filters unless whitelisted
```

### 7.3 RenderJobRunner

Responsibilities:

- Execute render jobs asynchronously.
- Run in an isolated sandbox.
- Enforce resource limits.

Required controls:

```text
timeout
CPU / memory limit
disk quota
output size limit
sandbox workdir
cancellation
retry policy
job lease / heartbeat
```

### 7.4 OutputVerifier

Responsibilities:

Validate rendered output:

```text
file exists
file size > minimum threshold
duration matches expected range
codec readable
no zero-frame output
audio/video stream valid
checksum recorded
preview generation succeeded
```

### 7.5 ExportMetadataWriter

Responsibilities:

- Persist `EditedVideoArtifact`.
- Link output artifact to render job, editing session, and source media.
- Update workflow artifact status.

---

## 8. Media Processing Workflow DAG

Heavy video processing is not part of the online agent graph.

Recommended DAG:

```text
Upload / StoreOriginal
        ↓
MetadataExtractionTask
        ↓
 ┌───────────────┬─────────────────┐
 │               │                 │
AudioExtraction  FrameExtraction   SceneShotDetection
 │               │                 │
ASRTask          OCRTask            SegmentBoundaryTask
                 CaptionTask        │
 │               │                 │
 └───────────────┴───────────────┬─┘
                                 ↓
                         SegmentBuilderTask
                                 ↓
              ┌──────────────────┴──────────────────┐
              │                                     │
        TextEmbeddingTask                    VisualEmbeddingTask
              │                                     │
              └──────────────────┬──────────────────┘
                                 ↓
                         IndexingTask
                                 ↓
                         SearchableStatusTask
```

Dependencies:

```text
ASRTask depends on AudioExtractionTask
OCRTask and CaptionTask depend on FrameExtractionTask
SegmentBuilderTask depends on ASR/OCR/Caption/SceneShot availability
TextEmbeddingTask depends on segment text
VisualEmbeddingTask depends on representative frames
IndexingTask depends on segment + embeddings + metadata
```

Workflow task fields:

```text
task_id
workflow_id
task_type
status
attempt
max_attempts
input_hash
output_ref
error
started_at
finished_at
depends_on
```

The workflow must support partial success:

```text
partially_searchable
searchable_with_missing_ocr
searchable_with_missing_caption
searchable_with_text_only_embedding
```

---

## 9. State Models

### 9.1 AgentState

Runtime state for a LangGraph execution.

Recommended fields:

```text
graph_run_id
thread_id
user_id
session_id
query_text
intent
route_targets
retrieval_state
editing_state_ref
node_trace
errors
final_response
```

AgentState is ephemeral and checkpointable. It is not the durable editing source of truth.

### 9.2 GlobalEditingState

Durable state for an editing session.

Recommended fields:

```text
editing_session_id
user_id
video_id
state_version
current_goal
selected_segments
subtitle_draft
editing_plan
clip_segments
title_candidates
tag_candidates
render_jobs
artifact_status
needs_refresh
last_user_revision
updated_at
```

### 9.3 WorkflowArtifactStatus

Tracks whether artifacts are ready, stale, blocked, failed, exportable, or missing.

Suggested statuses:

```text
missing
requested
running
ready
stale
blocked
failed
exportable
```

### 9.4 RenderJob

Fields:

```text
render_job_id
editing_session_id
status
input_clip_segments
ffmpeg_args_ref
sandbox_id
output_uri
error
attempt
created_at
updated_at
```

### 9.5 EditedVideoArtifact

Fields:

```text
edited_video_id
editing_session_id
render_job_id
output_uri
preview_uri
duration_seconds
checksum
metadata
created_at
```

---

## 10. API Expectations

### 10.1 Agentic Search

`POST /api/v1/search/agentic`

Should return:

```text
graph_run_id
thread_id
state_snapshot
node_trace
rewritten_query
retrieved_segments
reranked_segments
search_quality_report
final_answer
creative_suggestions
```

### 10.2 Editing Session APIs

Planned APIs:

```text
POST /api/v1/editing/sessions
GET /api/v1/editing/sessions/{editing_session_id}
POST /api/v1/editing/sessions/{editing_session_id}/message
GET /api/v1/editing/sessions/{editing_session_id}/events
POST /api/v1/editing/sessions/{editing_session_id}/render
GET /api/v1/editing/sessions/{editing_session_id}/render-jobs/{render_job_id}
GET /api/v1/editing/sessions/{editing_session_id}/exported-video
```

### 10.3 Event Stream

SSE events should include:

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

---

## 11. Testing Requirements

### 11.1 Retrieval Subgraph Tests

Must cover:

- Query rewrite output.
- Hybrid retrieval ordering.
- Evidence attachment.
- Rerank score stability.
- Grounding validation.
- Search quality metrics.
- Retry budget enforcement.
- Best-effort fallback after budget exhaustion.

### 11.2 Editing Planning Tests

Must cover:

- Reading `GlobalEditingState`.
- Generating minimal `EditingStatePatch`.
- Rejecting invalid patch operations.
- Preserving unaffected artifacts.
- Marking affected artifacts stale.
- Atomic state update with version check.
- State conflict behavior.

### 11.3 Editing Execution Tests

Must cover:

- Clip segment derivation.
- Safe FFmpeg command argument construction.
- Path validation.
- Render job creation.
- Output verification success and failure.
- Export metadata writing.

### 11.4 Media Workflow DAG Tests

Must cover:

- Task dependency ordering.
- No indexing before embeddings.
- No ASR before audio extraction.
- Partial success behavior.
- Retry and idempotency.

### 11.5 E2E Tests

Must cover:

```text
upload → media readiness → retrieval → quality check → editing plan patch → state update → render job creation
```

and:

```text
follow-up edit instruction → PlanDiffNode → patch validation → artifact refresh → state version update
```

---

## 12. Development Rules for AI Coding Agents

When using AI coding agents or Superpowers-style development:

1. Follow the current architecture in this document.
2. Do not introduce open-ended LLM retry loops.
3. Do not implement rendering inside LangGraph nodes.
4. Do not regenerate the entire editing plan when a minimal patch is sufficient.
5. Do not bypass `PatchValidationNode` or `EditingPlanValidationNode`.
6. Do not write stale or invalid artifacts into `GlobalEditingState`.
7. Do not add Phase 4 infrastructure unless explicitly requested.
8. Keep tests deterministic.
9. Preserve API backward compatibility.
10. Prefer thin nodes and domain services over fat nodes.
11. Add tests before production code.
12. Run full tests after every task.

Stop and ask for human approval if:

- A new dependency beyond the current phase is required.
- API compatibility needs to break.
- A LangGraph node would need to execute long-running media processing.
- Rendering would require unsafe shell execution.
- PlanDiff cannot express the requested edit without full regeneration.
- State version conflict cannot be resolved deterministically.
- Search retry budget is insufficient but no safe fallback exists.

---

## 13. Final Design Decision

The final Nova + VideoCutGPT architecture is:

> LangGraph Coordinator Graph for intent routing, state transition, retrieval, and editing planning; external deterministic services for rendering and media processing; durable `GlobalEditingState` and workflow artifact status for conversational editing continuity; quantified retrieval quality checks and bounded retry policies for production-grade search reliability.

This design intentionally avoids vague multi-agent hierarchy. It uses LangGraph for explicit workflow orchestration, keeps retrieval and editing services testable, and preserves production boundaries around state, rendering, and heavy media workflows.
