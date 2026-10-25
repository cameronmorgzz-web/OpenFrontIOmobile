"""Magazine + seesaw escapement feed simulation (MuJoCo), with variation.

Model: 30 deg chute rails (both can ends), end walls, vertical column guides above can2, five
free cans (can1, can2 on the chute; can3..can5 in the column), and the escapement rocker as a
hinged body driven by a position servo (MG996R: 0.17 s/60 deg at 5 V, MC +/-30 %).
One feed cycle = servo to RELEASE, dwell, back to HOLD, wait for the column to settle.
A can is "fed" when its centre passes 60 mm downhill of can1's resting point (it then rolls on
into the cup; that part is covered by sim/launch.py). Per cycle we require exactly one can:
  0 cans while cans remain  -> JAM
  2 cans                    -> DOUBLE FEED

Variation per trial: can-rail, can-can, can-wall friction (0.12-0.45), can diameter
(65.8-66.6 mm), wall gap (+0..0.6 mm, print tolerance), rail height (+/-0.3 mm), column guide
position (+/-0.3 mm), servo speed (+/-30 %), can mass (+/-4 %).

    python -m sim.feed_sim            # 300 trials x 5 cycles (~10 min on 4 cores)
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
from pathlib import Path

import mujoco
import numpy as np

from cad import params as P
from cad.src import launcher as L

OUT = Path(__file__).resolve().parent
MM = 1e-3


def build_xml(v: dict) -> str:
    r = v["can_d"] / 2 * MM
    Lc = P.CAN_L * MM
    yin = (L.MAG_Y_IN + v["wall_gap"]) * MM
    a0, a1, d = L._chute_pts()
    p0 = np.array(a0) * MM
    p1 = np.array(a1) * MM
    mid = (p0 + p1) / 2
    length = float(np.linalg.norm(p1 - p0))
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    nrm = np.array([0.5, 0.866])
    dz = v["rail_dz"] * MM
    geoms = []
    for s in (-1, 1):
        c = mid - nrm * 0.004 + nrm * dz
        geoms.append(f'<geom type="box" pos="{c[0]} {s * (yin - 0.0065)} {c[1]}" euler="0 {-ang} 0" '
                     f'size="{length / 2} 0.0065 0.004" friction="{v["mu_rail"]} 0.005 0.0001"/>')
        geoms.append(f'<geom type="box" pos="{mid[0]} {s * (yin + 0.004)} {mid[1] + 0.06}" euler="0 {-ang} 0" '
                     f'size="{length / 2} 0.004 0.08" friction="{v["mu_wall"]} 0.005 0.0001"/>')
    xc = L.MAG_XC * MM
    zc2 = (P.PIVOT_H + L.CAN2[1]) * MM
    top = L.MAG_TOP * MM
    col_h = (top - zc2) / 2
    g = v["guide_dx"] * MM
    # column guides (front stops above can2 so it can roll out; back runs full height)
    zf0 = zc2 + r + 0.012
    geoms.append(f'<geom type="box" pos="{xc - r - L.COL_CLR * MM - 0.003 - g} 0 {(zc2 - 0.01 + top) / 2}" size="0.003 {yin} {(top - zc2 + 0.01) / 2}" friction="{v["mu_wall"]} 0.005 0.0001"/>')
    geoms.append(f'<geom type="box" pos="{xc + r + L.COL_CLR * MM + 0.003 + g} 0 {(zf0 + top) / 2}" size="0.003 {yin} {(top - zf0) / 2}" friction="{v["mu_wall"]} 0.005 0.0001"/>')
    for s in (-1, 1):
        geoms.append(f'<geom type="box" pos="{xc} {s * (yin + 0.004)} {(zc2 + top) / 2}" size="{r + 0.01} 0.004 {col_h}" friction="{v["mu_wall"]} 0.005 0.0001"/>')
    # rocker
    ax = np.array(L.rocker_axle()) * MM
    up = np.array([0.5, 0.866])
    q1 = np.array(L.chute_s(L.ROCKER_S1)) * MM
    q2 = np.array(L.chute_s(L.ROCKER_S2)) * MM
    t1 = q1 + up * L.ROCKER_F1_H * MM + up * dz
    t2 = q2 + up * L.ROCKER_F2_H * MM + up * dz
    b1 = q1 - up * L.ROCKER_DEPTH * MM
    b2 = q2 - up * L.ROCKER_DEPTH * MM
    yr = (L.ROCKER_Y[0] + L.ROCKER_Y[1]) / 2 * MM

    def rel(p):
        return f"{p[0] - ax[0]} 0 {p[1] - ax[1]}"
    rocker = f"""
    <body name="rocker" pos="{ax[0]} {yr} {ax[1]}">
      <joint name="rock" type="hinge" axis="0 -1 0" damping="0.02" armature="0.005" limited="true" range="-55 10"/>  <!-- armature: servo rotor reflected through its gearbox -->
      <inertial pos="0 0 0" mass="0.01" diaginertia="2e-6 2e-6 2e-6"/>
      <geom type="capsule" fromto="0 0 0 {rel(b1)}" size="0.004" contype="0" conaffinity="0"/>
      <geom type="capsule" fromto="0 0 0 {rel(b2)}" size="0.004" contype="0" conaffinity="0"/>
      <geom name="f1" type="capsule" fromto="{rel(b1)} {rel(t1)}" size="0.0035" contype="2" conaffinity="2" friction="0.3 0.005 0.0001"/>
      <geom name="f2" type="capsule" fromto="{rel(b2)} {rel(t2)}" size="0.0035" contype="2" conaffinity="2" friction="0.3 0.005 0.0001"/>
    </body>"""
    # cans: can1, can2 on the chute, can3..5 in the column
    m_can = P.CAN["mass_full"] * v["mass"]
    I_ax = 0.15 * 0.5 * m_can * r * r + 1e-6
    I_tr = m_can * (3 * r * r + Lc * Lc) / 12
    starts = [np.array(L.abs_xz(L.CAN1)) * MM + np.array([-0.0005, 0.0003]), np.array(L.abs_xz(L.CAN2)) * MM]
    for k in range(L.N_COLUMN):
        starts.append(np.array([xc, zc2 + (k + 1) * (2 * r + 0.0006)]))
    cans = "".join(
        f'<body name="can{i + 1}" pos="{p[0]} 0 {p[1]}"><freejoint/>'
        f'<inertial pos="0 0 0" mass="{m_can}" diaginertia="{I_tr} {I_ax} {I_tr}"/>'
        f'<geom type="cylinder" size="{r} {Lc / 2}" euler="90 0 0" contype="3" conaffinity="3" friction="{v["mu_can"]} 0.005 0.0001"/></body>'
        for i, p in enumerate(starts))
    return f"""<mujoco>
  <option timestep="0.0005" integrator="implicitfast" cone="elliptic" impratio="5"/>
  <default><geom condim="4" solref="0.004 1" solimp="0.95 0.99 0.001" margin="0.0005"/></default>
  <worldbody>{''.join(geoms)}{rocker}{cans}</worldbody>
  <actuator><motor name="servo" joint="rock" gear="1" ctrllimited="false"/></actuator>
</mujoco>"""


T_STAGE, T_RELEASE, T_RETURN = 0.40, 0.45, 0.60
ESC_SERVO_TAU, ESC_SERVO_S60 = 0.92, 0.17   # MG996R at 5 V (an MG90S, 0.18 N m, jammed 129 of 480 cycles)


def trial(seed: int, cycles: int = 5) -> dict:
    rng = np.random.default_rng(seed)
    v = dict(mu_rail=rng.uniform(0.12, 0.45), mu_can=rng.uniform(0.10, 0.40), mu_wall=rng.uniform(0.10, 0.40),
             can_d=rng.uniform(65.8, 66.6), wall_gap=rng.uniform(0.0, 0.6), rail_dz=rng.uniform(-0.3, 0.3),
             guide_dx=rng.uniform(-0.3, 0.3), servo=rng.uniform(0.7, 1.3), mass=rng.uniform(0.96, 1.04))
    m = mujoco.MjModel.from_xml_string(build_xml(v))
    d = mujoco.MjData(m)
    dt = m.opt.timestep
    can_ids = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f"can{i + 1}") for i in range(2 + L.N_COLUMN)]
    qadr = [m.jnt_qposadr[m.body_jntadr[b]] for b in can_ids]
    dadr = [m.jnt_dofadr[m.body_jntadr[b]] for b in can_ids]
    # servo (MG996R) drives the rocker through the horn +
    # pushrod toggle: rocker angle theta(phi), torque limit tau_servo / |dtheta/dphi|; when the
    # servo saturates, the horn stalls (phi stops advancing)
    slew = math.radians(60) / (ESC_SERVO_S60 * v["servo"])
    tau_servo = ESC_SERVO_TAU / v["servo"]
    phi = math.radians(L.ESC_PHI_HOLD)
    target = phi
    jr = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "rock")]
    jd = m.jnt_dofadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "rock")]
    c1 = np.array(L.abs_xz(L.CAN1)) * MM
    down = np.array([0.866, -0.5])
    fed_flags = [False] * len(can_ids)
    t_clear = []

    def step(n):
        nonlocal phi
        for _ in range(n):
            pdeg = math.degrees(phi)
            th_t = L.esc_theta(pdeg)
            lim = min(tau_servo / max(abs(L.esc_dtheta_dphi(pdeg)), 1e-3), 30.0)
            tau = 400.0 * (th_t - d.qpos[jr]) - 2.0 * d.qvel[jd]
            sat = abs(tau) >= lim
            d.ctrl[0] = float(np.clip(tau, -lim, lim))
            if not sat or abs(th_t - d.qpos[jr]) < 0.02:
                phi += float(np.clip(target - phi, -slew * dt, slew * dt))
            mujoco.mj_step(m, d)
            for i, b in enumerate(can_ids):
                if fed_flags[i]:
                    continue
                p = d.xpos[b][[0, 2]]
                if (p - c1) @ down > 0.06:
                    fed_flags[i] = True
                    t_clear.append(d.time)
                    # park it far away (it would be in the cup now)
                    d.qpos[qadr[i]:qadr[i] + 3] = [5.0 + i, 0.0, -5.0]
                    d.qvel[dadr[i]:dadr[i] + 6] = 0.0
    step(int(0.6 / dt))                      # settle the full magazine
    results = []
    for c in range(cycles):
        before = sum(fed_flags)
        target = math.radians(L.ESC_PHI_STAGE)
        step(int(T_STAGE / dt))              # pre-stage while the arm is still cocking: nothing may move
        early = sum(fed_flags) - before
        t0 = d.time
        target = math.radians(L.ESC_PHI_REL)
        step(int(T_RELEASE / dt))            # horn 65 -> 125 deg (0.17 s unloaded) and dwells
        target = math.radians(L.ESC_PHI_HOLD)
        step(int(T_RETURN / dt))             # back to hold, column settles
        t_feed = [t - t0 for t in t_clear if t > t0]
        n = sum(fed_flags) - before
        remaining = len(can_ids) - sum(fed_flags)
        results.append(dict(cycle=c, fed=n, early=early, remaining=remaining, t_clear=t_feed[0] if t_feed else None))
    jams = sum(1 for r in results if r["fed"] == 0 and r["remaining"] + r["fed"] > 0)
    doubles = sum(1 for r in results if r["fed"] >= 2)
    early = sum(r["early"] for r in results)
    # can3+ must never end up uncontrolled on the chute (stuck between gates is checked as jam)
    return dict(seed=seed, var=v, cycles=results, jams=jams, doubles=doubles, early=early, total_fed=sum(fed_flags))


def main(n=300, cycles=5):
    with mp.Pool(mp.cpu_count()) as pool:
        rows = pool.starmap(trial, [(s, cycles) for s in range(n)])
    jam_trials = [r for r in rows if r["jams"]]
    dbl_trials = [r for r in rows if r["doubles"]]
    summary = dict(trials=n, cycles_each=cycles, total_cycles=n * cycles,
                   jam_cycles=sum(r["jams"] for r in rows), early_release=sum(r["early"] for r in rows), double_feed_cycles=sum(r["doubles"] for r in rows),
                   trials_with_jam=len(jam_trials), trials_with_double=len(dbl_trials),
                   fed_all_five=sum(1 for r in rows if r["total_fed"] == 2 + L.N_COLUMN),
                   worst_jam_vars=[r["var"] for r in jam_trials[:5]], worst_double_vars=[r["var"] for r in dbl_trials[:5]])
    (OUT / "feed_results.json").write_text(json.dumps(dict(summary=summary, trials=rows), indent=1))
    _plot(rows)
    print(json.dumps(summary, indent=1))
    return summary


def _plot(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    (OUT / "plots").mkdir(exist_ok=True)
    mu = np.array([r["var"]["mu_rail"] for r in rows])
    mc = np.array([r["var"]["mu_can"] for r in rows])
    bad = np.array([r["jams"] + r["doubles"] + r["early"] > 0 for r in rows])
    fig, ax = plt.subplots(figsize=(5.5, 4))
    ax.scatter(mu[~bad], mc[~bad], s=12, c="#1f6fb4", label="5/5 single feeds")
    ax.scatter(mu[bad], mc[bad], s=30, c="r", marker="x", label="jam / double / early")
    ax.set_xlabel("can-rail friction"), ax.set_ylabel("can-can friction"), ax.legend(fontsize=8)
    ax.set_title(f"Escapement feed sim: {len(rows)} trials x 5 cycles")
    fig.tight_layout(), fig.savefig(OUT / "plots" / "feed_sim.png", dpi=130), plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=300)
    a = ap.parse_args()
    main(a.n)
