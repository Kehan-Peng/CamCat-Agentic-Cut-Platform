from __future__ import annotations

import os
from pathlib import Path

import pytest
from camcat.config import Settings
from pydantic import ValidationError

try:
    Settings()
    provider_configuration_valid = True
except ValidationError:
    provider_configuration_valid = False
missing = [] if os.environ.get("CAMCAT_EXTERNAL_TEST_VIDEO") else ["CAMCAT_EXTERNAL_TEST_VIDEO"]
if not provider_configuration_valid:
    missing.append("valid provider configuration in .env/environment")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.external,
    pytest.mark.skipif(
        bool(missing), reason=f"missing real provider settings: {', '.join(missing)}"
    ),
]


def test_real_qwen_text_image_video_embedding_and_reranking(tmp_path: Path) -> None:
    from camcat.config import get_settings
    from camcat.media.ffmpeg import extract_thumbnail
    from camcat.services.providers import (
        QwenEmbeddingClient,
        QwenRerankerClient,
        QwenVisualAnalysisClient,
    )

    settings = get_settings()
    video = Path(os.environ["CAMCAT_EXTERNAL_TEST_VIDEO"])
    image = tmp_path / "query.jpg"
    extract_thumbnail(video, image, at=0.5)
    embedding = QwenEmbeddingClient(settings)
    embedding.healthcheck()
    text_vector = embedding.embed_text("海边日落的温暖镜头")
    image_vector = embedding.embed_image(image)
    video_vector = embedding.embed_video(video)
    assert len(text_vector) == len(image_vector) == len(video_vector) == 2048
    assert text_vector != image_vector != video_vector

    reranker = QwenRerankerClient(settings)
    reranker.healthcheck()
    scores = reranker.rerank(
        {"text": "海边日落"},
        [{"text": "夕阳下的海岸"}, {"text": "办公室里的键盘"}],
    )
    assert len(scores) == 2
    assert scores[0] > scores[1]
    mixed_scores = reranker.rerank(
        {"text": "海边日落", "image_base64": image_data_uri(image)},
        [{"text": "夕阳下的海岸"}, {"text": "办公室里的键盘"}],
    )
    assert len(mixed_scores) == 2

    semantics = QwenVisualAnalysisClient(settings).analyze_video(video)
    assert semantics.description
    assert semantics.scene
    assert 0 <= semantics.risk_score <= 1


def test_real_structured_llm_and_asr(tmp_path: Path) -> None:
    from camcat.config import get_settings
    from camcat.media.ffmpeg import extract_audio
    from camcat.services.providers import QwenAsrClient, QwenChatClient

    settings = get_settings()
    video = Path(os.environ["CAMCAT_EXTERNAL_TEST_VIDEO"])
    chat = QwenChatClient(settings)
    chat.healthcheck()
    intent = chat.json_completion(
        system="Return strict JSON with a non-empty summary field.",
        user="为一条旅行 vlog 生成简短剪辑目标。",
    )
    assert str(intent.get("summary", "")).strip()
    audio = tmp_path / "audio.mp3"
    extract_audio(video, audio)
    asr = QwenAsrClient(settings)
    asr.healthcheck()
    transcription = asr.transcribe(audio)
    assert "text" in transcription


def image_data_uri(path: Path) -> str:
    import base64

    return f"data:image/jpeg;base64,{base64.b64encode(path.read_bytes()).decode()}"


def test_real_agent_finishes_after_browser_disconnect() -> None:
    import json
    import time

    import httpx

    with httpx.Client(
        base_url=os.environ.get("CAMCAT_TEST_API_URL", "http://api:8000"), timeout=90
    ) as client:
        created = client.post("/api/v1/editing/sessions", json={"current_goal": "测试断线恢复"})
        created.raise_for_status()
        session = created.json()
        session_id = session["editing_session_id"]
        run_id = None
        try:
            with client.stream(
                "POST",
                f"/api/v1/editing/sessions/{session_id}/agent/stream",
                json={"base_version": session["state_version"], "instruction": "只把标题改为夏日"},
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        run_id = json.loads(line[5:])["graph_run_id"]
                        break
            assert run_id
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                response = client.get(f"/api/v1/graph-runs/{run_id}")
                response.raise_for_status()
                run = response.json()
                if run["status"] == "succeeded":
                    assert len(run["node_trace"]) == 3
                    updated = client.get(f"/api/v1/editing/sessions/{session_id}").json()
                    assert updated["state_version"] == session["state_version"] + 1
                    assert updated["state"]["title"]
                    return
                assert run["status"] not in ("failed", "dead_letter"), run.get("error")
                time.sleep(0.5)
            pytest.fail("Disconnected agent did not finish within 90 seconds")
        finally:
            client.delete(f"/api/v1/editing/sessions/{session_id}")
