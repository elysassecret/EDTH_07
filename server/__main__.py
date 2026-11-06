"""One command starts the demo (N3). Owner: C.

    uv run python -m server --serve-web    # real sim + console on http://localhost:8765/
    uv run python -m server --mock         # mock feed instead of the real sim
"""

import argparse
import asyncio
import logging


def main() -> None:
    ap = argparse.ArgumentParser(description="Console server: real sim bridge or mock feed (C).")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--mock", action="store_true", help="use server/mock_feed.py, not the sim")
    ap.add_argument("--serve-web", action="store_true", help="also serve web/dist over HTTP")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if args.mock:
        from server.mock_feed import serve
    else:
        from server.bridge import serve
    try:
        asyncio.run(serve(args.host, args.port, args.seed, args.hz, serve_web=args.serve_web))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
