"""Build the phone-readable build-guide page (dist/guide.html) from the repo docs and outputs.

    python tools/make_guide_page.py
"""

from __future__ import annotations

import base64
import csv
import html
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gen_docs  # noqa: E402

OUT = ROOT / "dist" / "guide.html"


# ---------------------------------------------------------------- markdown --
def _inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?!\w)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)            # repo-relative links: keep the text
    return t


def md(src: str) -> str:
    """Small Markdown subset: headings, paragraphs, nested lists, tables, code fences."""
    lines = src.splitlines()
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln.startswith("<!--"):
            i += 1
            continue
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append('<div class="scroll"><pre><code>' + html.escape("\n".join(lines[i + 1:j])) + "</code></pre></div>")
            i = j + 1
            continue
        m = re.match(r"(#{1,4}) (.*)", ln)
        if m:
            lvl = min(len(m.group(1)) + 1, 4)
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[2:]]
            t = "<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f'<div class="scroll"><table>{t}</tbody></table></div>')
            continue
        if re.match(r"\s*([-*]|\d+\.) ", ln):
            block = []
            while i < len(lines) and (re.match(r"\s*([-*]|\d+\.) ", lines[i]) or (lines[i].startswith("   ") and lines[i].strip())):
                block.append(lines[i])
                i += 1
            out.append(_list(block))
            continue
        para = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"(#|\||```|\s*([-*]|\d+\.) )", lines[i]):
            para.append(lines[i])
            i += 1
        out.append("<p>" + _inline(" ".join(p.strip() for p in para)) + "</p>")
    return "\n".join(out)


def _list(block: list[str]) -> str:
    items: list[tuple[int, bool, str]] = []
    for ln in block:
        m = re.match(r"(\s*)([-*]|\d+\.) (.*)", ln)
        if m:
            items.append((len(m.group(1)), m.group(2)[0].isdigit(), m.group(3)))
        elif items:
            d, o, t = items[-1]
            items[-1] = (d, o, t + " " + ln.strip())

    def build(k: int, depth: int) -> tuple[str, int]:
        tag = "ol" if items[k][1] else "ul"
        s = f"<{tag}>"
        while k < len(items) and items[k][0] >= depth:
            d, _, text = items[k]
            if d > depth:
                sub, k = build(k, d)
                s = s[:-5] + sub + "</li>"
                continue
            text = re.sub(r"^\[ \] ", "☐ ", text)
            s += f"<li>{_inline(text)}</li>"
            k += 1
        return s + f"</{tag}>", k
    return build(0, items[0][0])[0]


def section_of(path: str, start: str | None = None, stop: str | None = None) -> str:
    s = (ROOT / path).read_text()
    s = re.sub(r"<!-- BEGIN:\w+ -->|<!-- END:\w+ -->", "", s)
    if start:
        s = s[s.index(start):]
    if stop and stop in s:
        s = s[:s.index(stop)]
    return s


def img(name: str, alt: str, width=1100) -> str:
    im = Image.open(ROOT / "cad" / "renders" / name).convert("RGB")
    im.thumbnail((width, width))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'<img src="data:image/jpeg;base64,{b64}" alt="{html.escape(alt)}" loading="lazy">'


# -------------------------------------------------------------------- page --
CSS = """
/* Layout: one reading column, sticky section bar, wide tables scroll in place */
:root{
  --bg:#f3f4f2; --panel:#ffffff; --fg:#1d2321; --muted:#5c6763; --line:#d5dad6;
  --amber:#b8650a; --amber-soft:#fbe9cf; --warn:#a3261b; --warn-soft:#f8e1dd; --ok:#2f6b3d;
  --display:"Saira Condensed","Arial Narrow",sans-serif; --body:"Public Sans",system-ui,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#141917; --panel:#1c2220; --fg:#e7ebe8; --muted:#9aa5a0; --line:#2f3835;
  --amber:#f0a345; --amber-soft:#3a2a14; --warn:#ff8a7a; --warn-soft:#3b1d19; --ok:#7fc58f; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#141917; --panel:#1c2220; --fg:#e7ebe8; --muted:#9aa5a0; --line:#2f3835;
  --amber:#f0a345; --amber-soft:#3a2a14; --warn:#ff8a7a; --warn-soft:#3b1d19; --ok:#7fc58f; color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:16px/1.6 var(--body);
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
main{max-width:46rem;margin:0 auto;padding-block:8px 64px}
header.hero{padding-block:28px 8px}
.eyebrow{font:600 .78rem/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--amber)}
h1{font:700 clamp(2.6rem,9vw,4.2rem)/.95 var(--display);letter-spacing:.01em;margin:.3em 0 .25em;text-wrap:balance}
h2{font:700 2rem/1.05 var(--display);margin:2.2em 0 .5em;text-wrap:balance;scroll-margin-top:64px}
h3{font:700 1.3rem/1.2 var(--display);margin:1.6em 0 .4em;letter-spacing:.01em}
h4{font:600 1rem/1.3 var(--body);margin:1.2em 0 .3em}
p,li{max-width:65ch}
.lede{font-size:1.1rem;color:var(--muted)}
nav.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
  margin-inline:calc(-1*max(16px,env(safe-area-inset-left,0px)));padding:8px max(16px,env(safe-area-inset-left,0px))}
nav.bar ul{display:flex;gap:6px;overflow-x:auto;list-style:none;margin:0;padding:0;scrollbar-width:none}
nav.bar a{display:block;white-space:nowrap;padding:6px 12px;border-radius:999px;border:1px solid var(--line);
  color:var(--fg);text-decoration:none;font:600 .85rem/1 var(--body)}
nav.bar a:hover,nav.bar a:focus-visible{border-color:var(--amber);color:var(--amber);outline:none}
a{color:var(--amber)}
code{font:.88em var(--mono);background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:0 .25em;overflow-wrap:anywhere}
pre{margin:0;padding:12px;background:var(--panel);border:1px solid var(--line);border-radius:6px;font:.82rem/1.5 var(--mono)}
pre code{border:0;padding:0;background:none}
.scroll{overflow-x:auto;margin:1em 0;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;vertical-align:top;padding:7px 10px;border-bottom:1px solid var(--line)}
th{font:600 .74rem/1.2 var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--muted);white-space:nowrap}
figure{margin:1.2em 0}
figure img{display:block;width:100%;height:auto;border-radius:6px;border:1px solid var(--line);background:#fff}
figcaption{font-size:.85rem;color:var(--muted);margin-top:6px}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:12px}
.gallery figure{margin:0}
.callout{border-radius:6px;padding:12px 16px;margin:1.2em 0;background:var(--warn-soft);color:var(--fg);border:1px solid var(--line)}
.callout strong:first-child{color:var(--warn)}
.note{background:var(--amber-soft)}
.note strong:first-child{color:var(--amber)}
ol li,ul li{margin:.25em 0}
footer{margin-top:3em;font-size:.85rem;color:var(--muted)}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
"""


def main():
    gen_docs.main()
    n = gen_docs.numbers()
    with open(ROOT / "BOM.csv", newline="") as f:
        bom = list(csv.DictReader(f))
    bom_rows = ["| item | need | EUR | links |", "|---|---|---|---|"]
    for r in bom:
        if r["group"] == "filament" and float(r["buy_eur"]) == 0:
            continue
        flag = " (est.)" if r["verified"] == "unverified" else ""
        bom_rows.append(f"| **{r['item']}** — {r['spec']} | {r['qty_needed']} | {float(r['buy_eur']):.2f}{flag} | "
                        f"[AliExpress]({r['source_ali']}) · [Amazon.it]({r['source_amazon_it']}) |")
    key = section_of("README.md", "| | value | target |", "\n\n")
    plates = section_of("PRINT_GUIDE.md", "| plate file |", "\n\n")
    sections = [
        ("safety", "Safety first", md(section_of("SAFETY.md", "## Hard rules", "## Pinch points"))),
        ("parts", "Parts", f"<p><strong>Hardware and electronics: EUR {n['bom_hw']:.2f}</strong>, plus EUR {n['bom_fil']:.0f} "
                           "of PETG. That is over the EUR 80 target; see <a href='#limits'>Known limits</a>. Prices are pack "
                           "prices seen in October 2026. Check them in the app before ordering.</p>" + md("\n".join(bom_rows))),
        ("print", "Print", md(section_of("PRINT_GUIDE.md", "## Global settings", "## Orientation rules")) +
         f"<h3>Plates</h3><p>{n['n_parts']} parts, {n['grams']:.0f} g, {n['hours']:.1f} h. Open each <code>plate_*.3mf</code> "
         "in Bambu Studio.</p>" + md(plates)),
        ("build", "Build", md(section_of("ASSEMBLY_GUIDE.md", "## 1. Inserts")).replace("<h3>", "<h3>Step ")),
        ("calibrate", "Calibrate", md(section_of("CALIBRATION.md", "## 1. Measure", "## 7."))),
        ("limits", "Known limits", md(section_of("KNOWN_LIMITATIONS.md", "## Targets that are not met", "## Design compromises"))),
    ]
    gallery = "".join(f"<figure>{img(f, c, 900)}<figcaption>{c}</figcaption></figure>" for f, c in [
        ("launcher_side.png", "Side, at rest"), ("launcher_side_cocked.png", "Side, cocked with a can in the cup"),
        ("launcher_rear_right.png", "Rear: magazine, chute, escapement"), ("launcher_exploded.png", "Exploded view"),
        ("button.png", "The Beer Button"), ("button_exploded.png", "Button, exploded")])
    nav = "".join(f'<li><a href="#{k}">{t}</a></li>' for k, t, _ in sections)
    body = f"""<title>Beer Button Build Guide</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Public+Sans:ital,wght@0,400;0,600;1,400&family=Saira+Condensed:wght@600;700&display=swap">
<style>{CSS}</style>
<main>
<header class="hero">
  <div class="eyebrow">Print-at-home kit · Bambu A1 · ESP32-C3</div>
  <h1>Beer Button</h1>
  <p class="lede">You press a wireless puck on the sofa. A printed catapult beeps for 1.5 s, cocks its arm, drops one can
  from its magazine and lobs it about 4 m into your hands.</p>
  <figure>{img("launcher_front_left.png", "The launcher, front left")}<figcaption>The launcher at rest: magazine at the back, arm and cup in front, cocking ring on the right.</figcaption></figure>
</header>
<nav class="bar" aria-label="Sections"><ul>{nav}<li><a href="#renders">Renders</a></li></ul></nav>
<h2 id="numbers">Key numbers</h2>
{md(key)}
<div class="callout"><strong>Two targets are missed on purpose.</strong> No arc can deliver a can to 4 m at under 4 m/s, because
the minimum is 5.8 m/s. So catch with two hands. The 5 m setting takes 2.8 s from press to launch, against the 2.5 s target.</div>
{"".join(f'<section id="{k}"><h2>{t}</h2>{c}</section>' for k, t, c in sections)}
<section id="renders"><h2>Renders</h2><div class="gallery">{gallery}</div></section>
<footer>Generated from the kit's repo (README, BOM.csv, PRINT_GUIDE, ASSEMBLY_GUIDE, CALIBRATION, KNOWN_LIMITATIONS).
Every number comes from the code's own build, calculation and simulation outputs. Simulation is not reality: calibrate before you trust a throw.</footer>
</main>"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(body)
    print(OUT, round(OUT.stat().st_size / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
