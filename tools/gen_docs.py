"""Fill the generated blocks (<!-- BEGIN:x --> ... <!-- END:x -->) in the guides from the build and
simulation outputs, so the numbers in the docs are the numbers the code produced.

    python tools/gen_docs.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _j(p):
    f = ROOT / p
    return json.loads(f.read_text()) if f.exists() else None


def fill(path: Path, blocks: dict[str, str]):
    s = path.read_text()
    for k, v in blocks.items():
        s, n = re.subn(rf"(<!-- BEGIN:{k} -->\n).*?(<!-- END:{k} -->)", lambda m: m.group(1) + v.rstrip() + "\n" + m.group(2),
                       s, flags=re.S)
        assert n == 1, f"{path.name}: block {k} missing"
    path.write_text(s)


def numbers() -> dict:
    man = _j("cad/manifest.json")
    plates = man["plates"]
    with open(ROOT / "BOM.csv", newline="") as f:
        bom = list(csv.DictReader(f))
    hw = sum(float(r["buy_eur"]) for r in bom if r["group"] != "filament")
    fil = sum(float(r["buy_eur"]) for r in bom if r["group"] == "filament")
    gates = {g["name"]: g for g in _j("calc/results.json")["gate2"]}
    mc = _j("sim/mc_results.json")
    feed = _j("sim/feed_results.json")["summary"]
    fea = _j("sim/fea/results.json")["cases"]
    worst = min(fea, key=lambda c: min([c["sf_static"]] + [c[k] for k in ("sf_fatigue", "sf_creep") if c.get(k)]))
    return dict(
        grams=sum(p["grams"] for p in plates.values()), hours=sum(p["minutes"] for p in plates.values()) / 60,
        n_plates=len(plates), n_parts=sum(p["qty"] for p in man["parts"].values()),
        petg=sum(p["grams"] for p in plates.values() if p["material"] == "PETG"),
        tpu=sum(p["grams"] for p in plates.values() if p["material"] == "TPU"),
        bom_hw=hw, bom_fil=fil,
        lat4=gates["Press->launch <= 2.5 s at 4 m"]["value"], lat5=gates["Press->launch <= 2.5 s at 5 m"]["value"],
        vcatch=gates["Catch speed <= 4 m/s at 4 m"]["value"], cycle=gates["Cycle <= 8 s"]["value"],
        batt=gates["Battery >= 3 months"]["value"],
        sd_cal=mc["calibrated"]["range_sd"], sd_unc=mc["uncalibrated"]["range_sd"], n_cal=mc["calibrated"]["n"],
        n_unc=mc["uncalibrated"]["n"], peak=mc["calibrated"]["peak_max"], vc_mc=mc["calibrated"]["v_catch_mean"],
        a_peak=mc["calibrated"]["a_peak_max"],
        feed_cycles=feed["total_cycles"], feed_bad=feed["jam_cycles"] + feed["double_feed_cycles"] + feed["early_release"],
        fea_worst=f"{worst['part']} ({worst['case']})",
        fea_worst_sf=min([worst["sf_static"]] + [worst[k] for k in ("sf_fatigue", "sf_creep") if worst.get(k)]),
    )


def main():
    man = _j("cad/manifest.json")
    n = numbers()
    totals = (f"**{n['n_parts']} printed parts on {n['n_plates']} plates: {n['grams']:.0f} g "
              f"(PETG {n['petg']:.0f} g, TPU {n['tpu']:.0f} g), {n['hours']:.1f} h of printing** "
              "(slicer-independent estimate from part volume, walls and infill; Bambu Studio will differ by about ±15 %).")
    rows = ["| part | material | qty | walls | infill | grams | time (h) | plate | note |", "|---|---|---|---|---|---|---|---|---|"]
    for k, p in sorted(man["parts"].items()):
        rows.append(f"| {k} | {p['material']} | {p['qty']} | {p['walls']} | {p['infill']} % | {p['grams']:.0f} | "
                    f"{p['minutes'] / 60:.1f} | {p['plate']} | {p['note']} |")
    prow = ["| plate file | material | grams | time (h) | parts |", "|---|---|---|---|---|"]
    for k, p in sorted(man["plates"].items(), key=lambda kv: (kv[0].split('_')[0], int(kv[0].split('_')[1]))):
        prow.append(f"| `plate_{k}.3mf` | {p['material']} | {p['grams']:.0f} | {p['minutes'] / 60:.1f} | {', '.join(p['parts'])} |")
    fill(ROOT / "PRINT_GUIDE.md", dict(totals=totals, parts="\n".join(rows), plates="\n".join(prow)))
    key = "\n".join([
        "| | value | target |", "|---|---|---|",
        f"| BOM, hardware + electronics | **EUR {n['bom_hw']:.2f}** (+ EUR {n['bom_fil']:.0f} filament) | <= EUR 80 (**over**, see REPORT) |",
        f"| Print | {n['grams']:.0f} g, {n['hours']:.1f} h, {n['n_plates']} plates | fits 256 x 256 x 256 |",
        f"| Dispersion at 4 m (calibrated, {n['n_cal']} shots) | **sd {n['sd_cal'] * 100:.1f} cm** (uncalibrated {n['sd_unc'] * 100:.1f} cm) | <= 25 cm |",
        f"| Catch speed at 4 m | {n['vc_mc']:.2f} m/s (physics minimum 5.8) | <= 4 m/s (**impossible beyond 2.06 m**) |",
        f"| Peak height | {n['peak']:.2f} m max | <= 2.3 m |",
        f"| Press -> launch | 4 m: {n['lat4']:.2f} s, 5 m: {n['lat5']:.2f} s | <= 2.5 s (5 m **misses**) |",
        f"| Cycle time | {n['cycle']:.1f} s | <= 8 s |",
        f"| Feed (escapement) | {n['feed_cycles'] - n['feed_bad']}/{n['feed_cycles']} single feeds | single feed |",
        f"| Weakest printed part | SF {n['fea_worst_sf']:.2f}: {n['fea_worst']} | >= 2.5 |",
        f"| Button battery | {n['batt']:.1f} months | >= 3 months |",
    ])
    fill(ROOT / "README.md", dict(key=key))
    gates = ["| check | value | result |", "|---|---|---|"] + [
        f"| {g['name']} | {g['value']:.3f} | {'PASS' if g['ok'] else '**FAIL**'} |" for g in _j("calc/results.json")["gate2"]]
    fea = ["| part | case | vm p99.5 [MPa] | vm outside load zone | SF static | SF fatigue 10^3 | SF creep 24 h | min |",
           "|---|---|---|---|---|---|---|---|"]
    for c in _j("sim/fea/results.json")["cases"]:
        sfs = [c["sf_static"]] + [c[k] for k in ("sf_fatigue", "sf_creep") if c.get(k)]
        fea.append(f"| {c['part']} | {c['case']} | {c['vm_p995']:.2f} | {c.get('vm_far_p995', c['vm_p995']):.2f} | "
                   f"{c['sf_static']:.2f} | {c.get('sf_fatigue') or 0:.2f} | "
                   f"{('%.2f' % c['sf_creep']) if c.get('sf_creep') else '-'} | **{min(sfs):.2f}** |")
    fea.append(f"\nPreload lost to frame/cord-path deflection at full cock: {_j('sim/fea/results.json')['preload_loss_mm']:.2f} mm "
               "(fed into the Monte Carlo study as a per-unit loss).")
    val = ["| quantity | calc | sim | diff | explanation (> 15 %) |", "|---|---|---|---|---|"] + [
        f"| {r['quantity']} [{r['unit']}] | {r['calc']:.3f} | {r['sim']:.3f} | {r['diff_pct']:+.1f} % | {r['explanation'] or '-'} |"
        for r in _j("sim/validation.json")["rows"]]
    mc = _j("sim/mc_results.json")
    a = mc["calibrated"]["a_peak_max"]
    m_can = 0.370
    can = "\n".join([
        f"- Peak can acceleration, 2 ms filtered, worst of {mc['calibrated']['n'] + mc['uncalibrated']['n']} simulated shots: "
        f"**{a:.0f} m/s2 ({a / 9.81:.0f} g)**, mostly centripetal, across the can axis.",
        f"- Extra liquid pressure across the 66 mm diameter: rho a D = {1000 * a * 0.0662 / 1e5:.2f} bar. Beer is at 2.0-2.5 bar, "
        f"so the peak is {2.5 + 1000 * a * 0.0662 / 1e5:.1f} bar against the 6.2 bar (90 psi) buckle requirement for "
        f"beverage cans [C4]: **SF {6.2 / (2.5 + 1000 * a * 0.0662 / 1e5):.1f}**.",
        f"- Side-wall load on the 2 mm TPU pad: m a = {m_can * a:.0f} N, spread over a line contact of about 115 x 10 mm "
        f"= {m_can * a / (115 * 10):.2f} MPa. That is below the can's own internal pressure support, and far below the "
        "~900 N axial benchmark [C5].",
        "- For comparison, a 1 m drop onto tiles stops the can in about 1 mm: roughly 10 000 m/s2 (1000 g). Cans survive this "
        f"most of the time, with a dent. The launch is about {10000 / a:.0f}x gentler.",
    ])
    fill(ROOT / "REPORT.md", dict(key=key, gates="\n".join(gates), fea="\n".join(fea), validation="\n".join(val), can=can))
    print(json.dumps(n, indent=1))


if __name__ == "__main__":
    main()
