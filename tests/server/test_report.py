"""Incident report and tamper demo (feature 28), over the console server's HTTP API. Owner: C."""

import asyncio
import json
import urllib.error
import urllib.request

from evidence.report import report, tamper_demo
from server.bridge import SimSource


def _run(tmp_path, until=7_600):
    s = SimSource(1, runs_dir=tmp_path)
    while s.t < 7_500:
        s.step(60_000)
    s.command({"cmd": "stop", "id": "contact:C-07"})
    while s.t < until:
        s.step(60_000)
    s.close()
    return s


def test_report_lists_the_window_and_the_chain_check(tmp_path):
    s = _run(tmp_path)
    md = report(s.log.path, tmp_path / "k.pem", 7_000, 7_600)
    assert "Chain check: **OK**" in md
    assert "battery_low boat=1" in md and "link_off a=4 b=shore" in md
    assert "Watch officer command: stop id=contact:C-07 (accepted)" in md
    assert "| USV 03 |" in md and "No claim on admissibility" in md
    assert "Watch officer command" not in report(s.log.path, tmp_path / "k.pem", 0, 7_000)


def test_tamper_demo_names_the_changed_record(tmp_path):
    s = _run(tmp_path, until=600)
    d = tamper_demo(s.log.path, tmp_path / "k.pem")
    assert d["ok"] and d["original"]["ok"] and not d["tampered"]["ok"]
    chain, _, seq = d["changed"].split(":")[0].partition(" record ")
    assert d["tampered"]["messages"] == [
        f"{chain}: record {seq} was changed after it was written (hash differs)"]


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, None, e.read()


def test_http_api_on_the_real_sim_and_not_on_the_mock(tmp_path):
    async def go():
        from server.bridge import serve as sim_serve
        from server.mock_feed import serve as mock_serve

        loop = asyncio.get_running_loop()
        ready, mready = loop.create_future(), loop.create_future()
        t1 = asyncio.create_task(sim_serve("127.0.0.1", 0, 1, hz=20, ready=ready, runs_dir=tmp_path))
        t2 = asyncio.create_task(mock_serve("127.0.0.1", 0, 1, hz=20, ready=mready))
        (_, port), (_, mport) = await asyncio.wait_for(ready, 10), await asyncio.wait_for(mready, 10)
        try:
            await asyncio.sleep(0.5)
            code, ctype, body = await asyncio.to_thread(_get, f"http://127.0.0.1:{port}/api/report.md")
            assert code == 200 and ctype.startswith("text/markdown")
            assert body.decode().startswith("# Incident report")
            code, _, body = await asyncio.to_thread(_get, f"http://127.0.0.1:{port}/api/tamper-demo")
            assert code == 200 and json.loads(body)["ok"] in (True, False)
            code, _, _ = await asyncio.to_thread(_get, f"http://127.0.0.1:{mport}/api/report.md")
            assert code == 404
        finally:
            t1.cancel()
            t2.cancel()

    asyncio.run(go())
