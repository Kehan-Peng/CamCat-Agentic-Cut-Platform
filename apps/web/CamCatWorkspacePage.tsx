import React, { useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowUp,
  Boxes,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock3,
  Download,
  FileText,
  Filter,
  Folder,
  HelpCircle,
  Image as ImageIcon,
  Loader2,
  Maximize2,
  Mic,
  MoreHorizontal,
  PanelRight,
  Play,
  Plus,
  Scissors,
  Search,
  Settings,
  Share2,
  SkipBack,
  SkipForward,
  Sparkles,
  StepBack,
  StepForward,
  Upload,
  User,
  Volume2,
} from "lucide-react";
import {
  createCamCatApiClient,
  mapAgenticRunToWorkspace,
  runSearchAndPlan,
  userFacingErrorMessage,
  waitForJob,
  type AgenticSearchResponse,
  type AuditEvent,
  type EditingSessionResponse,
  type JobResponse,
  type ProjectResponse,
  type RenderJobResponse,
  type SourceUploadResponse,
  type UploadedVideoResponse,
  type WorkspaceTraceRow,
} from "./src/camcatApi";

type EvidenceKind = "video" | "doc" | "image";

type EvidenceItem = {
  id: string;
  title: string;
  meta: string;
  kind: EvidenceKind;
  active?: boolean;
  thumbnail?: string;
  videoId?: string;
  segmentId?: string;
  sourceVideoUrl?: string;
  startTime?: number;
  endTime?: number;
  score?: number;
};

type TimelineClip = {
  id: string;
  label: string;
  start: number;
  end: number;
  tone?: "neutral" | "blue" | "green";
};

type WorkspaceStatus = "idle" | "uploading" | "searching" | "rendering" | "ready" | "error";
export type ProductPage = "editing" | "processing" | "render";

type WorkspaceController = {
  apiBase: string;
  query: string;
  setQuery: (value: string) => void;
  status: WorkspaceStatus;
  error?: string;
  progress?: number;
  progressLabel?: string;
  searchDepth: "instant" | "deep";
  setSearchDepth: (value: "instant" | "deep") => void;
  analysisMode: "keyframes" | "per-second";
  setAnalysisMode: (value: "keyframes" | "per-second") => void;
  uploadedVideo?: UploadedVideoResponse;
  sourceUpload?: SourceUploadResponse;
  agentRun?: AgenticSearchResponse;
  renderResult?: RenderJobResponse;
  activeJob?: JobResponse;
  editingSession?: EditingSessionResponse;
  project?: ProjectResponse;
  page: ProductPage;
  auditEvents: AuditEvent[];
  queryImageName?: string;
  evidence: EvidenceItem[];
  traceRows: WorkspaceTraceRow[];
  canRender: boolean;
  selectedEvidenceId?: string;
  handleSelectEvidence: (item: EvidenceItem) => void;
  handleUpload: (files: File[]) => Promise<void>;
  handleSearch: () => Promise<void>;
  handleRender: () => Promise<void>;
  handleQueryImage: (file: File) => Promise<void>;
  handleRollback: () => Promise<void>;
  handleReorderClip: (sourceId: string, targetId: string) => Promise<void>;
  handleTrimClip: (clipId: string) => Promise<void>;
  handleSplitClip: (clipId: string) => Promise<void>;
  showEditingPage: () => void;
  showProcessingPage: () => void;
  showRenderPage: () => void;
  handleCancelJob: () => Promise<void>;
  handleRetryJob: () => Promise<void>;
  onBack?: () => void;
};

const workflowSteps = ["Ingest", "Understand", "Plan", "Edit", "Render", "Review", "Export"];

const waveform = [
  18, 32, 54, 41, 24, 46, 68, 76, 44, 30, 52, 72, 84, 60, 38, 24, 42, 58, 78,
  88, 70, 45, 28, 36, 62, 80, 90, 66, 48, 34, 22, 40, 64, 82, 74, 56, 32, 26,
  44, 72, 86, 68, 50, 30, 24, 38, 60, 78, 92, 74, 52, 34, 28, 46, 66, 80, 62,
  42, 25, 35, 58, 74, 86, 70, 44, 30, 22, 40, 62, 76, 58, 36, 26, 44, 64, 82,
  76, 54, 32, 24, 36, 56, 70, 60, 42, 28, 22, 34, 48,
];

export type CamCatWorkspacePageProps = {
  project?: ProjectResponse;
  initialSession?: EditingSessionResponse;
  initialPage?: ProductPage;
  onBack?: () => void;
};

export default function CamCatWorkspacePage(props: CamCatWorkspacePageProps) {
  const workspace = useWorkspaceController(props);

  return <AppShell workspace={workspace} />;
}

function useWorkspaceController({ project, initialSession, initialPage = "editing", onBack }: CamCatWorkspacePageProps): WorkspaceController {
  const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {};
  const apiBase = env.VITE_CAMCAT_API_BASE || "";
  const userId = env.VITE_CAMCAT_USER_ID ?? "camcat-local-user";
  const api = useMemo(() => createCamCatApiClient({ baseUrl: apiBase, userId }), [apiBase, userId]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<WorkspaceStatus>("idle");
  const [error, setError] = useState<string>();
  const [progress, setProgress] = useState<number>();
  const [progressLabel, setProgressLabel] = useState<string>();
  const [searchDepth, setSearchDepth] = useState<"instant" | "deep">("instant");
  const [analysisMode, setAnalysisMode] = useState<"keyframes" | "per-second">("keyframes");
  const initialSourceMedia = initialSession?.state.source_media ?? [];
  const initialSourceSegments = initialSession?.state.source_segments ?? [];
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | undefined>(initialSourceMedia[0]?.media_id);
  const [uploadedVideo, setUploadedVideo] = useState<UploadedVideoResponse | undefined>(() => {
    const first = initialSourceMedia[0];
    if (!first) return undefined;
    return {
      video_id: first.media_id,
      filename: first.filename,
      status: "ready",
      segment_count: initialSourceSegments.length,
      duration_seconds: initialSourceMedia.reduce((sum, item) => sum + (item.duration_seconds ?? 0), 0),
      playback_url: first.playback_url,
    };
  });
  const [sourceUpload, setSourceUpload] = useState<SourceUploadResponse>();
  const [liveTraceRows, setLiveTraceRows] = useState<WorkspaceTraceRow[]>([]);
  const [agentRun, setAgentRun] = useState<AgenticSearchResponse>();
  const [renderResult, setRenderResult] = useState<RenderJobResponse>();
  const [activeJob, setActiveJob] = useState<JobResponse>();
  const [page, setPage] = useState<ProductPage>(initialPage);
  const [editingSession, setEditingSession] = useState<EditingSessionResponse | undefined>(initialSession);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [queryImageBase64, setQueryImageBase64] = useState<string>();
  const [queryImageName, setQueryImageName] = useState<string>();

  const runView = useMemo(() => (agentRun ? mapAgenticRunToWorkspace(agentRun) : undefined), [agentRun]);
  const evidence = useMemo<EvidenceItem[]>(() => {
    const sourceMedia = sourceUpload?.media ?? editingSession?.state.source_media ?? [];
    const uploadedEvidence: EvidenceItem[] = sourceMedia.length
      ? sourceMedia.map((media, index) => ({
          id: media.media_id,
          title: media.filename,
          meta: `用户原片 ${index + 1}/${sourceMedia.length} · 临时保留 4 小时`,
          kind: "video" as const,
          active: selectedEvidenceId
            ? selectedEvidenceId === media.media_id
            : !runView?.evidence.length && index === 0,
          sourceVideoUrl: media.playback_url,
        }))
      : [];

    return runView?.evidence.length
      ? (runView.evidence as EvidenceItem[]).map((item, index) => ({
          ...item,
          active: selectedEvidenceId ? item.id === selectedEvidenceId : index === 0,
        }))
      : uploadedEvidence;
  }, [editingSession?.state.source_media, runView, selectedEvidenceId, sourceUpload]);

  const traceRows = useMemo<WorkspaceTraceRow[]>(() => {
    const rows = runView?.trace.length ? runView.trace : [];
    if (uploadedVideo) {
      return [
        {
          time: "now",
          name: `media_workflow:${uploadedVideo.status ?? "uploaded"}`,
          status: uploadedVideo.status === "processing" ? "running" : "done",
        },
        ...liveTraceRows,
        ...rows,
      ];
    }
    return [...liveTraceRows, ...rows];
  }, [liveTraceRows, runView, uploadedVideo]);

  const canRender = Boolean(runView?.selectedSegment?.video_id || editingSession?.state.clips?.length);

  async function handleUpload(files: File[]) {
    if (!files.length) return;
    setStatus("uploading");
    setError(undefined);
    setProgress(0);
    setProgressLabel("正在上传素材");
    setRenderResult(undefined);
    setPage("processing");

    try {
      const result = await api.uploadSourceMedia(files, analysisMode);
      setSourceUpload(result);
      setActiveJob(await api.getJob(result.job_id));
      const analysis = await waitForJob(api.getJob, result.job_id, {
            onProgress: (job) => {
              setActiveJob(job);
              setProgress(job.progress);
              setProgressLabel(
                job.status === "queued"
                  ? "等待原片分析 Worker"
                  : `正在检测场景、质量、重复镜头和语音 ${Math.round(job.progress * 100)}%`,
              );
            },
          });
      const analyzedMedia = (analysis.result?.source_media as SourceUploadResponse["media"] | undefined) ?? result.media;
      const completedUpload = { ...result, status: "succeeded", media: analyzedMedia };
      setSourceUpload(completedUpload);
      const first = analyzedMedia[0];
      const completed: UploadedVideoResponse = {
        video_id: first.media_id,
        filename: files.length === 1 ? first.filename : `${first.filename} 等 ${files.length} 个原片`,
        status: "ready",
        segment_count: Number(analysis.result?.segment_count ?? 0),
        duration_seconds: analyzedMedia.reduce((sum, item) => sum + (item.duration_seconds ?? 0), 0),
        playback_url: first.playback_url,
      };
      setUploadedVideo(completed);
      setSelectedEvidenceId(first.media_id);
      setProgress(1);
      setProgressLabel(`已分析 ${completed.segment_count} 个原片镜头；未写入素材库或向量库`);
      setStatus("ready");
    } catch (caught) {
      setError(errorMessage(caught));
      setStatus("error");
    }
  }

  async function handleSearch() {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("请输入需要检索或剪辑的需求。");
      setStatus("error");
      return;
    }

    setStatus("searching");
    setError(undefined);
    setRenderResult(undefined);

    try {
      setProgress(undefined);
      setLiveTraceRows([]);
      setProgressLabel("正在理解发布目标与叙事意图");
      const result = await runSearchAndPlan(api, {
        query: trimmedQuery,
        sourceJobId: sourceUpload?.job_id,
        projectId: project?.project_id,
        currentSession: editingSession,
        queryImageBase64,
        topK: searchDepth === "deep" ? 16 : 8,
        onAgentEvent: (event) => {
          setProgressLabel(event.message);
          if (event.node) {
            setLiveTraceRows((previous) => [
              ...previous.filter((item) => item.name !== event.node),
              {
                time: "now",
                name: event.node!,
                status: event.status === "completed" ? "done" : "running",
                elapsed: event.duration_ms ? `${Math.round(event.duration_ms)}ms` : undefined,
              },
            ]);
          }
        },
      });
      setAgentRun(result.agentRun);
      setEditingSession(result.editingSession);
      const audit = await api.getEditingSessionAudit(result.editingSession.editing_session_id);
      setAuditEvents(audit.items);
      setSelectedEvidenceId(result.agentRun.ranked_segments?.[0]?.segment_id);
      setProgressLabel("剪辑计划已通过 State Patch 写入");
      setStatus("ready");
    } catch (caught) {
      setError(errorMessage(caught));
      setStatus("error");
    }
  }

  async function handleRender() {
    const selectedSegment = runView?.selectedSegment;
    const sourceVideoId = selectedSegment?.video_id;

    if (!editingSession && (!selectedSegment || !sourceVideoId)) {
      setError("请先完成素材检索，再生成剪辑计划与 FFmpeg 输出。");
      setStatus("error");
      return;
    }

    setStatus("rendering");
    setError(undefined);
    setPage("render");

    try {
      let session = editingSession;
      if (!session) {
        session = await api.createEditingSession(sourceVideoId, query, sourceUpload?.job_id, project?.project_id);
        const completed = await api.runEditingAgentStream(
          session.editing_session_id,
          session.state_version,
          query,
          (event) => setProgressLabel(event.message),
          queryImageBase64,
        );
        session = completed.session;
        setAgentRun(completed.agentRun);
        setEditingSession(session);
      }
      const queued = await api.renderEditingSession(session.editing_session_id, session.state_version);
      setActiveJob(queued);
      const result = await waitForJob(api.getJob, queued.job_id, {
        onProgress: (job) => {
          setActiveJob(job);
          setProgress(job.progress);
          setProgressLabel(`FFmpeg 正在生成成片 ${Math.round(job.progress * 100)}%`);
        },
      });
      setRenderResult(result);
      setProgressLabel("FFmpeg 成片、SRT 与 ffprobe 元数据已生成");
      setStatus("ready");
    } catch (caught) {
      setError(errorMessage(caught));
      setStatus("error");
    }
  }

  async function handleCancelJob() {
    if (!activeJob || !["queued", "running"].includes(activeJob.status)) return;
    try {
      const cancelled = await api.cancelJob(activeJob.job_id);
      setActiveJob(cancelled);
      setError("任务已取消，可以返回编辑或重试。");
      setStatus("error");
    } catch (caught) {
      setError(errorMessage(caught));
      setStatus("error");
    }
  }

  async function handleRetryJob() {
    if (!activeJob || !["failed", "cancelled", "dead_letter"].includes(activeJob.status)) return;
    setError(undefined);
    setStatus(activeJob.kind === "render" ? "rendering" : "uploading");
    try {
      const queued = await api.retryJob(activeJob.job_id);
      setActiveJob(queued);
      const completed = await waitForJob(api.getJob, queued.job_id, {
        onProgress: (job) => {
          setActiveJob(job);
          setProgress(job.progress);
        },
      });
      setActiveJob(completed);
      if (completed.kind === "render") setRenderResult(completed);
      setStatus("ready");
    } catch (caught) {
      setError(errorMessage(caught));
      setStatus("error");
    }
  }

  async function handleQueryImage(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("查询参考图必须是图片文件。");
      setStatus("error");
      return;
    }
    setQueryImageBase64(await fileToDataUrl(file));
    setQueryImageName(file.name);
    setError(undefined);
  }

  async function handleRollback() {
    if (!editingSession || editingSession.state_version <= 1) return;
    setStatus("searching");
    try {
      const rolledBack = await api.rollbackEditingSession(
        editingSession.editing_session_id,
        editingSession.state_version,
        editingSession.state_version - 1,
      );
      setEditingSession(rolledBack);
      const audit = await api.getEditingSessionAudit(rolledBack.editing_session_id);
      setAuditEvents(audit.items);
      setStatus("ready");
    } catch (caught) {
      setError(errorMessage(caught));
      setStatus("error");
    }
  }

  async function persistClips(clips: Array<Record<string, unknown>>, reason: string) {
    if (!editingSession) return;
    let cursor = 0;
    const sequenced = clips.map((clip) => {
      const duration = Number(clip.source_end) - Number(clip.source_start);
      const next = { ...clip, output_start: cursor, output_end: cursor + duration };
      cursor += duration;
      return next;
    });
    const updated = await api.patchEditingSession(
      editingSession.editing_session_id,
      editingSession.state_version,
      [
        { op: "replace", path: "/clips", value: sequenced },
        { op: "replace", path: "/target_duration", value: cursor },
      ],
      reason,
    );
    setEditingSession(updated);
    const audit = await api.getEditingSessionAudit(updated.editing_session_id);
    setAuditEvents(audit.items);
  }

  async function handleReorderClip(sourceId: string, targetId: string) {
    const clips = [...(editingSession?.state.clips ?? [])];
    const sourceIndex = clips.findIndex((clip) => String(clip.clip_id) === sourceId);
    const targetIndex = clips.findIndex((clip) => String(clip.clip_id) === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
    const [moved] = clips.splice(sourceIndex, 1);
    clips.splice(targetIndex, 0, moved);
    await persistClips(clips, "timeline drag reorder");
  }

  async function handleTrimClip(clipId: string) {
    const clips = (editingSession?.state.clips ?? []).map((clip) => ({ ...clip }));
    const clip = clips.find((item) => String(item.clip_id) === clipId);
    if (!clip) return;
    const start = Number(clip.source_start);
    const end = Number(clip.source_end);
    clip.source_end = Math.max(start + 0.2, end - 0.5);
    await persistClips(clips, "timeline trim clip tail");
  }

  async function handleSplitClip(clipId: string) {
    const clips = (editingSession?.state.clips ?? []).map((clip) => ({ ...clip }));
    const index = clips.findIndex((item) => String(item.clip_id) === clipId);
    if (index < 0) return;
    const clip = clips[index];
    const start = Number(clip.source_start);
    const end = Number(clip.source_end);
    if (end - start < 0.4) return;
    const middle = (start + end) / 2;
    clips.splice(
      index,
      1,
      { ...clip, clip_id: `${clipId}-a`, source_end: middle },
      { ...clip, clip_id: `${clipId}-b`, source_start: middle },
    );
    await persistClips(clips, "timeline split clip");
  }

  function handleSelectEvidence(item: EvidenceItem) {
    setSelectedEvidenceId(item.id);
    document.getElementById("editor-workspace")?.scrollIntoView({ behavior: "smooth" });
  }

  return {
    apiBase,
    query,
    setQuery,
    status,
    error,
    progress,
    progressLabel,
    searchDepth,
    setSearchDepth,
    analysisMode,
    setAnalysisMode,
    uploadedVideo,
    sourceUpload,
    agentRun,
    renderResult,
    activeJob,
    editingSession,
    project,
    page,
    auditEvents,
    queryImageName,
    evidence,
    traceRows,
    canRender,
    selectedEvidenceId,
    handleSelectEvidence,
    handleUpload,
    handleSearch,
    handleRender,
    handleQueryImage,
    handleRollback,
    handleReorderClip,
    handleTrimClip,
    handleSplitClip,
    showEditingPage: () => setPage("editing"),
    showProcessingPage: () => setPage("processing"),
    showRenderPage: () => setPage("render"),
    handleCancelJob,
    handleRetryJob,
    onBack,
  };
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("读取参考图片失败"));
    reader.readAsDataURL(file);
  });
}

async function copyText(value: string) {
  try {
    await navigator.clipboard.writeText(value);
    return;
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    if (!copied) throw new Error("浏览器未授权剪贴板访问");
  }
}

function MediaProcessingPage({ workspace }: { workspace: WorkspaceController }) {
  const job = workspace.activeJob?.kind === "analyze_source" ? workspace.activeJob : undefined;
  const complete = job?.status === "succeeded" || workspace.uploadedVideo?.status === "ready";
  const progress = complete ? 1 : Math.max(0, Math.min(1, job?.progress ?? workspace.progress ?? 0));
  const failed = workspace.status === "error" || Boolean(job && ["failed", "cancelled", "dead_letter"].includes(job.status));
  const stages = [
    { label: "上传与 MIME / FFprobe 预检", detail: "用户原片仅作 4 小时临时输入", threshold: 0 },
    { label: "场景边界与片段提取", detail: "场景优先切分与事件上下文", threshold: 0.08 },
    { label: "ASR 语音识别", detail: "仅对包含音轨的片段执行", threshold: 0.22 },
    { label: "缩略图与镜头去重", detail: "生成临时证据和镜头签名", threshold: 0.42 },
    { label: "质量评分与结构化分析", detail: "画面质量、时长与来源边界", threshold: 0.65 },
    { label: "可编辑状态", detail: "不创建 Asset，不写入 Milvus", threshold: 1 },
  ];

  return (
    <ProductPageFrame title="媒体处理状态" subtitle={workspace.project?.name ?? "CamCat 项目"}>
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(380px,0.9fr)_minmax(460px,1.1fr)] gap-5 overflow-hidden px-8 pb-8">
        <section className="min-h-0 overflow-y-auto rounded-[20px] border border-[#272b2f] bg-[#090a0b] p-7">
          <div className="flex items-center justify-between border-b border-[#22262a] pb-5">
            <div>
              <div className="text-[11px] font-semibold tracking-[0.18em] text-[#737d87]">MEDIA PIPELINE</div>
              <h2 className="mt-2 text-xl font-semibold text-white">{workspace.sourceUpload?.media[0]?.filename ?? workspace.editingSession?.state.source_media?.[0]?.filename ?? "准备接收原片"}</h2>
            </div>
            <JobStatusBadge status={job?.status ?? workspace.status} />
          </div>
          <div className="mt-5 space-y-1">
            {stages.map((stage, index) => {
              const done = complete || (progress > stage.threshold && index < stages.length - 1);
              const active = !complete && !failed && progress >= stage.threshold && (index === stages.length - 1 || progress < stages[index + 1].threshold);
              return (
                <div key={stage.label} className="relative flex gap-4 pb-6 last:pb-0">
                  {index < stages.length - 1 && <span className={`absolute left-[15px] top-8 h-[calc(100%-22px)] w-px ${done ? "bg-[#34d399]/50" : "bg-[#30363b]"}`} />}
                  <span className={`relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full border ${done ? "border-[#2f765e] bg-[#123025] text-[#6ee7b7]" : active ? "border-[#60a5fa] bg-[#12243b] text-[#93c5fd]" : "border-[#343a40] bg-[#111315] text-[#69727c]"}`}>
                    {done ? <Check className="h-4 w-4 stroke-[3]" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : <MoreHorizontal className="h-4 w-4" />}
                  </span>
                  <div className="min-w-0 pt-1">
                    <div className={`text-[14px] font-medium ${done ? "text-[#c7f9e5]" : active ? "text-white" : "text-[#7c858e]"}`}>{stage.label}</div>
                    <div className="mt-1 text-[11px] text-[#68717b]">{stage.detail}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="min-h-0 overflow-y-auto rounded-[20px] border border-[#272b2f] bg-[#090a0b] p-8">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-[11px] font-semibold tracking-[0.18em] text-[#737d87]">CURRENT TASK</div>
              <h2 className="mt-3 text-2xl font-semibold text-white">{complete ? "原片分析已完成" : failed ? "处理需要介入" : "正在分析用户原片"}</h2>
            </div>
            <span className="font-mono text-3xl font-semibold text-white">{Math.round(progress * 100)}%</span>
          </div>
          <div className="mt-8 h-2 overflow-hidden rounded-full bg-[#24282c]">
            <div className={`h-full rounded-full transition-all duration-500 ${failed ? "bg-[#ef4444]" : "bg-[#45d69a]"}`} style={{ width: `${progress * 100}%` }} />
          </div>
          <p className="mt-4 min-h-6 text-[13px] text-[#9aa3ac]">{workspace.error ?? workspace.progressLabel ?? "等待 Worker 返回真实进度"}</p>
          <dl className="mt-8 grid grid-cols-[150px_1fr] gap-y-5 border-t border-[#22262a] pt-7 text-[13px]">
            <dt className="text-[#707983]">任务 ID</dt><dd className="truncate font-mono text-[#d7dde2]">{job?.job_id ?? (complete ? "历史任务已完成" : "等待创建")}</dd>
            <dt className="text-[#707983]">任务类型</dt><dd className="text-[#d7dde2]">{job?.kind ?? "analyze_source"}</dd>
            <dt className="text-[#707983]">尝试次数</dt><dd className="text-[#d7dde2]">{job ? `${job.attempts}/${job.max_attempts}` : "0/3"}</dd>
            <dt className="text-[#707983]">媒体数量</dt><dd className="text-[#d7dde2]">{workspace.sourceUpload?.media.length ?? workspace.editingSession?.state.source_media?.length ?? 0}</dd>
            <dt className="text-[#707983]">分析镜头</dt><dd className="text-[#d7dde2]">{workspace.uploadedVideo?.segment_count ?? (job?.result?.segment_count === undefined ? "处理中" : String(job.result.segment_count))}</dd>
            <dt className="text-[#707983]">保留策略</dt><dd className="text-[#34d399]">transient-4h-no-asset-no-milvus</dd>
          </dl>
          <div className="mt-10 flex flex-wrap gap-3">
            {complete && <button type="button" onClick={workspace.showEditingPage} className="rounded-[12px] bg-[#f5f7f8] px-5 py-3 text-[13px] font-semibold text-black hover:bg-white">进入编辑计划</button>}
            {failed && <button type="button" onClick={() => void workspace.handleRetryJob()} className="rounded-[12px] bg-[#f5f7f8] px-5 py-3 text-[13px] font-semibold text-black hover:bg-white">重试任务</button>}
            {!complete && !failed && <button type="button" onClick={() => void workspace.handleCancelJob()} className="rounded-[12px] border border-[#33383d] bg-[#111315] px-5 py-3 text-[13px] text-[#cbd3da] hover:bg-[#17191b]">取消处理</button>}
            <button type="button" onClick={workspace.showEditingPage} className="rounded-[12px] border border-[#33383d] bg-[#111315] px-5 py-3 text-[13px] text-[#cbd3da] hover:bg-[#17191b]">返回工作区</button>
          </div>
        </section>
      </div>
    </ProductPageFrame>
  );
}

function RenderStatusPage({ workspace }: { workspace: WorkspaceController }) {
  const [copyLabel, setCopyLabel] = useState("复制链接");
  const job = workspace.activeJob?.kind === "render" ? workspace.activeJob : undefined;
  const output = workspace.renderResult?.result;
  const progress = Math.max(0, Math.min(1, job?.progress ?? workspace.progress ?? 0));
  const complete = workspace.renderResult?.status === "succeeded";
  const failed = workspace.status === "error" || Boolean(job && ["failed", "cancelled", "dead_letter"].includes(job.status));
  const outputUrl = output?.output_url;
  const resolution = output?.width && output?.height
    ? `${output.width} × ${output.height}`
    : String(workspace.editingSession?.state.settings?.aspect_ratio ?? "自动画幅");
  return (
    <ProductPageFrame title="导出 / 渲染状态" subtitle={workspace.project?.name ?? "CamCat 项目"}>
      <div className="min-h-0 flex-1 px-8 pb-8">
        <section className="mx-auto flex h-full max-w-[1320px] flex-col rounded-[22px] border border-[#292d31] bg-[#090a0b] p-8 shadow-[0_30px_100px_rgba(0,0,0,0.35)]">
          <div className="flex items-center justify-between border-b border-[#22262a] pb-6">
            <div>
              <div className="text-[11px] font-semibold tracking-[0.18em] text-[#737d87]">RENDER JOB</div>
              <h2 className="mt-2 text-xl font-semibold text-white">{job ? `render_${job.job_id.slice(0, 8)}` : "当前版本尚未渲染"}</h2>
            </div>
            <JobStatusBadge status={job?.status ?? workspace.status} />
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-[0.85fr_1.15fr] gap-10 pt-8">
            <div className="flex min-h-0 flex-col">
              <div className="flex items-end justify-between">
                <div className="text-3xl font-semibold text-white">{complete ? "渲染完成" : failed ? "渲染失败" : job ? "渲染中" : "等待渲染"}</div>
                <div className="font-mono text-3xl font-semibold text-white">{Math.round(progress * 100)}%</div>
              </div>
              <div className="mt-7 h-3 overflow-hidden rounded-full bg-[#24282c]"><div className={`h-full rounded-full transition-all duration-500 ${failed ? "bg-[#ef4444]" : "bg-[#45d69a]"}`} style={{ width: `${progress * 100}%` }} /></div>
              <p className="mt-4 text-[13px] text-[#929ca5]">{workspace.error ?? workspace.progressLabel ?? (job ? "正在等待 FFmpeg Worker" : "当前剪辑版本已就绪，确认后开始真实 FFmpeg 渲染")}</p>
              <dl className="mt-8 grid grid-cols-[110px_1fr] gap-y-5 border-t border-[#22262a] pt-7 text-[14px]">
                <dt className="text-[#707983]">状态版本</dt><dd className="text-white">v{workspace.editingSession?.state_version ?? 1}</dd>
                <dt className="text-[#707983]">输出画幅</dt><dd className="text-white">{resolution}</dd>
                <dt className="text-[#707983]">时长</dt><dd className="text-white">{output?.duration_seconds ? `${output.duration_seconds.toFixed(2)} 秒` : `${Number(workspace.editingSession?.state.target_duration ?? 0).toFixed(1)} 秒`}</dd>
                <dt className="text-[#707983]">字幕</dt><dd className="text-white">{output?.subtitle_url ? "SRT 已生成并烧录" : "根据剪辑计划烧录"}</dd>
                <dt className="text-[#707983]">处理器</dt><dd className="font-mono text-white">FFmpeg / ffprobe</dd>
              </dl>
              <div className="mt-auto flex flex-wrap gap-3 pt-8">
                {complete && <button type="button" onClick={workspace.showEditingPage} className="rounded-[12px] bg-[#f5f7f8] px-5 py-3 text-[13px] font-semibold text-black hover:bg-white">确认并返回编辑</button>}
                {!job && !failed && <button type="button" onClick={() => void workspace.handleRender()} disabled={!workspace.canRender} className="rounded-[12px] bg-[#f5f7f8] px-5 py-3 text-[13px] font-semibold text-black hover:bg-white disabled:cursor-not-allowed disabled:opacity-40">开始渲染</button>}
                {failed && <button type="button" onClick={() => void workspace.handleRetryJob()} className="rounded-[12px] bg-[#f5f7f8] px-5 py-3 text-[13px] font-semibold text-black hover:bg-white">重试渲染</button>}
                {job && !complete && !failed && <button type="button" onClick={() => void workspace.handleCancelJob()} className="rounded-[12px] border border-[#33383d] bg-[#111315] px-5 py-3 text-[13px] text-[#cbd3da] hover:bg-[#17191b]">取消渲染</button>}
                <button type="button" onClick={workspace.showEditingPage} className="rounded-[12px] border border-[#33383d] bg-[#111315] px-5 py-3 text-[13px] text-[#cbd3da] hover:bg-[#17191b]">返回编辑</button>
              </div>
            </div>
            <div className="flex min-h-0 flex-col">
              <div className="mb-3 text-[13px] text-[#8f99a3]">成片预览</div>
              <div className="grid min-h-[360px] flex-1 place-items-center overflow-hidden rounded-[18px] border border-[#282d31] bg-black">
                {outputUrl ? <video data-testid="render-output-video" src={outputUrl} controls playsInline className="h-full max-h-[560px] w-full object-contain" /> : <div className="flex flex-col items-center gap-4 text-[#66707a]"><Loader2 className="h-10 w-10 animate-spin" /><span>{failed ? "未生成可播放产物" : "等待真实渲染产物"}</span></div>}
              </div>
              <div className="mt-4 flex items-center gap-3 rounded-[14px] border border-[#272b2f] bg-[#111315] p-3">
                <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-[#8a949e]">{outputUrl ?? "成功后返回 MinIO 短时签名地址"}</span>
                <button type="button" disabled={!outputUrl} onClick={() => { if (!outputUrl) return; void copyText(outputUrl).then(() => { setCopyLabel("已复制"); window.setTimeout(() => setCopyLabel("复制链接"), 1600); }); }} className="rounded-[10px] border border-[#343a40] px-4 py-2 text-[12px] text-white disabled:opacity-40">{copyLabel}</button>
                <a href={output?.download_url ?? outputUrl} download aria-disabled={!outputUrl} className="rounded-[10px] bg-[#f5f7f8] px-4 py-2 text-[12px] font-semibold text-black aria-disabled:pointer-events-none aria-disabled:opacity-40">下载</a>
              </div>
            </div>
          </div>
        </section>
      </div>
    </ProductPageFrame>
  );
}

function ProductPageFrame({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <main data-testid="product-content" className="flex min-h-0 w-full max-w-[1444px] flex-col overflow-hidden border-r border-[#1b1d1f] bg-[radial-gradient(circle_at_50%_-20%,#111820_0%,#050607_42%,#030404_100%)] text-[#c9d0d6]">
      <div className="px-8 py-6"><div className="text-[11px] font-semibold tracking-[0.24em] text-[#65707a]">CAMCAT WORKFLOW · {subtitle}</div><div className="mt-2 text-[28px] font-semibold text-white">{title}</div></div>
      {children}
    </main>
  );
}

function JobStatusBadge({ status }: { status: string }) {
  const failed = ["failed", "cancelled", "dead_letter", "error"].includes(status);
  const done = status === "succeeded" || status === "ready";
  return <span className={`rounded-full border px-3 py-1.5 font-mono text-[11px] ${failed ? "border-[#7f1d1d] bg-[#2a1010] text-[#fca5a5]" : done ? "border-[#235d48] bg-[#0d241b] text-[#6ee7b7]" : "border-[#1d4d68] bg-[#0b1d27] text-[#7dd3fc]"}`}>{status}</span>;
}

function AppShell({ workspace }: { workspace: WorkspaceController }) {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#030404] font-sans text-[12px] text-[#c9d0d6] antialiased">
      <TopHeader workspace={workspace} />
      <div className="grid min-h-0 flex-1" style={{ gridTemplateColumns: "96px minmax(0, 1fr)" }}>
        <ProductRail workspace={workspace} />
        {workspace.page === "processing" ? (
          <MediaProcessingPage workspace={workspace} />
        ) : workspace.page === "render" ? (
          <RenderStatusPage workspace={workspace} />
        ) : (
          <main className="grid min-h-0 grid-cols-[400px_minmax(600px,1fr)_540px] overflow-hidden bg-[#030404] max-[1500px]:grid-cols-[360px_minmax(560px,1fr)_500px] max-[1180px]:grid-cols-[340px_minmax(560px,1fr)]">
            <EvidencePanel workspace={workspace} />
            <EditorWorkspace workspace={workspace} />
            <AgentChatPanel workspace={workspace} />
          </main>
        )}
      </div>
    </div>
  );
}

function TopHeader({ workspace }: { workspace: WorkspaceController }) {
  const [shareLabel, setShareLabel] = useState("Share");
  const busy = workspace.status === "uploading" || workspace.status === "searching" || workspace.status === "rendering";
  const savedLabel =
    workspace.status === "ready"
      ? "Backend synced"
      : workspace.status === "error"
        ? "Needs attention"
        : "Not started";

  return (
    <header data-testid="app-header" className="grid h-[72px] shrink-0 grid-cols-[minmax(360px,1fr)_420px_minmax(360px,1fr)] items-center border-b border-[#1b1d1f] bg-[#050606] px-5 shadow-[0_1px_0_rgba(255,255,255,0.02)]">
      <div className="flex min-w-0 items-center gap-3">
        <button type="button" onClick={workspace.onBack} aria-label="返回项目列表" className="flex shrink-0 items-center gap-2 pr-2 text-white transition hover:opacity-80">
          <PixelCatLogo className="h-8 w-8" />
          <span className="text-[26px] font-black leading-none tracking-normal">CamCat</span>
        </button>
        <span className="h-5 w-px shrink-0 bg-[#25282b]" />
        <button
          type="button"
          onClick={() => document.getElementById("agent-query")?.focus()}
          title="在 Agent 输入框中修改当前剪辑目标"
          className="flex min-w-0 max-w-[390px] items-center gap-1.5 text-left text-[12px] text-[#d7dde2] transition hover:text-white"
        >
          <span className="truncate">{workspace.editingSession?.state.title ?? workspace.uploadedVideo?.filename ?? workspace.project?.name ?? "未命名剪辑"}</span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[#707983]" />
        </button>
        <span className="rounded-md border border-[#25282b] bg-[#111213] px-2 py-0.5 text-[10px] text-[#a9b0b8]">
          v{workspace.editingSession?.state_version ?? 1}
        </span>
        <span className={`text-[10px] ${workspace.status === "error" ? "text-[#fca5a5]" : "text-[#6b7280]"}`}>
          {savedLabel}
        </span>
      </div>

      <div className="flex flex-col items-center gap-2">
        <div className="flex items-center gap-2 text-[11px] text-[#737b84]">
          <span>Workflow</span>
          <span className="font-medium text-[#edf1f4]">
            {workspace.status === "idle" ? "Waiting for input" : workspace.status}
          </span>
        </div>
        <div className="flex items-center">
          {workflowSteps.map((step, index) => {
            const completed = workflowStepCompleted(step, workspace);
            const current = workflowStepCurrent(step, workspace);
            return (
              <React.Fragment key={step}>
                <span className={`grid h-4 w-4 place-items-center rounded-full border ${
                  completed
                    ? "border-white/20 bg-[#f5f7f8] text-[#050606] shadow-[0_0_12px_rgba(245,247,248,0.16)]"
                    : current
                      ? "border-[#6cc7ff]/70 bg-[#12202a] text-[#dff5ff]"
                      : "border-[#34383c] bg-[#0d0e0f] text-[#59616a]"
                }`}>
                  {completed ? <Check className="h-2.5 w-2.5 stroke-[3]" /> : <span className="h-1 w-1 rounded-full bg-current" />}
                </span>
                {index !== workflowSteps.length - 1 && <span className={`h-px w-9 ${completed ? "bg-[#d8dee3]/70" : "bg-[#2b3035]"}`} />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      <div className="flex items-center justify-end gap-2.5">
        <span className="hidden max-w-[180px] truncate rounded-full border border-[#202326] bg-[#090a0b] px-2.5 py-1 font-mono text-[10px] text-[#76808a] 2xl:inline">
          {workspace.apiBase}
        </span>
        <button
          type="button"
          onClick={async () => {
            await copyText(window.location.href);
            setShareLabel("Copied");
            window.setTimeout(() => setShareLabel("Share"), 1600);
          }}
          className="inline-flex h-9 items-center gap-2 rounded-[10px] border border-[#25282b] bg-[#0c0d0e] px-3.5 text-[12px] font-medium text-[#dce2e7] transition hover:border-[#34383c] hover:bg-[#121314]"
        >
          <Share2 className="h-3.5 w-3.5" />
          {shareLabel}
        </button>
        <button
          onClick={workspace.handleRender}
          disabled={!workspace.canRender || busy}
          className="inline-flex h-9 items-center gap-2 rounded-[10px] bg-[#f5f7f8] px-4 text-[12px] font-semibold text-[#060707] transition hover:bg-white disabled:cursor-not-allowed disabled:bg-[#2a2d31] disabled:text-[#7b838c]"
        >
          {workspace.status === "rendering" ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5" />
          )}
          {workspace.status === "rendering" ? "Rendering" : "Export"}
          <ChevronDown className="h-3.5 w-3.5 opacity-60" />
        </button>
        <div className="ml-2 flex h-10 items-center gap-2 rounded-full border border-[#202326] bg-[#0b0c0d] px-1.5 pr-3">
          <span className="grid h-7 w-7 place-items-center rounded-full bg-[#151719] ring-1 ring-white/10" aria-label="CamCat user avatar">
            <PixelCatLogo className="h-4 w-4" />
          </span>
          <span className="hidden text-[11px] font-medium text-[#dce2e7] xl:block">CamCat</span>
          <span className="h-1.5 w-1.5 rounded-full bg-[#34d399] shadow-[0_0_10px_rgba(52,211,153,0.45)]" />
        </div>
      </div>
    </header>
  );
}

function ProductRail({ workspace }: { workspace: WorkspaceController }) {
  const navItems = [
    { label: "项目列表", icon: BriefcaseBusiness, page: "projects" as const, action: workspace.onBack },
    { label: "媒体处理", icon: Activity, page: "processing" as const, action: workspace.showProcessingPage },
    { label: "编辑计划", icon: Scissors, page: "editing" as const, action: workspace.showEditingPage },
    { label: "导出渲染", icon: Download, page: "render" as const, action: workspace.showRenderPage },
  ];

  return (
    <aside data-testid="product-navigation" className="flex min-h-0 flex-col justify-between border-r border-[#1b1d1f] bg-[#050606]">
      <div>
        <nav className="space-y-2 px-2.5 pt-4">
          {navItems.map(({ label, icon: Icon, page, action }) => {
            const active = page === workspace.page;
            return (
            <button
              key={label}
              type="button"
              onClick={action}
              aria-label={label}
              aria-current={active ? "page" : undefined}
              className={`flex h-[64px] w-full flex-col items-center justify-center gap-1.5 rounded-[10px] border transition ${
                active
                  ? "border-[#2a2d31] bg-[#121314] text-[#f5f7f8] shadow-[0_12px_30px_rgba(0,0,0,0.22)]"
                  : "border-transparent text-[#69717b] hover:bg-[#0d0e0f] hover:text-[#c3cbd2]"
              }`}
            >
              <Icon className="h-4.5 w-4.5" />
              <span className="text-[10px]">{label}</span>
            </button>
          );})}
        </nav>
      </div>
      <div className="flex flex-col items-center gap-2 px-2.5 pb-4 text-[#6b7280]">
        <RailIcon icon={HelpCircle} label="API 帮助" onClick={() => window.open("/docs", "_blank")} />
        <RailIcon icon={Settings} label="后端状态" onClick={() => window.open("/health/ready", "_blank")} />
      </div>
    </aside>
  );
}

function EvidencePanel({ workspace }: { workspace: WorkspaceController }) {
  const [videoOnly, setVideoOnly] = useState(false);
  const visibleEvidence = videoOnly
    ? workspace.evidence.filter((item) => item.kind === "video")
    : workspace.evidence;
  const artifactCount =
    Number(Boolean(workspace.editingSession?.state.subtitles?.length)) +
    Number(Boolean(workspace.renderResult?.result?.output_url));
  return (
    <aside className="min-h-0 overflow-hidden border-r border-[#1b1d1f] bg-[#080909]">
      <div className="flex h-full flex-col overflow-y-auto px-4 py-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div id="evidence-section" />
        <PanelSectionHeader title="EVIDENCE" count={visibleEvidence.length} right={<EvidenceActions videoOnly={videoOnly} onToggleVideoOnly={() => setVideoOnly((value) => !value)} />} />
        <div className="space-y-3">
          {visibleEvidence.map((item) => (
            <EvidenceCard key={item.id} item={item} onSelect={() => workspace.handleSelectEvidence(item)} />
          ))}
          {!visibleEvidence.length && <EmptyPanel text="等待真实素材与任务" />}
        </div>

        <div id="state-section" />
        <PanelSectionHeader title="ROUTE / STATE" />
        <RouteStateCard workspace={workspace} />

        <div id="trace-section" />
        <PanelSectionHeader title="TRACE" right={workspace.traceRows.length ? <LiveBadge /> : undefined} />
        {workspace.traceRows.length ? (
          <TracePanel rows={workspace.traceRows} />
        ) : (
          <EmptyPanel text="尚无真实节点执行记录" />
        )}

        <div id="artifacts-section" />
        <PanelSectionHeader title="ARTIFACTS" count={artifactCount} />
        <ArtifactsPanel workspace={workspace} />
      </div>
    </aside>
  );
}

function EmptyPanel({ text }: { text: string }) {
  return (
    <div className="rounded-[12px] border border-dashed border-[#25282b] bg-[#090a0b] px-3 py-5 text-center text-[10px] text-[#69717b]">
      {text}
    </div>
  );
}

function PanelSectionHeader({
  title,
  count,
  right,
}: {
  title: string;
  count?: number;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-3 mt-5 first:mt-0 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <h2 className="text-[10px] font-semibold tracking-[0.2em] text-[#707983]">{title}</h2>
        {count !== undefined && (
          <span className="rounded-md border border-[#24272a] bg-[#111213] px-1.5 py-0.5 text-[9px] text-[#8b949e]">
            {count}
          </span>
        )}
      </div>
      {right}
    </div>
  );
}

function EvidenceActions({ videoOnly, onToggleVideoOnly }: { videoOnly: boolean; onToggleVideoOnly: () => void }) {
  return (
    <div className="flex items-center gap-1.5 text-[#737b84]">
      <SmallIconButton icon={Plus} label="上传视频" onClick={() => document.getElementById("video-upload")?.click()} />
      <SmallIconButton icon={Filter} label={videoOnly ? "显示全部素材" : "只显示视频"} onClick={onToggleVideoOnly} active={videoOnly} />
    </div>
  );
}

function EvidenceCard({ item, onSelect }: { item: EvidenceItem; onSelect: () => void }) {
  const Icon = item.kind === "doc" ? FileText : item.kind === "image" ? ImageIcon : Play;

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={item.active}
      className={`group w-full rounded-[12px] border bg-[#121314] p-2.5 text-left transition ${
        item.active
          ? "border-[#303438] shadow-[0_14px_40px_rgba(0,0,0,0.28)]"
          : "border-[#232628] hover:border-[#303438] hover:bg-[#141516]"
      }`}
    >
      <div className="flex gap-3">
        <div className="relative h-[60px] w-[110px] shrink-0 overflow-hidden rounded-[8px] border border-[#25282b] bg-[#080909]">
          {item.thumbnail ? (
            <img
              src={item.thumbnail}
              alt=""
              className="h-full w-full object-cover opacity-85 grayscale-[0.2] saturate-[0.85] transition group-hover:scale-105"
            />
          ) : (
            <div className="grid h-full w-full place-items-center bg-[linear-gradient(135deg,#181a1d,#090a0b)]">
              <Icon className="h-6 w-6 text-[#8b949e]" />
            </div>
          )}
          {item.kind === "video" && (
            <span className="absolute bottom-1.5 right-1.5 grid h-6 w-6 place-items-center rounded-full border border-white/10 bg-black/65 text-white backdrop-blur-sm">
              <Play className="ml-0.5 h-3 w-3 fill-current" />
            </span>
          )}
        </div>
        <div className="flex min-w-0 flex-1 flex-col justify-between py-0.5">
          <div>
            <div className="truncate text-[12px] font-medium text-[#f0f3f5]">{item.title}</div>
            <div className="mt-1 truncate text-[10px] text-[#78818b]">{item.meta}</div>
          </div>
          {item.kind === "video" ? <MiniWaveform /> : <DocPreviewLines />}
        </div>
      </div>
    </button>
  );
}

function MiniWaveform() {
  const bars = [18, 34, 26, 48, 56, 22, 36, 50, 42, 28, 20, 44, 58, 38, 24, 32, 46, 30];
  return (
    <div className="mt-2 flex h-3 items-end gap-px">
      {bars.map((height, index) => (
        <span key={index} className="w-1 rounded-full bg-[#565f68]" style={{ height: `${height}%` }} />
      ))}
    </div>
  );
}

function DocPreviewLines() {
  return (
    <div className="mt-2 space-y-1">
      <span className="block h-1 rounded-full bg-[#3b424a]" />
      <span className="block h-1 w-4/5 rounded-full bg-[#2c3238]" />
      <span className="block h-1 w-2/3 rounded-full bg-[#242a30]" />
    </div>
  );
}

function workflowStepCompleted(step: string, workspace: WorkspaceController): boolean {
  if (step === "Ingest") return workspace.uploadedVideo?.status === "ready";
  if (step === "Understand") return Boolean(workspace.agentRun);
  if (step === "Plan" || step === "Edit") {
    return Boolean(workspace.editingSession?.state.clips?.length);
  }
  if (step === "Render" || step === "Review" || step === "Export") {
    return workspace.renderResult?.status === "succeeded";
  }
  return false;
}

function workflowStepCurrent(step: string, workspace: WorkspaceController): boolean {
  if (workspace.status === "uploading") return step === "Ingest";
  if (workspace.status === "searching") return step === (workspace.agentRun ? "Edit" : "Understand");
  if (workspace.status === "rendering") return step === "Render";
  if (workspace.uploadedVideo && !workspace.agentRun) return step === "Understand";
  if (workspace.agentRun && !workspace.editingSession) return step === "Plan";
  if (workspace.editingSession && !workspace.renderResult) return step === "Render";
  return false;
}

function RouteStateCard({ workspace }: { workspace: WorkspaceController }) {
  return (
    <div className="rounded-[14px] border border-[#1b1d1f] bg-[#070808] p-4">
      <div className="flex items-start">
        {workflowSteps.map((step, index) => (
          <React.Fragment key={step}>
            {index > 0 && <span aria-hidden="true" className="mt-4 min-w-2 flex-1 border-t border-dashed border-[#3a4249]" />}
            <RouteNode label={step} complete={workflowStepCompleted(step, workspace)} active={workflowStepCurrent(step, workspace)} />
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function RouteNode({ label, active, complete }: { label: string; active?: boolean; complete?: boolean }) {
  return (
    <div className="relative z-10 flex w-9 shrink-0 flex-col items-center gap-1.5">
      <div
        className={`grid h-8 w-8 place-items-center rounded-full border ${
          active
            ? "border-[#6cc7ff]/70 bg-[#12202a] text-[#dff5ff] shadow-[0_0_18px_rgba(108,199,255,0.14)]"
            : complete
              ? "border-[#2c5c4b] bg-[#0d1f19] text-[#8df0c7]"
              : "border-[#2b3035] bg-[#0d0e0f] text-[#59616a]"
        }`}
      >
        {complete ? <Check className="h-4 w-4 stroke-[3]" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      </div>
      <span className={`text-[9px] ${active ? "text-[#dff5ff]" : "text-[#79828b]"}`}>{label}</span>
    </div>
  );
}

function TracePanel({ rows }: { rows: WorkspaceTraceRow[] }) {
  return (
    <div className="rounded-[12px] border border-[#1b1d1f] bg-[#070808] p-2 font-mono">
      {rows.map((row, index) => (
        <div
          key={`${row.name}-${index}`}
          className={`flex h-7 items-center gap-2 rounded-[8px] px-2 text-[11px] ${
            index === 0 || row.name === "export_video" ? "bg-[#111517] text-[#d8e1e7]" : "text-[#7d8791]"
          }`}
        >
          <span className="w-[58px] shrink-0 text-[#66707a]">{row.time}</span>
          <span className="min-w-0 flex-1 truncate">{row.name}</span>
          {row.elapsed && <span className="text-[10px] text-[#8b949e]">{row.elapsed}</span>}
          {row.status === "running" ? (
            <Clock3 className="h-3.5 w-3.5 animate-spin text-[#6cc7ff]" />
          ) : (
            <CheckCircle2 className="h-3.5 w-3.5 text-[#34d399]" />
          )}
        </div>
      ))}
    </div>
  );
}

function ArtifactsPanel({ workspace }: { workspace: WorkspaceController }) {
  const artifacts: Array<{
    title: string;
    meta: string;
    status: string;
    icon: React.ComponentType<{ className?: string }>;
    url?: string;
  }> = [];
  if (workspace.editingSession?.state.subtitles?.length) {
    artifacts.push({ title: "subtitles.srt", meta: `${workspace.editingSession.state.subtitles.length} cues`, status: "状态已生成", icon: FileText, url: workspace.renderResult?.result?.subtitle_url });
  }
  if (workspace.renderResult?.result?.output_url) {
    const renderedResolution = workspace.renderResult.result.width && workspace.renderResult.result.height
      ? `${workspace.renderResult.result.width}×${workspace.renderResult.result.height}`
      : String(workspace.editingSession?.state.settings?.aspect_ratio ?? "自动画幅");
    artifacts.push({
      title: workspace.renderResult.result.output_url.split("/").pop() ?? "camcat-render.mp4",
      meta: workspace.renderResult.result.duration_seconds
        ? `${workspace.renderResult.result.duration_seconds.toFixed(1)}s · ${renderedResolution}`
        : renderedResolution,
      status: "已真实渲染",
      icon: Download,
      url: workspace.renderResult.result.output_url,
    });
  }

  return (
    <div className="space-y-2">
      {!artifacts.length && <EmptyPanel text="等待真实产物" />}
      {artifacts.map(({ title, meta, status, icon: Icon, url }) => (
        <div
          key={title}
          className="flex items-center gap-3 rounded-[12px] border border-[#1f2224] bg-[#101112] p-2.5"
        >
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-[9px] border border-[#25282b] bg-[#080909] text-[#a4adb6]">
            <Icon className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[12px] font-medium text-[#e8edf1]">{title}</div>
            <div className="mt-1 flex items-center gap-2 text-[10px] text-[#7d8791]">
              <span>{meta}</span>
              <span className="h-1 w-1 rounded-full bg-[#3f4750]" />
              <span className="text-[#34d399]">{status}</span>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#6f7882]">
            <SmallIconButton icon={Download} label={`下载 ${title}`} onClick={() => url && window.open(url, "_blank")} disabled={!url} />
            <SmallIconButton icon={MoreHorizontal} label={`复制 ${title} 地址`} onClick={() => void copyText(url ?? title)} />
          </div>
        </div>
      ))}
    </div>
  );
}

function EditorWorkspace({ workspace }: { workspace: WorkspaceController }) {
  const [workspaceMode, setWorkspaceMode] = useState<"edit" | "review">("edit");
  const [fitMode, setFitMode] = useState<"contain" | "cover">("contain");
  const [planTab, setPlanTab] = useState("Editing Plan");
  const sessionClips = (workspace.editingSession?.state.clips ?? []).map((clip, index) => ({
    id: String(clip.clip_id ?? `clip-${index + 1}`),
    label: String(clip.reason ?? `素材片段 ${index + 1}`),
    start: Number(clip.output_start ?? 0),
    end: Number(clip.output_end ?? 0),
  }));
  const sessionSubtitles = (workspace.editingSession?.state.subtitles ?? []).map((subtitle, index) => ({
    id: String(subtitle.subtitle_id ?? `subtitle-${index + 1}`),
    label: String(subtitle.text ?? ""),
    start: Number(subtitle.start ?? 0),
    end: Number(subtitle.end ?? 0),
    tone: "green" as const,
  }));
  const visiblePlan = sessionClips;
  const visibleSubtitles = sessionSubtitles;
  const timelineDuration = Math.max(1, ...visiblePlan.map((clip) => clip.end));
  const aspectRatio = String(workspace.editingSession?.state.settings?.aspect_ratio ?? "Auto");
  return (
    <section id="editor-workspace" className="flex min-h-0 min-w-0 flex-col border-r border-[#1b1d1f] bg-[#050606]">
      <EditorToolbar mode={workspaceMode} onModeChange={setWorkspaceMode} fitMode={fitMode} onFitModeChange={setFitMode} aspectRatio={aspectRatio} />
      <div data-testid="editor-scroll-region" role="region" aria-label="可滚动视频编辑区域" tabIndex={0} className="flex min-h-0 flex-1 flex-col gap-3 overflow-x-hidden overflow-y-auto p-4 outline-none [scrollbar-color:#31363b_#080909] [scrollbar-width:thin] focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[#5aa8d0]">
        <div className="flex min-h-[360px] shrink-0 items-center justify-center">
          <VideoPreview workspace={workspace} fitMode={fitMode} reviewMode={workspaceMode === "review"} />
        </div>
        <PlayerControls duration={visiblePlan.length ? timelineDuration : 0} aspectRatio={aspectRatio} />
        <EditingPlan clips={visiblePlan} subtitles={visibleSubtitles} workspace={workspace} activeTab={planTab} onTabChange={setPlanTab} />
        <MultiTrackTimeline clips={visiblePlan} subtitles={visibleSubtitles} totalDuration={timelineDuration} />
      </div>
    </section>
  );
}

function EditorToolbar({
  mode,
  onModeChange,
  fitMode,
  onFitModeChange,
  aspectRatio,
}: {
  mode: "edit" | "review";
  onModeChange: (mode: "edit" | "review") => void;
  fitMode: "contain" | "cover";
  onFitModeChange: (mode: "contain" | "cover") => void;
  aspectRatio: string;
}) {
  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#1b1d1f] bg-[#070808] px-4">
      <div className="flex h-full items-center gap-5">
        <button type="button" onClick={() => onModeChange("edit")} aria-pressed={mode === "edit"} className={`relative h-full px-1 text-[12px] font-semibold ${mode === "edit" ? "text-[#f5f7f8] after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-[#f5f7f8]" : "text-[#6f7882]"}`}>
          Edit
        </button>
        <button type="button" onClick={() => onModeChange("review")} aria-pressed={mode === "review"} className={`relative h-full px-1 text-[12px] font-medium transition hover:text-[#cbd3da] ${mode === "review" ? "text-[#f5f7f8] after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-[#f5f7f8]" : "text-[#6f7882]"}`}>
          Review
        </button>
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-flex h-8 items-center rounded-[10px] border border-[#25282b] bg-[#0d0e0f] px-3 text-[11px] font-medium text-[#cbd3da]">{aspectRatio}</span>
        <button type="button" onClick={() => onFitModeChange(fitMode === "contain" ? "cover" : "contain")} className="inline-flex h-8 items-center gap-2 rounded-[10px] border border-[#25282b] bg-[#0d0e0f] px-3 text-[11px] font-medium text-[#cbd3da] transition hover:bg-[#141516]">
          {fitMode === "contain" ? "Fit" : "Fill"}
        </button>
        <button type="button" onClick={() => document.getElementById("editor-workspace")?.requestFullscreen()} aria-label="全屏编辑器" className="grid h-8 w-8 place-items-center rounded-[10px] border border-[#25282b] bg-[#0d0e0f] text-[#9ca3af] transition hover:bg-[#141516] hover:text-white">
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function VideoPreview({ workspace, fitMode, reviewMode }: { workspace: WorkspaceController; fitMode: "contain" | "cover"; reviewMode: boolean }) {
  const runView = workspace.agentRun ? mapAgenticRunToWorkspace(workspace.agentRun) : undefined;
  const videoUrl =
    workspace.renderResult?.result?.output_url ??
    workspace.evidence.find((item) => item.active)?.sourceVideoUrl ??
    runView?.selectedSegment?.source_video_url ??
    workspace.uploadedVideo?.playback_url;
  return (
    <div className="relative w-full max-w-[980px] overflow-hidden rounded-[12px] border border-[#24272a] bg-black shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
      <div className="aspect-video">
        <div className="relative h-full w-full overflow-hidden bg-[#0b0d0e]">
          {videoUrl ? (
            <video
              data-testid="camcat-video-preview"
              className={`absolute inset-0 z-20 h-full w-full bg-black ${fitMode === "contain" ? "object-contain" : "object-cover"}`}
              src={videoUrl}
              controls
              playsInline
            />
          ) : (
            <div className="absolute inset-0 grid place-items-center bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.08),transparent_34%),linear-gradient(145deg,#0b0d0e,#050606)]">
              <div className="flex flex-col items-center text-center">
                <span className="grid h-16 w-16 place-items-center rounded-[18px] border border-[#263039] bg-[#101417] text-[#dff5ff] shadow-[0_0_36px_rgba(56,189,248,0.08)]">
                  <PixelCatLogo className="h-9 w-9" />
                </span>
                <div className="mt-4 text-[15px] font-semibold text-[#dce2e7]">上传视频或输入多模态检索需求</div>
                <div className="mt-1.5 text-[11px] text-[#69717b]">真实片段或 FFmpeg 成片将在这里播放</div>
              </div>
            </div>
          )}
          {reviewMode && videoUrl && <div className="pointer-events-none absolute left-3 top-3 z-30 rounded-full border border-white/15 bg-black/70 px-3 py-1 text-[10px] text-white backdrop-blur">Review mode</div>}
        </div>
      </div>
    </div>
  );
}

function PlayerControls({ duration, aspectRatio }: { duration: number; aspectRatio: string }) {
  const control = (action: "start" | "back" | "toggle" | "forward" | "end") => {
    const video = document.querySelector<HTMLVideoElement>("[data-testid='camcat-video-preview']");
    if (!video) return;
    if (action === "start") video.currentTime = 0;
    if (action === "back") video.currentTime = Math.max(0, video.currentTime - 5);
    if (action === "toggle") void (video.paused ? video.play() : video.pause());
    if (action === "forward") video.currentTime = Math.min(video.duration || Infinity, video.currentTime + 5);
    if (action === "end" && Number.isFinite(video.duration)) video.currentTime = video.duration;
  };
  return (
    <div className="flex h-[52px] shrink-0 items-center justify-between rounded-[10px] border border-[#1f2224] bg-[#080909] px-4">
      <div className="flex items-center gap-3 text-[#77818b]">
        <PanelRight className="h-4 w-4" />
        <span className="font-mono text-[11px]">
          <span className="text-[#e8edf1]">00:00</span> / {formatTime(duration)}
        </span>
      </div>
      <div className="flex items-center gap-2 text-[#a3adb6]">
        <ControlButton icon={StepBack} label="跳到开头" onClick={() => control("start")} />
        <ControlButton icon={SkipBack} label="后退 5 秒" onClick={() => control("back")} />
        <button type="button" onClick={() => control("toggle")} aria-label="播放或暂停" className="grid h-9 w-9 place-items-center rounded-full bg-[#f5f7f8] text-[#050606] transition hover:bg-white">
          <Play className="ml-0.5 h-4 w-4 fill-current" />
        </button>
        <ControlButton icon={SkipForward} label="前进 5 秒" onClick={() => control("forward")} />
        <ControlButton icon={StepForward} label="跳到结尾" onClick={() => control("end")} />
      </div>
      <div className="flex items-center gap-3 text-[#77818b]">
        <span className="rounded-[8px] border border-[#25282b] bg-[#0e0f10] px-2 py-1 font-mono text-[10px] text-[#cbd3da]">
          {aspectRatio}
        </span>
        <Volume2 className="h-4 w-4" />
        <Settings className="h-4 w-4" />
      </div>
    </div>
  );
}

function EditingPlan({ clips, subtitles, workspace, activeTab, onTabChange }: { clips: TimelineClip[]; subtitles: TimelineClip[]; workspace: WorkspaceController; activeTab: string; onTabChange: (tab: string) => void }) {
  const [selectedClipId, setSelectedClipId] = useState<string>();
  const [draggedClipId, setDraggedClipId] = useState<string>();
  const displayedClips = activeTab === "Subtitles" ? subtitles : activeTab === "Audit Log" ? [] : clips;
  return (
    <div className="shrink-0 rounded-[12px] border border-[#1b1d1f] bg-[#080909]">
      <div className="flex h-10 items-center gap-6 border-b border-[#1b1d1f] px-4">
        {["Editing Plan", "Segments", "Subtitles", "Audit Log"].map((tab, index) => (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            aria-pressed={activeTab === tab}
            className={`relative h-full text-[12px] font-medium ${
              activeTab === tab
                ? "text-[#f5f7f8] after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-[#f5f7f8]"
                : "text-[#6f7882] hover:text-[#cbd3da]"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="flex gap-2 overflow-x-auto px-4 py-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {activeTab === "Audit Log" && workspace.auditEvents.map((event) => (
          <div key={event.audit_event_id} className="h-[58px] min-w-[220px] rounded-[12px] border border-[#25282b] bg-[#111213] p-3 text-left">
            <div className="truncate text-[12px] font-medium text-[#e8edf1]">{event.event_type}</div>
            <div className="mt-1.5 font-mono text-[10px] text-[#737b84]">
              {new Date(event.created_at).toLocaleString()} · v{String(event.metadata.result_version ?? event.metadata.version ?? "1")}
            </div>
          </div>
        ))}
        {!displayedClips.length && (activeTab !== "Audit Log" || !workspace.auditEvents.length) && (
          <div className="flex h-[58px] min-w-[260px] items-center justify-center rounded-[12px] border border-dashed border-[#25282b] bg-[#0b0c0d] text-[10px] text-[#69717b]">
            {activeTab === "Audit Log" ? `当前状态版本 v${workspace.editingSession?.state_version ?? 1}` : activeTab === "Subtitles" ? "当前计划尚未生成字幕" : "剪辑计划将在 Agent 写入真实 State Patch 后出现"}
          </div>
        )}
        {displayedClips.map((segment, index) => (
          <button
            key={segment.id}
            type="button"
            onClick={() => setSelectedClipId(segment.id)}
            draggable={activeTab !== "Subtitles"}
            onDragStart={() => setDraggedClipId(segment.id)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => {
              if (draggedClipId) void workspace.handleReorderClip(draggedClipId, segment.id);
              setDraggedClipId(undefined);
            }}
            aria-pressed={(selectedClipId ?? displayedClips[0]?.id) === segment.id}
            className={`h-[58px] min-w-[150px] rounded-[12px] border p-3 text-left transition ${
              (selectedClipId ?? displayedClips[0]?.id) === segment.id
                ? "border-[#38bdf8]/65 bg-[#0b1d27] shadow-[0_0_24px_rgba(56,189,248,0.14)]"
                : "border-[#25282b] bg-[#111213] hover:bg-[#141516]"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="rounded-[6px] border border-white/10 bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-[#9ca3af]">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="truncate text-[12px] font-medium text-[#e8edf1]">{segment.label}</span>
            </div>
            <div className="mt-1.5 font-mono text-[10px] text-[#737b84]">
              {formatTime(segment.start)}-{formatTime(segment.end)}
            </div>
          </button>
        ))}
        {activeTab !== "Subtitles" && activeTab !== "Audit Log" && selectedClipId && (
          <div className="flex h-[58px] shrink-0 items-center gap-2 rounded-[12px] border border-[#25282b] bg-[#0e0f10] px-2">
            <button type="button" onClick={() => void workspace.handleTrimClip(selectedClipId)} className="rounded-[8px] border border-[#303438] px-2 py-1 text-[10px] text-[#cbd3da]">裁短 0.5s</button>
            <button type="button" onClick={() => void workspace.handleSplitClip(selectedClipId)} className="rounded-[8px] border border-[#303438] px-2 py-1 text-[10px] text-[#cbd3da]">中点拆分</button>
          </div>
        )}
        <button type="button" onClick={() => { workspace.setQuery("请从素材库再召回一个匹配片段，并追加到当前剪辑计划"); document.getElementById("agent-query")?.focus(); }} aria-label="通过 Agent 追加片段" className="grid h-[58px] w-[58px] shrink-0 place-items-center rounded-[12px] border border-[#25282b] bg-[#0e0f10] text-[#8b949e] transition hover:bg-[#141516] hover:text-white">
          <Plus className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

function MultiTrackTimeline({
  clips,
  subtitles,
  totalDuration,
}: {
  clips: TimelineClip[];
  subtitles: TimelineClip[];
  totalDuration: number;
}) {
  const hasContent = clips.length > 0;
  const playheadPercent = 0;

  return (
    <div className="min-h-[256px] shrink-0 overflow-hidden rounded-[12px] border border-[#1b1d1f] bg-[#080909]">
      <div className="relative h-full px-4 py-3">
        <TimelineRuler totalDuration={totalDuration} />
        <div className="pointer-events-none absolute bottom-3 left-[92px] right-4 top-3 z-30">
          <div
            className="absolute bottom-0 top-0 w-px bg-[#f5f7f8] shadow-[0_0_14px_rgba(245,247,248,0.42)]"
            style={{ left: `${playheadPercent}%` }}
          >
            <span className="absolute -top-1.5 left-1/2 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-[#f5f7f8]" />
          </div>
        </div>

        <TimelineTrack label="Video" height="h-[42px]">
          <VideoTrack clips={clips} totalDuration={totalDuration} />
        </TimelineTrack>
        <TimelineTrack label="Overlay">
          <ClipLayer clips={clips} totalDuration={totalDuration} />
        </TimelineTrack>
        <TimelineTrack label="Subtitle">
          <ClipLayer clips={subtitles} subtitle totalDuration={totalDuration} />
        </TimelineTrack>
        <TimelineTrack label="Audio">
          <AudioTrack active={hasContent} />
        </TimelineTrack>
        <TimelineTrack label="Markers">
          <EmptyTrackLabel text="No markers" />
        </TimelineTrack>
      </div>
    </div>
  );
}

function TimelineRuler({ totalDuration }: { totalDuration: number }) {
  return (
    <div className="ml-[76px] grid h-5 grid-cols-6 border-b border-[#1b1d1f] font-mono text-[10px] text-[#68717b]">
      {Array.from({ length: 6 }, (_, index) => formatTime((totalDuration * index) / 5)).map((time) => (
        <div key={time} className="relative">
          <span>{time}</span>
          <span className="absolute bottom-0 left-0 h-2 w-px bg-[#30363b]" />
        </div>
      ))}
    </div>
  );
}

function TimelineTrack({
  label,
  children,
  height = "h-[34px]",
}: {
  label: string;
  children: React.ReactNode;
  height?: string;
}) {
  return (
    <div className="flex items-center gap-3 border-b border-[#151719] py-1.5 last:border-b-0">
      <div className="w-16 shrink-0 text-right text-[10px] font-medium text-[#737b84]">{label}</div>
      <div className={`relative flex-1 overflow-hidden rounded-[8px] border border-[#1f2224] bg-[#0c0d0e] ${height}`}>
        {children}
      </div>
    </div>
  );
}

function VideoTrack({ clips, totalDuration }: { clips: TimelineClip[]; totalDuration: number }) {
  return (
    <div className="relative h-full w-full">
      {!clips.length && <EmptyTrackLabel text="No source clips" />}
      {clips.map((clip, index) => (
        <div
          key={clip.id}
          className="absolute inset-y-0 flex items-center overflow-hidden border-r border-[#050606] bg-[linear-gradient(135deg,#1b242a,#0f1518)] px-2 text-[9px] text-[#9fb4c0]"
          style={{
            left: `${(clip.start / totalDuration) * 100}%`,
            width: `${((clip.end - clip.start) / totalDuration) * 100}%`,
          }}
        >
          <span className="truncate">source {index + 1}</span>
        </div>
      ))}
    </div>
  );
}

function ClipLayer({
  clips,
  subtitle,
  totalDuration,
}: {
  clips: TimelineClip[];
  subtitle?: boolean;
  totalDuration: number;
}) {
  return (
    <div className="relative h-full w-full">
      {clips.map((clip) => {
        const tone =
          clip.tone === "blue"
            ? "border-[#38bdf8]/35 bg-[#0c2733] text-[#c8efff]"
            : clip.tone === "green"
              ? "border-[#34d399]/25 bg-[#0e221d] text-[#c8f8e4]"
              : subtitle
                ? "border-[#6cc7ff]/20 bg-[#111a1d] text-[#b9cbd2]"
                : "border-[#2b3035] bg-[#141516] text-[#c5cdd4]";
        return (
          <div
            key={clip.id}
            className={`absolute top-1 flex h-[calc(100%-8px)] items-center rounded-[7px] border px-2 text-[10px] ${tone}`}
            style={{
              left: `${(clip.start / totalDuration) * 100}%`,
              width: `${((clip.end - clip.start) / totalDuration) * 100}%`,
            }}
          >
            <span className="truncate">{clip.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function AudioTrack({ active }: { active: boolean }) {
  if (!active) return <EmptyTrackLabel text="No source audio" />;
  return (
    <div className="relative flex h-full w-full items-center gap-px px-2">
      <span className="absolute left-2 top-1 font-mono text-[9px] text-[#6ee7b7]">Source audio</span>
      {waveform.map((height, index) => (
        <span
          key={index}
          className="flex-1 rounded-full bg-[#34d399]/55"
          style={{ height: `${height}%` }}
        />
      ))}
    </div>
  );
}

function EmptyTrackLabel({ text }: { text: string }) {
  return (
    <div className="flex h-full w-full items-center justify-center font-mono text-[9px] text-[#4f5861]">
      {text}
    </div>
  );
}

function AgentChatPanel({ workspace }: { workspace: WorkspaceController }) {
  const runView = workspace.agentRun ? mapAgenticRunToWorkspace(workspace.agentRun) : undefined;
  const assistantStatus =
    workspace.status === "uploading"
      ? "上传中"
      : workspace.status === "searching"
        ? "检索中"
        : workspace.status === "rendering"
          ? "渲染中"
          : workspace.status === "error"
            ? "需处理"
            : runView
              ? "已完成"
              : "待执行";
  const toolRows = runView?.trace.length ? runView.trace.slice(0, 5) : [];

  return (
    <aside className="flex min-h-0 flex-col bg-[#080909] max-[1180px]:hidden">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#1b1d1f] px-4">
        <div className="text-[10px] font-semibold tracking-[0.2em] text-[#858f99]">AGENT CHAT</div>
        <span aria-label="本地 CamCat 用户" className="grid h-8 w-8 place-items-center rounded-[10px] border border-[#25282b] bg-[#0d0e0f] text-[#8b949e]">
          <User className="h-4 w-4" />
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex flex-col items-end gap-1.5">
          <div className="text-[10px] text-[#6b7280]">YOU / NOW</div>
          <div className="max-w-[78%] rounded-[16px] rounded-tr-[6px] border border-[#25282b] bg-[#151719] px-3.5 py-2.5 text-[12px] leading-relaxed text-[#edf1f4]">
            {workspace.query || "帮我找素材并生成剪辑计划"}
          </div>
        </div>

        <div className="mt-5 space-y-2.5">
          <div className="flex items-center justify-between text-[10px] text-[#6b7280]">
            <span>ASSISTANT / CAMCAT</span>
            <span className={workspace.status === "error" ? "text-[#fca5a5]" : "text-[#34d399]"}>
              {assistantStatus}
            </span>
          </div>
          <BackendStatusCard workspace={workspace} />
          {workspace.progressLabel && (
            <div className="rounded-[12px] border border-[#1b4356] bg-[#0b1d27] px-3 py-2 text-[11px] text-[#c7efff]">
              <div className="flex items-center justify-between gap-3"><span>{workspace.progressLabel}</span><span className="font-mono">{workspace.progress === undefined ? "Agent" : `${Math.round(workspace.progress * 100)}%`}</span></div>
              {workspace.progress !== undefined && <div className="mt-2 h-1 overflow-hidden rounded-full bg-black/30"><div className="h-full rounded-full bg-[#6cc7ff] transition-all" style={{ width: `${workspace.progress * 100}%` }} /></div>}
            </div>
          )}
          <CreateTaskBoardCard runView={runView} workspace={workspace} />
          {toolRows.map((row) => (
            <ToolCallRow key={`${row.name}-${row.time}`} name={row.name} time={row.time} status={row.status} />
          ))}
          <FinalOutputCard workspace={workspace} />
        </div>
      </div>

      <div className="shrink-0 space-y-3 border-t border-[#1b1d1f] p-4">
        <AnalysisModeCard workspace={workspace} />
        <AgentInputBar workspace={workspace} />
      </div>
    </aside>
  );
}

function BackendStatusCard({ workspace }: { workspace: WorkspaceController }) {
  const statusText =
    workspace.uploadedVideo?.status ??
    (workspace.agentRun ? "agentic_run_ready" : "waiting_for_action");

  return (
    <div className="grid grid-cols-3 gap-2">
      <MiniStatusPill icon={Upload} label="Media DAG" value={statusText} active={Boolean(workspace.uploadedVideo)} />
      <MiniStatusPill icon={Search} label="Retrieval" value={workspace.agentRun ? "multimodal" : "idle"} active={Boolean(workspace.agentRun)} />
      <MiniStatusPill icon={Scissors} label="Render" value={workspace.renderResult?.status ?? "not started"} active={Boolean(workspace.renderResult)} />
    </div>
  );
}

function MiniStatusPill({
  icon: Icon,
  label,
  value,
  active,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  active?: boolean;
}) {
  return (
    <div className={`min-w-0 rounded-[12px] border p-2 ${active ? "border-[#1b4356] bg-[#0b1d27]" : "border-[#24272a] bg-[#0c0d0e]"}`}>
      <div className="flex items-center gap-1.5 text-[10px] font-medium text-[#9ca3af]">
        <Icon className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{label}</span>
      </div>
      <div className={`mt-1 truncate font-mono text-[10px] ${active ? "text-[#c7efff]" : "text-[#737b84]"}`}>
        {value}
      </div>
    </div>
  );
}

function CreateTaskBoardCard({
  runView,
  workspace,
}: {
  runView?: ReturnType<typeof mapAgenticRunToWorkspace>;
  workspace: WorkspaceController;
}) {
  const selected = runView?.selectedSegment;
  const payload = {
    summary: workspace.query,
    route: runView?.routeLabel ?? "retrieval_then_editing",
    selected_segment: selected?.segment_id ?? null,
    multimodal_embedding: "Qwen3-VL-Embedding-8B / 2048d MRL",
    milvus_retrieval: Boolean(runView?.evidence.length),
    ffmpeg_export_ready: workspace.canRender,
  };

  return (
    <div className="overflow-hidden rounded-[12px] border border-[#24272a] bg-[#0c0d0e]">
      <div className="flex h-9 items-center justify-between border-b border-[#202326] px-3">
        <div className="flex items-center gap-2 text-[12px] font-medium text-[#e1e7ec]">
          <Sparkles className="h-3.5 w-3.5 text-[#6cc7ff]" />
          create_task_board
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[#7d8791]">
          <span className={workspace.status === "error" ? "text-[#fca5a5]" : "text-[#34d399]"}>
            {workspace.status === "idle" ? "待执行" : workspace.status === "error" ? "失败" : "已同步"}
          </span>
          <span className="font-mono">now</span>
          <ChevronDown className="h-3.5 w-3.5" />
        </div>
      </div>
      <pre className="m-2 overflow-x-auto rounded-[10px] border border-[#17191b] bg-[#050606] p-3 font-mono text-[12px] leading-relaxed text-[#8f99a3]">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  );
}

function ToolCallRow({ name, time, status = "done" }: { name: string; time: string; status?: "done" | "running" }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} title={expanded ? `节点 ${name} 已完成，点击收起` : `展开节点 ${name}`} className={`${expanded ? "min-h-14" : "h-10"} flex w-full items-center justify-between rounded-[12px] border border-[#24272a] bg-[#0c0d0e] px-3 text-left transition hover:bg-[#111213]`}>
      <span className="flex min-w-0 items-center gap-2 text-[12px] text-[#c5cdd4]">
        {status === "running" ? (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-[#6cc7ff]" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#34d399]" />
        )}
        <span><span className="block truncate">{name}</span>{expanded && <span className="mt-0.5 block font-mono text-[9px] text-[#68717b]">LangGraph node execution recorded</span>}</span>
      </span>
      <span className="flex items-center gap-2 text-[10px] text-[#737b84]">
        <span className={status === "running" ? "text-[#6cc7ff]" : "text-[#34d399]"}>
          {status === "running" ? "运行中" : "已完成"}
        </span>
        <span className="font-mono">{time}</span>
        <ChevronDown className="h-3.5 w-3.5" />
      </span>
    </button>
  );
}

function FinalOutputCard({ workspace }: { workspace: WorkspaceController }) {
  const hasRender = Boolean(workspace.renderResult);
  const statusLabel = workspace.error ? "执行遇到问题" : hasRender ? "视频已成功导出，可下载！" : "等待检索结果与剪辑计划";
  const outputPath = workspace.renderResult?.result?.output_url ?? "等待生成真实输出";

  return (
    <div className="overflow-hidden rounded-[12px] border border-[#24272a] bg-[#0c0d0e]">
      <div className="flex h-9 items-center justify-between border-b border-[#202326] px-3">
        <span className="flex items-center gap-2 text-[12px] font-medium text-[#e1e7ec]">
          {workspace.error ? (
            <HelpCircle className="h-3.5 w-3.5 text-[#fca5a5]" />
          ) : hasRender ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-[#34d399]" />
          ) : (
            <Clock3 className="h-3.5 w-3.5 text-[#8b949e]" />
          )}
          最终输出
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-[#737b84]" />
      </div>
      <div className="space-y-3 p-3 text-[12px] leading-relaxed text-[#9ca3af]">
        <div className={`flex items-center gap-2 ${workspace.error ? "text-[#fca5a5]" : hasRender ? "text-[#34d399]" : "text-[#9ca3af]"}`}>
          {workspace.status === "rendering" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircle2 className="h-4 w-4" />
          )}
          {workspace.error ?? statusLabel}
        </div>
        <div className="space-y-1.5">
          <OutputLine label="文件名" value={hasRender ? outputPath.split("/").pop() ?? "rendered.mp4" : "等待生成"} />
          <OutputLine label="时长" value={workspace.renderResult?.result?.duration_seconds ? `${workspace.renderResult.result.duration_seconds.toFixed(1)}秒` : "由剪辑计划决定"} />
          <OutputLine label="分辨率" value={workspace.renderResult?.result?.width && workspace.renderResult?.result?.height ? `${workspace.renderResult.result.width}×${workspace.renderResult.result.height}` : String(workspace.editingSession?.state.settings?.aspect_ratio ?? "由输出画幅决定")} />
          <OutputLine label="状态" value={workspace.renderResult?.status ?? workspace.status} />
        </div>
        <div className="flex items-center gap-2 rounded-[10px] border border-[#202326] bg-[#050606] p-2">
          <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-[#737b84]">
            {outputPath}
          </span>
          <a
            href={workspace.renderResult?.result?.output_url}
            download
            aria-disabled={!workspace.renderResult?.result?.output_url}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-[9px] bg-[#f5f7f8] text-[#050606] transition hover:bg-white aria-disabled:pointer-events-none aria-disabled:opacity-40"
          >
            <Download className="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  );
}

function OutputLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="w-12 shrink-0 text-[#6f7882]">{label}:</span>
      <span className="min-w-0 flex-1 text-[#d9e0e5]">{value}</span>
    </div>
  );
}

function AnalysisModeCard({ workspace }: { workspace: WorkspaceController }) {
  return (
    <div className="rounded-[16px] border border-[#202326] bg-[#090a0b] p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold tracking-[0.18em] text-[#858f99]">ANALYSIS MODE</div>
          <p className="mt-1 text-[11px] leading-relaxed text-[#6f7882]">
            选择智能视频理解方式，逐秒分析会读取更多帧，耗时更长。
          </p>
        </div>
        <div className="flex shrink-0 rounded-[12px] border border-[#202326] bg-[#050606] p-1">
          <button type="button" onClick={() => workspace.setAnalysisMode("keyframes")} aria-pressed={workspace.analysisMode === "keyframes"} className={`rounded-[9px] px-3 py-1.5 text-[11px] font-medium ${workspace.analysisMode === "keyframes" ? "border border-[#1b4356] bg-[#0b1d27] text-[#c7efff]" : "text-[#737b84]"}`}>
            关键帧分析
          </button>
          <button type="button" onClick={() => workspace.setAnalysisMode("per-second")} aria-pressed={workspace.analysisMode === "per-second"} className={`rounded-[9px] px-3 py-1.5 text-[11px] font-medium transition hover:text-[#cbd3da] ${workspace.analysisMode === "per-second" ? "border border-[#1b4356] bg-[#0b1d27] text-[#c7efff]" : "text-[#737b84]"}`}>
            逐秒分析
          </button>
        </div>
      </div>
    </div>
  );
}

function AgentInputBar({ workspace }: { workspace: WorkspaceController }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const busy = workspace.status === "uploading" || workspace.status === "searching" || workspace.status === "rendering";
  const [listening, setListening] = useState(false);

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      return;
    }

    await workspace.handleUpload(files);
    event.target.value = "";
  }

  async function onImageChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    await workspace.handleQueryImage(file);
    event.target.value = "";
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    void workspace.handleSearch();
  }

  function startVoiceInput() {
    type BrowserRecognition = {
      lang: string;
      start: () => void;
      onresult: (event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void;
      onend: () => void;
      onerror: () => void;
    };
    const browserWindow = window as unknown as {
      SpeechRecognition?: new () => BrowserRecognition;
      webkitSpeechRecognition?: new () => BrowserRecognition;
    };
    const SpeechRecognition = browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      workspace.setQuery(`${workspace.query}${workspace.query ? " " : ""}[当前浏览器不支持语音输入]`);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "zh-CN";
    recognition.onresult = (event) => workspace.setQuery(event.results[0][0].transcript);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    setListening(true);
    recognition.start();
  }

  return (
    <form onSubmit={submit} className="rounded-[24px] border border-[#202326] bg-[#111213] p-3">
      <div className="mb-2 flex flex-wrap gap-1.5">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#25282b] bg-[#0a0b0c] px-2.5 py-1 text-[10px] font-medium text-[#9ca3af]">
          Auto {String(workspace.editingSession?.state.settings?.aspect_ratio ?? "ratio")}
        </span>
        <InputToolButton type="button" onClick={() => fileInputRef.current?.click()}>
          {workspace.status === "uploading" ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Upload className="h-3.5 w-3.5" />
          )}
          Upload
        </InputToolButton>
        <InputToolButton type="button" onClick={workspace.handleRender} disabled={!workspace.canRender || busy}>
          <Scissors className="h-3.5 w-3.5" /> Render
        </InputToolButton>
        <InputToolButton type="button" onClick={() => imageInputRef.current?.click()}>
          <ImageIcon className="h-3.5 w-3.5" /> {workspace.queryImageName ?? "Reference image"}
        </InputToolButton>
        <InputToolButton
          type="button"
          onClick={workspace.handleRollback}
          disabled={!workspace.editingSession || workspace.editingSession.state_version <= 1 || busy}
        >
          <Clock3 className="h-3.5 w-3.5" /> Rollback
        </InputToolButton>
      </div>
      <div className="relative">
        <button type="button" onClick={() => fileInputRef.current?.click()} aria-label="添加视频附件" className="absolute left-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-full text-[#737b84] transition hover:bg-white/[0.06] hover:text-white">
          <Plus className="h-4.5 w-4.5" />
        </button>
        <input
          id="agent-query"
          value={workspace.query}
          onChange={(event) => workspace.setQuery(event.target.value)}
          className="h-11 w-full rounded-full border border-[#25282b] bg-[#080909] pl-11 pr-[130px] text-[12px] text-[#edf1f4] outline-none placeholder:text-[#69717b] focus:border-[#37404a]"
          placeholder="有问题，尽管问"
        />
        <input id="video-upload" ref={fileInputRef} className="hidden" type="file" accept="video/*" multiple onChange={onFileChange} />
        <input ref={imageInputRef} className="hidden" type="file" accept="image/*" onChange={onImageChange} />
        <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-1">
          <button type="button" onClick={() => workspace.setSearchDepth(workspace.searchDepth === "instant" ? "deep" : "instant")} title="切换召回深度" className="inline-flex h-8 items-center gap-1 rounded-full px-2 text-[10px] text-[#858f99] transition hover:bg-white/[0.06] hover:text-white">
            {workspace.searchDepth === "instant" ? "Instant" : "Deep"} <ChevronDown className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={startVoiceInput} aria-label="语音输入" aria-pressed={listening} className={`grid h-8 w-8 place-items-center rounded-full transition hover:bg-white/[0.06] hover:text-white ${listening ? "bg-[#0b1d27] text-[#6cc7ff]" : "text-[#858f99]"}`}>
            {listening ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
          </button>
          <button
            type="submit"
            disabled={busy}
            className="grid h-8 w-8 place-items-center rounded-full bg-[#f5f7f8] text-[#050606] transition hover:bg-white disabled:cursor-not-allowed disabled:bg-[#2a2d31] disabled:text-[#7b838c]"
          >
            {workspace.status === "searching" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowUp className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    </form>
  );
}

function LiveBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[#1c3c31] bg-[#0d1f19] px-2 py-0.5 text-[10px] font-medium text-[#8df0c7]">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#34d399]" />
      Live
    </span>
  );
}

function RailIcon({ icon: Icon, label, onClick }: { icon: React.ComponentType<{ className?: string }>; label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label} className="grid h-9 w-9 place-items-center rounded-[10px] transition hover:bg-[#111213] hover:text-[#cbd3da]">
      <Icon className="h-4.5 w-4.5" />
    </button>
  );
}

function SmallIconButton({ icon: Icon, label, onClick, active = false, disabled = false }: { icon: React.ComponentType<{ className?: string }>; label: string; onClick: () => void; active?: boolean; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label} title={label} aria-pressed={active} className={`grid h-6 w-6 place-items-center rounded-[7px] transition hover:bg-white/[0.06] hover:text-[#dce2e7] disabled:cursor-not-allowed disabled:opacity-30 ${active ? "bg-[#0b1d27] text-[#6cc7ff]" : "text-[#737b84]"}`}>
      <Icon className="h-3.5 w-3.5" />
    </button>
  );
}

function ControlButton({ icon: Icon, label, onClick }: { icon: React.ComponentType<{ className?: string }>; label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label} className="grid h-8 w-8 place-items-center rounded-[10px] transition hover:bg-white/[0.06] hover:text-white">
      <Icon className="h-4 w-4" />
    </button>
  );
}

function InputToolButton({
  children,
  type = "button",
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  type?: "button" | "submit";
  onClick?: () => void | Promise<void>;
  disabled?: boolean;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 rounded-full border border-[#25282b] bg-[#0a0b0c] px-2.5 py-1 text-[10px] font-medium text-[#9ca3af] transition hover:border-[#34383c] hover:text-white disabled:cursor-not-allowed disabled:opacity-45"
    >
      {children}
    </button>
  );
}

function PixelCatLogo({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg
      className={`${className} shrink-0 text-white`}
      viewBox="0 0 20 18"
      aria-label="CamCat pixel cat logo"
      role="img"
      shapeRendering="crispEdges"
    >
      <title>CamCat pixel cat logo</title>
      <path
        data-logo-part="outline"
        fill="currentColor"
        fillRule="evenodd"
        d="M1 1h5v2h8V1h5v11h-2v3h-3v2H6v-2H3v-3H1V1Zm2 2v9h2v2h3v1h4v-1h3v-2h2V3h-3v2H6V3H3Z"
      />
      <rect x="6" y="8" width="2" height="2" fill="currentColor" />
      <rect x="12" y="8" width="2" height="2" fill="currentColor" />
      <path d="M9 11h2v1h2v1H7v-1h2v-1Z" fill="currentColor" />
    </svg>
  );
}

function formatTime(value: number) {
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function errorMessage(caught: unknown) {
  return userFacingErrorMessage(caught instanceof Error ? caught.message : "未知错误");
}
