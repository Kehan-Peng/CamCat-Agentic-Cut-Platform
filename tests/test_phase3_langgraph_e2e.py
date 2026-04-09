def test_phase_3_langgraph_agentic_acceptance_flow(client):
    user_id = "phase3-langgraph-owner"
    upload_response = client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": ("phase3-hot-blooded.mp4", b"phase 3 acceptance video bytes", "video/mp4")},
    )
    assert upload_response.status_code == 200
    video_id = upload_response.json()["video_id"]

    search_response = client.post(
        "/api/v1/search/agentic",
        headers={"X-User-Id": user_id},
        json={
            "query_text": "帮我找适合做热血卡点的视频素材",
            "top_k": 3,
            "thread_id": "phase3-thread-1",
        },
    )

    assert search_response.status_code == 200
    body = search_response.json()
    assert body["graph_run_id"]
    assert body["thread_id"] == "phase3-thread-1"
    assert [entry["node_name"] for entry in body["node_trace"]] == [
        "query_rewrite",
        "retrieval",
        "rerank",
        "creative_suggestion",
        "final_answer",
        "reflection",
    ]
    assert [entry["status"] for entry in body["node_trace"]] == ["ok"] * 6
    assert body["retrieved_segments"]
    assert body["reranked_segments"] == body["ranked_segments"]
    assert body["reflection"]["passed"] is True
    assert body["reflection_result"] == body["reflection"]
    assert body["final_answer"]

    top_segment = body["ranked_segments"][0]
    assert top_segment["video_id"] == video_id
    assert top_segment["segment_id"] in body["final_answer"]
    assert top_segment["reason"] in body["final_answer"]
    assert any(evidence["text"] in body["final_answer"] for evidence in top_segment["evidence"])
    assert body["state_snapshot"]["final_answer"] == body["final_answer"]
    assert body["state_snapshot"]["node_trace"] == body["node_trace"]
