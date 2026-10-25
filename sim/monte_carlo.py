"""Monte Carlo over real-world variation, through the full MuJoCo launch model (sim/launch.py).

Two studies (DECISIONS.md D16):
  A) "uncalibrated": nominal preload, every unit- and shot-level variation at once.
  B) "calibrated" (how the kit is used): N_UNITS builds, each with its own spring batch etc.,
     calibrated with the CALIBRATION.md procedure (adjust preload until the mean lands at 4 m;
     preload resolution 0.5 mm = half a turn of the M6 adjusters; +/- 5 cm tape error),
     then N_SHOTS shots each with shot-to-shot variation.

    python -m sim.monte_carlo            # both studies, ~20 min on 4 cores
    python -m sim.monte_carlo --quick    # smoke test
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from sim.launch import nominal_preload, run
from sim.model import MM, Variation

OUT = Path(__file__).resolve().parent
TARGET = 4.0
DETENT = 4.0                 # release-angle detent used for 4 m (sim/launch.py: ~47 deg launch)
N_UNITS, N_SHOTS = 50, 20
N_UNCAL = 1000
FEA_JSON = OUT / "fea" / "results.json"


def frame_preload_loss_mm() -> float:
    """Cord-path shortening under load (FEA: plates + pulley bracket + anchor wall) and 24 h creep
    of the anchor wall, mm of spring preload lost. Falls back to 0 if FEA hasn't run."""
    if FEA_JSON.exists():
        d = json.loads(FEA_JSON.read_text())
        return float(d.get("preload_loss_mm", 0.0))
    return 0.0


def sample_unit(rng) -> dict:
    return dict(spring_rate=rng.uniform(0.9, 1.1), spring_f0=rng.uniform(0.85, 1.15),
                eta_f=0.05 * rng.uniform(0.7, 1.3), frame_loss=rng.uniform(0.0, 1.0) * frame_preload_loss_mm())


def sample_shot(rng, base: Variation) -> Variation:
    return replace(base,
                   can_mass=rng.uniform(0.96, 1.04),
                   mu_can_pad=0.55 * rng.uniform(0.7, 1.3),
                   mu_can_floor=0.12 * rng.uniform(0.7, 1.3),
                   mu_can_rail=0.25 * rng.uniform(0.7, 1.3),
                   eta_f=base.eta_f * rng.uniform(0.9, 1.1),          # day-to-day cord/spring friction
                   release_deg=DETENT + rng.normal(0.0, 0.15),          # stop seating / detent play
                   latch_delay=rng.uniform(0.0, 0.02),
                   cd=rng.uniform(0.60, 0.90), cl=rng.uniform(-0.10, 0.20),
                   rho_air=1.20 * rng.uniform(0.97, 1.03),
                   can_d=66.2 + rng.uniform(-0.3, 0.3),
                   spin_frac=rng.uniform(0.05, 0.3))


def _run(var: Variation) -> dict:
    r = run(var, release_deg=var.release_deg)
    d = {k: v for k, v in r.__dict__.items() if not isinstance(v, np.ndarray) and v is not None}
    d["preload_mm"] = var.preload_mm
    return d


def calibrate(unit: dict, rng, target=TARGET) -> float:
    """Secant on preload with nominal shot conditions, then quantise + measurement error."""
    base = replace(Variation(), spring_rate=unit["spring_rate"], spring_f0=unit["spring_f0"], eta_f=unit["eta_f"],
                   release_deg=DETENT)
    x0 = nominal_preload(4.0) / MM + 4.0
    x1 = x0 + 6.0

    def rng_at(x):
        r = run(replace(base, preload_mm=x - unit["frame_loss"]), release_deg=DETENT)
        return r.range_m if r.ok else float("nan")
    f0, f1 = rng_at(x0) - target, rng_at(x1) - target
    for _ in range(4):
        if not (math.isfinite(f0) and math.isfinite(f1)) or abs(f1 - f0) < 1e-6:
            break
        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        x0, f0 = x1, f1
        x1, f1 = x2, rng_at(x2) - target
        if abs(f1) < 0.01:
            break
    sens = 0.067                                       # m per mm (calc/RESULTS.md)
    x_cal = x1 + rng.normal(0.0, 0.05 / sens / math.sqrt(1.0))   # tape-measure / averaging error (+/-5 cm)
    return round(x_cal * 2) / 2                        # half-turn resolution


def unit_job(seed):
    rng = np.random.default_rng(seed)
    u = sample_unit(rng)
    x = calibrate(u, rng)
    base = replace(Variation(), spring_rate=u["spring_rate"], spring_f0=u["spring_f0"], eta_f=u["eta_f"],
                   preload_mm=x - u["frame_loss"])
    shots = [_run(sample_shot(rng, base)) for _ in range(N_SHOTS)]
    for s in shots:
        s.update(unit=seed, **{f"unit_{k}": v for k, v in u.items()}, preload_set=x)
    return shots


def uncal_job(seed):
    rng = np.random.default_rng(10_000 + seed)
    u = sample_unit(rng)
    base = replace(Variation(), spring_rate=u["spring_rate"], spring_f0=u["spring_f0"], eta_f=u["eta_f"],
                   preload_mm=NOMINAL_X - u["frame_loss"])
    return _run(sample_shot(rng, base))


NOMINAL_X = None


def nominal_x_for_target() -> float:
    u = dict(spring_rate=1.0, spring_f0=1.0, eta_f=0.05, frame_loss=0.0)
    rng = np.random.default_rng(0)
    x = calibrate(u, rng)
    return x


def summarize(rows, label):
    ok = [r for r in rows if r.get("ok")]
    R = np.array([r["range_m"] for r in ok])
    vc = np.array([r["v_catch"] for r in ok])
    pk = np.array([r["peak_z"] for r in ok])
    return dict(label=label, n=len(rows), n_ok=len(ok), fail_rate=1 - len(ok) / max(len(rows), 1),
                range_mean=float(R.mean()), range_sd=float(R.std(ddof=1)), range_p5=float(np.percentile(R, 5)),
                range_p95=float(np.percentile(R, 95)), v_catch_mean=float(vc.mean()), v_catch_max=float(vc.max()),
                peak_mean=float(pk.mean()), peak_max=float(pk.max()),
                v_release_sd_pct=float(np.std([r["v_release"] for r in ok]) / np.mean([r["v_release"] for r in ok]) * 100),
                angle_sd=float(np.std([r["angle_release"] for r in ok])),
                a_peak_max=float(np.max([r["a_can_peak"] for r in ok])),
                t_feed_max=float(np.max([r["t_feed"] for r in ok])))


def main(quick=False):
    global NOMINAL_X
    n_units, n_uncal = (3, 8) if quick else (N_UNITS, N_UNCAL)
    NOMINAL_X = nominal_x_for_target()
    with mp.Pool(mp.cpu_count()) as pool:
        cal = [s for shots in pool.map(unit_job, range(n_units)) for s in shots]
        unc = pool.map(uncal_job, range(n_uncal))
    res = dict(nominal_preload_mm=NOMINAL_X, frame_preload_loss_mm=frame_preload_loss_mm(),
               calibrated=summarize(cal, "calibrated"), uncalibrated=summarize(unc, "uncalibrated"))
    (OUT / "mc_results.json").write_text(json.dumps(res, indent=1))
    (OUT / "mc_runs.json").write_text(json.dumps(dict(calibrated=cal, uncalibrated=unc)))
    _plots(cal, unc)
    print(json.dumps(res, indent=1))
    return res


def _plots(cal, unc):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    (OUT / "plots").mkdir(exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for rows, lab, c in ((unc, "uncalibrated", "#bbbbbb"), (cal, "calibrated (CALIBRATION.md)", "#1f6fb4")):
        R = [r["range_m"] for r in rows if r.get("ok")]
        ax[0].hist(R, bins=40, alpha=0.75, label=f"{lab}: sd {np.std(R)*100:.1f} cm", color=c)
    ax[0].axvspan(TARGET - 0.25, TARGET + 0.25, color="g", alpha=0.08, label="+/-25 cm")
    ax[0].set_xlabel("landing distance at 0.9 m catch height [m]"), ax[0].legend(fontsize=7)
    vc = [r["v_catch"] for r in cal if r.get("ok")]
    ax[1].hist(vc, bins=30, color="#1f6fb4")
    ax[1].axvline(4.0, color="r", ls="--", lw=1, label="brief target 4 m/s (unreachable, see REPORT)")
    ax[1].set_xlabel("catch speed [m/s]"), ax[1].legend(fontsize=7)
    pk = [r["peak_z"] for r in cal if r.get("ok")]
    ax[2].hist(pk, bins=30, color="#1f6fb4")
    ax[2].axvline(2.3, color="r", ls="--", lw=1, label="peak limit 2.3 m")
    ax[2].set_xlabel("peak height [m]"), ax[2].legend(fontsize=7)
    fig.suptitle("Monte Carlo at the 4 m setting (MuJoCo launch model)")
    fig.tight_layout()
    fig.savefig(OUT / "plots" / "monte_carlo_4m.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
