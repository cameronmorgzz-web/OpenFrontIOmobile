"""Phase 3 validation: MuJoCo launch model vs the Phase 2 hand calc at the same inputs
(4 m setting, calc preload, nominal 138 deg release, nominal friction). Any difference over 15 %
must carry an explanation (brief); explanations are written here, next to the numbers.

    python -m sim.validate        -> sim/validation.json
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

from calc import design as D
from calc import motor as M
from sim.launch import run
from sim.model import MM, Variation

OUT = Path(__file__).resolve().parent / "validation.json"
LIMIT = 15.0

EXPLAIN = {
    "launch angle": "The can rolls out over the cup floor lip in the last ~10 deg of the swing and leaves "
                    "below the arm-normal direction (calc assumes it leaves perpendicular to the arm). "
                    "Handled by the +4 deg release detent and CALIBRATION.md (sim/launch.py, D16).",
    "range": "Follows from the lower launch angle and the rolling energy share; the kit is calibrated "
             "on the real machine with the preload adjuster, so the absolute range at fixed preload is "
             "not a design input (Monte Carlo calibrated study).",
    "peak can acceleration": "Calc is a rigid-cup average; the sim resolves the TPU pad contact and is "
                             "reported 2 ms-filtered. Both are far below the can's tolerance (REPORT.md).",
}


def rows():
    s = D.setting(4.0)
    m, sw = s["model"], s["swing"]
    v = replace(Variation(), preload_mm=m.x_rest / MM, release_deg=0.0)
    r = run(v, release_deg=0.0, keep_traj=True)
    calc_angle = m.alpha_release_deg - 90.0
    out = [
        ("release speed", sw.v_release, r.v_release, "m/s"),
        ("launch angle", calc_angle, r.angle_release, "deg"),
        ("range", 4.0, r.range_m, "m"),
        ("peak can acceleration", sw.a_peak, r.a_can_peak, "m/s2"),
        ("feed time", M.T_FEED, 0.223 + r.t_feed_after_60mm, "s"),
    ]
    res = []
    for name, c, sv, unit in out:
        d = (sv - c) / c * 100.0
        ex = EXPLAIN.get(name, "") if abs(d) > LIMIT else ""
        res.append(dict(quantity=name, unit=unit, calc=c, sim=sv, diff_pct=d, explanation=ex,
                        ok=abs(d) <= LIMIT or bool(ex)))
    return res


def main():
    rs = rows()
    OUT.write_text(json.dumps(dict(limit_pct=LIMIT, rows=rs), indent=1))
    for r in rs:
        print(f"{r['quantity']:24s} calc {r['calc']:8.3f}  sim {r['sim']:8.3f} {r['unit']:5s} "
              f"{r['diff_pct']:+6.1f} %  {'ok' if r['ok'] else 'UNEXPLAINED'}")
    return rs


if __name__ == "__main__":
    main()
