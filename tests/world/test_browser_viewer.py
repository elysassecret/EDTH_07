"""The browser viewer serves assets; it must not start a separate simulation."""

from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from world.gazebo import serve_stage1_viewer
from world.viewer import ViewerHandler, serve_viewer


def test_existing_serve_entry_delegates_without_constructing_a_world():
    with patch("world.viewer.serve_viewer") as serve:
        serve_stage1_viewer("127.0.0.1", 8766)
        serve.assert_called_once_with("127.0.0.1", 8766)


def test_missing_build_is_explicit(tmp_path):
    with pytest.raises(SystemExit, match="Build the browser viewer"):
        serve_viewer(root=tmp_path)


def test_http_root_serves_viewer_and_missing_geo_is_not_fake_html(tmp_path):
    (tmp_path / "viewer.html").write_text("<h1>WebGL viewer entry</h1>")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(ViewerHandler, directory=str(tmp_path)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/?feed=ws://127.0.0.1:18870/truth") as response:
            assert response.read() == b"<h1>WebGL viewer entry</h1>"
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/geo/missing.geojson")
        assert error.value.code == 404
        with pytest.raises(HTTPError):
            urlopen(base + "/state")  # no second one-boat physics state endpoint
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
