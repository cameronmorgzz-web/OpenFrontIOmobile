"""Full launch sequence in MuJoCo: COCK (motor model) -> FEED (escapement + chute + cup contact)
-> RELEASE (latch) -> swing (spring force element) -> absorber stop -> can flight (drag, Magnus)
-> landing point at catch height.

    python -m sim.launch            # nominal 4 m shot, prints a summary
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import mujoco
import numpy as np

from cad import params as P
from cad.src import launcher as L
from calc import design as D
from calc.design import GEAR_EFF, GEAR_RATIO, MOTOR
from sim.model import MM, Variation, build

H_CATCH = 0.90
ABS_C = 220.0         # N s^2/m^2 velocity-squared damping of the self-compensating absorber (5 m shot uses ~13 mm of 16)
ABS_FRET = 12.0       # N return spring
ABS_K_END = 2.0e6     # N/m hard stop at the end of stroke


@dataclass
class Result:
    ok: bool
    reason: str = ""
    t_cock: float = float("nan")
    t_feed: float = float("nan")
    t_feed_after_60mm: float = float("nan")   # roll time from 60 mm past the gate to seated (feed_sim measures up to 60 mm)
    v_release: float = float("nan")
    angle_release: float = float("nan")
    x_release: float = float("nan")
    z_release: float = float("nan")
    range_m: float = float("nan")
    v_catch: float = float("nan")
    peak_z: float = float("nan")
    t_flight: float = float("nan")
    a_can_peak: float = float("nan")
    abs_stroke_mm: float = float("nan")
    spin_rps: float = float("nan")
    traj: np.ndarray | None = None
    arm_trace: np.ndarray | None = None


def nominal_preload(range_m=4.0) -> float:
    return D.setting(range_m)["model"].x_rest


def spring_torque(alpha, var: Variation, x_rest):
    """Torque (N m) on the pivot in the +alpha direction (negative = fires)."""
    s = P.SPRING
    rd = P.DRUM_R * MM
    x = x_rest + rd * (alpha - math.radians(L.A_RELEASE))
    x = max(x, 0.0)
    F = P.N_SPRINGS * (s.f0 * var.spring_f0 + s.rate * var.spring_rate * 1000 * x)
    return -F * rd


def _can_in_contact_with_arm(m, d, arm_id):
    for i in range(d.ncon):
        c = d.contact[i]
        b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
        if arm_id in (b1, b2):
            return True
    return False


def run(var: Variation = Variation(), range_m: float = 4.0, do_cock=False, keep_traj=False,
        release_deg: float | None = None) -> Result:
    m, d = build(var, can_start="chute")
    arm_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "arm")
    can_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "can")
    j_arm = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "pivot")]
    dof_arm = m.jnt_dofadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "pivot")]
    can_q = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "can_free")]
    x_rest = var.preload_mm * MM if var.preload_mm is not None else nominal_preload(range_m)
    a_rel = math.radians(L.A_RELEASE + (release_deg if release_deg is not None else var.release_deg))
    a_cock = math.radians(L.A_COCKED)
    a_rest = a_rel - math.radians(P.ABS_STROKE_DEG)
    r_a = P.ABS_R * MM
    dt = m.opt.timestep
    res = Result(ok=False)

    # ---------------- COCK (optional): motor drives the arm from rest to cocked ----------------
    t = 0.0
    if do_cock:
        d.qpos[j_arm] = a_rest
        mujoco.mj_forward(m, d)
        w0 = MOTOR["w0_rpm"] * 2 * math.pi / 60
        Ts = MOTOR["stall_torque"]
        while d.qpos[j_arm] < a_cock and t < 4.0:
            w_arm = d.qvel[dof_arm]
            w_motor = w_arm * GEAR_RATIO
            Tm = Ts * max(0.0, 1 - w_motor / w0)
            d.qfrc_applied[dof_arm] = Tm * GEAR_RATIO * GEAR_EFF + spring_torque(d.qpos[j_arm], var, x_rest) * (1 + var.eta_f)
            # can waits on the chute against the gate
            mujoco.mj_step(m, d)
            t += dt
        res.t_cock = t
        if d.qpos[j_arm] < a_cock:
            res.reason = "cock stalled"
            return res
    # hold at cocked (latch + motor hold): kinematic lock
    def hold():
        d.qpos[j_arm] = a_cock
        d.qvel[dof_arm] = 0.0
    hold()
    mujoco.mj_forward(m, d)
    for _ in range(int(0.15 / dt)):   # can settles against the gate
        hold()
        mujoco.mj_step(m, d)
    # ---------------- FEED: drop the gate, can rolls down the chute into the cup ----------------
    d.mocap_pos[0] = [0, 0, -1]
    t_feed = 0.0
    seated = 0
    t60 = None
    c1 = np.array(L.abs_xz(L.CAN1)) * MM
    cs = np.array(L.abs_xz(L.CUP_SEAT_COCKED)) * MM
    while t_feed < 1.2:
        hold()
        mujoco.mj_step(m, d)
        t_feed += dt
        pos = d.xpos[can_id]
        if t60 is None and (pos[[0, 2]] - c1) @ np.array([0.866, -0.5]) > 0.06:
            t60 = t_feed
        v = np.linalg.norm(d.cvel[can_id][3:])
        if np.hypot(pos[0] - cs[0], pos[2] - cs[1]) < 0.006 and v < 0.05:
            seated += 1
            if seated * dt > 0.03:
                break
        else:
            seated = 0
    res.t_feed = t_feed
    res.t_feed_after_60mm = t_feed - (t60 if t60 is not None else 0.0)
    if seated * dt <= 0.03:
        res.reason = f"feed: can not seated (at {d.xpos[can_id].round(3)})"
        return res
    # latch delay (servo trip time / jitter)
    for _ in range(int(max(var.latch_delay, 0.0) / dt)):
        hold()
        mujoco.mj_step(m, d)
    # ---------------- RELEASE + swing + absorber + flight ----------------
    released = False
    t_r = 0.0
    a_peak = 0.0
    vprev = d.cvel[can_id][3:].copy()
    acc_hist = []                     # 2 ms moving average: contact chatter of a stiff solver is not
    n_avg = max(1, int(0.002 / dt))   # physical (the TPU pad smooths it)
    traj = []
    arm_tr = []
    max_stroke = 0.0
    k_d = 0.5 * var.rho_air * var.cd * (var.can_d * MM) * (P.CAN_L * MM)
    k_l = 0.5 * var.rho_air * var.cl * (var.can_d * MM) * (P.CAN_L * MM)
    peak = -1.0
    t_fl = 0.0
    while t_r < 3.0:
        a = d.qpos[j_arm]
        w = d.qvel[dof_arm]
        T = spring_torque(a, var, x_rest) * (1 - var.eta_f)
        s = max(0.0, (a_rel - a) * r_a)
        if s > 0:
            v = -w * r_a
            F = (ABS_C * v * v if v > 0 else 0.0) + ABS_FRET + (ABS_K_END * (s - P.ABS_STROKE * MM) if s > P.ABS_STROKE * MM else 0)
            T += F * r_a
            max_stroke = max(max_stroke, s)
        d.qfrc_applied[dof_arm] = T
        # aero on the can
        vel = d.cvel[can_id][3:]
        sp = np.linalg.norm(vel)
        if sp > 0.1:
            drag = -k_d * sp * vel
            # Magnus: lift perpendicular to v in the x-z plane, sign from spin about -y (top-spin -> down)
            om_y = d.cvel[can_id][1]
            spin_sign = np.sign(-om_y)
            lift = k_l * sp * np.array([vel[2], 0, -vel[0]]) * spin_sign
            d.xfrc_applied[can_id, :3] = drag + lift
        mujoco.mj_step(m, d)
        t_r += dt
        acc = (d.cvel[can_id][3:] - vprev) / dt
        vprev = d.cvel[can_id][3:].copy()
        if not released:
            acc_hist.append(acc + np.array([0, 0, 9.81]))
            if len(acc_hist) >= n_avg:
                a_peak = max(a_peak, float(np.linalg.norm(np.mean(acc_hist[-n_avg:], axis=0))))
            arm_tr.append((t_r, d.qpos[j_arm], d.qvel[dof_arm]))
        pos = d.xpos[can_id].copy()
        if keep_traj and int(t_r / dt) % 20 == 0:
            traj.append(pos.copy())
        if not released and t_r > 0.01 and not _can_in_contact_with_arm(m, d, arm_id) and d.qpos[j_arm] < a_rel + 0.3:
            released = True
            res.v_release = float(np.linalg.norm(d.cvel[can_id][3:]))
            res.angle_release = float(math.degrees(math.atan2(d.cvel[can_id][5], d.cvel[can_id][3])))
            res.x_release, res.z_release = float(pos[0]), float(pos[2])
            res.spin_rps = float(abs(d.cvel[can_id][1]) / (2 * math.pi))
            t_fl = 0.0
        if released:
            t_fl += dt
            peak = max(peak, pos[2])
            if d.cvel[can_id][5] < 0 and pos[2] <= H_CATCH:
                res.range_m = float(pos[0] - res.x_release)
                res.v_catch = float(np.linalg.norm(d.cvel[can_id][3:]))
                res.peak_z = float(peak)
                res.t_flight = float(t_fl)
                res.ok = True
                break
        if t_r > 0.5 and not released:
            res.reason = "can never left the cup"
            break
    res.a_can_peak = a_peak
    res.abs_stroke_mm = max_stroke / MM
    if keep_traj:
        res.traj = np.array(traj)
        res.arm_trace = np.array(arm_tr)
    if not res.ok and not res.reason:
        res.reason = "no landing"
    return res


if __name__ == "__main__":
    r = run(Variation(), do_cock=True, keep_traj=True)
    for k, v in r.__dict__.items():
        if not isinstance(v, np.ndarray):
            print(f"{k:14s} {v}")
