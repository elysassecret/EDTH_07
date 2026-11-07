"""Static checks on the console sources (U8 projector rule). Owner: C."""

import re

from server.feed import ROOT

WEB = ROOT / "web" / "src"


def test_no_text_below_14px():
    """U8: legible on a projector at 1280x720. Icon glyphs inside SVG are not text."""
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    small = [m.group(0) for m in re.finditer(r"font-size:\s*(\d+)px", css) if int(m.group(1)) < 14]
    assert small == []
    for f in sorted((WEB / "map").glob("*.ts*")):
        sizes = [int(n) for n in re.findall(r"getSize: (\d+)", f.read_text(encoding="utf-8"))]
        text_layers = f.read_text(encoding="utf-8").count("TextLayer")
        if text_layers:
            assert all(s >= 14 for s in sizes), f


# N1 offline (gap G3). Hosts that may appear in the console's code or build, and why each one
# is never fetched. Anything else fails the test. Checked in the browser on 7 Nov 2026: every
# request of a full console session went to the console server itself.
NOT_FETCHED = {
    "www.w3.org": "XML/SVG namespace names, not requests",
    "react.dev": "link text inside React error messages",
    "maplibre.invalid": "dummy base for URL parsing inside MapLibre",
    "github.com": "licence comment and a warning message in MapLibre",
    "wiki.openstreetmap.org": "text of MapLibre's 'needs WebGL' error",
    "maplibre.org": "MapLibre's attribution link; the console turns attribution off",
    "deck.gl": "link text in a deck.gl warning",
    "en.wikipedia.org": "comments inside deck.gl shader code",
    "unpkg.com": "loaders.gl's default worker CDN; the console loads no data through loaders",
}
URL = re.compile(r"https?://([A-Za-z0-9.-]+)")


def _hosts(paths):
    found = {}
    for p in paths:
        for h in URL.findall(p.read_text(encoding="utf-8", errors="ignore")):
            found.setdefault(h, p.name)
    return found


def test_console_source_has_no_web_addresses():
    files = [p for p in WEB.rglob("*") if p.suffix in (".ts", ".tsx", ".css", ".html")]
    files += [ROOT / "web" / "index.html"]
    assert set(_hosts(files)) <= {"www.w3.org"}


def test_built_console_has_no_unexpected_web_addresses():
    import pytest

    dist = ROOT / "web" / "dist"
    if not (dist / "index.html").is_file():
        pytest.skip("web/dist not built: run pnpm --dir web build")
    files = [p for p in dist.rglob("*") if p.suffix in (".js", ".css", ".html", ".json", ".geojson")]
    unexpected = {h: f for h, f in _hosts(files).items() if h not in NOT_FETCHED}
    assert unexpected == {}
