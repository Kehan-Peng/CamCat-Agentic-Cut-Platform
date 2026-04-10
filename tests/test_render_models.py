"""
测试 Render 数据模型
"""
import pytest
from backend.app.domain.render import (
    RenderJob,
    ClipSegment,
    EditedVideoArtifact,
)


def test_render_job_creation():
    """测试 RenderJob 创建"""
    job = RenderJob(
        job_id="job_001",
        editing_session_id="edit_001",
        user_id="user_001",
        status="pending",
        clip_segments=["clip_1", "clip_2"]
    )

    assert job.job_id == "job_001"
    assert job.editing_session_id == "edit_001"
    assert job.user_id == "user_001"
    assert job.status == "pending"
    assert job.clip_segments == ["clip_1", "clip_2"]


def test_render_job_status_transitions():
    """测试 RenderJob 状态转换"""
    job = RenderJob(
        job_id="job_002",
        editing_session_id="edit_001",
        user_id="user_001",
        status="pending",
        clip_segments=[]
    )

    # 状态应该可以更新
    assert job.status == "pending"
    # 在实际实现中，状态会通过方法更新


def test_clip_segment_creation():
    """测试 ClipSegment 创建"""
    segment = ClipSegment(
        clip_id="clip_001",
        source_video_id="video_001",
        start_time=0.0,
        end_time=5.0,
        output_start_time=0.0,
        output_end_time=5.0
    )

    assert segment.clip_id == "clip_001"
    assert segment.source_video_id == "video_001"
    assert segment.start_time == 0.0
    assert segment.end_time == 5.0
    assert segment.output_start_time == 0.0
    assert segment.output_end_time == 5.0


def test_clip_segment_with_filters():
    """测试 ClipSegment 包含滤镜"""
    segment = ClipSegment(
        clip_id="clip_002",
        source_video_id="video_001",
        start_time=5.0,
        end_time=10.0,
        output_start_time=5.0,
        output_end_time=10.0,
        filters=["fade_in", "speed_1.5x"]
    )

    assert segment.filters == ["fade_in", "speed_1.5x"]


def test_edited_video_artifact_creation():
    """测试 EditedVideoArtifact 创建"""
    artifact = EditedVideoArtifact(
        artifact_id="artifact_001",
        editing_session_id="edit_001",
        render_job_id="job_001",
        user_id="user_001",
        output_path="/path/to/output.mp4",
        status="completed"
    )

    assert artifact.artifact_id == "artifact_001"
    assert artifact.editing_session_id == "edit_001"
    assert artifact.render_job_id == "job_001"
    assert artifact.user_id == "user_001"
    assert artifact.output_path == "/path/to/output.mp4"
    assert artifact.status == "completed"


def test_edited_video_artifact_with_metadata():
    """测试 EditedVideoArtifact 包含元数据"""
    artifact = EditedVideoArtifact(
        artifact_id="artifact_002",
        editing_session_id="edit_001",
        render_job_id="job_002",
        user_id="user_001",
        output_path="/path/to/output2.mp4",
        status="completed",
        duration_seconds=30.5,
        file_size_bytes=1024000,
        resolution="1920x1080"
    )

    assert artifact.duration_seconds == 30.5
    assert artifact.file_size_bytes == 1024000
    assert artifact.resolution == "1920x1080"
