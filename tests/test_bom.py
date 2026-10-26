"""BOM <-> CAD: every insert hole and bearing bore in the exported parts has a BOM line with
enough parts, and BOM.md is generated from BOM.csv."""

import csv
import json

import build123d as bd
import pytest

from cad.hardware import census
from tests.conftest import ROOT


@pytest.fixture(scope="module")
def bom():
    with open(ROOT / "BOM.csv", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def cad_counts():
    parts = json.loads((ROOT / "cad" / "manifest.json").read_text())["parts"]
    tot = {}
    for n, spec in parts.items():
        for k, v in census(bd.import_step(str(ROOT / "cad" / "step" / f"{n}.step"))).items():
            tot[k] = tot.get(k, 0) + v * spec["qty"]
    return tot


@pytest.mark.parametrize("key", ["m3_insert", "bore_608"])
def test_cad_holes_covered_by_bom(bom, cad_counts, key):
    rows = [r for r in bom if r["cad_key"] == key]
    assert rows, f"no BOM line for {key}"
    need = sum(float(r["qty_needed"]) for r in rows)
    buy = sum(float(r["buy_qty"]) for r in rows)
    if key == "m3_insert":
        assert need == cad_counts[key], f"{key}: BOM says {need}, CAD has {cad_counts[key]}"
    else:   # bearings also sit on the catch pin and the pulley axle (no printed bore)
        assert need >= cad_counts[key], f"{key}: BOM says {need}, CAD has {cad_counts[key]} printed bores"
    assert buy >= need


def test_screws_cover_inserts(bom, cad_counts):
    screws = next(r for r in bom if r["id"] == "M11")
    assert float(screws["qty_needed"]) >= cad_counts["m3_insert"]


def test_every_line_has_two_sources_and_price(bom):
    for r in bom:
        assert r["source_ali"].startswith("http") and r["source_amazon_it"].startswith("http"), r["id"]
        assert float(r["buy_eur"]) >= 0
        assert r["verified"] in ("approx", "unverified", "checked"), r["id"]


def test_bom_md_up_to_date(bom):
    import subprocess
    import sys
    before = (ROOT / "BOM.md").read_text()
    subprocess.run([sys.executable, str(ROOT / "tools" / "bom.py")], check=True, capture_output=True)
    assert (ROOT / "BOM.md").read_text() == before


def test_mains_supply_is_ce_brick(bom):
    psu = [r for r in bom if "PSU" in r["item"]]
    assert len(psu) == 1 and "Mean Well" in psu[0]["item"] and "CE" in psu[0]["spec"]
