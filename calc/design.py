"""Design point shared by every calc and the simulation.

Masses / inertias come from cad/mass_props.json (written by cad/build.py from the
real CAD solids and PETG density) when it exists, otherwise from the documented
pre-CAD estimates below. run_all.py records which source was used.
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

from cad import params as P
from calc.arm_dynamics import ArmModel, preload_for_speed, simulate_swing
from calc.ballistics import Aero, speed_for_range

ROOT = Path(__file__).resolve().parents[1]
MASS_PROPS = ROOT / "cad" / "mass_props.json"

# Pre-CAD estimates (replaced by CAD values once cad/build.py has run)
EST = dict(I_arm=0.0060, m_arm=0.30, l_arm_cg=0.10, I_beam_cup=0.0040)

# Motor: 37GB555 12 V 30:1 with Hall encoder. Published: 133 rpm no-load,
# 10 kg.cm at 100 rpm, 1.5 A, 13 W [P7c]. Stall torque/current derived from the
# linear DC-motor line through those points (unverified -> calibrated in sim MC).
MOTOR = dict(name="37GB555 12V 30:1 + Hall encoder", w0_rpm=133.0, rated_rpm=100.0,
             rated_torque=10 * 0.0981, rated_current=1.5, no_load_current=0.25,
             v=12.0)
MOTOR["stall_torque"] = MOTOR["rated_torque"] / (1 - MOTOR["rated_rpm"] / MOTOR["w0_rpm"])
MOTOR["stall_current"] = MOTOR["no_load_current"] + (MOTOR["rated_current"] - MOTOR["no_load_current"]) \
    * MOTOR["stall_torque"] / MOTOR["rated_torque"]
MOTOR["R_winding"] = MOTOR["v"] / MOTOR["stall_current"]
GEAR_RATIO = P.RING_TEETH / P.PINION_TEETH
GEAR_EFF = 0.85          # printed spur stage (0.90) x bearing/dog friction (0.95)
FRICTION_FRAC = 0.05     # eta_f in the arm model (cord on drum, yokes, spring hysteresis)

H_CATCH = 0.90
RANGES = (3.0, 4.0, 5.0)


def mass_props() -> tuple[dict, str]:
    if MASS_PROPS.exists():
        d = json.loads(MASS_PROPS.read_text())
        return d["arm_assembly"], "CAD (cad/mass_props.json)"
    return EST, "pre-CAD estimate (calc/design.py EST)"


def release_height(alpha_deg: float = P.ALPHA_RELEASE_NOMINAL_DEG) -> float:
    return (P.PIVOT_H + P.ARM_L * math.sin(math.radians(alpha_deg))) / 1000.0


def launch_angle(alpha_deg: float = P.ALPHA_RELEASE_NOMINAL_DEG) -> float:
    return alpha_deg - 90.0


def aero(can: dict | None = None) -> Aero:
    c = can or P.CAN
    return Aero(cd=0.70, cl=0.0, area=c["d"] / 1000 * c["l"] / 1000, mass=c["mass_full"])


def arm_model(can: dict | None = None, alpha_release_deg: float = P.ALPHA_RELEASE_NOMINAL_DEG,
              swing_deg: float | None = None) -> ArmModel:
    c = can or P.CAN
    mp, _ = mass_props()
    s = P.SPRING
    swing = swing_deg if swing_deg is not None else P.ALPHA_COCKED_DEG - alpha_release_deg
    return ArmModel(L=P.ARM_L / 1000, r_d=P.DRUM_R / 1000, swing_deg=swing,
                    alpha_release_deg=alpha_release_deg, m_can=c["mass_full"], can_r=c["d"] / 2000,
                    I_arm=mp["I_arm"], m_arm=mp["m_arm"], l_arm_cg=mp["l_arm_cg"],
                    n_springs=P.N_SPRINGS, k=s.rate, f0=s.f0, m_spring=P.SPRING_MASS,
                    eta_f=FRICTION_FRAC, area_can=c["d"] / 1000 * c["l"] / 1000)


def setting(range_m: float, can: dict | None = None,
            alpha_release_deg: float = P.ALPHA_RELEASE_NOMINAL_DEG) -> dict:
    """Preload + release state for a target range."""
    h0 = release_height(alpha_release_deg)
    v = speed_for_range(range_m, launch_angle(alpha_release_deg), h0, aero(can), H_CATCH)
    m = arm_model(can, alpha_release_deg)
    x = preload_for_speed(m, v, lo=-0.03, hi=0.15)
    m = replace(m, x_rest=x)
    return dict(range_m=range_m, v0=v, h0=h0, model=m, swing=simulate_swing(m))
