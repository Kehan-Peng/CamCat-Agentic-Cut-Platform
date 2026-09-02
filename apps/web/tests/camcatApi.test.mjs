import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

async function loadApiModule() {
  const source = await readFile(new URL("../src/camcatApi.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
  });
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);
}

function response(body, init = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

test("uploadVideo sends real media and license provenance", async () => {
  const { createCamCatApiClient } = await loadApiModule();
  const requests = [];
  const client = createCamCatApiClient({
    baseUrl: "http://camcat.test",
    userId: "user_001",
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      return response({ video_id: "vid_1", status: "uploaded", job_id: "job_1" });
    },
  });
  const file = new File(["video"], "source.mp4", { type: "video/mp4" });

  await client.uploadVideo(file, { licenseName: "CC0", sourceUrl: "https://example.test/source" });

  const form = requests[0].init.body;
  assert.equal(requests[0].url, "http://camcat.test/api/v1/videos");
  assert.equal(requests[0].init.headers["X-User-Id"], "user_001");
  assert.ok(form instanceof FormData);
  assert.equal(form.get("license_name"), "CC0");
  assert.equal(form.get("source_url"), "https://example.test/source");
  assert.equal(form.get("analysis_mode"), "keyframes");
});

test("permanent library upload rejects missing or local-only provenance", async () => {
  const { createCamCatApiClient } = await loadApiModule();
  let requestCount = 0;
  const client = createCamCatApiClient({
    baseUrl: "http://camcat.test",
    userId: "user_001",
    fetchImpl: async () => {
      requestCount += 1;
      return response({ video_id: "should-not-exist" });
    },
  });
  const file = new File(["video"], "source.mp4", { type: "video/mp4" });

  await assert.rejects(() => client.uploadVideo(file), /license and HTTP\(S\) source URL/i);
  await assert.rejects(
    () =>
      client.uploadVideo(file, {
        licenseName: "user-provided",
        sourceUrl: "local://user-upload",
      }),
    /license and HTTP\(S\) source URL/i,
  );
  assert.equal(requestCount, 0);
});

test("user originals use the transient multi-file endpoint", async () => {
  const { createCamCatApiClient } = await loadApiModule();
  const requests = [];
  const client = createCamCatApiClient({
    baseUrl: "http://camcat.test",
    userId: "user_001",
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      return response({ batch_id: "b1", status: "queued", job_id: "j1", media: [] });
    },
  });

  await client.uploadSourceMedia([
    new File(["a"], "one.mp4", { type: "video/mp4" }),
    new File(["b"], "two.mov", { type: "video/quicktime" }),
  ]);

  assert.equal(requests[0].url, "http://camcat.test/api/v1/source-media");
  assert.equal(requests[0].init.body.getAll("files").length, 2);
});

test("text and image search share the multimodal request contract", async () => {
  const { createCamCatApiClient } = await loadApiModule();
  const requests = [];
  const client = createCamCatApiClient({
    baseUrl: "http://camcat.test",
    userId: "designer",
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      return response({ graph_run_id: "g1", ranked_segments: [], node_trace: [] });
    },
  });

  await client.runAgenticSearch("找海边日落", 6, "data:image/jpeg;base64,YQ==");

  const body = JSON.parse(requests[0].init.body);
  assert.equal(body.query_text, "找海边日落");
  assert.equal(body.query_image_base64, "data:image/jpeg;base64,YQ==");
  assert.equal(body.retrieval_mode, "multimodal");
  assert.equal(body.top_k, 6);
});

test("agent edit, render and job polling carry the state version", async () => {
  const { createCamCatApiClient } = await loadApiModule();
  const requests = [];
  const client = createCamCatApiClient({
    baseUrl: "http://camcat.test",
    userId: "designer",
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      if (url.endsWith("/agent")) {
        return response({ editing_session_id: "s1", state_version: 2, state: { clips: [{}] } });
      }
      if (url.endsWith("/render")) {
        return response({ job_id: "j1", status: "queued", progress: 0 });
      }
      return response({ job_id: "j1", status: "succeeded", progress: 1, result: { output_url: "https://cdn.test/out.mp4" } });
    },
  });

  await client.runEditingAgent("s1", 1, "剪成 15 秒");
  await client.renderEditingSession("s1", 2);
  const job = await client.getJob("j1");

  assert.deepEqual(JSON.parse(requests[0].init.body), { base_version: 1, instruction: "剪成 15 秒" });
  assert.equal(JSON.parse(requests[1].init.body).base_version, 2);
  assert.equal("resolution" in JSON.parse(requests[1].init.body), false);
  assert.equal(job.result.output_url, "https://cdn.test/out.mp4");
});

test("structured backend errors expose the conflict message", async () => {
  const { createCamCatApiClient } = await loadApiModule();
  const client = createCamCatApiClient({
    baseUrl: "http://camcat.test",
    userId: "designer",
    fetchImpl: async () =>
      response(
        { error: { code: "state_version_conflict", message: "状态已更新", details: { current_version: 4 } } },
        { status: 409 },
      ),
  });

  await assert.rejects(() => client.renderEditingSession("s1", 3), /状态已更新/);
});

test("job polling reports real progress before completion", async () => {
  const { waitForJob } = await loadApiModule();
  const jobs = [
    { job_id: "j1", status: "queued", progress: 0 },
    { job_id: "j1", status: "running", progress: 0.45 },
    { job_id: "j1", status: "succeeded", progress: 1 },
  ];
  const progress = [];

  const completed = await waitForJob(async () => jobs.shift(), "j1", {
    intervalMs: 0,
    timeoutMs: 1000,
    onProgress: (job) => progress.push([job.status, job.progress]),
  });

  assert.equal(completed.status, "succeeded");
  assert.deepEqual(progress, [
    ["queued", 0],
    ["running", 0.45],
    ["succeeded", 1],
  ]);
});

test("first edit creates a session and runs exactly one retrieval graph", async () => {
  const { runSearchAndPlan } = await loadApiModule();
  const calls = [];
  const api = {
    async createEditingSession(videoId, goal, sourceJobId) {
      calls.push(["create", videoId, goal, sourceJobId]);
      return { editing_session_id: "s1", state_version: 1, state: { clips: [] } };
    },
    async runEditingAgentStream(sessionId, version, instruction, onEvent, image) {
      calls.push(["edit", sessionId, version, instruction, image]);
      return {
        session: { editing_session_id: "s1", state_version: 2, state: { clips: [{ clip_id: "c1" }] } },
        agentRun: { graph_run_id: "g1", ranked_segments: [{ video_id: "vid_retrieved" }] },
      };
    },
  };

  const result = await runSearchAndPlan(api, {
    query: "剪成一条节奏明快的视频",
    sourceJobId: "source_job_1",
    queryImageBase64: "data:image/png;base64,YQ==",
  });

  assert.equal(result.editingSession.state.clips.length, 1);
  assert.deepEqual(calls, [
    ["create", undefined, "剪成一条节奏明快的视频", "source_job_1"],
    ["edit", "s1", 1, "剪成一条节奏明快的视频", "data:image/png;base64,YQ=="],
  ]);
});

test("SSE parser keeps node progress and completed session boundaries", async () => {
  const { parseServerSentEvents } = await loadApiModule();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('event: node_completed\ndata: {"message":"检索完成"}\n'));
      controller.enqueue(new TextEncoder().encode('\nevent: completed\ndata: {"message":"完成"}\n\n'));
      controller.close();
    },
  });

  const events = [];
  for await (const event of parseServerSentEvents(stream)) events.push(event);
  assert.deepEqual(events.map((item) => item.event), ["node_completed", "completed"]);
});

test("interrupted agent stream replays numbered events before polling truth", async () => {
  const { createCamCatApiClient } = await loadApiModule();
  const urls = [];
  const progress = [];
  const interrupted = new ReadableStream({
    start(controller) {
      controller.enqueue(
        new TextEncoder().encode(
          'id: 0\nevent: run_started\ndata: {"graph_run_id":"g1","message":"started"}\n\n',
        ),
      );
      controller.close();
    },
  });
  const replay = new ReadableStream({
    start(controller) {
      controller.enqueue(
        new TextEncoder().encode(
          'id: 1\nevent: node_completed\ndata: {"graph_run_id":"g1","node":"retrieve","message":"replayed"}\n\n',
        ),
      );
      controller.close();
    },
  });
  const client = createCamCatApiClient({
    baseUrl: "http://camcat.test",
    userId: "designer",
    fetchImpl: async (url) => {
      urls.push(url);
      if (url.endsWith("/agent/stream")) return new Response(interrupted);
      if (url.endsWith("/graph-runs/g1/events?after=0")) return new Response(replay);
      if (url.endsWith("/graph-runs/g1")) {
        return response({ status: "succeeded", editing_session_id: "s1" });
      }
      if (url.endsWith("/editing/sessions/s1")) {
        return response({ editing_session_id: "s1", state_version: 2, state: {} });
      }
      return response({ graph_run_id: "g1", ranked_segments: [], node_trace: [] });
    },
  });

  const result = await client.runEditingAgentStream("s1", 1, "edit", (event) => {
    progress.push(event);
  });

  assert.equal(result.session.state_version, 2);
  assert.ok(urls.some((url) => url.endsWith("/graph-runs/g1/events?after=0")));
  assert.ok(progress.some((event) => event.node === "retrieve" && event.message === "replayed"));
});
