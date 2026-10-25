"""Hand stress checks for every loaded part (anisotropic PETG).

Each check returns stress, the strength in the governing print direction, and
SF = strength / stress (static) plus, where the load cycles, a fatigue SF using
S_f = fatigue_ratio * UTS at the design life, and a creep SF for sustained loads
using creep_limit_ratio * UTS. Requirement: min(SF) >= 2.5 (brief).

Print orientation (PRINT_GUIDE.md) decides which strength applies:
  arm, hub, sear, gear, side plates, cup, base: loads act in the print XY plane -> sut_xy
  bosses whose load pulls layers apart (noted per check) -> sut_z
Sections are the as-printed shells (walls + skins), infill ignored (conservative).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cad import params as P

G = 9.81
PETG = P.PETG


@dataclass
class Check:
    part: str
    case: str
    formula: str
    load: str
    stress: float          # MPa
    direction: str         # "xy" | "z" | "steel" | "line"
    strength: float        # MPa (or N for line/hardware)
    sf_static: float
    sf_fatigue: float | None = None
    sf_creep: float | None = None

    @property
    def sf(self) -> float:
        vals = [self.sf_static] + [v for v in (self.sf_fatigue, self.sf_creep) if v is not None]
        return min(vals)


def _sut(direction: str) -> float:
    return PETG.sut_xy if direction == "xy" else PETG.sut_z


def petg(part, case, formula, load, stress, direction="xy", cyclic=True, sustained=None):
    s = _sut(direction)
    sf_f = (PETG.fatigue_ratio_1e3 * s / stress) if cyclic else None
    sf_c = (PETG.creep_limit_ratio * s / sustained) if sustained else None
    return Check(part, case, formula, load, stress, direction, s, s / stress, sf_f, sf_c)


def hollow_rect_Z(h, b, t_wall, t_skin):
    """Section modulus about the axis parallel to b (bending in the h direction)."""
    I = (b * h ** 3 - (b - 2 * t_skin) * (h - 2 * t_wall) ** 3) / 12
    return I / (h / 2)


def rect_Z(h, b):
    return b * h * h / 6


# ---------------------------------------------------------------------------
# Geometry used by the checks (mirrors cad/src parts; asserted in tests)
# ---------------------------------------------------------------------------
ARM_ROOT_R = 0.045         # m, where the beam leaves the hub
ARM_BEAM_H, ARM_BEAM_B = 42.0, 28.0   # mm in-plane height, thickness along y
ARM_WALLS = 6 * 0.45       # 6 perimeters
SKIN = 5 * 0.2             # 5 top/bottom layers
ABS_R = 0.080              # m absorber strike radius on the hub
ABS_STROKE = 0.016         # m AC1416
ABS_ENERGY_MAX = 20.0      # J per cycle (AC1416-x) [P21]
ABS_V_MAX = 2.6            # m/s (-1 variant) [P21]
ABS_SHAPE = 1.3            # peak/mean force of a self-compensating absorber (est.)
SHAFT_D = 8.0              # mm hardened GCr15 linear rod
SHAFT_SPAN = (P.FRAME_INNER_W + P.SIDE_PLATE_T) / 1000
HUB_BEARING_SPAN = 0.050   # m between the two hub 608 bearings
SHAFT_SY = 1200.0          # MPa yield, through-hardened GCr15 (conservative vs ~1700)


def run(st5, st4, cock_ring_torque, gear_force_t, mp) -> list[Check]:
    """st5/st4: design.setting() dicts at 5 m / 4 m. mp: mass props dict."""
    out: list[Check] = []
    m5, s5 = st5["model"], st5["swing"]
    T_cock5 = m5.spring_torque(0.0)                  # N m at the cocked position
    T_rest5 = m5.spring_torque(m5.swing)            # sustained at rest (on the absorber)
    F_cord5 = m5.n_springs * m5.spring_force(0.0)   # N
    F_cord_rest5 = m5.n_springs * m5.spring_force(m5.swing)
    I_bc = mp["I_beam_cup"]

    # 1 Arm root bending during the swing (can reaction at L) -------------------
    Zb = hollow_rect_Z(ARM_BEAM_H, ARM_BEAM_B, ARM_WALLS, SKIN)
    F_t = m5.m_can * s5.a_tan_peak + m5.m_can * G
    M_swing = F_t * (m5.L - ARM_ROOT_R) + I_bc * s5.a_tan_peak / m5.L
    out.append(petg("arm", "swing, 5 m", "M=(m a_t+mg)(L-r_root)+I_bc*phidd; s=M/Z",
                    f"F_t={F_t:.0f} N, M={M_swing:.1f} N m, Z={Zb:.0f} mm3", M_swing * 1e3 / Zb))

    # 2 Arm root during the absorber stop (normal shot; can already gone) --------
    E_arm = s5.energy_arm_kin + T_rest5 * ABS_STROKE / ABS_R
    F_abs = ABS_SHAPE * E_arm / ABS_STROKE
    dec = (F_abs * ABS_R + T_rest5) / mp["I_arm"]
    M_stop = I_bc * dec
    out.append(petg("arm", "absorber stop, 5 m", "phidd=(F_abs r_a+T_s)/I_arm; M=I_beamcup*phidd",
                    f"E={E_arm:.2f} J, F_abs={F_abs:.0f} N, M={M_stop:.1f} N m", M_stop * 1e3 / Zb))

    # 3 Dry fire (accidental; firmware + can sensor prevent it) ------------------
    E_dry = s5.energy_spring * (1 - m5.eta_f) - s5.energy_grav + T_rest5 * ABS_STROKE / ABS_R \
        + m5.m_can * G * 0  # can absent
    F_dry = ABS_SHAPE * E_dry / ABS_STROKE
    I_dry = mp["I_arm"] + m5.n_springs * m5.m_spring / 3 * m5.r_d ** 2
    M_dry = I_bc * (F_dry * ABS_R + T_rest5) / I_dry
    c = petg("arm", "DRY FIRE (accidental), 5 m", "as stop, all spring energy into absorber",
             f"E={E_dry:.1f} J (absorber max {ABS_ENERGY_MAX} J), M={M_dry:.1f} N m", M_dry * 1e3 / Zb,
             cyclic=False)
    out.append(c)

    # 4 Cup floor: centripetal load of the can at release (500 ml worst case) ----
    m500 = P.CANS["500"]["mass_full"]
    F_cen = m500 * s5.v_release ** 2 / m5.L
    # floor plate 80 wide, 5 mm thick, supported by back wall + side ribs: cantilever 33 mm
    M_cup = F_cen * 0.033 / 2
    out.append(petg("cup", "centripetal, 500 ml can @5 m speed", "M=F*a/2 on 80x5 plate",
                    f"F={F_cen:.0f} N", M_cup * 1e3 / rect_Z(5.0, 80.0)))

    # 5 Hub bearing seats (2 x 608 in PETG hub) at the cocked position ----------
    F_latch = T_cock5 / (P.CATCH_R / 1000)
    F_hub = math.hypot(F_cord5, F_latch)  # cord ~vertical, latch force ~tangential at cocked
    p_seat = F_hub / 2 / (22.0 * 7.0)
    out.append(petg("hub", "bearing seat, cocked 5 m", "p=F/(2 D B)", f"F={F_hub:.0f} N",
                    p_seat, sustained=None))

    # 6 Shaft bending (steel) ---------------------------------------------------
    a = (SHAFT_SPAN - HUB_BEARING_SPAN) / 2
    M_sh = F_hub / 2 * a
    s_sh = 32 * M_sh / (math.pi * (SHAFT_D / 1000) ** 3) / 1e6
    out.append(Check("pivot shaft", "cocked 5 m", "M=F/2*a; s=32M/(pi d^3)", f"F={F_hub:.0f} N, a={a*1e3:.0f} mm",
                     s_sh, "steel", SHAFT_SY, SHAFT_SY / s_sh))

    # 7 Side plate shaft boss (pin bearing in PETG, load in plate plane) ---------
    boss_t = 16.0
    out.append(petg("side plate", "shaft boss bearing, cocked 5 m", "p=(F/2)/(d t_boss)",
                    f"F/2={F_hub/2:.0f} N", F_hub / 2 / (SHAFT_D * boss_t)))
    # side plate root (cantilever from base, horizontal shaft load component)
    M_pl = F_latch / 2 * (P.PIVOT_H - 30) / 1000
    out.append(petg("side plate", "root bending, cocked 5 m", "M=F_h/2*h; Z=t L^2/6 (L=230)",
                    f"F_h/2={F_latch/2:.0f} N", M_pl * 1e3 / rect_Z(230.0, P.SIDE_PLATE_T)))

    # 8 Gear teeth (Lewis, no velocity factor: v<0.2 m/s) -------------------------
    m_mod, b = P.GEAR_MODULE, P.GEAR_FACE
    Y = {14: 0.277, 16: 0.296, 80: 0.43, 84: 0.43}
    s_pin = gear_force_t / (b * m_mod * Y[P.PINION_TEETH])
    s_ring = gear_force_t / (b * m_mod * Y[P.RING_TEETH])
    out.append(petg("motor pinion", "peak cocking torque", "Lewis s=Ft/(b m Y)", f"Ft={gear_force_t:.0f} N",
                    s_pin))
    out.append(petg("dog ring gear", "peak cocking torque", "Lewis s=Ft/(b m Y)", f"Ft={gear_force_t:.0f} N",
                    s_ring))
    # ring latch: nose bending (cantilever 8 mm from the hook root), 14 (tangential) x 7 (y) is
    # too thin, so the lever is 12 mm thick in y and the nose 14 mm deep
    F_c = T_cock5 / (P.CATCH_R / 1000)
    # latch is 10 mm thick (y) in the slab next to the ring; nose carries a 4 mm steel dowel
    out.append(petg("ring latch", "nose bending, cocked 5 m", "M=F_c*8mm; Z=b h^2/6 (b=10 y, h=18)",
                    f"F_c={F_c:.0f} N", F_c * 8 / rect_Z(18.0, 10.0)))
    out.append(petg("ring latch", "pivot hole bearing (4 mm dowel, 10 mm)", "p=F/(d t)", f"F={F_c:.0f} N",
                    F_c / (4.0 * 10.0)))
    out.append(petg("ring latch", "nose dowel hole bearing (4 mm dowel, 10 mm)", "p=F/(d t)", f"F={F_c:.0f} N",
                    F_c / (4.0 * 10.0)))
    # ring-latch pivot pin boss in the ring gear: the 4 mm dowel loads the ring in-plane
    out.append(petg("dog ring gear", "latch-pin boss (pin in 2 cheeks, 2 x 8 mm)", "p=F/(2 d t)",
                    f"F={F_c:.0f} N", F_c / (2 * 4.0 * 8.0)))
    F_sear = F_c

    # 10 Spring anchor wall in base_rear (two M6 rods through a 10 mm wall) ---------
    F_each_rod = F_cord5 / 2
    out.append(petg("base rear", "M6 adjuster rod bearing on anchor wall, cocked 5 m", "p=F/(d t)",
                    f"F={F_each_rod:.0f} N", F_each_rod / (6.0 * 10.0),
                    sustained=F_cord_rest5 / 2 / (6.0 * 10.0)))
    out.append(petg("base rear", "anchor wall shear-out", "tau=F/(2 e t), e=12 mm edge distance",
                    f"F={F_each_rod:.0f} N", F_each_rod / (2 * 12.0 * 10.0) * math.sqrt(3),
                    sustained=F_cord_rest5 / 2 / (2 * 12.0 * 10.0) * math.sqrt(3)))
    # yoke (printed, 3 spring hooks on a 4 mm steel dowel, carried by 2 M6 rods 40 mm apart)
    M_yoke = F_cord5 / 2 * 0.020
    out.append(petg("spring yoke", "bending between rods", "M=F/2*20mm, 22x16 section",
                    f"F={F_cord5:.0f} N", M_yoke * 1e3 / rect_Z(16.0, 22.0),
                    sustained=F_cord_rest5 / 2 * 0.020 * 1e3 / rect_Z(16.0, 22.0)))

    # 11 Redirect pulley cheeks (608 on M8 bolt, base_front) ----------------------
    F_pul = math.sqrt(2) * F_cord5
    out.append(petg("base front", "redirect pulley cheeks (2 x 8 mm)", "p=F/(2 d t)", f"F={F_pul:.0f} N",
                    F_pul / (2 * 8.0 * 8.0), sustained=math.sqrt(2) * F_cord_rest5 / (2 * 8.0 * 8.0)))

    # 12 Absorber bracket (M14 nut clamp in printed bracket; load along the absorber axis,
    #    bracket printed so the load is in-plane), sustained = rest preload on the bottomed absorber
    F_abs_rest = T_rest5 / ABS_R
    out.append(petg("stop bracket", "absorber reaction, 5 m shot", "s=F/A_net, A_net=2x(10x12)",
                    f"F={F_abs:.0f} N peak", F_abs / (2 * 10 * 12),
                    sustained=F_abs_rest / (2 * 10 * 12)))
    out.append(petg("stop bracket", "DRY FIRE", "s=F/A_net", f"F={F_dry:.0f} N", F_dry / (2 * 10 * 12),
                    cyclic=False))

    # 13 Cord and hardware -------------------------------------------------------
    out.append(Check("Dyneema cord 2 mm", "cocked 5 m", "T=n F", f"T={F_cord5:.0f} N",
                     F_cord5, "line", P.CORD_BREAK_N, P.CORD_BREAK_N / F_cord5))
    spring_frac = m5.spring_force(0.0) / P.SPRING.f_max
    # springs: not a printed part; criterion is F <= SPRING_LOAD_LIMIT*Fn (Gate 2), reported separately
    _ = spring_frac
    return out, dict(T_cock5=T_cock5, T_rest5=T_rest5, F_cord5=F_cord5, F_sear5=F_sear, F_hub=F_hub,
                     E_dry=E_dry, F_abs=F_abs, F_dry=F_dry, abs_impact_v=s5.omega * ABS_R)
