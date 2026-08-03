import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../CamCatWorkspacePage.tsx", import.meta.url), "utf8");
const appSource = await readFile(new URL("../CamCatApp.tsx", import.meta.url), "utf8");
const tailwindSource = await readFile(new URL("../tailwind.config.js", import.meta.url), "utf8");
const nginxSource = await readFile(new URL("../nginx.conf", import.meta.url), "utf8");

test("idle workspace never presents seeded evidence or completed production work", () => {
  for (const forbidden of [
    "traceRowsSeed",
    "evidenceItems",
    "Prototype ready",
    "最终视频_导出.mp4",
    "https://i.pravatar.cc",
    "washing machine drum background",
  ]) {
    assert.equal(source.includes(forbidden), false, `found seeded UI value: ${forbidden}`);
  }
});

test("idle workspace exposes an explicit real-data empty state", () => {
  assert.match(source, /等待真实素材与任务/);
  assert.match(source, /上传视频或输入多模态检索需求/);
});

test("editor exposes automatic output ratio instead of hard-coding 9:16", () => {
  assert.equal(source.includes('label="9:16"'), false);
  assert.equal(source.includes("\n          9:16\n"), false);
  assert.match(source, /Auto.*aspect_ratio/s);
  assert.match(source, /multiple onChange=\{onFileChange\}/);
});

test("pixel cat uses the design outline instead of scattered mosaic pixels", () => {
  assert.match(source, /viewBox="0 0 20 18"/);
  assert.match(source, /data-logo-part="outline"/);
  assert.equal(source.includes("].map(([x, y]) =>"), false);
});

test("the first search runs retrieval and plan generation as one workflow", () => {
  assert.match(source, /runSearchAndPlan/);
  assert.match(source, /setEditingSession\(result\.editingSession\)/);
});

test("project navigation stays beside content with an explicit two-column layout", () => {
  assert.match(appSource, /data-testid="project-layout"/);
  assert.match(appSource, /gridTemplateColumns:\s*"96px minmax\(0, 1fr\)"/);
  assert.doesNotMatch(appSource, /grid-cols-\[112px_minmax\(0,1fr\)\]/);
});

test("Tailwind scans every top-level React product page", () => {
  assert.match(tailwindSource, /\.\/\*\.tsx/);
});

test("the editor center column is a real vertical scroll region", () => {
  assert.match(source, /data-testid="editor-scroll-region"/);
  assert.match(source, /overflow-y-auto/);
  assert.match(source, /min-h-\[360px\].*shrink-0/s);
});

test("workspace chrome remains outside product-page conditionals", () => {
  const shellStart = source.indexOf("function AppShell");
  const shellEnd = source.indexOf("function TopHeader");
  const shell = source.slice(shellStart, shellEnd);
  assert.match(shell, /<TopHeader workspace=\{workspace\} \/>/);
  assert.match(shell, /<ProductRail workspace=\{workspace\} \/>/);
  assert.match(shell, /workspace\.page === "processing"/);
  assert.match(shell, /workspace\.page === "render"/);
});

test("same-origin proxy re-resolves the API after Compose service recreation", () => {
  assert.match(nginxSource, /resolver 127\.0\.0\.11 valid=10s;/);
  assert.match(nginxSource, /set \$camcat_api http:\/\/api:8000;/);
  assert.match(nginxSource, /proxy_pass \$camcat_api;/);
});
