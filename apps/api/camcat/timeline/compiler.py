from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Literal
from uuid import UUID

from camcat.timeline.mapping import ProjectionPolicy, SourceTimeMapper
from camcat.timeline.schemas import (
    CompiledAudioCue,
    CompiledAudioTrack,
    CompiledSubtitle,
    CompiledTimeline,
    CompiledVideoSegment,
    CompiledVideoTrack,
    MediaFingerprint,
    ProtectedSourceRange,
    RenderProfile,
    TransitionSpec,
)
from camcat.timeline.validator import (
    TimelineValidationError,
    compiled_content,
    content_hash,
    source_manifest_content,
    verify_compiled_timeline,
)


class TimelineCompiler:
    def __init__(self, profile: RenderProfile) -> None:
        self.profile = profile

    def compile(
        self,
        *,
        session_id: UUID,
        state_version: int,
        document: dict[str, Any],
        sources: dict[str, MediaFingerprint],
    ) -> CompiledTimeline:
        if document.get("speech_edit", {}).get("check_decisions_pending"):
            raise TimelineValidationError("unresolved CHECK decisions block timeline compilation")
        raw_clips = document.get("clips", [])
        if not isinstance(raw_clips, list) or not raw_clips:
            raise TimelineValidationError("editing state has no clips")
        segments = self._compile_video(raw_clips, sources)
        frame_count = segments[-1].target_start_frame + segments[-1].target_duration_frames
        mapper = SourceTimeMapper.from_segments(
            segments, fps_num=self.profile.fps_num, fps_den=self.profile.fps_den
        )
        subtitles = self._compile_subtitles(document.get("subtitles", []), mapper, frame_count)
        audio_tracks = self._compile_audio(
            document.get("audio_plan", {}), sources, mapper, frame_count
        )
        dialogue_cues = [
            CompiledAudioCue(
                cue_id=f"dialogue-{item.clip_id}",
                kind="dialogue",
                source_id=item.source_id,
                source_sha256=item.source_sha256,
                source_start_us=item.source_start_us,
                target_start_frame=item.target_start_frame,
                target_duration_frames=item.target_duration_frames,
            )
            for item in segments
            if sources[item.source_id].audio_codec
        ]
        if dialogue_cues:
            audio_tracks.insert(
                0,
                CompiledAudioTrack(track_id="audio-dialogue", kind="dialogue", cues=dialogue_cues),
            )
        used_ids = {item.source_id for item in segments}
        used_ids.update(cue.source_id for track in audio_tracks for cue in track.cues)
        manifest = sorted((sources[item] for item in used_ids), key=lambda item: item.media_id)
        timeline = CompiledTimeline(
            session_id=session_id,
            state_version=state_version,
            fps_num=self.profile.fps_num,
            fps_den=self.profile.fps_den,
            width=self.profile.width,
            height=self.profile.height,
            frame_count=frame_count,
            duration_us=self._frames_to_us(frame_count),
            video_tracks=[CompiledVideoTrack(segments=segments)],
            audio_tracks=audio_tracks,
            subtitles=subtitles,
            source_manifest=manifest,
            source_manifest_hash=content_hash(source_manifest_content(manifest)),
            state_hash=content_hash(document),
            render_profile_hash=content_hash(self.profile),
            compiled_hash="0" * 64,
        )
        timeline = timeline.model_copy(
            update={"compiled_hash": content_hash(compiled_content(timeline))}
        )
        verify_compiled_timeline(timeline)
        return timeline

    def _compile_video(
        self,
        raw_clips: list[dict[str, Any]],
        sources: dict[str, MediaFingerprint],
    ) -> list[CompiledVideoSegment]:
        result: list[CompiledVideoSegment] = []
        cursor = 0
        pending_in = TransitionSpec()
        for index, raw in enumerate(raw_clips):
            source_id = self._source_id(raw)
            source = self._source(sources, source_id)
            if not source.video_codec:
                raise TimelineValidationError(f"video clip source has no video stream: {source_id}")
            speed = float(raw.get("speed", 1.0))
            if not 0.1 <= speed <= 8:
                raise TimelineValidationError("clip speed is outside 0.1..8")
            selected_start = self._seconds_to_us(raw.get("source_start", 0))
            selected_end = self._seconds_to_us(raw.get("source_end", 0))
            if (
                selected_start < 0
                or selected_end <= selected_start
                or selected_end > source.duration_us
            ):
                raise TimelineValidationError(
                    f"clip source range exceeds source: {raw.get('clip_id')}"
                )
            speed_ratio = Fraction(str(speed))
            frame_count = (
                (selected_end - selected_start)
                * self.profile.fps_num
                * speed_ratio.denominator
                // (1_000_000 * self.profile.fps_den * speed_ratio.numerator)
            )
            if frame_count < 1:
                raise TimelineValidationError("clip is shorter than one output frame")
            aligned_source_duration = _round_ratio(
                frame_count * 1_000_000 * self.profile.fps_den * speed_ratio.numerator,
                self.profile.fps_num * speed_ratio.denominator,
            )
            protected = [
                ProtectedSourceRange.model_validate(item)
                for item in raw.get("protected_ranges", [])
            ]
            selected_start = self._fit_protected_range(
                selected_start, selected_end, aligned_source_duration, protected
            )
            transition_out = self._transition(raw.get("transition"), index == len(raw_clips) - 1)
            segment = CompiledVideoSegment(
                clip_id=str(raw.get("clip_id") or f"clip-{index + 1}"),
                segment_id=str(
                    raw.get("segment_id") or raw.get("clip_id") or f"segment-{index + 1}"
                ),
                origin=str(raw.get("origin", "source")),
                source_id=source_id,
                source_sha256=source.sha256,
                source_start_us=selected_start,
                source_duration_us=aligned_source_duration,
                target_start_frame=cursor - pending_in.duration_frames,
                target_duration_frames=frame_count,
                speed=speed,
                transition_in=pending_in,
                transition_out=transition_out,
                protected_ranges=protected,
                reason=str(raw.get("reason", "")),
            )
            if pending_in.type == "dissolve":
                self._verify_transition_handles(result[-1], segment, sources, pending_in)
            result.append(segment)
            cursor = segment.target_start_frame + frame_count
            pending_in = transition_out
        return result

    def _compile_subtitles(
        self,
        raw_subtitles: Any,
        mapper: SourceTimeMapper,
        frame_count: int,
    ) -> list[CompiledSubtitle]:
        result: list[CompiledSubtitle] = []
        for index, raw in enumerate(raw_subtitles if isinstance(raw_subtitles, list) else []):
            text = str(raw.get("text", "")).strip()
            if not text or "\x00" in text:
                raise TimelineValidationError("subtitle text is empty or invalid")
            source_id = raw.get("source_id") or raw.get("timeline_source_id")
            if (
                not source_id
                or not raw.get("clip_id")
                or "source_start" not in raw
                or "source_end" not in raw
            ):
                raise TimelineValidationError(
                    "subtitle must be source-bound with clip_id, source_id, "
                    "source_start, and source_end"
                )
            policy = ProjectionPolicy(str(raw.get("projection_policy", "error")))
            start = mapper.project(
                str(source_id),
                self._seconds_to_us(raw.get("source_start")),
                policy,
                clip_id=str(raw.get("clip_id")) if raw.get("clip_id") else None,
            )
            end = mapper.project(
                str(source_id),
                self._seconds_to_us(raw.get("source_end")),
                policy,
                clip_id=str(raw.get("clip_id")) if raw.get("clip_id") else None,
            )
            start = max(0, start)
            end = min(frame_count, end)
            if end <= start:
                raise TimelineValidationError("subtitle bounds are invalid")
            result.append(
                CompiledSubtitle(
                    subtitle_id=str(raw.get("subtitle_id") or f"subtitle-{index + 1}"),
                    text=text,
                    target_start_frame=start,
                    target_end_frame=end,
                    style=deepcopy(raw.get("style", "default")),
                )
            )
        return sorted(result, key=lambda item: (item.target_start_frame, item.subtitle_id))

    def _compile_audio(
        self,
        raw_plan: Any,
        sources: dict[str, MediaFingerprint],
        mapper: SourceTimeMapper,
        frame_count: int,
    ) -> list[CompiledAudioTrack]:
        if not isinstance(raw_plan, dict):
            raise TimelineValidationError("audio plan must be an object")
        tracks: list[CompiledAudioTrack] = []
        audio_kinds: tuple[tuple[str, Literal["bgm", "ambient", "sfx"]], ...] = (
            ("bgm", "bgm"),
            ("ambient", "ambient"),
            ("sound_effects", "sfx"),
        )
        for state_key, kind in audio_kinds:
            cues: list[CompiledAudioCue] = []
            values = raw_plan.get(state_key, [])
            if not isinstance(values, list):
                raise TimelineValidationError(f"audio plan {state_key} must be a list")
            for index, raw in enumerate(values):
                source_id = str(
                    raw.get("media_id") or raw.get("source_id") or raw.get("storage_key") or ""
                )
                source = self._source(sources, source_id)
                if not source.audio_codec:
                    raise TimelineValidationError(
                        f"audio cue source has no audio stream: {source_id}"
                    )
                mapping_source = raw.get("timeline_source_id")
                if mapping_source is not None and "source_time" in raw:
                    policy = ProjectionPolicy(str(raw.get("projection_policy", "error")))
                    target_start = mapper.project(
                        str(mapping_source),
                        self._seconds_to_us(raw["source_time"]),
                        policy,
                        clip_id=(
                            str(raw["timeline_clip_id"]) if raw.get("timeline_clip_id") else None
                        ),
                    )
                else:
                    target_start = self._seconds_to_frame(
                        raw.get("target_start", raw.get("start", 0))
                    )
                requested_duration = raw.get("target_duration", raw.get("duration"))
                duration_frames = (
                    self._seconds_to_frame(requested_duration)
                    if requested_duration is not None
                    else frame_count - target_start
                )
                duration_frames = min(duration_frames, frame_count - target_start)
                if target_start < 0 or duration_frames <= 0:
                    raise TimelineValidationError("audio cue bounds are invalid")
                source_start_us = self._seconds_to_us(raw.get("source_start", 0))
                loop = bool(raw.get("loop", kind in {"bgm", "ambient"}))
                cue_duration_us = self._frames_to_us(duration_frames)
                if (
                    source_start_us < 0
                    or source_start_us >= source.duration_us
                    or (not loop and source_start_us + cue_duration_us > source.duration_us)
                ):
                    raise TimelineValidationError("audio cue source range is invalid")
                cues.append(
                    CompiledAudioCue(
                        cue_id=str(raw.get("cue_id") or f"{kind}-{index + 1}"),
                        kind=kind,
                        source_id=source_id,
                        source_sha256=source.sha256,
                        source_start_us=source_start_us,
                        target_start_frame=target_start,
                        target_duration_frames=duration_frames,
                        volume=float(raw.get("volume", 1.0)),
                        fade_in_frames=int(raw.get("fade_in_frames", 0)),
                        fade_out_frames=int(raw.get("fade_out_frames", 0)),
                        loop=loop,
                    )
                )
            if cues:
                tracks.append(CompiledAudioTrack(track_id=f"audio-{kind}", kind=kind, cues=cues))
        return tracks

    def _fit_protected_range(
        self,
        selected_start: int,
        selected_end: int,
        aligned_duration: int,
        protected: list[ProtectedSourceRange],
    ) -> int:
        for item in protected:
            if item.start_us < selected_start or item.end_us > selected_end:
                raise TimelineValidationError("protected range lies outside selected source range")
        if not protected:
            return selected_start
        first = min(item.start_us for item in protected)
        last = max(item.end_us for item in protected)
        lower = max(selected_start, last - aligned_duration)
        upper = min(first, selected_end - aligned_duration)
        if lower > upper:
            raise TimelineValidationError(
                "no frame-aligned cut preserves the protected source range"
            )
        return min(max(selected_start, lower), upper)

    def _transition(self, value: Any, is_last: bool) -> TransitionSpec:
        if is_last:
            if value not in (None, "", "cut"):
                raise TimelineValidationError("last clip cannot have an outgoing transition")
            return TransitionSpec()
        if value in (None, "", "cut"):
            return TransitionSpec()
        if value == "dissolve":
            duration_frames = _round_ratio(
                self.profile.default_dissolve_duration_ms * self.profile.fps_num,
                1000 * self.profile.fps_den,
            )
            return TransitionSpec(type="dissolve", duration_frames=max(1, duration_frames))
        raise TimelineValidationError(f"unsupported transition contract: {value}")

    def _verify_transition_handles(
        self,
        previous: CompiledVideoSegment,
        current: CompiledVideoSegment,
        sources: dict[str, MediaFingerprint],
        transition: TransitionSpec,
    ) -> None:
        if transition.duration_frames >= min(
            previous.target_duration_frames, current.target_duration_frames
        ):
            raise TimelineValidationError("transition duration exceeds adjacent clip duration")
        half_target_us = _round_ratio(
            transition.duration_frames * 1_000_000 * self.profile.fps_den,
            2 * self.profile.fps_num,
        )
        previous_speed = Fraction(str(previous.speed))
        current_speed = Fraction(str(current.speed))
        previous_handle = _round_ratio(
            half_target_us * previous_speed.numerator, previous_speed.denominator
        )
        current_handle = _round_ratio(
            half_target_us * current_speed.numerator, current_speed.denominator
        )
        previous_source = sources[previous.source_id]
        if (
            previous_source.duration_us - (previous.source_start_us + previous.source_duration_us)
            < previous_handle
            or current.source_start_us < current_handle
        ):
            raise TimelineValidationError(
                "dissolve transition requires source head and tail handles"
            )

    @staticmethod
    def _source_id(raw: dict[str, Any]) -> str:
        value = raw.get("media_id") or raw.get("source_id") or raw.get("source_video_id")
        if not value:
            value = raw.get("segment_id")
        return str(value or "")

    @staticmethod
    def _source(sources: dict[str, MediaFingerprint], source_id: str) -> MediaFingerprint:
        try:
            return sources[source_id]
        except KeyError as exc:
            raise TimelineValidationError(f"source fingerprint is missing: {source_id}") from exc

    @staticmethod
    def _seconds_to_us(value: Any) -> int:
        try:
            seconds = Decimal(str(value))
            if not seconds.is_finite():
                raise ValueError
            return int((seconds * 1_000_000).to_integral_value())
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise TimelineValidationError("time value must be a finite number") from exc

    def _seconds_to_frame(self, value: Any) -> int:
        microseconds = self._seconds_to_us(value)
        return _round_ratio(
            microseconds * self.profile.fps_num,
            1_000_000 * self.profile.fps_den,
        )

    def _frames_to_us(self, frames: int) -> int:
        return _round_ratio(
            frames * 1_000_000 * self.profile.fps_den,
            self.profile.fps_num,
        )


def _round_ratio(numerator: int, denominator: int) -> int:
    if numerator < 0 or denominator <= 0:
        raise TimelineValidationError("timeline ratio must be nonnegative")
    return (2 * numerator + denominator) // (2 * denominator)
