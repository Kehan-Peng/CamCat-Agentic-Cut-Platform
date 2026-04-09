def _upload_video(client, user_id: str, filename: str = "agentic.mp4"):
    return client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": (filename, b"agentic video bytes", "video/mp4")},
    )


def test_agentic_search_uses_in_memory_checkpointer_with_supplied_thread_id(client, monkeypatch):
    import backend.app.api.routes as routes

    _upload_video(client, "agentic-checkpoint-user")
    calls = {"passed": None}
    real_build_agent_graph = routes.build_agent_graph

    def capturing_build_agent_graph(segments, *, checkpointer=None):
        calls["passed"] = checkpointer
        return real_build_agent_graph(segments, checkpointer=checkpointer)

    monkeypatch.setattr(routes, "build_agent_graph", capturing_build_agent_graph)

    response = client.post(
        "/api/v1/search/agentic",
        headers={"X-User-Id": "agentic-checkpoint-user"},
        json={"query_text": "热血卡点", "thread_id": "api-thread-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "api-thread-1"
    assert body["state_snapshot"]["thread_id"] == "api-thread-1"
    assert calls["passed"] is routes.agent_checkpointer


def test_agentic_search_returns_grounded_plan_trace_ranked_segments_and_suggestions(client):
    upload_response = _upload_video(client, "agentic-owner")
    video_id = upload_response.json()["video_id"]

    response = client.post(
        "/api/v1/search/agentic",
        headers={"X-User-Id": "agentic-owner"},
        json={"query_text": "帮我找适合做热血卡点的视频素材", "top_k": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert {
        "plan",
        "rewritten_query",
        "tool_trace",
        "ranked_segments",
        "reflection",
        "final_answer",
        "creative_suggestion",
        "graph_run_id",
        "thread_id",
        "state_snapshot",
        "node_trace",
        "retrieved_segments",
        "reranked_segments",
        "reflection_result",
        "creative_suggestions",
    }.issubset(body)
    assert [step["tool_name"] for step in body["plan"]["steps"]] == [
        "query_rewrite",
        "search",
        "rerank",
        "creative_suggestion",
        "reflection",
    ]
    assert body["rewritten_query"]["original_query"] == "帮我找适合做热血卡点的视频素材"
    assert "high_energy" in body["rewritten_query"]["expanded_queries"]
    assert [entry["status"] for entry in body["tool_trace"]] == ["ok", "ok", "ok", "ok", "ok"]
    assert [entry["node_name"] for entry in body["node_trace"]] == [
        "query_rewrite",
        "retrieval",
        "rerank",
        "creative_suggestion",
        "final_answer",
        "reflection",
    ]
    assert body["graph_run_id"]
    assert body["thread_id"]
    assert body["state_snapshot"]["graph_run_id"] == body["graph_run_id"]
    assert body["state_snapshot"]["thread_id"] == body["thread_id"]
    assert body["retrieved_segments"]
    assert body["reranked_segments"] == body["ranked_segments"]
    assert body["reflection_result"] == body["reflection"]
    assert body["creative_suggestions"][0] == body["creative_suggestion"]
    assert body["reflection"]["passed"] is True
    assert body["reflection"]["issues"] == []
    assert body["creative_suggestion"]["recommended_bgm_style"]

    top_segment = body["ranked_segments"][0]
    assert top_segment["video_id"] == video_id
    assert {"start_time", "end_time", "reason", "evidence", "creative_suggestion"}.issubset(top_segment)
    evidence_text = " ".join(item["text"] for item in top_segment["evidence"])
    grounding_text = f"{top_segment['reason']} {evidence_text} {body['final_answer']}"
    assert any(term in grounding_text for term in ["高能", "high_energy", "highlight", "热血", "卡点"])
    assert top_segment["segment_id"] in body["final_answer"]
    assert str(top_segment["start_time"]) in body["final_answer"]
    assert str(top_segment["end_time"]) in body["final_answer"]
    assert top_segment["reason"] in body["final_answer"]


def test_agentic_search_blocks_cross_user_results(client):
    owner_response = _upload_video(client, "agentic-private-owner", filename="owner.mp4")
    owner_video_id = owner_response.json()["video_id"]
    _upload_video(client, "agentic-private-viewer", filename="viewer.mp4")

    response = client.post(
        "/api/v1/search/agentic",
        headers={"X-User-Id": "agentic-private-viewer"},
        json={"query_text": "热血卡点", "top_k": 10},
    )

    assert response.status_code == 200
    result_video_ids = {result["video_id"] for result in response.json()["ranked_segments"]}
    assert owner_video_id not in result_video_ids


def test_agentic_search_rejects_missing_or_blank_query_text(client):
    missing_response = client.post(
        "/api/v1/search/agentic",
        headers={"X-User-Id": "agentic-blank-user"},
        json={},
    )
    blank_response = client.post(
        "/api/v1/search/agentic",
        headers={"X-User-Id": "agentic-blank-user"},
        json={"query_text": "   "},
    )

    assert missing_response.status_code == 400
    assert blank_response.status_code == 400


def test_existing_search_response_shape_remains_backward_compatible(client):
    _upload_video(client, "agentic-compat-user")

    response = client.post(
        "/api/v1/search",
        headers={"X-User-Id": "agentic-compat-user"},
        json={"query_text": "帮我找适合做热血卡点的视频素材"},
    )

    assert response.status_code == 200
    body = response.json()
    assert {"query_rewrite", "expanded_queries", "results", "answer", "creative_suggestion"}.issubset(body)
    assert "ranked_segments" not in body
    assert "tool_trace" not in body
