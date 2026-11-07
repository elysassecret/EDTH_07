"""Serve the built React/WebGL fleet viewer, without starting a second simulation.

This process serves local assets only. The browser reads the existing dashboard
server's /truth WebSocket. No physics, sensors or agent state are owned here.
"""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


class ViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path == "/":
            query = urlsplit(self.path).query
            self.path = "/viewer.html" + ("?" + query if query else "")
        super().do_GET()

    def log_message(self, fmt, *args):
        return


def serve_viewer(host="127.0.0.1", port=8766, root=ROOT):
    dist = Path(root) / "web/dist"
    if not (dist / "viewer.html").is_file():
        raise SystemExit("Build the browser viewer first: pnpm --dir web build")
    handler = partial(ViewerHandler, directory=str(dist))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Maritime 3D viewer: http://{host}:{port}/", flush=True)
    print(
        "Uses the existing dashboard simulation on :8765/truth; no second World instance.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    serve_viewer(args.host, args.port)


if __name__ == "__main__":
    main()
