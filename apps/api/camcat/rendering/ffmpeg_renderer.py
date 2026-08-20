from __future__ import annotations

import subprocess
from pathlib import Path

from camcat.rendering.backend import RenderResult
from camcat.rendering.build import RenderBuild, verify_render_build


class FFmpegRenderError(RuntimeError):
    pass


class FFmpegRenderer:
    VERSION = "camcat-ffmpeg-renderer/v1"

    def render(self, build: RenderBuild, output: Path) -> RenderResult:
        build = verify_render_build(build.root)
        timeline, profile = build.timeline, build.profile
        segments = timeline.video_tracks[0].segments
        by_id = {item.media_id: item for item in timeline.source_manifest}
        args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
        input_indices: dict[str, int] = {}
        audio_layout = "mono" if profile.audio_channels == 1 else "stereo"

        def add_input(source_id: str, *, loop: bool = False) -> int:
            key = f"{source_id}:{loop}"
            if key in input_indices:
                return input_indices[key]
            if loop:
                args.extend(["-stream_loop", "-1"])
            index = len(input_indices)
            args.extend(["-i", by_id[source_id].local_path])
            input_indices[key] = index
            return index

        segment_inputs = [add_input(item.source_id) for item in segments]
        filters: list[str] = []
        for index, (segment, input_index) in enumerate(zip(segments, segment_inputs, strict=True)):
            start = segment.source_start_us / 1_000_000
            duration = segment.source_duration_us / 1_000_000
            filters.append(
                f"[{input_index}:v:0]trim=start={start:.6f}:duration={duration:.6f},"
                f"setpts=(PTS-STARTPTS)/{segment.speed:.10g},"
                f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=increase,"
                f"crop={profile.width}:{profile.height},"
                f"eq=contrast={profile.color_contrast:.10g}:"
                f"saturation={profile.color_saturation:.10g}:gamma={profile.color_gamma:.10g},"
                "setsar=1,"
                f"fps={profile.fps_num}/{profile.fps_den},format={profile.pixel_format}[v{index}]"
            )
            target_duration = segment.target_duration_frames * profile.fps_den / profile.fps_num
            if by_id[segment.source_id].audio_codec:
                filters.append(
                    f"[{input_index}:a:0]atrim=start={start:.6f}:duration={duration:.6f},"
                    f"asetpts=PTS-STARTPTS,{_atempo(segment.speed)},"
                    f"aresample={profile.audio_sample_rate},"
                    f"aformat=channel_layouts={audio_layout},"
                    f"apad,atrim=duration={target_duration:.6f}[a{index}]"
                )
            else:
                filters.append(
                    f"anullsrc=channel_layout={audio_layout}:"
                    f"sample_rate={profile.audio_sample_rate},"
                    f"atrim=duration={target_duration:.6f}[a{index}]"
                )

        current_video, current_audio = "v0", "a0"
        for index in range(1, len(segments)):
            transition = segments[index].transition_in
            if transition.type == "dissolve":
                duration = transition.duration_frames * profile.fps_den / profile.fps_num
                offset = segments[index].target_start_frame * profile.fps_den / profile.fps_num
                filters.append(
                    f"[{current_video}][v{index}]xfade=transition=fade:duration={duration:.6f}:"
                    f"offset={offset:.6f}[vx{index}]"
                )
                filters.append(
                    f"[{current_audio}][a{index}]acrossfade=d={duration:.6f}:c1=tri:c2=tri[ax{index}]"
                )
            else:
                filters.append(f"[{current_video}][v{index}]concat=n=2:v=1:a=0[vx{index}]")
                filters.append(f"[{current_audio}][a{index}]concat=n=2:v=0:a=1[ax{index}]")
            current_video, current_audio = f"vx{index}", f"ax{index}"

        if timeline.subtitles and profile.burn_subtitles:
            subtitle = _escape_filter_path(build.root / "subtitles.srt")
            filters.append(
                f"[{current_video}]subtitles='{subtitle}':force_style='Alignment=2,"
                f"MarginV={profile.subtitle_margin_v},"
                "Fontsize=18,Outline=2,Shadow=0'[vsub]"
            )
            current_video = "vsub"

        mix_labels = [f"[{current_audio}]"]
        cue_index = 0
        for track in timeline.audio_tracks:
            if track.kind == "dialogue":
                continue
            for cue in track.cues:
                input_index = add_input(cue.source_id, loop=cue.loop)
                duration = cue.target_duration_frames * profile.fps_den / profile.fps_num
                start = cue.source_start_us / 1_000_000
                delay_ms = round(cue.target_start_frame * 1000 * profile.fps_den / profile.fps_num)
                delays = "|".join(str(delay_ms) for _ in range(profile.audio_channels))
                chain = (
                    f"[{input_index}:a:0]atrim=start={start:.6f}:duration={duration:.6f},"
                    f"asetpts=PTS-STARTPTS,aresample={profile.audio_sample_rate},"
                    f"aformat=channel_layouts={audio_layout},volume={cue.volume:.10g}"
                )
                if cue.fade_in_frames:
                    fade = cue.fade_in_frames * profile.fps_den / profile.fps_num
                    chain += f",afade=t=in:st=0:d={fade:.6f}"
                if cue.fade_out_frames:
                    fade = cue.fade_out_frames * profile.fps_den / profile.fps_num
                    chain += f",afade=t=out:st={max(0.0, duration - fade):.6f}:d={fade:.6f}"
                chain += f",adelay={delays}[cue{cue_index}]"
                filters.append(chain)
                mix_labels.append(f"[cue{cue_index}]")
                cue_index += 1
        if cue_index:
            filters.append(
                f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first:"
                "dropout_transition=0[amixed]"
            )
            current_audio = "amixed"
        if profile.normalize_loudness:
            filters.append(
                f"[{current_audio}]loudnorm=I={profile.loudness_target_lufs:.10g}:"
                f"TP={profile.loudness_true_peak_db:.10g}:"
                f"LRA={profile.loudness_range_lu:.10g}[aout]"
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
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode != 0:
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
