def _upload_video(client, user_id: str, filename: str = "vertical-slice.mp4"):
    return client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": (filename, b"small uploaded video bytes", "video/mp4")},
    )


def _get_segment(client, user_id: str, segment_id: str):
    return client.get(
        f"/api/v1/segments/{segment_id}",
        headers={"X-User-Id": user_id},
    )


def _evidence_types(segment_detail: dict) -> set[str]:
    return {
        evidence["evidence_type"]
        for evidence in segment_detail.get("evidence", [])
        if evidence.get("text")
    }


def _assert_reason_is_grounded(result: dict, segment_detail: dict) -> None:
    reason = result["reason"]
    evidence_types = _evidence_types(segment_detail)

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

    segment_evidence_texts = {
        evidence["text"] for evidence in segment_detail.get("evidence", [])
    }
    for evidence in result["evidence"]:
        assert evidence["text"] in segment_evidence_texts


def test_phase_1_vertical_slice_acceptance_flow(client):
    user_a = "vertical-slice-user-a"
    user_b = "vertical-slice-user-b"

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "service": "nova-backend"}

    upload_response = _upload_video(client, user_a, filename="hot-blooded-clip.mp4")
    assert upload_response.status_code == 200
    upload_body = upload_response.json()
    assert upload_body["video_id"]
    assert upload_body["status"]
    assert upload_body["filename"] == "hot-blooded-clip.mp4"
    assert upload_body["segment_count"] >= 3

    video_id = upload_body["video_id"]
    video_response = client.get(
        f"/api/v1/videos/{video_id}",
        headers={"X-User-Id": user_a},
    )
    assert video_response.status_code == 200
    video_body = video_response.json()
    assert video_body["video_id"] == video_id
    assert video_body["user_id"] == user_a
    assert video_body["filename"] == "hot-blooded-clip.mp4"
    assert video_body["segment_count"] == upload_body["segment_count"]

    search_response = client.post(
        "/api/v1/search",
        headers={"X-User-Id": user_a},
        json={"query_text": "帮我找适合做热血卡点的视频素材", "top_k": 5},
    )
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["results"]
    assert search_body["creative_suggestion"]["recommended_bgm_style"]
    assert search_body["creative_suggestion"]["transition_suggestions"]

    scores = [result["score"] for result in search_body["results"]]
    assert scores == sorted(scores, reverse=True)

    for result in search_body["results"]:
        assert {
            "segment_id",
            "video_id",
            "start_time",
            "end_time",
            "score",
            "reason",
            "evidence",
        }.issubset(result)
        assert result["video_id"] == video_id
        assert result["start_time"] < result["end_time"]
        assert result["score"] > 0
        assert result["reason"]
        assert result["evidence"]
        assert "creative_suggestion" in result

        detail_response = _get_segment(client, user_a, result["segment_id"])
        assert detail_response.status_code == 200
        detail_body = detail_response.json()
        assert detail_body["segment_id"] == result["segment_id"]
        assert detail_body["video_id"] == result["video_id"]
        _assert_reason_is_grounded(result, detail_body)

    top_result = search_body["results"][0]
    top_detail = _get_segment(client, user_a, top_result["segment_id"]).json()
    assert (
        "high_energy" in top_detail["tags"]
        or "highlight" in top_detail["tags"]
        or top_detail["motion_score"] >= 0.85
        or top_detail["highlight_score"] >= 0.85
    )

    cross_user_search = client.post(
        "/api/v1/search",
        headers={"X-User-Id": user_b},
        json={"query_text": "热血卡点", "top_k": 10},
    )
    assert cross_user_search.status_code == 200
    assert video_id not in {
        result["video_id"] for result in cross_user_search.json()["results"]
    }

    cross_user_segment = _get_segment(client, user_b, top_result["segment_id"])
    assert cross_user_segment.status_code == 404
