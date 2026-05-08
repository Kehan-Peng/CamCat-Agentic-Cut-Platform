import hashlib

from backend.app.domain.models import MediaSegment, SegmentEvidence, Video


def generate_mock_media_segments(video: Video) -> list[MediaSegment]:
    segment_count = _segment_count_for(video.video_id)
    duration_seconds = max(video.duration_seconds or 30.0, float(segment_count))
    segment_length = duration_seconds / segment_count
    high_energy_index = min(1, segment_count - 1)

    segments: list[MediaSegment] = []
    for index in range(segment_count):
        start_time = round(index * segment_length, 2)
        end_time = round((index + 1) * segment_length, 2)
        if end_time <= start_time:
            end_time = start_time + 1.0

        if index == high_energy_index:
            segment = _make_high_energy_segment(video, index, start_time, end_time)
        else:
            segment = _make_default_segment(video, index, start_time, end_time)
        segments.append(segment)

    return segments


def _segment_count_for(video_id: str) -> int:
    digest = hashlib.sha256(video_id.encode("utf-8")).digest()
    return 3 + (digest[0] % 3)


def _make_high_energy_segment(
    video: Video,
    index: int,
    start_time: float,
    end_time: float,
) -> MediaSegment:
    asr_transcript = "最后一波团战开启，反打成功，全场沸腾"
    ocr_text = "ACE / 胜利 / 高能时刻"
    frame_captions = ["快节奏战斗", "冲刺"]
    tags = ["gameplay", "high_energy", "hot_blooded", "highlight"]

    return MediaSegment(
        segment_id=_segment_id(video.video_id, index),
        video_id=video.video_id,
        user_id=video.user_id,
        start_time=start_time,
        end_time=end_time,
        asr_transcript=asr_transcript,
        ocr_text=ocr_text,
        frame_captions=frame_captions,
        tags=tags,
        motion_score=0.92,
        highlight_score=0.94,
        representative_frame_uri=f"mock://frames/{video.video_id}/{index + 1}.jpg",
        evidence=[
            SegmentEvidence(
                evidence_type="asr",
                text=asr_transcript,
                start_time=start_time,
                end_time=end_time,
                confidence=0.93,
            ),
            SegmentEvidence(
                evidence_type="ocr",
                text=ocr_text,
                start_time=start_time,
                end_time=end_time,
                confidence=0.91,
            ),
            SegmentEvidence(
                evidence_type="frame_caption",
                text="; ".join(frame_captions),
                frame_uri=f"mock://frames/{video.video_id}/{index + 1}.jpg",
                confidence=0.89,
            ),
        ],
        metadata={"mock_pipeline": "deterministic_v1", "template": "high_energy"},
    )


def _make_default_segment(
    video: Video,
    index: int,
    start_time: float,
    end_time: float,
) -> MediaSegment:
    templates = [
        {
            "asr_transcript": "开场镜头建立环境，队友准备进入下一阶段",
            "ocr_text": "准备 / 地图载入",
            "frame_captions": ["环境展示", "角色移动"],
            "tags": ["gameplay", "setup", "navigation"],
            "motion_score": 0.42,
            "highlight_score": 0.36,
        },
        {
            "asr_transcript": "中段持续推进，资源点争夺进入白热化",
            "ocr_text": "推进 / 资源争夺",
            "frame_captions": ["团队推进", "技能释放"],
            "tags": ["gameplay", "teamfight", "momentum"],
            "motion_score": 0.68,
            "highlight_score": 0.72,
        },
        {
            "asr_transcript": "镜头切到侧翼，队伍完成包夹",
            "ocr_text": "侧翼 / 包夹",
            "frame_captions": ["战术转移", "侧翼切入"],
            "tags": ["gameplay", "strategy", "flank"],
            "motion_score": 0.61,
            "highlight_score": 0.58,
        },
        {
            "asr_transcript": "结尾回放关键操作，节奏逐渐收束",
            "ocr_text": "回放 / 精彩操作",
            "frame_captions": ["关键操作", "镜头回放"],
            "tags": ["gameplay", "replay", "recap"],
            "motion_score": 0.48,
            "highlight_score": 0.66,
        },
    ]
    template = templates[index % len(templates)]
    frame_uri = f"mock://frames/{video.video_id}/{index + 1}.jpg"

    return MediaSegment(
        segment_id=_segment_id(video.video_id, index),
        video_id=video.video_id,
        user_id=video.user_id,
        start_time=start_time,
        end_time=end_time,
        asr_transcript=template["asr_transcript"],
        ocr_text=template["ocr_text"],
        frame_captions=template["frame_captions"],
        tags=template["tags"],
        motion_score=template["motion_score"],
        highlight_score=template["highlight_score"],
        representative_frame_uri=frame_uri,
        evidence=[
            SegmentEvidence(
                evidence_type="asr",
                text=template["asr_transcript"],
                start_time=start_time,
                end_time=end_time,
                confidence=0.82,
            ),
            SegmentEvidence(
                evidence_type="ocr",
                text=template["ocr_text"],
                start_time=start_time,
                end_time=end_time,
                confidence=0.78,
            ),
            SegmentEvidence(
                evidence_type="frame_caption",
                text="; ".join(template["frame_captions"]),
                frame_uri=frame_uri,
                confidence=0.8,
            ),
        ],
        metadata={"mock_pipeline": "deterministic_v1", "template": "default"},
    )


def _segment_id(video_id: str, index: int) -> str:
    return f"{video_id}-segment-{index + 1}"
