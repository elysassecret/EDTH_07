"""Honesty rule (CLAUDE.md): the product never calls a contact "suspicious" or "hostile" and never
says "coverage restored". Checks every source that produces text an officer or a jury sees: the
console, the server, the evidence report and the boats' own messages. Owner: C."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANNED = re.compile(r"suspicious|hostile|coverage restored", re.IGNORECASE)
# a line that states the rule itself ("never say ...") is not a use of the word
RULE = re.compile(r"\bnever\b|\bnot\b|not\.toMatch|wording rule", re.IGNORECASE)
SOURCES = [
    *ROOT.glob("web/src/**/*.ts"), *ROOT.glob("web/src/**/*.tsx"),
    *ROOT.glob("server/*.py"), *ROOT.glob("evidence/*.py"), *ROOT.glob("agent/*.py"),
    *ROOT.glob("world/*.py"), *ROOT.glob("config/*.json"),
]


def test_no_banned_wording_in_anything_the_officer_or_a_report_shows():
    hits = []
    for path in sorted(SOURCES):
        if ".test." in path.name or "/template/" in str(path):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if BANNED.search(line) and not RULE.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:100]}")
    assert hits == [], "banned wording:\n" + "\n".join(hits)
