# Can launcher: Phase-1 physics and materials research

**How this was gathered:** Direct page fetching was blocked in this environment. WebFetch could not resolve DNS, and curl got a proxy 403. Every number below therefore comes from search-engine excerpts of the cited pages, not from reading the full documents. Re-check the critical values against the original PDFs before final design.

**Key to labels:**
- `[n]` is a source number.
- **NOT FOUND** means no citable value turned up. A proxy is given where one exists.
- **[derived]** marks my own arithmetic from cited inputs.

---

## 1. EU beverage cans

### 1.1 Dimensions and mass

| Item | Value | Src |
|---|---|---|
| 330 ml standard: body diameter | 66 mm (imperial "211") | [1] |
| 330 ml standard: height | 115.2 mm | [1] |
| 330 ml standard: lid ("202" end) | ≈52 mm (206 ≈ 57, 204 ≈ 55, 202 ≈ 52, 200 ≈ 50 mm) | [2] |
| 330 ml *sleek* (different can, for contrast) | height 145.4 ±0.3 mm, ends 206.5/202/200, mass 9.6 ±0.6 g | [3] |
| 500 ml standard: body OD | 66.3 mm max | [4] |
| 500 ml standard: height | 168.0 ±0.3 mm empty; 168.0 ±0.4 mm seamed | [4] |
| 500 ml standard: empty mass | 12.4 ±0.8 g | [4] |
| 330 ml empty mass, industry figure | "about 13 g" | [5] |
| 330 ml lightweight (Ball, 2012) | just under 9.5 g | [6] |
| Regular cola density | 1.026 g/ml (measured); about 1.03 g/ml | [25] |
| Sugar solution reference, 20 °C | 10 % sugar → 1.038 g/ml | [26] |
| Diet cola density | 0.911 g/ml as quoted (rough measurement; the source page may describe the whole can rather than the liquid) | [25] |
| Beer density | **NOT FOUND**. Proxy: water ≈ 1.00 g/ml | – |
| Full 330 ml soft drink | ≈ 330 × 1.03 + 13 ≈ **353 g** | [derived from 5, 25] |
| Full 330 ml beer | ≈ 330 × 1.00 + 13 ≈ **343 g**. Headspace and fill tolerance not included. | [derived] |

### 1.2 Wall thickness

| Item | Value | Src |
|---|---|---|
| Ironed side wall | ≈ 0.004 in (0.10 mm) | [7][8] (patent excerpt) |
| Bottom/dome | ≈ 0.012 in (0.30 mm); the end wall keeps the original sheet thickness | [7][8] |
| Wall-thickness sensitivity | 90 → 100 µm wall raises axial collapse force by 116 N; a 5 µm varnish layer adds 21 N | [15] |

### 1.3 Internal pressure

All values are gauge pressure.

| Condition | Value | Src |
|---|---|---|
| Cola, 3.7 vol CO₂, 24 °C (Coca-Cola letter) | ≈ 55 psi ≈ 3.8 bar | [11] |
| Pepsi can at 60 °F (15.6 °C) | ≈ 40 psi ≈ 2.8 bar | [11] |
| 3.0 vol CO₂ can, fridge → about 21 °C | 17 → 36 psig (1.2 → 2.5 bar) | [11] |
| Above about 40 °C | ≈ 0.6 MPa (6 bar) | Patent excerpt; specific patent not pinned. Treat as indicative. |
| Beer, 0.5 % CO₂ (≈ 5 g/L, ≈ 2.5 vol), 20 °C equilibrium | ≈ 2 kg/cm² ≈ 2.0 bar (≈ 28 psi) | [13] |
| Beer 2.5 vol at serving temperature (keg) | 12 psi equilibrium | [14] |

### 1.4 Dome reversal, buckle and axial strength

| Item | Value | Src |
|---|---|---|
| Bottler buckle-strength requirement | **90 psi (6.2 bar)** | [9] |
| Cans for beer or carbonated drinks must withstand | ≈ 95 psi | [10] |
| Dome may face, hot and agitated | > 100 psi | [7] |
| Axial (top-load) strength, reference | 900 N (200 lbf), quoted in a patent as the benchmark to beat | [16] |
| Absolute axial collapse load of a standard empty can | **NOT FOUND** in the excerpts. [15] has the full force–displacement data; its FE model agreed with tests to within 8.9 %. | [15] |
| Pressurised versus empty, axial | Liquid-filled cans resist axial compression better than empty ones (tin-plate steel study). No beverage-can figure found. | [18] |
| Proxy: steel food can, 10 cm diameter, beaded | Peak buckling load ≈ 10 kN | [17] |
| Side-wall denting force | **NOT FOUND**. Sidewall indentation, buckling and piercing have been modelled with FE using sphere impactors [19]. The industry drop test is a water-filled can dropped 24 in through a tube onto an inclined wedge, bottom down, with a dent at the chime; it measures coating cracking, not force [20]. | [19][20] |

### 1.5 Friction

| Pair | μ | Src |
|---|---|---|
| Aluminium can on Rexnord LF/WLF low-friction acetal conveyor chain | 0.20 dry; 0.15 water; 0.12 soap-water | [21] |
| Aluminium on Rexnord FRPLUS | 0.14 dry; 0.13 wet; 0.12 soap-water | [22] |
| Aluminium on plastic chain (Misumi) | 0.2 dry; 0.12 soap-water | [23] |
| Aluminium on aluminium, clean | 1.05–1.35 static; 0.4 kinetic | [24] |
| Aluminium on PETG specifically | **NOT FOUND**. Proxy: acetal-type chain values above. PET on PET is 0.5–1.2 [24 context]. | – |
| Can on can (coated or printed) | **NOT FOUND** | – |

**Wet and condensation effect:** water lowers μ only modestly on low-friction plastics, for example 0.20 → 0.15 [21]. Expect a cold, sweating can to slide slightly more easily on PETG, not dramatically more.

---

## 2. Aerodynamics

Can geometry: D = 66 mm, L = 115 mm, L/D ≈ 1.74. At 5–8 m/s in air, Re ≈ 2–4×10⁴, which is subcritical.

| Item | Value | Src |
|---|---|---|
| Axial flow, blunt flat end leading | Cd ≈ 0.81 for L/D > 2; 1.17 at L/D = 0 (disk). Hoerner, via aerospaceweb. **At L/D ≈ 1.7, interpolate roughly 0.85–0.9; this is my interpolation and not sourced.** | [27] |
| Axial flow, White's correlation | Cd = 0.91 at L/D = 5 (one point) | [32] |
| Cross flow, finite cylinder with two free ends | Cd *falls* as L/D falls (Zdravkovich 1989, L/D 1–10, Re 6×10⁴–2.6×10⁵). Very short cylinders (L/D < 3) have an asymmetric wake; periodic shedding appears for 2 < L/D < 8. | [29][28] |
| Cross flow, coin-like cylinder fit (0 < AR ≤ 1, Re 2–6×10⁵) | Cd = 0.024/AR + 0.633. At AR ≈ 1 this gives ≈ 0.66. | [28] |
| Cross flow, Hoerner values at L/D 1 and 2 (often quoted as ≈ 0.63 / 0.68; infinite ≈ 1.2) | **NOT VERIFIED.** The 0.63 to 0.68 range agrees with [28]. The infinite-cylinder value of 1.16–1.21 is confirmed by Wieselsberger data reproduced in arXiv 2308.05272. | [28] |
| AR 2–15 free-ended cylinders, Re 9.3×10³–1.05×10⁵ | Tip vortices reduce Cd; Reynolds-number effects are minor. Numbers are in the paper. | [30] |
| Tumbling, time-averaged | **NOT FOUND** as a number. Free-fall experiments (Re 200–6000) show that secondary motion lowers the time-averaged projected area and the apparent Cd. | [31] |
| **Suggested modelling band** | Use Cd·A between a broadside value (≈ 0.65 × 66 × 115 mm² ≈ 0.0049 m²) and an end-on value (≈ 0.87 × π/4 × 66² ≈ 0.0030 m²). At 4 m range and about 7 m/s, drag changes range by only a few %. | [derived] |

### Magnus lift on a spinning cylinder

| Item | Value | Src |
|---|---|---|
| Lift coefficient C_L at spin ratio S = ωr/V of 0.05–0.3, Re ≈ 3×10⁴ | **NOT FOUND** as a primary number | – |
| Measured lift on smooth sphere and cylinder | Positive Magnus lift appeared at S ≈ 0.3–0.4. Cylinders and cubes follow similar trends above S ≈ 0.3. | [34] |
| Inverse (negative) Magnus | Region 0.4 < S < 0.7 at Re ≈ 9.4×10⁴ (CFD and experiment) | [33] |
| 2-D cylinder CFD | Force stays positive at all spin ratios at Re = 1×10⁵; the sign flips only at higher subcritical and critical Re | [35] |
| Finite length, free ends | End effects reduce lift and grow with rotation | [36] |
| Classic summaries | Swanson 1961, *J. Basic Eng.* 83: 461–470 (not accessed) | [33] |
| **Practical reading** | At S ≤ 0.3 and short L/D, expect C_L of order 0.1–0.5 with large scatter. This is an **unsourced estimate**; test it. | – |

### Stability and liquid fill

**Gyroscopic stability factor:** Sg ∝ (I_x²·p²)/(I_y·ρ·V²·d³·C_Mα), and Sg > 1 is required for stability [40].

**Inertia of a full can** (treated as a uniform solid cylinder, r = 33 mm, L = 115 mm) [derived]:
- I_x = mr²/2 = 5.4×10⁻⁴·m
- I_y = m(3r² + L²)/12 = 1.37×10⁻³·m
- I_x/I_y ≈ **0.40**

So the long axis is the **minor** axis.

**Energy dissipation:** with energy dissipation, spin about the minor axis is unstable (the major-axis rule). Explorer 1 is the classic example: designed to spin about its long axis, it went into flat spin [37][38].

**Liquid fill:** the liquid does not spin up during a ≈ 1 s flight. Spin-up takes about E^(-1/2)·Ω⁻¹ (Greenspan & Howard 1963), where E = ν/(ΩL²) [39].

Worked example [derived]:
- ν = 1e-6 m²/s, L = 0.03 m, Ω = 30 rad/s
- E ≈ 3.7×10⁻⁵
- t_spinup ≈ 165/30 ≈ 5.5 s, which is much longer than the flight time.

**Consequence:** only the shell (≈ 13 g) spins, and a spin about the long axis gives little gyroscopic stiffness. Viscous coupling with the liquid dissipates energy and drives the can toward a flat (end-over-end) tumble. **Design for a tumbling can rather than relying on spin stabilisation.**

---

## 3. 3D-printing materials

### 3.1 Bambu Lab datasheet and retailer values

All values are printed on an X1C, 0.4 mm nozzle, 0.2 mm layers.

| Property | PETG HF | PETG Basic | PLA Basic | TPU 95A HF |
|---|---|---|---|---|
| Tensile strength X-Y | 34 ±4 MPa [41][42] | **NOT FOUND** in excerpts | NOT FOUND | 27.3 ±0.8 MPa [60] |
| Elongation at break | 8.6 ±1.2 % [41] | – | – | > 650 % [60] |
| Tensile strength Z | **NOT FOUND** | NOT FOUND | NOT FOUND | – |
| Bending strength X-Y | 64 MPa [41] | 75 MPa [43] (one listing gives 65 MPa [44]) | 76 MPa [41] | – |
| Bending strength Z ("layer strength") | 48 MPa [41] | 56 MPa [43] (one listing gives 48 [44]) | 59 MPa [41] | – |
| Bending modulus X-Y | 2050 ±120 MPa [41][42] | 1670 MPa [44] | – | – |
| Impact | ≈ 31.5 kJ/m² [42] | XY 52.7 / Z 13.6 kJ/m² [44]; another listing gives XY 34.2 / Z 10.5 [45] | – | – |
| HDT at 0.45 MPa | 69 °C [42] | 69 °C [44] | – | – |
| Density | 1.28 g/cm³ [42] | – | – | 1.22 g/cm³ [60] |
| Hardness | – | – | – | 95A [61] |

**Z/XY ratio from bending:** PETG HF 48/64 = 0.75; PETG Basic 56/75 = 0.75 [derived from 41, 43].

### 3.2 PETG anisotropy, creep and fatigue

| Item | Value | Src |
|---|---|---|
| Z versus XY tensile, PETG on a Bambu P1S (thesis) | The X build was 127.9 % stronger than the Z build, so Z ≈ 0.44 × X | [47] |
| General FDM rule of thumb | XY up to 4–5× Z in tension; vendor page, not specific to PETG | [48] |
| Peer-reviewed anisotropy study | Tensile response is the most orientation-sensitive; compression is almost insensitive. The ratio is in the full text. | [49] |
| **PETG creep: quantitative strain versus stress over 1000 h** | **NOT FOUND.** Studies exist: anisotropic viscoelastic creep [50]; time–temperature superposition predictions out to 3.88 years at 23 °C, which break down above 60 °C [51]; compression creep and relaxation that depend strongly on load level [52]; a stepped iso-stress method within 5 % of 24 h tests [53]. | [50]–[53] |
| Sustained-stress guidance, PETG | "Creeps at room temperature above about 30 % of yield"; manufacturer blog, unverified | [54] |
| PETG fatigue: S-N data | **NOT FOUND** as numbers. S-N curves for PETG exist: Kim & Huang 2021, R = 0.4 [55]; Martins et al. 2024, PLA and PETG printed at 45°, R = 0.2 [56]. | [55][56] |
| PLA creep, for contrast | Tensile creep tested at 25–50 % of yield at 30 °C. Rupture time depends on infill pattern, and creep rate on layer height, infill % and pattern (ASTM D2990). PLA HDT is near Tg (55–65 °C), so it is poor under sustained load. | [57][58] |

**Design implication [derived, not sourced]:** for printed PETG parts loaded continuously (for example a cocked spring held in a printed latch), keep sustained stress at no more than 20–30 % of XY strength. That is about 7–10 MPa against 34 MPa. Hold the Z direction to roughly half of that again, and put metal pins and steel latch faces at the contact points.

---

## 4. Throwing mechanisms

### 4.1 Ball launchers and traps

| Device | Mechanism | Consistency notes | Src |
|---|---|---|---|
| iFetch Original | Dual wheels (flywheel pair); 3 range settings: 3, 6 and 9 m. A later model offers 10/25/40 ft. | Miniature balls only; needs two drive motors | [62][63][64] |
| GoDogGo-type launchers | Rotary "hammer" striking arm. The patent family also covers linear strikers. | A gravity switch detects that a ball is present | [64][65] |
| BU capstone dog launcher (2025) | Spring platform cocked by linear actuators. Flywheels were rejected for noise. | – | [66] |
| Clay pigeon trap | Spring-tensioned throwing arm held cocked by a latch (rockable levers on a stop boss) and released by a trigger. Motor traps use one motor to re-tension the arm and index the magazine. A solenoid shutter or photocell drops one clay at a time. | Mature, repeatable design | [67][68][69] |
| Tennis ball machine | Pneumatic machines claim better consistency than wheel machines (patent claim). One measured launcher gave 18.9 ±0.89 m/s (CV ≈ 4.7 %), with landing CV of 8.3 % lateral and 18.4 % vertical. Literature CV for projection speed is 2–10 %. | Wheel grip on the ball adds spin scatter | [70][71] |

**Takeaway:** a spring arm with a hard latch, cocked by a motor through a one-way cam, is the established design for repeatable energy (the clay-trap approach). Flywheels pinch the payload, which suits compressible balls but not a rigid, pressurised can.

### 4.2 Single-feed escapements for cans

| Type | Notes | Src |
|---|---|---|
| Two-finger (pin) escapement | Two fingers alternate; a cam interlock stops both from opening at once. | [72] |
| Rotary pocket roller (star wheel) | The roller pockets receive and release one can or bottle per indexed rotation, "in a controlled and positive manner". | [75] |
| Helical carriers (vending) | Phased helices lower the bottom can and drop one per cycle. | [74] |
| Staggered stacks | One actuation releases a can from each stack and holds the second until the next cycle. | [76] |
| Failure modes | Bridging and jamming in gravity columns, which serpentine guides prevent. Clamping or skewing against the neighbouring part. Shingling or overlap at the release point, which a plunger escapement can cause. Any jam stops the cycle. | [73][74][76] |
| Typical feed rate (industrial) | 5–50 parts/min | [77] |

**Design note [derived]:** stand the cans upright in a vertical column (60–70 mm channel; the can is 66 mm diameter [1]) so that the 52 mm neck cannot lock against the next can. A star wheel indexed by the cocking cam gives a positive one-per-cycle feed. Clearance should be about 2–4 mm so a sweating can cannot bridge.

---

## 5. Springs and line

### 5.1 Steel extension springs

| Item | Value | Src |
|---|---|---|
| Shear modulus G, patented-drawn carbon steel (EN 10270-1 type) | 80,500 MPa | [82] |
| G, music wire (QQ-W-470) | 11.2 Mpsi ≈ 77.2 GPa. Calculator example uses 79 GPa. | [82][84] |
| EN 10270-1 SH/DH tensile range across all diameters | 1300–2940 N/mm² | [78] |
| SH at 3.6 mm | 1700–1970 MPa | [79] |
| **EN 10270-1 Rm at 1.5 / 2.0 / 2.5 mm** | **NOT FOUND** in accessible sources (the standard is paywalled). Interpolate from [78][79] or ask the wire supplier for a certificate. | – |
| Grade meaning | SH = high tensile, static loads; DH = high tensile, dynamic loads | [79][80] |
| Allowable body torsion (extension spring) | 30–45 % of minimum tensile strength (MTS) | [81] |
| Hook allowable, torsion | 30–45 % MTS | [81] |
| Hook allowable, bending | 75 % MTS. The hook usually fails first. | [81] |
| Wahl factor | K_w = (4C−1)/(4C−4) + 0.615/C, with τ = K_w·8FD/(πd³) and C = D/d. Example: K_w = 1.2525 at C = 6. | [83][84] |
| Recommended spring index | 4 ≤ C ≤ 12 | [84] |
| Initial tension | Gives the body a constant stress that varies with C (Century Spring chart). **The typical numeric range was NOT FOUND in the excerpts.** | [81][85] |

### 5.2 Dyneema / UHMWPE line

| Item | Value | Src |
|---|---|---|
| Creep at 20 % of rated break strength | SK75 ≈ 0.1 %/month; SK78 ≈ 0.033 %/month | [86] |
| Creep at 30 °C and 300 MPa | SK75 0.02 %/day; SK78 0.006 %/day. Creep rupture at about 30 % elongation (secondary source). | [88] |
| Creep drivers | Creep rises with load, temperature and time | [87] |
| Long-term tests | Tested at 15 % and 30 % of break load; creep "cannot be despised" at ambient temperature | [89] |
| Strength, SK99 vs SK78 | SK99 is 20 % stronger with the same creep | [87] |

**Implication:** a Dyneema cord holding a cocked spring for days will lengthen measurably. Keep the line well under 20 % of its break load, or hold the spring by a steel latch rather than by the cord.

---

## 6. ESP32-C3 power

| Item | Value | Src |
|---|---|---|
| ESP32-C3 chip deep sleep (RTC memory on) | 5 µA | [90] |
| Light sleep (datasheet, as quoted on forum) | 130 µA | [91] |
| DevKit-M1 measured | ≈ 750 µA deep sleep; ≈ 1.1 mA light sleep. USB-UART and board parts dominate. | [91] |
| Custom boards, forum reports | 300–430 µA | [91] |
| SuperMini (standard) deep sleep | ≈ 43 µA with the LED removed; blog figure | [92] |
| SuperMini Plus (WS2812 LED on 3.3 V) | ≈ 0.6–1.5 mA | [93] |
| Plus Mini V1 | Theory < 5 µA; real boards 100–500 µA (LDO quiescent current and LED); ≈ 20 µA after removing the LED or setting GPIO8 high-Z | [94] |
| Espressif staff on the RGB LED | SK68XXMINI standby current ≈ 1 mA | [91] |
| ME6211 LDO quiescent current | 30–40 µA [101a]; 55–60 µA [101b]. Sources conflict; check the Microne datasheet. | [101] |
| ESP-NOW mesh nodes (C3), measured deep sleep | 34 µA | [100] |
| ESP32-C3 TX current (all rates, up to 21 dBm) | 276–335 mA; RX 84–87 mA (distributor summary of the datasheet) | [95] |
| ESP-NOW TX, measured (ESP32-WROOM, not C3) | ≈ 200 mA average during the send | [99] |
| ESP-NOW PHY default | 1 Mbps | [96] |
| Wake from deep sleep | Much slower than light sleep because of the full SPI boot. A wake stub runs before the bootloader. | [97] |
| Wake time, measured (classic ESP32) | ≈ 160 ms | [98] |
| C3 boot-to-send time and energy per ESP-NOW packet | **NOT FOUND**. Measure with a power profiler. | – |
| TP4056 battery drain with input removed | < 2 µA (one clone gives < 1 µA) | [103] |
| TP4056 shutdown supply current (input present) | 35–60 µA, depending on the clone | [103] |
| DW01 protection IC quiescent current | ≈ 3 µA at 3.9 V; 0.1 µA power-down at 2.0 V | [102] |
| TP4056 + DW01 board, anecdote | 1.6 mA continuous drain on one board; cause unclear | [104] |
| LiPo self-discharge | < 10 %/month [105]; < 8 %/month [106]; ≈ 3 %/month [107]. Budget about 5 %/month. | [105]–[107] |

**Budget example [derived]:** SuperMini with the LED removed (≈ 43 µA) plus TP4056/DW01 (≈ 5 µA) ≈ 48 µA ≈ 35 mAh/month, plus 5 %/month self-discharge. A 500 mAh cell would last about 8–9 months idle.

---

## Sources

1. Crown, 11.3 oz / 330 ml standard can. https://www.crowncork.com/beverage-packaging/products/beverage-cans/113oz-330ml-standard. Supports: 66 mm diameter, 115.2 mm height, "211".
2. US10246218B2, necked beverage can. https://patents.google.com/patent/US10246218. Supports: lid code to diameter (202 ≈ 52 mm).
3. Ardagh/nomoQ spec, 330 ml sleek. https://help.nomoq.com/hubfs/Product%20Specifications/04_5_1_58_330_1_02_en.pdf. Supports: sleek height and mass.
4. Ardagh/nomoQ spec, 500 ml. https://help.nomoq.com/hubfs/Product%20Specifications/04_5_1_66_500_1_06_en.pdf. Supports: 66.3 mm, 168 mm, 12.4 g.
5. International Aluminium Institute, Alustory "lightweight". https://alustory.international-aluminium.org/packaging/lightweight/. Supports: 330 ml can ≈ 13 g.
6. Cantech, "Ball reduces weight of beverage cans". https://www.cantechonline.com/news/3522/ball-reduces-weight-of-beverage-cans/. Supports: < 9.5 g.
7. US4953738A, one-piece can body with domed bottom. https://patents.google.com/patent/US4953738. Supports: pressure > 100 psi; wall and bottom thickness (excerpt).
8. US6132155A, can bottom manufacture. https://patents.google.com/patent/US6132155. Supports: dome reversal pressure definition and plug-diameter effect; thickness (excerpt).
9. US6220073, can bottom with improved strength. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6220073. Supports: 90 psi buckle requirement.
10. US4294373, lightweight metal container. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/4294373. Supports: ≈ 95 psi; axial-load test method.
11. Physics Factbook, "Pressure in a can of soda". https://hypertextbook.com/facts/2000/SeemaMeraj.shtml. Supports: soda pressures versus temperature.
13. US5115841, draught beer dispensing. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5115841. Supports: beer ≈ 2 kg/cm² at 20 °C.
14. Chart Industries, "CO₂ in draught beer". https://files.chartindustries.com/Article_Co2_in_Draught_Beer_article_R.3.pdf. Supports: 2.5 vol = 12 psi in a keg.
15. Wędrychowicz, Kustra, Milenin 2023, *Materials* 16:6603. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10574569/. Supports: axial collapse sensitivity to wall and varnish.
16. US12384590B2, lightweight aluminium can. https://patents.google.com/patent/US12384590. Supports: 900 N axial benchmark.
17. NAFEMS NWC01, steel food can buckling. https://www.nafems.org/publications/resource_center/nwc01_2/. Supports: ≈ 10 kN (proxy).
18. *J. Eng. Sci. Tech.* 2011, filled versus empty cans. https://doaj.org/article/a0af868aba8b4c0cb3cc32a9c705f9d5. Supports: filled cans are stronger axially.
19. LS-DYNA 2000, "Piercing of aluminum beverage cans". https://www.dynalook.com/conferences/international-conf-2000/session10-4.pdf. Supports: sidewall indentation modelling.
20. US10113027, drop/dent test of coatings. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10113027. Supports: 24 in wedge drop test.
21. Rexnord LF/WLF material page. https://documents.mrosupply.com/product_documents/11/114-2142-1/Material%2520page%2520LF%2520WLF.pdf. Supports: aluminium on plastic μ, dry and wet.
22. Rexnord FRPLUS product sheet. https://www.rexnord.com/contentitems/techlibrary/documents/ft5-033_ltr_productsheet. Supports: aluminium μ, dry and wet.
23. Misumi chain friction table. https://uk.misumi-ec.com/pdf/fa/2014/P1_2251-2252_F80_EN.pdf. Supports: aluminium μ 0.2 dry / 0.12 soap.
24. Misumi, coefficient of friction blog. https://us.misumi-ec.com/blog/coefficient-of-friction/. Supports: aluminium on aluminium μ.
25. Harvard Science Demonstrations, Coke can buoyancy. https://sciencedemonstrations.fas.harvard.edu/presentations/coke-can-buoyancy. Supports: cola density.
26. Flinn Scientific, sugar solution densities. https://www.flinnsci.com/api/library/Download/d92476f95aff4ffca467e2dccadc7825. Supports: density versus sugar %.
27. Aerospaceweb Q0231 (citing Hoerner). https://aerospaceweb.org/question/aerodynamics/q0231.shtml. Supports: axial Cd 0.81 (L/D > 2) and 1.17 (disk).
28. Yang et al., "Onset of vortex shedding around a short cylinder", arXiv 2111.07356. https://arxiv.org/pdf/2111.07356. Supports: Zdravkovich trends; Cd = 0.024/AR + 0.633.
29. Zdravkovich et al. 1989, JFM, "Flow past short circular cylinders with two free ends". https://resolve.cambridge.org/core/journals/journal-of-fluid-mechanics/article/flow-past-short-circular-cylinders-with-two-free-ends/09813C6A9D9ACE925C5399FB8AD97B9C. Supports: L/D 1–10 regimes.
30. Univ. St. Thomas, "Impact of aspect ratio on drag". https://researchonline.stthomas.edu/esploro/outputs/conferenceProceeding/Impact-of-Aspect-Ratio-on-Drag/991015164046303691. Supports: AR 2–15 at Re ≈ 10⁴.
31. USGS PP 562-C, free-falling cylinders (excerpt). https://pubs.usgs.gov/pp/0562c/report.pdf. Supports: secondary motion lowers average Cd.
32. EES drag library (White). https://fchartsoftware.com/ees/drag_coefficients/hs1050.htm. Supports: axial Cd 0.91 at L/D = 5.
33. ICAS 2012 paper 245, rotating-cylinder CFD. https://icas.org/ICAS_ARCHIVE/ICAS2012/PAPERS/245.PDF. Supports: inverse Magnus at 0.4–0.7; Swanson citation.
34. *Aeronautical Journal*, spinning bodies coefficients. https://resolve.cambridge.org/core/journals/aeronautical-journal/article/experimental-determination-of-the-aerodynamic-coefficients-of-spinning-bodies/05D0BA440425FCE21EDBC2A3212EDA6C. Supports: positive lift at S 0.3–0.4.
35. Zheng et al., negative Magnus of a 2-D cylinder. https://pure.bit.edu.cn/en/publications/numerical-simulation-of-the-negative-magnus-effect-of-a-two-dimen/. Supports: sign versus Re.
36. JAFM, Magnus on a cylinder with two free ends. https://www.jafmonline.net/article_2850.html. Supports: end effects grow with spin.
37. Efroimsky, arXiv astro-ph/0112054. https://arxiv.org/pdf/astro-ph/0112054. Supports: Explorer 1; major-axis rule.
38. ASU MAE462 Lecture 17. https://control.asu.edu/Classes/MAE462/462Lecture17.pdf. Supports: spin stability with dissipation.
39. Greenspan & Howard 1963, JFM 17:385. https://empslocal.ex.ac.uk/people/staff/gv219/classics.d/Greenspan_Howard63.pdf. Supports: spin-up time ~ E^(-1/2)/Ω.
40. US 2002/0190156, controlled spin projectile. https://patents.justia.com/patent/20020190156. Supports: Sg definition; Sg > 1.
41. Bambu Lab store, PETG HF. https://eu.store.bambulab.com/en-ro/products/petg-hf. Supports: PETG HF and PLA Basic values.
42. Filament2Print, PETG HF Bambu. https://filament2print.com/en/pet-petg-cpe/3678-petg-hf-bambulab.html. Supports: 34 MPa, 2050 MPa, 31.5 kJ/m², 69 °C, 1.28 g/cm³.
43. Ultimate 3D Printing Store, PETG Basic. https://ultimate3dprintingstore.com/collections/bambu-lab-filaments/products/bambu-lab-petg-basic-filament-1-75mm-1kg-black. Supports: bending 75 / 56 MPa.
44. MatterHackers, PETG Basic. https://matterhackers.com/store/l/bambu-lab-petg-basic-filament-175mm-1kg/sk/MEQ3G60P. Supports: 65 / 48 MPa, 1670 MPa, impact, HDT.
45. Memory Express, PETG Basic. https://www.memoryexpress.com/Products/MX00137780. Supports: impact XY 34.2 / Z 10.5.
46. Bambu PETG Basic TDS v2.0 (mirror). https://www.additive-x.com/shop/mpattachments/file/viewonline/id/580/product_id/2330. Supports: print settings (mechanical table not seen).
47. Sacramento State MS thesis, FDM comparison. https://scholars.csus.edu/esploro/outputs/graduate/Mechanical-and-FEA-comparison-of-FDM/99258311232901671. Supports: PETG X 127.9 % stronger than Z.
48. Shapeways, part orientation. https://support.shapeways.com/hc/en-us/articles/17839359742876-How-does-part-orientation-affect-the-strength-of-3D-printed-parts. Supports: XY up to 4–5× Z.
49. Azcaray et al. 2026, *Appl. Sci.* 16:9401. https://www.citedrive.com/en/discovery/anisotropy-and-defect-tolerance-of-fff-manufactured-petg-a-combined-tensile-compressive-and-mode-i-fracture-study/. Supports: PETG anisotropy.
50. Stankevics et al. 2025, *Polymers* 17:2075. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12349189/. Supports: creep of printed PETG.
51. UTS, creep of printed PETG. https://opus.cloud1.lib.uts.edu.au/handle/10453/166023. Supports: TTS out to 3.88 years; breakdown above 60 °C.
52. Valvez et al. 2022, *Aerospace* 9:124. https://api.crossref.org/works/10.3390/aerospace9030124. Supports: PETG compression creep and relaxation.
53. FSU, stepped iso-stress creep of PETG. https://materials.fsu.edu/sites/default/files/2025-10/Abstract%20%2828%29.pdf. Supports: accelerated creep method.
54. QIDI blog, PETG brackets. https://eu.qidi3d.com/pt/blogs/print-lab/petg-strength-wall-mounted-brackets. Supports: creep above about 30 % of yield (unverified).
55. Kim & Huang 2021, *J. Compos. Sci.* 5:76. https://www.mdpi.com/2504-477X/5/3/76. Supports: PETG S-N characterisation.
56. Martins et al. 2024, *Polymers* 16:1868. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11243948/. Supports: PLA and PETG S-N at R = 0.2.
57. Waseem et al. 2020, *Polymers* 12:2962. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7764475/. Supports: PLA tensile creep and rupture.
58. "Creep behaviour of a polymer used for 3D printing". https://redi.cedia.edu.ec/document/102172 (and https://www.scielo.br/j/rmat/a/k7YbRX5pcCNTvLYVJyPnMFt/abstract/?lang=en). Supports: PLA creep at 25–50 % of yield, 303 K.
60. Stemfinity, TPU 95A HF. https://stemfinity.com/products/bambu-lab-tpu-95a-hf-1. Supports: 27.3 MPa, > 650 %, 1.22 g/cm³.
61. Bambu TPU 95A TDS. https://polyalkemi.no/wp-content/uploads/2023/06/Bambu_TPU_95A_Technical_Data_Sheet.pdf. Supports: Shore 95A.
62. Petbarn, iFetch Original. https://www.petbarn.com.au/p/ifetch-original-ball-launcher-dog-toy. Supports: 3/6/9 m settings.
63. iFetch. https://goifetch.com/products/ifetch-ball-launcher. Supports: 10/20/30 ft; 1.5 in ball.
64. US9339716B1, automatic ball launcher. https://patents.google.com/patent/US9339716. Supports: rotary striker; iFetch dual wheels.
65. US10625135B2, automatic ball launcher. https://patents.google.com/patent/US10625135. Supports: launcher variants.
66. Boston University capstone, dog ball thrower. https://www.bu.edu/eng/files/2025/06/Automatic-Dog-Ball-Thrower-Capstone-Page.pdf. Supports: spring and actuator design; flywheel rejected for noise.
67. US3937203, spring-type clay pigeon device. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/3937203. Supports: spring arm with trigger latch.
68. US11441879B1, trap spring manipulation. https://patents.google.com/patent/US11441879. Supports: motor-driven tensioning.
69. US3621828A, magazine indexing trap. https://patents.google.com/patent/US3621828A/en. Supports: magazine feed.
70. Norris et al. 2012, tennis launcher reliability. https://ojs.ub.uni-konstanz.de/cpa/article/view/5397. Supports: 18.9 ±0.89 m/s; CVs.
71. US6085735, tennis ball projector. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6085735. Supports: pneumatic consistency claim.
72. SMC MIW/MIS escapements. https://smcpneumatics.com/pdfs/miw_and_miw_series_escapements.pdf. Supports: interlocked two-finger escapement.
73. US4149641A, component feed mechanism. https://patents.google.com/patent/US4149641. Supports: jam, skew and shingling modes.
74. US5547105A, can vending mechanism. https://patents.google.com/patent/US5547105. Supports: helical one-at-a-time feed; anti-bridging.
75. US6540102B2, article dispensing. https://patents.google.com/patent/US6540102. Supports: rotary pocket roller.
76. US4335832, staggered stack vending. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/4335832. Supports: staggered release; serpentine anti-jam (excerpt).
77. US6298977, parts escapement. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6298977. Supports: 5–50 parts/min.
78. Stahl-Becker / RS data sheet, SH/DH wire. https://static.rapidonline.com/pdf/521667_v1.pdf. Supports: Rm 1300–2940 N/mm².
79. Scribd, spring materials. https://www.scribd.com/document/456528759/Spring-Materials. Supports: SH at 3.6 mm, 1700–1970 MPa; grade meaning.
80. MfgRobots, EN 10270-1 DH. https://www.mfgrobots.com/Article/material/metal/38565.html. Supports: DH description.
81. Century Spring, selecting an extension spring. https://www.centuryspring.com/resources/how-to-select-an-extension-spring. Supports: 30–45 % / 75 % MTS; hooks fail first.
82. Autodesk Inventor spring material tables. https://help.autodesk.com/cloudhelp/2026/ENU/Inventor-Help/files/GUID-E3E3709F-A30D-4089-9CF6-8AB3AEE1E899.htm and https://help.autodesk.com/cloudhelp/2023/ENU/Inventor-Help/files/GUID-2504979C-11F3-4886-A9C1-C6E28F2E438D.htm. Supports: G = 80,500 MPa; 11.2 Mpsi.
83. AmesWeb, extension spring formulas. https://amesweb.info/MechanicalSprings/extension-spring-formulas.aspx. Supports: C = D/d; hook factors.
84. Firgelli spring calculator. https://www.firgelliauto.com/blogs/engineering-calculators/spring-calculator. Supports: Wahl formula; 4 ≤ C ≤ 12; G = 79 GPa example.
85. MiSUMi catalogue page (GB/T 23935). https://th.c.misumi-ec.com/book/THA_EconomySeries_e-catalog2025/files/basic-html/page1177.html. Supports: initial tension definition.
86. Samson, "Understanding creep". https://www.samsonrope.com/resources/general/understanding-creep. Supports: SK75 / SK78 creep rates.
87. Marlow D12 78 datasheet. https://marinestore.co.uk/mm5/graphics/pdf/marlow-d12-78-data-sheet.pdf. Supports: creep drivers; SK99 strength.
88. Rigging Doctor, "Not all Dyneema is created equal". https://www.riggingdoctor.com/life-aboard/2020/4/12/not-all-dyneema-is-created-equal. Supports: %/day creep; rupture at 30 %.
89. COBEM 2005-0703, HMPE creep. https://abcm.org.br/anais/cobem/2005/PDF/COBEM2005-0703.pdf. Supports: creep at 15 % and 30 % of break load.
90. Espressif ESP32-C3 datasheet. https://documentation.espressif.com/api/resource/doc/file/aYwvqd1B/FILE/esp32-c3_datasheet_en.pdf. Supports: 5 µA deep sleep.
91. esp32.com, "ESP32-C3 power consumption doesn't match the datasheet". https://esp32.com/viewtopic.php?p=83684 (also p=108596, p=106467). Supports: measured currents; LED standby.
92. Mischianti, ESP32-C3 SuperMini. https://mischianti.org/esp32-c3-super-mini-high-resolution-pinout-datasheet-and-specs/. Supports: ≈ 43 µA without the LED.
93. Mischianti, SuperMini Plus v2. https://mischianti.org/esp32-c3-supermini-plus-v2-high-resolution-pinout-datasheet-and-specs/. Supports: 0.6–1.5 mA with the WS2812.
94. Mischianti, Plus Mini V1. https://mischianti.org/esp32-c3-plus-mini-1-esp32-c3_mini_v1-high-resolution-pinout-datasheet-schema-and-specs/. Supports: ME6211; 100–500 µA; ≈ 20 µA after the mod.
95. LionCircuits, ESP32-C3FH4X. https://www.lioncircuits.com/parts/ESP32-C3FH4X. Supports: TX 276–335 mA; RX 84–87 mA.
96. ESP-IDF ESP-NOW docs (C3). https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32c3/api-reference/network/esp_now.html. Supports: 1 Mbps default; sleep notes.
97. ESP-IDF deep-sleep wake stubs (C3). https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-guides/deep-sleep-stub.html. Supports: slow deep-sleep wake.
98. esp32.com, "wake up time and low power". https://esp32.com/viewtopic.php?p=25348. Supports: ≈ 160 ms wake.
99. MySensors forum, ESP-NOW node. https://forum.mysensors.org/post/110503. Supports: ≈ 200 mA during ESP-NOW TX; 5.4 µA sleep.
100. VŠB thesis, ESP-NOW with ESP32-C3. https://dspace.vsb.cz/items/09e3ddc2-0900-48a8-9faf-bb7c58d68e88. Supports: 34 µA deep sleep.
101. ME6211 listings. (a) https://www.hqonline.com/product-detail/linear-voltage-regulators---ldos-microne-me6211c33m5g-n-2500237468; (b) https://probots.co.in/me6211c33m5g-3-3v-ldo-voltage-regulator-pmic-sot-23-5.html. Supports: 30–60 µA quiescent current (conflicting).
102. DW01 datasheet. https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7158/5272_DW01.pdf. Supports: 3 µA / 0.1 µA.
103. TP4056 datasheet. https://wiki.adom.inc/blob/component/tp4056/docs/tp4056-datasheet.pdf. Supports: < 2 µA battery drain; 35–60 µA shutdown.
104. All About Circuits, TP4056 current. https://forum.allaboutcircuits.com/threads/tp4056-current-consumption.164076/. Supports: 1.6 mA anecdote.
105. Ultralife UBBP01 datasheet. https://engineering.purdue.edu/ece477/Archive/2008/Fall/F08-Grp02/datasheets/UBI-5154_UBBP01.pdf. Supports: < 10 %/month.
106. SparkFun 110 mAh LiPo. https://sparkfun.com/products/13251. Supports: < 8 %/month.
107. SOS Electronic / EEMB LiPol. https://www.soselectronic.com/articles/eemb/lipol-rechargeable-batteries-for-industrial-applications-2587. Supports: ≈ 3 %/month.

(Numbers 12 and 59 are intentionally unused.)
