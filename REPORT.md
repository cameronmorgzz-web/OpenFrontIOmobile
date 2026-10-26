# Report — phase gates

Every number below is produced by code in this repo. Generated blocks are refreshed by `make docs`, and `make test` fails if a gate regresses.

<!-- BEGIN:key -->
| | value | target |
|---|---|---|
| BOM, hardware + electronics | **EUR 148.99** (+ EUR 56 filament) | <= EUR 80 (**over**, see REPORT) |
| Print | 3538 g, 93.7 h, 17 plates | fits 256 x 256 x 256 |
| Dispersion at 4 m (calibrated, 1000 shots) | **sd 18.6 cm** (uncalibrated 30.2 cm) | <= 25 cm |
| Catch speed at 4 m | 5.82 m/s (physics minimum 5.8) | <= 4 m/s (**impossible beyond 2.06 m**) |
| Peak height | 1.91 m max | <= 2.3 m |
| Press -> launch | 4 m: 2.42 s, 5 m: 2.86 s | <= 2.5 s (5 m **misses**) |
| Cycle time | 3.5 s | <= 8 s |
| Feed (escapement) | 1500/1500 single feeds | single feed |
| Weakest printed part | SF 2.74: arm (absorber stop 5 m (beam+cup inertia)) | >= 2.5 |
| Button battery | 6.2 months | >= 3 months |
<!-- END:key -->

## Phase 1 — Research: **PASS, with caveats**

- **What is covered.** `research/SOURCES.md` tags every number the design uses: cans C1–C6, aerodynamics A1–A4, materials M1–M6, springs S1, friction S-mu, catching K1–K3, parts and prices P*, electronics E1–E7.
- **Physics.** Can geometry, pressure and strength, cylinder drag and Magnus effect, PETG anisotropy, fatigue and creep, and catch biomechanics are in `research/physics_notes.md`.
- **Parts.** Candidates with links and prices are in `research/parts_notes.md`.
- **Caveat.** Several pages could only be read through search snippets or USD mirrors, and these are marked "unverified" where they apply.

## Phase 2 — Hand calculations: **PASS, except 3 documented conflicts**

`python -m calc.run_all` → `calc/RESULTS.md` (ballistics, arm dynamics, motor and latency, latch, stresses for every loaded part, button battery).

<!-- BEGIN:gates -->
| check | value | result |
|---|---|---|
| Peak height <= 2.3 m (5 m shot) | 1.963 | PASS |
| Catch speed <= 4 m/s at 4 m | 5.821 | **FAIL** |
| Press->launch <= 2.5 s at 4 m | 2.420 | PASS |
| Press->launch <= 2.5 s at 5 m | 2.863 | **FAIL** |
| Cycle <= 8 s | 3.539 | PASS |
| Motor < 90% stall at 5 m | 0.796 | PASS |
| Servo trip margin >= 2 (worst mu, max e) | 4.403 | PASS |
| Latch self-locking at min e | 1.000 | PASS |
| Min SF (non-accidental) >= 2.5 | 2.749 | PASS |
| Dry-fire min SF >= 1 and absorber energy <= 20 J | 1.842 | PASS |
| Battery >= 3 months | 6.220 | PASS |
| Cap actuation 3-5 N | 4.324 | PASS |
| Springs <= 85% Fn at 5 m (330 ml) | 0.865 | **FAIL** |
<!-- END:gates -->

**Conflict 1: catch speed (physics).**
- The minimum possible catch speed at range R with drop dh is the minimum-energy shot: `v_c² = g(√(R² + dh²) − dh)` in vacuum.
- For 4 m/s with dh = 0.48 m, R can be at most 2.06 m.
- At 4 m the minimum is 5.82 m/s, including drag.
- The design flies that arc (D2).

**Conflict 2: 5 m latency (motor).**
- Cocking against the 5 m preload takes 1.82 s. With the 0.6 s feed, the escapement settle and the button, the total is 2.86 s.
- A motor fast enough to reach 2.5 s would have less than 25 % stall margin.
- At 4 m the latency passes (2.42 s).

**Conflict 3: 5 m spring margin.** The springs reach 86.5 % of their rated Fn at 5 m in the hand calc (about 93 % at the simulated preload), against a self-imposed 85 % margin. They stay under 100 %. See KNOWN_LIMITATIONS #16.

## Phase 3 — Simulation: **PASS**

### Launch model (MuJoCo 3.17, `sim/launch.py`)

- **Model:** a rigid arm with the CAD mass properties (`cad/mass_props.json`: arm assembly 0.473 kg, I = 0.0073 kg m²); a spring torque from the drum geometry; the cup, TPU pad and PTFE floor as contact geoms; a velocity-squared absorber with a hard end stop; drag and Magnus effect on the can in flight. It runs COCK, then FEED down the chute, then the latch delay, the swing, release and flight to the catch height.
- **Key finding:** the can rolls out over the cup lip and leaves about 5° below the arm-normal direction. This is handled by the +4° detent and by calibration.

### Monte Carlo (≥ 1000 runs, `sim/monte_carlo.py`)

**Varied per unit:**
- spring rate ±10 %, initial tension ±15 %
- cord and spring friction ±30 %
- frame/creep preload loss from FEA

**Varied per shot:**
- can mass ±4 %, can diameter ±0.3 mm
- pad, floor and rail friction ±30 %
- release detent seating σ 0.15°, latch jitter 0–20 ms
- Cd 0.6–0.9, CL −0.1–0.2, air density ±3 %, spin fraction

**Two studies:**
- **Calibrated:** 50 units × 20 shots, each unit set up with the CALIBRATION.md procedure, including 0.5 mm adjuster resolution and ±5 cm tape error.
- **Uncalibrated:** 1000 shots at nominal preload.

Results are in the key table above and in `sim/plots/monte_carlo_4m.png`.

### Can survival

<!-- BEGIN:can -->
- Peak can acceleration, 2 ms filtered, worst of 2000 simulated shots: **404 m/s2 (41 g)**, mostly centripetal, across the can axis.
- Extra liquid pressure across the 66 mm diameter: rho a D = 0.27 bar. Beer is at 2.0-2.5 bar, so the peak is 2.8 bar against the 6.2 bar (90 psi) buckle requirement for beverage cans [C4]: **SF 2.2**.
- Side-wall load on the 2 mm TPU pad: m a = 149 N, spread over a line contact of about 115 x 10 mm = 0.13 MPa. That is below the can's own internal pressure support, and far below the ~900 N axial benchmark [C5].
- For comparison, a 1 m drop onto tiles stops the can in about 1 mm: roughly 10 000 m/s2 (1000 g). Cans survive this most of the time, with a dent. The launch is about 25x gentler.
<!-- END:can -->

### Feed (`sim/feed_sim.py`)

300 trials × 5 cycles with a full magazine.

**Varied:**
- can–rail friction 0.12–0.45, can–can 0.10–0.40, wall friction 0.10–0.40
- can diameter 65.8–66.6 mm
- wall gap 0–0.6 mm, rail height ±0.3 mm, guide offset ±0.3 mm
- servo speed and torque ±30 %, can mass ±4 %

**Fixes the sim forced (D8, D8b):**
- The direct servo drive was back-driven by the column, so the escapement is now a toggle pushrod drive.
- A can yaw-wedged in 1 mm of clearance, so the column guides now have 3.2 mm.
- f2's tip stood 2.5 mm proud of the rail and stalled the last can, so it now sits below the rail.
- Lever ratio 1.8 double-fed 1.4 % of cycles, so the ratio is now 1.2.

**Final result:** 0 jams, 0 double feeds, 0 early releases in 1500 cycles. Can1 clears the gate within 0.223 s of the release command. Plot: `sim/plots/feed_sim.png`.

### FEA (CalculiX 2.21, `sim/fea.py`)

- **Mesh and material:** C10 tetrahedra (gmsh), orthotropic PETG: E 1800/1500 MPa, UTS XY 34 / Z 19 MPa. Each part is in its print orientation and assembly pose, with loads and fixes on half holes, at the 5 m setting (worst case).
- **Fatigue:** S_f = 0.6 × UTS at 10³ cycles.
- **Creep:** **every part loaded while cocked is held at full cocked load for 24 h** (a power cut while ARMED leaves the latch holding), with an allowable of 0.25 × UTS outside a 3 mm load-introduction zone (D17).
- **Changes this check forced:** the ring latch went from 10 to 12 mm thick with bigger bosses, and the pulley bracket got longer cheek roots and a 10 mm top plate.

<!-- BEGIN:fea -->
| part | case | vm p99.5 [MPa] | vm outside load zone | SF static | SF fatigue 10^3 | SF creep 24 h | min |
|---|---|---|---|---|---|---|---|
| arm | absorber stop 5 m (beam+cup inertia) | 7.44 | 7.88 | 4.57 | 2.74 | - | **2.74** |
| hub_catch | cocked 5 m: latch force on the catch pin | 2.21 | 1.65 | 15.39 | 9.23 | 5.14 | **5.14** |
| hub_drum | cocked 5 m: cord tension on the drum | 1.41 | 0.98 | 24.16 | 14.50 | 8.64 | **8.64** |
| ring_gear | cocked 5 m: latch pin load + tooth load | 2.29 | 2.19 | 14.87 | 8.92 | 3.88 | **3.88** |
| ring_latch | cocked 5 m: nose load | 4.16 | 3.03 | 8.17 | 4.90 | 2.81 | **2.81** |
| side_plate_left | cocked 5 m: shaft reaction | 1.32 | 1.23 | 25.84 | 15.50 | 6.93 | **6.93** |
| side_plate_right | cocked 5 m: shaft reaction | 1.45 | 1.34 | 23.50 | 14.10 | 6.33 | **6.33** |
| cup | release: centripetal envelope (330 @5 m / 500 @3.3 m) | 3.43 | 3.46 | 9.91 | 5.94 | - | **5.94** |
| cup | sim peak can acceleration 422 m/s2 (Monte Carlo worst) | 6.36 | 6.41 | 5.35 | 3.21 | - | **3.21** |
| stop_bracket | absorber peak 5 m | 1.05 | 0.58 | 32.41 | 19.44 | 65.80 | **19.44** |
| pulley_bracket | cocked 5 m: cord over the pulley | 4.72 | 2.45 | 7.20 | 4.32 | 3.46 | **3.46** |
| spring_yoke_front | cocked 5 m: 3 springs | 3.10 | 2.90 | 10.98 | 6.59 | 2.93 | **2.93** |

Preload lost to frame/cord-path deflection at full cock: 0.43 mm (fed into the Monte Carlo study as a per-unit loss).
<!-- END:fea -->

### Validation: simulation vs hand calculation (same inputs: 4 m preload, 138° release)

<!-- BEGIN:validation -->
| quantity | calc | sim | diff | explanation (> 15 %) |
|---|---|---|---|---|
| release speed [m/s] | 6.750 | 6.407 | -5.1 % | - |
| launch angle [deg] | 48.000 | 42.541 | -11.4 % | - |
| range [m] | 4.000 | 3.486 | -12.9 % | - |
| peak can acceleration [m/s2] | 194.322 | 282.536 | +45.4 % | Calc is a rigid-cup average; the sim resolves the TPU pad contact and is reported 2 ms-filtered. Both are far below the can's tolerance (REPORT.md). |
| feed time [s] | 0.600 | 0.552 | -8.1 % | - |
<!-- END:validation -->

## Phase 4 — CAD: **PASS**

build123d 0.13; every key dimension is in `cad/params.py`.

**Outputs:** 43 parts as STEP and STL, Bambu `.3mf` plates with per-object settings, renders from 4 angles plus an exploded view and the cocked state, and an assembly STEP.

**`make test` checks (`tests/`):**
- every part fits 256³ on the bed and is manifold;
- overhangs ≤ 50° except bridges ≤ 30 mm and holes ≤ 8.5 mm;
- minimum wall ≥ 1.6 mm (1st percentile, ray-cast);
- no interference at rest, cocked or release, through a 22-step arm sweep (with a can while firing) and through the 9-step escapement stroke;
- joint clearances ≥ 0.2 mm;
- every insert hole and bearing bore is covered by the BOM;
- 500 ml changes only `mag_bridge` (tested by rebuilding with `BEER_CAN_SIZE=500`);
- per-plate grams and time are present.

**Look:**
- rounded edges and chamfers;
- the motor is under a conical cover;
- a cable channel runs along the base;
- the button's screws are hidden under the snap-on cap.

## Phase 5 — Electronics and firmware: **PASS (host tests); ESP32 build NOT run**

**Wiring:** `electronics/` has the wiring SVGs, pin map, power tree and current budget. It covers the IRF4905 reverse-polarity protection, the SMBJ15A TVS, the 5 A fuse, the MP1584 servo/logic buck, and flyback diodes on the buzzer and haptic motor. All sensing uses real limit switches.

**Firmware (PlatformIO projects):**
- **Button:** deep sleep, HMAC-SHA256 with a sequence number, low-battery warning, pairing.
- **Launcher:** state machine IDLE → WARN → COCK → FEED → ARMED → FIRE → RESET, plus FAULT and DECOCK.

**Tests:** 82 unit and HIL-style tests, run by `firmware/tools/host_tests.sh` with g++ -Werror against a plant model with fault injection. Every fault code is exercised; the last test asserts the set.

**Not done: ESP32 build.** `pio run -e esp32c3` could not run, because the PlatformIO registry was blocked by the build environment's network policy. KNOWN_LIMITATIONS #4.

## Phase 6 — Independent review

<!-- BEGIN:review -->
An independent review agent read the repo cold: it had the brief and the files, not the design reasoning. It reported 3 critical, 14 major and 8 minor findings. Each was verified, and each is fixed or documented below.

**Critical, all fixed:**
1. **A held or stuck button re-fired every 2.5 min.** Now only a real press (GPIO wake) can send FIRE (`button_logic.h: shouldSendFire`, new test).
2. **The pinion/ring mesh was unguarded and the guards had no fasteners.** The gear guard now has a hood over the mesh and covers 25°–312°. It is held by 3 screws into bosses, and the motor cover by 2 screws into plate inserts. The open 70° arc is documented in SAFETY.
3. **The docs said the warning comes before the arm moves.** It doesn't: cocking starts with the warning. SAFETY rule 4 now states this plainly. Delaying the motor by 1.5 s would push 4 m latency to 3.9 s.

**Major:**
- **Fixed:**
  - Safe-release procedure rewritten: shorted-motor brake, pin pulled with a 1 m cord, dry-fire fallback. Power-cut behaviour corrected: the arm unwinds through the back-drivable gearbox and cannot throw.
  - Absorber changed to the AC1416-1, rated 2.6 m/s against 2.0–2.5 m/s at impact.
  - Button LiPo goes to the 5V pin, not 3V3.
  - Buzzer and beacon are 12 V parts.
  - The safety pin now presses two micro switches.
  - Limit-switch and sensor brackets added, with a mounting table (ASSEMBLY §7b).
  - Shaft is 300 mm, cut into the pivot and the pulley axle.
  - Cup screws are M3 × 30.
  - Hub joint has 6 dowels and 6 screws.
  - Missing hardware added to the BOM: yoke pins, button passives, M2 screws, 608 count.
  - Pulley-bracket wall raised from 1.0 to ≥ 1.6 mm.
- **Documented:** 5 m spring load at the simulated preload (KNOWN_LIMITATIONS #16).

**Minor:**
- **Fixed:**
  - Motor screw count.
  - Latency, sensitivity and test-count numbers aligned across the docs.
  - Stale wiring notes removed.
  - Safety-pin path described correctly.
  - Servos now start 300 ms apart at power-up.
  - FIRE waits until the escapement has been at HOLD for 400 ms (the electronics review's finding).
- **Documented:** two `mag_bridge` prints for 500 ml (#17), clear-text pairing key (#19).

**A modelling gap the review exposed:** the cup was checked against the hand-calc load, but the simulation's worst can acceleration is higher (434 m/s²). Under the new FEA case for that load the cup's fatigue SF was 1.73, so the cup now has a full-height socket and a thicker floor and wall. The new SF is in the FEA table above.
<!-- END:review -->
