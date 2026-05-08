def _upload_video(client, user_id: str, filename: str = "agentic.mp4"):
    return client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": (filename, b"agentic video bytes", "video/mp4")},
    )


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
