"""Button: battery life budget and cap spring force.

Battery life:
    Q_day = I_sleep * 24 h + n_press * (I_awake * t_awake + I_tx * t_tx)
            + haptic + LED + self-discharge
    life  = C_usable / Q_day
Cap force: 4 compression springs in parallel + the switch's own spring:
    F = 4 * k_s * (preload + travel) + F_switch
k_s from the coil formula k = G d^4 / (8 D^3 n_a) when only geometry is
published (assortment box), with measurement procedure in CALIBRATION.md.
"""

from __future__ import annotations

# Current budget (sources: research/SOURCES.md [E1]-[E8])
SLEEP = {
    "ESP32-C3 chip deep sleep (RTC timer off, GPIO wake)": 5e-6,     # datasheet [E1]
    "ME6211 LDO quiescent (SuperMini)": 40e-6,                        # 30-60 uA [E3]
    "TP4056+DW01A board, battery side (no USB)": 5e-6,                # <2 + ~3 uA [E6]
    "Battery divider 2 x 1 MOhm": 4.0 / 2e6,                          # 2.0 uA at 4.0 V
    "Switch pull-up 1 MOhm (open switch)": 0.0,
    "Haptic NPN / LED leakage": 0.2e-6,
}
SLEEP_NOTE = "SuperMini red power LED must be desoldered (it draws ~1 mA otherwise) [E2]"

AWAKE_MS = 250.0          # boot + radio init + TX + wait for ACK (firmware/README budget)
I_AWAKE = 0.085           # A average (CPU 160 MHz + RX listening 84-87 mA) [E4]
TX_MS = 3 * 1.0           # up to 3 frames of ~1 ms at ~300 mA [E4]
I_TX = 0.30
HAPTIC_MS, I_HAPTIC = 80.0, 0.075       # 10 mm coin motor 3 V ~75 mA
LED_MS, I_LED = 150.0, 0.005
SELF_DISCHARGE_PER_MONTH = 0.05         # LiPo 3-10 %/month, budget 5 % [E7]
CAPACITY_MAH = 500.0
USABLE_FRACTION = 0.80                  # 4.2 V -> 3.45 V cut-off, ageing


def battery_life(presses_per_day: float = 5.0, capacity_mah: float = CAPACITY_MAH) -> dict:
    i_sleep = sum(SLEEP.values())
    q_sleep = i_sleep * 24 * 3600  # C/day
    q_press = (I_AWAKE * AWAKE_MS + I_TX * TX_MS + I_HAPTIC * HAPTIC_MS + I_LED * LED_MS) / 1000
    q_day = q_sleep + presses_per_day * q_press
    mah_day = q_day / 3.6
    usable = capacity_mah * USABLE_FRACTION
    sd_mah_day = capacity_mah * SELF_DISCHARGE_PER_MONTH / 30.4
    days = usable / (mah_day + sd_mah_day)
    return dict(I_sleep_uA=i_sleep * 1e6, mAh_per_day_sleep=q_sleep / 3.6, mAh_per_press=q_press / 3.6,
                mAh_per_day=mah_day, self_discharge_mAh_day=sd_mah_day, days=days, months=days / 30.4)


# Cap springs: 4 x compression spring from the assortment, 0.5 mm wire, OD 10 mm, L0 15 mm,
# 6 active coils (spec printed on the assortment box/listing). Music wire G = 79 GPa.
CAP_SPRING = dict(d=0.5, D=10.0 - 0.5, na=6.0, L0=15.0, G=79e3)
CAP_INSTALLED = 13.5   # mm installed height (cap at rest) -> 1.5 mm preload stops cap rattle
CAP_TRAVEL = 3.0       # mm hard stop (params.BTN_CAP_TRAVEL); 1.5 mm free travel, contact at ~2.3 mm
SWITCH_FORCE = 2.5     # N, 16 mm metal momentary: not published -> measured in CALIBRATION.md


def coil_rate(d, D, na, G) -> float:
    return G * d ** 4 / (8 * D ** 3 * na)


def cap_force() -> dict:
    k = coil_rate(CAP_SPRING["d"], CAP_SPRING["D"], CAP_SPRING["na"], CAP_SPRING["G"])
    pre = CAP_SPRING["L0"] - CAP_INSTALLED
    f_rest = 4 * k * pre
    f_actuate = 4 * k * (pre + 2.3) + SWITCH_FORCE
    f_bottom = 4 * k * (pre + CAP_TRAVEL) + SWITCH_FORCE
    solid = CAP_SPRING["d"] * (CAP_SPRING["na"] + 2)
    return dict(k_each=k, F_rest=f_rest, F_actuate=f_actuate, F_bottom=f_bottom,
                solid_len=solid, min_len=CAP_INSTALLED - CAP_TRAVEL)
