"""
测试 FFmpegCommandBuilder
"""
import pytest
from backend.app.services.ffmpeg_command_builder import FFmpegCommandBuilder
from backend.app.domain.render import ClipSegment


def test_ffmpeg_command_builder_uses_argument_list():
    """测试 FFmpegCommandBuilder 使用参数列表（不是 shell 字符串）"""
    builder = FFmpegCommandBuilder()

    clip = ClipSegment(
        clip_id="clip_001",
        source_video_id="video_001",
        start_time=0.0,
        end_time=5.0,
        output_start_time=0.0,
        output_end_time=5.0
    )

    command = builder.build_clip_command(
        input_path="/safe/input/video.mp4",
        output_path="/safe/output/clip.mp4",
        clip=clip
    )

    # 验证返回的是列表，不是字符串
    assert isinstance(command, list)
    assert len(command) > 0
    assert command[0] == "ffmpeg"


def test_ffmpeg_command_builder_validates_paths():
    """测试 FFmpegCommandBuilder 验证路径"""
    builder = FFmpegCommandBuilder()

    clip = ClipSegment(
        clip_id="clip_001",
        source_video_id="video_001",
        start_time=0.0,
        end_time=5.0,
        output_start_time=0.0,
        output_end_time=5.0
    )

    # 不安全的路径应该被拒绝
    with pytest.raises(ValueError, match="不安全的路径"):
        builder.build_clip_command(
            input_path="../../../etc/passwd",
            output_path="/safe/output/clip.mp4",
            clip=clip
        )


def test_ffmpeg_command_builder_basic_clip():
    """测试 FFmpegCommandBuilder 基本剪辑命令"""
    builder = FFmpegCommandBuilder()

    clip = ClipSegment(
        clip_id="clip_001",
        source_video_id="video_001",
        start_time=10.0,
        end_time=20.0,
        output_start_time=0.0,
        output_end_time=10.0
    )

    command = builder.build_clip_command(
        input_path="/safe/input/video.mp4",
        output_path="/safe/output/clip.mp4",
        clip=clip
    )

    # 验证命令包含必要的参数
    assert "ffmpeg" in command
    assert "-i" in command
    assert "/safe/input/video.mp4" in command
    assert "/safe/output/clip.mp4" in command
    # 验证时间参数
    assert "-ss" in command or "-t" in command


def test_ffmpeg_command_builder_with_filters():
    """测试 FFmpegCommandBuilder 包含滤镜"""
    builder = FFmpegCommandBuilder()

    clip = ClipSegment(
        clip_id="clip_002",
        source_video_id="video_001",
        start_time=0.0,
        end_time=5.0,
        output_start_time=0.0,
        output_end_time=5.0,
        filters=["fade_in"]
    )

    command = builder.build_clip_command(
        input_path="/safe/input/video.mp4",
        output_path="/safe/output/clip.mp4",
        clip=clip
    )

    # 验证滤镜参数
    assert isinstance(command, list)
    # 滤镜应该在命令中（具体格式取决于实现）


def test_ffmpeg_command_builder_rejects_unsafe_filters():
    """测试 FFmpegCommandBuilder 拒绝不安全的滤镜"""
    builder = FFmpegCommandBuilder()

    clip = ClipSegment(
        clip_id="clip_003",
        source_video_id="video_001",
        start_time=0.0,
        end_time=5.0,
        output_start_time=0.0,
        output_end_time=5.0,
        filters=["unsafe_filter; rm -rf /"]
    )

    # 不安全的滤镜应该被拒绝
    with pytest.raises(ValueError, match="不安全的滤镜"):
        builder.build_clip_command(
            input_path="/safe/input/video.mp4",
            output_path="/safe/output/clip.mp4",
            clip=clip
        )
