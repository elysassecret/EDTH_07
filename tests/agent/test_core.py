"""Five agents and the shore on the scene-like mission: heartbeats and records flood across hops."""
from contract.constants import RELEASED, SHORE
from contract.mission import load_params
from contract.tasks import Rec, to_wire
from tests.agent.harness import Sim
from tests.agent.scene import START, scene_mission

PARAMS = load_params()


def sim(**kw):
    return Sim(scene_mission(), PARAMS, START, **kw)


def test_everyone_hears_everyone_and_the_shore():
    s = sim()
    s.run_until(20_000)
    for b, a in s.agents.items():
        others = [o for o in s.mission.boats if o != b]
        assert all(a.table.last_hb.get(o, 0) >= 10_000 for o in others), (b, a.table.last_hb)
        assert a.shore_t >= 10_000, b  # boats 2 and 3 only reach the mast through the relay
    assert sorted(s.shore.boats) == [1, 2, 3, 4, 5]
    assert s.shore.boats[2][1] > 0  # boat 2 is heard through a peer, not directly


def test_a_record_reaches_every_node_across_hops():
    s = sim()
    s.run_until(10_000)
    rec = Rec("pick:N", 2, RELEASED, 0, 3)
    s.agents[3].publish(rec)
    s.run_until(20_000)
    for a in s.agents.values():
        assert a.table.recs["pick:N"] == rec
    assert s.shore.table.recs["pick:N"] == rec


def test_tables_converge_with_loss():
    s = sim(loss=0.05, seed=3)
    s.run_until(5_000)
    s.agents[2].publish(Rec("seg:H:1", 2, RELEASED, 0, 2))
    s.agents[4].publish(Rec("pick:S", 2, RELEASED, 0, 4))
    s.run_until(70_000)  # periodic re-advertise repairs anything lost
    tables = [[to_wire(r) for r in sorted(a.table.recs.values(), key=lambda r: r.task)]
              for a in s.agents.values()]
    assert all(tb == tables[0] for tb in tables)


def test_isolated_boat_hears_nobody():
    s = sim()
    s.isolate(4)
    s.run_until(30_000)
    a4 = s.agents[4]
    assert a4.table.last_hb == {} and a4.shore_t == -1
    assert 4 not in s.shore.boats and SHORE == 0
