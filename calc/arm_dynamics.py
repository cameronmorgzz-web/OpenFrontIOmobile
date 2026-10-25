"""Spring -> arm -> can energy chain (1-DOF, analytical ODE).

Generalised coordinate: phi = alpha_cocked - alpha  (0 at cocked, swing at release).

    I(phi) phi'' = T_spring(phi) * (1 - eta_f) - dV/dphi - T_aero
    T_spring    = N * F(x) * r_d                 (cord on drum, equaliser -> N springs)
    F(x)        = F0 + k * x                     (extension spring, x = extension)
    x(phi)      = x_rest + r_d * (swing - phi)   (x_rest = preload extension at rest)
    dV/dphi     = -(m_c L + m_a l_a) g cos(alpha)
    T_aero      = 1/2 rho Cd A (phi' L)^2 L      (can drag during the swing)

Effective inertia about the pivot:
    I = I_arm + m_c L^2 + I_can_spin + N * (m_spring/3) * r_d^2 + I_equaliser
The can leaves the cup at the forward stop with v = phi' L, spin = phi'.
Energy bookkeeping is returned so the efficiency is explicit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

G = 9.81


@dataclass
class ArmModel:
    L: float = 0.240            # m pivot -> can centre
    r_d: float = 0.040          # m drum radius
    swing_deg: float = 90.0
    alpha_release_deg: float = 138.0
    m_can: float = 0.355
    can_r: float = 0.0331
    can_spin_frac: float = 0.15  # fraction of can mass that spins with the shell (liquid lags) [A4]
    I_arm: float = 0.0060        # kg m^2 arm + cup + hub + pad about pivot (CAD, cad/mass_props.json)
    m_arm: float = 0.30          # kg moving arm assembly
    l_arm_cg: float = 0.120      # m pivot -> arm CG
    n_springs: int = 2
    k: float = 1.0               # N/mm per spring
    f0: float = 10.0             # N initial tension
    m_spring: float = 0.025      # kg each
    x_rest: float = 0.020        # m preload extension at rest
    eta_f: float = 0.05          # fraction of spring torque lost to friction (cord, pulleys, hysteresis)
    cd_can: float = 0.8
    area_can: float = 0.0662 * 0.1152

    @property
    def swing(self) -> float:
        return math.radians(self.swing_deg)

    @property
    def alpha_c(self) -> float:
        return math.radians(self.alpha_release_deg + self.swing_deg)

    def inertia(self) -> float:
        I_spin = self.can_spin_frac * 0.5 * self.m_can * self.can_r ** 2
        I_spr = self.n_springs * self.m_spring / 3 * self.r_d ** 2
        return self.I_arm + self.m_can * self.L ** 2 + I_spin + I_spr

    def extension(self, phi: float) -> float:
        return self.x_rest + self.r_d * (self.swing - phi)

    def spring_force(self, phi: float) -> float:
        """Force per spring, N."""
        return self.f0 + self.k * 1000.0 * self.extension(phi)

    def spring_torque(self, phi: float) -> float:
        return self.n_springs * self.spring_force(phi) * self.r_d

    def grav_torque(self, phi: float) -> float:
        """dV/dphi (positive = gravity resists firing)."""
        a = self.alpha_c - phi
        return -(self.m_can * self.L + self.m_arm * self.l_arm_cg) * G * math.cos(a)

    def stored_energy(self) -> float:
        """Spring energy released between cocked and rest, J."""
        x1, x0 = self.extension(0.0), self.extension(self.swing)
        k = self.k * 1000.0
        return self.n_springs * (self.f0 * (x1 - x0) + 0.5 * k * (x1 ** 2 - x0 ** 2))


@dataclass
class SwingResult:
    v_release: float
    omega: float
    t_swing: float
    a_peak: float        # peak can acceleration magnitude, m/s^2
    a_tan_peak: float
    a_cen_release: float
    energy_spring: float
    energy_can_kin: float
    energy_arm_kin: float
    energy_grav: float
    energy_friction: float
    min_back_wall_force: float  # N, must stay > 0 (can stays in cup until the stop)
    t: np.ndarray
    phi: np.ndarray
    phid: np.ndarray

    @property
    def efficiency(self) -> float:
        return self.energy_can_kin / self.energy_spring


def simulate_swing(m: ArmModel, dt_out: float = 1e-4) -> SwingResult:
    I = m.inertia()
    rho = 1.2

    def rhs(_t, y):
        phi, w = y
        T = m.spring_torque(phi) * (1 - m.eta_f) - m.grav_torque(phi)
        T -= 0.5 * rho * m.cd_can * m.area_can * (w * m.L) ** 2 * m.L
        return [w, T / I]

    def done(_t, y):
        return y[0] - m.swing
    done.terminal = True
    done.direction = 1

    sol = solve_ivp(rhs, (0, 2.0), [0.0, 0.0], events=done, max_step=dt_out, rtol=1e-9, atol=1e-12)
    if sol.t_events[0].size == 0:
        raise RuntimeError("arm never reached the stop (spring too weak for gravity)")
    t, phi, w = sol.t, sol.y[0], sol.y[1]
    acc = np.array([rhs(ti, [p, wi])[1] for ti, p, wi in zip(t, phi, w)])
    a_tan = acc * m.L
    a_cen = w ** 2 * m.L
    alpha = m.alpha_c - phi
    # back-wall normal force: N = m L phi'' - m g cos(alpha)
    n_back = m.m_can * (a_tan - G * np.cos(alpha))
    omega = float(w[-1])
    E_s = m.stored_energy()
    E_can = 0.5 * m.m_can * (omega * m.L) ** 2
    E_tot_kin = 0.5 * I * omega ** 2
    a_c, a_r = m.alpha_c, m.alpha_c - m.swing
    E_g = (m.m_can * m.L + m.m_arm * m.l_arm_cg) * G * (math.sin(a_r) - math.sin(a_c))
    return SwingResult(
        v_release=omega * m.L, omega=omega, t_swing=float(t[-1]),
        a_peak=float(np.max(np.hypot(a_tan, a_cen))), a_tan_peak=float(np.max(a_tan)),
        a_cen_release=float(a_cen[-1]), energy_spring=E_s, energy_can_kin=E_can,
        energy_arm_kin=E_tot_kin - E_can, energy_grav=E_g,
        energy_friction=E_s - E_tot_kin - E_g,
        min_back_wall_force=float(np.min(n_back[t > 0.002])) if t[-1] > 0.002 else float(n_back[-1]),
        t=t, phi=phi, phid=w)


def preload_for_speed(m: ArmModel, v_target: float, lo=0.0, hi=0.12) -> float:
    """Rest preload extension x_rest (m) giving release speed v_target."""
    def f(x):
        try:
            return simulate_swing(replace(m, x_rest=x)).v_release - v_target
        except RuntimeError:  # too weak to reach the stop -> treat as zero speed
            return -v_target
    return brentq(f, lo, hi, xtol=1e-6)
