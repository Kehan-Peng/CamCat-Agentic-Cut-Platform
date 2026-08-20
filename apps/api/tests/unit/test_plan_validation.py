import pytest
from camcat.agent.planning import validate_plan


@pytest.mark.parametrize(
    "clips",
    [
        [],
        None,
        ["bad"],
        [{"segment_id": "invented"}],
        [{"segment_id": "real", "source_start": float("nan"), "source_end": 2}],
        [{"segment_id": "real", "source_start": 3, "source_end": 2}],
    ],
)
def test_invalid_plans_are_rejected(clips):
    with pytest.raises(ValueError):
        validate_plan({"clips": clips}, {"real": {"start_time": 0, "end_time": 4}})


def test_valid_plan_uses_actual_candidate_bounds():
    validate_plan(
        {"clips": [{"segment_id": "real", "source_start": 1, "source_end": 3}]},
        {"real": {"start_time": 0, "end_time": 4}},
    )


@pytest.mark.parametrize(
    "physical_field",
    [
        {"output_start": 0},
        {"output_end": 1},
        {"duration_frames": 9},
        {"transition": {"type": "dissolve", "duration_frames": 9}},
    ],
)
def test_plan_rejects_physical_timeline_coordinates(physical_field):
    clip = {"segment_id": "real", "source_start": 0, "source_end": 1, **physical_field}
    with pytest.raises(ValueError, match="physical|transition intent"):
        validate_plan({"clips": [clip]}, {"real": {"start_time": 0, "end_time": 2}})


def test_plan_rejects_outgoing_transition_on_final_clip():
    with pytest.raises(ValueError, match="final clip"):
        validate_plan(
            {
                "clips": [
                    {
                        "segment_id": "real",
                        "source_start": 0,
                        "source_end": 1,
                        "transition": "dissolve",
                    }
                ]
            },
            {"real": {"start_time": 0, "end_time": 2}},
        )
