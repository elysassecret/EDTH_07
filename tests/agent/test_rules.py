"""RL: agent/ stays deterministic and sees only its own inputs (D4, D6 for A's folder)."""
import re
from pathlib import Path

FORBIDDEN = re.compile(r"\btime\.time\b|\bimport random\b|\bfrom random\b|\bdatetime\b"
                       r"|\bhash\(|\bopen\(|\bos\.environ\b")
IMPORTS = re.compile(r"^\s*(from|import)\s+(world|eval|server|ais|triage)\b", re.MULTILINE)


def test_agent_code_rules():
    for f in sorted(Path("agent").glob("*.py")):
        text = f.read_text()
        bad = FORBIDDEN.search(text)
        assert bad is None, f"{f}: {bad.group()}"
        assert not IMPORTS.search(text), f"{f}: imports another owner's package"
