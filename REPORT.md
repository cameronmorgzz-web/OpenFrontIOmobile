# Report — phase gates

Every number below is produced by code in this repo. Generated blocks are refreshed by `make docs`, and `make test` fails if a gate regresses.

<!-- BEGIN:key -->
<!-- END:key -->

## Phase 1 — Research: **PASS, with caveats**

- **What is covered.** `research/SOURCES.md` tags every number the design uses: cans C1–C6, aerodynamics A1–A4, materials M1–M6, springs S1, friction S-mu, catching K1–K3, parts and prices P*, electronics E1–E7.
- **Physics.** Can geometry, pressure and strength, cylinder drag and Magnus effect, PETG anisotropy, fatigue and creep, and catch biomechanics are in `research/physics_notes.md`.
- **Parts.** Candidates with links and prices are in `research/parts_notes.md`.
- **Caveat.** Several pages could only be read through search snippets or USD mirrors, and these are marked "unverified" where they apply.

## Phase 2 — Hand calculations: **PASS, except 2 documented target conflicts**

`python -m calc.run_all` → `calc/RESULTS.md` (ballistics, arm dynamics, motor and latency, latch, stresses for every loaded part, button battery).

<!-- BEGIN:gates -->
<!-- END:gates -->

**Conflict 1: catch speed (physics).**
- The minimum possible catch speed at range R with drop dh is the minimum-energy shot: `v_c² = g(√(R² + dh²) − dh)` in vacuum.
- For 4 m/s with dh = 0.48 m, R can be at most 2.06 m.
- At 4 m the minimum is 5.82 m/s, including drag.
- The design flies that arc (D2).

**Conflict 2: 5 m latency (motor).**
- Cocking against the 5 m preload takes 1.75 s. Add the 0.6 s feed and the 0.4 s escapement settle, and the total is 2.79 s.
- A motor fast enough to reach 2.5 s would have less than 25 % stall margin.
- At 4 m the latency passes (2.39 s).

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
<!-- END:fea -->

### Validation: simulation vs hand calculation (same inputs: 4 m preload, 138° release)

<!-- BEGIN:validation -->
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

**Tests:** 81 unit and HIL-style tests, run by `firmware/tools/host_tests.sh` with g++ -Werror against a plant model with fault injection. Every fault code is exercised; the last test asserts the set.

**Not done: ESP32 build.** `pio run -e esp32c3` could not run, because the PlatformIO registry was blocked by the build environment's network policy. KNOWN_LIMITATIONS #4.

## Phase 6 — Independent review

<!-- BEGIN:review -->
<!-- END:review -->
