# Calibration

The simulation is not the real machine. Spring batches vary ±10 % in rate and ±15 % in initial tension, friction varies ±30 %, and PETG prints vary. The design therefore has three adjustments, and this procedure sets them on your build. Allow about 30 minutes and 20 throws (use water-filled cans for the first ones).

You need:
- a tape measure (5 m)
- a luggage scale (digital, 0.01 kg resolution; about €5)
- a felt pen
- masking tape
- a phone with slow-motion video (optional)

## 1. Measure what you bought (before assembly)

Datasheets can be wrong, and AliExpress parts have none. Measure.

**Spring rate and initial tension (each of the 3 springs):**
1. Hang the spring from a hook. Hang the luggage scale from the spring's lower loop and pull the scale down by hand.
2. Note the force when the coils just start to separate. That is F0 (expected 14.5 N ≈ 1.48 kg on the scale).
3. Pull until the spring is 60 mm longer than free length; measure with the tape at the loop inner edges. Note F60.
4. Rate R = (F60 − F0) / 60 mm. Expected 1.2 N/mm, so F60 ≈ 86.5 N ≈ 8.8 kg.
5. Use three springs within ±5 % of each other. If one is off, the arm twists slightly; mark it and put it in the middle position.

**Button cap switch force:** press the cap down with the scale's hook under a flat washer. Expected 4.3 N (0.44 kg). Below 3 N the button false-triggers when knocked, so add a spacer under the springs.

**Escapement servo:** at hold, with the magazine full, the horn must sit on the mark 8° past the pushrod line (`ESC_PHI_HOLD`). If it does not, adjust `kEscClosedUs` in `firmware/common/src/config.h` ±20 µs at a time.

## 2. Mechanical zero

1. Safety pin **in**, arm resting on the absorber, power off.
2. Set both M6 preload adjusters to the **4 m starting value: 43 mm** of exposed thread between yoke face and wing nut (the scale on the yoke; 1 turn = 1 mm).
3. Set the release-angle stop to the **middle detent (138°)** for the first throws.
4. Check the cord runs in the pulley groove and is not twisted.

## 3. First throws (water cans, 330 ml)

1. Mark a line 4 m in front of the cup pivot. Put masking-tape marks every 25 cm from 3 m to 5 m.
2. Fire 5 cans and note where each lands at the catch height (about hip height, 0.9 m). Ask a helper to catch, or film from the side and read the landing on the floor marks. Floor landings are about 0.85 m longer than hip-height landings at the 4 m setting, so subtract 0.85 m if you read them off the floor.
3. Average the 5 landings: R̄.

## 4. Adjust range with preload (fine knob)

Change preload by **ΔX = (4.00 − R̄) / 0.067 mm**: 0.067 m of range per mm, i.e. per full turn of the wing nuts. Turn both nuts by the same amount. Half turns are fine.

- Example: R̄ = 3.70 m → ΔX = 4.5 mm → tighten 4½ turns each.
- Limits: 0–70 mm of adjuster travel. If you need more than 70 mm, a spring is weak (re-measure, §1).

Repeat 5 throws. Two iterations normally land within ±10 cm of 4 m. The Monte Carlo study models exactly this procedure: 50 builds calibrated this way, 20 shots each (`sim/monte_carlo.py`).

## 5. Trim angle with the detents (coarse knob)

If the throw is too **flat** (peaks below head height, hard to catch), move the stop one detent up. If it is too **lofty** (peak above 2.3 m), move it one down. Each detent is 4°. Re-run §4 after changing detents.

- 134° (−4°): lower, faster arc.
- 138°: nominal.
- 142° (+4°): the detent used for 4 m in the simulation, because the can rolls out about 5° low.

## 6. Settings table (starting points; your values will differ)

| Range | Detent | Preload (exposed thread) | Note |
|---|---|---|---|
| 3 m | 138° | ~28 mm | |
| 4 m | 142° | ~43 mm | default |
| 5 m | 142° | ~59 mm | springs at 85 % Fn; latency 2.8 s |
| 500 ml, ≤ 3.3 m | 142° | find with §4 | reprint `mag_bridge` × 2 with `CAN_SIZE = "500"` |

Write your final numbers on the yoke with the felt pen.

## 7. Re-check schedule

- **After the first 50 throws:** PETG settles. Re-run §3–4.
- **Every 500 throws, or if the range drifts by more than 20 cm:**
  - check the cord for fraying, and replace it at the first broken strand;
  - check the absorber for oil;
  - check the latch nose dowel for wear.
- **If the machine sat cocked for hours (power cut):** re-run §3. Creep may have cost 1–2 mm of preload.
