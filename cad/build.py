"""Build everything from the parametric sources.

    python -m cad.build            # STEP + STL + 3MF + mass props + manifest + renders
    python -m cad.build --no-render

Outputs
  cad/step/<part>.step       assembly pose (for Fusion 360), plus launcher_assembly.step
  cad/stl/<part>.stl         print pose (flat face on the bed, oriented for layer strength)
  cad/3mf/plate_<X>.3mf      one Bambu Studio project per plate (PETG / TPU), per-object settings
  cad/mass_props.json        arm assembly inertia about the pivot (feeds calc/ and sim/)
  cad/manifest.json          per part: material, plate, orientation, settings, grams, time
  cad/renders/*.png
"""

from __future__ import annotations

import argparse
import json
import math
import os
import xml.sax.saxutils as su
import zipfile
from pathlib import Path

import build123d as bd
import numpy as np

from cad import checks as C
from cad import params as P
from cad.src import button as BTN
from cad.src import launcher as L

ROOT = Path(__file__).resolve().parent
DIRS = {k: ROOT / k for k in ("step", "stl", "3mf", "renders")}

# ---------------------------------------------------------------------------
# Part catalogue (launcher + button)
# ---------------------------------------------------------------------------
BUTTON_SPECS = [
    L.PartSpec("btn_shell", "PETG", 1, L.FLAT, walls=4, infill=20, plate="M", loaded=False, color=L.WHITE,
               note="upright; USB-C window top is a 10 mm bridge"),
    L.PartSpec("btn_cap", "PETG", 1, L.UPSIDE, walls=4, infill=25, plate="M", loaded=True, color=L.ORANGE,
               note="top face down; snap ring has a 45 deg ramp"),
    L.PartSpec("btn_switch_plate", "PETG", 1, L.FLAT, walls=4, infill=40, plate="M", color=L.GREY),
    L.PartSpec("btn_tray", "PETG", 1, L.FLAT, walls=3, infill=30, plate="M", loaded=False, color=L.GREY),
    L.PartSpec("btn_foot_ring", "TPU", 1, L.FLAT, walls=3, infill=100, plate="T", loaded=False, color=L.BLACK),
]
SPECS = {s.name: s for s in L.PARTS + BUTTON_SPECS}


def solids_rest() -> dict[str, bd.Part]:
    asm = L.assembly("rest", with_hardware=False, with_can=False)
    asm["foot"] = L.foot()
    asm["switch_bracket"] = L.switch_bracket()
    asm["sensor_bracket"] = L.sensor_bracket()
    b = BTN.assembly(0.0)
    asm.update({k: v for k, v in b.items() if not k.startswith("hw_")})
    return asm


def effective_volume(part_vol: float, area: float, spec: L.PartSpec) -> float:
    """Printed (not solid) volume: perimeter shell + skins at 100 %, the rest at infill %."""
    t_shell = 0.5 * (spec.walls * 0.42 + 5 * spec.layer)    # average of side walls and top/bottom skins
    shell = min(part_vol, area * t_shell)
    return shell + (part_vol - shell) * spec.infill / 100.0


DENSITY = {"PETG": 1.27e-3, "TPU": 1.22e-3, "PLA": 1.24e-3}   # g/mm^3 (Bambu TDS)
VOL_FLOW = {"PETG": 9.0, "TPU": 3.0, "PLA": 11.0}             # mm^3/s average incl. slow walls (A1, 0.4 mm)


def print_estimate(part: bd.Part, spec: L.PartSpec, posed: bd.Part) -> dict:
    vol = part.volume
    area = part.area
    veff = effective_volume(vol, area, spec)
    grams = veff * DENSITY[spec.material]
    h = posed.bounding_box().max.Z
    layers = h / spec.layer
    t_s = veff / VOL_FLOW[spec.material] + layers * 1.2 + area * 0.004   # extrusion + layer change + travel
    return dict(volume_solid_mm3=vol, volume_printed_mm3=veff, grams=grams, minutes=t_s / 60, height=h)


# ---------------------------------------------------------------------------
# Mass properties of the arm assembly about the pivot axis
# ---------------------------------------------------------------------------
def mass_props() -> dict:
    parts = {"hub_drum": L.hub_drum_local(), "arm": L.arm_local(), "hub_catch": L.hub_catch_local(),
             "cup": L.cup_local(), "cup_pad": L.cup_pad_local()}
    pin, roller = L.catch_pin_local()
    steel = {"catch_pin": (pin, 7.85e-6), "catch_roller": (roller, None)}
    I = 0.0
    m_tot = 0.0
    mx = 0.0
    I_beam_cup = 0.0
    detail = {}
    for name, part in parts.items():
        spec = SPECS[name]
        mesh = C.to_mesh(part, tol=0.2, ang=0.3)
        fill = effective_volume(part.volume, part.area, spec) / part.volume
        rho = DENSITY[spec.material] * 1e-3 * fill          # kg/mm^3 (printed, smeared)
        # inertia about the pivot axis (y through (0, PZ)) via tetra decomposition of the mesh
        Ixx, m, cx = _inertia_about_pivot(mesh, rho)
        I += Ixx
        m_tot += m
        mx += m * cx
        if name in ("cup", "cup_pad"):
            I_beam_cup += Ixx
        detail[name] = dict(mass_kg=m, I_kgm2=Ixx, fill=fill)
    # beam outside the root radius (r > 45 mm) belongs to the "beam + cup" inertia used in stress.py
    hub_mesh = C.to_mesh(parts["arm"], tol=0.2, ang=0.3)
    beam = hub_mesh.slice_plane([45.0, 0, 0], [1, 0, 0], cap=True)
    fillh = detail["arm"]["fill"]
    Ib, mb, _ = _inertia_about_pivot(beam, DENSITY["PETG"] * 1e-3 * fillh)
    I_beam_cup += Ib
    # steel pin (8x30) and 608 roller (12 g)
    pc = L.polar(P.CATCH_R, L.BETA_CATCH)
    r2 = (pc[0] ** 2 + pc[1] ** 2) * 1e-6
    for nm, mm in (("catch_pin", 0.0118), ("catch_roller", 0.012)):
        I += mm * r2
        m_tot += mm
        mx += mm * pc[0]
        detail[nm] = dict(mass_kg=mm, I_kgm2=mm * r2)
    return dict(arm_assembly=dict(I_arm=I, m_arm=m_tot, l_arm_cg=abs(mx / m_tot) / 1000.0, I_beam_cup=I_beam_cup),
                detail=detail, note="printed density smeared by the walls/infill fill fraction")


def _inertia_about_pivot(mesh, rho):
    """Mass, inertia about the y axis through (0, PZ) and CG x (mm), by signed tetrahedra."""
    v = mesh.vertices.copy()
    v[:, 2] -= P.PIVOT_H
    tri = v[mesh.faces]
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    vol6 = np.einsum("ij,ij->i", a, np.cross(b, c))
    vol = vol6 / 6.0
    m = rho * vol.sum()
    cen = (a + b + c) / 4.0
    cx = (vol * cen[:, 0]).sum() / vol.sum()

    def second(i):
        # integral of x_i^2 over each tetra (with origin vertex) = vol/10 * (sum of squares + cross terms)
        ai, bi, ci = a[:, i], b[:, i], c[:, i]
        return vol / 10.0 * (ai * ai + bi * bi + ci * ci + ai * bi + bi * ci + ci * ai)
    sxx, szz = second(0).sum(), second(2).sum()
    I = rho * (sxx + szz) * 1e-6          # kg m^2 (mm^2 -> m^2)
    return float(I), float(m), float(cx)


# ---------------------------------------------------------------------------
# Plates and 3MF
# ---------------------------------------------------------------------------
def pack(items, bed=(256.0, 256.0), gap=6.0):
    """Shelf packing of (name, w, d). Returns placements or raises if it doesn't fit one plate."""
    items = sorted(items, key=lambda t: -t[2])
    x = y = shelf_h = 0.0
    pos = {}
    for name, w, d in items:
        if w > bed[0] or d > bed[1]:
            raise ValueError(f"{name} {w:.0f}x{d:.0f} exceeds the bed")
        if x + w > bed[0]:
            x, y, shelf_h = 0.0, y + shelf_h + gap, 0.0
        if y + d > bed[1]:
            raise ValueError("plate overflow")
        pos[name] = (x + w / 2, y + d / 2)
        x += w + gap
        shelf_h = max(shelf_h, d)
    return pos


def fit_on_bed(posed: bd.Part) -> tuple[bd.Part, float]:
    """Rotate about Z (0..90 deg) to minimise the footprint; returns part and angle."""
    best = None
    for ang in range(0, 91, 3):
        p = bd.Rot(0, 0, ang) * posed
        bb = p.bounding_box()
        w, d = bb.size.X, bb.size.Y
        score = max(w, d) if (w <= 256 and d <= 256) else 1e9 + max(w, d)
        if best is None or score < best[0]:
            best = (score, ang, p)
    p = best[2]
    bb = p.bounding_box()
    return bd.Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * p, best[1]


def write_3mf(path: Path, objects: list[dict], plate: str):
    """Minimal 3MF (core spec) + Bambu Studio metadata (project + per-object settings)."""
    model = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
             '<metadata name="Application">beer-launcher cad/build.py</metadata><resources>']
    build = ["<build>"]
    settings = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    for i, o in enumerate(objects, start=1):
        mesh = o["mesh"]
        vs = "".join(f'<vertex x="{v[0]:.4f}" y="{v[1]:.4f}" z="{v[2]:.4f}"/>' for v in mesh.vertices)
        ts = "".join(f'<triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>' for t in mesh.faces)
        model.append(f'<object id="{i}" name="{su.escape(o["name"])}" type="model"><mesh><vertices>{vs}</vertices>'
                     f'<triangles>{ts}</triangles></mesh></object>')
        tx, ty = o["xy"]
        build.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {tx:.3f} {ty:.3f} 0" printable="1"/>')
        sp = o["spec"]
        settings += [f'<object id="{i}">', f'<metadata key="name" value="{su.escape(o["name"])}"/>',
                     f'<metadata key="wall_loops" value="{sp.walls}"/>',
                     f'<metadata key="sparse_infill_density" value="{sp.infill}%"/>',
                     '<metadata key="sparse_infill_pattern" value="gyroid"/>',
                     f'<metadata key="layer_height" value="{sp.layer:.2f}"/>',
                     '<metadata key="top_shell_layers" value="5"/>', '<metadata key="bottom_shell_layers" value="4"/>',
                     '<metadata key="enable_support" value="0"/>', "</object>"]
    model.append("</resources>")
    build.append("</build>")
    model += build + ["</model>"]
    settings.append("</config>")
    mat = objects[0]["spec"].material
    project = {
        "printer_model": "Bambu Lab A1", "printer_settings_id": "Bambu Lab A1 0.4 nozzle",
        "nozzle_diameter": ["0.4"], "filament_type": [mat],
        "filament_settings_id": ["Bambu PETG HF @BBL A1" if mat == "PETG" else "Bambu TPU 95A HF @BBL A1"],
        "print_settings_id": "0.20mm Standard @BBL A1", "layer_height": "0.2",
        "enable_support": "0", "support_type": "normal(manual)", "brim_type": "auto_brim",
        "curr_bed_type": "Textured PEI Plate", "seam_position": "aligned",
        "beer_launcher_plate": plate,
    }
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "\n".join(model))
        z.writestr("Metadata/model_settings.config", "\n".join(settings))
        z.writestr("Metadata/project_settings.config", json.dumps(project, indent=1))


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------
def _export_stl(part, path):
    """STL via build123d; if the tessellation leaves gaps, re-mesh with trimesh and repair."""
    import trimesh
    bd.export_stl(part, str(path), tolerance=0.02, angular_tolerance=0.15)
    m = trimesh.load(path)
    for tol, ang in ((0.01, 0.1), (0.05, 0.2), (0.03, 0.12), (0.1, 0.3)):
        if m.is_watertight:
            break
        bd.export_stl(part, str(path), tolerance=tol, angular_tolerance=ang)
        m = trimesh.load(path)
    if not m.is_watertight:
        m.merge_vertices()
        trimesh.repair.fill_holes(m)
        trimesh.repair.fix_normals(m)
        m.export(path)


def build(render=True):
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    for old in list(DIRS["3mf"].glob("*.3mf")) + list(DIRS["stl"].glob("*.stl")):
        old.unlink()                     # plate names change when the packing changes
    solids = solids_rest()
    manifest = {}
    plates: dict[str, list] = {}
    for name, part in solids.items():
        spec = SPECS[name]
        bd.export_step(part, str(DIRS["step"] / f"{name}.step"))
        posed = C.print_pose(part, spec.print_rot)
        posed, zrot = fit_on_bed(posed)
        _export_stl(posed, DIRS["stl"] / f"{name}.stl")
        bb = posed.bounding_box()
        est = print_estimate(part, spec, posed)
        manifest[name] = dict(material=spec.material, qty=spec.qty, plate=spec.plate, walls=spec.walls,
                              infill=spec.infill, layer=spec.layer, print_rot=spec.print_rot, bed_zrot=zrot,
                              size=[bb.size.X, bb.size.Y, bb.size.Z], loaded=spec.loaded, note=spec.note,
                              **{k: round(v, 2) for k, v in est.items()})
        for _ in range(spec.qty):
            plates.setdefault(spec.material, []).append((name, posed, spec))
    # assembly STEP
    asm = L.assembly("rest")
    comp = bd.Compound(children=[p for p in asm.values()])
    bd.export_step(comp, str(DIRS["step"] / "launcher_assembly.step"))
    # plates -> 3MF
    plate_info = {}
    groups = {}
    for mat, items in sorted(plates.items()):
        # first-fit decreasing into as many plates as needed
        items = sorted(items, key=lambda t: -(t[1].bounding_box().size.X * t[1].bounding_box().size.Y))
        bins: list[list] = []
        for it in items:
            for b in bins:
                try:
                    pack([(f"{n}#{i}", p.bounding_box().size.X, p.bounding_box().size.Y)
                          for i, (n, p, _) in enumerate(b + [it])])
                    b.append(it)
                    break
                except ValueError:
                    continue
            else:
                bins.append([it])
        for k, b in enumerate(bins, start=1):
            groups[f"{mat}_{k}"] = b
    for pl, items in groups.items():
        for n, _, _ in items:
            manifest[n]["plate"] = pl
        sizes = [(f"{n}#{i}", p.bounding_box().size.X, p.bounding_box().size.Y) for i, (n, p, _) in enumerate(items)]
        pos = pack(sizes)
        objs = []
        for i, (n, p, sp) in enumerate(items):
            mesh = C.to_mesh(p, tol=0.05, ang=0.2)
            x, y = pos[f"{n}#{i}"]
            objs.append(dict(name=n, mesh=mesh, xy=(x, y), spec=sp))
        write_3mf(DIRS["3mf"] / f"plate_{pl}.3mf", objs, pl)
        g = sum(manifest[n]["grams"] for n, _, _ in items)
        t = sum(manifest[n]["minutes"] for n, _, _ in items) + 6.0  # + heat-up and auto-level
        plate_info[pl] = dict(parts=[n for n, _, _ in items], material=items[0][2].material,
                              grams=round(g, 1), minutes=round(t, 0))
    mp = mass_props()
    (ROOT / "mass_props.json").write_text(json.dumps(mp, indent=1))
    (ROOT / "manifest.json").write_text(json.dumps(dict(parts=manifest, plates=plate_info), indent=1))
    if render:
        from cad import render as R
        R.render_all()
    return manifest, plate_info, mp


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    man, plates, mp = build(render=not a.no_render)
    tot_g = sum(p["grams"] for p in plates.values())
    tot_t = sum(p["minutes"] for p in plates.values())
    for k, v in plates.items():
        print(f"plate {k}: {v['material']} {v['grams']:.0f} g {v['minutes']/60:.1f} h  {v['parts']}")
    print(f"TOTAL {tot_g:.0f} g, {tot_t/60:.1f} h")
    print("mass props", mp["arm_assembly"])
