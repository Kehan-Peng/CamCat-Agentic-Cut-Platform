import React from "react";
import {
  Activity,
  ArrowUp,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock3,
  Download,
  Eye,
  FileText,
  Filter,
  Folder,
  HelpCircle,
  Image as ImageIcon,
  Maximize2,
  Mic,
  MoreHorizontal,
  PanelRight,
  Play,
  Plus,
  Settings,
  Share2,
  SkipBack,
  SkipForward,
  StepBack,
  StepForward,
  Upload,
  User,
  Volume2,
} from "lucide-react";

type EvidenceKind = "video" | "doc" | "image";
type ToolStatus = "done" | "running";

type EvidenceItem = {
  id: string;
  title: string;
  meta: string;
  kind: EvidenceKind;
  active?: boolean;
  thumbnail?: string;
};

type TimelineClip = {
  id: string;
  label: string;
  start: number;
  end: number;
  tone?: "neutral" | "blue" | "green";
};

type Marker = {
  id: string;
  label: string;
  time: number;
};

const duration = 15;
const playheadTime = 6;

const evidenceItems: EvidenceItem[] = [
  {
    id: "ev1",
    title: "Seaways 产品视频.mp4",
    meta: "00:15 · 9:16 · 1080×1920",
    kind: "video",
    active: true,
    thumbnail:
      "https://images.unsplash.com/photo-1585421514284-efb74c2b69ba?q=80&w=360&auto=format&fit=crop",
  },
  {
    id: "ev2",
    title: "竞品清洁效果对比.mp4",
    meta: "00:12 · 9:16 · 1080×1920",
    kind: "video",
    thumbnail:
      "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?q=80&w=360&auto=format&fit=crop",
  },
  {
    id: "ev3",
    title: "产品卖点文案.md",
    meta: "2.4 KB · Markdown",
    kind: "doc",
  },
];

const workflowSteps = ["Ingest", "Understand", "Plan", "Edit", "Render", "Review", "Export"];

const traceRows = [
  { time: "10:56:47", name: "ingest_media", status: "done" as ToolStatus },
  { time: "10:56:51", name: "understand_content", status: "done" as ToolStatus },
  { time: "10:56:56", name: "create_task_board", status: "done" as ToolStatus },
  { time: "10:56:58", name: "write_subtitles", status: "done" as ToolStatus },
  { time: "10:57:02", name: "derive_clip_segments", status: "done" as ToolStatus },
  { time: "10:57:08", name: "render_clip_segment", status: "done" as ToolStatus },
  { time: "10:57:19", name: "export_video", status: "running" as ToolStatus, elapsed: "15s" },
];

const planSegments: TimelineClip[] = [
  { id: "p1", label: "产品亮相", start: 0, end: 3, tone: "blue" },
  { id: "p2", label: "去污对比", start: 3, end: 7 },
  { id: "p3", label: "清净细节", start: 7, end: 11 },
  { id: "p4", label: "使用场景", start: 11, end: 13 },
  { id: "p5", label: "CTA 结尾", start: 13, end: 15 },
];

const overlayClips: TimelineClip[] = [
  { id: "o1", label: "产品亮相", start: 0, end: 2.7 },
  { id: "o2", label: "深层去污 洁净如新", start: 2.7, end: 6.4, tone: "blue" },
  { id: "o3", label: "99.9% 除菌率", start: 6.4, end: 8.9 },
  { id: "o4", label: "强效去垢 呵护内筒", start: 8.9, end: 12.3, tone: "green" },
  { id: "o5", label: "Seaways 洗衣机清洁剂", start: 12.3, end: 15 },
];

const subtitleClips: TimelineClip[] = [
  { id: "s1", label: "你的洗衣机，真的干净吗？", start: 0.2, end: 3.2 },
  { id: "s2", label: "看不见的污垢正在影响健康", start: 3.2, end: 6.2, tone: "green" },
  { id: "s3", label: "Seaways 深层清洁", start: 6.2, end: 9.2 },
  { id: "s4", label: "去污除菌 呵护内筒", start: 9.2, end: 12.2, tone: "green" },
  { id: "s5", label: "洁净如新 安心之选", start: 12.2, end: 15 },
];

const markers: Marker[] = [
  { id: "m1", label: "对比开始", time: 2 },
  { id: "m2", label: "去污特写", time: 5.8 },
  { id: "m3", label: "效果展示", time: 9.8 },
  { id: "m4", label: "使用场景", time: 12.1 },
  { id: "m5", label: "CTA", time: 14.2 },
];

const waveform = [
  18, 32, 54, 41, 24, 46, 68, 76, 44, 30, 52, 72, 84, 60, 38, 24, 42, 58, 78,
  88, 70, 45, 28, 36, 62, 80, 90, 66, 48, 34, 22, 40, 64, 82, 74, 56, 32, 26,
  44, 72, 86, 68, 50, 30, 24, 38, 60, 78, 92, 74, 52, 34, 28, 46, 66, 80, 62,
  42, 25, 35, 58, 74, 86, 70, 44, 30, 22, 40, 62, 76, 58, 36, 26, 44, 64, 82,
  76, 54, 32, 24, 36, 56, 70, 60, 42, 28, 22, 34, 48,
];

const thumbnailSources = [
  "https://images.unsplash.com/photo-1585421514284-efb74c2b69ba?q=80&w=160&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?q=80&w=160&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1604335399105-a0c585fd81a1?q=80&w=160&auto=format&fit=crop",
];

export default function NovaWorkspacePage() {
  return <AppShell />;
}

function AppShell() {
  return (
    <div className="grid h-screen grid-cols-[96px_minmax(0,1fr)] overflow-hidden bg-[#030404] font-sans text-[12px] text-[#c9d0d6] antialiased max-[1500px]:grid-cols-[88px_minmax(0,1fr)] max-[1180px]:grid-cols-[84px_minmax(0,1fr)]">
        <LeftRail />
      <div className="flex min-h-0 min-w-0 flex-col">
        <TopHeader />
        <main className="grid h-[calc(100vh-72px)] min-h-0 grid-cols-[400px_minmax(600px,1fr)_540px] overflow-hidden bg-[#030404] max-[1500px]:grid-cols-[360px_minmax(560px,1fr)_500px] max-[1180px]:grid-cols-[340px_minmax(560px,1fr)]">
          <EvidencePanel />
          <EditorWorkspace />
          <AgentChatPanel />
        </main>
      </div>
    </div>
  );
}

function TopHeader() {
  return (
    <header className="grid h-[72px] grid-cols-[minmax(360px,1fr)_420px_minmax(360px,1fr)] items-center border-b border-[#1b1d1f] bg-[#050606] px-5 shadow-[0_1px_0_rgba(255,255,255,0.02)]">
      <div className="flex min-w-0 items-center gap-3">
        <button className="flex min-w-0 max-w-[390px] items-center gap-1.5 text-left text-[12px] text-[#d7dde2] transition hover:text-white">
          <span className="truncate">Seaways 洗衣机清洁剂推广视频</span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[#707983]" />
        </button>
        <span className="rounded-md border border-[#25282b] bg-[#111213] px-2 py-0.5 text-[10px] text-[#a9b0b8]">
          v3.2
        </span>
        <span className="text-[10px] text-[#6b7280]">Saved 10:57</span>
      </div>

      <div className="flex flex-col items-center gap-2">
        <div className="flex items-center gap-2 text-[11px] text-[#737b84]">
          <span>Workflow</span>
          <span className="font-medium text-[#edf1f4]">8/8 Completed</span>
        </div>
        <div className="flex items-center">
          {Array.from({ length: 8 }).map((_, index) => (
            <React.Fragment key={index}>
              <span className="grid h-4 w-4 place-items-center rounded-full border border-white/20 bg-[#f5f7f8] text-[#050606] shadow-[0_0_12px_rgba(245,247,248,0.16)]">
                <Check className="h-2.5 w-2.5 stroke-[3]" />
              </span>
              {index !== 7 && <span className="h-px w-9 bg-[#d8dee3]/70" />}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-end gap-2.5">
        <button className="inline-flex h-9 items-center gap-2 rounded-[10px] border border-[#25282b] bg-[#0c0d0e] px-3.5 text-[12px] font-medium text-[#dce2e7] transition hover:border-[#34383c] hover:bg-[#121314]">
          <Share2 className="h-3.5 w-3.5" />
          Share
        </button>
        <button className="inline-flex h-9 items-center gap-2 rounded-[10px] bg-[#f5f7f8] px-4 text-[12px] font-semibold text-[#060707] transition hover:bg-white">
          <Download className="h-3.5 w-3.5" />
          Export
          <ChevronDown className="h-3.5 w-3.5 opacity-60" />
        </button>
        <div className="ml-2 flex h-10 items-center gap-2 rounded-full border border-[#202326] bg-[#0b0c0d] px-1.5 pr-3">
          <img
            className="h-7 w-7 rounded-full object-cover ring-1 ring-white/10"
            src="https://i.pravatar.cc/80?img=47"
            alt="Nova Pro user avatar"
          />
          <span className="hidden text-[11px] font-medium text-[#dce2e7] xl:block">Nova Pro</span>
          <span className="h-1.5 w-1.5 rounded-full bg-[#34d399] shadow-[0_0_10px_rgba(52,211,153,0.45)]" />
        </div>
      </div>
    </header>
  );
}

function LeftRail() {
  const navItems = [
    { label: "Evidence", icon: Boxes, active: true },
    { label: "State", icon: CircleDot },
    { label: "Trace", icon: Activity },
    { label: "Artifacts", icon: Folder },
  ];

  return (
    <aside className="flex min-h-0 flex-col justify-between border-r border-[#1b1d1f] bg-[#050606] px-2.5 py-4">
      <div className="space-y-5">
        <div className="flex h-[52px] w-full items-center justify-center text-white">
          <PixelCatLogo className="h-[38px] w-[54px]" />
        </div>
        <nav className="space-y-2">
          {navItems.map(({ label, icon: Icon, active }) => (
            <button
              key={label}
              className={`flex h-[64px] w-full flex-col items-center justify-center gap-1.5 rounded-[10px] border transition ${
                active
                  ? "border-[#2a2d31] bg-[#121314] text-[#f5f7f8] shadow-[0_12px_30px_rgba(0,0,0,0.22)]"
                  : "border-transparent text-[#69717b] hover:bg-[#0d0e0f] hover:text-[#c3cbd2]"
              }`}
            >
              <Icon className="h-4.5 w-4.5" />
              <span className="text-[10px]">{label}</span>
            </button>
          ))}
        </nav>
      </div>
      <div className="flex flex-col items-center gap-2 text-[#6b7280]">
        <RailIcon icon={HelpCircle} />
        <RailIcon icon={Settings} />
      </div>
    </aside>
  );
}

function EvidencePanel() {
  return (
    <aside className="min-h-0 overflow-hidden border-r border-[#1b1d1f] bg-[#080909]">
      <div className="flex h-full flex-col overflow-y-auto px-4 py-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <PanelSectionHeader title="EVIDENCE" count={12} right={<EvidenceActions />} />
        <div className="space-y-3">
          {evidenceItems.map((item) => (
            <EvidenceCard key={item.id} item={item} />
          ))}
        </div>

        <PanelSectionHeader title="ROUTE / STATE" />
        <RouteStateCard />

        <PanelSectionHeader title="TRACE" right={<LiveBadge />} />
        <TracePanel />

        <PanelSectionHeader title="ARTIFACTS" count={7} />
        <ArtifactsPanel />
      </div>
    </aside>
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

function EvidenceActions() {
  return (
    <div className="flex items-center gap-1.5 text-[#737b84]">
      <SmallIconButton icon={Plus} />
      <SmallIconButton icon={Filter} />
    </div>
  );
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const Icon = item.kind === "doc" ? FileText : item.kind === "image" ? ImageIcon : Play;

  return (
    <button
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

function RouteStateCard() {
  return (
    <div className="rounded-[14px] border border-[#1b1d1f] bg-[#070808] p-4">
      <div className="relative grid grid-cols-4 gap-x-4 gap-y-5">
        <RouteConnector className="left-[13%] top-[18px] w-[24%]" />
        <RouteConnector className="left-[39%] top-[18px] w-[24%]" />
        <RouteConnector className="left-[65%] top-[18px] w-[22%]" />
        <RouteConnector className="left-[13%] bottom-[18px] w-[24%]" />
        <RouteConnector className="left-[39%] bottom-[18px] w-[24%]" />
        <RouteConnector vertical className="right-[12%] top-[18px] h-[55px]" />
        {workflowSteps.slice(0, 4).map((step) => (
          <RouteNode key={step} label={step} active={step === "Export"} />
        ))}
        <div />
        {workflowSteps.slice(4).map((step) => (
          <RouteNode key={step} label={step} active={step === "Export"} />
        ))}
      </div>
    </div>
  );
}

function RouteConnector({ className, vertical }: { className: string; vertical?: boolean }) {
  return (
    <span
      className={`pointer-events-none absolute border-[#2e3439] ${
        vertical ? "border-l border-dashed" : "border-t border-dashed"
      } ${className}`}
    />
  );
}

function RouteNode({ label, active }: { label: string; active?: boolean }) {
  return (
    <div className="relative z-10 flex flex-col items-center gap-1.5">
      <div
        className={`grid h-8 w-8 place-items-center rounded-full border ${
          active
            ? "border-[#6cc7ff]/70 bg-[#12202a] text-[#dff5ff] shadow-[0_0_18px_rgba(108,199,255,0.14)]"
            : "border-[#2b3035] bg-[#0d0e0f] text-[#b8c0c7]"
        }`}
      >
        <Check className="h-4 w-4 stroke-[3]" />
      </div>
      <span className={`text-[9px] ${active ? "text-[#dff5ff]" : "text-[#79828b]"}`}>{label}</span>
    </div>
  );
}

function TracePanel() {
  return (
    <div className="rounded-[12px] border border-[#1b1d1f] bg-[#070808] p-2 font-mono">
      {traceRows.map((row) => (
        <div
          key={row.name}
          className={`flex h-7 items-center gap-2 rounded-[8px] px-2 text-[11px] ${
            row.name === "export_video" ? "bg-[#111517] text-[#d8e1e7]" : "text-[#7d8791]"
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

function ArtifactsPanel() {
  const artifacts = [
    { title: "字幕文件.srt", meta: "24 KB", status: "已生成", icon: FileText },
    { title: "清洁效果对比_片段1.mp4", meta: "00:15 · 9:16", status: "已渲染", icon: Play },
    { title: "最终视频_导出.mp4", meta: "00:15 · 9:16", status: "已导出", icon: Download },
  ];

  return (
    <div className="space-y-2">
      {artifacts.map(({ title, meta, status, icon: Icon }) => (
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
            <SmallIconButton icon={Eye} />
            <SmallIconButton icon={Download} />
            <SmallIconButton icon={MoreHorizontal} />
          </div>
        </div>
      ))}
    </div>
  );
}

function EditorWorkspace() {
  return (
    <section className="flex min-h-0 min-w-0 flex-col border-r border-[#1b1d1f] bg-[#050606]">
      <EditorToolbar />
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden p-4">
        <div className="flex min-h-0 flex-1 items-center justify-center">
          <VideoPreview />
        </div>
        <PlayerControls />
        <EditingPlan />
        <MultiTrackTimeline />
      </div>
    </section>
  );
}

function EditorToolbar() {
  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#1b1d1f] bg-[#070808] px-4">
      <div className="flex h-full items-center gap-5">
        <button className="relative h-full px-1 text-[12px] font-semibold text-[#f5f7f8] after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-[#f5f7f8]">
          Edit
        </button>
        <button className="h-full px-1 text-[12px] font-medium text-[#6f7882] transition hover:text-[#cbd3da]">
          Review
        </button>
      </div>
      <div className="flex items-center gap-2">
        <ToolbarButton label="9:16" />
        <ToolbarButton label="Fit" />
        <button className="grid h-8 w-8 place-items-center rounded-[10px] border border-[#25282b] bg-[#0d0e0f] text-[#9ca3af] transition hover:bg-[#141516] hover:text-white">
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function ToolbarButton({ label }: { label: string }) {
  return (
    <button className="inline-flex h-8 items-center gap-2 rounded-[10px] border border-[#25282b] bg-[#0d0e0f] px-3 text-[11px] font-medium text-[#cbd3da] transition hover:bg-[#141516]">
      {label}
      <ChevronDown className="h-3.5 w-3.5 text-[#6f7882]" />
    </button>
  );
}

function VideoPreview() {
  return (
    <div className="relative w-full max-w-[980px] overflow-hidden rounded-[12px] border border-[#24272a] bg-black shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
      <div className="aspect-video">
        <div className="relative h-full w-full overflow-hidden bg-[#0b0d0e]">
          <img
            src="https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?q=85&w=1400&auto=format&fit=crop"
            alt="washing machine drum background"
            className="absolute inset-0 h-full w-full object-cover opacity-32 grayscale saturate-75"
          />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_23%_45%,rgba(255,255,255,0.22),transparent_18%),radial-gradient(circle_at_72%_46%,rgba(255,255,255,0.12),transparent_24%),linear-gradient(90deg,rgba(3,4,4,0.18),rgba(3,4,4,0.42)_48%,rgba(3,4,4,0.88))]" />
          <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black/70 to-transparent" />
          <div className="absolute left-[9%] top-[12%] h-[76%] w-[24%] max-w-[220px] rounded-[34px] border border-white/25 bg-gradient-to-b from-white via-[#f6f6f4] to-[#d5d9dc] shadow-[0_28px_80px_rgba(0,0,0,0.58)]">
            <div className="absolute left-1/2 top-3 h-7 w-[48%] -translate-x-1/2 rounded-full bg-[#d8dde1] shadow-inner" />
            <div className="absolute inset-x-[13%] top-[24%] rounded-[18px] border border-[#d4d8db] bg-white/80 px-3 py-5 text-center text-[#121416] shadow-inner">
              <div className="font-serif text-[clamp(18px,2vw,28px)] font-black italic tracking-tight">Seaways</div>
              <div className="mt-2 text-[clamp(7px,0.75vw,10px)] font-bold tracking-[0.25em] text-[#4b5560]">
                WASHING MACHINE
              </div>
              <div className="text-[clamp(10px,1vw,14px)] font-black tracking-[0.1em]">CLEANER</div>
              <div className="mx-auto mt-5 grid h-12 w-12 place-items-center rounded-full border-2 border-[#bfc7cc] bg-[#eef1f3] text-[10px] font-bold text-[#326789]">
                99.9%
              </div>
              <div className="mt-5 text-[9px] font-medium text-[#717982]">200ml</div>
            </div>
          </div>
          <div className="absolute right-[9%] top-1/2 max-w-[430px] -translate-y-1/2 text-white">
            <h1 className="text-[clamp(36px,4vw,52px)] font-bold leading-[1.08] tracking-normal drop-shadow-[0_12px_28px_rgba(0,0,0,0.65)]">
              深层去污
              <br />
              洁净如新
            </h1>
            <div className="mt-5 inline-flex items-center rounded-[8px] border border-white/15 bg-black/35 px-4 py-2 text-[14px] font-medium text-[#edf1f4] backdrop-blur-md">
              Seaways 洗衣机清洁剂
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-[13px] font-medium text-[#dce4ea]">
              <span>99.9% 除菌率</span>
              <span className="h-3.5 w-px bg-white/30" />
              <span>强效去垢</span>
              <span className="h-3.5 w-px bg-white/30" />
              <span>呵护内筒</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PlayerControls() {
  return (
    <div className="flex h-[52px] shrink-0 items-center justify-between rounded-[10px] border border-[#1f2224] bg-[#080909] px-4">
      <div className="flex items-center gap-3 text-[#77818b]">
        <PanelRight className="h-4 w-4" />
        <span className="font-mono text-[11px]">
          <span className="text-[#e8edf1]">00:06</span> / 00:15
        </span>
      </div>
      <div className="flex items-center gap-2 text-[#a3adb6]">
        <ControlButton icon={StepBack} />
        <ControlButton icon={SkipBack} />
        <button className="grid h-9 w-9 place-items-center rounded-full bg-[#f5f7f8] text-[#050606] transition hover:bg-white">
          <Play className="ml-0.5 h-4 w-4 fill-current" />
        </button>
        <ControlButton icon={SkipForward} />
        <ControlButton icon={StepForward} />
      </div>
      <div className="flex items-center gap-3 text-[#77818b]">
        <span className="rounded-[8px] border border-[#25282b] bg-[#0e0f10] px-2 py-1 font-mono text-[10px] text-[#cbd3da]">
          9:16
        </span>
        <Volume2 className="h-4 w-4" />
        <Settings className="h-4 w-4" />
      </div>
    </div>
  );
}

function EditingPlan() {
  return (
    <div className="shrink-0 rounded-[12px] border border-[#1b1d1f] bg-[#080909]">
      <div className="flex h-10 items-center gap-6 border-b border-[#1b1d1f] px-4">
        {["Editing Plan", "Segments", "Subtitles", "Audit Log"].map((tab, index) => (
          <button
            key={tab}
            className={`relative h-full text-[12px] font-medium ${
              index === 0
                ? "text-[#f5f7f8] after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-[#f5f7f8]"
                : "text-[#6f7882] hover:text-[#cbd3da]"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="flex gap-2 overflow-x-auto px-4 py-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {planSegments.map((segment, index) => (
          <button
            key={segment.id}
            className={`h-[58px] min-w-[150px] rounded-[12px] border p-3 text-left transition ${
              index === 0
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
        <button className="grid h-[58px] w-[58px] shrink-0 place-items-center rounded-[12px] border border-[#25282b] bg-[#0e0f10] text-[#8b949e] transition hover:bg-[#141516] hover:text-white">
          <Plus className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

function MultiTrackTimeline() {
  const playheadPercent = (playheadTime / duration) * 100;

  return (
    <div className="min-h-[256px] shrink-0 overflow-hidden rounded-[12px] border border-[#1b1d1f] bg-[#080909]">
      <div className="relative h-full px-4 py-3">
        <TimelineRuler />
        <div className="pointer-events-none absolute bottom-3 left-[92px] right-4 top-3 z-30">
          <div
            className="absolute bottom-0 top-0 w-px bg-[#f5f7f8] shadow-[0_0_14px_rgba(245,247,248,0.42)]"
            style={{ left: `${playheadPercent}%` }}
          >
            <span className="absolute -top-1.5 left-1/2 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-[#f5f7f8]" />
          </div>
        </div>

        <TimelineTrack label="Video" height="h-[42px]">
          <VideoTrack />
        </TimelineTrack>
        <TimelineTrack label="Overlay">
          <ClipLayer clips={overlayClips} />
        </TimelineTrack>
        <TimelineTrack label="Subtitle">
          <ClipLayer clips={subtitleClips} subtitle />
        </TimelineTrack>
        <TimelineTrack label="Audio">
          <AudioTrack />
        </TimelineTrack>
        <TimelineTrack label="Markers">
          <MarkerTrack />
        </TimelineTrack>
      </div>
    </div>
  );
}

function TimelineRuler() {
  return (
    <div className="ml-[76px] grid h-5 grid-cols-6 border-b border-[#1b1d1f] font-mono text-[10px] text-[#68717b]">
      {["00:00", "00:03", "00:06", "00:09", "00:12", "00:15"].map((time) => (
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

function VideoTrack() {
  return (
    <div className="flex h-full w-full">
      {Array.from({ length: 20 }).map((_, index) => (
        <div key={index} className="relative flex-1 overflow-hidden border-r border-black/45 last:border-r-0">
          <img
            src={thumbnailSources[index % thumbnailSources.length]}
            alt=""
            className="h-full w-full object-cover opacity-75 grayscale-[0.15] saturate-[0.75]"
          />
          <span className="absolute inset-0 bg-black/15" />
        </div>
      ))}
    </div>
  );
}

function ClipLayer({ clips, subtitle }: { clips: TimelineClip[]; subtitle?: boolean }) {
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
              left: `${(clip.start / duration) * 100}%`,
              width: `${((clip.end - clip.start) / duration) * 100}%`,
            }}
          >
            <span className="truncate">{clip.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function AudioTrack() {
  return (
    <div className="relative flex h-full w-full items-center gap-px px-2">
      <span className="absolute left-2 top-1 font-mono text-[9px] text-[#6ee7b7]">BGM.mp3</span>
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

function MarkerTrack() {
  return (
    <div className="relative h-full w-full">
      {markers.map((marker) => (
        <div
          key={marker.id}
          className="absolute top-1/2 flex -translate-y-1/2 items-center gap-1.5 text-[9px] text-[#8b949e]"
          style={{ left: `${(marker.time / duration) * 100}%` }}
        >
          <span className="h-2.5 w-2.5 rotate-45 rounded-[2px] border border-white/20 bg-[#e8edf1]" />
          <span className="hidden 2xl:inline">{marker.label}</span>
        </div>
      ))}
    </div>
  );
}

function AgentChatPanel() {
  return (
    <aside className="flex min-h-0 flex-col bg-[#080909] max-[1180px]:hidden">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#1b1d1f] px-4">
        <div className="text-[10px] font-semibold tracking-[0.2em] text-[#858f99]">AGENT CHAT</div>
        <button className="grid h-8 w-8 place-items-center rounded-[10px] border border-[#25282b] bg-[#0d0e0f] text-[#8b949e] transition hover:bg-[#141516] hover:text-white">
          <User className="h-4 w-4" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex flex-col items-end gap-1.5">
          <div className="text-[10px] text-[#6b7280]">YOU / 10:55</div>
          <div className="max-w-[78%] rounded-[16px] rounded-tr-[6px] border border-[#25282b] bg-[#151719] px-3.5 py-2.5 text-[12px] leading-relaxed text-[#edf1f4]">
            生成英文字幕并重新剪辑视频
          </div>
        </div>

        <div className="mt-5 space-y-2.5">
          <div className="flex items-center justify-between text-[10px] text-[#6b7280]">
            <span>ASSISTANT / 10:55</span>
            <span className="text-[#34d399]">已完成</span>
          </div>
          <CreateTaskBoardCard />
          <ToolCallRow name="write_subtitles" time="10:55:18" />
          <ToolCallRow name="思考过程" time="10:55:18" />
          <ToolCallRow name="derive_clip_segments" time="10:55:34" />
          <ToolCallRow name="render_clip_segment" time="10:56:01" />
          <FinalOutputCard />
        </div>
      </div>

      <div className="shrink-0 space-y-3 border-t border-[#1b1d1f] p-4">
        <AnalysisModeCard />
        <AgentInputBar />
      </div>
    </aside>
  );
}

function CreateTaskBoardCard() {
  return (
    <div className="overflow-hidden rounded-[12px] border border-[#24272a] bg-[#0c0d0e]">
      <div className="flex h-9 items-center justify-between border-b border-[#202326] px-3">
        <div className="flex items-center gap-2 text-[12px] font-medium text-[#e1e7ec]">
          <Activity className="h-3.5 w-3.5 text-[#6cc7ff]" />
          create_task_board
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[#7d8791]">
          <span className="text-[#34d399]">已完成</span>
          <span className="font-mono">10:55:08</span>
          <ChevronDown className="h-3.5 w-3.5" />
        </div>
      </div>
      <pre className="m-2 overflow-x-auto rounded-[10px] border border-[#17191b] bg-[#050606] p-3 font-mono text-[12px] leading-relaxed text-[#8f99a3]">
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

function ToolCallRow({ name, time }: { name: string; time: string }) {
  return (
    <button className="flex h-10 w-full items-center justify-between rounded-[12px] border border-[#24272a] bg-[#0c0d0e] px-3 text-left transition hover:bg-[#111213]">
      <span className="flex min-w-0 items-center gap-2 text-[12px] text-[#c5cdd4]">
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#34d399]" />
        <span className="truncate">{name}</span>
      </span>
      <span className="flex items-center gap-2 text-[10px] text-[#737b84]">
        <span className="text-[#34d399]">已完成</span>
        <span className="font-mono">{time}</span>
        <ChevronDown className="h-3.5 w-3.5" />
      </span>
    </button>
  );
}

function FinalOutputCard() {
  return (
    <div className="overflow-hidden rounded-[12px] border border-[#24272a] bg-[#0c0d0e]">
      <div className="flex h-9 items-center justify-between border-b border-[#202326] px-3">
        <span className="flex items-center gap-2 text-[12px] font-medium text-[#e1e7ec]">
          <CheckCircle2 className="h-3.5 w-3.5 text-[#34d399]" />
          最终输出
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-[#737b84]" />
      </div>
      <div className="space-y-3 p-3 text-[12px] leading-relaxed text-[#9ca3af]">
        <div className="flex items-center gap-2 text-[#34d399]">
          <CheckCircle2 className="h-4 w-4" />
          视频已成功导出，可下载！
        </div>
        <div className="space-y-1.5">
          <OutputLine label="文件名" value="seaways_cleaner_exported.mp4" />
          <OutputLine label="时长" value="15秒（9:16 竖屏，适配 TikTok）" />
          <OutputLine label="分辨率" value="1080×1920" />
          <OutputLine label="字幕" value="英文硬字幕" />
        </div>
        <div className="flex items-center gap-2 rounded-[10px] border border-[#202326] bg-[#050606] p-2">
          <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-[#737b84]">
            /api/download/exports/seaways_cleaner_exported.mp4
          </span>
          <button className="grid h-8 w-8 shrink-0 place-items-center rounded-[9px] bg-[#f5f7f8] text-[#050606] transition hover:bg-white">
            <Download className="h-4 w-4" />
          </button>
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

function AnalysisModeCard() {
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
          <button className="rounded-[9px] border border-[#1b4356] bg-[#0b1d27] px-3 py-1.5 text-[11px] font-medium text-[#c7efff]">
            关键帧分析
          </button>
          <button className="rounded-[9px] px-3 py-1.5 text-[11px] font-medium text-[#737b84] transition hover:text-[#cbd3da]">
            逐秒分析
          </button>
        </div>
      </div>
    </div>
  );
}

function AgentInputBar() {
  return (
    <div className="rounded-[24px] border border-[#202326] bg-[#111213] p-3">
      <div className="mb-2 flex flex-wrap gap-1.5">
        <InputToolButton>
          TikTok <ChevronDown className="h-3.5 w-3.5" />
        </InputToolButton>
        <InputToolButton>
          <Upload className="h-3.5 w-3.5" /> Upload
        </InputToolButton>
        <InputToolButton>
          <Activity className="h-3.5 w-3.5" /> Selling Points
        </InputToolButton>
      </div>
      <div className="relative">
        <button className="absolute left-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-full text-[#737b84] transition hover:bg-white/[0.06] hover:text-white">
          <Plus className="h-4.5 w-4.5" />
        </button>
        <input
          className="h-11 w-full rounded-full border border-[#25282b] bg-[#080909] pl-11 pr-[130px] text-[12px] text-[#edf1f4] outline-none placeholder:text-[#69717b] focus:border-[#37404a]"
          placeholder="有问题，尽管问"
        />
        <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-1">
          <button className="inline-flex h-8 items-center gap-1 rounded-full px-2 text-[10px] text-[#858f99] transition hover:bg-white/[0.06] hover:text-white">
            Instant <ChevronDown className="h-3.5 w-3.5" />
          </button>
          <button className="grid h-8 w-8 place-items-center rounded-full text-[#858f99] transition hover:bg-white/[0.06] hover:text-white">
            <Mic className="h-4 w-4" />
          </button>
          <button className="grid h-8 w-8 place-items-center rounded-full bg-[#f5f7f8] text-[#050606] transition hover:bg-white">
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
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

function RailIcon({ icon: Icon }: { icon: React.ComponentType<{ className?: string }> }) {
  return (
    <button className="grid h-9 w-9 place-items-center rounded-[10px] transition hover:bg-[#111213] hover:text-[#cbd3da]">
      <Icon className="h-4.5 w-4.5" />
    </button>
  );
}

function SmallIconButton({ icon: Icon }: { icon: React.ComponentType<{ className?: string }> }) {
  return (
    <button className="grid h-6 w-6 place-items-center rounded-[7px] text-[#737b84] transition hover:bg-white/[0.06] hover:text-[#dce2e7]">
      <Icon className="h-3.5 w-3.5" />
    </button>
  );
}

function ControlButton({ icon: Icon }: { icon: React.ComponentType<{ className?: string }> }) {
  return (
    <button className="grid h-8 w-8 place-items-center rounded-[10px] transition hover:bg-white/[0.06] hover:text-white">
      <Icon className="h-4 w-4" />
    </button>
  );
}

function InputToolButton({ children }: { children: React.ReactNode }) {
  return (
    <button className="inline-flex items-center gap-1.5 rounded-full border border-[#25282b] bg-[#0a0b0c] px-2.5 py-1 text-[10px] font-medium text-[#9ca3af] transition hover:border-[#34383c] hover:text-white">
      {children}
    </button>
  );
}

function PixelCatLogo({ className = "h-7 w-10" }: { className?: string }) {
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
      className={`${className} shrink-0 text-white`}
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

function formatTime(value: number) {
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
