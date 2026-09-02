import type {
  AgenticSearchResponse as AgenticSearchDto,
  EditingSessionResponse as EditingSessionDto,
  JobResponse as JobDto,
  SourceMediaReference as SourceMediaDto,
  SourceUploadResponse as SourceUploadDto,
} from "./generated/api";

export type FetchLike = typeof fetch;

export type UploadedVideoResponse = {
  video_id: string;
  status: string;
  filename: string;
  job_id?: string;
  segment_count: number;
  duration_seconds?: number;
  playback_url?: string;
  error?: string;
};

export type SourceMediaReference = SourceMediaDto & {
  media_id: string;
  filename: string;
  content_type: string;
  storage_key: string;
  expires_at: string;
  duration_seconds?: number;
  width?: number;
  height?: number;
  has_audio?: boolean;
  playback_url?: string;
};

export type SourceUploadResponse = Omit<SourceUploadDto, "media"> & {
  batch_id: string;
  status: string;
  job_id: string;
  expires_at: string;
  media: SourceMediaReference[];
};

export type AgentProgressEvent = {
  event: string;
  graph_run_id?: string;
  node?: string;
  status?: string;
  duration_ms?: number;
  message: string;
  session?: EditingSessionResponse;
  agent_run?: AgenticSearchResponse;
};

export type RankedSegment = {
  segment_id: string;
  video_id: string;
  start_time: number;
  end_time: number;
  score: number;
  reranker_score: number;
  caption: string;
  tags: string[];
  route_scores: Record<string, number>;
  route_ranks: Record<string, number>;
  thumbnail_url?: string;
  source_video_url?: string;
  event_type?: string;
  risk_score: number;
  semantic_metadata: Record<string, unknown>;
  license_name: string;
  source_url: string;
};

export type NodeTraceItem = {
  node_name?: string;
  name?: string;
  status?: string;
  duration_ms?: number;
  elapsed_ms?: number;
};

export type AgenticSearchResponse = Omit<AgenticSearchDto, "node_trace" | "ranked_segments"> & {
  graph_run_id: string;
  thread_id: string;
  final_answer: string;
  route_sequence: string[];
  node_trace: NodeTraceItem[];
  ranked_segments: RankedSegment[];
};

export type EditingState = {
  title?: string;
  goal?: string;
  target_duration?: number;
  clips?: Array<Record<string, unknown>>;
  subtitles?: Array<Record<string, unknown>>;
  settings?: Record<string, unknown>;
};

export type EditingSessionResponse = Omit<EditingSessionDto, "state"> & {
  editing_session_id: string;
  state_version: number;
  state: EditingState;
  updated_at?: string;
};

export type JobResponse = Omit<JobDto, "status" | "result"> & {
  job_id: string;
  kind?: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled" | "dead_letter";
  progress: number;
  result?: {
    output_url?: string;
    subtitle_url?: string;
    duration_seconds?: number;
    file_size?: number;
    width?: number;
    height?: number;
    [key: string]: unknown;
  };
  error?: string;
};

export type RenderJobResponse = JobResponse;

export type AuditEvent = {
  audit_event_id: string;
  event_type: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type WorkspaceEvidenceItem = {
  id: string;
  title: string;
  meta: string;
  kind: "video" | "doc" | "image";
  active?: boolean;
  thumbnail?: string;
  videoId?: string;
  segmentId?: string;
  sourceVideoUrl?: string;
  startTime?: number;
  endTime?: number;
  score?: number;
};

export type WorkspaceTraceRow = {
  time: string;
  name: string;
  status: "done" | "running";
  elapsed?: string;
};

export type WorkspaceRunView = {
  evidence: WorkspaceEvidenceItem[];
  trace: WorkspaceTraceRow[];
  selectedSegment?: RankedSegment;
  finalAnswer: string;
  routeLabel: string;
};

type ClientOptions = { baseUrl: string; userId: string; fetchImpl?: FetchLike };
type RequestOptions = {
  method: "GET" | "POST" | "PATCH";
  body?: BodyInit | string;
  headers?: Record<string, string>;
};

export function createCamCatApiClient({ baseUrl, userId, fetchImpl = fetch }: ClientOptions) {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  async function requestJson<T>(path: string, options: RequestOptions): Promise<T> {
    const response = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      method: options.method,
      body: options.body,
      headers: { "X-User-Id": userId, ...options.headers },
    });
    const payload = await readJson(response);
    if (!response.ok) {
      throw new Error(`${options.method} ${path} failed: ${extractErrorDetail(payload)}`);
    }
    return payload as T;
  }

  function json<T>(path: string, method: "POST" | "PATCH", body: unknown) {
    return requestJson<T>(path, {
      method,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  return {
    uploadSourceMedia(files: File[], analysisMode: "keyframes" | "per-second" = "keyframes") {
      const form = new FormData();
      files.forEach((file) => form.append("files", file));
      form.append("analysis_mode", analysisMode);
      return requestJson<SourceUploadResponse>("/api/v1/source-media", {
        method: "POST",
        body: form,
      });
    },

    uploadVideo(
      file: File,
      provenance: { licenseName: string; sourceUrl: string } = {
        licenseName: "user-provided",
        sourceUrl: "local://user-upload",
      },
      analysisMode: "keyframes" | "per-second" = "keyframes",
    ) {
      const form = new FormData();
      form.append("file", file);
      form.append("license_name", provenance.licenseName);
      form.append("source_url", provenance.sourceUrl);
      form.append("analysis_mode", analysisMode);
      return requestJson<UploadedVideoResponse>("/api/v1/videos", { method: "POST", body: form });
    },

    getVideo(videoId: string) {
      return requestJson<UploadedVideoResponse>(`/api/v1/videos/${encodeURIComponent(videoId)}`, {
        method: "GET",
      });
    },

    getJob(jobId: string) {
      return requestJson<JobResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}`, { method: "GET" });
    },

    runAgenticSearch(queryText: string, topK = 8, queryImageBase64?: string) {
      return json<AgenticSearchResponse>("/api/v1/search/agentic", "POST", {
        query_text: queryText || undefined,
        query_image_base64: queryImageBase64,
        top_k: topK,
        retrieval_mode: "multimodal",
        thread_id: `web_${Date.now()}`,
      });
    },

    createEditingSession(
      videoId: string | undefined,
      currentGoal: string,
      sourceJobId?: string,
    ) {
      return json<EditingSessionResponse>("/api/v1/editing/sessions", "POST", {
        video_id: videoId,
        source_job_id: sourceJobId,
        current_goal: currentGoal,
      });
    },

    getEditingSession(editingSessionId: string) {
      return requestJson<EditingSessionResponse>(
        `/api/v1/editing/sessions/${encodeURIComponent(editingSessionId)}`,
        { method: "GET" },
      );
    },

    getEditingSessionAudit(editingSessionId: string) {
      return requestJson<{ items: AuditEvent[]; next_cursor?: string }>(
        `/api/v1/editing/sessions/${encodeURIComponent(editingSessionId)}/audit`,
        { method: "GET" },
      );
    },

    patchEditingSession(
      editingSessionId: string,
      baseVersion: number,
      operations: Array<{ op: "add" | "replace" | "remove"; path: string; value?: unknown }>,
      reason: string,
    ) {
      return json<EditingSessionResponse>(
        `/api/v1/editing/sessions/${encodeURIComponent(editingSessionId)}`,
        "PATCH",
        { base_version: baseVersion, operations, reason },
      );
    },

    runEditingAgent(
      editingSessionId: string,
      baseVersion: number,
      instruction: string,
      queryImageBase64?: string,
    ) {
      return json<EditingSessionResponse>(
        `/api/v1/editing/sessions/${encodeURIComponent(editingSessionId)}/agent`,
        "POST",
        { base_version: baseVersion, instruction, query_image_base64: queryImageBase64 },
      );
    },

    async runEditingAgentStream(
      editingSessionId: string,
      baseVersion: number,
      instruction: string,
      onEvent: (event: AgentProgressEvent) => void,
      queryImageBase64?: string,
      topK = 12,
    ) {
      const path = `/api/v1/editing/sessions/${encodeURIComponent(editingSessionId)}/agent/stream`;
      const response = await fetchImpl(`${normalizedBaseUrl}${path}`, {
        method: "POST",
        headers: { "X-User-Id": userId, "content-type": "application/json" },
        body: JSON.stringify({
          base_version: baseVersion,
          instruction,
          query_image_base64: queryImageBase64,
          top_k: topK,
        }),
      });
      if (!response.ok) {
        const payload = await readJson(response);
        throw new Error(`POST ${path} failed: ${extractErrorDetail(payload)}`);
      }
      if (!response.body) throw new Error("Agent 进度流不可用");
      let completed: EditingSessionResponse | undefined;
      let agentRun: AgenticSearchResponse | undefined;
      let graphRunId: string | undefined;
      try {
        for await (const event of parseServerSentEvents(response.body)) {
          const progress = { event: event.event, ...JSON.parse(event.data) } as AgentProgressEvent;
          graphRunId = progress.graph_run_id ?? graphRunId;
          onEvent(progress);
          if (progress.event === "failed") throw new Error(progress.message);
          if (progress.event === "completed") {
            completed = progress.session;
            agentRun = progress.agent_run;
          }
        }
        if (!completed) throw new Error("Agent 进度流提前中断");
      } catch (error) {
        if (!graphRunId) throw error;
        for (let attempt = 0; attempt < 120; attempt += 1) {
          const run = await requestJson<{ status: string; editing_session_id?: string }>(
            `/api/v1/graph-runs/${encodeURIComponent(graphRunId)}`,
            { method: "GET" },
          );
          if (run.status === "failed") throw error;
          if (run.status === "succeeded" && run.editing_session_id) {
            completed = await requestJson<EditingSessionResponse>(
              `/api/v1/editing/sessions/${encodeURIComponent(run.editing_session_id)}`,
              { method: "GET" },
            );
            agentRun = await requestJson<AgenticSearchResponse>(
              `/api/v1/graph-runs/${encodeURIComponent(graphRunId)}/search-result`,
              { method: "GET" },
            );
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
      }
      if (!completed) throw new Error("Agent 进度流在返回剪辑状态前中断");
      if (!agentRun) throw new Error("Agent 进度流未返回本轮检索证据");
      return { session: completed, agentRun };
    },

    rollbackEditingSession(editingSessionId: string, baseVersion: number, targetVersion: number) {
      return json<EditingSessionResponse>(
        `/api/v1/editing/sessions/${encodeURIComponent(editingSessionId)}/rollback`,
        "POST",
        { base_version: baseVersion, target_version: targetVersion },
      );
    },

    renderEditingSession(editingSessionId: string, baseVersion: number) {
      return json<JobResponse>(
        `/api/v1/editing/sessions/${encodeURIComponent(editingSessionId)}/render`,
        "POST",
        { base_version: baseVersion, burn_subtitles: true },
      );
    },
  };
}

export async function waitForJob(
  getJob: (jobId: string) => Promise<JobResponse>,
  jobId: string,
  options: {
    intervalMs?: number;
    timeoutMs?: number;
    onProgress?: (job: JobResponse) => void;
  } = {},
) {
  const intervalMs = options.intervalMs ?? 1000;
  const deadline = Date.now() + (options.timeoutMs ?? 20 * 60 * 1000);
  while (Date.now() < deadline) {
    const job = await getJob(jobId);
    options.onProgress?.(job);
    if (job.status === "succeeded") return job;
    if (job.status === "failed" || job.status === "cancelled" || job.status === "dead_letter") {
      throw new Error(job.error || `job ${jobId} ${job.status}`);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`job ${jobId} timed out`);
}

type SearchAndPlanApi = Pick<
  ReturnType<typeof createCamCatApiClient>,
  "createEditingSession" | "runEditingAgentStream"
>;

export async function runSearchAndPlan(
  api: SearchAndPlanApi,
  options: {
    query: string;
    uploadedVideoId?: string;
    sourceJobId?: string;
    currentSession?: EditingSessionResponse;
    queryImageBase64?: string;
    topK?: number;
    onAgentEvent?: (event: AgentProgressEvent) => void;
  },
) {
  const sourceVideoId = options.uploadedVideoId;
  if (!sourceVideoId && !options.sourceJobId && !options.currentSession) {
    throw new Error("请先上传一个或多个用户原片。");
  }

  const session =
    options.currentSession ??
    (await api.createEditingSession(sourceVideoId, options.query, options.sourceJobId));
  const completed = await api.runEditingAgentStream(
    session.editing_session_id,
    session.state_version,
    options.query,
    options.onAgentEvent ?? (() => undefined),
    options.queryImageBase64,
    options.topK ?? 8,
  );
  return { agentRun: completed.agentRun, editingSession: completed.session };
}

export async function* parseServerSentEvents(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<{ event: string; data: string; id?: string }> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = block.match(/^event:\s*(.+)$/m)?.[1] ?? "message";
        const id = block.match(/^id:\s*(.+)$/m)?.[1];
        const data = block
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (data) yield { event, data, id };
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
}

export function mapAgenticRunToWorkspace(run: AgenticSearchResponse): WorkspaceRunView {
  const rankedSegments = run.ranked_segments ?? [];
  return {
    evidence: rankedSegments.map((segment, index) => ({
      id: segment.segment_id,
      title: segment.caption || segment.segment_id,
      meta: `${formatClock(segment.start_time)}-${formatClock(segment.end_time)} · score ${formatScore(segment.reranker_score)} · ${segment.license_name || "license unknown"}`,
      kind: "video",
      active: index === 0,
      thumbnail: segment.thumbnail_url,
      videoId: segment.video_id,
      segmentId: segment.segment_id,
      sourceVideoUrl: segment.source_video_url,
      startTime: segment.start_time,
      endTime: segment.end_time,
      score: segment.reranker_score,
    })),
    trace: (run.node_trace ?? []).map((item, index) => ({
      time: index === 0 ? "now" : `+${index}`,
      name: item.node_name ?? item.name ?? `node_${index + 1}`,
      status: item.status === "running" ? "running" : "done",
      elapsed:
        typeof item.duration_ms === "number"
          ? `${Math.round(item.duration_ms)}ms`
          : typeof item.elapsed_ms === "number"
            ? `${Math.round(item.elapsed_ms)}ms`
            : undefined,
    })),
    selectedSegment: rankedSegments[0],
    finalAnswer: run.final_answer ?? "已完成本轮素材理解与检索。",
    routeLabel: run.route_sequence?.join(" → ") ?? "multimodal_retrieval",
  };
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function extractErrorDetail(payload: unknown) {
  if (payload && typeof payload === "object") {
    if ("error" in payload) {
      const error = (payload as { error?: { message?: unknown } }).error;
      if (typeof error?.message === "string") return error.message;
    }
    if ("detail" in payload) {
      const detail = (payload as { detail?: unknown }).detail;
      return typeof detail === "string" ? detail : JSON.stringify(detail);
    }
  }
  return "Unexpected backend error";
}

function formatClock(value: number) {
  const bounded = Math.max(0, Math.floor(value));
  return `${String(Math.floor(bounded / 60)).padStart(2, "0")}:${String(bounded % 60).padStart(2, "0")}`;
}

function formatScore(value?: number) {
  return typeof value === "number" ? value.toFixed(2) : "n/a";
}
