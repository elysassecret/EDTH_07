"""N1-N4: dedupe, expiry, hop limit, forwarding keeps times; retries; slot boundaries."""
from dataclasses import replace

from agent.net import Every, Net
from contract.constants import EXPIRY, MAX_HOPS, RETRY
from contract.messages import decode, encode, new


def test_dedupe_and_own_echo():
    n = Net(2)
    raw = encode(new(1, 1, 0, "HB", {}))
    assert n.receive(0, raw) is not None
    assert n.receive(500, raw) is None  # N1: second copy dropped
    own = n.send(0, "HB", {})
    assert n.receive(1_000, encode(own)) is None  # our own message coming back


def test_expired_dropped():
    m = new(1, 1, 0, "BID", {})
    assert Net(2).receive(m.te + 1, encode(m)) is None  # N2
    assert Net(2).receive(m.te, encode(m)) is not None


def test_hop_limit_and_forward_keeps_times():
    n = Net(2)
    m = replace(new(1, 1, 7_000, "REC", {"recs": []}), hops=MAX_HOPS - 1)
    n.receive(7_500, encode(m))
    (fwd,) = n.flush()
    f = decode(fwd)
    assert (f.id, f.tc, f.te, f.hops) == (m.id, m.tc, m.te, MAX_HOPS)  # N4
    n.receive(7_600, fwd.replace(b'"id":"1:1"', b'"id":"1:2"'))
    assert n.flush() == []  # N3: a message already at MAX_HOPS is not forwarded


def test_garbage_ignored():
    assert Net(2).receive(0, b"not json") is None
    assert Net(2).receive(0, b'{"id":"1:1"}') is None


def test_retry_until_ack_or_expiry():
    n = Net(0)
    m = n.send(0, "CMD", {"task": "contact:C-07", "dec": "close", "ans": "approve"}, retry=True)
    assert len(n.flush()) == 1
    n.tick(RETRY - 1)
    assert n.flush() == []
    n.tick(RETRY)
    assert n.flush() == [encode(m)]  # same id, so boats that have it drop it
    n.ack(m.id)
    n.tick(2 * RETRY)
    assert n.flush() == []
    m2 = n.send(0, "VETO", {}, retry=True)
    n.flush()
    for t in range(RETRY, EXPIRY["VETO"] + 3 * RETRY, RETRY):
        n.tick(t)
    resent = n.flush()
    assert len(resent) == EXPIRY["VETO"] // RETRY  # every 5 s up to te, then given up
    assert m2.id not in n.pending


def test_every_fires_on_boundaries_with_offset():
    e = Every(5_000, 1_000)
    fired = [t for t in range(0, 20_001, 1_000) if e(t)]
    assert fired == [0, 4_000, 9_000, 14_000, 19_000]
