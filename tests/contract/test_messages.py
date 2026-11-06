"""C1: envelope round trip and byte-stable encoding."""
import pytest

from contract.constants import EXPIRY
from contract.messages import decode, encode, new


def test_round_trip():
    m = new(3, 17, 7_200_000, "BID", {"task": "seg:G:0", "e": 600, "cost": 42, "boat": 3})
    assert decode(encode(m)) == m
    assert m.id == "3:17" and m.hops == 0 and m.te == 7_200_000 + EXPIRY["BID"]


def test_encoding_ignores_payload_insertion_order():
    a = new(1, 1, 0, "HB", {"x": 1, "y": 2, "mode": "PATROL"})
    b = new(1, 1, 0, "HB", {"mode": "PATROL", "y": 2, "x": 1})
    assert encode(a) == encode(b)


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        new(1, 1, 0, "PING", {})
    with pytest.raises(ValueError):
        decode(b'{"id":"1:1","src":1,"tc":0,"te":1,"kind":"PING","hops":0,"p":{}}')
