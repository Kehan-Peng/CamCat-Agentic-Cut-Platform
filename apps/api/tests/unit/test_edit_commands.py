from __future__ import annotations

import pytest
from camcat.domain.edit_commands import (
    AddAudioCue,
    AddSubtitle,
    CommandConflict,
    InsertClip,
    MoveClip,
    RemoveAudioCue,
    RemoveClip,
    RemoveSubtitle,
    ReplaceAudioPlan,
    ReplaceClipMedia,
    ReplaceClipPlan,
    ReplaceSubtitles,
    SetOutputSettings,
    SetTransition,
    SplitClip,
    TrimClip,
    UpdateSubtitle,
    command_to_patch,
    commands_to_patch,
)
from camcat.domain.state_patch import VersionedState, apply_versioned_patch


def state() -> dict[str, object]:
    return {
        "clips": [
            {
                "clip_id": "a",
                "source_start": 0.0,
                "source_end": 4.0,
                "transition": "cut",
            },
            {
                "clip_id": "b",
                "source_start": 5.0,
                "source_end": 9.0,
                "transition": "cut",
            },
            {
                "clip_id": "c",
                "source_start": 10.0,
                "source_end": 14.0,
                "transition": "cut",
            },
        ],
        "subtitles": [],
        "audio_plan": {"bgm": [], "ambient": [], "sound_effects": []},
    }


def apply(command):
    operations = command_to_patch(state(), command)
    result, _ = apply_versioned_patch(
        VersionedState("session", 1, state()),
        base_version=1,
        operations=operations,
        actor="agent",
        reason="domain command",
    )
    return result.document["clips"]


def test_trim_clip_uses_stable_id_and_is_rebase_safe() -> None:
    command = TrimClip(clip_id="b", source_start=6.0, source_end=8.0)
    clips = apply(command)
    assert command.rebase_safe
    assert clips[1]["clip_id"] == "b"
    assert (clips[1]["source_start"], clips[1]["source_end"]) == (6.0, 8.0)


def test_move_and_remove_clip_use_ids_not_indexes() -> None:
    moved = apply(MoveClip(clip_id="c", before_clip_id="a"))
    assert [item["clip_id"] for item in moved] == ["c", "a", "b"]
    removed = apply(RemoveClip(clip_id="b"))
    assert [item["clip_id"] for item in removed] == ["a", "c"]


def test_split_clip_creates_two_stable_clips() -> None:
    clips = apply(SplitClip(clip_id="a", at_source=2.5, right_clip_id="a-right"))
    assert [item["clip_id"] for item in clips] == ["a", "a-right", "b", "c"]
    assert clips[0]["source_end"] == 2.5
    assert clips[1]["source_start"] == 2.5


def test_transition_command_stores_semantic_intent_only() -> None:
    clips = apply(SetTransition(clip_id="a", transition_type="dissolve"))
    assert clips[0]["transition"] == "dissolve"


def test_missing_stable_reference_is_a_command_conflict() -> None:
    with pytest.raises(CommandConflict, match="clip.*missing"):
        command_to_patch(state(), TrimClip(clip_id="missing", source_start=1, source_end=2))
    with pytest.raises(CommandConflict, match="before clip.*missing"):
        command_to_patch(state(), MoveClip(clip_id="a", before_clip_id="missing"))


def test_insert_and_replace_media_preserve_clip_identity() -> None:
    inserted = command_to_patch(
        state(),
        InsertClip(
            clip={
                "clip_id": "inserted",
                "segment_id": "new",
                "media_id": "media-new",
                "storage_key": "temporary/new.mp4",
                "origin": "source",
                "source_start": 0,
                "source_end": 1,
                "transition": "cut",
            },
            before_clip_id="b",
        ),
    )[0]["value"]
    assert [item["clip_id"] for item in inserted] == ["a", "inserted", "b", "c"]
    replaced = command_to_patch(
        state(),
        ReplaceClipMedia(
            clip_id="b",
            source_id="replacement",
            storage_key="library/replacement.mp4",
            segment_id="replacement-segment",
            origin="library",
            source_start=1,
            source_end=3,
        ),
    )[0]["value"]
    assert replaced[1]["clip_id"] == "b"
    assert replaced[1]["media_id"] == "replacement"


def test_subtitle_and_audio_commands_use_stable_ids() -> None:
    subtitle = {
        "subtitle_id": "subtitle-1",
        "text": "hello",
        "clip_id": "a",
        "source_id": "media-a",
        "source_start": 0,
        "source_end": 1,
        "style": "default",
    }
    added_subtitles = command_to_patch(state(), AddSubtitle(subtitle=subtitle))[0]["value"]
    with_subtitle = {**state(), "subtitles": added_subtitles}
    updated = command_to_patch(
        with_subtitle, UpdateSubtitle(subtitle_id="subtitle-1", text="updated")
    )[0]["value"]
    assert updated[0]["text"] == "updated"
    assert (
        command_to_patch(
            {**state(), "subtitles": updated}, RemoveSubtitle(subtitle_id="subtitle-1")
        )[0]["value"]
        == []
    )

    cue = {"cue_id": "cue-1", "media_id": "music", "storage_key": "audio/music.m4a"}
    audio_plan = command_to_patch(state(), AddAudioCue(kind="bgm", cue=cue))[0]["value"]
    assert audio_plan["bgm"][0]["cue_id"] == "cue-1"
    removed = command_to_patch(
        {**state(), "audio_plan": audio_plan}, RemoveAudioCue(cue_id="cue-1")
    )[0]["value"]
    assert removed["bgm"] == []


def test_agent_plan_commands_reduce_to_auditable_root_patches() -> None:
    replacement = [
        {
            "clip_id": "stable",
            "segment_id": "segment",
            "source_start": 1.0,
            "source_end": 2.0,
            "transition": "dissolve",
        }
    ]
    subtitles = [
        {
            "subtitle_id": "stable-subtitle",
            "text": "hello",
            "clip_id": "stable",
            "source_id": "source",
            "source_start": 1.0,
            "source_end": 2.0,
        }
    ]
    operations = commands_to_patch(
        state(),
        [
            ReplaceClipPlan(clips=replacement),
            ReplaceSubtitles(subtitles=subtitles),
            SetOutputSettings(aspect_ratio="9:16", external_material_ratio_limit=0.25),
            ReplaceAudioPlan(audio_plan={"bgm": [], "ambient": [], "sound_effects": []}),
        ],
    )

    assert [operation["path"] for operation in operations] == [
        "/clips",
        "/subtitles",
        "/settings",
        "/audio_plan",
    ]
    assert operations[0]["value"] == replacement
    assert operations[2]["op"] == "add"
