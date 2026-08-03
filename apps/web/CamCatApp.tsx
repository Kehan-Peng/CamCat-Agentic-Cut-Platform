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
    <div className="h-screen overflow-hidden bg-[radial-gradient(circle_at_55%_-15%,#131920_0%,#060708_38%,#030404_100%)] text-[#cbd2d8]">
      <div className="grid h-full w-full max-w-[1540px] grid-cols-[112px_minmax(0,1fr)] gap-5 p-6">
        <ProjectRail onNavigate={onNavigateProduct} disabled={!projects.length} />
        <main className="flex min-h-0 flex-col overflow-hidden rounded-[22px] border border-[#2a2e32] bg-[#08090a]/95 shadow-[0_35px_120px_rgba(0,0,0,0.42)]">
          <header className="flex h-[112px] shrink-0 items-center justify-between border-b border-[#23272b] px-10">
            <div className="flex items-center gap-4 text-white">
              <CamCatMark className="h-11 w-11" />
              <div>
                <div className="text-[30px] font-black leading-none">CamCat</div>
                <div className="mt-2 text-[10px] font-semibold tracking-[0.24em] text-[#69737d]">MULTIMODAL VIDEO STUDIO</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button type="button" onClick={onRefresh} aria-label="刷新项目" className="grid h-12 w-12 place-items-center rounded-[13px] border border-[#2d3237] bg-[#111315] text-[#aab2ba] hover:bg-[#181a1d] hover:text-white"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /></button>
              <button type="button" onClick={onCreate} className="inline-flex h-12 items-center gap-2 rounded-[13px] border border-[#34393e] bg-[linear-gradient(180deg,#202327,#151719)] px-6 text-[14px] font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] hover:border-[#4a5158]"><Plus className="h-5 w-5" />新建项目</button>
            </div>
          </header>

          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-10 py-8 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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
          </div>
        </main>
      </div>
      {children}
    </div>
  );
}

function ProjectCard({ project, index, onOpen, onDeleteSession }: { project: ProjectWithSessions; index: number; onOpen: (project: ProjectResponse, session?: EditingSessionResponse) => void; onDeleteSession: (projectId: string, sessionId: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const latest = [...project.sessions].sort((a, b) => Date.parse(b.updated_at ?? "") - Date.parse(a.updated_at ?? ""))[0];
  const clipCount = latest?.state.clips?.length ?? 0;
  const gradient = ["from-[#1d2730] via-[#101d22] to-[#171416]", "from-[#1a2631] via-[#10151d] to-[#172018]", "from-[#241c2b] via-[#14151c] to-[#111e22]"][index % 3];
  return (
    <article className="overflow-hidden rounded-[18px] border border-[#262b2f] bg-[linear-gradient(105deg,rgba(24,26,28,0.96),rgba(12,13,14,0.96))] shadow-[0_18px_50px_rgba(0,0,0,0.24)]">
      <div className="flex min-h-[150px] items-center gap-7 px-6 py-5">
        <button type="button" onClick={() => onOpen(project, latest)} className={`grid h-[108px] w-[164px] shrink-0 place-items-center overflow-hidden rounded-[14px] border border-white/10 bg-gradient-to-br ${gradient}`} aria-label={`打开项目 ${project.name}`}><CamCatMark className="h-12 w-12 text-white/70" /></button>
        <button type="button" onClick={() => onOpen(project, latest)} className="min-w-0 flex-1 text-left">
          <div className="flex items-center gap-3"><h2 className="truncate text-[22px] font-semibold text-white">{project.name}</h2><span className={`rounded-[7px] border px-2.5 py-1 text-[10px] font-medium ${latest ? "border-[#246048] bg-[#0c241b] text-[#62dda9]" : "border-[#3c4650] bg-[#15191d] text-[#93a0ab]"}`}><span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${latest ? "bg-[#34d399]" : "bg-[#77818b]"}`} />{latest ? "Editing ready" : "New project"}</span></div>
          <div className="mt-4 grid grid-cols-2 gap-x-12 gap-y-2 text-[13px] text-[#858f99]"><span>创建：{formatProjectDate(project.created_at)}</span><span>剪辑会话：{project.sessions.length}</span><span>状态版本：v{latest?.state_version ?? 1}</span><span>计划片段：{clipCount}</span></div>
        </button>
        <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} aria-label={`展开 ${project.name} 会话`} className="grid h-12 w-12 place-items-center rounded-[12px] text-[#9aa3ac] hover:bg-white/[0.05] hover:text-white">{expanded ? <ChevronDown className="h-6 w-6" /> : <ChevronRight className="h-6 w-6" />}</button>
      </div>
      {expanded && <div className="border-t border-[#23272b] bg-[#0b0c0d] px-6 py-4"><div className="mb-3 flex items-center justify-between"><span className="text-[10px] font-semibold tracking-[0.18em] text-[#68727c]">EDITING SESSIONS</span><button type="button" onClick={() => onOpen(project)} className="inline-flex items-center gap-1.5 rounded-[9px] border border-[#30353a] px-3 py-2 text-[11px] text-white"><Plus className="h-3.5 w-3.5" />新建剪辑</button></div>{project.sessions.length ? <div className="space-y-2">{project.sessions.map((session) => <div key={session.editing_session_id} className="flex items-center gap-3 rounded-[11px] border border-[#22262a] bg-[#111315] px-4 py-3"><button type="button" onClick={() => onOpen(project, session)} className="min-w-0 flex-1 text-left"><div className="truncate text-[12px] font-medium text-white">{session.state.title ?? session.state.goal ?? `剪辑会话 ${session.editing_session_id.slice(0, 8)}`}</div><div className="mt-1 font-mono text-[10px] text-[#707983]">v{session.state_version} · {formatProjectDate(session.updated_at)}</div></button><button type="button" onClick={() => onDeleteSession(project.project_id, session.editing_session_id)} aria-label={`删除剪辑会话 ${session.editing_session_id}`} className="grid h-8 w-8 place-items-center rounded-[8px] text-[#7f8993] hover:bg-[#2a1010] hover:text-[#fca5a5]"><Trash2 className="h-4 w-4" /></button></div>)}</div> : <div className="py-5 text-center text-[12px] text-[#68727c]">该项目尚无剪辑会话</div>}</div>}
    </article>
  );
}

function ProjectRail({ onNavigate, disabled }: { onNavigate: (page: ProductPage) => void; disabled: boolean }) {
  const items = [
    { icon: BriefcaseBusiness, label: "项目列表", active: true },
    { icon: Activity, label: "媒体处理", page: "processing" as const },
    { icon: Scissors, label: "编辑计划", page: "editing" as const },
    { icon: Download, label: "导出渲染", page: "render" as const },
  ];
  return <aside className="flex flex-col items-center justify-between rounded-[22px] border border-[#2a2e32] bg-[#090a0b]/95 py-6"><nav className="space-y-3">{items.map(({ icon: Icon, label, active, page }) => <button type="button" key={label} onClick={() => page && onNavigate(page)} disabled={!active && disabled} aria-label={label} aria-current={active ? "page" : undefined} title={label} className={`flex h-16 w-16 flex-col items-center justify-center gap-1 rounded-[14px] border text-[9px] ${active ? "border-[#2b3035] bg-[#17191c] text-white shadow-[0_10px_28px_rgba(0,0,0,0.3)]" : "border-transparent text-[#9099a2] hover:bg-[#121416] hover:text-white disabled:cursor-not-allowed disabled:opacity-35"}`}><Icon className="h-5 w-5" /><span>{label}</span></button>)}</nav><div className="grid h-16 w-16 place-items-center rounded-[17px] border border-[#2a2e32] bg-[#111315]"><CamCatMark className="h-9 w-9" /></div></aside>;
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
