"""Gate 3: simulation results (run `make sim` to regenerate)."""

import json

import pytest

from cad import params as P
from tests.conftest import ROOT

SIM = ROOT / "sim"


def _j(p):
    return json.loads((SIM / p).read_text())


def test_feed_single_feeds():
    s = _j("feed_results.json")["summary"]
    assert s["total_cycles"] >= 1000
    assert s["jam_cycles"] == 0 and s["double_feed_cycles"] == 0 and s["early_release"] == 0


def test_monte_carlo_dispersion():
    m = _j("mc_results.json")
    cal = m["calibrated"]
    assert cal["n"] >= 1000, "run the full study: python -m sim.monte_carlo"
    assert cal["fail_rate"] == 0.0
    assert cal["range_sd"] <= 0.25
    assert abs(cal["range_mean"] - 4.0) <= 0.10
    assert cal["peak_max"] <= 2.3
    assert m["uncalibrated"]["n"] >= 1000


def test_can_survives():
    # peak filtered can acceleration vs a 1 m drop onto a hard floor (~1000 g); see REPORT.md
    assert _j("mc_results.json")["calibrated"]["a_peak_max"] < 0.2 * 1000 * 9.81


def test_fea_safety_factors():
    cases = _j("fea/results.json")["cases"]
    assert len(cases) >= 10
    for c in cases:
        if "DRY FIRE" in c["case"].upper():
            assert c["sf_static"] >= 1.0, c
            continue
        sfs = [c["sf_static"]] + [c[k] for k in ("sf_fatigue", "sf_creep") if c.get(k) is not None]
        assert min(sfs) >= 2.5, f"{c['part']} / {c['case']}: {min(sfs):.2f}"


def test_fea_preload_loss_small():
    # elastic + creep loss of the cord path must stay inside the preload adjuster range
    assert _j("fea/results.json")["preload_loss_mm"] < 0.1 * P.PRELOAD_ADJ_RANGE[1]


def test_sim_vs_calc():
    v = _j("validation.json")
    for row in v["rows"]:
        assert row["ok"], row
