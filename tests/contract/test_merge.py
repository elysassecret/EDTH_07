"""D5: merge is commutative, associative, idempotent; any delivery order gives one record."""
from functools import reduce

from hypothesis import given
from hypothesis import strategies as st

from contract.constants import CLAIMED, VETOED
from contract.tasks import Rec, from_wire, kind, merge, to_wire

# Small ranges on purpose, so ties on every field are common.
recs = st.builds(
    Rec,
    task=st.just("contact:C-07"),
    ver=st.integers(0, 3),
    state=st.integers(0, 2),
    bid=st.integers(0, 3),
    owner=st.integers(0, 3),
    deputy=st.integers(0, 3),
)


@given(recs, recs)
def test_commutative(a, b):
    assert merge(a, b) == merge(b, a)


@given(recs, recs, recs)
def test_associative(a, b, c):
    assert merge(merge(a, b), c) == merge(a, merge(b, c))


@given(recs)
def test_idempotent(a):
    assert merge(a, a) == a


@given(st.lists(recs, min_size=1, max_size=6), st.randoms(use_true_random=False))
def test_any_delivery_order_gives_one_record(rs, rnd):
    shuffled = list(rs)
    rnd.shuffle(shuffled)
    assert reduce(merge, rs) == reduce(merge, shuffled)


@given(recs, st.integers(0, 3))
def test_veto_is_absorbing(a, ver):
    stop = Rec(a.task, ver, VETOED, 0, 0, 0)
    if a.state != VETOED:
        assert merge(a, stop) == stop


def test_lower_bid_wins_at_equal_version():
    a = Rec("seg:G:0", 2, CLAIMED, 100, 1)
    b = Rec("seg:G:0", 2, CLAIMED, 90, 3)
    assert merge(a, b) == b


def test_wire_round_trip_and_kind():
    r = Rec("seg:H:1", 4, CLAIMED, 1234, 2, 5)
    assert from_wire(to_wire(r)) == r
    assert kind("seg:H:1") == "seg" and kind("relay") == "relay"
    assert kind("contact:C-07") == "contact"
