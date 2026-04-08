def _upload_video(client, user_id: str, filename: str = "search.mp4"):
    return client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": (filename, b"small video bytes", "video/mp4")},
    )


def test_search_returns_ranked_segments_after_upload(client):
    upload_response = _upload_video(client, "search-owner")
    video_id = upload_response.json()["video_id"]

    response = client.post(
        "/api/v1/search",
        headers={"X-User-Id": "search-owner"},
        json={"query_text": "帮我找适合做热血卡点的视频素材", "top_k": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    scores = [result["score"] for result in body["results"]]
    assert scores == sorted(scores, reverse=True)
    assert body["results"][0]["video_id"] == video_id
    assert {"segment_id", "video_id", "start_time", "end_time", "score", "reason", "evidence", "creative_suggestion"}.issubset(
        body["results"][0]
    )


def test_search_blocks_cross_user_results(client):
    owner_response = _upload_video(client, "private-search-owner")
    owner_video_id = owner_response.json()["video_id"]
    _upload_video(client, "private-search-viewer")

    response = client.post(
        "/api/v1/search",
        headers={"X-User-Id": "private-search-viewer"},
        json={"query_text": "热血卡点", "top_k": 10},
    )

    assert response.status_code == 200
    result_video_ids = {result["video_id"] for result in response.json()["results"]}
    assert owner_video_id not in result_video_ids


def test_search_returns_empty_results_for_user_without_segments(client):
    response = client.post(
        "/api/v1/search",
        headers={"X-User-Id": "empty-search-user"},
        json={"query_text": "热血卡点"},
    )

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_response_includes_query_rewrite_expanded_queries_and_creative_suggestion(client):
    _upload_video(client, "rewrite-search-user")

    response = client.post(
        "/api/v1/search",
        headers={"X-User-Id": "rewrite-search-user"},
        json={"query_text": "帮我找适合做热血卡点的视频素材"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query_rewrite"]["original_query"] == "帮我找适合做热血卡点的视频素材"
    assert "high_energy" in body["expanded_queries"]
    assert body["creative_suggestion"]["recommended_bgm_style"]
    assert body["results"][0]["creative_suggestion"]["transition_suggestions"]
