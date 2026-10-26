# Print guide (Bambu Lab A1, 0.4 mm nozzle, no AMS)

Every part has a flat face on the bed and is pre-oriented in its STL / 3MF. Load each `cad/3mf/plate_*.3mf` in Bambu Studio. Object names, materials and per-part wall/infill settings are already set. Check the plate's filament, slice and print.

<!-- BEGIN:totals -->
**53 printed parts on 17 plates: 3538 g (PETG 3502 g, TPU 36 g), 93.7 h of printing** (slicer-independent estimate from part volume, walls and infill; Bambu Studio will differ by about ±15 %).
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
| part | material | qty | walls | infill | grams | time (h) | plate | note |
|---|---|---|---|---|---|---|---|---|
| arm | PETG | 1 | 6 | 35 % | 150 | 3.7 | PETG_13 | lies flat: arm bending is in the layer plane |
| base_front | PETG | 1 | 4 | 25 % | 365 | 9.1 | PETG_5 | deck down on the bed; open ribbed underside |
| base_rear | PETG | 1 | 4 | 25 % | 300 | 7.5 | PETG_6 |  |
| btn_cap | PETG | 1 | 4 | 25 % | 18 | 0.5 | PETG_11 | top face down; snap ring has a 45 deg ramp |
| btn_foot_ring | TPU | 1 | 3 | 100 % | 5 | 0.4 | TPU_1 |  |
| btn_shell | PETG | 1 | 4 | 20 % | 46 | 1.2 | PETG_16 | upright; USB-C window top is a 10 mm bridge |
| btn_switch_plate | PETG | 1 | 4 | 40 % | 22 | 0.6 | PETG_13 |  |
| btn_tray | PETG | 1 | 3 | 30 % | 9 | 0.2 | PETG_13 |  |
| cup | PETG | 1 | 4 | 20 % | 108 | 2.8 | PETG_15 |  |
| cup_pad | TPU | 1 | 3 | 100 % | 12 | 1.0 | TPU_1 |  |
| ebox | PETG | 1 | 3 | 15 % | 148 | 3.8 | PETG_11 |  |
| ebox_lid | PETG | 1 | 3 | 15 % | 46 | 1.2 | PETG_12 |  |
| esc_servo_mount | PETG | 1 | 4 | 40 % | 13 | 0.4 | PETG_10 |  |
| escapement_rocker | PETG | 1 | 6 | 100 % | 14 | 0.4 | PETG_16 |  |
| foot | TPU | 4 | 3 | 40 % | 5 | 0.4 | TPU_1 |  |
| gear_guard | PETG | 1 | 3 | 15 % | 132 | 3.4 | PETG_7 |  |
| hub_catch | PETG | 1 | 6 | 50 % | 85 | 2.2 | PETG_11 |  |
| hub_drum | PETG | 1 | 6 | 50 % | 107 | 2.7 | PETG_15 |  |
| latch_servo_mount | PETG | 1 | 4 | 40 % | 43 | 1.2 | PETG_13 |  |
| mag_bridge_back | PETG | 1 | 4 | 30 % | 22 | 0.6 | PETG_16 | ONLY part to reprint for 500 ml (CAN_SIZE) |
| mag_bridge_top | PETG | 1 | 4 | 30 % | 22 | 0.6 | PETG_16 | ONLY part to reprint for 500 ml (CAN_SIZE) |
| mag_chute_left | PETG | 1 | 4 | 25 % | 59 | 1.5 | PETG_15 |  |
| mag_chute_right | PETG | 1 | 4 | 25 % | 59 | 1.5 | PETG_15 |  |
| mag_wall_left_lower | PETG | 1 | 4 | 20 % | 121 | 3.1 | PETG_3 |  |
| mag_wall_left_upper | PETG | 1 | 3 | 15 % | 107 | 2.7 | PETG_14 |  |
| mag_wall_right_lower | PETG | 1 | 4 | 20 % | 121 | 3.1 | PETG_4 |  |
| mag_wall_right_upper | PETG | 1 | 3 | 15 % | 107 | 2.7 | PETG_14 |  |
| motor_cover | PETG | 1 | 3 | 15 % | 51 | 1.5 | PETG_12 |  |
| pulley_bracket | PETG | 1 | 5 | 50 % | 35 | 0.9 | PETG_12 | top plate on the bed; cheeks grow up (creep SF 3.4 at 24 h cocked, sim/fea.py) |
| ring_gear | PETG | 1 | 5 | 50 % | 239 | 5.9 | PETG_10 | teeth in the layer plane |
| ring_latch | PETG | 1 | 6 | 100 % | 24 | 0.6 | PETG_12 |  |
| safety_pin_handle | PETG | 1 | 4 | 40 % | 5 | 0.1 | PETG_9 |  |
| sensor_bracket | PETG | 1 | 4 | 60 % | 5 | 0.2 | PETG_9 | can-in-cup TCRT5000 |
| shaft_cap_left | PETG | 1 | 3 | 30 % | 4 | 0.1 | PETG_5 |  |
| shaft_cap_right | PETG | 1 | 3 | 30 % | 4 | 0.1 | PETG_5 |  |
| shaft_spacer_left | PETG | 1 | 4 | 40 % | 3 | 0.1 | PETG_5 |  |
| shaft_spacer_mid | PETG | 1 | 4 | 40 % | 2 | 0.1 | PETG_5 |  |
| side_cheek_left | PETG | 1 | 3 | 15 % | 122 | 3.1 | PETG_8 |  |
| side_cheek_right | PETG | 1 | 3 | 15 % | 122 | 3.1 | PETG_9 |  |
| side_plate_left | PETG | 1 | 4 | 30 % | 263 | 6.5 | PETG_1 | outer face down; loads in the layer plane |
| side_plate_right | PETG | 1 | 4 | 30 % | 257 | 6.4 | PETG_2 | outer face down; loads in the layer plane |
| spring_yoke_front | PETG | 1 | 6 | 60 % | 27 | 0.7 | PETG_11 |  |
| spring_yoke_rear | PETG | 1 | 6 | 60 % | 27 | 0.7 | PETG_11 |  |
| stop_bracket | PETG | 1 | 6 | 60 % | 59 | 1.5 | PETG_9 |  |
| switch_bracket | PETG | 6 | 4 | 60 % | 5 | 0.1 | PETG_9 | 3 limit switches + 2 safety-pin switches + 1 spare |
<!-- END:parts -->

## Plates

<!-- BEGIN:plates -->
| plate file | material | grams | time (h) | parts |
|---|---|---|---|---|
| `plate_PETG_1.3mf` | PETG | 262 | 6.6 | side_plate_left |
| `plate_PETG_2.3mf` | PETG | 257 | 6.5 | side_plate_right |
| `plate_PETG_3.3mf` | PETG | 121 | 3.1 | mag_wall_left_lower |
| `plate_PETG_4.3mf` | PETG | 121 | 3.1 | mag_wall_right_lower |
| `plate_PETG_5.3mf` | PETG | 377 | 9.6 | base_front, shaft_cap_left, shaft_cap_right, shaft_spacer_left, shaft_spacer_mid |
| `plate_PETG_6.3mf` | PETG | 300 | 7.6 | base_rear |
| `plate_PETG_7.3mf` | PETG | 132 | 3.5 | gear_guard |
| `plate_PETG_8.3mf` | PETG | 146 | 3.9 | side_cheek_left, switch_bracket, switch_bracket, switch_bracket, switch_bracket, switch_bracket |
| `plate_PETG_9.3mf` | PETG | 196 | 5.2 | side_cheek_right, switch_bracket, sensor_bracket, safety_pin_handle, stop_bracket |
| `plate_PETG_10.3mf` | PETG | 252 | 6.4 | ring_gear, esc_servo_mount |
| `plate_PETG_11.3mf` | PETG | 305 | 8.0 | ebox, hub_catch, spring_yoke_front, spring_yoke_rear, btn_cap |
| `plate_PETG_12.3mf` | PETG | 156 | 4.3 | ebox_lid, ring_latch, motor_cover, pulley_bracket |
| `plate_PETG_13.3mf` | PETG | 224 | 5.9 | arm, latch_servo_mount, btn_switch_plate, btn_tray |
| `plate_PETG_14.3mf` | PETG | 214 | 5.5 | mag_wall_left_upper, mag_wall_right_upper |
| `plate_PETG_15.3mf` | PETG | 334 | 8.6 | mag_chute_left, mag_chute_right, cup, hub_drum |
| `plate_PETG_16.3mf` | PETG | 105 | 2.9 | mag_bridge_top, mag_bridge_back, escapement_rocker, btn_shell |
| `plate_TPU_1.3mf` | TPU | 36 | 3.0 | btn_foot_ring, cup_pad, foot, foot, foot, foot |
<!-- END:plates -->

## After printing

- **Heat-set inserts:** use 220 °C and a flat tip, and press them straight. Count them: 54 in total.
- **Dowel holes:** ream with a 4 mm drill by hand if a dowel will not start.
- **PTFE tape:**
  - Cup floor: one strip, 25 mm wide.
  - Chute rails: both ledges, full length.
  - Reduces can friction so the feed and the launch angle repeat (MuJoCo: the floor friction moves the launch angle by about 5°).
- **TPU pad:** glue the cup pad to the cup back wall with CA glue.
