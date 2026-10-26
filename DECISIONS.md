# Decisions

One line of "why" per decision; the numbers behind each one are in the file it points to.
IDs are cited from code comments.

## Physics and targets

- **D1 — Spring catapult arm, not a flywheel, pneumatic or linear launcher.** A rotating arm gives a repeatable release angle from a hard stop, stores energy in off-the-shelf extension springs, and needs no compressed air (an Italian home user should not run a pressure vessel). Flywheels shear the can label and spin it unpredictably. (`research/physics_notes.md`)
- **D2 — Fly the minimum-catch-speed arc (~47 deg), not the 45 deg max-range arc.** The brief's catch speed target (≤ 4 m/s) is physically impossible beyond 2.06 m of range with a 0.48 m launch-to-catch drop: at 4 m the lowest possible catch speed is 5.82 m/s with drag. Choosing the arc that minimises catch speed is the best that physics allows, and it costs < 1 % in launch speed versus the max-range arc. (`calc/RESULTS.md` §1, `tests/test_calc.py`)
- **D3 — The can flies axis-parallel to the pivot, with top-spin from roll-out.** Its drag is modelled at Cd 0.6–0.9 (cylinder side-on) and its lift at CL −0.1–0.2 (Magnus effect), and both are sampled in the Monte Carlo study. A 2 mm TPU pad on the cup's back wall keeps the spin low. (`calc/ballistics.py`)
- **D4 — Throw range is set by spring preload; the release angle is a coarse trim.** Preload changes range by about 0.067 m per mm (one M6 turn = 1 mm), which is a fine, linear knob. The 134/138/142 deg detents correct the launch angle for roll-out. **D4u:** 500 ml cans use the same springs; their range is capped at about 3.3 m by the 85 % spring-load limit.

## Mechanism

- **D5 — Three Gutekunst Z-141HI springs on a 30 mm drum.** Two springs would run at 105 % of Fn (rated maximum force) for the 5 m shot. Three run at 85 % with a datasheet you can trust; AliExpress springs have no published rate. (`calc/arm_dynamics.py`, `research/parts_notes.md` §6)
- **D6 — Cocking is a ring gear (80T) driven by a steel 16T pinion on a 37GB555 30:1 motor with an encoder.** The JGB37-545 motor could not meet the 2.5 s latency. A PETG pinion fails on fatigue. The motor sits outside the right plate because it does not fit inside. (`calc/motor.py`, `calc/stress.py`)
- **D7 — The magazine is a 30 deg chute from can1 plus a vertical column over can2, and only `mag_bridge` changes for 500 ml.** Can1 sits 190 mm from the cup (14 mm clear of the cup's sweep, which MuJoCo found clashing at 175 mm). Rails at the can ends keep the magazine clear of the cup's width.
- **D8 — The escapement is a seesaw.** f1 is a post taller than the can's centre, so a cylinder cannot climb it. f2 sits under the can1/can2 V and rises behind can1. With lever ratio 1.2, f2 rises about 21 mm: the 1.8 ratio double-fed in 1.4 % of cycles. f2's tip sits 1 mm below the rail at hold, because a proud tip stalled the last can. The column guides have 3.2 mm clearance, because 1 mm let a can yaw 0.5 deg and wedge. Result: 1500/1500 single feeds. (`sim/feed_sim.py`)
- **D8b — The escapement is driven by a servo horn and pushrod toggle, not directly by the servo.** The can column back-drove a directly mounted MG996R. At hold the horn is 8 deg past dead centre, so the load locks the linkage. The firmware pre-stages the horn to 65 deg during COCK, where f1 still stands 28 mm. It finishes the stroke once the arm is cocked, so the feed takes 0.6 s instead of 0.86 s. An MG90S was tried in the sim and jammed.
- **D9 — An over-centre toggle latch on the ring, tripped by a frame-mounted MG996R.** It is self-locking (e = +1.5 mm closing). The trip-force margin is 4.5–7× at the worst friction (`calc/latch.py`). Because the latch rides on the ring, no retract is needed before FIRE. The ring returns during RESET.
- **D10 — The motor holds the cocked position in closed loop, and decock is the motor in reverse.** Stored energy is never released except through FIRE (into the absorber) or a controlled reverse. A power cut while ARMED leaves the self-locking latch holding, which is why every part loaded while cocked passes a 24 h creep check (D17).
- **D11 — An AC1416-2 hydraulic absorber (20 J, 16 mm) at r = 80 mm stops the arm.** It also absorbs a dry fire: 15.1 J worst case (5 m), arm SF 1.9 and stop-bracket SF 6.1 for that accidental load.
- **D12 — A 12 V Mean Well GST60A12 CE desktop brick powers the launcher.** You never touch mains (brief). 5 A covers the 4.9 A cocking peak at 5 m. The 5 A fuse protects the wiring against a short, not against a stall; the firmware's stall timeout does that. (`electronics/WIRING.md`)

## Printing and structure

- **D13 — PETG for every loaded part, TPU for feet and pads, no PLA.** Every part is oriented so the governing stress lies in the layer plane. Anisotropy is Z = 19 MPa against XY = 34 MPa (56 %).
- **D14 — Holes and slots up to 8.5 mm wide count as self-bridging, and flat ceilings up to 30 mm wide are allowed.** These are the brief's bridge rule, applied in `cad/checks.py`. Everything else stays at or under 50 deg.
- **D15 — Hand calcs credit the infill core at 0.5 × infill fraction.** This is conservative. Walls and skins are taken at full strength.
- **D16 — Monte Carlo runs two studies:** calibrated (50 units × 20 shots, each unit calibrated as in CALIBRATION.md) and uncalibrated (1000 shots at nominal preload). The ±25 cm dispersion target is judged on the calibrated study, because that is how the kit is used.
- **D17 — FEA uses the 99.5th-percentile von Mises stress over all nodes for static and fatigue checks, and excludes a 3 mm load-introduction zone for the 24 h creep check.** Point loads on half holes create local peaks that thickening the part does not change (ring latch: 6.1 → 3.7 MPa outside the zone). Every part loaded while cocked (hub, ring, latch, plates, pulley bracket, spring yoke) is checked for creep at full cocked load for 24 h. The stop bracket is checked at the rest preload. Creep allowable = 0.25 × UTS. (`sim/fea.py`)
- **D18 — The arm hub is split into three parts (hub_drum, arm, hub_catch) joined by 4 × 20 dowels and M3 screws into inserts.** As one part it could not be printed flat with its layers along the arm.
- **D19 — M3 inserts are sized to the brief's OD 4.0–4.2 (hole 4.0 mm).** Most "M3 × 5.7" inserts on sale are OD 4.6. If yours are, set `M3_INSERT_HOLE = 4.4` in `cad/params.py` and rebuild.

## Process

- **D20 — Firmware is verified by host-compiled unit tests (81 tests, plant model with fault injection).** PlatformIO could not run here: its registry and GitHub are blocked by the session's network policy. Building it yourself is step 1 of ASSEMBLY_GUIDE §8.
