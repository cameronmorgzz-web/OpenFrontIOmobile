# Assembly guide

**Time:** about 6 hours, plus the printing. **Tools:**
- hex keys 2.5 / 3 mm and 10 mm spanners
- soldering iron (plus a flat heat-set tip)
- small vise
- multimeter
- side cutters
- CA glue
- 4 mm drill bit (by hand)
- luggage scale

Read SAFETY.md first. **Keep the safety pin in from step 5 onwards.**

Part names below are the STL/3MF object names. The renders show the finished assembly: `cad/renders/launcher_exploded.png` for part positions, and `launcher_side.png` / `launcher_side_cocked.png` for the two end states.

## 1. Inserts and prep (all printed parts)

1. Heat-set the 54 M3 inserts at 220 °C:
   - `base_front` 16, `base_rear` 10, `arm` 8, `stop_bracket` 4
   - `latch_servo_mount` 2, `esc_servo_mount` 2, `mag_bridge_*` 2 each, `btn_shell` 3
   - `gear_guard` 3, and 2 in the outer face of `side_plate_right` (motor cover)
2. Apply PTFE tape to the `cup` floor and to both magazine rail ledges.
3. Glue `cup_pad` (TPU) to the cup back wall. Press the four TPU `foot` parts into the recesses under the bases.

## 2. Base and frame

1. Lay `base_front` and `base_rear` deck-up and butt them together.
2. Fit `side_cheek_left` and `side_cheek_right`. Their flanges bridge the joint: 2 × M3 × 10 per side into the deck inserts.
3. Fit `side_plate_left` and `side_plate_right`. Their flanges sit on the deck: M3 × 12 into the base inserts. The bosses face inwards.
4. Do not tighten fully yet.

## 3. Arm hub (on the bench)

1. Press the 8 × 30 hardened catch pin into `hub_catch` and slide the 608 catch roller onto it.
2. Stack the three parts `hub_drum` → `arm` → `hub_catch` with 6 × 4 × 20 dowels (3 per joint) and 6 × M3 × 16 screws (3 per joint). The dowels take the torque and the screws only clamp.
3. Press one 608 bearing into each hub end bore. If it is loose, use a drop of CA glue on the outer race only.
4. Bolt the `cup` onto the arm tongue: 2 × M3 × 30 through the cup's 2 counterbored holes into the arm's inserts.

## 4. Ring, latch and shaft

1. Press the nose dowel into `ring_latch`.
2. Fit the latch on its 4 mm pivot dowel in `ring_gear`. It must swing freely: check with the ring held vertical.
3. Press the 608 bearings into the ring bore.
4. Cut the 300 mm 8 mm shaft into 214 mm (main pivot) and 37 mm (pulley axle), and deburr both. Slide the long piece through: left cap → `shaft_spacer_left` → hub stack → `shaft_spacer_mid` → ring → right plate → right cap. The ring's latch must catch the roller when you rotate the ring towards the arm.
5. Tighten the side-plate screws now. The shaft must turn with no binding.

## 5. Cocking drive, absorber, stop

1. Fit the motor to the outside of the right plate (2 × M3 on its 31 mm hole circle). Mount the steel pinion on the 6 mm D-shaft with its grub screw, flush with the ring face.
2. Fit `gear_guard` inside the frame over the ring and pinion: 3 × M3 × 12 from outside the right plate into its boss inserts. Then screw `motor_cover` over the motor: 2 × M3 × 12 into the inserts in the plate's outer face.
3. Screw the AC1416 absorber into `stop_bracket` (M14 × 1.5) and lock it with its nut. Bolt the bracket to the left plate at the **142° detent**.
4. Mount the latch servo (MG996R) in `latch_servo_mount` and bolt the mount to the right plate. Fit the horn so that at 1100 µs (HOLD) the finger clears the latch tail by 2 mm.
5. **Insert the safety pin** through the plate, ring and latch tail holes.

## 6. Springs and cord

1. Drop the `pulley_bracket` into the channel with a 608 bearing on the 8 mm axle. Screw it down with 4 × M3 into the base inserts.
2. Tie the 2 mm Dyneema cord to the drum: pass it through the drum hole and tie a stopper knot; the knot sits inside the drum. Take it over the pulley, then rearwards to `spring_yoke_front`.
3. Hook the three Z-141HI springs between `spring_yoke_front` and `spring_yoke_rear`. Slide the M6 rods through the rear yoke and the anchor wall. Fit the wing nuts and set **55 mm exposed thread** (CALIBRATION §2).
4. Cord length: with the arm resting on the absorber, the springs carry their preload (the springs just stretched, cord taut). Retie until it is right. A loose cord costs range; an over-tight cord lifts the arm off the absorber.

## 7. Magazine and escapement

1. Assemble the left wall: `mag_wall_left_lower` + `mag_chute_left` + `mag_wall_left_upper`, joined by 4 mm dowels and M3. Repeat on the right.
2. Press the 4 × 30 rocker dowel into the left wall. Slide `escapement_rocker` onto it, fingers up, crank arm down, and secure the free end with the 4 mm starlock washer.
3. Screw the escapement MG996R into `esc_servo_mount` through its tabs. Bolt the mount to the inner face of the left lower wall: 2 × M3 from outside.
4. Make the 2 mm pushrod:
   - Hook a Z-bend into the horn hole at 12 mm radius.
   - Set the horn at hold, 8° past the rod line (towards the rod).
   - Mark the rocker crank hole with f2's top 1 mm below the rail, then bend the second Z.
   - Rod centre distance: 40 mm.
5. Join the two walls with `mag_bridge_top` and `mag_bridge_back` (M3 through the walls into the bridge inserts). Stand the magazine on `base_rear`: 2 × M3 per side through the wall feet.
6. Fit the two TCRT5000 sensors:
   - can-in-cup: looks at the cup floor;
   - magazine-empty: through the 11 mm hole in the left wall, looking at can1's end.

## 7b. Limit switches and sensors

Their positions are not fixed in the CAD. Each sits on a printed `switch_bracket` / `sensor_bracket` with an 18 mm slot, screwed with an M3 × 12 self-tapper into a 2.8 mm pilot hole you drill on assembly. Set each one with the safety pin in and the motor unpowered, turning the ring by hand through the pinion.

| Switch | Mount on | Actuated by | Set it to close |
|---|---|---|---|
| SW_ARM_HOME | left side plate, inner face, below the hub | `hub_drum` rim when the arm rests on the absorber | 1–2 mm before the arm bottoms |
| SW_ARM_COCKED | right side plate, inner face, behind the hub | `hub_catch` ear at the cocked angle (228°) | 1–2 mm before the ring reaches its end stop |
| SW_RING_HOME | right side plate, inner face | the latch boss on `ring_gear` at park | when the latch roller seat is at park |
| SW_SAFETY_PIN A + B | right side plate, outer face, both behind the pin hole | the pin's tip | both switch when the pin is fully home |
| can-in-cup TCRT5000 | chute end on `mag_chute_left`, looking at the cup floor at the cocked angle | the can's side | turn the module pot until its LED lights with a can in the cup and stays off when empty |

Check every switch with the console `status` command before the first powered cycle (§10).

## 8. Electronics

Follow `electronics/WIRING.md` step by step, including its pre-power checklist (buck set to 5.0 V **before** connecting the ESP32). The pin map is in `electronics/PINMAP.md` and the wiring diagram in `electronics/wiring_launcher.svg`.

**Firmware.** Install PlatformIO on your PC (`pip install platformio`), then:

```bash
cd firmware/launcher && pio test -e native && pio run -e esp32c3 -t upload   # 12 V unplugged while flashing
cd firmware/button   && pio test -e native && pio run -e esp32c3 -t upload   # LiPo unplugged while flashing
```

These ESP32 builds have **not** been compiled by the author's pipeline: the PlatformIO registry was blocked there. The 82 host tests did pass on the same sources. If a build fails, it is most likely a library or API version issue; the build log will name the line.

**Pairing** (always open the launcher's pairing window first: a paired button sends FIRE at the start of every press, and the launcher ignores it only while it is in PAIRING):
1. Launcher idle: hold TEST for 5 s (chirp).
2. Beer Button: hold for 5 s.
3. You hear a triple beep, and the button gives two buzzes.

## 9. Button

1. Desolder the SuperMini's red power LED.
2. Wire it as in `electronics/wiring_button.svg`: battery → TP4056 → OUT+ to the SuperMini **5V** pin (its LDO makes 3.3 V; never put the 4.2 V cell on the 3V3 pin, which exceeds the chip's 3.6 V limit), switch, divider, haptic.
3. Assembly order: `btn_tray` into `btn_shell` → `btn_switch_plate` (3 × M3 into the shell inserts) → 4 cap springs → snap on `btn_cap` → `btn_foot_ring` (TPU).
4. Check the press force with the luggage scale: 3–5 N.

## 10. First power-up checklist

- [ ] Safety pin in. Lane clear. No can in the magazine.
- [ ] Plug in the 12 V supply. The beacon blinks the boot pattern and the console shows `IDLE`.
- [ ] Console `status`: the arm-home and ring-home switches read closed, the pin reads IN, the magazine reads EMPTY.
- [ ] Press the button: 2 refusal beeps (pin in). Good.
- [ ] Remove the pin. Press TEST briefly with the **magazine empty**: 3 beeps (magazine empty). Good.
- [ ] Load one water-filled can. Clear the lane. Press TEST. You get the warning, the arm cocks, the can feeds, then FIRE.
- [ ] Continue with CALIBRATION.md.
