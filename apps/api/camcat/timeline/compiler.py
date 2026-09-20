from __future__ import annotations

from fractions import Fraction
from uuid import UUID

from camcat.domain.project import AudioTrack, EditingProjectV2, TextTrack, VideoTrack
from camcat.rendering.materialization import MaterializedMedia, MaterializedSources
from camcat.timeline.frames import frame_to_us, round_ratio, us_range_to_frames, us_to_frame
from camcat.timeline.schemas import (
    CompiledAudioSegment,
    CompiledAudioTrack,
    CompiledTextSegment,
    CompiledTextTrack,
    CompiledTimelineV2,
    CompiledTransitionEdge,
    CompiledVideoSegment,
    CompiledVideoTrack,
    RenderProfile,
)
from camcat.timeline.validator import (
    TimelineValidationError,
    compiled_content,
    content_hash,
    source_manifest_content,
    verify_compiled_timeline,
)


class TimelineCompilerV2:
    def __init__(self, profile: RenderProfile) -> None:
        self.profile = profile

    def compile(
        self,
        *,
        session_id: UUID,
        state_version: int,
        project: EditingProjectV2,
        sources: MaterializedSources,
    ) -> CompiledTimelineV2:
        if any(item.decision == "CHECK" for item in project.speech_review.items):
            raise TimelineValidationError("unresolved CHECK decisions block timeline compilation")
        fps_num, fps_den = project.canvas.fps_num, project.canvas.fps_den
        edges = self._compile_transitions(project, fps_num, fps_den)
        edge_by_left = {item.left_segment_id: item for item in edges}
        edge_by_right = {item.right_segment_id: item for item in edges}
        video_tracks: list[CompiledVideoTrack] = []
        text_tracks: list[CompiledTextTrack] = []
        audio_tracks: list[CompiledAudioTrack] = []
        used_sources: set[str] = set()
        for track in project.timeline.tracks:
            if isinstance(track, VideoTrack):
                segments: list[CompiledVideoSegment] = []
                for segment in track.segments:
                    materialized = self._source(sources, segment.source_id)
                    ref = materialized.ref
                    if not ref.video_codec:
                        raise TimelineValidationError(
                            f"video segment source has no video stream: {segment.source_id}"
                        )
                    visible_start, visible_frames = us_range_to_frames(
                        segment.timeline_start_us,
                        segment.timeline_duration_us,
                        fps_num,
                        fps_den,
                    )
                    incoming = edge_by_right.get(segment.segment_id)
                    outgoing = edge_by_left.get(segment.segment_id)
                    head_frames = incoming.duration_frames // 2 if incoming else 0
                    tail_frames = (
                        outgoing.duration_frames - outgoing.duration_frames // 2 if outgoing else 0
                    )
                    speed = Fraction(str(segment.speed))
                    head_us = round_ratio(
                        frame_to_us(head_frames, fps_num, fps_den) * speed.numerator,
                        speed.denominator,
                    )
                    tail_us = round_ratio(
                        frame_to_us(tail_frames, fps_num, fps_den) * speed.numerator,
                        speed.denominator,
                    )
                    render_start_us = segment.source_start_us - head_us
                    render_end_us = segment.source_start_us + segment.source_duration_us + tail_us
                    if render_start_us < 0 or render_end_us > ref.duration_us:
                        raise TimelineValidationError(
                            f"transition source handles are insufficient: {segment.segment_id}"
                        )
                    compiled = CompiledVideoSegment(
                        track_id=track.track_id,
                        segment_id=segment.segment_id,
                        source_id=segment.source_id,
                        source_sha256=ref.sha256,
                        visible_source_start_us=segment.source_start_us,
                        visible_source_duration_us=segment.source_duration_us,
                        render_source_start_us=render_start_us,
                        render_source_duration_us=render_end_us - render_start_us,
                        timeline_start_frame=visible_start,
                        timeline_duration_frames=visible_frames,
                        render_start_frame=visible_start - head_frames,
                        render_duration_frames=visible_frames + head_frames + tail_frames,
                        speed=segment.speed,
                        transform=segment.transform,
                        reason=segment.reason,
                        evidence=[item.model_dump(mode="json") for item in segment.evidence],
                    )
                    segments.append(compiled)
                    used_sources.add(segment.source_id)
                video_tracks.append(
                    CompiledVideoTrack(track_id=track.track_id, name=track.name, segments=segments)
                )
            elif isinstance(track, TextTrack):
                text_tracks.append(
                    CompiledTextTrack(
                        track_id=track.track_id,
                        name=track.name,
                        segments=[
                            CompiledTextSegment(
                                segment_id=item.segment_id,
                                start_frame=us_range_to_frames(
                                    item.start_us, item.duration_us, fps_num, fps_den
                                )[0],
                                duration_frames=us_range_to_frames(
                                    item.start_us, item.duration_us, fps_num, fps_den
                                )[1],
                                text=item.text,
                                style=item.style,
                            )
                            for item in track.segments
                        ],
                    )
                )
            elif isinstance(track, AudioTrack):
                compiled_audio: list[CompiledAudioSegment] = []
                for item in track.segments:
                    ref = self._source(sources, item.source_id).ref
                    if not ref.audio_codec:
                        raise TimelineValidationError(
                            f"audio segment source has no audio stream: {item.source_id}"
                        )
                    start_frame, duration_frames = us_range_to_frames(
                        item.timeline_start_us,
                        item.timeline_duration_us,
                        fps_num,
                        fps_den,
                    )
                    if item.source_start_us >= ref.duration_us or (
                        not item.loop
                        and item.source_start_us + item.source_duration_us > ref.duration_us
                    ):
                        raise TimelineValidationError(
                            f"audio source range exceeds source: {item.segment_id}"
                        )
                    compiled_audio.append(
                        CompiledAudioSegment(
                            segment_id=item.segment_id,
                            source_id=item.source_id,
                            source_sha256=ref.sha256,
                            source_start_us=item.source_start_us,
                            source_duration_us=item.source_duration_us,
                            timeline_start_frame=start_frame,
                            timeline_duration_frames=duration_frames,
                            volume=item.volume,
                            fade_in_frames=us_to_frame(item.fade_in_us, fps_num, fps_den),
                            fade_out_frames=us_to_frame(item.fade_out_us, fps_num, fps_den),
                            loop=item.loop,
                        )
                    )
                    used_sources.add(item.source_id)
                audio_tracks.append(
                    CompiledAudioTrack(
                        track_id=track.track_id,
                        name=track.name,
                        role=track.role,
                        segments=compiled_audio,
                    )
                )
        if not video_tracks or not video_tracks[0].segments:
            raise TimelineValidationError("editing project requires a primary video track")
        frame_count = max(
            item.timeline_start_frame + item.timeline_duration_frames
            for track in video_tracks
            for item in track.segments
        )
        for compiled_text_track in text_tracks:
            if any(
                item.start_frame + item.duration_frames > frame_count
                for item in compiled_text_track.segments
            ):
                raise TimelineValidationError("text segment exceeds the visible timeline")
        for compiled_audio_track in audio_tracks:
            if any(
                item.timeline_start_frame + item.timeline_duration_frames > frame_count
                for item in compiled_audio_track.segments
            ):
                raise TimelineValidationError("audio segment exceeds the visible timeline")
        manifest = sorted(
            (sources[item].ref for item in used_sources), key=lambda item: item.media_id
        )
        timeline = CompiledTimelineV2(
            session_id=session_id,
            state_version=state_version,
            canvas=project.canvas,
            frame_count=frame_count,
            duration_us=frame_to_us(frame_count, fps_num, fps_den),
            video_tracks=video_tracks,
            audio_tracks=audio_tracks,
            text_tracks=text_tracks,
            transitions=edges,
            source_manifest=manifest,
            source_manifest_hash=content_hash(source_manifest_content(manifest)),
            state_hash=content_hash(project),
            render_profile_hash=content_hash(self.profile),
            compiled_hash="0" * 64,
        )
        timeline = timeline.model_copy(
            update={"compiled_hash": content_hash(compiled_content(timeline))}
        )
        verify_compiled_timeline(timeline)
        return timeline

    @staticmethod
    def _source(sources: MaterializedSources, source_id: str) -> MaterializedMedia:
        try:
            return sources[source_id]
        except KeyError as exc:
            raise TimelineValidationError(f"materialized source is missing: {source_id}") from exc

    @staticmethod
    def _compile_transitions(
        project: EditingProjectV2, fps_num: int, fps_den: int
    ) -> list[CompiledTransitionEdge]:
        owner = {
            segment.segment_id: track.track_id
            for track in project.timeline.tracks
            if isinstance(track, VideoTrack)
            for segment in track.segments
        }
        result = []
        for edge in project.timeline.transitions:
            frames = us_to_frame(edge.duration_us, fps_num, fps_den)
            if frames < 2:
                raise TimelineValidationError("dissolve transition must span at least two frames")
            result.append(
                CompiledTransitionEdge(
                    transition_id=edge.transition_id,
                    track_id=owner[edge.left_segment_id],
                    left_segment_id=edge.left_segment_id,
                    right_segment_id=edge.right_segment_id,
                    type=edge.type,
                    duration_frames=frames,
                )
            )
        return result
