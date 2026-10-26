"""BOM.csv -> BOM.md with totals (hardware/electronics vs filament) and the budget check.

    python tools/bom.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET = 80.0


def load():
    with open(ROOT / "BOM.csv", newline="") as f:
        return list(csv.DictReader(f))


def totals(rows):
    hw = sum(float(r["buy_eur"]) for r in rows if r["group"] != "filament")
    fil = sum(float(r["buy_eur"]) for r in rows if r["group"] == "filament")
    return hw, fil


def main():
    rows = load()
    hw, fil = totals(rows)
    out = ["# Bill of materials", "",
           "Prices are what you pay for the pack you have to buy (AliExpress Choice / EU shop, EUR incl. VAT, "
           "seen 2026-10-25). `approx` = taken from a listing snippet or a USD mirror at 1 USD = 0.90 EUR; "
           "`unverified` = no price seen, estimate. Re-check in the app before ordering (research/parts_notes.md).", "",
           f"**Hardware + electronics: EUR {hw:.2f}** (budget EUR {BUDGET:.0f}: "
           f"{'within' if hw <= BUDGET else f'**over by EUR {hw - BUDGET:.2f}**'})  ",
           f"**Filament: EUR {fil:.2f}**  ",
           f"**Everything: EUR {hw + fil:.2f}**", ""]
    for grp in ("electronics", "button", "mechanical", "filament"):
        out += [f"## {grp.capitalize()}", "",
                "| id | item | spec | need | buy | EUR | price | AliExpress | Amazon.it | notes |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            if r["group"] == grp:
                out.append(f"| {r['id']} | {r['item']} | {r['spec']} | {r['qty_needed']} | {r['buy_qty']} | "
                           f"{float(r['buy_eur']):.2f} | {r['verified']} | [link]({r['source_ali']}) | "
                           f"[link]({r['source_amazon_it']}) | {r['notes']} |")
        out.append("")
    (ROOT / "BOM.md").write_text("\n".join(out))
    print(f"hardware+electronics EUR {hw:.2f}, filament EUR {fil:.2f}, total EUR {hw + fil:.2f}")


if __name__ == "__main__":
    main()
