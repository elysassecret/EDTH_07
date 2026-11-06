"""DT: same inputs give the same state, also under a different PYTHONHASHSEED."""
import os
import subprocess
import sys

from contract.mission import load_params
from tests.agent.harness import Sim
from tests.agent.scene import START, scene_mission

RUN = """
from contract.mission import load_params
from tests.agent.harness import Sim
from tests.agent.scene import START, scene_mission
s = Sim(scene_mission(), load_params(), START, loss=0.05, seed=7)
s.run_until(60_000)
print(s.digest())
"""


def digest():
    s = Sim(scene_mission(), load_params(), START, loss=0.05, seed=7)
    s.run_until(60_000)
    return s.digest()


def test_two_runs_identical():
    assert digest() == digest()


def test_hash_seed_does_not_matter():
    here = digest()
    for seed in ("1", "4242"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": os.getcwd()}
        out = subprocess.run([sys.executable, "-c", RUN], env=env, capture_output=True,
                             text=True, check=True).stdout.strip()
        assert out == here
