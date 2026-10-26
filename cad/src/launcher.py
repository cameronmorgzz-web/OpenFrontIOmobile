"""Launcher parts (build123d), parametric from cad/params.py.

Frames
------
Assembly: x forward (throw direction), y = pivot axis (left = -y), z up, floor z = 0.
Pivot axis at (x=0, z=PIVOT_H).
Arm-hub frame: built with the arm pointing along +x (alpha = 0), then rotated by alpha.
Ring frame: built with the catch roller at frame angle 0 (latched geometry), then
rotated by psi. psi_cocked puts the latch tail at the trip servo.

Every builder returns a build123d Part in assembly coordinates for a given state.
`PARTS` lists every printed part with material, print orientation and settings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

import build123d as bd

from cad import params as P
from cad.src import geom as G
from cad.src.geom import box, circle, circles_hull, polar, rect, slab, xcyl, ycyl, zcyl

PZ = P.PIVOT_H
G.PIVOT = (0.0, PZ)

# ---------------------------------------------------------------------------
# Kinematic angles (deg)
# ---------------------------------------------------------------------------
A_RELEASE = P.ALPHA_RELEASE_NOMINAL_DEG                  # 138: absorber contact, can leaves
A_REST = P.ALPHA_REST_DEG                                # 126.5: bottomed on the absorber
A_COCKED = P.ALPHA_COCKED_DEG                            # 228
PSI_COCKED = -27.2                                       # ring frame rotation when cocked
BETA_CATCH = PSI_COCKED - A_COCKED                       # catch pin angle on the hub
BETA_CATCH = (BETA_CATCH + 180) % 360 - 180              # -> 104.8
PSI_PARK = PSI_COCKED - (A_COCKED - A_REST) - P.DOG_GAP_DEG   # -131.7
ABS_CONTACT_DEG = 15.0                                   # absolute angle of the absorber tip
BETA_ABS_FACE = ABS_CONTACT_DEG - A_RELEASE              # -123 on the hub
CORD_EXIT_DEG = 0.0                                      # cord leaves the drum at the front, going down

# ring-latch geometry in the ring frame (roller centre at (CATCH_R, 0)), see calc/latch.py
_n = (math.cos(math.radians(-50)), math.sin(math.radians(-50)))           # contact normal (roller -> latch)
_p = (-_n[1], _n[0]) if False else (0.766, 0.643)                         # opening direction of the nose
ROLLER_R = 11.0
CONTACT = (P.CATCH_R + ROLLER_R * _n[0], ROLLER_R * _n[1])
LATCH_T = 26.0
LATCH_O = (CONTACT[0] + LATCH_T * _n[0] + P.LATCH_E * _p[0], CONTACT[1] + LATCH_T * _n[1] + P.LATCH_E * _p[1])
NOSE_DOWEL = (CONTACT[0] + 2.0 * _n[0], CONTACT[1] + 2.0 * _n[1])
_u = (math.cos(math.radians(-21.1 + 90)), math.sin(math.radians(-21.1 + 90)))  # tail direction (+alpha tangent)
LATCH_RT = 60.0
LATCH_TAIL = (LATCH_O[0] + LATCH_RT * _u[0], LATCH_O[1] + LATCH_RT * _u[1])
LATCH_PINHOLE = (LATCH_O[0] + 42 * _u[0], LATCH_O[1] + 42 * _u[1])        # safety-pin hole in the tail

RING_R = P.GEAR_MODULE * P.RING_TEETH / 2       # 100 pitch radius
RING_TIP = RING_R + P.GEAR_MODULE
RING_ROOT = RING_R - 1.25 * P.GEAR_MODULE
PINION_R = P.GEAR_MODULE * P.PINION_TEETH / 2
MOTOR_ANGLE = 280.0
MOTOR_C = polar(RING_R + PINION_R, MOTOR_ANGLE)  # rel. pivot

SHAFT_D = 8.0
Y_IN = P.Y_PLATE_IN            # 90
T_PL = P.SIDE_PLATE_T          # 8
BASE_H = 30.0
BASE_W = 220.0
BASE_FRONT_X = (-125.0, 125.0)
BASE_REAR_X = (-375.0, -125.0)
PLATE_X = (-122.0, 118.0)

# Magazine geometry (rel. pivot), see DECISIONS.md D7
CUP_SEAT_COCKED = polar(P.ARM_L, A_COCKED)                      # can centre in the cup, cocked
FEED_DIR = 150.0                                                # chute direction from the cup up to the magazine
CAN1_T = 190.0          # can1 (next to feed) distance from the cup seat along the chute (>= 15 mm sweep clearance)
CAN_PITCH = P.CAN_D + 0.3
_fd = (math.cos(math.radians(FEED_DIR)), math.sin(math.radians(FEED_DIR)))
CAN1 = (CUP_SEAT_COCKED[0] + CAN1_T * _fd[0], CUP_SEAT_COCKED[1] + CAN1_T * _fd[1])
CAN2 = (CAN1[0] + CAN_PITCH * _fd[0], CAN1[1] + CAN_PITCH * _fd[1])
CAN_GAP = 0.3
MAG_XC = CAN2[0]          # vertical column sits above can2
N_COLUMN = 3              # cans in the column above can2 -> capacity = 2 + 3 = 5
MAG_Y_IN = P.CAN_L / 2 + 1.5                                     # wall inner face |y|
MAG_WALL_T = 8.0
# column guide clearance per side: a can yawed against the end walls (1.5 mm each) spans 71.6 mm,
# so guides 72.5 mm apart can never wedge it (1 mm per side jammed in sim/feed_sim.py)
COL_CLR = 3.2
RAIL_END_R = 281.0


def _rel(x, z):
    return (x, z - PZ)


def abs_xz(rel):
    return (rel[0], rel[1] + PZ)


# ---------------------------------------------------------------------------
# Part metadata
# ---------------------------------------------------------------------------
@dataclass
class PartSpec:
    name: str
    material: str           # PETG / TPU / PLA
    qty: int
    print_rot: tuple        # (rx, ry, rz) applied to the assembly-pose part to get the print pose
    walls: int = 4
    infill: int = 25
    layer: float = 0.20
    plate: str = "A"
    body: str = "frame"     # frame | arm | ring | latch | mag
    loaded: bool = True
    note: str = ""
    color: tuple = (0.92, 0.92, 0.90)
    mirror_of: str | None = None


ON_YNEG = (90, 0, 0)    # Rot(90,0,0): z' = y  -> the assembly y_min face lies on the bed
ON_YPOS = (-90, 0, 0)   # Rot(-90,0,0): z' = -y -> the assembly y_max face lies on the bed
FLAT = (0, 0, 0)
UPSIDE = (180, 0, 0)

WHITE = (0.93, 0.93, 0.91)
GREY = (0.32, 0.33, 0.35)
ORANGE = (0.95, 0.45, 0.10)
BLACK = (0.12, 0.12, 0.13)


# ---------------------------------------------------------------------------
# Arm hub (arm + hub + drum + ears) — one PETG part
# ---------------------------------------------------------------------------
HUB_SPLIT = (P.Y_ARM[0], P.Y_ARM[1])     # drum | arm | catch-ear joints at y = -14 and +14
HUB_JOINT_R = 19.0
DOWEL_ANGLES = (30.0, 150.0, 270.0)       # 4 x 20 steel dowels carry the torque across each joint
SCREW_ANGLES = (90.0, 210.0, 330.0)       # M3 x 16 clamp screws into inserts in the arm disc


def _hub_joint_features(part, y_face, y_far, into_arm: bool):
    """Dowel holes and screw holes on a hub joint face."""
    c0 = (0.0, PZ)
    for a in DOWEL_ANGLES:
        x, z = polar(HUB_JOINT_R, a, c0)
        part = part - ycyl(x, z, 1.95 if into_arm else 2.0, y_face - 10.5, y_face + 10.5)
    for a in SCREW_ANGLES:
        x, z = polar(HUB_JOINT_R, a, c0)
        if into_arm:
            part = part - ycyl(x, z, P.M3_INSERT_HOLE / 2, y_face - P.M3_INSERT_DEPTH, y_face + P.M3_INSERT_DEPTH)
        else:
            lo, hi = sorted((y_face, y_far))
            part = part - ycyl(x, z, P.M3_CLEAR / 2, lo - 1, hi + 1)
            # deep counterbore from the outer face so an M3 x 16 reaches the arm (hidden fastener)
            if y_far < y_face:
                part = part - ycyl(x, z, 3.2, y_far - 1, y_face - 10.0)
            else:
                part = part - ycyl(x, z, 3.2, y_face + 10.0, y_far + 1)
    return part


@lru_cache(None)
def hub_drum_local() -> bd.Part:
    """Left hub part: cord drum + absorber strike ear + 608 seat (prints on its -y face)."""
    c0 = (0.0, PZ)
    yl = P.Y_HUB[0]
    abs_face = BETA_ABS_FACE
    ear_c = polar(78.0, abs_face + 9.0, c0)
    drum = circle(c0, 36.0) + circles_hull([(c0[0], c0[1], 30.0), (ear_c[0], ear_c[1], 10.0)])
    left = slab(drum, yl, P.Y_ABS[1])
    # V-groove for the cord at Y_DRUM (root r = 29), 45 deg flanks (prints without support)
    yd = P.Y_DRUM
    vprof = bd.Polygon((29.0, yd - 1.0), (29.0, yd + 1.0), (37.0, yd + 9.0), (40.0, yd + 9.0), (40.0, yd - 5.0),
                       (33.0, yd - 5.0))   # upper flank 45 deg out through the flange top: no ledge, no knife edge
    vgroove = bd.revolve(bd.Plane.XY * vprof, bd.Axis.Y)     # 90 deg V (45 deg flanks) about the pivot axis
    left = left - bd.Pos(0, 0, PZ) * vgroove
    anc = polar(31.0, CORD_EXIT_DEG + 30.0 - A_REST, c0)
    left = left - ycyl(anc[0], anc[1], 3.0, P.Y_DRUM - 6, P.Y_DRUM + 6)
    fa = math.radians(abs_face)
    t = (math.cos(fa), math.sin(fa))
    nrm = (math.sin(fa), -math.cos(fa))
    cutter_pts = [polar(60, abs_face, c0), polar(100, abs_face, c0),
                  (c0[0] + 100 * t[0] + 30 * nrm[0], c0[1] + 100 * t[1] + 30 * nrm[1]),
                  (c0[0] + 60 * t[0] + 30 * nrm[0], c0[1] + 60 * t[1] + 30 * nrm[1])]
    left = left - slab(bd.Polygon(*cutter_pts), yl - 1, P.Y_ABS[1] + 1)
    hub = left + slab(circle(c0, 27.0), P.Y_ABS[1], HUB_SPLIT[0])
    hub = hub - ycyl(0, PZ, P.BEARING_608_BORE / 2, yl - 1, yl + 7) - ycyl(0, PZ, 6.5, yl - 1, HUB_SPLIT[0] + 1)
    return _hub_joint_features(hub, HUB_SPLIT[0], yl, into_arm=False)


@lru_cache(None)
def arm_local() -> bd.Part:
    """Arm beam + hub disc (y -14..14). Bending is in the layer plane (prints flat)."""
    c0 = (0.0, PZ)
    bh0, bh1 = 26.0, 16.0
    # beam tapers straight into the 28 mm tongue (no step: FEA showed a stress raiser there)
    beam_prof = bd.Polygon((18, PZ - bh0), (162, PZ - 17.5), (172, PZ - 14.0), (196, PZ - 14.0), (196, PZ + 14.0),
                           (172, PZ + 14.0), (162, PZ + 17.5), (18, PZ + bh0)) + circle(c0, 27.0)
    beam = slab(G.round2d(beam_prof, 3.0), *P.Y_ARM)
    win = slab(G.round2d(bd.Polygon((62, PZ - 9), (176, PZ - 5.5), (176, PZ + 5.5), (62, PZ + 9)), 4.0),
               P.Y_ARM[0] - 1, P.Y_ARM[1] + 1)
    arm = beam - win - ycyl(0, PZ, 6.5, P.Y_ARM[0] - 1, P.Y_ARM[1] + 1)
    arm = _hub_joint_features(arm, P.Y_ARM[0], P.Y_ARM[1], into_arm=True)
    arm = _hub_joint_features(arm, P.Y_ARM[1], P.Y_ARM[0], into_arm=True)
    for x in CUP_SCREW_X:
        arm = arm - ycyl(x, PZ, P.M3_INSERT_HOLE / 2, P.Y_ARM[1] - P.M3_INSERT_DEPTH, P.Y_ARM[1] + 1)
        arm = arm - ycyl(x, PZ, P.M3_CLEAR / 2, P.Y_ARM[0] - 1, P.Y_ARM[1])
    return arm


@lru_cache(None)
def hub_catch_local() -> bd.Part:
    """Right hub part: carries the 8 mm catch pin + 608 seat (prints on its +y face)."""
    c0 = (0.0, PZ)
    yr = P.Y_HUB[1]
    pin_c = polar(P.CATCH_R, BETA_CATCH, c0)
    hub = slab(circle(c0, 27.0), HUB_SPLIT[1], P.Y_CATCH_EAR[0]) \
        + slab(circles_hull([(c0[0], c0[1], 27.0), (pin_c[0], pin_c[1], 10.5)]), *P.Y_CATCH_EAR)
    hub = hub - ycyl(0, PZ, P.BEARING_608_BORE / 2, yr - 7, yr + 1) - ycyl(0, PZ, 6.5, HUB_SPLIT[1] - 1, yr + 1)
    hub = hub - ycyl(pin_c[0], pin_c[1], 3.95, P.Y_CATCH_EAR[0] + 1, P.Y_CATCH_EAR[1] + 1)
    return _hub_joint_features(hub, HUB_SPLIT[1], yr, into_arm=False)


def arm_hub_local() -> bd.Part:
    """Union of the three hub parts (for analysis only)."""
    return hub_drum_local() + arm_local() + hub_catch_local()


def catch_pin_local():
    pin_c = polar(P.CATCH_R, BETA_CATCH, (0, PZ))
    pin = ycyl(pin_c[0], pin_c[1], 4.0, P.Y_CATCH_EAR[0] + 1, P.Y_ROLLER[1] + 0.5)
    roller = ycyl(pin_c[0], pin_c[1], 11.0, *P.Y_ROLLER) - ycyl(pin_c[0], pin_c[1], 4.0, P.Y_ROLLER[0] - 1, P.Y_ROLLER[1] + 1)
    return pin, roller


# ---------------------------------------------------------------------------
# Cup + TPU pad (hub frame)
# ---------------------------------------------------------------------------
CUP_Y = (-30.0, 30.0)
CUP_SCREW_X = (183.0, 191.5)
CUP_WALL = 5.0
CUP_FLOOR = 6.0


def _cup_geom():
    L = P.ARM_L
    r = P.CAN_D / 2
    pad = P.CUP_PAD
    zc = PZ
    return L, r, pad, zc, zc + r + pad, L + r + pad   # back-wall inner (z), floor inner (x)


@lru_cache(None)
def cup_local() -> bd.Part:
    """L-shaped cradle: back wall (trailing side, +z), floor (radial outer), 15 deg feed lip,
    low inner lip; a thin-walled socket slides over the arm tongue (2 x M3 along y)."""
    L, r, pad, zc, back_in, floor_in = _cup_geom()
    w = CUP_WALL
    x_lip = L - r - pad                     # inner lip face
    wf = CUP_FLOOR
    shell2d = (rect(x_lip - 6, floor_in + wf, back_in, back_in + w)         # back wall
               + rect(floor_in, floor_in + wf, zc - 2, back_in + w))         # floor
    lip_ang = math.radians(15.0)
    p0 = (floor_in, zc - 2)
    p1 = (floor_in + 30 * math.sin(lip_ang), zc - 2 - 30 * math.cos(lip_ang))
    shell2d = shell2d + bd.Polygon(p0, p1, (p1[0] + w, p1[1] + 1.2), (p0[0] + w, p0[1]))
    shell2d = shell2d + rect(x_lip - 6, x_lip, back_in - 14, back_in)        # inner lip (14 mm)
    shell2d = shell2d + bd.Polygon((x_lip - 0.5, back_in + 0.5), (x_lip + 10, back_in + 0.5), (x_lip - 0.5, back_in - 10))  # gusset
    # tapered stiffener on the trailing side: the floor's centripetal load reaches the arm through it
    top = back_in + w
    stiff = bd.Polygon((x_lip - 6, top), (x_lip - 6, top + 20), (floor_in + wf - 12, top + 5), (floor_in + wf, top + 2),
                       (floor_in + wf, top))
    win = bd.Polygon((x_lip + 42, top + 2.5), (x_lip + 42, top + 9.0), (floor_in - 18, top + 4.6), (floor_in - 18, top + 2.5))
    stiff3d = slab(stiff, *CUP_Y) - slab(G.round2d(win, 3.0), CUP_Y[0] - 1, CUP_Y[1] + 1)
    cup = slab(G.round2d(shell2d, 1.5), *CUP_Y) + stiff3d
    # socket around the arm tongue (x 170..196, |z| <= 17.8, |y| <= 14.2) with 3 mm walls
    sock = box(176.0, x_lip, CUP_Y[0], CUP_Y[1], zc - 18.2, back_in - 13.0) \
        - box(166.0, 196.2, P.Y_ARM[0] - 0.2, P.Y_ARM[1] + 0.2, zc - 14.2, zc + 14.2)   # ceiling = 28.4 mm bridge
    cup = cup + sock
    # ribs on the back of the back wall and floor (stiffen the L, 3 mm)
    for yr in (-26.0, 0.0, 26.0):
        rib = slab(bd.Polygon((x_lip - 6, back_in + w), (floor_in + w, back_in + w), (floor_in + w, zc + 10),
                              (floor_in + w + 0.01, back_in + w + 0.01)), yr - 1.5, yr + 1.5) if False else None
        del rib
    for x in CUP_SCREW_X:
        cup = cup - ycyl(x, zc, P.M3_CLEAR / 2, CUP_Y[0] - 1, CUP_Y[1] + 1)
        cup = cup - ycyl(x, zc, P.M3_HEAD_D / 2 + 0.3, CUP_Y[0] - 1, -17.2)

    return cup


@lru_cache(None)
def cup_pad_local() -> bd.Part:
    L, r, pad, zc, back_in, floor_in = _cup_geom()
    t = 2.0
    prof = rect(L - r - pad + 12, floor_in, back_in - t, back_in) + rect(floor_in - t, floor_in, zc - 2, back_in)
    return slab(prof, CUP_Y[0] + 3, CUP_Y[1] - 3) - cup_local()


# ---------------------------------------------------------------------------
# Ring gear with latch (ring frame), and the toggle latch
# ---------------------------------------------------------------------------
@lru_cache(None)
def ring_gear_local() -> bd.Part:
    c0 = (0.0, PZ)
    y0, y1 = P.Y_RING
    gear2d = bd.Pos(*c0) * G.involute_gear_profile(P.GEAR_MODULE, P.RING_TEETH)
    rim_in = RING_ROOT - 7.0
    web = gear2d - circle(c0, rim_in)
    hubring = circle(c0, 20.0)
    # 5 curved spokes
    spokes = None
    for k in range(5):
        a = 90 + 72 * k
        s = circles_hull([(c0[0] + 15 * math.cos(math.radians(a)), c0[1] + 15 * math.sin(math.radians(a)), 6.0),
                          (*polar(rim_in + 2, a + 10, c0), 7.0)])
        spokes = s if spokes is None else spokes + s
    # latch pivot boss and park/cocked safety-pin bosses
    lo = (c0[0] + LATCH_O[0], c0[1] + LATCH_O[1])
    a_lo = math.degrees(math.atan2(LATCH_O[1], LATCH_O[0]))
    boss = circle(lo, 10.0) + circles_hull([(lo[0], lo[1], 9.0), (*polar(rim_in + 3, a_lo, c0), 9.0)]) \
        + circles_hull([(lo[0], lo[1], 7.0), (*polar(15.0, a_lo, c0), 6.0)])     # strut: latch load -> rim + hub
    pin_cocked = (c0[0] + LATCH_PINHOLE[0], c0[1] + LATCH_PINHOLE[1])
    a_pin = math.degrees(math.atan2(LATCH_PINHOLE[1], LATCH_PINHOLE[0]))
    r_pin = math.hypot(*LATCH_PINHOLE)
    pin_park = polar(r_pin, a_pin + (PSI_COCKED - PSI_PARK), c0)
    prof = web + hubring + spokes + boss + circle(pin_cocked, 7.0) + circle(pin_park, 7.0)
    ring = slab(prof, y0, y1)
    # latch boss stand-off towards the latch slab (y 68..70), plus stop bump
    ring = ring + slab(circle(lo, 7.0), P.Y_LATCH[1], y0 + 1.0)
    # bores
    ring = ring - ycyl(0, PZ, P.BEARING_608_BORE / 2, y0 - 1, y0 + 7) - ycyl(0, PZ, P.BEARING_608_BORE / 2, y1 - 7, y1 + 1)
    ring = ring - ycyl(0, PZ, 9.0, y0, y1)  # centre lip leaves 2 x 7 mm seats + 6 mm web at r 9..11
    ring = ring + slab(circle(c0, 11.0) - circle(c0, 9.0), y0 + 7, y1 - 7)
    # latch pivot dowel 4 mm (press 3.9), 15 deep
    ring = ring - ycyl(lo[0], lo[1], 1.95, P.Y_LATCH[1] - 1, y0 + 15)
    # safety pin holes 6.3
    for pc in (pin_cocked, pin_park):
        ring = ring - ycyl(pc[0], pc[1], 3.15, y0 - 1, y1 + 1)
    return ring


@lru_cache(None)
def ring_latch_local(open_deg: float = 0.0) -> bd.Part:
    c0 = (0.0, PZ)
    o = (c0[0] + LATCH_O[0], c0[1] + LATCH_O[1])
    nd = (c0[0] + NOSE_DOWEL[0], c0[1] + NOSE_DOWEL[1])
    body_c = (nd[0] + 6.5 * _n[0], nd[1] + 6.5 * _n[1])    # reaches 1.5 mm past the dowel towards the roller
    tail = (c0[0] + LATCH_TAIL[0], c0[1] + LATCH_TAIL[1])
    ph = (c0[0] + LATCH_PINHOLE[0], c0[1] + LATCH_PINHOLE[1])
    # sized for creep: held cocked 24 h at the 5 m setting (sim/fea.py, SF_creep >= 2.5)
    prof = circles_hull([(o[0], o[1], 11.0), (body_c[0], body_c[1], 8.0)]) \
        + circles_hull([(o[0], o[1], 11.0), (ph[0], ph[1], 9.5), (tail[0], tail[1], 7.0)])
    lat = slab(prof, *P.Y_LATCH)
    lat = lat - ycyl(o[0], o[1], 2.1, P.Y_LATCH[0] - 1, P.Y_LATCH[1] + 1)      # pivot (sliding on 4 mm)
    lat = lat - ycyl(nd[0], nd[1], 1.95, P.Y_LATCH[0] - 1, P.Y_LATCH[1] + 1)   # nose dowel (press)
    lat = lat - ycyl(ph[0], ph[1], 3.15, P.Y_LATCH[0] - 1, P.Y_LATCH[1] + 1)   # safety pin
    lat = lat - ycyl(tail[0], tail[1], 1.95, P.Y_LATCH[0] - 1, P.Y_LATCH[1] + 1)  # tail dowel (finger contact)
    if open_deg:
        lat = G.rot_about_pivot(lat, -open_deg, pivot=o)
    return lat


def nose_dowel_local():
    c0 = (0.0, PZ)
    nd = (c0[0] + NOSE_DOWEL[0], c0[1] + NOSE_DOWEL[1])
    return ycyl(nd[0], nd[1], 2.0, P.Y_LATCH[0], P.Y_LATCH[1])


# ---------------------------------------------------------------------------
# Side plates
# ---------------------------------------------------------------------------
def _plate_profile(right: bool):
    c0 = (0.0, PZ)
    x0, x1 = PLATE_X
    pts = [(x0, BASE_H), (x1, BASE_H), (x1, 200.0), (60.0, PZ + 18), (-40.0, PZ + 18), (x0, 150.0)]
    prof = G.hull2d(pts) + circle(c0, 24.0)
    if right:
        # bump for the latch-servo mount above the front
        prof = prof + G.hull2d([(70, 200), (x1, 200), (x1, 282), (88, 282)])
    else:
        prof = prof + G.hull2d([(60, 160), (x1, 160), (x1, 282), (70, 282)])
    # lightening windows
    prof = G.round2d(prof, 6.0)
    win = G.round2d(bd.Polygon((-95, 58), (-22, 58), (-22, 168), (-95, 128)), 9) \
        + G.round2d(bd.Polygon((-6, 58), (48, 58), (48, 148), (-6, 196)), 9)
    return prof - win


def side_plate(right: bool) -> bd.Part:
    y0, y1 = (Y_IN, Y_IN + T_PL) if right else (-Y_IN - T_PL, -Y_IN)
    pl = slab(_plate_profile(right), y0, y1)
    # shaft boss: left plate 16 mm (boss on the inner face, so both plates print on their flat
    # outer face); right plate 8 mm (the ring gear sits right against it)
    if not right:
        pl = pl + ycyl(0, PZ, 16, y1, y1 + 8)
    pl = pl - ycyl(0, PZ, (SHAFT_D + 0.2) / 2, y0 - 1, y1 + 9)
    # bottom flange inward (for screws into the base): 14 wide, 6 thick
    fy0, fy1 = (Y_IN - 14, Y_IN) if right else (-Y_IN, -Y_IN + 14)
    fl = box(PLATE_X[0] + 8, PLATE_X[1] - 8, fy0, fy1, BASE_H, BASE_H + 6)
    pl = pl + fl
    ym = (fy0 + fy1) / 2
    for x in (-100, -40, 30, 100):
        pl = pl - zcyl(x, ym, BASE_H - 1, BASE_H + 7, P.M3_CLEAR / 2)
        pl = pl - zcyl(x, ym, BASE_H + 3, BASE_H + 7, P.M3_HEAD_D / 2 + 0.3)
    if right:
        # motor: shaft/pinion hub clearance + 2 x M3 on PCD 31
        mx, mz = abs_xz(MOTOR_C)
        pl = pl - ycyl(mx, mz, 13.0, y0 - 1, y1 + 1)
        for a in (0, 180):
            hx, hz = polar(15.5, a + 45, (mx, mz))
            pl = pl - ycyl(hx, hz, P.M3_CLEAR / 2, y0 - 1, y1 + 1)
        # safety pin hole at the cocked tail-hole position
        sp = _safety_pin_xz()
        pl = pl - ycyl(sp[0], sp[1], 3.3, y0 - 1, y1 + 1)
        # latch-servo mount inserts
        for hx, hz in _servo_mount_holes():
            pl = pl - ycyl(hx, hz, P.M3_CLEAR / 2, y0 - 1, y1 + 1)
    else:
        # 3 detent hole pairs for the stop bracket (release 134/138/142 deg)
        for d in (-4.0, 0.0, 4.0):
            for hx, hz in _stop_bracket_holes(d):
                pl = pl - ycyl(hx, hz, P.M3_CLEAR / 2, y0 - 1, y1 + 1)
                pl = pl - ycyl(hx, hz, P.M3_HEAD_D / 2 + 0.3, y0 - 1, y0 + P.M3_HEAD_H)
    return pl


def _safety_pin_xz():
    ph = LATCH_PINHOLE
    a = math.degrees(math.atan2(ph[1], ph[0])) + PSI_COCKED
    return polar(math.hypot(*ph), a, (0.0, PZ))


# ---------------------------------------------------------------------------
# Absorber + stop bracket (left, slab Y_ABS), latch servo + mount (right)
# ---------------------------------------------------------------------------
ABS_LEN = 100.0
ABS_BODY_D = 14.0


def absorber_axis(detent: float = 0.0):
    tip = polar(P.ABS_R, ABS_CONTACT_DEG + detent, (0.0, PZ))
    a = math.radians(ABS_CONTACT_DEG + detent)
    d = (math.sin(a), -math.cos(a))          # body extends clockwise from the tip
    return tip, d


def absorber_solid(detent=0.0, pressed=0.0):
    tip, d = absorber_axis(detent)
    ya = sum(P.Y_ABS) / 2
    t0 = (tip[0] + pressed * d[0], tip[1] + pressed * d[1])
    body0 = (tip[0] + 18 * d[0], tip[1] + 18 * d[1])
    end = (tip[0] + ABS_LEN * d[0], tip[1] + ABS_LEN * d[1])
    ang = math.degrees(math.atan2(d[1], d[0]))

    def seg(a, b, r):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return bd.Pos((a[0] + b[0]) / 2, ya, (a[1] + b[1]) / 2) * bd.Rot(0, -ang + 90, 0) * bd.Cylinder(r, L) \
            if False else bd.Pos((a[0] + b[0]) / 2, ya, (a[1] + b[1]) / 2) * bd.Rot(0, 90 - ang, 0) * bd.Cylinder(r, L)
    rod = seg(t0, body0, 3.0) + seg(t0, (t0[0] + 3 * d[0], t0[1] + 3 * d[1]), 5.0)
    return rod + seg(body0, end, ABS_BODY_D / 2)


STOP_BLOCK = (36.0, 40.0)    # along / across the absorber axis (deep section: the bracket is a cantilever)


def _stop_bracket_holes(detent):
    tip, d = absorber_axis(detent)
    mid = (tip[0] + 55 * d[0], tip[1] + 55 * d[1])
    nrm = (-d[1], d[0])
    a, c = STOP_BLOCK[0] / 2 - 6, STOP_BLOCK[1] / 2 - 6
    return [(mid[0] + sa * a * d[0] + sc * c * nrm[0], mid[1] + sa * a * d[1] + sc * c * nrm[1])
            for sa in (-1, 1) for sc in (-1, 1)]


def stop_bracket(detent=0.0) -> bd.Part:
    """Solid block on the left plate holding the AC1416 by its M14 body (two nuts on the 36 mm bore).
    4 x M3 screws from outside the plate into inserts in the block."""
    tip, d = absorber_axis(detent)
    mid = (tip[0] + 55 * d[0], tip[1] + 55 * d[1])
    ang = math.degrees(math.atan2(d[1], d[0]))
    blk2d = bd.Pos(*mid) * bd.Rot(0, 0, ang) * bd.Rectangle(*STOP_BLOCK)
    br = slab(G.round2d(blk2d, 4), -Y_IN, P.Y_ABS[1] + 3)
    br = br - _abs_bore(detent, 7.2)
    for hx, hz in _stop_bracket_holes(detent):
        br = br - ycyl(hx, hz, P.M3_INSERT_HOLE / 2, -Y_IN - 1, -Y_IN + P.M3_INSERT_DEPTH)
    return br


def _abs_bore(detent, r):
    """Bore along the absorber axis with a 45 deg teardrop roof towards +y (print up)."""
    tip, d = absorber_axis(detent)
    ya = sum(P.Y_ABS) / 2
    ang = math.degrees(math.atan2(d[1], d[0]))
    c = (tip[0] + 57 * d[0], tip[1] + 57 * d[1])
    cyl = bd.Pos(c[0], ya, c[1]) * bd.Rot(0, 90 - ang, 0) * bd.Cylinder(r, 60)
    roof = bd.Pos(c[0], ya, c[1]) * bd.Rot(0, 90 - ang, 0) * bd.Rot(0, 0, 45) * bd.Box(2 * r, 2 * r, 60)
    return cyl + (roof & box(-1000, 1000, ya, 1000, -1000, 1000))


TRIP_SHAFT = None


def _servo_axis():
    # finger contact at the cocked tail; servo shaft 15 mm away perpendicular to the push direction
    tail = LATCH_TAIL
    a = math.degrees(math.atan2(tail[1], tail[0])) + PSI_COCKED
    t_abs = polar(math.hypot(*tail), a, (0.0, PZ))
    push = (0.933, -0.36)
    c, s = math.cos(math.radians(PSI_COCKED)), math.sin(math.radians(PSI_COCKED))
    push = (push[0] * c - push[1] * s, push[0] * s + push[1] * c)
    perp = (push[1] * -1, push[0]) if False else (-push[1], push[0])
    shaft = (t_abs[0] + 17 * perp[0], t_abs[1] + 17 * perp[1])
    return t_abs, shaft


def _servo_mount_holes():
    _, sh = _servo_axis()
    return [(sh[0] + 2.75, sh[1] - 60.0), (sh[0] + 2.75, sh[1] - 52.0)]


def latch_servo_solid():
    """MG996R body (40.7 x 19.7 x 42.9 incl. tabs), shaft along +y towards the latch slab."""
    _, sh = _servo_axis()
    top = P.Y_LATCH[0] - 6.0    # horn plane just inside the latch slab
    body = box(sh[0] - 10, sh[0] + 9.7, top - 36.5 - 8, top - 8, sh[1] - 10, sh[1] + 30.7) \
        if False else box(sh[0] - 9.85, sh[0] + 9.85, top - 44.5, top - 8.0, sh[1] - 10.0, sh[1] + 30.7)
    horn = ycyl(sh[0], sh[1], 5, top - 8, top - 3)
    finger = box(sh[0] - 3, sh[0] + 3, top - 3, P.Y_LATCH[1] - 1, sh[1] - 3, sh[1] + 3)
    return body + horn


def latch_servo_mount() -> bd.Part:
    """Cradle around the MG996R (inside the frame) + low bridge to the right plate that stays
    outside the ring-gear tip radius."""
    _, sh = _servo_axis()
    top = P.Y_LATCH[0] - 6.0
    y_body0 = top - 44.5
    cradle = box(sh[0] - 13, sh[0] + 13, y_body0 - 3, top - 8.0, sh[1] - 15, sh[1] - 10) \
        + box(sh[0] - 13, sh[0] - 9.85, y_body0 - 3, top - 8.0, sh[1] - 15, sh[1] + 30.7)
    post = box(sh[0] - 4, sh[0] + 9.5, y_body0 - 3, P.Y_LATCH[0] - 1.0, sh[1] - 64, sh[1] - 10)
    bridge = box(sh[0] - 4, sh[0] + 9.5, y_body0 - 3, Y_IN, sh[1] - 64, sh[1] - 48) + post
    m = cradle + bridge
    # keep the bridge outside the ring tip (+3 mm)
    m = m - slab(circle((0.0, PZ), RING_TIP + 3.0), P.Y_RING[0] - 2, Y_IN + 1)
    for hx, hz in _servo_mount_holes():
        m = m - ycyl(hx, hz, P.M3_INSERT_HOLE / 2, Y_IN - P.M3_INSERT_DEPTH, Y_IN + 1)
    return m


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
SPR_CH_Y = (-92.0, -8.0)
PULLEY_C = (30.0 + 13.0, P.SPRING_Z + 13.0)   # (x, z abs)
CUP_WELL_X = (-245.0, -95.0)
ANCHOR_WALL_X = (-266.0, -256.0)


DECK_T = 4.0
FOOT_INSET = 22.0


def _base(x0, x1, front: bool) -> bd.Part:
    """Open-bottom ribbed tray: 4 mm deck on top, 3 mm perimeter and ribs. Printed upside down
    (deck on the bed), so nothing overhangs. Feet bosses in the corners."""
    w = BASE_W / 2
    outer = bd.fillet(box(x0, x1, -w, w, 0, BASE_H).edges().filter_by(bd.Axis.Z), 8.0)
    inner = box(x0 + 3, x1 - 3, -w + 3, w - 3, -1, BASE_H - DECK_T)
    b = outer - inner
    nrib = max(1, int((x1 - x0) // 55))
    for k in range(1, nrib + 1):
        xr = x0 + k * (x1 - x0) / (nrib + 1)
        b = b + box(xr - 1.5, xr + 1.5, -w + 3, w - 3, 0, BASE_H - DECK_T)
    for yr in (-Y_IN + 7, Y_IN - 7, 0.0):
        b = b + box(x0 + 3, x1 - 3, yr - 1.5, yr + 1.5, 0, BASE_H - DECK_T)
    # feet bosses (solid) with a 2 mm recess for the TPU feet
    for x in (x0 + FOOT_INSET, x1 - FOOT_INSET):
        for y in (-w + FOOT_INSET, w - FOOT_INSET):
            b = b + zcyl(x, y, 0, BASE_H - DECK_T, 17.0) - zcyl(x, y, -1, 2.0, 15.3)
    # spring channel (open top and bottom) and cup well
    xn = CHANNEL_NARROW_X
    b = b - box(x0 - 1, min(x1, xn) + 0.01, SPR_CH_Y[0], SPR_CH_Y[1], -1, BASE_H + 1)
    if x1 > xn:
        b = b - box(xn, x1 + 1, P.Y_DRUM - PB_HALF_W - 0.3, P.Y_DRUM + PB_HALF_W + 0.3, -1, BASE_H + 1)
    b = b + box(x0, min(x1, xn), SPR_CH_Y[0] - 3, SPR_CH_Y[0], 0, BASE_H) \
        + box(x0, min(x1, xn), SPR_CH_Y[1], SPR_CH_Y[1] + 3, 0, BASE_H)
    wx0, wx1 = max(CUP_WELL_X[0], x0 - 1), min(CUP_WELL_X[1], x1 + 1)
    if wx0 < wx1:
        b = b - box(wx0, wx1, SPR_CH_Y[1], 60, -1, BASE_H + 1)
    # joint to the other half: the side cheeks' flanges bolt into both decks (2 inserts per side each)
    for y in (CHEEK_FLANGE_Y, -CHEEK_FLANGE_Y):
        for xj in CHEEK_SCREW_X:
            if x0 < xj < x1:
                b = b - zcyl(xj, y, BASE_H - P.M3_INSERT_DEPTH, BASE_H + 1, P.M3_INSERT_HOLE / 2)
    if front:
        # pulley bracket inserts (bracket straddles the channel)
        for (hx, hy) in _pulley_bracket_holes():
            b = b - zcyl(hx, hy, BASE_H - P.M3_INSERT_DEPTH, BASE_H + 1, P.M3_INSERT_HOLE / 2)
        for x in (-60.0, 100.0):
            for y in (8.0, 68.0):
                b = b - zcyl(x, y, BASE_H - P.M3_INSERT_DEPTH, BASE_H + 1, P.M3_INSERT_HOLE / 2)
        for sgn in (-1, 1):
            ym = sgn * (Y_IN - 7)
            for x in (-100, -40, 30, 100):
                b = b - zcyl(x, ym, BASE_H - P.M3_INSERT_DEPTH, BASE_H + 1, P.M3_INSERT_HOLE / 2)
    else:
        b = b + box(*ANCHOR_WALL_X, SPR_CH_Y[0], SPR_CH_Y[1], 0, BASE_H)
        for yr in SPRING_ROD_Y:
            b = b - xcyl(ANCHOR_WALL_X[0] - 1, ANCHOR_WALL_X[1] + 1, yr, P.SPRING_Z, 3.3)
        for cl in (P.CANS["330"]["l"], P.CANS["500"]["l"]):
            yi = cl / 2 + 1.5 + MAG_WALL_T / 2 - 3.25
            for sgn in (-1, 1):
                for x in MAG_FOOT_X:
                    b = b - zcyl(x, sgn * yi, BASE_H - P.M3_INSERT_DEPTH, BASE_H + 1, P.M3_INSERT_HOLE / 2)
    return b


CHANNEL_NARROW_X = 4.0
CHEEK_FLANGE_Y = Y_IN + T_PL + 6.5
CHEEK_SCREW_X = (-110.0, -150.0, -200.0, -300.0)


# pulley cheeks: 15.5 mm each so the axle-hole bearing stress stays below the 24 h creep limit
PB_HALF_W = 19.5


def _pulley_bracket_holes():
    px = PULLEY_C[0]
    yo = PB_HALF_W + 4.5
    return [(px - 16, P.Y_DRUM - yo), (px + 16, P.Y_DRUM - yo), (px - 16, P.Y_DRUM + yo), (px + 16, P.Y_DRUM + yo)]


def pulley_bracket() -> bd.Part:
    """Bridge over the spring channel carrying the 608 redirect pulley on an 8 mm axle."""
    px, pz = PULLEY_C
    y0, y1 = P.Y_DRUM - PB_HALF_W - 6.3, P.Y_DRUM + PB_HALF_W + 6.3   # left plate flange at y -76
    top = bd.fillet(box(px - 26, px + 26, y0, y1, BASE_H, BASE_H + 10).edges().filter_by(bd.Axis.Z), 5)
    cheeks = None
    # cheeks root along the whole plate (creep: held cocked 24 h, sim/fea.py)
    for yc0, yc1 in ((P.Y_DRUM - PB_HALF_W, P.Y_DRUM - 4.0), (P.Y_DRUM + 4.0, P.Y_DRUM + PB_HALF_W)):
        c = slab(G.hull2d([(px - 25, BASE_H + 5), (px + 25, BASE_H + 5), (px + 13, pz - 2), (px, pz - 14),
                           (px - 13, pz - 2)]) + circle((px, pz), 14.5), yc0, yc1)
        cheeks = c if cheeks is None else cheeks + c
    br = top + (cheeks & box(-1000, 1000, -1000, 1000, -1000, BASE_H + 8))
    br = br - ycyl(px, pz, 4.05, P.Y_DRUM - 17, P.Y_DRUM + 17)
    for hx, hy in _pulley_bracket_holes():
        br = br - zcyl(hx, hy, BASE_H - 1, BASE_H + 6, P.M3_CLEAR / 2)
    # cord passes down through the deck plate
    br = br - box(px - 15, px - 8, P.Y_DRUM - 4.8, P.Y_DRUM + 4.8, BASE_H - 1, BASE_H + 9)
    return br


def base_front():
    return _base(*BASE_FRONT_X, front=True)


def base_rear():
    return _base(*BASE_REAR_X, front=False)


def base_joint_plate():
    return box(-145, -105, -100, 100, -0.01, 0.01) if False else None


# ---------------------------------------------------------------------------
# Spring yokes, springs, cord (non-printed parts modelled for clearance)
# ---------------------------------------------------------------------------
def spring_positions(state_ext_mm: float):
    """x of the cord yoke front face and the anchor yoke back face for a spring extension."""
    x_cy_front = PULLEY_C[0] - 13.0 - 30.0       # cord yoke sits 30 mm behind the pulley tangent
    L = P.SPRING.l0 + state_ext_mm
    x_cy_back = x_cy_front - 20.0
    x_ay_front = x_cy_back - L
    return x_cy_front, x_cy_back, x_ay_front, x_ay_front - 20.0


SPRING_ROD_Y = (-82.0, -18.0)


def spring_yoke(x_front) -> bd.Part:
    y0, y1 = -88.0, -12.0
    z0, z1 = P.SPRING_Z - 9, P.SPRING_Z + 11
    yk = box(x_front - 20, x_front, y0, y1, z0, z1)
    yk = bd.chamfer(yk.edges().filter_by(bd.Axis.X), 2.0)
    for yr in SPRING_ROD_Y:
        yk = yk - xcyl(x_front - 21, x_front + 1, yr, P.SPRING_Z, 3.3)
    # dowel along y for the spring hooks + slots for the hooks
    yk = yk - ycyl(x_front - 8, P.SPRING_Z, 2.05, y0 - 1, y1 + 1)
    for ys in P.SPRING_Y:
        yk = yk - box(x_front - 12, x_front + 1, ys - 2.5, ys + 2.5, z0 - 1, z1 + 1)
    yk = yk - box(x_front - 21, x_front - 15, -60, -40, z0 - 1, z1 + 1) if False else yk
    return yk


def springs_solid(x_cy_back, x_ay_front):
    s = None
    for ys in P.SPRING_Y:
        c = xcyl(x_ay_front, x_cy_back, ys, P.SPRING_Z, P.SPRING.od / 2) \
            - xcyl(x_ay_front - 1, x_cy_back + 1, ys, P.SPRING_Z, P.SPRING.od / 2 - P.SPRING.d_wire)
        s = c if s is None else s + c
    return s


# ---------------------------------------------------------------------------
# Magazine: walls (L/R, lower+upper), bridges (the 500 ml part), rocker
# ---------------------------------------------------------------------------
def _rail_line():
    """Rail top surface: line offset from the can-centre path by the can radius."""
    d = (math.cos(math.radians(FEED_DIR + 180)), math.sin(math.radians(FEED_DIR + 180)))  # down the chute
    nrm = (d[1], -d[0]) if d[1] < 0 else (-d[1], d[0])
    nrm = (-0.5, -0.866)
    top = (CAN2[0] - 30 * d[0], CAN2[1] - 30 * d[1])
    p0 = (top[0] + P.CAN_D / 2 * nrm[0], top[1] + P.CAN_D / 2 * nrm[1])
    # walk down until r == RAIL_END_R
    s = 0.0
    while math.hypot(p0[0] + s * d[0], p0[1] + s * d[1]) > RAIL_END_R:
        s += 0.5
    return p0, d, s


MAG_Z_SPLIT = 245.0     # abs z where the lower and upper wall halves meet (both < 256 mm tall)
MAG_TOP = PZ + CAN2[1] + N_COLUMN * CAN_PITCH + P.CAN_D / 2 + 12


def _chute_pts():
    p0, d, s_end = _rail_line()
    a0 = abs_xz(p0)
    a1 = (a0[0] + s_end * d[0], a0[1] + s_end * d[1])
    return a0, a1, d


def chute_s(s_from_can1: float):
    """Point on the rail surface at chute coordinate s (downhill +) measured from can1's contact."""
    d = (-_fd[0], -_fd[1])
    nrm = (-0.5, -0.866)
    c1 = abs_xz(CAN1)
    base = (c1[0] + P.CAN_D / 2 * nrm[0], c1[1] + P.CAN_D / 2 * nrm[1])
    return (base[0] + s_from_can1 * d[0], base[1] + s_from_can1 * d[1])


def _mag_wall_profile():
    xc = MAG_XC
    zc2 = PZ + CAN2[1]
    r = P.CAN_D / 2
    a0, a1, d = _chute_pts()
    xback = xc - r - COL_CLR - 23.0              # encloses the back guide and the bridges behind it
    col = rect(xback, xc + r + COL_CLR + 8.0, zc2 + 10, MAG_TOP)
    # chute web under the rails, down to the floor at the back and the base deck at the front
    web = G.hull2d([(a0[0] - 6, a0[1] + 8), (a1[0], a1[1] + 6), (a1[0], a1[1] - 16),
                    (MAG_FOOT_X[1] + 15, BASE_H), (BASE_REAR_X[0] - 0.5, BASE_H), (xback, zc2 + 20)])
    rear_foot = G.hull2d([(BASE_REAR_X[0] - 0.5, 0.0), (BASE_REAR_X[0] - 0.5, BASE_H + 20), (xback, BASE_H + 60),
                          (xback, 0.0)])
    return G.round2d(col + web + rear_foot, 5.0)


def mag_wall(right: bool, part: str):
    """part: 'lower' (z < MAG_Z_SPLIT) or 'upper'."""
    prof = _mag_wall_profile()
    xc = MAG_XC
    zc2 = PZ + CAN2[1]
    r = P.CAN_D / 2
    yin = MAG_Y_IN
    y0, y1 = (yin, yin + MAG_WALL_T) if right else (-yin - MAG_WALL_T, -yin)
    w = slab(prof, y0, y1) - box(BASE_REAR_X[0], BASE_REAR_X[1], -200, 200, -1, BASE_H)
    fy0, fy1 = (yin - 22, yin) if right else (-yin, -yin + 22)
    # column guides: back flange full height, front flange stops above can2 so it can roll out
    w = w + box(xc - r - COL_CLR - 6, xc - r - COL_CLR, fy0, fy1, zc2 - 10, MAG_TOP - 4)
    w = w + box(xc + r + COL_CLR, xc + r + COL_CLR + 6, fy0, fy1, zc2 + r + 12, MAG_TOP - 4)
    # chute rail ledge (13 mm) under the can ends
    a0, a1, d = _chute_pts()
    ry0, ry1 = (yin - 13, yin) if right else (-yin, -yin + 13)
    w = w + slab(G.hull2d([(a0[0] - 6, a0[1]), (a1[0], a1[1]), (a1[0], a1[1] - 8), (a0[0] - 6, a0[1] - 10)]), ry0, ry1)
    # column window
    w = w - slab(G.round2d(rect(xc - 16, xc + 16, zc2 + 50, MAG_TOP - 22), 8), y0 - 1, y1 + 1)
    if not right:
        # TCRT5000 looks at can1's end face; rocker axle (the fingers rise inboard of the ledge)
        c1 = abs_xz(CAN1)
        w = w - ycyl(c1[0], c1[1], 5.5, y0 - 1, y1 + 1)
        ax = rocker_axle()
        w = w - ycyl(ax[0], ax[1], ROCKER_PIN_D / 2 - 0.05, y0 - 1, y1 + 1)     # 4 mm dowel, press fit
        # escapement servo bracket: 2 x M3 from outside into inserts in the bracket arm
        for hx, hz in esc_mount_holes():
            w = w - ycyl(hx, hz, P.M3_CLEAR / 2, y0 - 1, y1 + 1)
            w = w - ycyl(hx, hz, P.M3_HEAD_D / 2 + 0.3, y0 - 1, y0 + 3.0)
    # base screws: front foot onto base_rear (2 x M3 vertical)
    ym = (y0 + y1) / 2
    for x in MAG_FOOT_X:
        by0, by1 = (y0 - 6.5, y1) if right else (y0, y1 + 6.5)      # boss on the inner face only
        w = w + bd.fillet(box(x - 8, x + 8, by0, by1, BASE_H, BASE_H + 32).edges().filter_by(bd.Axis.Z), 3)
        yb = ym - 3.25 if right else ym + 3.25
        w = w - zcyl(x, yb, BASE_H - 1, BASE_H + 33, P.M3_CLEAR / 2)
        w = w - zcyl(x, yb, BASE_H + 8, BASE_H + 33, P.M3_HEAD_D / 2 + 0.4)
    for (bx, bz) in _bridge_points():
        w = w - ycyl(bx, bz, P.M3_CLEAR / 2, y0 - 1, y1 + 1)
    # chute/lower joint: two 4 mm dowels + 2 x M3 along x across the cut face
    joint_z = (BASE_H + 24.0, PZ + CAN1[1] - 10.0)
    for jz in joint_z:
        w = w - xcyl(MAG_X_CUT - 10, MAG_X_CUT + 10, ym, jz, 1.55)
    if part in ("lower", "chute"):
        w = w & box(-1000, 1000, -1000, 1000, -1, MAG_Z_SPLIT)
        if part == "lower":
            w = w & box(-1000, MAG_X_CUT, -1000, 1000, -1000, 1000)
            for x in (xc - r - 4,):
                w = w - zcyl(x, ym, MAG_Z_SPLIT - 8, MAG_Z_SPLIT + 1, 2.05)
        else:
            w = w & box(MAG_X_CUT, 1000, -1000, 1000, -1000, 1000)
    else:
        w = w & box(-1000, 1000, -1000, 1000, MAG_Z_SPLIT, 2000)
        for x in (xc - r - 4, xc + r + 4):
            w = w - zcyl(x, ym, MAG_Z_SPLIT - 1, MAG_Z_SPLIT + 8, 2.05)
    return w


MAG_FOOT_X = (BASE_REAR_X[0] + 50.0, BASE_REAR_X[0] + 90.0)
MAG_X_CUT = BASE_REAR_X[0] + 55.0   # lower-wall / chute split (keeps both under 256 mm)


def _bridge_points():
    zc2 = PZ + CAN2[1]
    r = P.CAN_D / 2
    xb = MAG_XC - r - COL_CLR - 13.0          # just behind the back column guide
    return [(xb, MAG_TOP - 14), (xb, zc2 + 30)]


def mag_bridge(which: int) -> bd.Part:
    """Cross-member between the two magazine walls (inserts in both ends, screws through the
    walls). Its length = CAN_L + 3 is the ONLY thing that changes for 500 ml cans."""
    bx, bz = _bridge_points()[which]
    yin = MAG_Y_IN
    br = slab(rect(bx - 7, bx + 7, bz - 10, bz + 10), -yin + 0.0, yin)
    br = bd.chamfer(br.edges().filter_by(bd.Axis.Y), 1.5)
    for ye in (-yin, yin):
        br = br - ycyl(bx, bz, P.M3_INSERT_HOLE / 2, ye - P.M3_INSERT_DEPTH, ye + P.M3_INSERT_DEPTH)
    return br


# Seesaw escapement (DECISIONS.md D8). Chute coordinate s: + downhill, 0 = can1's rail contact.
# f1: post taller than the can centre ahead of can1 (a cylinder cannot roll over it).
# f2: short finger under the can1/can2 V; rises behind can1 and stops can2 (12-13 mm step).
# Drive: servo horn + pushrod toggle (D8b). At hold the horn sits 8 deg past dead centre, so the
# column load on f1 pushes the linkage into the servo along the rod (~0.03 N m at the servo);
# the direct-drive version was back-driven by the column in sim/feed_sim.py.
ROCKER_F1_H = 38.0
ROCKER_F2_H = -4.5                            # f2 tip centre at hold: its 3.5 mm round top sits 1 mm below the rail
ROCKER_S1 = P.CAN_D / 2 + 3.5                 # f1 post face touches can1 at centre height
ROCKER_S2 = -33.0                             # f2 under the can1/can2 V
ROCKER_RATIO = 1.2                            # f2 rises ~21 mm: can2 + falling column cannot climb it (1.8 double-fed 1.4 %)
ROCKER_SM = (ROCKER_S1 + ROCKER_RATIO * ROCKER_S2) / (1 + ROCKER_RATIO)
ROCKER_L1 = ROCKER_S1 - ROCKER_SM
ROCKER_DEPTH = 10.0                           # axle below the rail surface
ROCKER_Y = (-MAG_Y_IN + 13.5, -MAG_Y_IN + 21.5)   # 0.5 mm inboard of the rail ledge, on the can's straight body;
                                                # tied to the left wall so 500 ml changes only mag_bridge
ROCKER_HOLD_DEG = 0.0
ROCKER_RELEASE_DEG = -48.0                    # clockwise: f1 top 2 mm below the rail, f2 ~21 mm up
ESC_PHI_HOLD = -8.0                           # servo horn angle at hold (past dead centre, locks)
ESC_PHI_REL = 125.0                           # servo horn angle at release
ESC_PHI_STAGE = 65.0                          # pre-staged during COCK: f1 still 28 mm up (unclimbable), f2 8 mm up
ESC_K = math.radians(ROCKER_RELEASE_DEG) / ((1 - math.cos(math.radians(ESC_PHI_REL)))
                                            - (1 - math.cos(math.radians(ESC_PHI_HOLD))))


def esc_theta(phi_deg: float) -> float:
    """Rocker angle (rad) for servo horn angle phi (deg): ideal crank-rocker toggle, K = -crank/rocker arm."""
    return ESC_K * ((1 - math.cos(math.radians(phi_deg))) - (1 - math.cos(math.radians(ESC_PHI_HOLD))))


def esc_dtheta_dphi(phi_deg: float) -> float:
    return ESC_K * math.sin(math.radians(phi_deg))


def rocker_axle():
    q = chute_s(ROCKER_SM)
    nrm = (-0.5, -0.866)
    return (q[0] + ROCKER_DEPTH * nrm[0], q[1] + ROCKER_DEPTH * nrm[1])


def escapement_rocker(released: bool = False, theta_deg: float | None = None) -> bd.Part:
    """Seesaw: arm along the chute under the rail, two finger posts up through the ledge slots.
    Hold pose: f1 tip 41 mm above the rail (blocks can1), f2 tip 1 mm below.
    Release: rotate clockwise so f2 rises into the can1/can2 V-gap, then f1 drops below the rail."""
    ax = rocker_axle()
    nrm = (-0.5, -0.866)
    up = (-nrm[0], -nrm[1])
    q1, q2 = chute_s(ROCKER_S1), chute_s(ROCKER_S2)
    t1 = (q1[0] + ROCKER_F1_H * up[0], q1[1] + ROCKER_F1_H * up[1])
    t2 = (q2[0] + ROCKER_F2_H * up[0], q2[1] + ROCKER_F2_H * up[1])
    b1 = (q1[0] - ROCKER_DEPTH * up[0], q1[1] - ROCKER_DEPTH * up[1])
    b2 = (q2[0] - ROCKER_DEPTH * up[0], q2[1] - ROCKER_DEPTH * up[1])
    prof = circles_hull([(ax[0], ax[1], 7.0), (b1[0], b1[1], 4.5), (b2[0], b2[1], 4.5)]) \
        + circles_hull([(b1[0], b1[1], 4.0), (t1[0], t1[1], 3.5)]) \
        + circles_hull([(b2[0], b2[1], 4.0), (t2[0], t2[1], 3.5)])
    pin = esc_rocker_pin()
    prof = prof + circles_hull([(ax[0], ax[1], 7.0), (pin[0], pin[1], 4.5)])
    rk = slab(prof, *ROCKER_Y) - ycyl(ax[0], ax[1], ROCKER_PIN_D / 2 + 0.1, ROCKER_Y[0] - 1, ROCKER_Y[1] + 1)
    rk = rk - ycyl(pin[0], pin[1], 1.15, ROCKER_Y[0] - 1, ROCKER_Y[1] + 1)          # 2 mm Z-bend pushrod
    # sign: negative rotation (clockwise) lowers f1 (downhill side) and raises f2
    ang = theta_deg if theta_deg is not None else (ROCKER_RELEASE_DEG if released else ROCKER_HOLD_DEG)
    return G.rot_about_pivot(rk, ang, pivot=ax) if ang else rk


# Escapement drive (D8b): MG996R under the chute, shaft along -y; 12 mm horn + 2 mm steel Z-bend
# pushrod to a crank pin on the rocker. Rocker arm _|_ rod, horn in line with the rod at phi = 0:
# theta ~ -(rc/ra)((1 - cos phi) - (1 - cos phi_hold)), so rc/ra = -ESC_K.
ROCKER_PIN_D = 4.0
ESC_RC = 12.0
ESC_RA = ESC_RC / -ESC_K
ESC_ROD = 40.0                     # pushrod centre distance
ESC_ROD_Y = ROCKER_Y[1] + 1.5      # pushrod plane between the rocker crank face and the horn
ESC_CASE_TOP_Y = ESC_ROD_Y + 5.5   # servo case top (horn side); MG996R case 36.5 deep, tabs 9.5-12 from the top
_U = (-0.866, 0.5)                 # uphill along the chute
_N = (0.5, 0.866)                  # rail normal, up


def esc_rocker_pin(theta_deg: float = 0.0):
    ax = rocker_axle()
    a = math.radians(240.0 + theta_deg)            # -_N direction at hold
    return (ax[0] + ESC_RA * math.cos(a), ax[1] + ESC_RA * math.sin(a))


def esc_shaft():
    p = esc_rocker_pin()
    return (p[0] + (ESC_ROD + ESC_RC) * _U[0], p[1] + (ESC_ROD + ESC_RC) * _U[1])


def _esc_frame(u, n):
    sh = esc_shaft()
    return (sh[0] + u * _U[0] + n * _N[0], sh[1] + u * _U[1] + n * _N[1])


def _esc_box(u0, u1, n0, n1, y0, y1):
    return slab(G.hull2d([_esc_frame(u0, n0), _esc_frame(u1, n0), _esc_frame(u1, n1), _esc_frame(u0, n1)]), y0, y1)


def esc_mount_holes():
    return [_esc_frame(-22.0, -9.0), _esc_frame(-22.0, -19.0)]   # downhill of the servo, below the pushrod sweep


def esc_servo_solid(phi_deg: float = ESC_PHI_HOLD):
    yt = ESC_CASE_TOP_Y
    body = _esc_box(-10.0, 30.7, -9.85, 9.85, yt, yt + 36.5)
    tabs = _esc_box(-17.0, 37.7, -9.85, 9.85, yt + 9.5, yt + 12.0)
    sh = esc_shaft()
    a = math.atan2(-_U[1], -_U[0]) + math.radians(phi_deg)      # horn points at the rocker at phi = 0
    tip = (sh[0] + ESC_RC * math.cos(a), sh[1] + ESC_RC * math.sin(a))
    horn = ycyl(sh[0], sh[1], 5.0, yt - 4.0, yt) + slab(circles_hull([(sh[0], sh[1], 5.0), (tip[0], tip[1], 3.0)]), yt - 4.0, yt - 2.0)
    return body + tabs + horn


def esc_rod_solid(phi_deg: float = ESC_PHI_HOLD, theta_deg: float = 0.0):
    sh = esc_shaft()
    a = math.atan2(-_U[1], -_U[0]) + math.radians(phi_deg)
    tip = (sh[0] + ESC_RC * math.cos(a), sh[1] + ESC_RC * math.sin(a))
    pin = esc_rocker_pin(theta_deg)
    return slab(circles_hull([(tip[0], tip[1], 1.0), (pin[0], pin[1], 1.0)]), ESC_ROD_Y - 1.0, ESC_ROD_Y + 1.0)


def escapement_pose(phi_deg: float) -> dict:
    """Rocker, servo (horn) and pushrod at servo horn angle phi (ideal toggle kinematics)."""
    th = math.degrees(esc_theta(phi_deg))
    return {"escapement_rocker": escapement_rocker(theta_deg=th), "hw_esc_servo": esc_servo_solid(phi_deg),
            "hw_esc_rod": esc_rod_solid(phi_deg, th)}


def esc_servo_mount() -> bd.Part:
    """Frame under the servo tabs + arm along y to the left magazine wall (2 x M3 from outside)."""
    yt = ESC_CASE_TOP_Y
    y_plate = (yt + 12.0, yt + 17.0)
    plate = _esc_box(-27.0, 37.7, -13.85, 13.85, *y_plate) - _esc_box(-10.6, 31.3, -10.35, 10.35, y_plate[0] - 1, y_plate[1] + 1)
    plate = plate + _esc_box(-27.0, -17.0, -24.0, -4.0, *y_plate)
    arm = _esc_box(-27.0, -17.0, -24.0, -4.0, -MAG_Y_IN, y_plate[1])
    m = plate + arm
    for u in (-13.5, 34.2):                      # MG996R tab holes, M3 self-tapping into the plate
        for n in (-5.0, 5.0):
            c = _esc_frame(u, n)
            m = m - ycyl(c[0], c[1], 1.25, y_plate[0] - 1, y_plate[1] + 1)
    for hx, hz in esc_mount_holes():
        m = m - ycyl(hx, hz, P.M3_INSERT_HOLE / 2, -MAG_Y_IN - 1, -MAG_Y_IN + P.M3_INSERT_DEPTH)
    return m


# ---------------------------------------------------------------------------
# Cosmetic / guards
# ---------------------------------------------------------------------------
def gear_guard() -> bd.Part:
    c0 = (0.0, PZ)
    band = circle(c0, RING_TIP + 6.5) - circle(c0, RING_TIP + 3.5)
    sector = bd.Polygon(c0, polar(200, 25, c0), polar(200, 100, c0), polar(200, 180, c0), polar(200, 250, c0))
    g = slab(band & sector, P.Y_LATCH[0] - 2, Y_IN)
    # side disk on the inside (y = Y_LATCH[0]-2..) only above the hub (keeps fingers off the teeth)
    side = (circle(c0, RING_TIP + 6.5) - circle(c0, 62.0)) & sector
    g = g + slab(side, P.Y_LATCH[0] - 4, P.Y_LATCH[0] - 2)
    # clamp tabs to the plate (2 x M3 inserts in the plate's inner face)
    return g


def motor_cover() -> bd.Part:
    mx, mz = abs_xz(MOTOR_C)
    y0 = Y_IN + T_PL
    L_c = 104.0
    cov = ycyl(mx, mz, 24, y0, y0 + L_c) - ycyl(mx, mz, 21.5, y0 - 1, y0 + L_c + 1)
    # 45 deg conical end (prints without support, standing on the flange)
    endc = bd.Pos(mx, y0 + L_c, mz) * bd.Rot(-90, 0, 0) * bd.Cone(24.0, 6.0, 18.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    endi = bd.Pos(mx, y0 + L_c - 0.01, mz) * bd.Rot(-90, 0, 0) * bd.Cone(21.5, 3.0, 18.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    cov = cov + (endc - endi)
    cone = bd.Pos(mx, y0 + 1.5, mz) * bd.Rot(-90, 0, 0) * bd.Cone(30.0, 24.0, 6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)) \
        + (ycyl(mx, mz, 30.0, y0, y0 + 1.5) - ycyl(mx, mz, 21.5, y0 - 1, y0 + 2))
    cov = cov + (cone - ycyl(mx, mz, 21.5, y0 - 1, y0 + 9))
    cov = cov - box(mx - 6, mx + 6, y0 + 20, y0 + 110, mz - 30, mz - 18)  # vent slots underneath
    return cov


def motor_solid():
    mx, mz = abs_xz(MOTOR_C)
    y0 = Y_IN + T_PL
    gb = ycyl(mx, mz, 18.5, y0, y0 + 26)
    mot = ycyl(mx, mz, 17.75, y0 + 26, y0 + 26 + 57)
    enc = ycyl(mx, mz, 16, y0 + 83, y0 + 100)
    shaft = ycyl(mx, mz, 3.0, y0 - 20, y0)
    return gb + mot + enc + shaft


def pinion_phase(psi: float) -> float:
    """Pinion rotation (deg) that puts a pinion gap on the ring tooth nearest the mesh line."""
    pitch_r = 360.0 / P.RING_TEETH
    m_r = MOTOR_ANGLE - psi                       # mesh line in the ring frame
    delta = m_r - pitch_r * round(m_r / pitch_r)  # ring tooth offset from the mesh line (deg)
    s_arc = math.radians(delta) * RING_R          # arc offset, + = CCW on the ring
    to_ring = MOTOR_ANGLE + 180.0                 # direction from pinion centre to ring centre
    return to_ring + 180.0 / P.PINION_TEETH + math.degrees(s_arc / PINION_R)


def pinion_solid(psi: float = 0.0):
    mx, mz = abs_xz(MOTOR_C)
    g = bd.Pos(mx, mz) * bd.Rot(0, 0, pinion_phase(psi)) * G.involute_gear_profile(P.GEAR_MODULE, P.PINION_TEETH)
    pin = slab(g, P.Y_RING[0] + 0.5, P.Y_RING[1] - 0.5) + ycyl(mx, mz, 9, P.Y_RING[1] - 0.5, Y_IN + T_PL - 0.5)
    return pin - ycyl(mx, mz, 3.0, P.Y_RING[0], Y_IN + T_PL)


def ebox() -> bd.Part:
    x0, x1, y0, y1, z0, z1 = -75.0, 112.0, 2.0, 74.0, BASE_H, BASE_H + 78.0
    outer = box(x0, x1, y0, y1, z0, z1)
    outer = bd.fillet(outer.edges().filter_by(bd.Axis.Z), 6.0)
    b = outer - box(x0 + 2.4, x1 - 2.4, y0 + 2.4, y1 - 2.4, z0 + 2.4, z1 + 1)
    # DC jack (12 mm) on the front, USB access slot, vents
    b = b - xcyl(x1 - 3, x1 + 1, 40.0, z0 + 25, 6.1)
    b = b - (bd.Pos(x1 - 1, 40.0, z0 + 25) * bd.Rot(45, 0, 0) * bd.Box(4, 12.2, 12.2)
             & box(-1000, 1000, -1000, 1000, z0 + 25, 1000))
    b = b - box(x1 - 3, x1 + 1, 60, 72, z0 + 12, z0 + 18)
    for k in range(6):
        b = b - box(x0 + 30 + k * 20, x0 + 36 + k * 20, y1 - 3, y1 + 1, z0 + 30, z0 + 60)
    for x in (-60.0, 100.0):
        for y in (8.0, 68.0):
            b = b - zcyl(x, y, z0 - 1, z0 + 3, P.M3_CLEAR / 2)
    return b


def ebox_lid() -> bd.Part:
    x0, x1, y0, y1, z1 = -75.0, 112.0, 2.0, 74.0, BASE_H + 78.0
    top = bd.fillet(box(x0, x1, y0, y1, z1, z1 + 2.4).edges().filter_by(bd.Axis.Z), 6.0)
    lid = top + box(x0 + 2.6, x1 - 2.6, y0 + 2.6, y1 - 2.6, z1 - 4, z1)
    lid = lid - box(x0 + 5, x1 - 5, y0 + 5, y1 - 5, z1 - 5, z1 - 0.001)
    return lid


def foot() -> bd.Part:
    return zcyl(0, 0, -6.0, 2.0, 15.0)


def safety_pin_handle() -> bd.Part:
    sp = _safety_pin_xz()
    y0 = Y_IN + T_PL + 6
    ring = slab(circle((sp[0], sp[1] + 22), 16) - circle((sp[0], sp[1] + 22), 10), y0, y0 + 6)
    hub = ycyl(sp[0], sp[1], 8, y0, y0 + 10) + slab(rect(sp[0] - 4, sp[0] + 4, sp[1], sp[1] + 13), y0, y0 + 6)
    return (ring + hub) - ycyl(sp[0], sp[1], 3.0, y0 - 1, y0 + 11)


def safety_pin_steel():
    sp = _safety_pin_xz()
    return ycyl(sp[0], sp[1], 3.0, P.Y_LATCH[0] + 1, Y_IN + T_PL + 16)


def shaft_solid():
    return ycyl(0, PZ, 4.0, -Y_IN - T_PL - 9, Y_IN + T_PL + 9)


def shaft_spacer(y0, y1) -> bd.Part:
    return ycyl(0, PZ, 7.0, y0, y1) - ycyl(0, PZ, 4.2, y0 - 1, y1 + 1)


def shaft_cap(right: bool) -> bd.Part:
    y0 = Y_IN + T_PL if right else -Y_IN - T_PL - 6
    cap = ycyl(0, PZ, 15, y0, y0 + 6)
    cap = cap - ycyl(0, PZ, 4.1, y0 + (0 if right else 2), y0 + (4 if right else 7))
    return cap


def side_cheek(right: bool) -> bd.Part:
    """Finger guard closing the side between the side plate and the magazine (arm sweep zone).
    Rounded 8 mm slots: fingers cannot reach the cup's path (EN ISO 13857, opening <= 8 mm)."""
    yy = (Y_IN + T_PL, Y_IN + T_PL + 3) if right else (-Y_IN - T_PL - 3, -Y_IN - T_PL)
    prof = G.round2d(bd.Polygon((PLATE_X[0] + 2, BASE_H), (PLATE_X[0] + 2, 230), (MAG_XC + 42, 215),
                                (MAG_XC + 42, BASE_H)), 10)
    ch = slab(prof, *yy)
    fy = (yy[1], yy[1] + 9) if right else (yy[0] - 9, yy[0])
    ch = ch + box(MAG_XC + 44, PLATE_X[0] + 2, fy[0], fy[1], BASE_H, BASE_H + 4)
    ym = (fy[0] + fy[1]) / 2
    for xj in CHEEK_SCREW_X:
        ch = ch - zcyl(xj, ym, BASE_H - 1, BASE_H + 5, P.M3_CLEAR / 2)
    for k in range(9):
        x = -290 + k * 17
        ch = ch - slab(G.round2d(rect(x - 4, x + 4, 70, 175), 3.9), yy[0] - 1, yy[1] + 1)
    return ch


# ---------------------------------------------------------------------------
# Can (for clearance checks and renders)
# ---------------------------------------------------------------------------
def can_solid(center_xz, length=None):
    L = length or P.CAN_L
    r = P.CAN_D / 2
    return ycyl(center_xz[0], center_xz[1], r, -L / 2, L / 2)


# ---------------------------------------------------------------------------
# Assembly states
# ---------------------------------------------------------------------------
def place_arm(part, alpha):
    return G.rot_about_pivot(part, alpha)


def place_ring(part, psi):
    return G.rot_about_pivot(part, psi)


STATES = {
    # name: (alpha_arm, psi_ring, latch_open_deg, absorber_pressed_mm)
    "rest": (A_REST, PSI_PARK, 0.0, P.ABS_STROKE),
    "cocked": (A_COCKED, PSI_COCKED, 0.0, 0.0),
    "release": (A_RELEASE, PSI_COCKED, 24.0, 0.0),
}


def assembly(state="rest", with_hardware=True, with_can=True) -> dict[str, bd.Part]:
    a, psi, lo, pressed = STATES[state]
    out: dict[str, bd.Part] = {}
    out["base_front"] = base_front()
    out["base_rear"] = base_rear()
    out["pulley_bracket"] = pulley_bracket()
    out["side_plate_left"] = side_plate(False)
    out["side_plate_right"] = side_plate(True)
    out["hub_drum"] = place_arm(hub_drum_local(), a)
    out["arm"] = place_arm(arm_local(), a)
    out["hub_catch"] = place_arm(hub_catch_local(), a)
    out["cup"] = place_arm(cup_local(), a)
    out["cup_pad"] = place_arm(cup_pad_local(), a)
    out["ring_gear"] = place_ring(ring_gear_local(), psi)
    out["ring_latch"] = place_ring(ring_latch_local(lo), psi)
    out["stop_bracket"] = stop_bracket(0.0)
    out["latch_servo_mount"] = latch_servo_mount()
    out["gear_guard"] = gear_guard()
    out["motor_cover"] = motor_cover()
    out["ebox"] = ebox()
    out["ebox_lid"] = ebox_lid()
    ext = {"rest": 33.0, "cocked": 86.6, "release": 39.5}[state]   # 4 m setting, mm
    xf, xb, xaf, _ = spring_positions(ext)
    out["spring_yoke_front"] = spring_yoke(xf)
    out["spring_yoke_rear"] = spring_yoke(xaf)
    out["shaft_spacer_left"] = shaft_spacer(-Y_IN + 8, P.Y_HUB[0])
    out["shaft_spacer_mid"] = shaft_spacer(P.Y_HUB[1], P.Y_RING[0])
    out["shaft_cap_left"] = shaft_cap(False)
    out["shaft_cap_right"] = shaft_cap(True)
    out["mag_chute_left"] = mag_wall(False, "chute")
    out["mag_chute_right"] = mag_wall(True, "chute")
    out["mag_wall_left_lower"] = mag_wall(False, "lower")
    out["mag_wall_left_upper"] = mag_wall(False, "upper")
    out["mag_wall_right_lower"] = mag_wall(True, "lower")
    out["mag_wall_right_upper"] = mag_wall(True, "upper")
    out["mag_bridge_top"] = mag_bridge(0)
    out["mag_bridge_back"] = mag_bridge(1)
    out["escapement_rocker"] = escapement_rocker(False)
    out["esc_servo_mount"] = esc_servo_mount()
    out["side_cheek_left"] = side_cheek(False)
    out["side_cheek_right"] = side_cheek(True)
    out["safety_pin_handle"] = safety_pin_handle()
    if with_hardware:
        pin, roller = catch_pin_local()
        out["hw_catch_pin"] = place_arm(pin, a)
        out["hw_catch_roller"] = place_arm(roller, a)
        out["hw_nose_dowel"] = place_ring(G.rot_about_pivot(nose_dowel_local(), -lo,
                                                            pivot=(LATCH_O[0], PZ + LATCH_O[1])), psi)
        out["hw_shaft"] = shaft_solid()
        out["hw_absorber"] = absorber_solid(0.0, pressed)
        out["hw_motor"] = motor_solid()
        out["hw_pinion"] = pinion_solid(psi)
        out["hw_latch_servo"] = latch_servo_solid()
        out["hw_esc_servo"] = esc_servo_solid()
        out["hw_esc_rod"] = esc_rod_solid()
        out["hw_springs"] = springs_solid(xb, xaf)
        out["hw_safety_pin"] = safety_pin_steel()
    if with_can:
        if state == "cocked":
            out["can_in_cup"] = can_solid(abs_xz(CUP_SEAT_COCKED))
        else:
            out["can_in_cup"] = place_arm(can_solid((P.ARM_L, PZ)), a)
        out["can_mag_1"] = can_solid(abs_xz(CAN1))
        out["can_mag_2"] = can_solid(abs_xz(CAN2))
        for k in range(N_COLUMN):
            out[f"can_mag_{k+3}"] = can_solid((MAG_XC, PZ + CAN2[1] + (k + 1) * CAN_PITCH))
    return out


# moving bodies for interference grouping
MOVING_ARM = {"hub_drum", "arm", "hub_catch", "cup", "cup_pad", "hw_catch_pin", "hw_catch_roller", "can_in_cup"}
MOVING_RING = {"ring_gear", "ring_latch", "hw_nose_dowel"}

PARTS: list[PartSpec] = [
    PartSpec("arm", "PETG", 1, ON_YNEG, walls=6, infill=35, plate="B", body="arm",
             note="lies flat: arm bending is in the layer plane", color=WHITE),
    PartSpec("hub_drum", "PETG", 1, ON_YNEG, walls=6, infill=50, plate="B", body="arm", color=WHITE),
    PartSpec("hub_catch", "PETG", 1, ON_YPOS, walls=6, infill=50, plate="B", body="arm", color=WHITE),
    PartSpec("cup", "PETG", 1, ON_YNEG, walls=4, infill=20, plate="C", body="arm", color=WHITE),
    PartSpec("cup_pad", "TPU", 1, ON_YNEG, walls=3, infill=100, plate="T", body="arm", loaded=False, color=GREY),
    PartSpec("ring_gear", "PETG", 1, ON_YPOS, walls=5, infill=50, plate="D", body="ring",
             note="teeth in the layer plane", color=ORANGE),
    PartSpec("ring_latch", "PETG", 1, ON_YNEG, walls=6, infill=100, plate="C", body="ring", color=ORANGE),
    PartSpec("side_plate_left", "PETG", 1, ON_YNEG, walls=4, infill=30, plate="E", color=WHITE,
             note="outer face down; loads in the layer plane"),
    PartSpec("side_plate_right", "PETG", 1, ON_YPOS, walls=4, infill=30, plate="F", color=WHITE,
             note="outer face down; loads in the layer plane"),
    PartSpec("base_front", "PETG", 1, UPSIDE, walls=4, infill=25, plate="G", color=WHITE,
             note="deck down on the bed; open ribbed underside"),
    PartSpec("base_rear", "PETG", 1, UPSIDE, walls=4, infill=25, plate="H", color=WHITE),
    PartSpec("pulley_bracket", "PETG", 1, UPSIDE, walls=5, infill=50, plate="C", color=GREY,
             note="top plate on the bed; cheeks grow up (pulley load across layers is low: 3.6 MPa)"),
    PartSpec("stop_bracket", "PETG", 1, ON_YNEG, walls=6, infill=60, plate="C", color=GREY),
    PartSpec("latch_servo_mount", "PETG", 1, ON_YNEG, walls=4, infill=40, plate="C", color=GREY),
    PartSpec("gear_guard", "PETG", 1, ON_YNEG, walls=3, infill=15, plate="D", loaded=False, color=GREY),
    PartSpec("motor_cover", "PETG", 1, ON_YNEG, walls=3, infill=15, plate="I", loaded=False, color=GREY),
    PartSpec("ebox", "PETG", 1, FLAT, walls=3, infill=15, plate="I", loaded=False, color=GREY),
    PartSpec("ebox_lid", "PETG", 1, UPSIDE, walls=3, infill=15, plate="I", loaded=False, color=GREY),
    PartSpec("spring_yoke_front", "PETG", 1, FLAT, walls=6, infill=60, plate="C", color=GREY),
    PartSpec("spring_yoke_rear", "PETG", 1, FLAT, walls=6, infill=60, plate="C", color=GREY),
    PartSpec("shaft_spacer_left", "PETG", 1, ON_YNEG, walls=4, infill=40, plate="C", loaded=False, color=GREY),
    PartSpec("shaft_spacer_mid", "PETG", 1, ON_YNEG, walls=4, infill=40, plate="C", loaded=False, color=GREY),
    PartSpec("shaft_cap_left", "PETG", 1, ON_YNEG, walls=3, infill=30, plate="C", loaded=False, color=GREY),
    PartSpec("shaft_cap_right", "PETG", 1, ON_YPOS, walls=3, infill=30, plate="C", loaded=False, color=GREY),
    PartSpec("mag_wall_left_lower", "PETG", 1, ON_YNEG, walls=4, infill=20, plate="J", body="mag", color=WHITE),
    PartSpec("mag_wall_right_lower", "PETG", 1, ON_YPOS, walls=4, infill=20, plate="J", body="mag", color=WHITE),
    PartSpec("mag_chute_left", "PETG", 1, ON_YNEG, walls=4, infill=25, plate="J", body="mag", color=WHITE),
    PartSpec("mag_chute_right", "PETG", 1, ON_YPOS, walls=4, infill=25, plate="J", body="mag", color=WHITE),
    PartSpec("mag_wall_left_upper", "PETG", 1, ON_YNEG, walls=3, infill=15, plate="K", body="mag", loaded=False, color=WHITE),
    PartSpec("mag_wall_right_upper", "PETG", 1, ON_YPOS, walls=3, infill=15, plate="K", body="mag", loaded=False, color=WHITE),
    PartSpec("mag_bridge_top", "PETG", 1, FLAT, walls=4, infill=30, plate="K", body="mag", loaded=False, color=ORANGE,
             note="ONLY part to reprint for 500 ml (CAN_SIZE)"),
    PartSpec("mag_bridge_back", "PETG", 1, FLAT, walls=4, infill=30, plate="K", body="mag", loaded=False, color=ORANGE,
             note="ONLY part to reprint for 500 ml (CAN_SIZE)"),
    PartSpec("escapement_rocker", "PETG", 1, ON_YNEG, walls=6, infill=100, plate="C", body="mag", color=ORANGE),
    PartSpec("esc_servo_mount", "PETG", 1, ON_YNEG, walls=4, infill=40, plate="C", body="mag", color=GREY),
    PartSpec("side_cheek_left", "PETG", 1, ON_YPOS, walls=3, infill=15, plate="L", loaded=False, color=GREY),
    PartSpec("side_cheek_right", "PETG", 1, ON_YNEG, walls=3, infill=15, plate="L", loaded=False, color=GREY),
    PartSpec("safety_pin_handle", "PETG", 1, ON_YNEG, walls=4, infill=40, plate="C", loaded=False, color=(0.85, 0.1, 0.1)),
    PartSpec("foot", "TPU", 4, FLAT, walls=3, infill=40, plate="T", loaded=False, color=BLACK),
]
