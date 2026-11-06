"""Must always pass on main. Owner: D."""
import importlib


def test_packages_import():
    for p in ("contract", "agent", "world", "ais", "server", "eval"):
        importlib.import_module(p)


def test_merge_is_deterministic():
    from contract.tasks import Rec, merge
    a = Rec("seg:G:0", 2, 1, 100, 1)
    b = Rec("seg:G:0", 2, 1, 90, 3)
    assert merge(a, b) == merge(b, a) == b   # lower bid wins at equal version


def test_agent_never_imports_world():
    import pathlib
    for f in pathlib.Path("agent").glob("*.py"):
        text = f.read_text()
        assert "import world" not in text and "from world" not in text
        assert "import eval" not in text and "from eval" not in text
