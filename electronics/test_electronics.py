"""Consistency checks between electronics/ docs and the firmware pin maps.

    pytest electronics/test_electronics.py
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HAL = ROOT / "firmware/launcher/src/hal_esp32.cpp"
BTN = ROOT / "firmware/button/src/main.cpp"
FW_README = ROOT / "firmware/README.md"
PINMAP = HERE / "PINMAP.md"

PIN_RE = re.compile(r"constexpr\s+uint8_t\s+(kPin\w+)\s*=\s*(\d+)\s*;")


def firmware_pins(path: Path) -> dict[str, int]:
    pins = {name: int(n) for name, n in PIN_RE.findall(path.read_text(encoding="utf-8"))}
    assert pins, f"no kPin constants found in {path}"
    return pins


def md_section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert m, f"section '## {heading}' not found"
    return m.group(1)


def md_table(section: str) -> list[dict[str, str]]:
    rows = [l.strip() for l in section.splitlines() if l.strip().startswith("|")]
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    out = []
    for r in rows[2:]:  # skip header + separator
        cells = [c.strip() for c in r.strip("|").split("|")]
        out.append(dict(zip(header, cells)))
    return out


def pinmap_rows(heading: str) -> list[dict[str, str]]:
    return md_table(md_section(PINMAP.read_text(encoding="utf-8"), heading))


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def readme_launcher_nets() -> dict[int, str]:
    text = FW_README.read_text(encoding="utf-8")
    sec = re.search(r"^### Launcher\s*$(.*?)(?=^#)", text, re.M | re.S).group(1)
    return {int(r["GPIO"]): r["Signal"] for r in md_table(sec)}


@pytest.mark.parametrize("heading,src", [("Launcher", HAL), ("Button", BTN)])
def test_every_firmware_gpio_is_in_pinmap(heading: str, src: Path) -> None:
    fw = firmware_pins(src)
    rows = pinmap_rows(heading)
    by_const = {r["Firmware const"].strip("`"): r for r in rows}
    assert set(by_const) == set(fw), "PINMAP constants differ from firmware"
    for const, gpio in fw.items():
        assert int(by_const[const]["GPIO"]) == gpio, f"{const}: firmware GPIO{gpio}, PINMAP {by_const[const]['GPIO']}"
    gpios = [int(r["GPIO"]) for r in rows]
    assert len(gpios) == len(set(gpios)), "duplicate GPIO in PINMAP"


@pytest.mark.parametrize("heading,src", [("Launcher", HAL), ("Button", BTN)])
def test_net_names_match_firmware_constants(heading: str, src: Path) -> None:
    """Net name must carry the constant's meaning (kPinArmHome -> SW_ARM_HOME, kPinBatt -> BATT_SENSE)."""
    rows = {r["Firmware const"].strip("`"): r for r in pinmap_rows(heading)}
    alias = {"kPinTestBtn": "BTNTEST"}  # README calls it BTN_TEST
    for const in firmware_pins(src):
        key = alias.get(const, norm(const[len("kPin"):]))
        assert key in norm(rows[const]["Net"]), f"{const} -> net {rows[const]['Net']!r}"


def test_launcher_nets_match_firmware_readme() -> None:
    readme = readme_launcher_nets()
    rows = {int(r["GPIO"]): r["Net"] for r in pinmap_rows("Launcher")}
    assert set(readme) == set(rows) == set(firmware_pins(HAL).values())
    for gpio, sig in readme.items():
        assert norm(sig) == norm(rows[gpio]), f"GPIO{gpio}: README {sig!r} vs PINMAP {rows[gpio]!r}"


def test_strapping_pins_are_flagged() -> None:
    rows = {int(r["GPIO"]): r for r in pinmap_rows("Launcher")}
    for g in (2, 8, 9):
        assert "strapping" in rows[g]["Notes"].lower(), f"GPIO{g} notes must mention strapping"
    assert "1k" in rows[21]["Connected part"].lower() or "1 k" in rows[21]["Notes"].lower()


@pytest.mark.parametrize("name", ["wiring_launcher.svg", "wiring_button.svg"])
def test_svgs_exist_and_are_valid_xml(name: str) -> None:
    path = HERE / name
    assert path.is_file(), f"{name} missing: run python electronics/make_wiring.py"
    root = ET.parse(path).getroot()
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert "@import" not in path.read_text(encoding="utf-8"), "no external fonts"


@pytest.mark.parametrize("heading,svg", [("Launcher", "wiring_launcher.svg"), ("Button", "wiring_button.svg")])
def test_every_net_is_labelled_in_svg(heading: str, svg: str) -> None:
    root = ET.parse(HERE / svg).getroot()
    texts = " ".join("".join(t.itertext()) for t in root.iter("{http://www.w3.org/2000/svg}text"))
    for r in pinmap_rows(heading):
        assert f"GPIO{r['GPIO']} → {r['Net']}" in texts, f"{svg}: no label for GPIO{r['GPIO']} {r['Net']}"


def test_svgs_are_up_to_date() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("make_wiring", HERE / "make_wiring.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert (HERE / "wiring_launcher.svg").read_text(encoding="utf-8") == mod.launcher()
    assert (HERE / "wiring_button.svg").read_text(encoding="utf-8") == mod.button()
