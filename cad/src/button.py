"""The Button: 78 x 52 mm puck. Parts: shell, board tray, switch plate (with snap rim), cap,
TPU foot ring.

Stack (z, mm): shell floor 0-2 | LiPo 503035 2-7.5 | tray 9-10.5 with ESP32-C3 SuperMini and
TP4056 USB-C board | 16 mm switch body 12-32 | switch plate 32-35 + snap rim to 44 |
4 cap springs | cap 40-52 (3 mm travel, hard stop).
Fasteners: 3 x M3 x 8 through the switch plate into inserts in the shell columns, hidden
under the snap-on cap (pop the cap off with a fingernail to service the battery).
Every part prints without support: shell upright, plate flat, cap top-down, rim hook
chamfered at 45 deg.
"""

from __future__ import annotations

import math
from functools import lru_cache

import build123d as bd

from cad import params as P
from cad.src.geom import box, zcyl

OD = P.BTN_OD
H = P.BTN_H
WALL = 2.4
R_IN = OD / 2 - WALL
CAP_D = P.BTN_CAP_D
TRAVEL = P.BTN_CAP_TRAVEL
Z_PLATE = 32.0
PLATE_T = 3.0
Z_SHELL_TOP = Z_PLATE + PLATE_T + 3.0
SCREW_R = R_IN - 5.0
SPRING_R = 20.0
RIM_RI, RIM_RO = CAP_D / 2 + 0.6, CAP_D / 2 + 2.8      # 31.6 .. 33.8
HOOK_RI = CAP_D / 2 - 0.4                            # 0.2 outside the cap skirt
Z_RIM_TOP = 44.5
Z_HOOK = Z_RIM_TOP - 1.6


def _ring(z0, z1, ro, ri):
    return zcyl(0, 0, z0, z1, ro) - zcyl(0, 0, z0 - 1, z1 + 1, ri)


def _cone(z0, h, r0, r1):
    return bd.Pos(0, 0, z0) * bd.Cone(r0, r1, h, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))


@lru_cache(None)
def shell() -> bd.Part:
    s = zcyl(0, 0, 0, Z_SHELL_TOP, OD / 2) - zcyl(0, 0, 2.0, Z_SHELL_TOP + 1, R_IN)
    s = bd.fillet(s.edges().group_by(bd.Axis.Z)[-1].filter_by(bd.GeomType.CIRCLE), 1.0)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        x, y = SCREW_R * math.cos(a), SCREW_R * math.sin(a)
        s = s + zcyl(x, y, 0, Z_PLATE, 4.6)
        s = s - zcyl(x, y, Z_PLATE - P.M3_INSERT_DEPTH, Z_PLATE + 1, P.M3_INSERT_HOLE / 2)
    # tray posts and battery rails on the floor
    for a in (0, 120, 240):
        x, y = 30.0 * math.cos(math.radians(a + 30)), 30.0 * math.sin(math.radians(a + 30))
        s = s + zcyl(x, y, 0, 9.0, 2.5)
    s = s + box(-19.5, 19.5, -17.2, -15.2, 2.0, 5.0) + box(-19.5, 19.5, 15.2, 17.2, 2.0, 5.0)
    # USB-C window for the TP4056 board (+x) and LED light-pipe hole (-y)
    s = s - box(OD / 2 - 4, OD / 2 + 1, -5.0, 5.0, 10.5, 15.0)
    s = s - bd.Pos(0, -OD / 2 + 1, 24) * bd.Rot(90, 0, 0) * bd.Cylinder(2.6, 5)
    return s


@lru_cache(None)
def tray() -> bd.Part:
    t = zcyl(0, 0, 9.0, 11.0, R_IN - 0.6) - zcyl(0, 0, 8, 12, 9.0)
    t = t + box(-34.5, -11.0, -10.8, -9.0, 11.0, 13.0) + box(-34.5, -11.0, 9.0, 10.8, 11.0, 13.0)
    t = t + box(10.0, 35.0, -10.3, -8.5, 11.0, 13.0) + box(10.0, 35.0, 8.5, 10.3, 11.0, 13.0)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        x, y = SCREW_R * math.cos(a), SCREW_R * math.sin(a)
        t = t - zcyl(x, y, 8, 12, 5.4)
    for a in (0, 120, 240):
        x, y = 30.0 * math.cos(math.radians(a + 30)), 30.0 * math.sin(math.radians(a + 30))
        t = t - zcyl(x, y, 8, 12, 1.4)
    return t


@lru_cache(None)
def switch_plate() -> bd.Part:
    p = zcyl(0, 0, Z_PLATE, Z_PLATE + PLATE_T, R_IN - 0.3)
    p = p - zcyl(0, 0, Z_PLATE - 1, Z_PLATE + PLATE_T + 1, P.BTN_SWITCH_D / 2 + 0.2)
    # snap rim with a 45 deg chamfered hook (retains the cap's snap ring)
    dh = RIM_RI - HOOK_RI
    z0 = Z_PLATE + PLATE_T - 0.01
    rim2d = bd.Polygon((RIM_RO, z0), (RIM_RO, Z_RIM_TOP), (HOOK_RI, Z_RIM_TOP), (HOOK_RI, Z_HOOK),
                       (RIM_RI, Z_HOOK - dh), (RIM_RI, z0))
    p = p + bd.revolve(bd.Plane.XZ * rim2d, bd.Axis.Z)
    # 4 relief slots so the rim flexes when the cap is snapped in
    for k in range(4):
        a = 90 * k
        p = p - bd.Pos(0, 0, 0) * bd.Rot(0, 0, a) * box(RIM_RI - 3, RIM_RO + 1, -1.0, 1.0, Z_PLATE + PLATE_T + 2.5, Z_RIM_TOP + 1)
    # hard stop ring under the cap skirt: travel limited to TRAVEL
    z_skirt = H - 12.0
    p = p + (_ring(Z_PLATE + PLATE_T, z_skirt - TRAVEL, CAP_D / 2 - 0.4, CAP_D / 2 - 2.4) - box(-40, 40, -5, 5, 0, 100))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        x, y = SPRING_R * math.cos(a), SPRING_R * math.sin(a)
        p = p + zcyl(x, y, Z_PLATE + PLATE_T, Z_PLATE + PLATE_T + 3, 3.9)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        x, y = SCREW_R * math.cos(a), SCREW_R * math.sin(a)
        p = p - zcyl(x, y, Z_PLATE - 1, Z_PLATE + PLATE_T + 1, P.M3_CLEAR / 2)
    p = p - box(-30, -24, -4, 4, Z_PLATE - 1, Z_PLATE + PLATE_T + 1)   # wire pass-through
    return p


@lru_cache(None)
def cap(pressed: float = 0.0) -> bd.Part:
    z_top = H - pressed
    top = zcyl(0, 0, z_top - 3.0, z_top, CAP_D / 2)
    top = bd.chamfer(top.edges().group_by(bd.Axis.Z)[-1], 1.5)
    skirt = _ring(z_top - 12.0, z_top - 3.0, CAP_D / 2 - 0.6, CAP_D / 2 - 2.6)
    snap_r = RIM_RI - 0.6                         # snap ring OD sits under the hook
    snap = _ring(z_top - 12.0, z_top - 10.6, snap_r + 0.0, CAP_D / 2 - 2.6) if False else None
    del snap
    # outward snap bead at the bottom of the skirt, 45 deg on both sides (prints top-down, no overhang)
    bead = (_cone(z_top - 12.0, 0.9, CAP_D / 2 - 0.6, RIM_RI - 0.2) + _cone(z_top - 11.1, 0.9, RIM_RI - 0.2, CAP_D / 2 - 0.6)) \
        - zcyl(0, 0, z_top - 13, z_top - 9, CAP_D / 2 - 2.6)
    c = top + skirt + bead
    c = c + zcyl(0, 0, z_top - 11.0, z_top - 3.0, 7.0)      # actuator boss (1.5 mm free travel)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        x, y = SPRING_R * math.cos(a), SPRING_R * math.sin(a)
        c = c + zcyl(x, y, z_top - 6.0, z_top - 3.0, 4.0)
    return c


@lru_cache(None)
def foot_ring() -> bd.Part:
    return _ring(-2.0, 0.0, OD / 2 - 1, OD / 2 - 12)


SWITCH_STROKE = 1.5   # 16 mm metal momentary: plunger stroke (measure yours, CALIBRATION.md)


def hardware():
    sw_body = zcyl(0, 0, 12.0, Z_PLATE, 8.0)
    sw_head = zcyl(0, 0, Z_PLATE + PLATE_T, Z_PLATE + PLATE_T + 4.5, 7.0)
    lipo = box(-17.5, 17.5, -15, 15, 2.0, 7.5)
    esp = box(-34.0, -11.5, -9.0, 9.0, 10.5, 14.5)
    tp = box(10.5, 35.0, -8.5, 8.5, 10.5, 14.5)
    return dict(hw_switch=sw_body + sw_head, hw_lipo=lipo, hw_esp32=esp, hw_tp4056=tp)


def assembly(pressed: float = 0.0) -> dict:
    out = dict(btn_shell=shell(), btn_tray=tray(), btn_switch_plate=switch_plate(), btn_cap=cap(pressed),
               btn_foot_ring=foot_ring())
    out.update(hardware())
    return out
