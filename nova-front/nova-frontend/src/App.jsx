import React, { useState } from 'react';
import { 
  Play, Pause, SkipBack, SkipForward, Volume2, Maximize, 
  Settings, Download, Share2, Mic, ArrowUp,
  FileVideo, FileText, CheckCircle2, Circle, Clock,
  MessageSquare, LayoutTemplate, Layers, Activity, 
  ChevronRight, MoreHorizontal, Video, Image as ImageIcon,
  Check, ChevronDown, FolderGit2
} from 'lucide-react';

export default function NovaWorkspace() {
  const [isPlaying, setIsPlaying] = useState(false);

  return (
    <div className="h-screen w-screen bg-[#0A0A0A] text-gray-300 font-sans flex flex-col overflow-hidden">
      {/* 顶部导航栏 */}
      <header className="h-14 border-b border-white/10 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-white font-bold text-xl">
            <div className="w-6 h-6 bg-white rounded-sm flex items-center justify-center text-black text-xs">N</div>
            Nova
          </div>
          <span className="text-sm font-medium border-l border-white/20 pl-4">Seaways 洗衣机槽清洁剂推广视频</span>
          <span className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded">v3.2</span>
          <span className="text-xs text-gray-500">Saved 10:57</span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center text-xs text-gray-400 mr-8">
            <span className="mr-2">Workflow</span>
            <div className="flex items-center">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <React.Fragment key={i}>
                  <div className={`w-2 h-2 rounded-full ${i <= 4 ? 'bg-white' : 'bg-gray-600'}`} />
                  {i < 6 && <div className={`w-4 h-[1px] ${i < 4 ? 'bg-white' : 'bg-gray-600'}`} />}
                </React.Fragment>
              ))}
            </div>
          </div>
          <button className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-white/10 rounded transition-colors">
            <Share2 className="w-4 h-4" /> Share
          </button>
          <button className="flex items-center gap-2 text-sm bg-white text-black px-4 py-1.5 rounded font-medium hover:bg-gray-200 transition-colors">
            <Download className="w-4 h-4" /> Export
            <ChevronDown className="w-3 h-3 ml-1" />
          </button>
          <div className="w-8 h-8 rounded-full bg-gray-700 ml-4 overflow-hidden border border-white/20">
            <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" alt="User" />
          </div>
        </div>
      </header>

      {/* 主体内容 */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* 最左侧窄边栏 - 导航 */}
        <div className="w-16 border-r border-white/10 flex flex-col items-center py-4 gap-6 shrink-0 bg-[#0A0A0A] z-10">
          <NavIcon icon={<LayoutTemplate />} label="Evidence" active />
          <NavIcon icon={<Activity />} label="State" />
          <NavIcon icon={<Layers />} label="Trace" />
          <NavIcon icon={<FolderGit2 />} label="Artifacts" />
          <div className="mt-auto">
            <NavIcon icon={<Settings />} label="Settings" />
          </div>
        </div>

        {/* 左侧面板 - Evidence / State / Trace / Artifacts */}
        <div className="w-[320px] border-r border-white/10 flex flex-col overflow-y-auto custom-scrollbar bg-[#0E0E0E]">
          {/* EVIDENCE */}
          <PanelSection title="EVIDENCE" badge="12">
            <div className="space-y-2">
              <EvidenceItem title="Seaways 产品视频.mp4" desc="00:15 • 9:16 • 1080x1920" active />
              <EvidenceItem title="产品卖点整理.md" desc="2.4 KB • Markdown" type="doc" />
            </div>
          </PanelSection>

          {/* ROUTE / STATE */}
          <PanelSection title="ROUTE / STATE">
            <div className="relative pt-2 pb-6 px-2 flex justify-between items-center text-xs text-gray-400">
              <div className="absolute top-4 left-6 right-6 h-[1px] bg-gray-700 -z-10" />
              <StateNode label="Inject" done />
              <StateNode label="Understand" done />
              <StateNode label="Plan" done />
              <StateNode label="Edit" active />
            </div>
          </PanelSection>

          {/* TRACE */}
          <PanelSection title="TRACE" badge="Live">
            <div className="space-y-3 text-xs font-mono text-gray-400">
              <TraceItem time="10:56:47" task="ingest_media" done />
              <TraceItem time="10:56:50" task="understand_content" done />
              <TraceItem time="10:56:52" task="create_task_board" done />
              <TraceItem time="10:56:58" task="write_subtitles" done />
              <TraceItem time="10:57:02" task="derive_clip_segments" done />
              <TraceItem time="10:57:08" task="render_clip_segment" active />
              <TraceItem time="10:57:19" task="export_video" pending />
            </div>
          </PanelSection>

          {/* ARTIFACTS */}
          <PanelSection title="ARTIFACTS">
             <div className="space-y-2">
              <ArtifactItem title="字幕文件.srt" desc="24 KB • 导出完成" />
              <ArtifactItem title="脚本方案_初稿_v1.md" desc="00:15 • 9:16 • 已同步" active />
            </div>
          </PanelSection>
        </div>

        {/* 中间工作区 - 视频与时间线 */}
        <div className="flex-1 flex flex-col min-w-[500px] bg-[#121212]">
          {/* 视频预览区 */}
          <div className="h-[55%] border-b border-white/10 flex flex-col p-4">
            <div className="flex gap-4 text-sm font-medium mb-3">
              <span className="text-white border-b-2 border-white pb-1">Edit</span>
              <span className="text-gray-500 hover:text-gray-300 cursor-pointer">Review</span>
            </div>
            
            <div className="flex-1 bg-black rounded-lg border border-white/10 relative overflow-hidden group flex items-center justify-center">
              {/* 模拟视频画面 */}
              <div className="absolute inset-0 bg-gradient-to-tr from-gray-900 to-gray-800 flex items-center justify-center">
                <div className="text-center">
                  <h1 className="text-4xl font-bold text-white mb-2 tracking-wider">深层去污<br/>洁净如新</h1>
                  <p className="text-gray-400 mt-4">Seaways 洗衣机槽清洁剂</p>
                  <div className="flex gap-4 justify-center mt-6 text-sm">
                    <span className="bg-white/10 px-3 py-1 rounded-full">99.9% 除菌率</span>
                    <span className="bg-white/10 px-3 py-1 rounded-full">强效去垢</span>
                  </div>
                </div>
              </div>

              {/* 视频控制栏 */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 flex items-center justify-between text-gray-300">
                <div className="flex items-center gap-4">
                  <button className="hover:text-white"><SkipBack className="w-5 h-5" /></button>
                  <button className="hover:text-white" onClick={() => setIsPlaying(!isPlaying)}>
                    {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
                  </button>
                  <button className="hover:text-white"><SkipForward className="w-5 h-5" /></button>
                  <span className="text-xs font-mono ml-2">00:06 / 00:15</span>
                </div>
                <div className="flex items-center gap-4">
                  <button className="hover:text-white"><Volume2 className="w-5 h-5" /></button>
                  <button className="hover:text-white"><Settings className="w-5 h-5" /></button>
                  <button className="hover:text-white"><Maximize className="w-5 h-5" /></button>
                </div>
              </div>
            </div>
          </div>

          {/* 时间线区 */}
          <div className="flex-1 flex flex-col p-4 overflow-hidden">
            <div className="flex gap-6 text-xs font-medium mb-4 text-gray-500">
              <span className="text-white bg-white/10 px-3 py-1 rounded-md cursor-pointer">Editing Plan</span>
              <span className="hover:text-gray-300 cursor-pointer py-1">Segments</span>
              <span className="hover:text-gray-300 cursor-pointer py-1">Subtitles</span>
              <span className="hover:text-gray-300 cursor-pointer py-1">Audit Log</span>
            </div>

            {/* Editing Plan Clips */}
            <div className="flex gap-2 mb-6 overflow-x-auto custom-scrollbar pb-2">
              <ClipBlock num="01" title="产品亮相" time="0:00 - 0:03" active />
              <ClipBlock num="02" title="室内污染" time="0:03 - 0:07" />
              <ClipBlock num="03" title="洁净细节" time="0:07 - 0:11" />
              <ClipBlock num="04" title="使用效果" time="0:11 - 0:13" />
              <ClipBlock num="05" title="CTA 结尾" time="0:13 - 0:15" />
            </div>

            {/* Timeline Tracks */}
            <div className="flex-1 overflow-y-auto custom-scrollbar relative">
               {/* 播放头指示器 */}
               <div className="absolute top-0 bottom-0 left-1/3 w-[1px] bg-red-500 z-20">
                 <div className="w-2 h-2 bg-red-500 rounded-full -translate-x-1/2 -top-1 absolute" />
               </div>

               <TrackRow label="Video">
                 <div className="h-10 bg-gray-800 rounded border border-gray-700 w-full overflow-hidden flex">
                    {/* 模拟缩略图序列 */}
                    {[...Array(12)].map((_, i) => (
                      <div key={i} className="flex-1 border-r border-gray-700/50 bg-[url('https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?auto=format&fit=crop&q=80&w=100')] bg-cover opacity-50" />
                    ))}
                 </div>
               </TrackRow>
               <TrackRow label="Overlay">
                 <div className="flex gap-1 w-full h-8">
                   <div className="bg-blue-900/40 border border-blue-500/30 rounded text-[10px] flex items-center px-2 w-[20%]">产品亮相</div>
                   <div className="bg-blue-900/40 border border-blue-500/30 rounded text-[10px] flex items-center px-2 w-[30%]">深层去污 洁净如新</div>
                   <div className="bg-blue-900/40 border border-blue-500/30 rounded text-[10px] flex items-center px-2 w-[25%]">99.9% 除菌率</div>
                 </div>
               </TrackRow>
               <TrackRow label="Subtitle">
                 <div className="flex gap-1 w-full h-8">
                   <div className="bg-purple-900/40 border border-purple-500/30 rounded text-[10px] flex items-center px-2 w-[30%]">你的洗衣机，真的干净吗？</div>
                   <div className="bg-purple-900/40 border border-purple-500/30 rounded text-[10px] flex items-center px-2 w-[40%]">看不见的污垢正在滋生细菌</div>
                 </div>
               </TrackRow>
               <TrackRow label="Audio">
                 <div className="h-10 w-full bg-[#1A1A1A] rounded border border-gray-800 flex items-center px-2">
                    {/* 模拟音频波形 */}
                    <div className="w-full h-4 flex items-center gap-[1px]">
                      {[...Array(100)].map((_, i) => (
                        <div key={i} className="w-1 bg-green-500/60 rounded-full" style={{ height: `${Math.random() * 100}%` }} />
                      ))}
                    </div>
                 </div>
               </TrackRow>
            </div>
          </div>
        </div>

        {/* 右侧面板 - Agent Chat */}
        <div className="w-[380px] border-l border-white/10 flex flex-col bg-[#0A0A0A]">
          <div className="h-12 border-b border-white/10 flex items-center justify-between px-4 shrink-0 text-sm font-medium">
            AGENT CHAT
            <MoreHorizontal className="w-4 h-4 text-gray-500" />
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
            {/* User Message */}
            <div className="flex flex-col items-end gap-1">
              <span className="text-[10px] text-gray-500 uppercase">You • 10:55</span>
              <div className="bg-white/10 px-4 py-2 rounded-2xl rounded-tr-sm text-sm max-w-[85%]">
                生成洗衣机槽清洁剂的短视频
              </div>
            </div>

            {/* Assistant Message */}
            <div className="flex flex-col items-start gap-2">
              <div className="flex items-center gap-2 text-[10px] text-gray-500 uppercase w-full">
                <div className="w-4 h-4 rounded-sm bg-blue-600 flex items-center justify-center text-white font-bold">A</div>
                Assistant • 10:55
                <span className="ml-auto flex items-center gap-1 text-green-500">
                  <CheckCircle2 className="w-3 h-3" /> 已完成
                </span>
              </div>

              {/* Tool calls */}
              <div className="w-full space-y-2">
                <ToolCard title="create_task_board" time="0.05s" code={`{
  "summary": "生成洗衣机槽清洁剂推广视频",
  "selection_ids": [],
  "subtitle_overlay": true,
  "clip_mapping": true,
  "video_export": true,
  "export_latest": true
}`} />
                <ToolSummary title="write_subtitles" time="0.5s" />
                
                <div className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs flex items-center justify-between cursor-pointer hover:bg-white/10">
                   <div className="flex items-center gap-2 text-gray-400">
                     <Clock className="w-3 h-3" /> 思考过程
                   </div>
                   <ChevronDown className="w-3 h-3" />
                </div>

                <ToolSummary title="derive_clip_segments" time="1.2s" />
                <ToolSummary title="render_clip_segment" time="3.5s" />
              </div>

              {/* Final Output */}
              <div className="w-full mt-2 bg-[#121212] border border-white/10 rounded-lg p-3 text-sm">
                <div className="flex items-center gap-2 mb-2 font-medium">
                  <Video className="w-4 h-4 text-green-400" /> 最终输出
                </div>
                <p className="text-gray-300 text-xs leading-relaxed mb-3">
                  视频已成功导出，可下载！🎉
                </p>
                <ul className="text-xs text-gray-400 space-y-1 list-disc pl-4">
                  <li>导出文件：seaways_cleaner_export.mp4</li>
                  <li>分辨率：1080x1920 (竖屏 TikTok)</li>
                  <li>字幕：内嵌硬字幕</li>
                  <li>下载地址：<span className="text-blue-400 underline cursor-pointer">/api/download/exports/seaways_cleaner_export.mp4</span></li>
                </ul>
              </div>
            </div>
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-white/10 bg-[#0E0E0E]">
            <div className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2 mb-3 border border-white/10">
              <div className="flex flex-col">
                <span className="text-xs font-medium text-white">ANALYSIS MODE</span>
                <span className="text-[10px] text-gray-500">选择视频处理和理解模式，返回不同级别的分析。</span>
              </div>
              <div className="flex bg-black rounded p-0.5">
                <button className="text-[10px] bg-white/20 text-white px-2 py-1 rounded shadow-sm">关键帧分析</button>
                <button className="text-[10px] text-gray-400 px-2 py-1 rounded hover:text-white">混剪分析</button>
              </div>
            </div>

            <div className="flex gap-2 mb-3 overflow-x-auto custom-scrollbar pb-1">
              <span className="text-xs bg-white/10 px-2 py-1 rounded flex items-center gap-1 cursor-pointer hover:bg-white/20"><MessageSquare className="w-3 h-3"/> TikTok v</span>
              <span className="text-xs bg-white/10 px-2 py-1 rounded flex items-center gap-1 cursor-pointer hover:bg-white/20"><ImageIcon className="w-3 h-3"/> Upload</span>
              <span className="text-xs bg-white/10 px-2 py-1 rounded flex items-center gap-1 cursor-pointer hover:bg-white/20">Selling Points</span>
            </div>

            <div className="bg-[#1A1A1A] border border-white/20 rounded-xl flex items-center p-2 focus-within:border-white/50 transition-colors">
              <button className="p-2 text-gray-400 hover:text-white"><Settings className="w-4 h-4" /></button>
              <input 
                type="text" 
                placeholder="有问题，尽管问" 
                className="flex-1 bg-transparent text-sm text-white placeholder-gray-600 outline-none px-2"
              />
              <div className="flex items-center gap-1">
                 <button className="text-xs text-gray-400 bg-white/5 px-2 py-1 rounded flex items-center gap-1">
                   Instant <ChevronDown className="w-3 h-3"/>
                 </button>
                 <button className="p-2 text-gray-400 hover:text-white"><Mic className="w-4 h-4" /></button>
                 <button className="p-2 bg-white text-black rounded-lg hover:bg-gray-200 ml-1">
                   <ArrowUp className="w-4 h-4" />
                 </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

// 辅助组件封装
function NavIcon({ icon, label, active = false }) {
  return (
    <div className={`relative group cursor-pointer flex justify-center w-full`}>
      {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-white rounded-r-md" />}
      <div className={`p-2 rounded-lg ${active ? 'text-white bg-white/10' : 'text-gray-500 hover:text-white hover:bg-white/5'}`}>
        {React.cloneElement(icon, { className: "w-5 h-5" })}
      </div>
    </div>
  );
}

function PanelSection({ title, badge, children }) {
  return (
    <div className="py-4 px-4 border-b border-white/5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[11px] font-semibold text-gray-500 tracking-wider uppercase">{title}</h3>
        {badge && <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded text-gray-400">{badge}</span>}
      </div>
      {children}
    </div>
  );
}

function EvidenceItem({ title, desc, active, type = 'video' }) {
  return (
    <div className={`flex gap-3 p-2 rounded-lg cursor-pointer ${active ? 'bg-white/10' : 'hover:bg-white/5'}`}>
      <div className="w-16 h-12 bg-gray-800 rounded relative overflow-hidden shrink-0 flex items-center justify-center">
        {type === 'video' ? (
          <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1582735689369-4fe89db7114c?auto=format&fit=crop&q=80&w=200')] bg-cover opacity-60" />
        ) : (
           <FileText className="w-5 h-5 text-gray-500" />
        )}
      </div>
      <div className="flex flex-col justify-center overflow-hidden">
        <span className="text-sm text-gray-200 truncate">{title}</span>
        <span className="text-[10px] text-gray-500 mt-0.5">{desc}</span>
      </div>
    </div>
  );
}

function StateNode({ label, done, active }) {
  return (
    <div className="flex flex-col items-center gap-2 z-10">
      <div className={`w-5 h-5 rounded-full flex items-center justify-center border-2 
        ${done ? 'bg-black border-gray-600 text-gray-400' : 
          active ? 'bg-transparent border-white text-white' : 'bg-black border-gray-800'}`}>
        {done && <Check className="w-3 h-3" />}
        {active && <div className="w-1.5 h-1.5 bg-white rounded-full" />}
      </div>
      <span className={active ? 'text-white font-medium' : ''}>{label}</span>
    </div>
  );
}

function TraceItem({ time, task, done, active, pending }) {
  return (
    <div className="flex items-start gap-3 group">
      <span className="text-gray-600 shrink-0">{time}</span>
      <span className={`flex-1 ${active ? 'text-white font-medium' : pending ? 'text-gray-600' : 'text-gray-400'}`}>{task}</span>
      {done && <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0 mt-0.5" />}
      {active && <div className="w-3 h-3 rounded-full border border-white border-t-transparent animate-spin shrink-0 mt-0.5" />}
      {pending && <Circle className="w-3 h-3 text-gray-700 shrink-0 mt-0.5" />}
    </div>
  );
}

function ArtifactItem({ title, desc, active }) {
  return (
    <div className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer 
      ${active ? 'border-white/30 bg-white/5' : 'border-white/5 hover:border-white/10 bg-[#121212]'}`}>
      <div className="flex items-center gap-3 overflow-hidden">
        <FileVideo className="w-4 h-4 text-gray-400 shrink-0" />
        <div className="flex flex-col truncate">
          <span className="text-sm text-gray-200 truncate">{title}</span>
          <span className="text-[10px] text-gray-500">{desc}</span>
        </div>
      </div>
      <Download className="w-4 h-4 text-gray-500 hover:text-white shrink-0" />
    </div>
  );
}

function ClipBlock({ num, title, time, active }) {
  return (
    <div className={`shrink-0 p-2.5 rounded-lg border ${active ? 'border-white bg-white/10' : 'border-white/10 bg-[#1A1A1A] hover:border-white/30'} cursor-pointer min-w-[120px]`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] bg-white/20 text-white px-1 rounded">{num}</span>
        <span className="text-xs font-medium text-gray-200">{title}</span>
      </div>
      <div className="text-[10px] text-gray-500">{time}</div>
    </div>
  );
}

function TrackRow({ label, children }) {
  return (
    <div className="flex items-center mb-2 h-10">
      <div className="w-16 text-[10px] text-gray-500 font-medium shrink-0">{label}</div>
      <div className="flex-1 relative">
        {children}
      </div>
    </div>
  );
}

function ToolCard({ title, time, code }) {
  return (
    <div className="bg-black/50 border border-white/10 rounded-lg overflow-hidden font-mono text-xs">
      <div className="px-3 py-2 bg-white/5 border-b border-white/10 flex justify-between items-center text-gray-300">
        <span className="flex items-center gap-2">
          <Settings className="w-3 h-3" /> {title}
        </span>
        <span className="text-gray-600">{time} <CheckCircle2 className="w-3 h-3 inline text-gray-600 ml-1"/></span>
      </div>
      <pre className="p-3 text-gray-400 overflow-x-auto m-0 leading-relaxed">
        {code}
      </pre>
    </div>
  );
}

function ToolSummary({ title, time }) {
  return (
    <div className="bg-transparent border border-white/10 rounded-lg px-3 py-2 text-xs flex items-center justify-between text-gray-400">
      <span className="flex items-center gap-2">
         <Settings className="w-3 h-3" /> {title}
      </span>
      <span className="text-gray-600">{time} <CheckCircle2 className="w-3 h-3 inline ml-1"/></span>
    </div>
  );
}
