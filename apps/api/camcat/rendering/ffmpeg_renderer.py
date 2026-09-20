from __future__ import annotations

import json
import subprocess
from pathlib import Path

from camcat.rendering.backend import RenderResult
from camcat.rendering.build import RenderBuild, verify_materialized_sources, verify_render_build
from camcat.rendering.materialization import MaterializedSources


class FFmpegRenderError(RuntimeError):
    pass


class FFmpegRenderer:
    VERSION = "camcat-ffmpeg-renderer/v2"

    def render(
        self, build: RenderBuild, sources: MaterializedSources, output: Path
    ) -> RenderResult:
        build = verify_render_build(build.root)
        verify_materialized_sources(build, sources)
        timeline, profile = build.timeline, build.profile
        fps_num, fps_den = timeline.canvas.fps_num, timeline.canvas.fps_den
        fps = f"{fps_num}/{fps_den}"
        args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
        inputs: dict[tuple[str, bool], int] = {}

        def add_input(source_id: str, *, loop: bool = False) -> int:
            key = (source_id, loop)
            if key in inputs:
                return inputs[key]
            if loop:
                args.extend(["-stream_loop", "-1"])
            index = len(inputs)
            args.extend(["-i", str(sources[source_id].local_path)])
            inputs[key] = index
            return index

        filters: list[str] = []
        primary = timeline.video_tracks[0]
        transitions = {item.right_segment_id: item for item in timeline.transitions}
        primary_labels: list[str] = []
        audio_labels: list[str] = []
        audio_layout = "mono" if profile.audio_channels == 1 else "stereo"
        for index, segment in enumerate(primary.segments):
            input_index = add_input(segment.source_id)
            start = segment.render_source_start_us / 1_000_000
            duration = segment.render_source_duration_us / 1_000_000
            transform = segment.transform
            chain = (
                f"[{input_index}:v:0]trim=start={start:.6f}:duration={duration:.6f},"
                f"setpts=(PTS-STARTPTS)/{segment.speed:.10g},"
                f"scale={timeline.canvas.width}:{timeline.canvas.height}:force_original_aspect_ratio=increase,"
                f"crop={timeline.canvas.width}:{timeline.canvas.height},"
                f"eq=contrast={profile.color_contrast:.10g}:saturation={profile.color_saturation:.10g}:gamma={profile.color_gamma:.10g},"
                f"setsar=1,fps={fps},format=rgba"
            )
            if transform.scale_x != 1 or transform.scale_y != 1:
                chain += f",scale=iw*{transform.scale_x:.10g}:ih*{transform.scale_y:.10g}"
            if transform.rotation:
                chain += f",rotate={transform.rotation:.10g}*PI/180:ow=rotw(iw):oh=roth(ih):c=none"
            if transform.opacity != 1:
                chain += f",colorchannelmixer=aa={transform.opacity:.10g}"
            transformed = any(
                (
                    transform.x,
                    transform.y,
                    transform.rotation,
                    transform.scale_x - 1,
                    transform.scale_y - 1,
                    transform.opacity - 1,
                )
            )
            if transformed:
                chain += f"[pve{index}]"
                filters.append(chain)
                render_seconds = segment.render_duration_frames * fps_den / fps_num
                filters.append(
                    f"color=c=black:s={timeline.canvas.width}x{timeline.canvas.height}:"
                    f"r={fps}:d={render_seconds:.9f},format=rgba[pvb{index}]"
                )
                x = f"(W-w)/2+{transform.x:.10g}*W"
                y = f"(H-h)/2+{transform.y:.10g}*H"
                filters.append(
                    f"[pvb{index}][pve{index}]overlay=x='{x}':y='{y}':shortest=1[pv{index}]"
                )
            else:
                chain += f"[pv{index}]"
                filters.append(chain)
            primary_labels.append(f"pv{index}")

            visible_start = segment.visible_source_start_us / 1_000_000
            visible_duration = segment.visible_source_duration_us / 1_000_000
            target_duration = segment.timeline_duration_frames * fps_den / fps_num
            if sources[segment.source_id].ref.audio_codec:
                filters.append(
                    f"[{input_index}:a:0]atrim=start={visible_start:.6f}:duration={visible_duration:.6f},"
                    f"asetpts=PTS-STARTPTS,{_atempo(segment.speed)},aresample={profile.audio_sample_rate},"
                    f"aformat=channel_layouts={audio_layout},apad,atrim=duration={target_duration:.6f}[pa{index}]"
                )
            else:
                filters.append(
                    f"anullsrc=channel_layout={audio_layout}:sample_rate={profile.audio_sample_rate},"
                    f"atrim=duration={target_duration:.6f}[pa{index}]"
                )
            audio_labels.append(f"pa{index}")

        current_video = primary_labels[0]
        for index in range(1, len(primary_labels)):
            edge = transitions.get(primary.segments[index].segment_id)
            if edge:
                duration = edge.duration_frames * fps_den / fps_num
                offset = primary.segments[index].render_start_frame * fps_den / fps_num
                filters.append(
                    f"[{current_video}][{primary_labels[index]}]xfade=transition=fade:duration={duration:.9f}:offset={offset:.9f}[px{index}]"
                )
            else:
                filters.append(
                    f"[{current_video}][{primary_labels[index]}]concat=n=2:v=1:a=0[px{index}]"
                )
            current_video = f"px{index}"
        filters.append(
            f"[{current_video}]trim=end_frame={timeline.frame_count},setpts=PTS-STARTPTS,format={profile.pixel_format}[vbase]"
        )
        current_video = "vbase"

        for track_index, track in enumerate(timeline.video_tracks[1:], start=1):
            if any(item.track_id == track.track_id for item in timeline.transitions):
                raise FFmpegRenderError(
                    "overlay-track transitions are not supported by this renderer"
                )
            for segment_index, segment in enumerate(track.segments):
                input_index = add_input(segment.source_id)
                start = segment.visible_source_start_us / 1_000_000
                duration = segment.visible_source_duration_us / 1_000_000
                transform = segment.transform
                label = f"ov{track_index}_{segment_index}"
                chain = (
                    f"[{input_index}:v:0]trim=start={start:.6f}:duration={duration:.6f},"
                    f"setpts=(PTS-STARTPTS)/{segment.speed:.10g},fps={fps},format=rgba,"
                    f"scale=iw*{transform.scale_x:.10g}:ih*{transform.scale_y:.10g}"
                )
                if transform.rotation:
                    chain += (
                        f",rotate={transform.rotation:.10g}*PI/180:ow=rotw(iw):oh=roth(ih):c=none"
                    )
                if transform.opacity != 1:
                    chain += f",colorchannelmixer=aa={transform.opacity:.10g}"
                delay = segment.timeline_start_frame * fps_den / fps_num
                chain += f",setpts=PTS+{delay:.9f}/TB[{label}]"
                filters.append(chain)
                out = f"vo{track_index}_{segment_index}"
                x = f"(W-w)/2+{transform.x:.10g}*W"
                y = f"(H-h)/2+{transform.y:.10g}*H"
                filters.append(
                    f"[{current_video}][{label}]overlay=x='{x}':y='{y}':eof_action=pass:shortest=0[{out}]"
                )
                current_video = out

        if timeline.text_tracks and profile.burn_subtitles:
            ass = _escape_filter_path(build.root / "captions.ass")
            filters.append(f"[{current_video}]ass='{ass}'[vtext]")
            current_video = "vtext"

        current_audio = audio_labels[0]
        for index in range(1, len(audio_labels)):
            filters.append(f"[{current_audio}][{audio_labels[index]}]concat=n=2:v=0:a=1[ad{index}]")
            current_audio = f"ad{index}"
        mix_labels = [f"[{current_audio}]"]
        cue_index = 0
        for audio_track in timeline.audio_tracks:
            for audio_segment in audio_track.segments:
                input_index = add_input(audio_segment.source_id, loop=audio_segment.loop)
                start = audio_segment.source_start_us / 1_000_000
                source_duration = audio_segment.source_duration_us / 1_000_000
                target_duration = audio_segment.timeline_duration_frames * fps_den / fps_num
                delay_ms = round(audio_segment.timeline_start_frame * 1000 * fps_den / fps_num)
                delays = "|".join(str(delay_ms) for _ in range(profile.audio_channels))
                trim = (
                    f"atrim=start={start:.6f}"
                    if audio_segment.loop
                    else f"atrim=start={start:.6f}:duration={source_duration:.6f}"
                )
                chain = (
                    f"[{input_index}:a:0]{trim},asetpts=PTS-STARTPTS,"
                    f"aresample={profile.audio_sample_rate},"
                    f"aformat=channel_layouts={audio_layout},volume={audio_segment.volume:.10g}"
                )
                if audio_segment.loop:
                    chain += f",atrim=duration={target_duration:.9f}"
                else:
                    chain += f",atrim=duration={target_duration:.9f}"
                if audio_segment.fade_in_frames:
                    fade = audio_segment.fade_in_frames * fps_den / fps_num
                    chain += f",afade=t=in:st=0:d={fade:.9f}"
                if audio_segment.fade_out_frames:
                    fade = audio_segment.fade_out_frames * fps_den / fps_num
                    chain += f",afade=t=out:st={max(0.0, target_duration - fade):.9f}:d={fade:.9f}"
                chain += f",adelay={delays}[cue{cue_index}]"
                filters.append(chain)
                mix_labels.append(f"[cue{cue_index}]")
                cue_index += 1
        if cue_index:
            filters.append(
                f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first:dropout_transition=0[amix]"
            )
            current_audio = "amix"
        if profile.normalize_loudness:
            filters.append(
                f"[{current_audio}]loudnorm=I={profile.loudness_target_lufs:.10g}:TP={profile.loudness_true_peak_db:.10g}:LRA={profile.loudness_range_lu:.10g}[aout]"
            )
            current_audio = "aout"

        output.parent.mkdir(parents=True, exist_ok=True)
        args += [
            "-filter_complex",
            ";".join(filters),
            "-map",
            f"[{current_video}]",
            "-map",
            f"[{current_audio}]",
            "-frames:v",
            str(timeline.frame_count),
            "-c:v",
            profile.video_codec,
            "-preset",
            profile.preset,
            "-crf",
            str(profile.crf),
            "-pix_fmt",
            profile.pixel_format,
            "-c:a",
            profile.audio_codec,
            "-ar",
            str(profile.audio_sample_rate),
            "-ac",
            str(profile.audio_channels),
            "-movflags",
            "+faststart",
            str(output),
        ]
        (output.parent / "renderer-command.json").write_text(
            json.dumps(args, ensure_ascii=False), encoding="utf-8"
        )
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            (output.parent / "renderer-stderr.log").write_text(
                result.stderr[-1_000_000:], encoding="utf-8"
            )
            raise FFmpegRenderError(f"FFmpeg render failed: {result.stderr[-4000:]}")
        return RenderResult(output=output, renderer=self.VERSION, command=args)


def _atempo(speed: float) -> str:
    factors: list[float] = []
    remaining = speed
    while remaining > 2:
        factors.append(2)
        remaining /= 2
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    factors.append(remaining)
    return ",".join(f"atempo={item:.10g}" for item in factors)


def _escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
