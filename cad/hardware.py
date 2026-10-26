"""Hole census of the exported parts, used to tie the CAD to the BOM (tests/test_bom.py).

A hole is a set of cylindrical faces sharing an axis and an axial midpoint; its depth is the
cylinder area / (2 pi r). Heat-set insert holes: d = M3_INSERT_HOLE, depth ~ M3_INSERT_DEPTH.
"""

from __future__ import annotations

import collections
import math

import build123d as bd

from cad import params as P


def holes(part: bd.Part) -> list[tuple[float, float]]:
    """[(diameter, depth)] of every cylindrical hole/boss face group in the part."""
    groups: dict = collections.defaultdict(float)
    for f in part.faces():
        if f.geom_type != bd.GeomType.CYLINDER:
            continue
        r = f.radius
        if r is None:
            continue
        ax = f.axis_of_rotation
        d, p, c = ax.direction, ax.position, f.center()
        t = (c.X - p.X) * d.X + (c.Y - p.Y) * d.Y + (c.Z - p.Z) * d.Z
        q = (round((p.X + t * d.X) * 2) / 2, round((p.Y + t * d.Y) * 2) / 2, round((p.Z + t * d.Z) * 2) / 2)
        groups[(round(r, 2), q)] += f.area
    return [(2 * r, a / (2 * math.pi * r)) for (r, _), a in groups.items()]


def census(part: bd.Part) -> dict[str, int]:
    out = dict(m3_insert=0, m3_clear=0, bore_608=0)
    for dia, depth in holes(part):
        if abs(dia - P.M3_INSERT_HOLE) < 0.01 and 3.0 <= depth <= P.M3_INSERT_DEPTH + 0.5:
            out["m3_insert"] += 1
        elif abs(dia - P.M3_CLEAR) < 0.01:
            out["m3_clear"] += 1
        elif abs(dia - P.BEARING_608_BORE) < 0.01:
            out["bore_608"] += 1
    return out
