"""--hours: a longer live console run (owner C)."""
import pytest

from server.bridge import SimSource


def test_hours_runs_past_the_default_four_hours():
    """--hours: the live run goes on past run.toml's 4 h, up to one full battery."""
    from server.feed import boat_model

    limit = boat_model()["endurance_s"]
    src = SimSource(1, horizon_s=limit)
    assert src.scene_msg()["horizon_s"] == limit
    src.step(15_000 * 1000)
    assert src.t == 15_000  # the default run would have stopped at 14 400 s
    src.step(limit * 1000)
    assert src.t == limit  # and it still stops at the end it was given


@pytest.mark.parametrize("bad", [0, -1, 10**6])
def test_hours_refuses_a_run_out_of_range(bad):
    with pytest.raises(ValueError, match="between 0 and 24 h"):
        SimSource(1, horizon_s=bad)
