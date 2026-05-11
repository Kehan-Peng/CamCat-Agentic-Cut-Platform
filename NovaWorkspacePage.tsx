import React, { useState } from "react";
import {
  Activity,
  ArrowUp,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock,
  Download,
  FileText,
  Filter,
  Folder,
  Image as ImageIcon,
  LayoutGrid,
  Maximize2,
  MessageSquare,
  Mic,
  MoreHorizontal,
  Play,
  Plus,
  Settings,
  Share2,
  Sparkles,
  SkipBack,
  SkipForward,
  Upload,
  User,
  Volume2,
} from "lucide-react";

type WorkflowStatus = "done" | "running" | "pending";
type TraceStatus = "done" | "running" | "queued";

type EvidenceItem = {
  id: string;
  title: string;
  meta: string;
  kind: "video" | "doc" | "image";
  thumbnail?: string;
  active?: boolean;
};

type TimelineClip = {
  id: string;
  label: string;
  start: number;
  end: number;
  tone?: "default" | "blue" | "green" | "amber";
};

const duration = 15;
const currentTime = 6;

const evidenceItems: EvidenceItem[] = [
  {
    id: "ev-1",
    title: "Seaways 产品视频.mp4",
    meta: "00:15 / 9:16 / 1080x1920",
    kind: "video",
    active: true,
    thumbnail:
      "https://images.unsplash.com/photo-1585421514284-efb74c2b69ba?q=80&w=240&auto=format&fit=crop",
  },
  {
    id: "ev-2",
    title: "竞品清洁效果对比.mp4",
    meta: "00:12 / 9:16 / 1080x1920",
    kind: "video",
    thumbnail:
      "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?q=80&w=240&auto=format&fit=crop",
  },
  {
    id: "ev-3",
    title: "产品卖点文案.md",
    meta: "2.4 KB / Markdown",
    kind: "doc",
  },
];

const workflowSteps = [
  { id: "ingest", label: "Ingest", status: "done" as WorkflowStatus },
  { id: "understand", label: "Understand", status: "done" as WorkflowStatus },
  { id: "plan", label: "Plan", status: "done" as WorkflowStatus },
  { id: "edit", label: "Edit", status: "done" as WorkflowStatus },
  { id: "render", label: "Render", status: "done" as WorkflowStatus },
  { id: "review", label: "Review", status: "done" as WorkflowStatus },
  { id: "export", label: "Export", status: "running" as WorkflowStatus },
];

const traceLogs = [
  { time: "10:56:47", name: "ingest_media", status: "done" as TraceStatus },
  { time: "10:56:51", name: "understand_content", status: "done" as TraceStatus },
  { time: "10:56:56", name: "create_task_board", status: "done" as TraceStatus },
  { time: "10:56:58", name: "write_subtitles", status: "done" as TraceStatus },
  { time: "10:57:02", name: "derive_clip_segments", status: "done" as TraceStatus },
  { time: "10:57:08", name: "render_clip_segment", status: "done" as TraceStatus },
  { time: "10:57:19", name: "export_video", status: "running" as TraceStatus },
];

const planBlocks: TimelineClip[] = [
  { id: "p1", label: "产品亮相", start: 0, end: 3, tone: "blue" },
  { id: "p2", label: "去污对比", start: 3, end: 7 },
  { id: "p3", label: "洁净细节", start: 7, end: 11 },
  { id: "p4", label: "使用场景", start: 11, end: 13 },
  { id: "p5", label: "CTA 结尾", start: 13, end: 15 },
];

const overlays: TimelineClip[] = [
  { id: "o1", label: "产品亮相", start: 0, end: 3, tone: "default" },
  { id: "o2", label: "深层去污 洁净如新", start: 3, end: 8, tone: "blue" },
  { id: "o3", label: "99.9% 除菌率", start: 8, end: 11, tone: "default" },
  { id: "o4", label: "Seaways 洗衣机清洁剂", start: 12, end: 15, tone: "default" },
];

const subtitles: TimelineClip[] = [
  { id: "s1", label: "你的洗衣机，真的干净吗？", start: 0.2, end: 3.7 },
  { id: "s2", label: "看不见的污垢正在威胁健康", start: 3.7, end: 7.8, tone: "green" },
  { id: "s3", label: "Seaways 深层清洁", start: 7.8, end: 11.2 },
  { id: "s4", label: "让内筒洁净如新", start: 11.2, end: 15, tone: "green" },
];

const markers = [
  { id: "m1", label: "对比开始", time: 2 },
  { id: "m2", label: "去污特写", time: 5.8 },
  { id: "m3", label: "效果展示", time: 9.8 },
  { id: "m4", label: "使用场景", time: 12.1 },
  { id: "m5", label: "CTA", time: 14.2 },
];

const waveform = [
  16, 24, 36, 52, 28, 18, 42, 62, 58, 44, 30, 22, 48, 66, 72, 50, 36, 26, 40,
  58, 76, 84, 70, 54, 38, 24, 34, 52, 68, 72, 56, 44, 30, 20, 36, 58, 74, 82,
  66, 50, 34, 26, 40, 60, 78, 86, 72, 54, 40, 28, 42, 64, 80, 88, 70, 52, 36,
  22, 34, 54, 74, 82, 64, 48, 32, 24, 38, 56, 76, 84, 68, 52, 34, 26, 44, 62,
  78, 72, 56, 40, 30, 24, 38, 52, 66, 74, 60, 46, 34, 24, 32, 48, 64, 58, 42,
  30, 22, 34, 46, 40,
];

export default function NovaWorkspacePage() {
  const [activePlan, setActivePlan] = useState("p1");
  const playheadProgress = currentTime / duration;

  return (
    <div className="h-screen w-full overflow-hidden bg-[#050506] text-[12px] text-zinc-300 antialiased">
      <div className="flex h-full flex-col">
        <TopBar />
        <main className="grid min-h-0 flex-1 grid-cols-[52px_minmax(210px,250px)_minmax(380px,1fr)_minmax(280px,320px)] overflow-hidden max-[900px]:grid-cols-[minmax(220px,260px)_minmax(360px,1fr)]">
          <Rail />
          <LeftInspector />
          <EditorCanvas
            activePlan={activePlan}
            setActivePlan={setActivePlan}
            playheadProgress={playheadProgress}
          />
          <AgentChat />
        </main>
      </div>
    </div>
  );
}

function TopBar() {
  return (
    <header className="grid h-12 shrink-0 grid-cols-[1fr_auto_1fr] items-center border-b border-white/[0.07] bg-[#070708] px-3 shadow-[0_1px_0_rgba(255,255,255,0.03)]">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex items-center gap-2.5 text-white">
          <PixelCatLogo />
          <span className="text-[18px] font-semibold leading-none tracking-tight">Nova</span>
        </div>
        <div className="h-4 w-px bg-white/10" />
        <button className="flex min-w-0 max-w-[330px] items-center gap-1.5 truncate text-[12px] text-zinc-300 hover:text-white">
          <span className="truncate">Seaways 洗衣机清洁剂推广视频</span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
        </button>
        <span className="rounded-md border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-zinc-400">
          v3.2
        </span>
        <span className="text-[10px] text-zinc-600">Saved 10:57</span>
      </div>

      <div className="flex flex-col items-center gap-1">
        <div className="flex items-center gap-1 text-[10px] text-zinc-500">
          <span>Workflow</span>
          <span className="font-medium text-zinc-200">8/8 Completed</span>
        </div>
        <div className="flex items-center">
          {Array.from({ length: 8 }).map((_, index) => (
            <React.Fragment key={index}>
              <span className="h-1.5 w-1.5 rounded-full bg-white shadow-[0_0_10px_rgba(255,255,255,0.35)]" />
              {index !== 7 && <span className="h-px w-7 bg-white/70" />}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-end gap-2">
        <button className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 text-[12px] text-zinc-200 hover:bg-white/[0.07]">
          <Share2 className="h-3.5 w-3.5" />
          Share
        </button>
        <button className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-white px-3.5 font-medium text-zinc-950 hover:bg-zinc-200">
          <Download className="h-3.5 w-3.5" />
          Export
          <ChevronDown className="h-3.5 w-3.5 opacity-60" />
        </button>
        <div className="ml-1 flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-1.5 py-1">
          <img
            className="h-6 w-6 rounded-full object-cover"
            src="https://i.pravatar.cc/64?img=47"
            alt="Nova Pro user avatar"
          />
          <span className="hidden text-[11px] text-zinc-300 xl:block">Nova Pro</span>
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        </div>
      </div>
    </header>
  );
}

function PixelCatLogo() {
  const pixels = [
    [1, 0],
    [2, 0],
    [15, 0],
    [16, 0],
    [1, 1],
    [2, 1],
    [3, 1],
    [14, 1],
    [15, 1],
    [16, 1],
    [1, 2],
    [4, 2],
    [13, 2],
    [16, 2],
    [1, 3],
    [5, 3],
    [6, 3],
    [7, 3],
    [8, 3],
    [9, 3],
    [10, 3],
    [11, 3],
    [12, 3],
    [16, 3],
    [1, 4],
    [3, 4],
    [13, 4],
    [15, 4],
    [1, 5],
    [16, 5],
    [1, 6],
    [5, 6],
    [6, 6],
    [11, 6],
    [12, 6],
    [16, 6],
    [1, 7],
    [16, 7],
    [1, 8],
    [8, 8],
    [9, 8],
    [16, 8],
    [2, 9],
    [7, 9],
    [8, 9],
    [9, 9],
    [10, 9],
    [15, 9],
    [3, 10],
    [4, 10],
    [5, 10],
    [6, 10],
    [7, 10],
    [8, 10],
    [9, 10],
    [10, 10],
    [11, 10],
    [12, 10],
    [13, 10],
    [14, 10],
  ];

  return (
    <svg
      className="h-7 w-10 shrink-0 text-white"
      viewBox="0 0 36 24"
      aria-label="Nova pixel cat logo"
      role="img"
      shapeRendering="crispEdges"
    >
      <title>Nova pixel cat logo</title>
      {pixels.map(([x, y]) => (
        <rect key={`${x}-${y}`} x={x * 2} y={y * 2} width="2" height="2" fill="currentColor" />
      ))}
    </svg>
  );
}

function Rail() {
  const items = [
    { icon: LayoutGrid, label: "Evidence", active: true },
    { icon: CircleDot, label: "State" },
    { icon: Activity, label: "Trace" },
    { icon: Folder, label: "Artifacts" },
  ];

  return (
    <aside className="flex min-h-0 flex-col items-center justify-between border-r border-white/[0.07] bg-[#070708] py-3 max-[900px]:hidden">
      <div className="flex flex-col items-center gap-3">
        {items.map(({ icon: Icon, label, active }) => (
          <button
            key={label}
            className={`group flex w-11 flex-col items-center gap-1 rounded-xl px-1.5 py-2 transition ${
              active
                ? "bg-white/[0.06] text-white ring-1 ring-white/10"
                : "text-zinc-600 hover:bg-white/[0.03] hover:text-zinc-300"
            }`}
          >
            <Icon className="h-4 w-4" />
            <span className="text-[9px] leading-none">{label}</span>
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-3 text-zinc-600">
        <IconButton icon={MessageSquare} />
        <IconButton icon={Settings} />
      </div>
    </aside>
  );
}

function LeftInspector() {
  return (
    <aside className="min-h-0 overflow-hidden border-r border-white/[0.07] bg-[#080809]">
      <div className="flex h-full flex-col overflow-y-auto overscroll-contain px-2 py-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <SectionHeader title="EVIDENCE" count={12} right={<EvidenceActions />} />
        <div className="space-y-1.5 pb-3">
          {evidenceItems.map((item) => (
            <EvidenceCard key={item.id} item={item} />
          ))}
        </div>

        <SectionHeader title="ROUTE / STATE" />
        <WorkflowMap />

        <SectionHeader
          title="TRACE"
          right={
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[9px] text-emerald-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              Live
            </span>
          }
        />
        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-2 font-mono">
          {traceLogs.map((log) => (
            <TraceRow key={`${log.time}-${log.name}`} {...log} />
          ))}
        </div>

        <SectionHeader title="ARTIFACTS" count={7} />
        <div className="space-y-1.5 pb-4">
          <ArtifactCard title="字幕文件.srt" meta="24 KB / 已生成" />
          <ArtifactCard title="清洁效果对比_片段1.mp4" meta="00:15 / 9:16 / 已渲染" />
          <ArtifactCard title="最终视频_导出.mp4" meta="00:15 / 9:16 / 导出中" active />
        </div>
      </div>
    </aside>
  );
}

function EvidenceActions() {
  return (
    <div className="flex items-center gap-1 text-zinc-500">
      <IconButton icon={Plus} small />
      <IconButton icon={Filter} small />
    </div>
  );
}

function SectionHeader({
  title,
  count,
  right,
}: {
  title: string;
  count?: number;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-1.5 mt-2.5 flex items-center justify-between px-1">
      <div className="flex items-center gap-2">
        <h2 className="text-[10px] font-semibold tracking-[0.18em] text-zinc-500">
          {title}
        </h2>
        {count !== undefined && (
          <span className="rounded-md bg-white/[0.06] px-1.5 py-px text-[9px] text-zinc-500">
            {count}
          </span>
        )}
      </div>
      {right}
    </div>
  );
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const Icon = item.kind === "doc" ? FileText : item.kind === "image" ? ImageIcon : Play;

  return (
    <button
      className={`group flex w-full items-center gap-2 rounded-xl border p-1.5 text-left transition ${
        item.active
          ? "border-white/15 bg-white/[0.06] shadow-[0_12px_40px_rgba(0,0,0,0.25)]"
          : "border-white/[0.04] bg-white/[0.025] hover:border-white/10 hover:bg-white/[0.045]"
      }`}
    >
      <div className="relative h-12 w-16 shrink-0 overflow-hidden rounded-lg border border-white/10 bg-zinc-900">
        {item.thumbnail ? (
          <img
            src={item.thumbnail}
            alt=""
            className="h-full w-full object-cover opacity-90 saturate-[0.9] transition group-hover:scale-105"
          />
        ) : (
          <div className="grid h-full w-full place-items-center bg-gradient-to-br from-zinc-800 to-zinc-950">
            <Icon className="h-5 w-5 text-zinc-400" />
          </div>
        )}
        {item.kind === "video" && (
          <span className="absolute bottom-1 right-1 grid h-4 w-4 place-items-center rounded-full bg-black/70 text-white backdrop-blur">
            <Play className="ml-0.5 h-2.5 w-2.5 fill-current" />
          </span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[11px] font-medium text-zinc-200">{item.title}</div>
        <div className="mt-0.5 truncate text-[9px] text-zinc-500">{item.meta}</div>
      </div>
    </button>
  );
}

function WorkflowMap() {
  return (
    <div className="mb-2 rounded-xl border border-white/[0.06] bg-black/20 px-3 py-4">
      <div className="relative mx-auto grid max-w-[230px] grid-cols-4 grid-rows-2 gap-x-4 gap-y-4">
        <Connector className="left-[15%] top-[22px] w-[28%]" />
        <Connector className="left-[57%] top-[22px] w-[28%]" />
        <Connector className="left-[15%] bottom-[22px] w-[28%]" />
        <Connector className="left-[57%] bottom-[22px] w-[28%]" />
        <Connector vertical className="left-[49.5%] top-[25px] h-[48px]" />
        {workflowSteps.slice(0, 4).map((step) => (
          <WorkflowNode key={step.id} {...step} />
        ))}
        <div />
        {workflowSteps.slice(4).map((step) => (
          <WorkflowNode key={step.id} {...step} />
        ))}
      </div>
    </div>
  );
}

function Connector({ className, vertical }: { className: string; vertical?: boolean }) {
  return (
    <span
      className={`pointer-events-none absolute rounded-full bg-[linear-gradient(90deg,rgba(255,255,255,0.12),rgba(255,255,255,0.55),rgba(255,255,255,0.12))] ${
        vertical ? "w-px" : "h-px"
      } ${className}`}
    />
  );
}

function WorkflowNode({ label, status }: { label: string; status: WorkflowStatus }) {
  const running = status === "running";
  return (
    <div className="relative z-10 flex flex-col items-center gap-1">
      <div
        className={`grid h-6 w-6 place-items-center rounded-full border bg-[#080809] ${
          running
            ? "border-white text-white shadow-[0_0_18px_rgba(255,255,255,0.28)]"
            : "border-white/20 text-zinc-400"
        }`}
      >
        {running ? (
          <Activity className="h-3.5 w-3.5 animate-pulse" />
        ) : (
          <Check className="h-3.5 w-3.5" />
        )}
      </div>
      <span className={`text-[9px] ${running ? "text-white" : "text-zinc-500"}`}>{label}</span>
    </div>
  );
}

function TraceRow({ time, name, status }: { time: string; name: string; status: TraceStatus }) {
  return (
    <div className="flex h-5 items-center justify-between gap-2 text-[9px] text-zinc-500">
      <div className="flex min-w-0 items-center gap-2">
        <span className="text-zinc-600">{time}</span>
        <span className="truncate text-zinc-400">{name}</span>
      </div>
      {status === "running" ? (
        <Clock className="h-3 w-3 animate-spin text-zinc-400" />
      ) : (
        <CheckCircle2 className="h-3 w-3 text-emerald-500/70" />
      )}
    </div>
  );
}

function ArtifactCard({ title, meta, active }: { title: string; meta: string; active?: boolean }) {
  return (
    <button
      className={`flex w-full items-center gap-2 rounded-xl border p-2 text-left transition ${
        active
          ? "border-white/[0.12] bg-white/[0.055]"
          : "border-white/[0.04] bg-white/[0.025] hover:bg-white/[0.045]"
      }`}
    >
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/10 bg-black/30 text-zinc-400">
        <FileText className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[11px] text-zinc-200">{title}</div>
        <div className="mt-0.5 truncate text-[9px] text-zinc-500">{meta}</div>
      </div>
      {active ? (
        <Activity className="h-3.5 w-3.5 animate-pulse text-zinc-400" />
      ) : (
        <MoreHorizontal className="h-3.5 w-3.5 text-zinc-600" />
      )}
    </button>
  );
}

function EditorCanvas({
  activePlan,
  setActivePlan,
  playheadProgress,
}: {
  activePlan: string;
  setActivePlan: (id: string) => void;
  playheadProgress: number;
}) {
  return (
    <section className="flex min-h-0 min-w-0 flex-col bg-[#0b0b0d]">
      <div className="flex h-10 shrink-0 items-center justify-between border-b border-white/[0.07] px-3">
        <div className="flex h-full items-center gap-4">
          <button className="relative h-full px-1 text-[12px] font-medium text-white after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-white">
            Edit
          </button>
          <button className="h-full px-1 text-[12px] text-zinc-500 hover:text-zinc-300">Review</button>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-zinc-400">
          <ToolbarSelect label="9:16" />
          <ToolbarSelect label="Fit" />
          <button className="grid h-7 w-7 place-items-center rounded-md border border-white/10 bg-white/[0.03] hover:bg-white/[0.07]">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 items-center justify-center p-3">
        <VideoStage />
      </div>

      <PlaybackBar />

      <div className="h-[235px] shrink-0 border-t border-white/[0.07] bg-[#070708]">
        <div className="flex h-9 items-center gap-5 border-b border-white/[0.07] px-3 text-[11px]">
          <button className="relative h-full font-medium text-white after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:bg-white">
            Editing Plan
          </button>
          <button className="text-zinc-500 hover:text-zinc-300">Segments</button>
          <button className="text-zinc-500 hover:text-zinc-300">Subtitles</button>
          <button className="text-zinc-500 hover:text-zinc-300">Audit Log</button>
        </div>

        <div className="flex gap-2 overflow-x-auto border-b border-white/[0.07] px-3 py-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {planBlocks.map((block, index) => (
            <button
              key={block.id}
              onClick={() => setActivePlan(block.id)}
              className={`h-12 min-w-[120px] rounded-xl border p-2 text-left transition ${
                activePlan === block.id
                  ? "border-sky-400/55 bg-sky-400/[0.10] shadow-[0_0_24px_rgba(56,189,248,0.08)]"
                  : "border-white/[0.07] bg-white/[0.035] hover:bg-white/[0.055]"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span className="rounded bg-white/[0.07] px-1 text-[9px] text-zinc-400">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="truncate text-[11px] font-medium text-zinc-200">{block.label}</span>
              </div>
              <div className="mt-1 font-mono text-[9px] text-zinc-500">
                {formatTime(block.start)} - {formatTime(block.end)}
              </div>
            </button>
          ))}
          <button className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.025] text-zinc-500 hover:bg-white/[0.05] hover:text-zinc-300">
            <Plus className="h-4 w-4" />
          </button>
        </div>

        <div className="relative h-[144px] overflow-hidden px-3 py-2">
          <TimelineRuler />
          <div className="pointer-events-none absolute bottom-0 left-[72px] right-3 top-2 z-30">
            <div
              className="absolute bottom-0 top-0 w-px bg-white shadow-[0_0_14px_rgba(255,255,255,0.55)]"
              style={{ left: `${playheadProgress * 100}%` }}
            >
              <span className="absolute -top-1.5 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 bg-white" />
            </div>
          </div>
          <TimelineTrack name="Video" large>
            <VideoStrip />
          </TimelineTrack>
          <TimelineTrack name="Overlay">
            <ClipLayer clips={overlays} />
          </TimelineTrack>
          <TimelineTrack name="Subtitle">
            <ClipLayer clips={subtitles} />
          </TimelineTrack>
          <TimelineTrack name="Audio">
            <Waveform />
          </TimelineTrack>
          <TimelineTrack name="Markers">
            <MarkerLayer />
          </TimelineTrack>
        </div>
      </div>
    </section>
  );
}

function ToolbarSelect({ label }: { label: string }) {
  return (
    <button className="inline-flex h-7 items-center gap-1 rounded-md border border-white/10 bg-white/[0.03] px-2 hover:bg-white/[0.07]">
      {label}
      <ChevronDown className="h-3 w-3 text-zinc-600" />
    </button>
  );
}

function VideoStage() {
  return (
    <div className="relative w-full max-w-[620px] overflow-hidden rounded-xl border border-white/[0.09] bg-black shadow-[0_28px_100px_rgba(0,0,0,0.65)]">
      <div className="aspect-video overflow-hidden">
        <div className="relative h-full w-full bg-[#101010]">
          <img
            src="https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?q=85&w=1200&auto=format&fit=crop"
            alt="washing machine background"
            className="absolute inset-0 h-full w-full object-cover opacity-55 blur-[0.2px] saturate-75"
          />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_28%_50%,rgba(255,255,255,0.18),transparent_24%),linear-gradient(90deg,rgba(0,0,0,0.18),rgba(0,0,0,0.35)_52%,rgba(0,0,0,0.72))]" />
          <div className="absolute left-[7%] top-[17%] h-[62%] w-[25%] rounded-[28px] border border-white/20 bg-white/90 shadow-[0_30px_70px_rgba(0,0,0,0.45)]">
            <div className="absolute left-1/2 top-2 h-5 w-12 -translate-x-1/2 rounded-full bg-zinc-200" />
            <div className="flex h-full flex-col items-center justify-center px-3 text-center text-zinc-950">
              <div className="font-serif text-[20px] font-bold italic tracking-tight">Seaways</div>
              <div className="mt-1 text-[8px] font-semibold tracking-widest text-zinc-700">WASHING MACHINE</div>
              <div className="text-[10px] font-bold tracking-wide">CLEANER</div>
              <div className="mt-5 text-[9px] font-bold text-sky-700">99.9%</div>
              <div className="mt-1 h-9 w-9 rounded-full border-2 border-zinc-300 bg-zinc-100" />
              <div className="mt-4 text-[7px] text-zinc-500">200ml</div>
            </div>
          </div>
          <div className="absolute right-[10%] top-[26%] max-w-[360px] text-white">
            <div className="text-[34px] font-semibold leading-tight tracking-[0.08em] drop-shadow-xl xl:text-[40px]">
              深层去污
              <br />
              洁净如新
            </div>
            <div className="mt-4 inline-flex items-center rounded-md border border-white/10 bg-black/35 px-4 py-2 backdrop-blur-md">
              <span className="text-[13px] text-zinc-200">Seaways 洗衣机清洁剂</span>
            </div>
            <div className="mt-3 flex items-center gap-2 text-[12px] text-zinc-200">
              <span>99.9% 除菌率</span>
              <span className="h-3 w-px bg-white/30" />
              <span>强效去垢</span>
              <span className="h-3 w-px bg-white/30" />
              <span>呵护内筒</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PlaybackBar() {
  return (
    <div className="flex h-10 shrink-0 items-center justify-between border-y border-white/[0.07] bg-[#070708] px-3">
      <div className="font-mono text-[10px] text-zinc-500">
        <span className="text-zinc-300">00:06</span> / 00:15
      </div>
      <div className="flex items-center gap-3 text-zinc-400">
        <button className="hover:text-white">
          <SkipBack className="h-4 w-4" />
        </button>
        <button className="grid h-8 w-8 place-items-center rounded-full bg-white text-black shadow-[0_0_18px_rgba(255,255,255,0.18)] hover:bg-zinc-200">
          <Play className="ml-0.5 h-4 w-4 fill-current" />
        </button>
        <button className="hover:text-white">
          <SkipForward className="h-4 w-4" />
        </button>
      </div>
      <div className="flex items-center gap-3 text-zinc-500">
        <span className="rounded-md border border-white/10 bg-white/[0.03] px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
          9:16
        </span>
        <Volume2 className="h-4 w-4" />
        <Settings className="h-4 w-4" />
      </div>
    </div>
  );
}

function TimelineRuler() {
  return (
    <div className="ml-[72px] grid h-4 grid-cols-6 border-b border-white/[0.04] font-mono text-[8px] text-zinc-600">
      {["00:00", "00:03", "00:06", "00:09", "00:12", "00:15"].map((time) => (
        <div key={time} className="relative">
          <span>{time}</span>
          <span className="absolute bottom-0 left-0 h-1.5 w-px bg-white/10" />
        </div>
      ))}
    </div>
  );
}

function TimelineTrack({
  name,
  children,
  large,
}: {
  name: string;
  children: React.ReactNode;
  large?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      <div className="w-16 shrink-0 text-right text-[9px] text-zinc-500">{name}</div>
      <div
        className={`relative flex-1 overflow-hidden rounded-md border border-white/[0.055] bg-white/[0.025] ${
          large ? "h-8" : "h-6"
        }`}
      >
        {children}
      </div>
    </div>
  );
}

function VideoStrip() {
  return (
    <div className="flex h-full w-full">
      {Array.from({ length: 18 }).map((_, index) => (
        <div key={index} className="relative flex-1 overflow-hidden border-r border-black/40 last:border-r-0">
          <img
            src={
              index % 3 === 0
                ? "https://images.unsplash.com/photo-1585421514284-efb74c2b69ba?q=80&w=140&auto=format&fit=crop"
                : index % 3 === 1
                  ? "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?q=80&w=140&auto=format&fit=crop"
                  : "https://images.unsplash.com/photo-1604335399105-a0c585fd81a1?q=80&w=140&auto=format&fit=crop"
            }
            alt=""
            className="h-full w-full object-cover opacity-75 saturate-75"
          />
          <span className="absolute inset-0 bg-black/10" />
        </div>
      ))}
    </div>
  );
}

function ClipLayer({ clips }: { clips: TimelineClip[] }) {
  return (
    <div className="relative h-full w-full">
      {clips.map((clip) => {
        const left = `${(clip.start / duration) * 100}%`;
        const width = `${((clip.end - clip.start) / duration) * 100}%`;
        const tone =
          clip.tone === "blue"
            ? "border-sky-400/30 bg-sky-400/15 text-sky-100"
            : clip.tone === "green"
              ? "border-emerald-400/25 bg-emerald-400/15 text-emerald-100"
              : clip.tone === "amber"
                ? "border-amber-300/25 bg-amber-300/15 text-amber-100"
                : "border-white/10 bg-white/[0.07] text-zinc-300";
        return (
          <div
            key={clip.id}
            className={`absolute top-0.5 flex h-[calc(100%-4px)] items-center truncate rounded border px-2 text-[9px] ${tone}`}
            style={{ left, width }}
          >
            <span className="truncate">{clip.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function Waveform() {
  return (
    <div className="flex h-full w-full items-center gap-px px-1">
      {waveform.map((height, index) => (
        <span
          key={index}
          className="flex-1 rounded-full bg-emerald-400/55"
          style={{ height: `${Math.max(12, height)}%` }}
        />
      ))}
    </div>
  );
}

function MarkerLayer() {
  return (
    <div className="relative h-full w-full">
      {markers.map((marker) => (
        <div
          key={marker.id}
          className="absolute top-1/2 flex -translate-y-1/2 items-center gap-1 text-[8px] text-zinc-500"
          style={{ left: `${(marker.time / duration) * 100}%` }}
        >
          <span className="h-2 w-2 rotate-45 rounded-[1px] bg-white/60" />
          <span className="hidden xl:inline">{marker.label}</span>
        </div>
      ))}
    </div>
  );
}

function AgentChat() {
  return (
    <aside className="flex min-h-0 flex-col border-l border-white/[0.07] bg-[#080809] max-[900px]:hidden">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/[0.07] px-3">
        <div className="text-[10px] font-semibold tracking-[0.18em] text-zinc-400">AGENT CHAT</div>
        <button className="grid h-7 w-7 place-items-center rounded-lg border border-white/10 bg-white/[0.03] text-zinc-500 hover:bg-white/[0.07] hover:text-zinc-300">
          <User className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex flex-col items-end gap-1">
          <div className="text-[9px] text-zinc-600">YOU / 10:55</div>
          <div className="max-w-[82%] rounded-2xl rounded-tr-md border border-white/10 bg-white/[0.08] px-3 py-2 text-[12px] leading-relaxed text-zinc-100">
            生成英文字幕并重新剪辑视频
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-[9px] text-zinc-600">
            <span>ASSISTANT / 10:55</span>
            <span className="text-zinc-500">已完成</span>
          </div>

          <ToolCard />
          <AgentStep name="write_subtitles" time="10:55:18" />
          <AgentStep name="思考过程" time="10:55:18" />
          <AgentStep name="derive_clip_segments" time="10:55:34" />
          <AgentStep name="render_clip_segment" time="10:56:01" />
          <FinalOutput />
        </div>
      </div>

      <ChatComposer />
    </aside>
  );
}

function ToolCard() {
  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.07] bg-black/35 shadow-[0_14px_40px_rgba(0,0,0,0.25)]">
      <div className="flex h-8 items-center justify-between border-b border-white/[0.07] bg-white/[0.035] px-3">
        <div className="flex items-center gap-2 text-[11px] text-zinc-300">
          <Sparkles className="h-3.5 w-3.5 text-zinc-400" />
          create_task_board
        </div>
        <span className="font-mono text-[9px] text-zinc-600">10:55:08</span>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-[10px] leading-relaxed text-zinc-500">
        {`{
  "summary": "生成英文字幕并重新剪辑导出视频",
  "selected_ids": [1],
  "subtitle_rewrite": true,
  "clip_mapping": true,
  "video_export": true,
  "export_intent": true
}`}
      </pre>
    </div>
  );
}

function AgentStep({ name, time }: { name: string; time: string }) {
  return (
    <button className="flex h-8 w-full items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.025] px-3 text-left hover:bg-white/[0.045]">
      <span className="flex min-w-0 items-center gap-2 text-[11px] text-zinc-400">
        <Sparkles className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{name}</span>
      </span>
      <span className="flex items-center gap-2 text-[9px] text-zinc-600">
        <span className="font-mono">{time}</span>
        <span>已完成</span>
        <ChevronDown className="h-3 w-3" />
      </span>
    </button>
  );
}

function FinalOutput() {
  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.025]">
      <div className="flex h-8 items-center justify-between border-b border-white/[0.07] bg-white/[0.035] px-3">
        <span className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-200">
          <Sparkles className="h-3.5 w-3.5" />
          最终输出
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-zinc-600" />
      </div>
      <div className="space-y-2 p-3 text-[11px] leading-relaxed text-zinc-500">
        <div className="flex items-center gap-1.5 text-emerald-400">
          <CheckCircle2 className="h-3.5 w-3.5" />
          视频已成功导出，可以下载。
        </div>
        <ul className="space-y-1 pl-1">
          <li>
            文件名: <span className="text-zinc-300">seaways_cleaner_exported.mp4</span>
          </li>
          <li>
            时长: <span className="text-zinc-300">15 秒，9:16 竖屏，适配 TikTok</span>
          </li>
          <li>
            分辨率: <span className="text-zinc-300">1080x1920</span>
          </li>
          <li>
            字幕: <span className="text-zinc-300">英文硬字幕</span>
          </li>
        </ul>
        <div className="flex items-center gap-2 rounded-lg border border-white/[0.07] bg-black/30 p-2">
          <span className="min-w-0 flex-1 truncate font-mono text-[9px] text-zinc-600">
            /api/download/exports/seaways_cleaner_exported.mp4
          </span>
          <button className="grid h-7 w-7 place-items-center rounded-md bg-white/[0.08] text-zinc-200 hover:bg-white/[0.12]">
            <Download className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ChatComposer() {
  return (
    <div className="shrink-0 border-t border-white/[0.07] p-3">
      <div className="mb-3 rounded-xl border border-white/[0.07] bg-white/[0.025] p-2">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="text-[10px] font-semibold tracking-[0.14em] text-zinc-500">ANALYSIS MODE</div>
            <div className="mt-0.5 text-[9px] text-zinc-600">
              选择剪辑视角，逐步分析或快速生成
            </div>
          </div>
          <div className="flex rounded-lg border border-white/[0.06] bg-black/35 p-0.5">
            <button className="rounded-md bg-white/[0.09] px-2 py-1 text-[9px] text-zinc-100">
              关键帧分析
            </button>
            <button className="rounded-md px-2 py-1 text-[9px] text-zinc-500 hover:text-zinc-300">
              逐镜分析
            </button>
          </div>
        </div>
      </div>

      <div className="mb-2 flex flex-wrap gap-1.5">
        <Pill>
          TikTok <ChevronDown className="h-3 w-3" />
        </Pill>
        <Pill>
          <Upload className="h-3 w-3" /> Upload
        </Pill>
        <Pill>
          <Sparkles className="h-3 w-3" /> Selling Points
        </Pill>
      </div>

      <div className="relative">
        <button className="absolute left-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-full text-zinc-500 hover:bg-white/[0.06] hover:text-zinc-300">
          <Plus className="h-4 w-4" />
        </button>
        <input
          className="h-10 w-full rounded-full border border-white/10 bg-white/[0.035] pl-10 pr-[116px] text-[12px] text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-white/20 focus:bg-white/[0.05]"
          placeholder="有问题，尽管问"
        />
        <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-1">
          <button className="inline-flex h-7 items-center gap-1 rounded-full px-2 text-[10px] text-zinc-500 hover:bg-white/[0.06] hover:text-zinc-300">
            Instant <ChevronDown className="h-3 w-3" />
          </button>
          <button className="grid h-7 w-7 place-items-center rounded-full text-zinc-500 hover:bg-white/[0.06] hover:text-zinc-300">
            <Mic className="h-3.5 w-3.5" />
          </button>
          <button className="grid h-7 w-7 place-items-center rounded-full bg-white text-black hover:bg-zinc-200">
            <ArrowUp className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <button className="inline-flex items-center gap-1 rounded-full border border-white/[0.07] bg-white/[0.035] px-2 py-1 text-[10px] text-zinc-400 hover:bg-white/[0.06] hover:text-zinc-200">
      {children}
    </button>
  );
}

function IconButton({
  icon: Icon,
  small,
}: {
  icon: React.ComponentType<{ className?: string }>;
  small?: boolean;
}) {
  return (
    <button
      className={`grid place-items-center rounded-lg hover:bg-white/[0.04] hover:text-zinc-300 ${
        small ? "h-5 w-5" : "h-8 w-8"
      }`}
    >
      <Icon className={small ? "h-3.5 w-3.5" : "h-4 w-4"} />
    </button>
  );
}

function formatTime(value: number) {
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
