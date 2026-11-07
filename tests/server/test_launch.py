"""Console side of the shore launch and the battery swap (owner C)."""

from server.bridge import SimSource


def run_to(s: SimSource, t_s: float, dt_ms: int = 24_000) -> None:
    while s.t < t_s:
        s.step(dt_ms)


def test_the_console_shows_the_launch_and_the_swap_it_knows_from_the_dock():
    s = SimSource(1, launch=True)
    shore = s.snapshot("shore")
    assert shore["launch"] is True and shore["swaps"] == {}
    run_to(s, 300)
    texts = [e["text"] for e in s.snapshot("shore")["events"]]
    assert sum("switched on at Korsør: launching" in t for t in texts) == 4  # the first starts at 0
    boat = next(b["id"] for b in s.snapshot("shore")["boats"] if b["mode"] != "UNAVAILABLE")
    assert s.command({"cmd": "inject", "kind": "battery_low", "a": boat})["ok"]
    swap_seen = None
    while s.t < 6000 and swap_seen is None:
        s.step(24_000)
        swap_seen = s.snapshot("shore")["swaps"].get(str(boat))
    assert swap_seen is not None and swap_seen > s.t  # ready time is in the future
    run_to(s, swap_seen + 30)
    snap = s.snapshot("shore")
    assert str(boat) not in snap["swaps"]
    assert any("battery swapped at Korsør: full" in e["text"] for e in snap["events"])


def test_the_placed_start_is_still_there_and_the_video_preset_keeps_it():
    assert SimSource(1).snapshot("shore")["launch"] is False
    assert SimSource(1, demo={"start_s": 0}).launch is False
    assert SimSource(1, demo={"launch": True}).launch is True
