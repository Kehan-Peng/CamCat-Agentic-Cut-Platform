import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../CamCatWorkspacePage.tsx", import.meta.url), "utf8");

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
