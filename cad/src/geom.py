"""Geometry helpers shared by the part builders.

Convention: most launcher parts are prisms whose profile lies in the mechanism
plane (x forward, z up) and which are extruded along y (the pivot axis).
`slab(sketch, y0, y1)` builds such a prism from an XY-plane sketch where the
sketch's (X, Y) are the assembly's (x, z).
"""

from __future__ import annotations

import math

import build123d as bd

PIVOT = (0.0, 260.0)  # (x, z) of the pivot axis, set from params in launcher.py


def slab(sk, y0: float, y1: float) -> bd.Part:
    """Extrude an (x, z) profile over y0..y1 (y0 < y1)."""
    # dir= makes the extrusion independent of the polygon winding (a clockwise polygon has a -Z normal)
    return bd.Rot(90, 0, 0) * bd.Pos(0, 0, -y1) * bd.extrude(sk, y1 - y0, dir=(0, 0, 1))


def ycyl(x: float, z: float, r: float, y0: float, y1: float) -> bd.Part:
    """Cylinder along y."""
    return bd.Pos(x, (y0 + y1) / 2, z) * bd.Rot(90, 0, 0) * bd.Cylinder(r, y1 - y0)


def xcyl(x0, x1, y, z, r) -> bd.Part:
    return bd.Pos((x0 + x1) / 2, y, z) * bd.Rot(0, 90, 0) * bd.Cylinder(r, x1 - x0)


def zcyl(x, y, z0, z1, r) -> bd.Part:
    return bd.Pos(x, y, (z0 + z1) / 2) * bd.Cylinder(r, z1 - z0)


def box(x0, x1, y0, y1, z0, z1) -> bd.Part:
    return bd.Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * bd.Box(x1 - x0, y1 - y0, z1 - z0)


def polar(r: float, deg: float, c=(0.0, 0.0)) -> tuple[float, float]:
    a = math.radians(deg)
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def rot_about_pivot(part, deg: float, pivot=None):
    """Rotate by +deg in the x-z plane (CCW looking from -y, i.e. towards +z from +x)."""
    px, pz = pivot or PIVOT
    return bd.Pos(px, 0, pz) * bd.Rot(0, -deg, 0) * bd.Pos(-px, 0, -pz) * part


def circle(c, r):
    return bd.Pos(c[0], c[1]) * bd.Circle(r)


def rect(x0, x1, y0, y1):
    return bd.Pos((x0 + x1) / 2, (y0 + y1) / 2) * bd.Rectangle(x1 - x0, y1 - y0)


def hull2d(points):
    """Convex polygon through the convex hull of points."""
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in points))
    if len(pts) < 3:
        raise ValueError("need 3 points")

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return bd.Polygon(*(lower[:-1] + upper[:-1]))


def circles_hull(circles, n=48):
    """Convex hull of a list of (cx, cy, r) circles."""
    pts = []
    for cx, cy, r in circles:
        for i in range(n):
            a = 2 * math.pi * i / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return hull2d(pts)


def round2d(sk, r):
    try:
        return bd.fillet(sk.vertices(), r)
    except Exception:  # noqa: BLE001 - some vertices too tight to fillet; keep sharp
        return sk


def teardrop_y(x, z, r, y0, y1):
    """Hole along y printable with the part lying on a y face is a plain cylinder; when the
    part lies on an x/z face, use this teardrop (45 deg roof) so the hole needs no support.
    The roof points +z_print; callers pass the print-up direction mapped to assembly +z."""
    cyl = ycyl(x, z, r, y0, y1)
    s = r * math.sqrt(2)
    roof = slab(bd.Polygon((x - r / math.sqrt(2), z + r / math.sqrt(2)), (x, z + s),
                           (x + r / math.sqrt(2), z + r / math.sqrt(2)), (x, z)), y0, y1)
    return cyl + roof


def involute_gear_profile(module: float, teeth: int, pa_deg: float = 20.0, backlash: float = 0.15,
                          pts_per_flank: int = 8):
    """2D spur gear outline (polygon) centred at the origin."""
    pa = math.radians(pa_deg)
    rp = module * teeth / 2
    rb = rp * math.cos(pa)
    ra = rp + module
    rf = max(rp - 1.25 * module, 0.5)
    # tooth half-thickness angle at pitch circle (minus backlash)
    inv = lambda a: math.tan(a) - a  # noqa: E731
    half_t = (math.pi / (2 * teeth)) - backlash / (2 * rp)
    flank = []
    for i in range(pts_per_flank + 1):
        r = max(rb, rf) + (ra - max(rb, rf)) * i / pts_per_flank
        a_r = math.acos(min(1.0, rb / r))
        theta = half_t + inv(pa) - inv(a_r)
        flank.append((r, theta))
    pts = []
    step = 2 * math.pi / teeth
    for k in range(teeth):
        c = k * step
        # root point before the tooth
        pts.append(polar(rf, math.degrees(c - step / 2 + 0.0001)))
        if rf < rb:
            pts.append(polar(rf, math.degrees(c - flank[0][1])))
        for r, th in flank:  # right flank (negative angle side)
            pts.append(polar(r, math.degrees(c - th)))
        for r, th in reversed(flank):
            pts.append(polar(r, math.degrees(c + th)))
        if rf < rb:
            pts.append(polar(rf, math.degrees(c + flank[0][1])))
    return bd.Polygon(*pts)
