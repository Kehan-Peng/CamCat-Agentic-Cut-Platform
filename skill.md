---
name: frontend-workspace-page-design
description: Use when transforming an existing frontend page into a production-grade dark workspace UI from a visual reference, especially AI video editing, dashboard, editor, or agent-workflow pages. Covers reference-image decomposition, dense multi-panel layout, dark visual systems, timeline/editor UI details, and implementation/validation steps in React/Tailwind.
---

# Frontend Workspace Page Design

## Purpose

Use this skill to refactor an existing frontend page into a professional, dense workspace UI that closely follows a supplied reference image. Prioritize structure, information density, visual hierarchy, spacing, and component fidelity over superficial color changes.

## Core Workflow

1. Read the existing page and identify the real entry component, app shell, layout wrappers, CSS system, icon library, and build command.
2. Inspect the reference image and decompose it into layout regions before editing code:
   - global header
   - left vertical navigation
   - left resource/status panel
   - main editor canvas
   - timeline or data-dense work surface
   - right agent/chat/properties panel
3. Convert the design into a stable shell first, then fill each panel with production-like content and states.
4. Keep edits scoped to the page and nearby app shell unless the project needs missing bootstrap files.
5. Build and open the page after implementation. Fix compile issues before reporting completion.

## Layout Rules

- Use `100vh` and prevent whole-page scrolling for app-like tools.
- Let panels scroll internally: resource lists, logs, chat, and sidebars.
- Use fixed side rail widths and fixed right panel widths on desktop; let the center editor flex.
- Prefer clear 1px region borders over heavy shadows.
- Preserve a strong center of gravity: preview/canvas and timeline should occupy most visual weight.
- For desktop-first production tools, optimize for 1440px+ while keeping reasonable collapse behavior.

Recommended workspace proportions:

- left rail: 84-96px
- left resource panel: 340-420px
- center editor: flexible, largest region
- right agent/properties panel: 500-560px
- header: 64-76px

## Dark Visual System

Use a restrained, near-black palette:

- app background: `#030404`
- header/rail background: `#050606`
- panel background: `#080909` or `#0b0c0d`
- card background: `#111213` or `#141516`
- border: `#1f2224`, `#202326`, `#25282b`
- primary text: `#f5f7f8`
- secondary text: `#9ca3af`
- muted text: `#6b7280`
- small blue accent: `#38bdf8` or `#6cc7ff`
- small success accent: `#34d399`

Use accents sparingly: active outlines, status dots, tiny checks, selected timeline clips. Avoid large saturated fills.

## Component Patterns

### Header

- Start with project context unless a separate rail owns the brand.
- Include project name, dropdown affordance, version badge, save status, workflow completion, share/export actions, and user status.
- Use dark outline buttons for secondary actions and white/near-white fill for the main export action.

### Brand And Left Rail

- Avoid duplicate brand marks. If the rail owns the brand, remove brand logo/text from the header.
- Align the brand icon to the same vertical center axis as nav icons.
- Keep nav items vertically consistent: icon, label, fixed height, selected state, bottom utility icons.
- Pixel or custom logos should be implemented as crisp SVG rectangles with `shapeRendering="crispEdges"` when a pixel-art look is required.

### Evidence / Resource Panel

- Use compact cards with thumbnail, title, metadata, and a small material cue.
- Video assets should show a real/mock thumbnail, play icon, and subtle waveform.
- Documents should show a document icon and preview/progress lines.
- Keep card height around 74-90px for dense tools.

### Route / State

- Show workflow as nodes connected by dashed or thin lines.
- Completed nodes use check icons.
- Current or final node may receive a small blue highlight.
- Labels should remain short and legible below nodes.

### Trace / Logs

- Use monospace at 11-12px.
- Include time, step name, status icon, and elapsed time for current/final row.
- Current row can use a slightly brighter background, not a saturated color block.

### Editor Preview

- Use a large, bordered preview frame with a fixed aspect ratio.
- Build a believable visual scene with image overlays, gradients, product mockups, and typography if real media is unavailable.
- Place product and marketing text with clear composition, not random decoration.
- Keep preview cinematic and dark; avoid over-bright backgrounds.

### Player Controls

- Add a separate control bar below preview.
- Include timecode, previous/back/play/forward/next controls, aspect badge, volume, and settings.
- Make play the primary control.

### Editing Plan

- Use tabs with a short active underline.
- Segment chips should include index, label, and time range.
- Selected chip should use a small blue border/glow; unselected chips stay dark.

### Multi-Track Timeline

Always include explicit track labels and a playhead:

- ruler: `00:00`, `00:03`, `00:06`, `00:09`, `00:12`, `00:15`
- playhead: thin white vertical line with a small top dot at the current time
- tracks: Video, Overlay, Subtitle, Audio, Markers
- video: continuous thumbnail strip
- overlay/subtitle: positioned clips based on start/end time
- audio: green waveform with file label
- markers: diamond markers with optional labels

Compute clip `left` and `width` from `start / duration` and `(end - start) / duration`.

### Agent Chat Panel

- Use a fixed right panel for agent workflows.
- Show user request bubble, assistant timestamp/status, tool call cards, collapsed tool rows, and expanded final output.
- Tool cards should include title, status, time, optional code block, and chevron.
- Code blocks use near-black background, monospace, and readable muted text.
- Keep final output actionable with filename, duration, resolution, subtitles, download path, and download button.

### Analysis Mode And Input

- Place analysis mode near the bottom of the right panel, above the composer.
- Use two pill toggles with a restrained selected state.
- Input composer should include platform/tool chips, plus button, placeholder, mode dropdown, mic, and send button.

## Implementation Notes For React + Tailwind

- Split large pages into semantic local components before polishing details.
- Keep mock data close to the page unless it is shared elsewhere.
- Use `lucide-react` for common UI icons.
- Use Tailwind arbitrary values for exact workspace dimensions and dark palette colors.
- Avoid broad refactors, global CSS churn, or new UI libraries unless required.
- For static mockups, CSS gradients and public image URLs are acceptable, but the page must still compile and run without custom backend services.

## Validation Checklist

Before finishing:

- Build passes with the project command, usually `npm run build`.
- The page opens locally and the dev server responds.
- Whole page does not scroll; panels scroll independently.
- Only one brand mark appears if the user requested a single brand entry.
- Header, rail, left panel, editor, timeline, and right agent panel are all present.
- Timeline includes all required tracks and a visible playhead.
- Agent panel includes complete tool chain and final output.
- Colors, borders, radius, font sizes, and spacing feel like one system.
- Git status is reviewed before committing or pushing.
