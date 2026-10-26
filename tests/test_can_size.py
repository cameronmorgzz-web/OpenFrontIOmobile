"""Brief: 500 ml works by changing ONE parameter and reprinting a single part (mag_bridge, x2).
Every other part must be the same shape for both can sizes (walls may move, not change)."""

import json
import os
import subprocess
import sys

from tests.conftest import ROOT

SCRIPT = """
import json
from cad import build as B
out = {}
for n, p in B.solids_rest().items():
    bb = p.bounding_box()
    out[n] = [round(p.volume, 0), round(bb.size.X, 1), round(bb.size.Y, 1), round(bb.size.Z, 1)]
print(json.dumps(out))
"""


def _shapes(size):
    env = dict(os.environ, BEER_CAN_SIZE=size)
    r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900,
                       check=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_only_mag_bridge_changes():
    a, b = _shapes("330"), _shapes("500")
    changed = sorted(n for n in a if a[n] != b[n])
    assert changed == ["mag_bridge_back", "mag_bridge_top"], changed
