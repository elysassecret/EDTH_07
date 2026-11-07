"""One command starts the demo (N3). Owner: C.

    uv run python -m server --serve-web    # real sim + console on http://localhost:8765/
    uv run python -m server --mock         # mock feed instead of the real sim

The real sim writes a JSONL run log to runs/ (one file per reset); check it with
    uv run python -m server.replay runs/<file>.jsonl

Demo video preset (server/demo.toml, shot list in server/DEMO.md):
    uv run python -m server --serve-web --demo
"""

import argparse
import asyncio
import logging
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Console server: real sim bridge or mock feed (C).")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--mock", action="store_true", help="use server/mock_feed.py, not the sim")
    ap.add_argument("--serve-web", action="store_true", help="also serve web/dist over HTTP")
    ap.add_argument("--no-log", action="store_true", help="real sim: do not write runs/*.jsonl")
    ap.add_argument("--scorecard", type=Path, default=None, metavar="JSON",
                    help="real sim: eval scorecard for the evaluator view "
                         "(default runs/main/scorecard_console.json)")
    ap.add_argument("--tracks", type=int, default=6,
                    help="mock only: synthetic AIS tracks for the load test (G4), e.g. 240")
    ap.add_argument("--demo", nargs="?", const="server/demo.toml", default=None, metavar="TOML",
                    help="real sim with the video preset (default server/demo.toml)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    extra = {}
    if args.demo and args.mock:
        ap.error("--demo runs the real sim; leave out --mock")
    if args.tracks != 6 and not args.mock:
        ap.error("--tracks is for the mock feed: add --mock")
    if args.mock:
        from server.mock_feed import serve

        extra = {"tracks": args.tracks}
    else:
        from server.bridge import serve
        from server.feed import ROOT

        extra = {"runs_dir": None if args.no_log else ROOT / "runs", "scorecard": args.scorecard}
        if args.demo:
            import tomllib

            demo = tomllib.loads((ROOT / args.demo).read_text(encoding="utf-8"))
            extra["demo"] = demo
            args.seed = int(demo.get("seed", args.seed))
    try:
        asyncio.run(serve(args.host, args.port, args.seed, args.hz, serve_web=args.serve_web,
                          **extra))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
