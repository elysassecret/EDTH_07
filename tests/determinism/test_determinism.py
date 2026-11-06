"""D1 to D6: determinism and isolation."""
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from contract.config import ROOT
from contract.tasks import Rec, key, merge
from tests.helpers import make_sim


def _hash_in_subprocess(hashseed: str, until_s: int = 300) -> str:
    code = ("from tests.helpers import make_sim\n"
            "s,_=make_sim('elysa',1); s.run_warm(); s.run_until(%d); print(s.state_hash())" % until_s)
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    out = subprocess.check_output([sys.executable, "-c", code], cwd=ROOT, env=env, text=True)
    return out.strip().splitlines()[-1]


def test_d1_same_seed_two_processes_different_hashseed():
    assert _hash_in_subprocess("1") == _hash_in_subprocess("4242")


def test_d2_reset_equals_fresh_run():
    a, _ = make_sim("elysa", 2)
    a.run_warm()
    a.run_until(400)
    b, _ = make_sim("elysa", 2)
    b.run_warm()
    b.run_until(400)
    assert a.state_hash() == b.state_hash()
    assert a.warm_hash == b.warm_hash


def test_d3_replay_matches_hashes(tmp_path):
    from server.replay import replay
    from contract.config import MODES, load
    from eval.metrics import Metrics
    from world.sim import Sim
    cfg = load(overrides=MODES["elysa"])
    log = tmp_path / "run.jsonl"
    sim = Sim(cfg, "elysa", 3, use_ais=True, log_path=log)
    sim.observers.append(Metrics(sim))
    sim.run_warm()
    sim.run_until(100)
    sim.inject({"kind": "boat_fail", "boat": 3})
    sim.run_until(400)
    sim.inject({"kind": "cmd", "action": "stop", "cid": "contact:none"})
    sim.run_until(660)
    sim.log.close()
    ok, msg = replay(log)
    assert ok, msg


def test_d4_grep_no_wall_clock_or_global_random_in_agent_and_world():
    bad = []
    for folder in ("agent", "world", "contract", "eval"):
        for p in (ROOT / folder).glob("*.py"):
            src = p.read_text(encoding="utf-8")
            if re.search(r"\btime\.time\(", src) or re.search(r"\bimport random\b", src) or "from random import" in src:
                bad.append(p.name)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.For) and isinstance(node.iter, ast.Set):
                    bad.append(f"{p.name}: for over a set literal")
    assert not bad, bad


@settings(max_examples=300, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 5), st.integers(0, 2), st.integers(0, 10**6), st.integers(0, 5), st.integers(0, 5)),
                min_size=1, max_size=6))
def test_d5_merge_is_commutative_associative_idempotent(recs):
    rs = [Rec("seg:X:0", *r) for r in recs]
    for a in rs:
        assert merge(a, a) == a
        for b in rs:
            assert merge(a, b) == merge(b, a)
            for c in rs:
                assert merge(merge(a, b), c) == merge(a, merge(b, c))
    # any delivery order gives one final record
    import itertools
    finals = set()
    for perm in itertools.permutations(rs[:4]):
        cur = perm[0]
        for r in perm[1:]:
            cur = merge(cur, r)
        finals.add(cur)
    assert len(finals) == 1


def test_d6_agent_imports_only_contract():
    for p in (ROOT / "agent").glob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            for n in names:
                top = n.split(".")[0]
                assert top not in ("world", "eval", "server", "ais", "evidence", "numpy", "pandas"), f"{p.name} imports {n}"
