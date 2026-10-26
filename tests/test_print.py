"""Gate 4 print checks on the exported STLs (print pose, as they go on the bed)."""

import pytest
import trimesh

from cad import checks as C
from cad import params as P
from tests.conftest import ROOT
import json

MANIFEST = json.loads((ROOT / "cad" / "manifest.json").read_text())
PARTS = sorted(MANIFEST["parts"])
BED = 256.0
MIN_WALL = 1.6
# Thin by design, not load-bearing (documented in PRINT_GUIDE.md): TPU pads/feet and the snap cap
# skirt are checked against 1.2 mm (3 perimeters at 0.4).
THIN_OK = {"cup_pad": 1.2, "foot": 1.2, "btn_foot_ring": 1.2, "btn_cap": 1.2}


def _mesh(name):
    return trimesh.load(ROOT / "cad" / "stl" / f"{name}.stl", force="mesh")


@pytest.mark.parametrize("name", PARTS)
def test_fits_bed(name):
    ext = _mesh(name).extents
    assert max(ext[0], ext[1]) <= BED - 1 and ext[2] <= BED, f"{name} {ext}"   # A1: 256 x 256 x 256 printable


@pytest.mark.parametrize("name", PARTS)
def test_manifold(name):
    m = _mesh(name)
    assert m.is_watertight and m.is_winding_consistent and m.volume > 0, name
    assert m.bounds[0][2] == pytest.approx(0.0, abs=0.01), f"{name} not on the bed"


@pytest.mark.parametrize("name", PARTS)
def test_overhang(name):
    bad, _, worst = C.overhang_report(_mesh(name), max_deg=50.0, bridge_max=30.0)
    assert bad <= 5.0, f"{name}: {bad:.1f} mm2 of >50 deg overhang (widest {worst:.1f} mm)"


@pytest.mark.parametrize("name", PARTS)
def test_min_wall(name):
    t1, _ = C.min_wall(_mesh(name))
    assert t1 >= THIN_OK.get(name, MIN_WALL) - 0.05, f"{name}: 1st-percentile wall {t1:.2f} mm"


def test_loaded_parts_have_4_walls():
    for n, p in MANIFEST["parts"].items():
        if p["loaded"] and p["material"] == "PETG":
            assert p["walls"] >= 4, n


def test_materials_rule():
    for n, p in MANIFEST["parts"].items():
        assert p["material"] in ("PETG", "PLA", "TPU"), n
        if p["material"] == "PLA":
            assert not p["loaded"], f"{n}: PLA only for unloaded cosmetic parts"


def test_plates_have_time_and_grams():
    plates = MANIFEST["plates"]
    assert plates
    for pl, info in plates.items():
        assert (ROOT / "cad" / "3mf" / f"plate_{pl}.3mf").exists(), pl
        assert info["grams"] > 0 and info["minutes"] > 0, pl
    on_plates = sorted(n for info in plates.values() for n in info["parts"])
    expected = sorted(n for n, p in MANIFEST["parts"].items() for _ in range(p["qty"]))
    assert on_plates == expected


def test_insert_hole_matches_insert():
    # 0.1 mm press per side on a 4.2 OD insert (brief: OD 4.0-4.2, L 4-5.7)
    assert P.M3_INSERT_OD - P.M3_INSERT_HOLE == pytest.approx(0.2)
    assert P.M3_INSERT_DEPTH >= 5.7
