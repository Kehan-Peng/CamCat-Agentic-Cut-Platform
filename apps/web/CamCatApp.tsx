import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BriefcaseBusiness,
  ChevronDown,
  ChevronRight,
  Download,
  Loader2,
  Plus,
  RefreshCw,
  Scissors,
  Trash2,
  X,
} from "lucide-react";
import CamCatWorkspacePage, { type ProductPage } from "./CamCatWorkspacePage";
import {
  createCamCatApiClient,
  type EditingSessionResponse,
  type ProjectResponse,
} from "./src/camcatApi";

type ProjectWithSessions = ProjectResponse & { sessions: EditingSessionResponse[] };
type OpenWorkspace = { project: ProjectResponse; session?: EditingSessionResponse; page?: ProductPage };

export default function CamCatApp() {
  const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {};
  const apiBase = env.VITE_CAMCAT_API_BASE || "";
  const userId = env.VITE_CAMCAT_USER_ID ?? "camcat-local-user";
  const api = useMemo(() => createCamCatApiClient({ baseUrl: apiBase, userId }), [apiBase, userId]);
  const [projects, setProjects] = useState<ProjectWithSessions[]>([]);
  const [openWorkspace, setOpenWorkspace] = useState<OpenWorkspace>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [showCreate, setShowCreate] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const page = await api.listProjects();
      const hydrated = await Promise.all(
        page.items.map(async (project) => ({
          ...project,
          sessions: (await api.listEditingSessions(project.project_id)).items,
        })),
      );
      setProjects(hydrated);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载项目失败");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function createProject(name: string) {
    const project = await api.createProject(name);
    setShowCreate(false);
    setOpenWorkspace({ project });
  }

  async function removeSession(projectId: string, sessionId: string) {
    await api.deleteEditingSession(sessionId);
    setProjects((current) =>
      current.map((project) =>
        project.project_id === projectId
          ? { ...project, sessions: project.sessions.filter((session) => session.editing_session_id !== sessionId) }
          : project,
      ),
    );
  }

  function openProductPage(page: ProductPage) {
    const project = projects.find((candidate) => candidate.sessions.some((session) => (session.state.source_media?.length ?? 0) > 0)) ?? projects[0];
    if (!project) return;
    const session = [...project.sessions].sort((a, b) => Date.parse(b.updated_at ?? "") - Date.parse(a.updated_at ?? ""))[0];
    setOpenWorkspace({ project, session, page });
  }

  if (openWorkspace) {
    return (
      <CamCatWorkspacePage
        key={`${openWorkspace.project.project_id}:${openWorkspace.session?.editing_session_id ?? "new"}`}
        project={openWorkspace.project}
        initialSession={openWorkspace.session}
        initialPage={openWorkspace.page}
        onBack={() => {
          setOpenWorkspace(undefined);
          void reload();
        }}
      />
    );
  }

  return (
    <ProjectHomePage
      projects={projects}
      loading={loading}
      error={error}
      onRefresh={() => void reload()}
      onCreate={() => setShowCreate(true)}
      onOpen={(project, session) => setOpenWorkspace({ project, session })}
      onNavigateProduct={openProductPage}
      onDeleteSession={(projectId, sessionId) => void removeSession(projectId, sessionId)}
    >
      {showCreate && (
        <CreateProjectDialog
          onClose={() => setShowCreate(false)}
          onCreate={createProject}
        />
      )}
    </ProjectHomePage>
  );
}

function ProjectHomePage({
  projects,
  loading,
  error,
  onRefresh,
  onCreate,
  onOpen,
  onNavigateProduct,
  onDeleteSession,
  children,
}: {
  projects: ProjectWithSessions[];
  loading: boolean;
  error?: string;
  onRefresh: () => void;
  onCreate: () => void;
  onOpen: (project: ProjectResponse, session?: EditingSessionResponse) => void;
  onNavigateProduct: (page: ProductPage) => void;
  onDeleteSession: (projectId: string, sessionId: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen overflow-hidden bg-[#030404] text-[#cbd2d8]">
      <div className="flex h-full w-full max-w-[1540px] flex-col bg-[radial-gradient(circle_at_55%_-15%,#131920_0%,#060708_38%,#030404_100%)]">
        <header data-testid="app-header" className="grid h-[72px] shrink-0 grid-cols-[minmax(360px,1fr)_420px_minmax(360px,1fr)] items-center border-b border-[#1b1d1f] bg-[#050606] px-5">
          <div className="flex min-w-0 items-center gap-3 text-white">
            <CamCatMark className="h-8 w-8" />
            <span className="text-[26px] font-black leading-none">CamCat</span>
            <span className="h-5 w-px bg-[#25282b]" />
            <span className="text-[12px] text-[#d7dde2]">项目列表</span>
          </div>
          <div className="text-center"><div className="text-[11px] text-[#737b84]">Workspace</div><div className="mt-1 text-[12px] font-medium text-white">项目 / 项目列表</div></div>
          <div className="flex items-center justify-end gap-3">
            <button type="button" onClick={onRefresh} aria-label="刷新项目" className="grid h-9 w-9 place-items-center rounded-[10px] border border-[#2d3237] bg-[#111315] text-[#aab2ba] hover:bg-[#181a1d] hover:text-white"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /></button>
            <button type="button" onClick={onCreate} className="inline-flex h-9 items-center gap-2 rounded-[10px] border border-[#34393e] bg-[linear-gradient(180deg,#202327,#151719)] px-4 text-[12px] font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] hover:border-[#4a5158]"><Plus className="h-4 w-4" />新建项目</button>
          </div>
        </header>
        <div data-testid="project-layout" className="grid min-h-0 flex-1" style={{ gridTemplateColumns: "96px minmax(0, 1fr)" }}>
          <ProjectRail onNavigate={onNavigateProduct} disabled={!projects.length} />
          <main data-testid="project-content" className="min-h-0 overflow-y-auto border-r border-[#1b1d1f] bg-[#08090a]/95 px-10 py-8 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <div className="flex items-end justify-between">
              <div><div className="text-[11px] font-semibold tracking-[0.24em] text-[#68727c]">PROJECTS</div><h1 className="mt-2 text-[28px] font-semibold text-white">项目首页 / 工作区列表</h1></div>
              <div className="font-mono text-[11px] text-[#68727c]">{projects.length} projects · {projects.reduce((sum, project) => sum + project.sessions.length, 0)} sessions</div>
            </div>

            {error && <div role="alert" className="mt-6 rounded-[14px] border border-[#7f1d1d] bg-[#2a1010] px-5 py-4 text-[13px] text-[#fca5a5]">{error}</div>}
            {loading && !projects.length && <div className="mt-12 grid flex-1 place-items-center"><div className="flex items-center gap-3 text-[#858f99]"><Loader2 className="h-5 w-5 animate-spin" />正在从 CamCat API 加载项目</div></div>}
            {!loading && !error && !projects.length && (
              <div className="mt-10 grid min-h-[340px] place-items-center rounded-[20px] border border-dashed border-[#30353a] bg-[#0b0c0d] text-center">
                <div><BriefcaseBusiness className="mx-auto h-11 w-11 text-[#59636d]" /><h2 className="mt-5 text-xl font-semibold text-white">还没有项目</h2><p className="mt-2 text-[13px] text-[#747e87]">创建第一个项目，然后上传原片开始剪辑。</p><button type="button" onClick={onCreate} className="mt-6 rounded-[12px] bg-white px-5 py-3 text-[13px] font-semibold text-black">新建项目</button></div>
              </div>
            )}
            <div className="mt-7 space-y-4">
              {projects.map((project, index) => <ProjectCard key={project.project_id} project={project} index={index} onOpen={onOpen} onDeleteSession={onDeleteSession} />)}
            </div>
          </main>
        </div>
      </div>
      {children}
    </div>
  );
}

function ProjectCard({ project, index, onOpen, onDeleteSession }: { project: ProjectWithSessions; index: number; onOpen: (project: ProjectResponse, session?: EditingSessionResponse) => void; onDeleteSession: (projectId: string, sessionId: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const latest = [...project.sessions].sort((a, b) => Date.parse(b.updated_at ?? "") - Date.parse(a.updated_at ?? ""))[0];
  const clipCount = latest?.state.clips?.length ?? 0;
  const previewUrl = latest?.state.source_media?.[0]?.playback_url;
  const gradient = ["from-[#1d2730] via-[#101d22] to-[#171416]", "from-[#1a2631] via-[#10151d] to-[#172018]", "from-[#241c2b] via-[#14151c] to-[#111e22]"][index % 3];
  return (
    <article className="overflow-hidden rounded-[18px] border border-[#262b2f] bg-[linear-gradient(105deg,rgba(24,26,28,0.96),rgba(12,13,14,0.96))] shadow-[0_18px_50px_rgba(0,0,0,0.24)]">
      <div className="grid min-h-[142px] grid-cols-[112px_minmax(0,1fr)_36px] items-center gap-4 px-4 py-4 lg:grid-cols-[156px_minmax(0,1fr)_220px_40px] lg:gap-7 lg:px-5 lg:py-5">
        <button type="button" onClick={() => onOpen(project, latest)} className={`relative grid h-[96px] w-[112px] place-items-center overflow-hidden rounded-[14px] border border-white/10 bg-gradient-to-br lg:h-[120px] lg:w-[156px] ${gradient}`} aria-label={`打开项目 ${project.name}`}>
          {previewUrl ? (
            <video src={previewUrl} muted playsInline preload="metadata" aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full object-cover" />
          ) : (
            <CamCatMark className="h-11 w-11 text-white/70" />
          )}
          <span className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-white/[0.03]" />
        </button>
        <button data-testid="project-card-summary" type="button" onClick={() => onOpen(project, latest)} className="min-w-0 self-stretch py-1 text-left lg:py-2">
          <div className="flex min-w-0 items-center gap-3">
            <h2 className="truncate text-[17px] font-semibold text-white sm:text-[20px] lg:text-[22px]">{project.name}</h2>
            <ProjectStatusBadge ready={Boolean(latest)} className="hidden sm:inline-flex lg:hidden" />
          </div>
          <div className="mt-3 space-y-1.5 text-[12px] text-[#858f99] sm:text-[13px] lg:mt-4">
            <div className="truncate">创建：{formatProjectDate(project.created_at)}</div>
            <div>剪辑会话：{project.sessions.length}</div>
            <div className="flex gap-4 lg:hidden"><span>状态：v{latest?.state_version ?? 1}</span><span>片段：{clipCount}</span></div>
          </div>
        </button>
        <div className="hidden self-stretch flex-col justify-center gap-4 lg:flex">
          <ProjectStatusBadge ready={Boolean(latest)} />
          <div className="space-y-1.5 text-[13px] text-[#858f99]"><div>状态版本：v{latest?.state_version ?? 1}</div><div>计划片段：{clipCount}</div></div>
        </div>
        <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} aria-label={`展开 ${project.name} 会话`} className="grid h-10 w-9 place-items-center rounded-[10px] text-[#9aa3ac] hover:bg-white/[0.05] hover:text-white">{expanded ? <ChevronDown className="h-6 w-6" /> : <ChevronRight className="h-6 w-6" />}</button>
      </div>
      {expanded && <div className="border-t border-[#23272b] bg-[#0b0c0d] px-6 py-4"><div className="mb-3 flex items-center justify-between"><span className="text-[10px] font-semibold tracking-[0.18em] text-[#68727c]">EDITING SESSIONS</span><button type="button" onClick={() => onOpen(project)} className="inline-flex items-center gap-1.5 rounded-[9px] border border-[#30353a] px-3 py-2 text-[11px] text-white"><Plus className="h-3.5 w-3.5" />新建剪辑</button></div>{project.sessions.length ? <div className="space-y-2">{project.sessions.map((session) => <div key={session.editing_session_id} className="flex items-center gap-3 rounded-[11px] border border-[#22262a] bg-[#111315] px-4 py-3"><button type="button" onClick={() => onOpen(project, session)} className="min-w-0 flex-1 text-left"><div className="truncate text-[12px] font-medium text-white">{session.state.title ?? session.state.goal ?? `剪辑会话 ${session.editing_session_id.slice(0, 8)}`}</div><div className="mt-1 font-mono text-[10px] text-[#707983]">v{session.state_version} · {formatProjectDate(session.updated_at)}</div></button><button type="button" onClick={() => onDeleteSession(project.project_id, session.editing_session_id)} aria-label={`删除剪辑会话 ${session.editing_session_id}`} className="grid h-8 w-8 place-items-center rounded-[8px] text-[#7f8993] hover:bg-[#2a1010] hover:text-[#fca5a5]"><Trash2 className="h-4 w-4" /></button></div>)}</div> : <div className="py-5 text-center text-[12px] text-[#68727c]">该项目尚无剪辑会话</div>}</div>}
    </article>
  );
}

function ProjectStatusBadge({ ready, className = "" }: { ready: boolean; className?: string }) {
  return <span className={`w-fit items-center whitespace-nowrap rounded-[7px] border px-2.5 py-1 text-[10px] font-medium ${ready ? "border-[#246048] bg-[#0c241b] text-[#62dda9]" : "border-[#3c4650] bg-[#15191d] text-[#93a0ab]"} ${className || "inline-flex"}`}><span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${ready ? "bg-[#34d399]" : "bg-[#77818b]"}`} />{ready ? "Editing ready" : "New project"}</span>;
}

function ProjectRail({ onNavigate, disabled }: { onNavigate: (page: ProductPage) => void; disabled: boolean }) {
  const items = [
    { icon: BriefcaseBusiness, label: "项目列表", active: true },
    { icon: Activity, label: "媒体处理", page: "processing" as const },
    { icon: Scissors, label: "编辑计划", page: "editing" as const },
    { icon: Download, label: "导出渲染", page: "render" as const },
  ];
  return <aside data-testid="product-navigation" className="flex min-h-0 flex-col items-center justify-between border-r border-[#1b1d1f] bg-[#050606] py-4"><nav className="w-full space-y-2 px-2.5">{items.map(({ icon: Icon, label, active, page }) => <button type="button" key={label} onClick={() => page && onNavigate(page)} disabled={!active && disabled} aria-label={label} aria-current={active ? "page" : undefined} title={label} className={`flex h-16 w-full flex-col items-center justify-center gap-1 rounded-[10px] border text-[9px] ${active ? "border-[#2b3035] bg-[#17191c] text-white shadow-[0_10px_28px_rgba(0,0,0,0.3)]" : "border-transparent text-[#9099a2] hover:bg-[#121416] hover:text-white disabled:cursor-not-allowed disabled:opacity-35"}`}><Icon className="h-5 w-5" /><span>{label}</span></button>)}</nav><div className="grid h-12 w-12 place-items-center rounded-[12px] border border-[#2a2e32] bg-[#111315]"><CamCatMark className="h-7 w-7" /></div></aside>;
}

function CreateProjectDialog({ onClose, onCreate }: { onClose: () => void; onCreate: (name: string) => Promise<void> }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(undefined);
    try { await onCreate(name.trim()); } catch (caught) { setError(caught instanceof Error ? caught.message : "创建项目失败"); setBusy(false); }
  }
  return <div role="dialog" aria-modal="true" aria-labelledby="create-project-title" className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-6 backdrop-blur-sm"><form onSubmit={(event) => void submit(event)} className="w-full max-w-[480px] rounded-[20px] border border-[#30353a] bg-[#0c0e0f] p-7 shadow-[0_30px_100px_rgba(0,0,0,0.7)]"><div className="flex items-center justify-between"><div><div className="text-[10px] font-semibold tracking-[0.2em] text-[#68727c]">NEW PROJECT</div><h2 id="create-project-title" className="mt-2 text-2xl font-semibold text-white">新建 CamCat 项目</h2></div><button type="button" onClick={onClose} aria-label="关闭" className="grid h-10 w-10 place-items-center rounded-[10px] text-[#8b949e] hover:bg-white/[0.05] hover:text-white"><X className="h-5 w-5" /></button></div><label className="mt-7 block text-[12px] text-[#9aa3ac]">项目名称<input autoFocus value={name} onChange={(event) => setName(event.target.value)} maxLength={255} placeholder="例如：旅行短片 2026" className="mt-2 h-12 w-full rounded-[12px] border border-[#30353a] bg-[#060708] px-4 text-[14px] text-white outline-none placeholder:text-[#505860] focus:border-[#609cc0]" /></label>{error && <div role="alert" className="mt-3 text-[12px] text-[#fca5a5]">{error}</div>}<div className="mt-7 flex justify-end gap-3"><button type="button" onClick={onClose} className="rounded-[11px] border border-[#30353a] px-5 py-2.5 text-[12px] text-[#cbd3da]">取消</button><button type="submit" disabled={busy || !name.trim()} className="inline-flex items-center gap-2 rounded-[11px] bg-white px-5 py-2.5 text-[12px] font-semibold text-black disabled:opacity-40">{busy && <Loader2 className="h-4 w-4 animate-spin" />}创建并打开</button></div></form></div>;
}

function CamCatMark({ className }: { className?: string }) {
  return <svg className={`${className ?? "h-8 w-8"} shrink-0 text-white`} viewBox="0 0 20 18" aria-label="CamCat pixel cat logo" role="img" shapeRendering="crispEdges"><path fill="currentColor" fillRule="evenodd" d="M1 1h5v2h8V1h5v11h-2v3h-3v2H6v-2H3v-3H1V1Zm2 2v9h2v2h3v1h4v-1h3v-2h2V3h-3v2H6V3H3Z" /><rect x="6" y="8" width="2" height="2" fill="currentColor" /><rect x="12" y="8" width="2" height="2" fill="currentColor" /><path d="M9 11h2v1h2v1H7v-1h2v-1Z" fill="currentColor" /></svg>;
}

function formatProjectDate(value?: string) {
  if (!value) return "尚未更新";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}
