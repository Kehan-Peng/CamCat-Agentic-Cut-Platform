from backend.app.domain.models import MediaSegment, SegmentEvidence


def build_reason(
    segment: MediaSegment,
    matched_fields: set[str],
) -> tuple[str, list[SegmentEvidence]]:
    reason_parts: list[str] = []
    evidence: list[SegmentEvidence] = []

    if "asr_transcript" in matched_fields and segment.asr_transcript:
        reason_parts.append("ASR台词命中")
        evidence.extend(_evidence_of_type(segment, "asr"))

    if "ocr_text" in matched_fields and segment.ocr_text:
        reason_parts.append("OCR屏幕文字命中")
        evidence.extend(_evidence_of_type(segment, "ocr"))

    if "frame_captions" in matched_fields and segment.frame_captions:
        reason_parts.append("视觉画面描述命中")
        evidence.extend(_evidence_of_type(segment, "frame_caption"))

    if "tags" in matched_fields and segment.tags:
        reason_parts.append("标签命中")

    if segment.motion_score >= 0.85:
        reason_parts.append("高运动分")

    if segment.highlight_score >= 0.85:
        reason_parts.append("高光分")

    if not reason_parts:
        reason_parts.append("素材与查询存在词面匹配")

    return "，".join(reason_parts), _dedupe_evidence(evidence)


def _evidence_of_type(
    segment: MediaSegment,
    evidence_type: str,
) -> list[SegmentEvidence]:
    return [
        item
        for item in segment.evidence
        if item.evidence_type == evidence_type and item.text
    ]


def _dedupe_evidence(evidence: list[SegmentEvidence]) -> list[SegmentEvidence]:
    seen: set[tuple[str, str]] = set()
    deduped: list[SegmentEvidence] = []
    for item in evidence:
        key = (item.evidence_type, item.text)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped
