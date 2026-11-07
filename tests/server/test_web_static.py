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
