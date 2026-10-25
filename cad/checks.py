"""Geometry checks used by tests/ and cad/build.py.

- interference(state): pairwise solid intersections (bbox prefilter), minus intended contacts
- clearance at moving joints (min distance between parts of different bodies)
- overhang analysis on the print-oriented mesh
- wall thickness (ray-cast)
"""

from __future__ import annotations

import itertools
import math

import build123d as bd
import numpy as np

from cad.src import launcher as L

# Pairs that touch or press by design (press fits, threaded parts, rolling contacts, mesh).
INTENDED = {
    frozenset({"hw_catch_pin", "hub_catch"}),          # 0.1 press
    frozenset({"hw_nose_dowel", "ring_latch"}),        # 0.1 press
    frozenset({"hw_absorber", "stop_bracket"}),        # threaded through the clamp wall
    frozenset({"hw_safety_pin", "safety_pin_handle"}),
    frozenset({"hw_shaft", "shaft_cap_left"}), frozenset({"hw_shaft", "shaft_cap_right"}),
    frozenset({"hw_pinion", "side_plate_right"}),      # pinion hub inside the plate clearance hole
}
TOL_VOL = 2.0   # mm^3: below this an intersection is numerical noise / face contact
SMALL_HOLE = 8.5  # mm: holes / slots up to this width print without support (DECISIONS.md D14)


def _bb_overlap(a, b, pad=0.0):
    A, B = a.bounding_box(), b.bounding_box()
    return (A.min.X - pad <= B.max.X and B.min.X - pad <= A.max.X and A.min.Y - pad <= B.max.Y
            and B.min.Y - pad <= A.max.Y and A.min.Z - pad <= B.max.Z and B.min.Z - pad <= A.max.Z)


def interference(state: str, asm=None, skip_cans=False) -> list[tuple[str, str, float]]:
    asm = asm or L.assembly(state)
    names = [n for n in asm if not (skip_cans and n.startswith("can"))]
    hits = []
    for a, b in itertools.combinations(names, 2):
        if frozenset({a, b}) in INTENDED:
            continue
        if a.startswith("can_mag") and b.startswith("can_mag"):
            continue
        if not _bb_overlap(asm[a], asm[b]):
            continue
        try:
            v = (asm[a] & asm[b]).volume
        except Exception:  # noqa: BLE001
            v = float("nan")
        if v > TOL_VOL or math.isnan(v):
            hits.append((a, b, v))
    return hits


def min_distance(a: bd.Part, b: bd.Part) -> float:
    return a.distance_to(b)


def body_of(name: str) -> str:
    if name in L.MOVING_ARM:
        return "arm"
    if name in L.MOVING_RING:
        return "ring"
    return "frame"


# moving joints and the clearance that must exist (radial/axial running gaps)
JOINT_PAIRS = [
    ("hub_catch", "ring_gear"), ("hub_catch", "ring_latch"), ("hub_drum", "stop_bracket"),
    ("hub_drum", "side_plate_left"), ("arm", "gear_guard"), ("hub_catch", "gear_guard"), ("cup", "base_front"), ("cup", "base_rear"),
    ("cup", "mag_chute_left"), ("cup", "mag_chute_right"), ("cup", "mag_wall_left_lower"), ("ring_gear", "side_plate_right"),
    ("ring_gear", "gear_guard"), ("ring_latch", "latch_servo_mount"), ("ring_gear", "latch_servo_mount"),
    ("ring_latch", "hw_latch_servo"), ("hub_catch", "hw_latch_servo"), ("cup", "side_cheek_left"),
    ("cup", "side_cheek_right"), ("can_in_cup", "mag_chute_left"), ("can_in_cup", "mag_chute_right"),
    ("hub_drum", "hw_absorber"),
]


def joint_clearances(state: str, asm=None) -> dict[tuple[str, str], float]:
    asm = asm or L.assembly(state)
    out = {}
    for a, b in JOINT_PAIRS:
        if a in asm and b in asm:
            out[(a, b)] = min_distance(asm[a], asm[b])
    return out


# ---------------------------------------------------------------------------
# Mesh-based print checks
# ---------------------------------------------------------------------------
def to_mesh(part: bd.Part, tol=0.05, ang=0.2):
    import trimesh
    verts, faces = part.tessellate(tol, ang)
    v = np.array([(p.X, p.Y, p.Z) for p in verts])
    return trimesh.Trimesh(v, np.array(faces), process=True)


def print_pose(part: bd.Part, rot) -> bd.Part:
    p = bd.Rot(*rot) * part
    bb = p.bounding_box()
    return bd.Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * p


def overhang_report(mesh, max_deg=50.0, bridge_max=30.0, bed_tol=0.3):
    """Area of downward facets steeper than max_deg from vertical that are not on the bed and
    not short bridges. Returns (bad_area_mm2, total_down_area, worst_region_span)."""
    n = mesh.face_normals
    c = mesh.triangles_center
    area = mesh.area_faces
    # overhang angle measured from vertical: facet normal angle below horizontal
    down = n[:, 2] < -1e-6
    ang_from_vertical = np.degrees(np.arcsin(np.clip(-n[:, 2], 0, 1)))
    steep = down & (ang_from_vertical > max_deg + 0.5) & (c[:, 2] > bed_tol)
    if not steep.any():
        return 0.0, float(area[down].sum()), 0.0
    # group steep facets into connected regions; a region whose smallest bbox span < bridge_max
    # and that is (near) horizontal is a bridge, accepted.
    import trimesh
    idx = np.where(steep)[0]
    sub = mesh.submesh([idx], append=True)
    bad = 0.0
    worst = 0.0
    for comp in sub.split(only_watertight=False):
        if comp.area < 4.0:   # tiny tessellation slivers / chamfer tips
            continue
        # width of the region in its own principal axes (a hole roof is long and narrow)
        pts = comp.vertices[:, :2] - comp.vertices[:, :2].mean(axis=0)
        _, _, vt = np.linalg.svd(pts, full_matrices=False)
        proj = pts @ vt.T
        width = float(np.min(proj.max(axis=0) - proj.min(axis=0)))
        horizontal = (comp.bounds[1][2] - comp.bounds[0][2]) < 0.3   # flat ceiling = bridge
        if width <= SMALL_HOLE:            # roof of a hole/slot <= 8.5 mm wide self-bridges
            continue
        if horizontal and width <= bridge_max:
            continue
        span = width
        bad += comp.area
        worst = max(worst, span)
    del trimesh
    return float(bad), float(area[down].sum()), float(worst)


def min_wall(mesh, samples=1500, seed=1):
    """Ray-cast inward from random surface points; thickness = distance to the opposite surface."""
    rng = np.random.default_rng(seed)
    pts, fi = mesh.sample(samples, return_index=True) if False else (None, None)
    pts, fi = _sample(mesh, samples, rng)
    nrm = mesh.face_normals[fi]
    origins = pts - nrm * 1e-3
    loc, ray_idx, tri_idx = mesh.ray.intersects_location(origins, -nrm, multiple_hits=False)
    if len(loc) == 0:
        return float("inf"), np.array([])
    # only count hits on an opposing face (true wall thickness, not a ray grazing an adjacent face
    # at a corner)
    opp = np.einsum("ij,ij->i", mesh.face_normals[tri_idx], nrm[ray_idx]) < -0.85
    d = np.linalg.norm(loc - origins[ray_idx], axis=1)[opp]
    if len(d) == 0:
        return float("inf"), d
    return float(np.percentile(d, 1)), d


def _sample(mesh, n, rng):
    import trimesh
    pts, fi = trimesh.sample.sample_surface(mesh, n, seed=int(rng.integers(1e9)))
    return pts, fi
