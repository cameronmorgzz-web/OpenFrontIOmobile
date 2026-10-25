"""Single source of truth for every key dimension and physical constant.

All lengths in millimetres unless the name ends in _m. Masses in kg, forces in N.
calc/, sim/, cad/src and tests/ all import from here, so changing a value here
propagates through the analysis, the simulation and the geometry.

Coordinate frame (launcher): x = throw direction, z = up, y = pivot axis.
Arm angle alpha is measured from +x towards +z (degrees); the arm fires by
rotating towards smaller alpha and is cocked towards larger alpha.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Can (THE parameter for 330 vs 500 ml: CAN_SIZE). Reprint only the magazine.
# --------------------------------------------------------------------------
CAN_SIZE = "330"  # "330" or "500"

CANS = {
    # diameter / length per research/SOURCES.md [C1][C2]; masses [C3]
    "330": dict(d=66.2, l=115.2, mass_full=0.355, mass_empty=0.0125),
    "500": dict(d=66.2, l=168.0, mass_full=0.525, mass_empty=0.0165),
}
CAN = CANS[CAN_SIZE]
CAN_D = CAN["d"]
CAN_L = CAN["l"]
CAN_L_MAX = max(c["l"] for c in CANS.values())  # frame is always sized for the longest can

# --------------------------------------------------------------------------
# Print / fit rules (brief)
# --------------------------------------------------------------------------
CLR_SLIDE = 0.2  # sliding-fit clearance
CLR_PRESS = 0.1  # press-fit interference allowance
WALL_MIN = 1.6
OVERHANG_MAX_DEG = 50.0
BRIDGE_MAX = 30.0
BUILD_VOL = (256.0, 256.0, 256.0)

# Hardware (must match BOM)
M3_CLEAR = 3.4          # M3 clearance hole
M3_INSERT_HOLE = 4.0    # hole for 4.0-4.2 OD x 5.7 insert (insert OD 4.2 -> 0.1 press per side)
M3_INSERT_DEPTH = 6.2   # insert length 5.7 + 0.5
M3_INSERT_OD = 4.2
M3_HEAD_D = 5.5         # DIN 912 socket head
M3_HEAD_H = 3.0
M8_CLEAR = 8.4
BEARING_608 = dict(d=8.0, D=22.0, B=7.0)
BEARING_608_BORE = 22.0 - 0.05  # light press: printed holes shrink ~0.1 mm; tuned via PRINT_GUIDE test print
PIN_SAFETY_D = 6.0      # M6 x 60 safety pin (ring-pull "lynch" style handle printed)
DOWEL_4 = 4.0           # 4 x 20 mm steel dowel (sear pivots, roller axle)

# --------------------------------------------------------------------------
# Launcher geometry
# --------------------------------------------------------------------------
PIVOT_H = 260.0          # pivot axis height above floor
ARM_L = 240.0            # pivot -> can centre
ALPHA_RELEASE_DEG = (134.0, 138.0, 142.0)  # 3 detent positions of the forward stop (launch 44/48/52 deg)
ALPHA_RELEASE_NOMINAL_DEG = 138.0
SWING_DEG = 90.0         # cocked - release (at nominal detent)
ALPHA_COCKED_DEG = ALPHA_RELEASE_NOMINAL_DEG + SWING_DEG

FRAME_INNER_W = CAN_L_MAX + 2 * 6.0   # clear width between the two side plates
SIDE_PLATE_T = 8.0
CUP_W = 100.0            # cradle width (supports both can lengths centred)
CUP_WALL = 4.0
CUP_PAD = 3.0            # TPU liner thickness

# Shock absorber AC1416-1 strikes an ear on the hub; the arm rests bottomed on it
ABS_R = 80.0             # strike radius
ABS_STROKE = 16.0
ABS_STROKE_DEG = ABS_STROKE / ABS_R * 57.29578   # 11.46 deg: rest is this far past release
ALPHA_REST_DEG = ALPHA_RELEASE_NOMINAL_DEG - ABS_STROKE_DEG
DOG_GAP_DEG = 3.0        # parked dog clearance to the hub lug at rest

DRUM_R = 30.0            # spring-cord drum radius on the arm hub (calc/spring_select.py)
HUB_R = 34.0
CATCH_R = 46.0           # radius of the catch roller (608 on M8 pin) on the hub
LATCH_PIVOT_R = 70.0     # ring-latch pivot radius on the ring gear

# Gear (dog ring <- motor pinion)
GEAR_MODULE = 2.0
RING_TEETH = 80          # ratio 5.0 (calc/motor.py: latency optimum, motor <= 80 % stall at 5 m)
PINION_TEETH = 16
GEAR_FACE = 34.0         # wide face: pinion Lewis fatigue SF >= 2.5 (calc/stress.py)
GEAR_CENTRE = GEAR_MODULE * (RING_TEETH + PINION_TEETH) / 2  # 98 mm

# --------------------------------------------------------------------------
# Materials (anisotropic PETG, research/SOURCES.md [M*])
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Material:
    name: str
    rho: float          # kg/m^3
    E_xy: float         # MPa
    E_z: float          # MPa
    sut_xy: float       # MPa  tensile strength in-plane
    sut_z: float        # MPa  tensile strength across layers
    nu: float = 0.38
    fatigue_ratio_1e3: float = 0.6   # S at 1e3 cycles / UTS (derating)
    creep_limit_ratio: float = 0.25  # sustained stress limit / UTS


PETG = Material("PETG (Bambu PETG HF, printed)", rho=1270, E_xy=1800.0, E_z=1500.0,
                sut_xy=34.0, sut_z=19.0)
TPU95 = Material("TPU 95A", rho=1220, E_xy=26.0, E_z=26.0, sut_xy=26.0, sut_z=15.0, nu=0.45)

SF_REQUIRED = 2.5

# --------------------------------------------------------------------------
# Springs (selected in DECISIONS.md / calc/spring_select.py)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ExtSpring:
    part: str
    d_wire: float     # mm
    od: float         # mm
    l0: float         # free length incl. hooks, mm
    rate: float       # N/mm
    f0: float         # initial tension, N
    f_max: float      # max permissible load, N
    s_max: float      # max permissible extension, mm
    source: str
    price_eur: float = 0.0


# Gutekunst Federn Z-141HI, EN 10270-1 spring steel, all values published on the
# part page (research/SOURCES.md [P6a]). Three in parallel between two rigid yokes.
SPRING = ExtSpring(part="Gutekunst Z-141HI", d_wire=2.0, od=16.0, l0=121.0, rate=1.2,
                   f0=14.5, f_max=166.7, s_max=126.84,
                   source="https://www.federnshop.com/en/products/extension_springs/z-141hi.html",
                   price_eur=2.93)
N_SPRINGS = 3
SPRING_MASS = 0.030      # kg each (2 mm wire, ~28 active coils x pi x 14 mm x 24.7 g/m)
SPRING_LOAD_LIMIT = 0.85  # max fraction of Fn used at the 5 m setting (fatigue margin)
PRELOAD_ADJ_RANGE = (0.0, 70.0)  # mm of anchor travel on the two M6 adjuster rods

# Cord: Dyneema SK78 2 mm braided cord (break ~2.4 kN typ.), used single strand
CORD_D = 2.0
CORD_BREAK_N = 2400.0

# --------------------------------------------------------------------------
# Button
# --------------------------------------------------------------------------
BTN_OD = 78.0
BTN_H = 46.0
BTN_CAP_D = 62.0
BTN_CAP_TRAVEL = 4.0
BTN_SWITCH_D = 16.0     # 16 mm metal momentary switch, panel hole 16.2
LIPO = dict(name="503035", l=35.0, w=30.0, t=5.0, mah=500)
