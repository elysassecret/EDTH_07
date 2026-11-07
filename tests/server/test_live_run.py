"""The live console run: no end, no scripted exercise, AIS that does not run out (owner C)."""

from ais.replay import DAY_MS, AisReplay
from server.bridge import ROOT, SimSource


def test_a_live_run_has_no_end_and_plays_no_scripted_exercise():
    s = SimSource(1, launch=True, endless=True, scenario="scenarios/quiet.toml")
    assert s.scene_msg()["horizon_s"] == 0
    s.step(15_000_000)  # past the 14 400 s where a 4 h run stops
    assert s.t >= 15_000
    shore = s.snapshot("shore")
    assert not [e for e in shore["events"] if e.get("exercise")]
    assert shore["exercises"] == []


def test_the_scripted_tape_is_still_there_on_request():
    s = SimSource(1, scenario="scenarios/fixed.toml")
    assert s.horizon_ms == 14_400_000
    s.step(7_400_000)
    assert any(e.get("exercise") for e in s.snapshot("shore")["events"])


def test_the_ais_day_replays_after_it_ends():
    clip = AisReplay(ROOT / "data/ais-clip-box.csv")
    if not clip.available:
        return  # the clip is not in git; this laptop has none
    t = clip.times[-1] + 3_600_000  # an hour past the clip's last ping
    later = clip.between(t - 180_000, t)
    same = clip.between(t - DAY_MS - 180_000, t - DAY_MS)
    assert later and [p.track for p in later] == [p.track for p in same]
    assert all(a.t_ms == b.t_ms + DAY_MS for a, b in zip(later, same, strict=True))


def test_the_video_preset_keeps_its_scripted_tape_whatever_the_live_default():
    s = SimSource(1, demo={"start_s": 0}, scenario="scenarios/quiet.toml")
    assert s.scenario == "scenarios/fixed.toml"
