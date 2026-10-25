"""Over-centre (toggle) ring latch and its servo trip force.

Load path when cocked: springs -> hub -> catch roller (608 on M8, radius R_c)
-> steel nose dowel of the ring latch -> latch pivot (4 mm dowel in the ring)
-> ring gear -> pinion -> gearmotor (held in closed loop) .
    F_c = T / R_c
The roller pushes on the nose along the contact normal, which passes through the
roller centre. The latch pivot sits a distance e on the *closing* side of that
line, so the load presses the latch shut against its stop (self-locking; holds
with power off):
    M_close = F_c * e
Trip: a frame-mounted servo finger pushes the latch tail (R_t from the pivot)
until the normal crosses the pivot (rotation ~ e / (t + r_roller) rad), after
which the load opens it. Peak torque the finger must supply about the latch pivot:
    M_trip = F_c * e_max + mu_pin * F_c * r_pin + M_spring
    F_finger = M_trip / R_t ,  tau_servo = F_finger * r_horn
Release-force reduction vs a plain hook = F_c / F_finger.
Requirement: servo stall torque / tau_servo >= 2 at e_max and worst friction.
Robustness: e_min must stay > 0 so the latch never opens under load by itself;
the contact face is a steel dowel (no PETG creep at the contact).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cad import params as P


@dataclass
class Latch:
    R_c: float = P.CATCH_R / 1000
    e: float = 0.0015        # m closing offset (toggle), nominal
    e_tol: float = 0.0005    # +/- from print tolerance (pivot hole + nose dowel hole positions)
    t: float = 0.026         # m contact -> pivot along the normal
    r_roller: float = 0.011
    R_t: float = 0.060       # m latch pivot -> tail contact
    r_horn: float = 0.015    # m servo finger radius
    mu_pin: tuple = (0.15, 0.30, 0.45)   # steel pin in PETG bore: best/nominal/worst
    r_pin: float = 0.002
    M_spring: float = 0.02   # N m latch closing spring
    servo: str = "MG996R"
    servo_stall_Nm: float = 9.4 * 0.0981  # MG996R 9.4 kg.cm @ 4.8 V [P9b]
    mg90s_stall_Nm: float = 1.8 * 0.0981


def analyse(T_cocked: float, s: Latch = Latch()) -> dict:
    F_c = T_cocked / s.R_c
    out = dict(F_catch=F_c)
    for tag, e in (("min_e", s.e - s.e_tol), ("nom", s.e), ("max_e", s.e + s.e_tol)):
        M_close = F_c * e
        tau = {}
        for k, mu in zip(("best", "nom", "worst"), s.mu_pin):
            M_trip = F_c * e + mu * F_c * s.r_pin + s.M_spring
            tau[k] = M_trip / s.R_t * s.r_horn
        F_finger = tau["worst"] / s.r_horn
        out[tag] = dict(e=e, M_close=M_close, F_finger_worst=F_finger, tau_trip=tau,
                        servo_margin_worst=s.servo_stall_Nm / tau["worst"],
                        mg90s_margin_worst=s.mg90s_stall_Nm / tau["worst"],
                        trip_rotation_deg=math.degrees(e / (s.t + s.r_roller)) * 1.0)
    out["self_locking"] = (s.e - s.e_tol) > 0
    out["reduction_vs_direct"] = F_c / out["max_e"]["F_finger_worst"]
    out["plain_hook_servo_force"] = F_c  # a hook pulled straight off the roller
    return out


def safety_pin_load(T_cocked: float, s: Latch = Latch()) -> float:
    """The 6 mm pin passes through the latch tail at R_t: worst case it must hold the
    trip moment if someone forces the servo finger: M_trip(max) / R_t."""
    F_c = T_cocked / s.R_c
    return (F_c * (s.e + s.e_tol) + max(s.mu_pin) * F_c * s.r_pin + s.M_spring) / s.R_t
