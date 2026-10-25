# Sources

The source tags used in code comments (`[C1]`, `[A1]`, `[P6a]` …) are indexed here.
The full research notes, with every excerpt and its source number, are in
`physics_notes.md` (physics and materials, numbered 1–107) and `parts_notes.md` (parts and prices).

> **How the research was done, honestly:** this sandbox's network proxy blocked page fetches,
> so no product page or PDF could be opened directly. Every value was taken from search-engine
> excerpts of the cited pages, and the pages themselves were not opened. Values tagged
> **unverified** in the notes should be checked against the page before ordering. The safety-critical
> ones (spring Fn, motor stall, absorber energy) have a measurement step in `CALIBRATION.md`.

## Cans
| tag | value used | source (physics_notes #) |
|---|---|---|
| C1 | 330 ml standard: Ø66 (body) × 115.2 mm; we use Ø66.2 nominal, ±0.3 in Monte Carlo | Crown 330 ml standard (#1); lid 202 ≈ 52 mm (#2) |
| C2 | 500 ml: Ø66.3 × 168.0 mm, 12.4 g empty | Ardagh/nomoQ 500 ml spec (#4) |
| C3 | 330 ml empty ≈ 13 g; full 343–353 g (beer ≈ water density, cola 1.026–1.03) → design 0.355 kg, MC ±4 % | IAI Alustory (#5), Harvard (#25), Flinn (#26) |
| C4 | Side wall ≈ 0.10 mm; beer ≈ 2 bar, cola 2.8–3.8 bar at 16–24 °C; dome buckle requirement 6.2 bar (90 psi) | #7–#11, #13 |
| C5 | Axial column load benchmark ≈ 900 N (empty); filled cans stronger | #16, #18 |
| C6 | Aluminium on plastic μ: 0.20 dry, 0.15 wet, 0.12 soapy; MC range 0.12–0.40 | Rexnord (#21, #22), Misumi (#23) |

## Aerodynamics
| tag | value used | source |
|---|---|---|
| A1 | Broadside Cd for a short cylinder: Cd ≈ 0.024/AR + 0.633 ≈ 0.65 at AR 1.74; design 0.70, MC 0.60–0.90 (also covers tumbling) | Yang et al. / Zdravkovich (#28, #29), USGS (#31) |
| A2 | End-on Cd 0.81–0.9 (only if the can flies end-on; not our case) | Hoerner via Aerospaceweb (#27), EES (#32) |
| A3 | Magnus at spin ratio S ≈ 0.14: no positive-lift data below S ≈ 0.3, sign reversal 0.4–0.7 → design CL = 0, MC −0.1…+0.2 | ICAS 2012 (#33), #34–#36 |
| A4 | Liquid spin-up time ≈ 5 s ≫ 1 s flight → only the shell (~15 % of can inertia) spins with the arm; minor-axis spin with a liquid is not stable (energy sink) | Greenspan & Howard (#39), Efroimsky (#37), ASU (#38) |

## Materials
| tag | value used | source |
|---|---|---|
| M1 | Bambu PETG HF: tensile XY 34 ± 4 MPa, bending 64 (XY) / 48 (Z) MPa, bending modulus 2050 MPa, 1.28 g/cm³, HDT 69 °C | Bambu store (#41), Filament2Print (#42) |
| M2 | PETG Basic: bending 65–75 (XY) / 48–56 (Z) MPa, modulus 1670 MPa | #43, #44, #45 |
| M3 | Z/XY tensile ratio measured 0.44 (P1S tensile) to 0.75 (bending); brief: 0.5–0.6 → **design sut_z = 19 MPa (0.56)** | #47, #48, #49 |
| M4 | Creep: avoid sustained stress above ~30 % of yield → **design limit 25 % UTS** | QIDI (#54, unverified), Stankevics 2025 (#50), UTS (#51) |
| M5 | Fatigue S-N of printed PETG exists (R = 0.1–0.2) → **design S(1e3) = 0.6 UTS**; our design life is 1e3–1e4 shots | Kim & Huang 2021 (#55), Martins 2024 (#56) |
| M6 | TPU 95A HF: 27.3 MPa, > 650 % elongation, 1.22 g/cm³ | #60, #61 |

## Springs, cord, mechanisms
| tag | value used | source |
|---|---|---|
| S1 | G = 79–80.5 GPa; EN 10270-1 SH/DH Rm 1300–2940 MPa; body torsion allowable 30–45 % MTS, hook bending 75 %; Wahl factor | #78–#84 |
| S2 | Dyneema SK78 creep ≈ 0.033 %/month at 20 % load | Samson (#86), Marlow (#87) |
| S-mu | Steel on PETG cam μ 0.15–0.40 (design range; no direct source found → bracket used in the latch calc) | engineering estimate, flagged |
| K1 | Clay-pigeon traps: spring arm + latch + motor re-cock; most repeatable precedent | US3937203 (#67), US11441879 (#68), US3621828A (#69) |
| K2 | Tennis-ball flywheel machines: 18.9 ± 0.89 m/s (CV ≈ 4.7 %) | Norris 2012 (#70) |
| K3 | Escapements: interlocked two-finger; failure modes jam, skew, shingling | SMC MIW (#72), US4149641A (#73), US5547105A (#74) |

## Parts (full tables in `parts_notes.md`, prices seen 2026-10-25)
| tag | part | key published spec | source |
|---|---|---|---|
| P6a | Gutekunst Z-141HI extension spring | d 2.0, De 16, L0 121 mm, R 1.2 N/mm, F0 14.5 N, Fn 166.7 N, sn 126.84 mm | https://www.federnshop.com/en/products/extension_springs/z-141hi.html |
| P7a | JGB37-545 56:1 (fallback motor) | 110 rpm no-load, 4.5 kg·cm @ 95 rpm, stall 35 kg·cm / 5 A | precisionminidrives NFP-JGB37-545-EN |
| P7c | 37GB555 12 V 30:1 (chosen) | 133 rpm no-load, 10 kg·cm @ 100 rpm, 1.5 A, 13 W | digiwarestore 37GB555 page |
| P9 | MG90S | stall 1.8 kg·cm @ 4.8 V (2.2 @ 6 V) | listing data, parts_notes §9 |
| P11 | Mean Well GST60A12-P1J | 12 V 5 A, CE, Level VI | Mean Well datasheet (series GST60A) |
| P21 | AC1416-x shock absorber | M14×1.5, 16 mm stroke, 20 J/cycle, -1 = up to 2.6 m/s | Hennlich/EMC (#21 in parts_notes) |
| E1 | ESP32-C3 deep sleep 5 µA | Espressif datasheet (#90) |
| E2 | SuperMini ≈ 43 µA with LED removed | Mischianti (#92) |
| E3 | ME6211 Iq 30–60 µA | #101 |
| E4 | TX 276–335 mA, RX 84–87 mA | #95, #99 |
| E5 | Deep-sleep wake ≈ 160 ms (ESP32) | #98 |
| E6 | TP4056 < 2 µA battery drain, DW01 ≈ 3 µA | #102, #103 |
| E7 | LiPo self-discharge 3–10 %/month (design 5 %) | #105–#107 |
