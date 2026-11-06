"""T1-T3: two leases, is_open with deputy grace, leases from t_created."""
from agent.table import Table
from contract.constants import CLAIMED, DEPUTY_GRACE, LEASE, RELEASED
from contract.tasks import Rec
from tests.agent.scene import line_mission

SEG_LEASE = 3_600_000


def table(me=1):
    return Table(me, SEG_LEASE, line_mission())


def test_initial_records():
    t = table()
    assert t.recs["seg:A:0"] == Rec("seg:A:0", 1, CLAIMED, 0, 1)
    assert t.recs["relay"] == Rec("relay", 1, CLAIMED, 0, 3)
    assert t.held_by(2) == ["seg:A:1"]


def test_relay_and_seg_leases_differ():  # T1
    t = table()
    t.heard(3, 10_000)
    t.heard(2, 10_000)
    assert t.lease_ok(3, "relay", 10_000 + LEASE)
    assert not t.lease_ok(3, "relay", 10_000 + LEASE + 1)
    assert t.lease_ok(2, "seg:A:1", 10_000 + LEASE + 1)
    assert not t.lease_ok(2, "seg:A:1", 10_000 + SEG_LEASE + 1)
    assert t.lease_ok(1, "seg:A:0", 10**9)  # my own lease never expires for me


def test_is_open_with_deputy_grace():  # T2
    t = table()
    t.heard(3, 0)
    assert not t.is_open("relay", LEASE)
    assert t.is_open("relay", LEASE + 1)
    t.apply(Rec("relay", 2, CLAIMED, 50, 3, deputy=2))
    assert not t.is_open("relay", LEASE + DEPUTY_GRACE - 1)
    assert t.is_open("relay", LEASE + DEPUTY_GRACE)
    t.apply(Rec("relay", 3, RELEASED, 0, 3))
    assert t.is_open("relay", 0)


def test_lease_uses_t_created_not_arrival():  # T3
    t = table()
    t.heard(3, 1_000)  # a forwarded heartbeat created at 1 s, arriving much later
    t.heard(3, 500)  # an older one arriving after it changes nothing
    assert t.last_hb[3] == 1_000
    assert t.lease_ok(3, "relay", 1_000 + LEASE) and not t.lease_ok(3, "relay", 1_001 + LEASE)


def test_apply_reports_lost_task():
    t = table(me=1)
    changed, lost = t.apply(Rec("seg:A:0", 2, CLAIMED, 10, 2))
    assert changed and lost
    changed, lost = t.apply(Rec("seg:A:0", 1, CLAIMED, 0, 1))  # older: ignored
    assert not changed and not lost
