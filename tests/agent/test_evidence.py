"""#37: each boat chains what it claimed, released, flagged and was told, and signs the head."""
from agent.core import demo_key
from contract.mission import load_params
from evidence.chain import GENESIS, check_chain
from tests.agent.harness import Sim
from tests.agent.scene import START, scene_mission


def test_boat_chains_verify_and_the_shore_holds_their_heads():
    s = Sim(scene_mission(), load_params(), START)
    s.run_until(600_000)
    s.set_batt(1, 200)  # 01 goes home and releases, others claim: records on several chains
    s.run_until(900_000)
    for b, a in sorted(s.agents.items()):
        seq, h, sig = a.head()
        head = {"chain": a.chain.name, "seq": seq, "hash": h, "sig": sig}
        assert check_chain(a.chain.name, a.chain.records, head, demo_key(b).public_key()) is None
    assert any(r["kind"] == "return" for r in s.agents[1].chain.records)
    for b, head in s.shore.witnessed.items():
        assert head[0] <= s.agents[b].head()[0]  # the shore holds a head the boat really signed
        recs = s.agents[b].chain.records
        assert head[1] == (recs[head[0]]["hash"] if head[0] >= 0 else GENESIS)


def test_an_altered_record_no_longer_matches_the_witnessed_head():
    s = Sim(scene_mission(), load_params(), START)
    s.run_until(600_000)
    s.set_batt(1, 200)
    s.run_until(700_000)
    a = s.agents[1]
    seq, h, sig = s.shore.witnessed[1]
    a.chain.records[0]["data"] = {"rec": "rewritten"}
    head = {"chain": a.chain.name, "seq": seq, "hash": h, "sig": sig}
    problem = check_chain(a.chain.name, a.chain.records[:seq + 1], head, demo_key(1).public_key())
    assert problem and "changed after it was written" in problem
