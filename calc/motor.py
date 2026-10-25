"""Cocking drive: motor torque-speed line -> cocking time, current, thermal.

Linear brushed-DC model at the gearbox output:
    w = w0 (1 - T/Ts),   I = I0 + (Is - I0) T/Ts
Torque at the motor output shaft while cocking (arm pushed by the dog ring):
    T_m(phi) = [T_spring(phi)(1 + eta_f) - T_grav_arm(phi)] / (N * eta_gear)
(the cup is empty while cocking: FEED happens at the cocked position).
Dog retract (unloaded) runs at no-load speed through (swing + 5 deg).
Thermal: copper loss per cycle E_cu = sum I^2 R dt; the RMS current over the
minimum cycle period must stay below the rated (continuous) current.
"""

from __future__ import annotations

import math

import numpy as np

from calc.design import GEAR_EFF, GEAR_RATIO, MOTOR

G = 9.81
from cad import params as P  # noqa: E402

PRETRAVEL_DEG = P.ABS_STROKE_DEG          # rest (bottomed on absorber) -> release angle
RETRACT_EXTRA_DEG = P.ABS_STROKE_DEG  # ring returns to the parked arm in RESET (not in the latency path)


def cock(model, ratio: float = GEAR_RATIO, motor: dict = MOTOR, dphi: float = 2e-4) -> dict:
    w0 = motor["w0_rpm"] * 2 * math.pi / 60
    Ts, I0, Is, R = motor["stall_torque"], motor["no_load_current"], motor["stall_current"], motor["R_winding"]
    phi, t, e_cu, e_mech = model.swing, 0.0, 0.0, 0.0
    # pre-travel from rest to the release angle at the rest torque (absorber plunger returns)
    T0 = model.spring_torque(model.swing) * (1 + model.eta_f) / (ratio * GEAR_EFF)
    w_pre = w0 * (1 - T0 / Ts) / ratio
    t += math.radians(PRETRAVEL_DEG + P.DOG_GAP_DEG) / w_pre
    e_cu += (I0 + (Is - I0) * T0 / Ts) ** 2 * R * t
    t_hist, Tm_hist, I_hist = [], [], []
    while phi > 0:
        alpha = model.alpha_c - phi
        T_arm = model.spring_torque(phi) * (1 + model.eta_f) \
            + model.m_arm * G * model.l_arm_cg * math.cos(alpha)  # arm weight (cup empty)
        Tm = max(T_arm, 0.0) / (ratio * GEAR_EFF)
        if Tm >= Ts:
            return dict(ok=False, reason="stall", phi_stall=phi)
        w = w0 * (1 - Tm / Ts) / ratio
        dt = dphi / w
        I = I0 + (Is - I0) * Tm / Ts
        t += dt
        e_cu += I * I * R * dt
        e_mech += T_arm * dphi
        phi -= dphi
        t_hist.append(t), Tm_hist.append(Tm), I_hist.append(I)
    t_ret = math.radians(math.degrees(model.swing) + RETRACT_EXTRA_DEG) / (w0 / ratio)
    e_cu += I0 * I0 * R * t_ret
    Tm_arr = np.array(Tm_hist)
    return dict(ok=True, t_cock=t, t_retract=t_ret, Tm_peak=float(Tm_arr.max()),
                Tm_peak_frac_stall=float(Tm_arr.max() / Ts), I_peak=float(max(I_hist)),
                I_mean=float(np.mean(I_hist)), E_cu=e_cu, E_mech=e_mech,
                P_elec_peak=float(max(I_hist)) * motor["v"],
                ring_torque_peak=float(Tm_arr.max() * ratio * GEAR_EFF))


def thermal(c: dict, cycle_s: float = 8.0, motor: dict = MOTOR) -> dict:
    """RMS current over back-to-back cycles vs rated continuous current."""
    i_rms = math.sqrt(c["E_cu"] / motor["R_winding"] / cycle_s)
    return dict(I_rms=i_rms, I_rated=motor["rated_current"], ratio=i_rms / motor["rated_current"])


# Press -> launch latency budget (s). Button: deep-sleep wake + Wi-Fi/ESP-NOW init + TX
T_BUTTON_WAKE_TX = 0.25   # measured ESP32 ~160 ms boot [E5]; +90 ms radio init margin
T_RADIO = 0.01
T_FEED = 0.45             # escapement 0.25 s + roll down chute (sim/feed_sim.py)
T_SEAR_TRIP = 0.08        # MG90S 60 deg in 0.1 s; finger needs ~45 deg
T_SETTLE = 0.05
T_WARN_MIN = 1.5


def latency(c: dict) -> dict:
    # latch rides on the ring: no retract before FIRE; ring returns during RESET
    seq = c["t_cock"] + T_FEED + T_SETTLE
    t_fire_after_warn_start = max(T_WARN_MIN, seq)
    total = T_BUTTON_WAKE_TX + T_RADIO + t_fire_after_warn_start + T_SEAR_TRIP
    return dict(total=total, mech_sequence=seq, warning=t_fire_after_warn_start)


T_RESET_SETTLE = 0.30      # arm settles on the absorber


def cycle_time(c: dict) -> float:
    """Minimum fire -> fire period (operator presses again immediately)."""
    return T_RESET_SETTLE + c["t_retract"] + latency(c)["warning"] + T_SEAR_TRIP
