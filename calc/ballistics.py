"""Can flight with quadratic drag and Magnus force (2-D, x forward, z up).

Equations (point mass, broadside cylinder spinning about its own axis):
    m dv/dt = -1/2 rho Cd A |v| v  +  1/2 rho CL A |v| (n x v)/|v| * sign  -  m g z_hat
A = D * L (broadside area; constant because spin is about the can axis, which
stays parallel to the arm pivot - see DECISIONS.md D3). CL>0 means force
towards -z for top-spin (the arm imparts top-spin; Magnus pushes down).

Closed-form vacuum results used as a check:
    v0^2 = g (dh + sqrt(R^2 + dh^2))   minimum launch speed to reach (R, dh)
    v_catch^2 = v0^2 - 2 g dh
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, minimize_scalar

G = 9.81
RHO_AIR = 1.20  # kg/m^3 at 20 C, sea level (Milan ~120 m: 1.19)


@dataclass
class Aero:
    cd: float = 0.80   # finite cylinder broadside, L/D~1.7, Re~3e4 [A1]
    cl: float = 0.10   # Magnus coeff at spin ratio ~0.14 (uncertain, MC 0..0.25) [A3]
    area: float = 0.0662 * 0.1152  # m^2
    mass: float = 0.355


@dataclass
class Shot:
    range_m: float
    t_flight: float
    v_catch: float
    peak_z: float
    v0: float
    angle_deg: float
    traj: np.ndarray | None = None


def fly(v0: float, angle_deg: float, h0: float, aero: Aero, h_catch: float = 0.9,
        keep: bool = False) -> Shot:
    """Integrate until the can descends through h_catch."""
    k_d = 0.5 * RHO_AIR * aero.cd * aero.area / aero.mass
    k_l = 0.5 * RHO_AIR * aero.cl * aero.area / aero.mass

    def rhs(_t, y):
        _x, _z, vx, vz = y
        v = math.hypot(vx, vz)
        # drag opposite v; Magnus perpendicular, (vz, -vx) direction = downward for top-spin
        ax = -k_d * v * vx + k_l * v * vz
        az = -k_d * v * vz - k_l * v * vx - G
        return [vx, vz, ax, az]

    def hit(_t, y):
        return y[1] - h_catch
    hit.terminal = True
    hit.direction = -1

    a = math.radians(angle_deg)
    y0 = [0.0, h0, v0 * math.cos(a), v0 * math.sin(a)]
    sol = solve_ivp(rhs, (0, 5), y0, events=hit, max_step=0.005, rtol=1e-8, atol=1e-10,
                    dense_output=False)
    if sol.t_events[0].size == 0:  # never reached catch height descending
        return Shot(float("nan"), float("nan"), float("nan"), float(np.max(sol.y[1])), v0, angle_deg)
    ye = sol.y_events[0][0]
    return Shot(range_m=float(ye[0]), t_flight=float(sol.t_events[0][0]),
                v_catch=float(math.hypot(ye[2], ye[3])), peak_z=float(np.max(sol.y[1])),
                v0=v0, angle_deg=angle_deg, traj=sol.y if keep else None)


def speed_for_range(R: float, angle_deg: float, h0: float, aero: Aero, h_catch=0.9) -> float:
    f = lambda v: fly(v, angle_deg, h0, aero, h_catch).range_m - R  # noqa: E731
    return brentq(lambda v: np.nan_to_num(f(v), nan=-R), 3.0, 15.0, xtol=1e-6)


def min_catch_speed_angle(R: float, h0: float, aero: Aero, h_catch=0.9) -> Shot:
    """Angle that minimises catch speed for range R (== min launch energy)."""
    def obj(a):
        v = speed_for_range(R, a, h0, aero, h_catch)
        return fly(v, a, h0, aero, h_catch).v_catch
    res = minimize_scalar(obj, bounds=(35, 65), method="bounded", options={"xatol": 0.05})
    v = speed_for_range(R, res.x, h0, aero, h_catch)
    return fly(v, res.x, h0, aero, h_catch, keep=True)


def vacuum_min(R: float, dh: float) -> tuple[float, float, float]:
    v0 = math.sqrt(G * (dh + math.hypot(R, dh)))
    vc = math.sqrt(v0 ** 2 - 2 * G * dh)
    ang = math.degrees(math.atan(v0 ** 2 / (G * R)))
    return v0, vc, ang


def max_range_for_catch_speed(vc: float, dh: float) -> float:
    """Vacuum: largest R reachable with catch speed <= vc (minimum-energy shot)."""
    s = vc ** 2 / G + dh
    return math.sqrt(s * s - dh * dh)
