# Print guide (Bambu Lab A1, 0.4 mm nozzle, no AMS)

Every part has a flat face on the bed and is pre-oriented in its STL / 3MF. Load each `cad/3mf/plate_*.3mf` in Bambu Studio. Object names, materials and per-part wall/infill settings are already set. Check the plate's filament, slice and print.

<!-- BEGIN:totals -->
<!-- END:totals -->

## Global settings

| | PETG (all structural parts) | TPU 95A (feet, pads) |
|---|---|---|
| Profile | Bambu "Generic PETG" @ 0.20 mm Standard | "Generic TPU" @ 0.20 mm |
| Nozzle / bed | 240–250 °C / 70 °C, textured PEI | 225 °C / 35 °C |
| Walls | per part (4–6, see table) — **never fewer than 4 on loaded parts** | 3 |
| Top / bottom | 5 / 4 layers | 4 / 3 |
| Infill | per part, gyroid | 20 % gyroid |
| Cooling | 30–50 %, off for the first 3 layers | 50 % |
| Supports | **off** for every part (all overhangs ≤ 50° or bridges ≤ 30 mm, checked by `tests/test_print.py`) | off |
| Brim | 5 mm on `arm`, `side_plate_*`, `base_*` (long flat parts lift at the corners) | none |
| Seam | aligned, rear | |

Dry PETG at 65 °C for 4 h before printing the arm, hubs, ring gear and latch. Wet PETG loses 20–30 % of its layer strength, and the safety factors assume dry filament.

## Before the real parts: two test prints (≈ 40 min)

1. **Fit coupon.** Print `ring_latch`. A 4 mm dowel must press into the nose hole with a vise and slide freely in the pivot hole.
   - If the press hole is loose, set `CLR_PRESS` 0.05 smaller in `cad/params.py`.
   - If the pivot binds, set `CLR_SLIDE` 0.05 larger.
   - Then run `python -m cad.build`.
2. **Insert check.** Heat-set one M3 insert into `stop_bracket` at 220 °C. It must sit flush and not pull out with an M3 screw torqued by hand. If your inserts are OD 4.6 rather than 4.0–4.2, set `M3_INSERT_HOLE = 4.4` and rebuild (D19).

## Orientation rules (why parts sit the way they do)

- **arm, hub_drum, hub_catch:** lie flat (mechanism plane on the bed). The bending loads run along the layers, and Z strength (19 MPa) is never in the load path. FEA arm SF: static 4.9, fatigue 2.9.
- **ring_gear, ring_latch:** flat, so the teeth and the latch nose are printed in-plane.
- **side plates:** flat. The bosses face up.
- **base_front / base_rear:** printed upside down as open trays (deck on the bed), with no overhangs.
- **pulley_bracket:** top plate on the bed. The cheeks grow up; FEA creep SF 3.4 at 24 h cocked.
- **magazine walls:** on their outer face. The rail ledge grows up.

## Per-part settings

<!-- BEGIN:parts -->
<!-- END:parts -->

## Plates

<!-- BEGIN:plates -->
<!-- END:plates -->

## After printing

- **Heat-set inserts:** use 220 °C and a flat tip, and press them straight. Count them: 49 in total.
- **Dowel holes:** ream with a 4 mm drill by hand if a dowel will not start.
- **PTFE tape:**
  - Cup floor: one strip, 25 mm wide.
  - Chute rails: both ledges, full length.
  - Reduces can friction so the feed and the launch angle repeat (MuJoCo: the floor friction moves the launch angle by about 5°).
- **TPU pad:** glue the cup pad to the cup back wall with CA glue.
