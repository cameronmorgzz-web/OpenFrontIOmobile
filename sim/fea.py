"""FEA of every loaded printed part: gmsh (C3D10 tets) + CalculiX, orthotropic PETG oriented to
the print direction (axis 3 = print Z: E3 = 1500 MPa vs 1800 in-plane, strength 19 vs 34 MPa).

Load cases are the worst cases from calc/ (5 m setting, cocked; absorber stop; 500 ml can for
the cup). Each case records: max von Mises (99.5th percentile of nodal values, so that point
singularities at idealised point loads/fixtures don't dominate), max tension across layers
(sigma along print Z), max deflection, and safety factors:
    SF_xy = sut_xy / s_vm,   SF_z = sut_z / s_z,   SF_fatigue = 0.6 * SF   (1e3 cycles)

    python -m sim.fea           # all parts (~5-15 min)
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from cad import params as P
from cad.src import launcher as L
from calc import design as D

OUT = Path(__file__).resolve().parent / "fea"
STEP = Path(__file__).resolve().parents[1] / "cad" / "step"
PETG = P.PETG


@dataclass
class BC:
    name: str
    select: Callable[[np.ndarray], np.ndarray]   # nodes (N,3) mm -> bool mask
    dofs: tuple = (1, 2, 3)


@dataclass
class Load:
    name: str
    select: Callable[[np.ndarray], np.ndarray]
    force: tuple                                 # total force (N) distributed over the selected nodes


@dataclass
class Case:
    part: str
    case: str
    print_axis: str                              # 'y' or 'z' (assembly axis that is print Z)
    bcs: list
    loads: list
    size: float = 3.5
    pose: Callable | None = None                 # transform applied to the STEP shape (assembly -> case pose)
    sustained: bool = False
    sustained_factor: float = 1.0                # rest (sustained) load / analysed load
    note: str = ""


def _mesh(step_file: Path, size: float, work: Path):
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("p")
    gmsh.model.occ.importShapes(str(step_file))
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", size)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", size * 0.35)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    gmsh.model.mesh.generate(3)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    nodes = coords.reshape(-1, 3)
    etypes, etags, enodes = gmsh.model.mesh.getElements(3)
    gmsh.finalize()
    idx = list(etypes).index(11)        # 10-node tetrahedron
    conn = np.array(enodes[idx]).reshape(-1, 10)
    return np.array(tags, dtype=int), nodes, conn


def _write_inp(path: Path, tags, nodes, conn, case: Case):
    # gmsh 10-node tet ordering == CalculiX C3D10 ordering except nodes 9/10 swapped
    conn = conn[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
    lines = ["*NODE, NSET=NALL"]
    lines += [f"{t}, {x:.5f}, {y:.5f}, {z:.5f}" for t, (x, y, z) in zip(tags, nodes)]
    lines.append("*ELEMENT, TYPE=C3D10, ELSET=EALL")
    lines += [f"{i + 1}, " + ", ".join(str(int(n)) for n in c) for i, c in enumerate(conn)]
    Exy, Ez, nu = PETG.E_xy, PETG.E_z, PETG.nu
    G = Exy / (2 * (1 + nu))
    Gz = Ez / (2 * (1 + nu))
    # local axes: 1,2 in the print plane, 3 = print Z
    if case.print_axis == "y":
        a, b = (1, 0, 0), (0, 0, 1)      # local x = global x, local y = global z -> local z = -global y
    else:
        a, b = (1, 0, 0), (0, 1, 0)
    lines += ["*ORIENTATION, NAME=PRINT, SYSTEM=RECTANGULAR", f"{a[0]},{a[1]},{a[2]},{b[0]},{b[1]},{b[2]}",
              "*MATERIAL, NAME=PETG", "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
              f"{Exy},{Exy},{Ez},{nu},{nu},{nu},{G},{Gz},", f"{Gz},293.",
              "*SOLID SECTION, ELSET=EALL, MATERIAL=PETG, ORIENTATION=PRINT"]
    for bc in case.bcs:
        sel = tags[bc.select(nodes)]
        if len(sel) == 0:
            raise RuntimeError(f"{case.part}/{case.case}: BC {bc.name} selected no nodes")
        lines.append(f"*NSET, NSET={bc.name}")
        lines += [", ".join(map(str, sel[i:i + 12])) for i in range(0, len(sel), 12)]
    lines.append("*STEP")
    lines.append("*STATIC")
    lines.append("*BOUNDARY")
    for bc in case.bcs:
        for dof in bc.dofs:
            lines.append(f"{bc.name}, {dof}, {dof}, 0.")
    lines.append("*CLOAD")
    for ld in case.loads:
        sel = tags[ld.select(nodes)]
        if len(sel) == 0:
            raise RuntimeError(f"{case.part}/{case.case}: load {ld.name} selected no nodes")
        for k, f in enumerate(ld.force, start=1):
            if f:
                for n in sel:
                    lines.append(f"{n}, {k}, {f / len(sel):.6e}")
    lines += ["*NODE FILE", "U", "*EL FILE", "S", "*END STEP"]
    path.write_text("\n".join(lines) + "\n")


def _read_frd(path: Path):
    """Nodal displacement and stress blocks from a CalculiX .frd file."""
    U, S = {}, {}
    block = None
    for line in path.read_text(errors="ignore").splitlines():
        if line.startswith(" -4"):
            name = line.split()[1]
            block = "U" if name.startswith("DISP") else ("S" if name.startswith("STRESS") else None)
            continue
        if line.startswith(" -3"):
            block = None
            continue
        if block and line.startswith(" -1"):
            nid = int(line[3:13])
            vals = [float(line[13 + 12 * i:25 + 12 * i]) for i in range((len(line) - 13) // 12)]
            (U if block == "U" else S)[nid] = vals
    return U, S


LOAD_ZONE = 3.0   # mm


def run_case(case: Case, keep=False) -> dict:
    work = Path(tempfile.mkdtemp(prefix=f"fea_{case.part}_"))
    import build123d as bd
    step = STEP / f"{case.part}.step"
    if case.pose is not None:
        shape = bd.import_step(str(step))
        shape = case.pose(shape)
        step = work / "posed.step"
        bd.export_step(shape, str(step))
    tags, nodes, conn = _mesh(step, case.size, work)
    inp = work / "job.inp"
    _write_inp(inp, tags, nodes, conn, case)
    subprocess.run(["ccx", "-i", "job"], cwd=work, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    U, S = _read_frd(work / "job.frd")
    s = np.array([S[t] for t in tags if t in S])           # sxx syy szz sxy syz szx (global)
    u = np.array([U[t][:3] for t in tags if t in U])
    sxx, syy, szz, sxy, syz, szx = s.T
    vm = np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * (sxy ** 2 + syz ** 2 + szx ** 2))
    sz = syy if case.print_axis == "y" else szz            # normal stress across the layers
    vm_p = float(np.percentile(vm, 99.5))
    # St-Venant: nodal loads on a half hole and rigid BCs give local peaks that are an artefact of
    # the load model. Static/fatigue use all nodes (conservative); the 24 h creep check uses the
    # structure more than LOAD_ZONE mm from any loaded/fixed node (DECISIONS.md D17).
    from scipy.spatial import cKDTree
    pts = nodes[[i for i, t in enumerate(tags) if t in S]]
    zone = np.zeros(len(pts), bool)
    for item in list(case.bcs) + list(case.loads):
        sel = pts[item.select(pts)]
        if len(sel):
            zone |= cKDTree(sel).query(pts, distance_upper_bound=LOAD_ZONE)[0] < LOAD_ZONE
    vm_far = float(np.percentile(vm[~zone], 99.5)) if (~zone).sum() > 50 else vm_p
    sz_p = float(max(np.percentile(sz, 99.5), 0.0))
    umax = float(np.max(np.linalg.norm(u, axis=1)))
    sf_xy = PETG.sut_xy / vm_p
    sf_z = PETG.sut_z / sz_p if sz_p > 1e-6 else float("inf")
    res = dict(part=case.part, case=case.case, nodes=len(tags), elements=len(conn), vm_p995=vm_p,
               vm_max=float(vm.max()), sz_tension_p995=sz_p, u_max_mm=umax, sf_xy=sf_xy, sf_z=sf_z,
               sf_static=min(sf_xy, sf_z), sf_fatigue=PETG.fatigue_ratio_1e3 * min(sf_xy, sf_z),
               vm_far_p995=vm_far,
               sf_creep=(PETG.creep_limit_ratio * PETG.sut_xy / (vm_far * case.sustained_factor)) if case.sustained else None,
               note=case.note)
    if keep:
        res["_nodes"], res["_vm"], res["_u"] = nodes, vm, u
    return res


# ---------------------------------------------------------------------------
# Selection helpers (assembly pose, mm)
# ---------------------------------------------------------------------------
def near_ycyl(cx, cz, r, tol=0.6, y0=-1e9, y1=1e9, toward=None):
    """Nodes on a y-axis cylinder; `toward` (dx, dz) keeps only the loaded half (bearing contact)."""
    def f(n):
        m = (np.abs(np.hypot(n[:, 0] - cx, n[:, 2] - cz) - r) < tol) & (n[:, 1] >= y0) & (n[:, 1] <= y1)
        if toward is not None:
            m &= ((n[:, 0] - cx) * toward[0] + (n[:, 2] - cz) * toward[1]) > 0.3 * r * math.hypot(*toward)
        return m
    return f


def near_xcyl(cy, cz, r, tol=0.6, x0=-1e9, x1=1e9, toward=None):
    def f(n):
        m = (np.abs(np.hypot(n[:, 1] - cy, n[:, 2] - cz) - r) < tol) & (n[:, 0] >= x0) & (n[:, 0] <= x1)
        if toward is not None:
            m &= ((n[:, 1] - cy) * toward[0] + (n[:, 2] - cz) * toward[1]) > 0.3 * r * math.hypot(*toward)
        return m
    return f


def near_zcyl(cx, cy, r, tol=0.6, z0=-1e9, z1=1e9):
    return lambda n: (np.abs(np.hypot(n[:, 0] - cx, n[:, 1] - cy) - r) < tol) & (n[:, 2] >= z0) & (n[:, 2] <= z1)


def any_of(*fs):
    return lambda n: np.any([f(n) for f in fs], axis=0)


def plane(axis, value, tol=0.3):
    i = "xyz".index(axis)
    return lambda n: np.abs(n[:, i] - value) < tol


def _rot(deg):
    import build123d as bd
    from cad.src import geom as G
    return lambda shp: G.rot_about_pivot(shp, deg)


def cases() -> list[Case]:
    PZ = P.PIVOT_H
    to_hub = _rot(-L.A_REST)          # STEP files are in the rest pose -> hub frame (arm along +x)
    to_ring = _rot(-L.PSI_PARK)       # -> ring frame (latched geometry, roller at angle 0)
    s5 = D.setting(5.0)
    m5, w5 = s5["model"], s5["swing"]
    T5 = m5.spring_torque(0.0)
    F_cord = m5.n_springs * m5.spring_force(0.0)
    F_c = T5 / (P.CATCH_R / 1000)
    T_rest = m5.spring_torque(m5.swing)
    from calc import stress as ST
    mp, _ = D.mass_props()
    E_arm = w5.energy_arm_kin + T_rest * ST.ABS_STROKE / ST.ABS_R
    F_abs = ST.ABS_SHAPE * E_arm / ST.ABS_STROKE
    dec = (F_abs * ST.ABS_R + T_rest) / mp["I_arm"]
    M_stop = mp["I_beam_cup"] * dec
    out: list[Case] = []
    rest_ratio = m5.spring_torque(m5.swing) / T5          # sustained preload at rest vs cocked
    a_c = math.radians(L.A_COCKED)
    hj = [L.polar(L.HUB_JOINT_R, a, (0.0, PZ)) for a in L.DOWEL_ANGLES + L.SCREW_ANGLES]

    # 1) arm, absorber stop: fixed at the hub joint holes, root moment applied at the tongue as a force
    lever = 0.183 - 0.0
    F_tip = M_stop / lever
    out.append(Case("arm", "absorber stop 5 m (beam+cup inertia)", "y",
                    [BC("FIX", any_of(*[near_ycyl(x, z, 2.0, 0.8) for x, z in hj]))],
                    [Load("TIP", any_of(*[near_ycyl(x, PZ, P.M3_CLEAR / 2, 0.6) for x in L.CUP_SCREW_X]),
                          (170.0, 0.0, -F_tip))], size=3.5, pose=to_hub,
                    note=f"M_root={M_stop:.1f} N m as {F_tip:.0f} N at the cup screws + 170 N centripetal"))
    # 2) hub_catch: torque in through the dowels/screws (fixed), catch pin load out
    pin_c = L.polar(P.CATCH_R, L.BETA_CATCH, (0.0, PZ))
    tdir = (-math.sin(math.radians(L.BETA_CATCH)), math.cos(math.radians(L.BETA_CATCH)))   # +alpha tangent
    out.append(Case("hub_catch", "cocked 5 m: latch force on the catch pin", "y",
                    [BC("FIX", any_of(*[near_ycyl(x, z, 2.0, 0.8) for x, z in hj]))],
                    [Load("PIN", near_ycyl(pin_c[0], pin_c[1], 3.95, 0.6, toward=(-tdir[0], -tdir[1])),
                          (-F_c * tdir[0], 0.0, -F_c * tdir[1]))], size=3.0, pose=to_hub, sustained=True))
    # 3) hub_drum: cord tension (tangential at the drum, pulling down at the front in the cocked pose)
    out.append(Case("hub_drum", "cocked 5 m: cord tension on the drum", "y",
                    [BC("FIX", any_of(*[near_ycyl(x, z, 2.0, 0.8) for x, z in hj]))],
                    [Load("CORD", near_ycyl(0.0, PZ, 29.0, 0.8, P.Y_DRUM - 3, P.Y_DRUM + 3, toward=(1.0, 0.0)), (0.0, 0.0, -F_cord))],
                    size=3.0, pose=_rot(-L.A_REST + 0.0), sustained=True))
    # 4) ring gear: bore fixed, latch-pin force in, tooth reaction at the mesh carried by the bore
    lo = (L.LATCH_O[0], PZ + L.LATCH_O[1])
    mesh_pt = L.polar(L.RING_R, L.MOTOR_ANGLE - L.PSI_COCKED, (0.0, PZ))
    out.append(Case("ring_gear", "cocked 5 m: latch pin load + tooth load", "y",
                    [BC("BORE", near_ycyl(0.0, PZ, 11.0, 0.6)),
                     BC("MESH", lambda n: (np.hypot(n[:, 0] - mesh_pt[0], n[:, 2] - mesh_pt[1]) < 4.0), (1, 3))],
                    [Load("LATCH", near_ycyl(lo[0], lo[1], 1.95, 0.6, toward=(0.643, 0.766)), (F_c * 0.643, 0.0, F_c * 0.766))],
                    size=3.0, pose=to_ring, sustained=True,
                    note="ring frame (latched pose); latch force along the contact normal"))
    # 5) ring latch: pivot fixed, nose dowel load along the contact normal (into the latch)
    nd = (L.NOSE_DOWEL[0], PZ + L.NOSE_DOWEL[1])
    out.append(Case("ring_latch", "cocked 5 m: nose load", "y",
                    [BC("PIV", near_ycyl(lo[0], lo[1], 2.1, 0.6)),
                     BC("STOP", lambda n: np.hypot(n[:, 0] - (lo[0] + 10), n[:, 2] - (lo[1] + 6)) < 3.0, (1, 3))],
                    [Load("NOSE", near_ycyl(nd[0], nd[1], 1.95, 0.6, toward=(0.643, -0.766)), (F_c * 0.643, 0.0, -F_c * 0.766))],
                    size=2.0, pose=to_ring, sustained=True))
    # 6) side plates: flange screws fixed, half the hub reaction at the shaft bore
    F_hub = math.hypot(F_cord, F_c)
    for side, right in (("side_plate_left", False), ("side_plate_right", True)):
        out.append(Case(side, "cocked 5 m: shaft reaction", "y",
                        [BC("FLANGE", plane("z", L.BASE_H, 0.4)),
                         BC("AXIAL", near_ycyl(0.0, PZ, 4.1, 0.6), (2,))],      # shaft + spacer stack + caps
                        [Load("SHAFT", near_ycyl(0.0, PZ, 4.1, 0.6, toward=(F_c, -F_cord)), (F_c / 2, 0.0, -F_cord / 2))],
                        size=4.0, sustained=True))
    # 7) cup: fixed at the socket screws; 500 ml can centripetal on the floor + tangential on the back wall
    Lr, r = P.ARM_L, P.CAN_D / 2
    # envelope of the allowed settings: 330 ml at 5 m, 500 ml up to its spring-limited range (~3.3 m)
    F_cen = max(P.CANS["330"]["mass_full"] * w5.v_release ** 2 / m5.L,
                P.CANS["500"]["mass_full"] * 6.2 ** 2 / m5.L)
    floor_x = Lr + r + P.CUP_PAD
    back_z = PZ + r + P.CUP_PAD
    out.append(Case("cup", "release: centripetal envelope (330 @5 m / 500 @3.3 m)", "y",
                    [BC("SCREWS", any_of(*[near_ycyl(x, PZ, P.M3_CLEAR / 2, 0.6) for x in L.CUP_SCREW_X]))],
                    [Load("FLOOR", lambda n: (np.abs(n[:, 0] - floor_x) < 0.4) & (np.abs(n[:, 2] - PZ) < 8), (F_cen, 0, 0)),
                     Load("BACK", lambda n: (np.abs(n[:, 2] - back_z) < 0.4) & (np.abs(n[:, 0] - Lr) < 10), (0, 0, 40.0))],
                    size=2.5, pose=to_hub))
    # 7b) cup at the worst simulated can acceleration (Monte Carlo, 2 ms filtered), all of it on the
    #     floor (radial) plus the tangential back-wall load: envelope of the contact transients
    mc = Path(__file__).resolve().parent / "mc_results.json"
    if mc.exists():
        mcd = json.loads(mc.read_text())
        a_pk = max(mcd["calibrated"]["a_peak_max"], mcd["uncalibrated"]["a_peak_max"])
        F_pk = P.CANS["330"]["mass_full"] * 1.04 * a_pk          # Monte Carlo shots are 330 ml, mass +4 %
        out.append(Case("cup", f"sim peak can acceleration {a_pk:.0f} m/s2 (Monte Carlo worst)", "y",
                        [BC("SCREWS", any_of(*[near_ycyl(x, PZ, P.M3_CLEAR / 2, 0.6) for x in L.CUP_SCREW_X]))],
                        [Load("FLOOR", lambda n: (np.abs(n[:, 0] - floor_x) < 0.4) & (np.abs(n[:, 2] - PZ) < 8), (F_pk, 0, 0)),
                         Load("BACK", lambda n: (np.abs(n[:, 2] - back_z) < 0.4) & (np.abs(n[:, 0] - Lr) < 10), (0, 0, 40.0))],
                        size=2.5, pose=to_hub))
    # 8) stop bracket: flange screws fixed, absorber peak force along its axis
    tip, d = L.absorber_axis(0.0)
    out.append(Case("stop_bracket", "absorber peak 5 m", "y",
                    [BC("FL", any_of(*[near_ycyl(x, z, P.M3_CLEAR / 2, 0.6) for x, z in L._stop_bracket_holes(0.0)]))],
                    [Load("ABS", _bore_sel(tip, d, 7.2), (F_abs * d[0], 0, F_abs * d[1]))], size=2.5,
                    sustained=True, sustained_factor=(T_rest / ST.ABS_R) / F_abs,
                    note="sustained case = rest preload on the bottomed absorber (SF_creep)"))
    # 9) pulley bracket: screws fixed, resultant of the cord (down + back)
    px, pz = L.PULLEY_C
    out.append(Case("pulley_bracket", "cocked 5 m: cord over the pulley", "z",
                    [BC("SCR", any_of(*[near_zcyl(x, y, P.M3_CLEAR / 2, 0.6) for x, y in L._pulley_bracket_holes()]))],
                    [Load("AXLE", near_ycyl(px, pz, 4.05, 0.6, toward=(-1, -1)), (-F_cord, 0, -F_cord))], size=2.5,
                    sustained=True))
    # 10) spring yokes: rods fixed, 3 spring hooks pull
    out.append(Case("spring_yoke_front", "cocked 5 m: 3 springs", "z",
                    [BC("RODS", any_of(*[near_xcyl(y, P.SPRING_Z, 3.3, 0.6) for y in L.SPRING_ROD_Y]), (1, 2, 3))],
                    [Load("HOOKS", near_ycyl(None, None, 0, 0) if False else _yoke_dowel_sel(), (F_cord, 0, 0))],
                    size=2.0, sustained=True))      # held cocked 24 h (brief), not just the rest preload
    return out


def _bore_sel(tip, d, r):
    def f(n):
        rel = np.stack([n[:, 0] - tip[0], n[:, 2] - tip[1]], 1)
        along = rel @ np.array(d)
        perp = np.abs(rel @ np.array([-d[1], d[0]]))
        dist = np.hypot(perp, n[:, 1] - sum(P.Y_ABS) / 2)
        return (np.abs(dist - r) < 0.7) & (along > 40) & (along < 75)
    return f


def _yoke_dowel_sel():
    xf, xb, xaf, _ = L.spring_positions(86.6)
    xc = xf - 8.0
    return lambda n: (np.abs(np.hypot(n[:, 0] - xc, n[:, 2] - P.SPRING_Z) - 2.05) < 0.6)


def main(only: set[str] | None = None):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    old = {(r["part"], r["case"]): r for r in json.loads((OUT / "results.json").read_text())["cases"]} \
        if only and (OUT / "results.json").exists() else {}
    for c in cases():
        if only and c.part not in only:
            rows.append(old[(c.part, c.case)])
            continue
        try:
            r = run_case(c)
        except Exception as e:  # noqa: BLE001
            r = dict(part=c.part, case=c.case, error=str(e))
        rows.append(r)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    # preload loss for the Monte Carlo: deflection of the cord path under the cocked load
    defl = {r["part"]: r.get("u_max_mm", 0.0) for r in rows if "u_max_mm" in r}
    preload_loss = defl.get("pulley_bracket", 0) + defl.get("spring_yoke_front", 0) * 2 \
        + defl.get("hub_drum", 0) + 0.5 * (defl.get("side_plate_left", 0) + defl.get("side_plate_right", 0))
    out = dict(cases=rows, preload_loss_mm=preload_loss,
               note="preload_loss = elastic shortening of the spring/cord path at full cock (upper bound: max nodal deflections summed)")
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated parts to re-run (others are kept from results.json)")
    a = ap.parse_args()
    main(set(a.only.split(",")) if a.only else None)
