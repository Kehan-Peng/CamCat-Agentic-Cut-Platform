def _upload_video(client, user_id="user-segment", filename="clip.mp4"):
    return client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": (filename, b"small video bytes", "video/mp4")},
    )


def test_get_segment_returns_segment_detail(client):
    upload_response = _upload_video(
        client,
        user_id="user-segment-detail",
        filename="segment-detail.mp4",
    )
    video_id = upload_response.json()["video_id"]
    segment_id = f"{video_id}-segment-1"

    response = client.get(
        f"/api/v1/segments/{segment_id}",
        headers={"X-User-Id": "user-segment-detail"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["segment_id"] == segment_id
    assert body["video_id"] == video_id
    assert body["user_id"] == "user-segment-detail"
    assert body["start_time"] < body["end_time"]
    assert body["evidence"]


def test_get_segment_blocks_cross_user_access(client):
    upload_response = _upload_video(
        client,
        user_id="user-segment-owner",
        filename="segment-private.mp4",
    )
    video_id = upload_response.json()["video_id"]
    segment_id = f"{video_id}-segment-1"

    response = client.get(
        f"/api/v1/segments/{segment_id}",
        headers={"X-User-Id": "user-segment-intruder"},
    )

    assert response.status_code == 404
