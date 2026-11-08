"""Evidence hash chain (BUILD_PLAN step 30): edit one line, the verifier names it. Owner: C."""

import json
import stat

import pytest

from evidence.build import build
from evidence.chain import Chain, check_chain
from evidence.keys import key_id, load_or_create, pub_hex
from evidence.verify import verify
from server.bridge import SimSource


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    d = tmp_path_factory.mktemp("run")
    s = SimSource(1, runs_dir=d)
    s.command({"cmd": "inject", "kind": "link_off", "a": 3, "b": "shore"})
    # since #141 a contact task opens only after enough qualifying own-camera looks: run until
    # the shore has C-07's task and its decisions, then answer one
    while s.t < 9_000 and not s.snapshot("shore")["decisions"]:
        s.step(24_000)
    s.command({"cmd": "stop", "id": "contact:C-07"})
    s.step(24_000)
    s.close()
    return build(s.log.path, d / "key.pem"), d


def lines(path):
    return path.read_text().splitlines()


def test_built_log_verifies(evidence):
    path, _ = evidence
    ok, msgs = verify(path)
    assert ok, msgs
    recs = [json.loads(ln) for ln in lines(path)[1:]]
    chains = {r["chain"] for r in recs if r["type"] == "record"}
    assert {"shore", "usv-01", "usv-03"} <= chains
    report = next(r for r in recs if r["type"] == "record" and r["chain"] == "usv-01")
    assert report["time_source"].startswith("sim clock")
    assert report["t_obs"] <= report["t_log"]
    assert report["zone"][0] in ("inside patrol box", "outside patrol box")
    kinds = {r["kind"] for r in recs if r["type"] == "record" and r["chain"] == "shore"}
    assert {"event", "command", "decision"} <= kinds


def test_editing_one_line_names_the_first_bad_record(evidence, tmp_path):
    path, _ = evidence
    ls = lines(path)
    i = next(i for i, ln in enumerate(ls) if '"chain": "usv-02"' in ln and '"seq": 5,' in ln)
    rec = json.loads(ls[i])
    rec["data"]["batt"] += 1
    ls[i] = json.dumps(rec, sort_keys=True)
    bad = tmp_path / "bad.jsonl"
    bad.write_text("\n".join(ls) + "\n")
    ok, msgs = verify(bad)
    assert not ok
    assert msgs == ["usv-02: record 5 was changed after it was written (hash differs)"]


def test_rewriting_a_record_with_its_hash_breaks_the_next_link(evidence, tmp_path):
    from evidence.chain import record_hash

    path, _ = evidence
    ls = lines(path)
    i = next(i for i, ln in enumerate(ls) if '"chain": "usv-02"' in ln and '"seq": 5,' in ln)
    rec = json.loads(ls[i])
    rec["data"]["batt"] += 1
    rec["hash"] = record_hash(rec)
    ls[i] = json.dumps(rec, sort_keys=True)
    bad = tmp_path / "bad.jsonl"
    bad.write_text("\n".join(ls) + "\n")
    assert verify(bad)[1] == ["usv-02: record 6 does not link to record 5 (prev hash differs)"]


def test_deleting_the_last_record_or_resigning_is_caught(tmp_path):
    key = load_or_create(tmp_path / "k.pem")
    other = load_or_create(tmp_path / "other.pem")
    c = Chain("usv-04")
    for i in range(3):
        c.append("report", i, i, "sim clock", "test", [], {"i": i})
    head = c.sign_head(key)
    pub = key.public_key()
    assert check_chain("usv-04", c.records, head, pub) is None
    assert "chain ends at record 1" in check_chain("usv-04", c.records[:2], head, pub)
    assert "signature" in check_chain("usv-04", c.records, c.sign_head(other), pub)


def test_expected_key_id(evidence):
    path, d = evidence
    kid = key_id(pub_hex(load_or_create(d / "key.pem")))
    assert verify(path, kid)[0]
    ok, msgs = verify(path, "0" * 16)
    assert not ok and "not the expected" in msgs[0]


def test_private_key_is_owner_only(tmp_path):
    p = tmp_path / "k.pem"
    load_or_create(p)
    assert stat.S_IMODE(p.stat().st_mode) == 0o600
    assert load_or_create(p).public_key() is not None  # loads the same file again
