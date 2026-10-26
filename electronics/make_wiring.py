#!/usr/bin/env python3
"""Generate the block-level wiring diagrams for the Beer Launcher and the Beer Button.

    python electronics/make_wiring.py      ->  electronics/wiring_launcher.svg
                                               electronics/wiring_button.svg

Pure standard library, raw SVG, deterministic (same input -> byte-identical output):
no timestamps, no random ids, fixed coordinates. Only generic system font families
are named (no web fonts). Pin numbers come from firmware/launcher/src/hal_esp32.cpp
and firmware/button/src/main.cpp; see electronics/PINMAP.md.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FONT = "DejaVu Sans, Liberation Sans, Arial, Helvetica, sans-serif"

# Wire colours by net class.
C_12V = "#d62728"   # +12 V
C_GND = "#111111"   # ground
C_5V = "#ff7f0e"    # +5 V rails
C_3V3 = "#9467bd"   # +3V3
C_SIG = "#1f5fbf"   # logic signals
C_MOT = "#8c564b"   # motor leads
C_BAT = "#2ca02c"   # battery / LiPo


class Svg:
    """Tiny SVG builder. Every primitive appends one element; output order = call order."""

    def __init__(self, w: int, h: int, title: str) -> None:
        self.w, self.h, self.title = w, h, title
        self.el: list[str] = []

    # ---------------------------------------------------------- primitives --
    def line(self, x1, y1, x2, y2, color=C_SIG, width=2.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round"{d}/>'
        )

    def poly(self, pts, color=C_SIG, width=2.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.el.append(
            f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linejoin="round" stroke-linecap="round"{d}/>'
        )

    def rect(self, x, y, w, h, fill="#ffffff", stroke="#333333", width=2.0, rx=6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>'
        )

    def circle(self, x, y, r, fill="#111111", stroke="none"):
        self.el.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}"/>')

    def text(self, x, y, s, size=14, anchor="start", weight="normal", color="#111111", italic=False):
        st = ' font-style="italic"' if italic else ""
        self.el.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{color}"{st}>{escape(s)}</text>'
        )

    def lines(self, x, y, rows, size=13, anchor="start", weight="normal", color="#111111", gap=None):
        gap = gap or round(size * 1.3)
        for i, r in enumerate(rows):
            self.text(x, y + i * gap, r, size, anchor, weight if i == 0 else "normal", color)

    def label(self, x, y, s, size=12, color="#111111", anchor="start", weight="bold"):
        """Text on a white box so it stays readable over wires (no paint-order: works in every viewer)."""
        if not s:
            return
        w = len(s) * size * (0.62 if weight == "bold" else 0.57) + 4
        x0 = x - 2 if anchor == "start" else (x - w / 2 if anchor == "middle" else x - w + 2)
        self.el.append(
            f'<rect x="{x0:.1f}" y="{y - size + 1:.1f}" width="{w:.1f}" height="{size + 3}" '
            f'fill="#ffffff" fill-opacity="0.88" stroke="none"/>'
        )
        self.text(x, y, s, size, anchor, weight, color)

    # ----------------------------------------------------------- symbols --
    def dot(self, x, y, color=C_GND):
        self.circle(x, y, 4.5, fill=color)

    def gnd(self, x, y):
        """Ground symbol hanging below (x, y)."""
        self.line(x, y, x, y + 10, C_GND, 2)
        self.line(x - 10, y + 10, x + 10, y + 10, C_GND, 2.5)
        self.line(x - 6, y + 15, x + 6, y + 15, C_GND, 2)
        self.line(x - 2, y + 20, x + 2, y + 20, C_GND, 2)

    def flag(self, x, y, name, color, up=True):
        """Power-port flag: a short stem and a bar with the rail name."""
        s = -1 if up else 1
        self.line(x, y, x, y + s * 14, color, 2)
        self.line(x - 9, y + s * 14, x + 9, y + s * 14, color, 3)
        self.label(x, y + s * 14 + (s * 6 if up else 17), name, 11, color, "middle")

    def resistor(self, x1, y1, x2, y2, name, color=C_SIG):
        """IEC resistor (rectangle) centred on a straight horizontal or vertical segment."""
        horiz = y1 == y2
        L = abs(x2 - x1) if horiz else abs(y2 - y1)
        b = 30 if L >= 50 else max(L - 12, 16)
        if horiz:
            xm = (x1 + x2) / 2
            self.line(x1, y1, xm - b / 2, y1, color)
            self.line(xm + b / 2, y1, x2, y1, color)
            self.rect(xm - b / 2, y1 - 7, b, 14, rx=1, width=2, stroke="#222")
            self.label(xm, y1 - 11, name, 11, "#222", "middle", "normal")
        else:
            ym = (y1 + y2) / 2
            self.line(x1, y1, x1, ym - b / 2, color)
            self.line(x1, ym + b / 2, x1, y2, color)
            self.rect(x1 - 7, ym - b / 2, 14, b, rx=1, width=2, stroke="#222")
            self.label(x1 + 11, ym + 4, name, 11, "#222", "start", "normal")

    def cap(self, x, y1, y2, name, color=C_SIG, polar=False, side="right"):
        """Vertical capacitor between y1 (top) and y2 (bottom)."""
        ym = (y1 + y2) / 2
        self.line(x, y1, x, ym - 4, color)
        self.line(x, ym + 4, x, y2, C_GND)
        self.line(x - 11, ym - 4, x + 11, ym - 4, "#222", 3)
        self.line(x - 11, ym + 4, x + 11, ym + 4, "#222", 3)
        if polar:
            self.text(x - 16, ym - 7, "+", 12, "middle", "bold")
        if side == "right":
            self.label(x + 15, ym + 4, name, 11, "#222", "start", "normal")
        else:
            self.label(x - 15, ym + 4, name, 11, "#222", "end", "normal")

    def diode_v(self, x, y1, y2, name, color, kind="D", side="right"):
        """Vertical diode, cathode at the TOP (y1), anode at the bottom (y2): reverse-biased clamp."""
        ym = (y1 + y2) / 2
        self.line(x, y1, x, ym - 8, color)
        self.line(x, ym + 8, x, y2, C_GND if kind != "flyback" else color)
        self.el.append(
            f'<polygon points="{x - 9},{ym + 8} {x + 9},{ym + 8} {x},{ym - 8}" fill="#ffffff" '
            f'stroke="#222" stroke-width="2"/>'
        )
        self.line(x - 9, ym - 8, x + 9, ym - 8, "#222", 2.5)
        if kind == "tvs":
            self.line(x - 9, ym - 8, x - 13, ym - 4, "#222", 2)
            self.line(x + 9, ym - 8, x + 13, ym - 12, "#222", 2)
        if side == "right":
            self.label(x + 16, ym + 4, name, 11, "#222", "start", "normal")
        else:
            self.label(x - 16, ym + 4, name, 11, "#222", "end", "normal")

    def diode_h(self, x1, y, x2, name, color, cathode_right=True):
        xm = (x1 + x2) / 2
        self.line(x1, y, xm - 9, y, color)
        self.line(xm + 9, y, x2, y, color)
        if cathode_right:
            pts = f"{xm - 9},{y - 9} {xm - 9},{y + 9} {xm + 9},{y}"
            bar = xm + 9
        else:
            pts = f"{xm + 9},{y - 9} {xm + 9},{y + 9} {xm - 9},{y}"
            bar = xm - 9
        self.el.append(f'<polygon points="{pts}" fill="#ffffff" stroke="#222" stroke-width="2"/>')
        self.line(bar, y - 9, bar, y + 9, "#222", 2.5)
        self.label(xm, y - 13, name, 11, "#222", "middle", "normal")

    def fuse_h(self, x1, y, x2, name, color=C_12V):
        xm = (x1 + x2) / 2
        self.line(x1, y, xm - 22, y, color, 3)
        self.line(xm + 22, y, x2, y, color, 3)
        self.rect(xm - 22, y - 9, 44, 18, rx=2, width=2, stroke="#222")
        self.line(xm - 22, y, xm + 22, y, "#222", 1.5)
        self.label(xm, y - 14, name, 12, "#222", "middle")

    def switch_h(self, x1, y, x2, name, color=C_SIG, nc=False):
        """Horizontal switch contact. nc=True draws a normally-closed contact."""
        xm = (x1 + x2) / 2
        self.line(x1, y, xm - 15, y, color)
        self.line(xm + 15, y, x2, y, color)
        self.circle(xm - 15, y, 3, "#222")
        self.circle(xm + 15, y, 3, "#222")
        if nc:
            self.line(xm - 15, y, xm + 17, y + 6, "#222", 2.5)
        else:
            self.line(xm - 15, y, xm + 13, y - 12, "#222", 2.5)
        self.label(xm, y - 16, name, 11, "#222", "middle", "normal")

    def switch_v(self, x, y1, y2, name, color=C_SIG, nc=False, side="right"):
        ym = (y1 + y2) / 2
        self.line(x, y1, x, ym - 15, color)
        self.line(x, ym + 15, x, y2, color)
        self.circle(x, ym - 15, 3, "#222")
        self.circle(x, ym + 15, 3, "#222")
        if nc:
            self.line(x, ym - 15, x + 6, ym + 17, "#222", 2.5)
        else:
            self.line(x, ym - 15, x + 13, ym + 12, "#222", 2.5)
        if side == "right":
            self.label(x + 18, ym + 4, name, 11, "#222", "start", "normal")
        else:
            self.label(x - 10, ym + 4, name, 11, "#222", "end", "normal")

    def module(self, x, y, w, h, title, sub=(), fill="#f4f6fa", pins_l=(), pins_r=(), pins_t=(), pins_b=()):
        """A module box. pins_* are (name, coord) where coord is the absolute y (left/right) or x (top/bottom)."""
        self.rect(x, y, w, h, fill=fill, stroke="#333", width=2.2, rx=8)
        self.text(x + w / 2, y + 22, title, 15, "middle", "bold")
        for i, s in enumerate(sub):
            self.text(x + w / 2, y + 40 + i * 16, s, 12, "middle", color="#333")
        for name, py in pins_l:
            self.line(x - 6, py, x, py, "#333", 2)
            self.circle(x, py, 3.5, "#333")
            self.text(x + 8, py + 4, name, 12, "start", "bold", "#222")
        for name, py in pins_r:
            self.circle(x + w, py, 3.5, "#333")
            self.text(x + w - 8, py + 4, name, 12, "end", "bold", "#222")
        for name, px in pins_t:
            self.circle(px, y, 3.5, "#333")
            self.text(px, y + 16, name, 12, "middle", "bold", "#222")
        for name, px in pins_b:
            self.circle(px, y + h, 3.5, "#333")
            self.text(px, y + h - 7, name, 12, "middle", "bold", "#222")

    # ------------------------------------------------------------- output --
    def render(self) -> str:
        head = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">\n'
            f"<title>{escape(self.title)}</title>\n"
            f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="#ffffff"/>\n'
        )
        return head + "\n".join(self.el) + "\n</svg>\n"


def legend(s: Svg, x: int, y: int, items) -> None:
    s.rect(x, y, 300, 24 + 22 * len(items), fill="#ffffff", stroke="#999", width=1.5)
    s.text(x + 12, y + 18, "Wire colours", 13, weight="bold")
    for i, (name, col, w) in enumerate(items):
        yy = y + 40 + i * 22
        s.line(x + 14, yy - 4, x + 64, yy - 4, col, w)
        s.text(x + 74, yy, name, 12)


# ======================================================================= #
#                                LAUNCHER                                 #
# ======================================================================= #

def launcher() -> str:
    s = Svg(2000, 2060, "Beer Launcher wiring (block level)")
    s.text(40, 40, "BEER LAUNCHER — block wiring diagram", 26, weight="bold")
    s.text(40, 66, "ESP32-C3 SuperMini · BTS7960 (IBT-2) · 37GB555 12 V · 2 x MG996R · pins from "
           "firmware/launcher/src/hal_esp32.cpp · see PINMAP.md / WIRING.md", 14, color="#333")

    # ------------------------------------------------ input power chain --
    yP, yN = 150, 250            # + and - conductors of the input chain
    s.module(40, 100, 220, 180, "PSU (mains side)", ("Mean Well GST60A12", "12 V 5 A, CE, desktop", "never open it"),
             fill="#fff3f3", pins_r=(("+12V", yP), ("GND", yN)))
    s.module(400, 100, 150, 180, "J1 DC jack", ("5.5 x 2.1 panel", ">= 5 A rated"),
             pins_l=(("tip", yP), ("sleeve", yN)), pins_r=(("+", yP), ("-", yN)))
    s.line(260, yP, 400, yP, C_12V, 3)
    s.line(260, yN, 400, yN, C_GND, 3)
    s.label(330, yP - 8, "brick plug", 11, "#444", "middle", "normal")
    s.fuse_h(550, yP, 700, "F1 5 A (ATO blade)")
    s.module(700, 100, 200, 110, "Q1 IRF4905", ("P-MOSFET, reverse polarity", "ZD1 15 V G-S (K to S)"),
             fill="#fff8ee", pins_l=(("D", yP),), pins_r=(("S", yP),), pins_b=(("G", 800),))
    s.resistor(800, 210, 800, yN, "R1 10k G→GND", C_GND)
    s.dot(800, yN, C_GND)
    s.line(550, yN, 1000, yN, C_GND, 3)
    s.line(900, yP, 1000, yP, C_12V, 3)
    s.label(620, yN - 8, "GND 1.0 mm²", 11, C_GND, "middle")
    s.label(950, yP - 8, "+12V 1.0 mm²", 11, C_12V, "middle")
    s.module(1000, 100, 180, 180, "TB1 star point", ("screw terminal", "+12V / GND"),
             fill="#fffbe6", pins_l=(("+12V", yP), ("GND", yN)))

    # Rails from TB1
    y12, yG = 330, 390
    s.poly([(1180, yP), (1210, yP), (1210, y12)], C_12V, 3)
    s.poly([(1180, yN), (1240, yN), (1240, yG)], C_GND, 3)
    s.line(60, y12, 1960, y12, C_12V, 4)
    s.line(60, yG, 1960, yG, C_GND, 4)
    s.dot(1210, y12, C_12V)
    s.dot(1240, yG, C_GND)
    s.label(300, y12 - 8, "+12V_PROT rail · 1.0 mm² TB1 → bridge; 0.5 mm² to buck / beacon", 12, C_12V)
    s.label(300, yG + 18, "GND rail · 1.0 mm² (all returns meet at TB1)", 12, C_GND)

    # TVS + bulk cap at the bridge
    s.cap(1330, y12, yG, "C1 1000 µF 25 V", C_12V, polar=True, side="left")
    s.diode_v(1395, y12, yG, "D1 SMBJ15A", C_12V, "tvs", side="right")
    s.dot(1330, y12, C_12V); s.dot(1330, yG, C_GND)
    s.dot(1395, y12, C_12V); s.dot(1395, yG, C_GND)

    # ------------------------------------------------------- ESP32 box --
    ex, ew, ey, eh = 660, 300, 500, 1200
    right_pins = [
        ("GPIO0", 560), ("GPIO1", 650), ("GPIO3", 880), ("GPIO2 (strap)", 980),
        ("GPIO4", 1090), ("GPIO5", 1170), ("GPIO6", 1250), ("GPIO7", 1330),
        ("GPIO9 (strap/BOOT)", 1410), ("GPIO20 (U0RXD)", 1520), ("GPIO21 (U0TXD)", 1640),
    ]
    left_pins = [("5V", 560), ("GND", 660), ("3V3", 740), ("GPIO8 (strap/LED)", 840), ("GPIO10", 1060)]
    s.module(ex, ey, ew, eh, "ESP32-C3 SuperMini", ("launcher MCU", "USB-C for flashing"),
             fill="#eef5ff", pins_l=left_pins, pins_r=right_pins)
    s.lines(ex + 14, 1180, ["all 13 usable", "GPIO in use;", "BOOT button", "= GPIO9;", "on-board LED", "= GPIO8"],
            12, color="#333", gap=16)

    X0 = ex + ew  # right edge of the ESP box

    def sig(y, x2, net, extra="0.14 mm²"):
        s.line(X0, y, x2, y, C_SIG, 2)
        s.label(X0 + 12, y - 7, f"{net} · {extra}", 12, C_SIG)

    # --------------------------------------------------- IBT-2 + motor --
    bx, by, bw, bh = 1420, 470, 260, 380
    s.module(bx, by, bw, bh, "IBT-2 (BTS7960)", ("H-bridge, 43 A", "VCC = 3V3 logic"),
             fill="#fff3f3",
             pins_l=(("RPWM", 560), ("LPWM", 650), ("R_EN", 710), ("L_EN", 740), ("VCC", 770), ("GND", 800)),
             pins_r=(("M+", 560), ("M-", 650), ("R_IS nc", 740), ("L_IS nc", 780)))
    s.circle(1500, by, 4, "#333"); s.circle(1600, by, 4, "#333")
    s.label(1508, by - 6, "B+", 12, "#222", "start")
    s.label(1608, by - 6, "B-", 12, "#222", "start")
    s.line(1500, y12, 1500, by, C_12V, 3)
    s.line(1600, yG, 1600, by, C_GND, 3)
    s.dot(1500, y12, C_12V); s.dot(1600, yG, C_GND)
    s.label(1505, 440, "1.0 mm² screw", 11, C_12V, "start", "normal")

    sig(560, bx, "GPIO0 → MOT_RPWM")
    sig(650, bx, "GPIO1 → MOT_LPWM")
    s.resistor(1300, 560, 1300, 615, "R2 10k", C_SIG); s.gnd(1300, 615); s.dot(1300, 560, C_SIG)
    s.resistor(1360, 650, 1360, 705, "R3 10k", C_SIG); s.gnd(1360, 705); s.dot(1360, 650, C_SIG)
    for yy in (710, 740, 770):
        s.line(1395, yy, bx, yy, C_3V3, 2)
    s.line(1395, 710, 1395, 770, C_3V3, 2)
    s.line(1395, 740, 1260, 740, C_3V3, 2)
    s.flag(1260, 740, "+3V3", C_3V3, up=True)
    s.label(1180, 790, "R_EN, L_EN, VCC → +3V3", 11, C_3V3, "start")
    s.line(1405, 800, bx, 800, C_GND, 2); s.gnd(1405, 800)

    mx, my, mw, mh = 1750, 470, 210, 300
    s.module(mx, my, mw, mh, "M1 37GB555", ("12 V gearmotor", "stall ~5.3 A", "Hall enc. 11/16 PPR"),
             fill="#f7f0ea", pins_l=(("M+", 560), ("M-", 650)),
             pins_b=(("VCC", 1790), ("GND", 1840), ("A", 1890), ("B", 1935)))
    s.line(bx + bw, 560, mx, 560, C_MOT, 3)
    s.line(bx + bw, 650, mx, 650, C_MOT, 3)
    s.label(1688, 550, "1.0 mm²", 11, C_MOT, "start", "normal")
    s.line(1714, 601, 1736, 601, "#222", 3); s.line(1714, 609, 1736, 609, "#222", 3)
    s.line(1725, 560, 1725, 601, C_MOT, 2); s.line(1725, 609, 1725, 650, C_MOT, 2)
    s.dot(1725, 560, C_MOT); s.dot(1725, 650, C_MOT)
    s.label(1715, 690, "C4 100 nF", 11, "#222", "middle", "normal")
    s.label(1715, 705, "on motor tabs", 11, "#222", "middle", "normal")
    s.line(1790, my + mh, 1790, my + mh + 30, C_3V3, 2); s.flag(1790, my + mh + 30, "+3V3", C_3V3, up=False)
    s.line(1840, my + mh, 1840, my + mh + 25, C_GND, 2); s.gnd(1840, my + mh + 25)
    s.label(1935, my + mh + 22, "nc", 11, "#555", "middle", "normal")
    s.poly([(1890, my + mh), (1890, 880), (X0, 880)], C_SIG, 2)
    s.label(X0 + 12, 873, "GPIO3 → ENC_A (interrupt, both edges) · 0.14 mm² · JST-XH 4p, encoder on 3V3", 12, C_SIG)

    # ------------------------------------------------ warning output --
    sig(980, 1420, "GPIO2 → WARN")
    s.line(1200, 980, 1200, 970, C_SIG, 2)
    s.rect(1193, 935, 14, 35, rx=1, width=2, stroke="#222")
    s.line(1200, 935, 1200, 925, C_3V3, 2)
    s.flag(1200, 925, "+3V3", C_3V3, up=True)
    s.label(1186, 958, "R4 10k strap pull-up", 11, "#222", "end", "normal")
    s.dot(1200, 980, C_SIG)
    s.resistor(1330, 980, 1420, 980, "R5 100 Ω")
    s.module(1420, 935, 180, 110, "Q2 AO3400", ("N-MOSFET low side",),
             fill="#fff8ee", pins_l=(("G", 980),), pins_r=(("D", 1000),), pins_b=(("S", 1510),))
    s.gnd(1510, 1045)
    s.module(1700, 925, 260, 120, "LS1 + BEACON", ("12 V buzzer ‖ 12 V beacon", "D2 1N5819 across", "(K to +12V)"),
             fill="#fffbe6", pins_l=(("(+)", 960), ("(-)", 1000)))
    s.line(1600, 1000, 1700, 1000, C_SIG, 2)
    s.label(1610, 1018, "0.25 mm²", 11, "#333", "start", "normal")
    s.poly([(1700, 960), (1660, 960), (1660, 950)], C_12V, 2)
    s.flag(1660, 950, "+12V", C_12V, up=True)

    # ------------------------------------------------ switches (to GND) --
    def sw_row(y, gpio_net, title, sub, cap=True):
        sig(y, 1440, gpio_net, "0.14 mm² · JST-XH 2p")
        if cap:
            s.cap(1340, y, y + 42, "100 nF", C_SIG, side="right")
            s.dot(1340, y, C_SIG)
            s.gnd(1340, y + 42)
        s.switch_h(1440, y, 1560, "", C_SIG)
        s.line(1560, y, 1580, y, C_GND, 2); s.gnd(1580, y)
        s.rect(1610, y - 26, 350, 52, fill="#f6fbf3", stroke="#555", width=1.5)
        s.text(1622, y - 6, title, 13, weight="bold")
        s.text(1622, y + 12, sub, 11, color="#333")

    sw_row(1090, "GPIO4 → SW_ARM_HOME", "SW_ARM_HOME", "microswitch NO, COM→GND · LOW = arm on fwd stop")
    sw_row(1170, "GPIO5 → SW_ARM_COCKED", "SW_ARM_COCKED", "microswitch NO · LOW = at cocked angle")
    sw_row(1250, "GPIO6 → SW_RING_HOME", "SW_RING_HOME", "microswitch NO · LOW = ring parked")
    sw_row(1330, "GPIO7 → SW_SAFETY_PIN", "SW_SAFETY_PIN pole A", "NO: pin INSERTED = closed = LOW = safe")
    sw_row(1410, "GPIO9 → BTN_TEST", "BTN_TEST (panel push button)", "‖ on-board BOOT · NO cap (strap pin!)", cap=False)

    # ------------------------------------------------ TCRT5000 sensors --
    def ir_row(y, net, title, sub, rser):
        s.line(X0, y, 1240, y, C_SIG, 2)
        s.label(X0 + 12, y - 7, f"{net} · 0.14 mm²", 12, C_SIG)
        s.resistor(1240, y, 1290, y, rser)
        s.line(1290, y, 1350, y, C_SIG, 2)
        s.dot(1318, y, C_SIG)
        s.line(1318, y, 1318, y - 10, C_SIG, 2)
        s.rect(1311, y - 42, 14, 32, rx=1, width=2, stroke="#222")
        s.line(1318, y - 42, 1318, y - 50, C_3V3, 2)
        s.flag(1318, y - 50, "+3V3", C_3V3, up=True)
        s.label(1304, y - 22, "10k", 11, "#222", "end", "normal")
        s.diode_h(1350, y, 1415, "BAT54 (K→)", C_SIG, cathode_right=True)
        s.line(1415, y, 1440, y, C_SIG, 2)
        s.module(1440, y - 40, 520, 90, title, sub, fill="#f3f7fb",
                 pins_l=(("DO", y),), pins_b=(("VCC", 1560), ("GND", 1640), ("AO nc", 1720)))
        s.line(1560, y + 50, 1560, y + 62, C_5V, 2)
        s.label(1552, y + 70, "+5V_LOGIC", 11, C_5V, "end")
        s.line(1640, y + 50, 1640, y + 56, C_GND, 2); s.gnd(1640, y + 56)

    ir_row(1520, "GPIO20 → SNS_MAG_EMPTY", "TCRT5000 module — magazine bottom",
           ("LM393 open-collector DO, LOW = can seen", "HIGH = magazine empty"), "R6 1k")
    ir_row(1640, "GPIO21 → SNS_CAN_IN_CUP", "TCRT5000 module — can in cup",
           ("LM393 DO, LOW = can in cup", "1k REQUIRED: GPIO21 is U0TXD at boot"), "R7 1k")
    s.text(980, 1745, "BAT54 blocks the module's 5 V pull-up; 10k to 3V3 gives the HIGH; "
           "LOW ≈ 0.5 V (< 0.8 V VIL).", 12, color="#333")

    # ------------------------------------------------ left: buck + servos --
    s.line(200, y12, 200, 440, C_12V, 2.5); s.dot(200, y12, C_12V)
    s.line(330, yG, 330, 440, C_GND, 2.5); s.dot(330, yG, C_GND)
    s.label(206, 425, "IN+ 0.5 mm²", 11, C_12V, "start", "normal")
    s.label(336, 425, "IN-", 11, C_GND, "start", "normal")
    s.module(140, 440, 260, 80, "U1 MP1584 buck", ("set 5.0 V BEFORE loads",),
             fill="#fff6ea", pins_b=(("OUT+", 200), ("OUT-", 330)))
    s.circle(200, 440, 3.5, "#333"); s.circle(330, 440, 3.5, "#333")
    s.line(330, 520, 330, 532, C_GND, 2.5); s.gnd(330, 532)
    yS = 560
    s.poly([(200, 520), (200, yS)], C_5V, 3); s.dot(200, yS, C_5V)
    s.line(60, yS, 560, yS, C_5V, 3.5)
    s.label(70, yS + 22, "+5V_SERVO · 0.75 mm²", 12, C_5V)
    s.cap(470, yS, 620, "C2 1000 µF 10 V low-ESR", C_5V, polar=True, side="left")
    s.dot(470, yS, C_5V); s.gnd(470, 620)
    s.diode_h(560, yS, 640, "D3 1N5819", C_5V)
    s.line(640, yS, ex, yS, C_5V, 2.5)
    s.label(636, yS - 20, "+5V_LOGIC", 11, C_5V, "start")
    s.line(605, yS, 605, yS + 25, C_5V, 2); s.dot(605, yS, C_5V)
    s.cap(605, yS + 25, yS + 70, "C3 470 µF", C_5V, polar=True, side="left")
    s.gnd(605, yS + 70)
    s.line(ex - 20, 660, ex, 660, C_GND, 2); s.gnd(ex - 20, 660)
    s.line(ex - 30, 740, ex, 740, C_3V3, 2); s.flag(ex - 30, 740, "+3V3 out", C_3V3, up=False)
    # Escapement servo (GPIO8)
    s.module(140, 790, 300, 110, "SERVO_ESC (MG996R)", ("escapement", "brown GND · red V+ · orange SIG"),
             fill="#f6f2fb", pins_t=(), pins_r=(("SIG", 840),), pins_b=(("GND", 290),))
    s.line(290, 900, 290, 915, C_GND, 2); s.gnd(290, 915)
    s.line(250, yS, 250, 790, C_5V, 2.5); s.dot(250, yS, C_5V)
    s.label(256, 776, "V+", 11, "#222", "start")
    s.resistor(440, 840, ex, 840, "R8 330 Ω")
    s.label(480, 870, "GPIO8 → SERVO_ESC · 0.14 mm²", 12, C_SIG)

    # Latch servo (GPIO10) with safety-pin pole B in V+
    s.module(140, 1010, 300, 110, "SERVO_LATCH (MG996R)", ("trips the ring latch", "V+ via safety pin pole B"),
             fill="#f6f2fb", pins_l=(("V+", 1060),), pins_r=(("SIG", 1060),), pins_b=(("GND", 290),))
    s.line(290, 1120, 290, 1135, C_GND, 2); s.gnd(290, 1135)
    s.line(90, yS, 90, 900, C_5V, 2.5); s.dot(90, yS, C_5V)
    s.switch_v(90, 900, 980, "SW_SAFETY_PIN pole B", C_5V, nc=True, side="right")
    s.label(108, 958, "(NC: opens when pin inserted)", 10, "#444", "start", "normal")
    s.poly([(90, 980), (90, 1060), (134, 1060)], C_5V, 2.5)
    s.resistor(440, 1060, ex, 1060, "R9 330 Ω")
    s.label(480, 1090, "GPIO10 → SERVO_LATCH · 0.14 mm²", 12, C_SIG)

    # Notes
    notes = [
        "Notes",
        "• TB1 is the only point where the 12 V return, buck return and logic GND join (star ground).",
        "• R2/R3 10k pull-downs keep the bridge off while the ESP32 is in reset/flashing (EN pins are tied high).",
        "• IBT-2 logic VCC from 3V3 so its input buffer accepts 3.3 V levels; R_IS/L_IS unused.",
        "• D2 1N5819 across a magnetic buzzer (cathode to +12V); not needed for a piezo / LED-only beacon.",
        "• Safety pin = one actuator, two contacts: pole A to GPIO7 (NO), pole B in latch-servo V+ (NC).",
        "• Debounce 100 nF on GPIO4/5/6/7 only. No cap on GPIO9 (strap) or GPIO3 (encoder).",
        "• Flash over USB with the 12 V brick unplugged: GPIO2's pull-up switches the beeper on in download mode.",
    ]
    s.rect(40, 1780, 1240, 30 + 20 * (len(notes) - 1) + 10, fill="#fbfbfb", stroke="#999", width=1.5)
    s.lines(56, 1802, notes, 13, gap=20)
    legend(s, 1320, 1780, [
        ("+12V (1.0 / 0.5 mm²)", C_12V, 4), ("GND", C_GND, 4), ("+5V servo / logic", C_5V, 3.5),
        ("+3V3 (from SuperMini)", C_3V3, 2), ("logic signal 0.14 mm²", C_SIG, 2), ("motor 1.0 mm²", C_MOT, 3),
    ])
    s.text(1960, 2045, "generated by electronics/make_wiring.py", 11, "end", color="#777")
    return s.render()


# ======================================================================= #
#                                 BUTTON                                  #
# ======================================================================= #

def button() -> str:
    s = Svg(1600, 1000, "Beer Button wiring (block level)")
    s.text(40, 40, "BEER BUTTON — block wiring diagram", 26, weight="bold")
    s.text(40, 66, "ESP32-C3 SuperMini · 1S LiPo 500 mAh · TP4056 + DW01A · pins from firmware/button/src/main.cpp",
           14, color="#333")

    # Battery + charger
    s.module(40, 120, 200, 110, "BT1 LiPo 1S", ("500 mAh, 3.0–4.2 V", "with JST-PH lead"), fill="#f0f8ee",
             pins_r=(("+", 160), ("-", 200)))
    s.module(380, 110, 260, 150, "TP4056 + DW01A", ("USB-C = charge input", "protection board"), fill="#f0f8ee",
             pins_l=(("B+", 160), ("B-", 200)), pins_r=(("OUT+", 160), ("OUT-", 200)))
    s.line(240, 160, 380, 160, C_BAT, 3); s.line(240, 200, 380, 200, C_GND, 3)
    s.label(310, 152, "0.25 mm²", 11, C_BAT, "middle", "normal")
    s.label(310, 222, "solder, no plug", 11, "#444", "middle", "normal")
    yB, yG = 160, 200
    s.line(640, yB, 1000, yB, C_BAT, 3)
    s.line(640, yG, 700, yG, C_GND, 3)
    s.label(660, yB - 8, "VBAT (OUT+) · 0.25 mm²", 12, C_BAT)
    s.gnd(700, yG)

    # ESP
    ex, ew, ey, eh = 660, 240, 300, 520
    s.module(ex, ey, ew, eh, "ESP32-C3 SuperMini", ("DESOLDER the red", "power LED"), fill="#eef5ff",
             pins_l=(("5V", 360), ("GND", 430), ("3V3", 500)),
             pins_r=(("GPIO3", 400), ("GPIO1", 520), ("GPIO4", 640), ("GPIO5", 760)))
    s.text(ex + ew / 2, ey + eh - 24, "unused: 0 2 6 7 8 9 10 20 21", 12, "middle", color="#333")
    s.poly([(650, yB), (650, 280), (600, 280), (600, 360), (ex, 360)], C_BAT, 2.5); s.dot(650, yB, C_BAT)
    s.label(540, 352, "VBAT→5V pin", 11, C_BAT, "end")
    s.label(540, 368, "(LDO in, 0.25 mm²)", 11, C_BAT, "end", "normal")
    s.line(ex - 40, 430, ex, 430, C_GND, 2); s.gnd(ex - 40, 430)
    s.line(ex - 40, 500, ex, 500, C_3V3, 2); s.flag(ex - 40, 500, "+3V3", C_3V3, up=False)

    X0 = ex + ew
    # GPIO3 switch: 1M pull-up to 3V3, microswitch to GND
    s.line(X0, 400, 1330, 400, C_SIG, 2)
    s.label(X0 + 12, 393, "GPIO3 → BTN_SWITCH (wake LOW) · 0.14 mm²", 12, C_SIG)
    s.line(1240, 400, 1240, 390, C_SIG, 2); s.dot(1240, 400, C_SIG)
    s.rect(1233, 352, 14, 38, rx=1, width=2, stroke="#222")
    s.line(1240, 352, 1240, 340, C_3V3, 2); s.flag(1240, 340, "+3V3", C_3V3, up=True)
    s.label(1226, 376, "R1 1M", 11, "#222", "end", "normal")
    s.cap(1290, 400, 450, "C1 10 nF (opt.)", C_SIG); s.dot(1290, 400, C_SIG); s.gnd(1290, 450)
    s.switch_h(1330, 400, 1420, "SW1 microswitch (NO)")
    s.line(1420, 400, 1440, 400, C_GND, 2); s.gnd(1440, 400)

    # GPIO1 battery divider from VBAT
    s.poly([(1000, yB), (1500, yB), (1500, 470)], C_BAT, 2)
    s.resistor(1500, 470, 1500, 520, "R2 1M", C_BAT)
    s.line(X0, 520, 1500, 520, C_SIG, 2)
    s.label(X0 + 12, 513, "GPIO1 → BATT_SENSE (ADC, VBAT/2) · 0.14 mm²", 12, C_SIG)
    s.dot(1500, 520, C_SIG)
    s.resistor(1500, 520, 1500, 580, "R3 1M", C_SIG); s.gnd(1500, 580)
    s.cap(1420, 520, 580, "C2 100 nF", C_SIG, side="left"); s.dot(1420, 520, C_SIG); s.gnd(1420, 580)

    # GPIO4 haptic via NPN
    s.line(X0, 640, 1140, 640, C_SIG, 2)
    s.label(X0 + 12, 633, "GPIO4 → HAPTIC · 0.14 mm²", 12, C_SIG)
    s.resistor(1140, 640, 1220, 640, "R4 1k")
    s.dot(1120, 640, C_SIG)
    s.resistor(1120, 640, 1120, 700, "R5 100k", C_SIG); s.gnd(1120, 700)
    s.module(1220, 600, 130, 90, "Q1 NPN", ("S8050 / 2N2222",), fill="#fff8ee",
             pins_l=(("B", 640),), pins_r=(("C", 625),), pins_b=(("E", 1285),))
    s.gnd(1285, 690)
    s.module(1400, 600, 180, 120, "M1 coin motor", ("1027, 3 V", "D1 1N5819 across", "(K to +3V3)"),
             fill="#f7f0ea", pins_l=(("(-)", 625), ("(+)", 680)))
    s.line(1350, 625, 1400, 625, C_SIG, 2)
    s.poly([(1400, 680), (1380, 680), (1380, 740)], C_3V3, 2); s.flag(1380, 740, "+3V3", C_3V3, up=False)

    # GPIO5 LED
    s.line(X0, 760, 1140, 760, C_SIG, 2)
    s.label(X0 + 12, 753, "GPIO5 → STATUS_LED · 0.14 mm²", 12, C_SIG)
    s.resistor(1140, 760, 1220, 760, "R6 330 Ω")
    s.diode_h(1220, 760, 1300, "LED1", C_SIG)
    s.line(1300, 760, 1320, 760, C_GND, 2); s.gnd(1320, 760)
    notes = [
        "Notes",
        "• No power switch: the button lives in deep sleep (~52 µA total, calc/RESULTS.md §6).",
        "• Charge through the TP4056 USB-C only. Do not plug the SuperMini USB while the LiPo is connected",
        "   unless you have checked the board has a diode between VBUS and its 5V pin (flash with LiPo unplugged).",
        "• GPIO3 is an RTC GPIO (0–5), required for deep-sleep GPIO wake.",
        "• C2 100 nF gives the ADC a low-impedance source; 1M/1M divider draws ~2 µA.",
    ]
    s.rect(40, 850, 920, 30 + 20 * (len(notes) - 1) + 10, fill="#fbfbfb", stroke="#999", width=1.5)
    s.lines(56, 872, notes, 13, gap=20)
    legend(s, 40, 260, [("VBAT (LiPo)", C_BAT, 3), ("GND", C_GND, 3), ("+3V3", C_3V3, 2),
                        ("signal 0.14 mm²", C_SIG, 2)])
    s.text(1580, 990, "generated by electronics/make_wiring.py", 11, "end", color="#777")
    return s.render()


def main() -> None:
    for name, fn in (("wiring_launcher.svg", launcher), ("wiring_button.svg", button)):
        out = HERE / name
        out.write_text(fn(), encoding="utf-8")
        print(f"wrote {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
