# Known limitations

These are honest gaps between this kit and the brief, ordered by how much they matter.

## Targets that are not met

1. **Catch speed ≤ 4 m/s is physically impossible at 4 m.**
   - **The physics.** With 0.48 m between launch and catch height, the minimum-energy arc gives 4 m/s only out to 2.06 m. At 4 m the floor is 5.82 m/s, even before drag. The design flies that minimum-catch-speed arc (D2); the Monte Carlo study gives about 5.8 m/s at 4 m.
   - **Your options.** Catch with two hands and a soft glove. Or throw at 2 m, if catch speed matters more than range.
2. **Press → launch at 5 m is 2.7–2.9 s, against the 2.5 s target.**
   - **The cause.** Cocking 90° against the springs takes 1.82 s at the 5 m preload with the 37GB555 motor at 30:1. The 1.5 s warning runs in parallel with cocking, so the sequence is button 0.26 s + cock 1.82 s + feed 0.6 s (the 0.4 s escapement settle overlaps it) + settle and trip 0.13 s.
   - **At 4 m** it passes: 2.42 s in the calc, 2.33 s in the firmware plant model (`firmware/launcher/test`, cock time set to the calc's 1.38 s).
   - **Possible fix.** A faster motor (for example 12 V 200 rpm with the same gearbox frame) would meet it, but the stall torque then sits at about 80 % of the 5 m load. That margin was not accepted.
3. **BOM is about €143 for hardware and electronics (+€56 filament), against the €80 target.**
   - **The fixed costs.** Four items alone cost €65: a genuine CE power supply (€25), springs with a datasheet (€17), an encoder gearmotor (€14) and a hydraulic absorber (€8.5).
   - **What could be cut.** About €15 with AliExpress no-name springs (measure them as in CALIBRATION §1). Shared pack sizes with other projects would also help.
   - **What should not be cut.** Do not save on the power supply: the brief requires CE, and unbranded "CE" bricks are not reliably compliant.

## Not verified (simulation is not reality)

4. **No ESP32 build was compiled.** The PlatformIO registry and GitHub were blocked by the build environment's network policy. All 82 firmware tests pass as host C++ (`firmware/tools/host_tests.sh`), but `pio run -e esp32c3` has never run. Expect possible API drift in the ESP-IDF / Arduino core (ESP-NOW callback signatures changed in core 3.x).
5. **Prices and links are not live-checked.** Most AliExpress prices came from search snippets and USD mirrors at 1 USD = 0.90 EUR. Three lines (motor, pinion, cord) are estimates (`BOM.md`, "unverified").
6. **PETG properties are book values:** E_xy 1.8 GPa, UTS_xy 34 MPa / UTS_z 19 MPa, fatigue 0.6 × UTS at 10³ cycles, creep allowable 0.25 × UTS at 24 h. Your printer and filament will differ. The 2.5 safety factor is the margin for that, not a guarantee.
7. **The FEA has limits:**
   - Linear elastic; infill is smeared over the volume rather than modelled; orthotropic constants apply to whole parts.
   - Creep is assessed outside a 3 mm load-introduction zone (D17).
   - Local bearing creep at the latch nose dowel and the pulley axle is not modelled. Expect 0.1–0.3 mm of set in the first 50 throws; CALIBRATION §7 covers it.
8. **The feed simulation has limits:**
   - Cans are rigid cylinders with friction sampled at μ 0.10–0.45.
   - Real cans have rims, dents, condensation and labels.
   - The 330 ml neck taper is not modelled; the fingers are placed on the straight body.
9. **The launch simulation has limits:**
   - The cup–can contact is a stiff penalty model, and the peak acceleration is 2 ms-filtered.
   - The arm is rigid. FEA gives 2.4 mm tip deflection at the absorber stop, which slightly affects the release.
   - Aero: drag Cd 0.6–0.9 and Magnus CL −0.1–0.2 from cylinder literature. They are not measured on a tumbling can.

## Design compromises

10. **500 ml cans:**
    - Range is capped at about 3.3 m by the 85 % spring-load limit.
    - The magazine holds the same count.
    - The cup is sized for the 66.2 mm diameter, so it works, but the longer can sticks out 26 mm each side of the cup.
11. **The encoder has one channel**, because no GPIO was free. Direction is inferred from the drive command, and the hold loop needs at least 70 % PWM to win against the springs (`firmware/README.md`).
12. **The 5 A supply runs at its limit:**
    - 4.9 A peak during a 5 m cock, while the escapement servo pre-stages.
    - A motor stall briefly draws about 5.8 A. The supply's overload protection may then hiccup and reset the ESP32, which is safe because the latch is self-locking.
13. **Print time is 91 h and filament is 3.4 kg**, mostly in the bases and side plates. These are deliberately stiff, because frame deflection costs preload (0.46 mm in FEA). A lighter frame was not explored.
14. **Heat-set inserts:** the brief's OD 4.0–4.2 inserts are rare. Most "M3 × 5.7" inserts are OD 4.6, so change one parameter and rebuild (D19).
15. **The firmware review found more power-on and flashing quirks** (`electronics/PINMAP.md`):
    - the beeper is on during download mode;
    - the motor driver inputs float during reset, so 10 k pull-downs are added in the wiring;
    - both servos move at power-on.
16. **5 m runs the springs past the 85 % design margin.**
    - **Hand calc.** 61 mm of preload loads the springs to 86.5 % of the Z-141HI's rated Fn when cocked; the margin was 85 %. The heavier cup the review required (FEA) added the last 1.5 %.
    - **Simulation.** Roll-out lowers the real launch angle, so 5 m needs about 70 mm, which is the adjuster's end. That loads the springs to about 155 N, 93 % of Fn: still under the rating, but with little reserve.
    - **Printed parts.** Their 5 m loads rise up to 9 % above what the FEA used. The lowest 5 m safety factor in REPORT drops from about 2.75 to 2.5.
    - **What to do.** Treat 4.5 m as the everyday maximum. Use 5 m only with springs measured as in CALIBRATION §1. A fourth spring would fix this, but there is no room for it on the drum.
17. **500 ml cans need two printed parts reprinted, not one:** `mag_bridge_top` and `mag_bridge_back`. They are the same design (one cross-member printed twice), and `tests/test_can_size.py` proves nothing else changes. Their 3.3 m range cap is the hand calc at 138°; check yours with CALIBRATION §4.
18. **The absorber has a speed limit.** The AC1416-1 is rated 2.6 m/s, and normal shots hit it at 2.0–2.5 m/s. A dry fire (no can) reaches about 5 m/s at the absorber, twice its rating. The firmware prevents dry fires through the can-in-cup interlock, so one needs a sensor fault. After any dry fire, check the absorber for oil and replace it if it leaks (€8.5). The calc's dry-fire SF 1.9 assumes the absorber still works at that speed, which is not verified.
19. **The pairing key travels in clear text.** The button sends its new key in the PAIR_REQ packet, so anyone listening on ESP-NOW during the 30 s pairing window could copy it. Pair at home, away from strangers' radios. After pairing, every packet is authenticated.
20. **Limit-switch and sensor positions are set on assembly**, not fixed in the CAD (ASSEMBLY_GUIDE §7b). Their adjustment slots are 18 mm long.
