"""MuJoCo model of the launcher (arm + cup + absorber + chute + escapement finger) and the can.

Built from cad/params.py, cad/src/launcher.py geometry and cad/mass_props.json, so it uses the
real CAD dimensions and masses. World frame = launcher assembly frame in metres (x forward,
y = pivot axis, z up, floor at z = 0).

Force elements (applied each step in sim/launch.py, not baked into the XML):
  * spring: T = n (F0 + k x) r_d (1 - eta_f), x = x_rest + r_d (alpha - alpha_release)   [calc/arm_dynamics.py]
  * absorber (AC1416, self-compensating): F = c v^2 + F_ret while compressed, hard stop at 16 mm
  * aerodynamics on the can: quadratic drag + Magnus (calc/ballistics.py coefficients)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import mujoco
import numpy as np

from cad import params as P
from cad.src import launcher as L

ROOT = Path(__file__).resolve().parents[1]
MM = 1e-3


@dataclass
class Variation:
    """Real-world variation applied to one run (1.0 / 0.0 = nominal)."""
    can_mass: float = 1.0          # x nominal
    spring_rate: float = 1.0       # x nominal (per unit, batch)
    spring_f0: float = 1.0
    mu_can_pad: float = 0.55       # aluminium on TPU 95A back-wall pad (est.; MC +/-30 %)
    mu_can_floor: float = 0.12     # aluminium on PTFE tape on the cup floor + feed lip (est.; MC +/-30 %)
    mu_can_rail: float = 0.25      # aluminium on PETG [C6]
    eta_f: float = 0.05            # friction fraction (cord, yokes, spring hysteresis), MC +/-30 %
    release_deg: float = 0.0       # absorber contact angle offset (stop tolerance)
    latch_delay: float = 0.0       # s, release timing jitter (servo/latch)
    frame_compliance: float = 0.0  # rad per N m: pivot-axis compliance from FEA (loss of stored energy)
    creep_deg: float = 0.0         # absorber bracket creep after sitting (rest-angle shift)
    cd: float = 0.70
    cl: float = 0.0
    rho_air: float = 1.20
    preload_mm: float | None = None   # x_rest; None -> nominal 4 m setting
    can_d: float = P.CAN_D
    spin_frac: float = 0.15
    ramp_deg: float = 15.0          # feed-lip divergence from the cup floor (CAD: launcher.CUP_RAMP_DEG)


def _quat_y(deg):
    """Quaternion for a rotation about +y that maps x towards -z... we need about -y (alpha CCW)."""
    a = math.radians(deg) / 2
    return (math.cos(a), 0.0, -math.sin(a), 0.0)


def build_xml(var: Variation = Variation(), can_start: str = "chute", with_gate=True) -> str:
    mp = json.loads((ROOT / "cad" / "mass_props.json").read_text())["arm_assembly"]
    pz = P.PIVOT_H * MM
    r = var.can_d / 2 * MM
    Lc = P.CAN_L * MM
    m_can = P.CAN["mass_full"] * var.can_mass
    # arm inertial (about COM): Iyy = I_pivot - m d^2
    m_arm, d_cg = mp["m_arm"], mp["l_arm_cg"]
    Iyy = max(mp["I_arm"] - m_arm * d_cg ** 2, 1e-5)
    # cup collision boxes in the arm frame (x along the arm, z = trailing side), metres
    Lr = P.ARM_L * MM
    pad = P.CUP_PAD * MM
    back_in = r + pad
    floor_in = Lr + r + 0.0003      # floor: PTFE tape (0.1 mm) instead of the TPU pad
    x_lip = Lr - r - pad
    w = L.CUP_WALL * MM
    wf = L.CUP_FLOOR * MM
    cup_hy = (L.CUP_Y[1] - 3) * MM
    soft = 'solref="0.004 0.9" solimp="0.9 0.97 0.001"'   # TPU pad: softer contact
    cup = f"""
      <geom name="cup_back" type="box" pos="{(x_lip + floor_in) / 2} 0 {back_in + w / 2}" size="{(floor_in - x_lip) / 2 + 0.006} {cup_hy} {w / 2}" {soft} friction="{var.mu_can_pad} 0.005 0.0001" rgba=".9 .5 .1 1"/>
      <geom name="cup_floor" type="box" pos="{floor_in + wf / 2} 0 {(back_in + w - 0.002) / 2 - 0.001}" size="{wf / 2} {cup_hy} {(back_in + w + 0.002) / 2}" friction="{var.mu_can_floor} 0.005 0.0001" rgba=".9 .5 .1 1"/>
      <geom name="cup_lip" type="box" pos="{x_lip - 0.003} 0 {back_in - 0.007}" size="0.003 {cup_hy} 0.007" friction="{var.mu_can_pad} 0.005 0.0001" rgba=".9 .5 .1 1"/>
      <geom name="cup_ramp" type="box" pos="{floor_in + 0.015 * math.sin(math.radians(var.ramp_deg)) + wf / 2} 0 {-0.002 - 0.015 * math.cos(math.radians(var.ramp_deg))}" euler="0 {-var.ramp_deg} 0" size="{wf / 2} {cup_hy} 0.015" friction="{var.mu_can_floor} 0.005 0.0001" rgba=".9 .5 .1 1"/>
      <geom name="beam" type="box" pos="0.11 0 0" size="0.09 0.014 0.02" contype="0" conaffinity="0" rgba=".95 .95 .93 1"/>
    """
    # chute rails (frame): from the magazine down to the rail end, both can ends
    a0, a1, d = L._chute_pts()
    p0 = np.array([a0[0], a0[1]]) * MM
    p1 = np.array([a1[0], a1[1]]) * MM
    mid = (p0 + p1) / 2
    length = np.linalg.norm(p1 - p0)
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    yin = L.MAG_Y_IN * MM
    rails = ""
    # end guides stop 90 mm before the rail end (as in the CAD walls), clear of the carried can
    pw1 = p0 + (p1 - p0) * max(0.0, (length - 0.09) / length)
    midw = (p0 + pw1) / 2
    lenw = np.linalg.norm(pw1 - p0)
    for s in (-1, 1):
        yc = s * (yin - 0.0065)
        rails += (f'<geom name="rail{s:+d}" type="box" pos="{mid[0]} {yc} {mid[1] - 0.004}" euler="0 {-ang} 0" '
                  f'size="{length / 2} 0.0065 0.004" friction="{var.mu_can_rail} 0.005 0.0001" rgba=".95 .95 .93 1"/>')
        # side guide (end wall) so the can can't walk axially
        rails += (f'<geom name="wall{s:+d}" type="box" pos="{midw[0]} {s * (yin + 0.004)} {midw[1] + 0.03}" euler="0 {-ang} 0" '
                  f'size="{lenw / 2} 0.004 0.04" friction="0.2 0.005 0.0001" rgba=".95 .95 .93 .3"/>')
    # escapement f1 finger (mocap so it can be dropped at release)
    q1 = np.array(L.chute_s(L.ROCKER_S1)) * MM
    up = np.array([0.5, 0.866])
    f1 = q1 + up * 0.011
    gate = (f'<body name="gate" mocap="true" pos="{f1[0]} {-(yin - 0.008)} {f1[1]}">'
            f'<geom type="cylinder" size="0.0035 0.004" euler="90 0 0" friction="0.3 0.005 0.0001" rgba=".2 .2 .2 1"/></body>'
            if with_gate else "")
    # can start pose
    if can_start == "chute":
        c1 = np.array(L.abs_xz(L.CAN1)) * MM + np.array([-0.002 * 0.866, 0.002 * 0.5])
        can_pos = f"{c1[0]} 0 {c1[1]}"
    else:  # seated in the cocked cup
        cs = np.array(L.abs_xz(L.CUP_SEAT_COCKED)) * MM
        can_pos = f"{cs[0]} 0 {cs[1]}"
    I_ax = var.spin_frac * 0.5 * m_can * r * r + 1e-6
    I_tr = m_can * (3 * r * r + Lc * Lc) / 12
    xml = f"""
<mujoco model="beer_launcher">
  <option timestep="0.0002" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="5"/>
  <default><geom condim="4" margin="0.0005" solref="0.003 1" solimp="0.95 0.99 0.001"/></default>
  <worldbody>
    <geom name="floor" type="plane" size="20 20 .1" contype="0" conaffinity="0" rgba=".9 .9 .9 1"/>
    <body name="arm" pos="0 0 {pz}" quat="{' '.join(map(str, _quat_y(0.0)))}">
      <joint name="pivot" type="hinge" axis="0 -1 0" damping="0.0005" armature="0"/>
      <inertial pos="{d_cg} 0 0" mass="{m_arm}" diaginertia="{Iyy * 0.3 + 1e-5} {Iyy} {Iyy * 0.9 + 1e-5}"/>
      {cup}
    </body>
    {rails}
    {gate}
    <body name="can" pos="{can_pos}">
      <freejoint name="can_free"/>
      <inertial pos="0 0 0" mass="{m_can}" diaginertia="{I_tr} {I_ax} {I_tr}"/>
      <geom name="can" type="cylinder" size="{r} {Lc / 2}" euler="90 0 0" friction="{var.mu_can_pad} 0.005 0.0001" rgba=".8 .1 .1 1"/>
    </body>
  </worldbody>
</mujoco>"""
    return xml


def build(var: Variation = Variation(), **kw) -> tuple[mujoco.MjModel, mujoco.MjData]:
    m = mujoco.MjModel.from_xml_string(build_xml(var, **kw))
    d = mujoco.MjData(m)
    return m, d
