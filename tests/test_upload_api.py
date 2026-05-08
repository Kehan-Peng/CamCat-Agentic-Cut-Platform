def _upload_video(client, user_id="user-upload", filename="clip.mp4"):
    return client.post(
        "/api/v1/videos",
        headers={"X-User-Id": user_id},
        files={"file": (filename, b"small video bytes", "video/mp4")},
    )


def test_upload_video_creates_searchable_video_and_segments(client):
    response = _upload_video(client, user_id="user-upload-create", filename="match.mp4")

    assert response.status_code == 200
    body = response.json()
    assert body["video_id"]
    assert body["status"] == "searchable"
    assert body["filename"] == "match.mp4"
    assert body["segment_count"] > 0

    first_segment_id = f"{body['video_id']}-segment-1"
    segment_response = client.get(
        f"/api/v1/segments/{first_segment_id}",
        headers={"X-User-Id": "user-upload-create"},
    )

    assert segment_response.status_code == 200
    assert segment_response.json()["video_id"] == body["video_id"]


def test_get_video_returns_video_and_segment_count(client):
    upload_response = _upload_video(
        client,
        user_id="user-upload-detail",
        filename="detail.mp4",
    )
    video_id = upload_response.json()["video_id"]

    response = client.get(
        f"/api/v1/videos/{video_id}",
        headers={"X-User-Id": "user-upload-detail"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["video_id"] == video_id
    assert body["user_id"] == "user-upload-detail"
    assert body["filename"] == "detail.mp4"
    assert body["status"] == "searchable"
    assert body["segment_count"] == upload_response.json()["segment_count"]


def test_get_video_blocks_cross_user_access(client):
    upload_response = _upload_video(
        client,
        user_id="user-upload-owner",
        filename="private.mp4",
    )
    video_id = upload_response.json()["video_id"]

    response = client.get(
        f"/api/v1/videos/{video_id}",
        headers={"X-User-Id": "user-upload-intruder"},
    )

    assert response.status_code == 404
