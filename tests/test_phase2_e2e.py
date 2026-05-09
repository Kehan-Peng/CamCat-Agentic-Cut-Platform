def _upload_video(client, user_id: str, filename: str = "phase2-hot-blooded.mp4"):
    return client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": (filename, b"phase 2 acceptance video bytes", "video/mp4")},
    )


def _agentic_search(client, user_id: str, query: str, top_k: int = 5):
    return client.post(
        "/api/v1/search/agentic",
        headers={"X-User-Id": user_id},
        json={"query_text": query, "top_k": top_k},
    )


def _get_segment(client, user_id: str, segment_id: str):
    return client.get(
        f"/api/v1/segments/{segment_id}",
        headers={"X-User-Id": user_id},
    )


def _evidence_texts(segment_detail: dict) -> set[str]:
    return {
        evidence["text"]
        for evidence in segment_detail.get("evidence", [])
        if evidence.get("text")
    }


def _assert_reason_uses_available_evidence(result: dict, segment_detail: dict) -> None:
    reason = result["reason"]
    evidence_types = {
        evidence["evidence_type"]
        for evidence in segment_detail.get("evidence", [])
        if evidence.get("text")
    }

    if "ASR" in reason:
        assert segment_detail["asr_transcript"] or "asr" in evidence_types
    if "OCR" in reason:
        assert segment_detail["ocr_text"] or "ocr" in evidence_types
    if "视觉" in reason:
        assert segment_detail["frame_captions"] or "frame_caption" in evidence_types
    if "高运动" in reason:
        assert segment_detail["motion_score"] >= 0.85
    if "高光" in reason:
        assert segment_detail["highlight_score"] >= 0.85

    available_evidence = _evidence_texts(segment_detail)
    for evidence in result["evidence"]:
        assert evidence["text"] in available_evidence


def test_phase_2_agentic_acceptance_flow_is_grounded_and_user_scoped(client):
    owner_id = "phase2-owner"
    other_user_id = "phase2-other-user"
    query = "帮我找适合做热血卡点的视频素材"

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "service": "nova-backend"}

    upload_response = _upload_video(client, owner_id)
    assert upload_response.status_code == 200
    upload_body = upload_response.json()
    assert upload_body["video_id"]
    assert upload_body["status"]
    assert upload_body["filename"] == "phase2-hot-blooded.mp4"
    assert upload_body["segment_count"] >= 3
    owner_video_id = upload_body["video_id"]

    search_response = _agentic_search(client, owner_id, query)
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert {
        "plan",
        "rewritten_query",
        "tool_trace",
        "ranked_segments",
        "reflection",
        "final_answer",
        "creative_suggestion",
    }.issubset(search_body)
    assert search_body["ranked_segments"]

    expected_path = [
        "query_rewrite",
        "search",
        "rerank",
        "creative_suggestion",
        "reflection",
    ]
    assert [step["tool_name"] for step in search_body["plan"]["steps"]] == expected_path
    assert [entry["tool_name"] for entry in search_body["tool_trace"]] == expected_path
    assert [entry["status"] for entry in search_body["tool_trace"]] == ["ok"] * len(expected_path)
    assert search_body["rewritten_query"]["original_query"] == query
    assert "high_energy" in search_body["rewritten_query"]["expanded_queries"]
    assert search_body["reflection"]["passed"] is True
    assert search_body["reflection"]["issues"] == []
    assert search_body["creative_suggestion"]["recommended_bgm_style"]
    assert search_body["creative_suggestion"]["transition_suggestions"]

    top_result = search_body["ranked_segments"][0]
    assert {
        "segment_id",
        "video_id",
        "start_time",
        "end_time",
        "score",
        "reason",
        "evidence",
        "creative_suggestion",
    }.issubset(top_result)
    assert top_result["video_id"] == owner_video_id
    assert top_result["start_time"] < top_result["end_time"]
    assert top_result["score"] > 0
    assert top_result["reason"]
    assert top_result["evidence"]
    assert top_result["creative_suggestion"]

    top_detail_response = _get_segment(client, owner_id, top_result["segment_id"])
    assert top_detail_response.status_code == 200
    top_detail = top_detail_response.json()
    assert top_detail["segment_id"] == top_result["segment_id"]
    assert top_detail["video_id"] == owner_video_id
    assert (
        "high_energy" in top_detail["tags"]
        or "highlight" in top_detail["tags"]
        or top_detail["motion_score"] >= 0.85
        or top_detail["highlight_score"] >= 0.85
    )
    _assert_reason_uses_available_evidence(top_result, top_detail)

    final_answer = search_body["final_answer"]
    assert top_result["segment_id"] in final_answer
    assert str(top_result["start_time"]) in final_answer
    assert str(top_result["end_time"]) in final_answer
    assert top_result["reason"] in final_answer
    assert any(evidence["text"] in final_answer for evidence in top_result["evidence"])

    for result in search_body["ranked_segments"]:
        segment_response = _get_segment(client, owner_id, result["segment_id"])
        assert segment_response.status_code == 200
        segment_detail = segment_response.json()
        assert result["video_id"] == owner_video_id
        _assert_reason_uses_available_evidence(result, segment_detail)

    other_user_search_response = _agentic_search(client, other_user_id, query, top_k=10)
    assert other_user_search_response.status_code == 200
    assert owner_video_id not in {
        result["video_id"]
        for result in other_user_search_response.json()["ranked_segments"]
    }

    other_user_segment_response = _get_segment(client, other_user_id, top_result["segment_id"])
    assert other_user_segment_response.status_code == 404
