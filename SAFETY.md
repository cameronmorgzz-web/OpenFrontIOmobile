# Safety

This machine stores up to **13 J in its springs** at the 5 m setting. That is roughly a 1.3 kg weight dropped from 1 m, released in 0.1 s through an arm moving at 28 rad/s.

It throws a 0.36 kg can at 6–7 m/s. A full can hitting a face can break teeth or a nose. Treat the launcher like a nail gun: it is safe when you follow the rules, and dangerous when you don't.

## Hard rules

1. **Mains.** Use only the CE-marked Mean Well GST60A12 brick, or another genuine CE brick rated 12 V ≥ 5 A. Never open the brick, never cut its cable, and never wire anything that carries 230 V. Everything inside the launcher runs at 12 V or below.
2. **Safety pin in whenever you work on the machine.** The M6 pin passes through the right side plate and the ring at park; when the arm is cocked it also passes through the latch tail. With the pin in, the ring cannot rotate (and, when cocked, the latch cannot open), even if the electronics misbehave. Two micro switches sense it: one tells the firmware, the other cuts the latch servo's supply. The firmware refuses to cock or fire while it senses the pin.
3. **Firing zone.**
   - Keep a clear 5 m × 2 m lane in front of the launcher.
   - Keep the catcher at least 3 m away.
   - Nobody stands beside the arm: it sweeps 90 deg up to about 0.5 m above the table.
   - Never point the launcher at a window, a TV or a person who is not ready to catch.
4. **The warning cannot be skipped, and it starts at the same moment the arm starts cocking.** FIRE happens no sooner than 1.5 s after the warning begins (`kWarnMinBeforeFireMs`), and no setting removes it. The arm itself starts moving with the first beep: cocking is slow (90° in about 1.35 s), but there is no silent pre-warning period, so keep hands out of the arm's path whenever the machine is powered and armed for a press.
5. **No fingers in the frame while it is powered.** The ring gear, pinion and latch are behind the gear guard. The arm and cup sweep an open volume. Before reaching in: unplug the 12 V barrel jack, insert the safety pin, and check the arm is at rest on the absorber.
6. **Children and pets:** keep them out of the firing lane and away from the button. The button is not child-proof.
7. **Cans:**
   - Only sealed, undamaged 330 ml or 500 ml aluminium cans.
   - No glass bottles.
   - No dented cans: a dented can can burst under the 30 g launch load.
   - No cans colder than 0 °C: frozen contents expand and the can can split.

## Releasing stored energy safely

| Situation | What to do |
|---|---|
| Arm cocked, sequence aborted (button not ready, fault) | The firmware **decocks automatically**: the motor runs in reverse at 35 % PWM until the home switches close. The can stays in the cup. |
| FAULT with the arm cocked | Clear the firing lane. Hold the TEST button for 2 s: the firmware clears the fault and runs DECOCK. |
| Power cut while cocked | The latch is self-locking, so the arm stays latched to the ring and **cannot throw**. But the gearmotor is back-drivable: with no power, the springs slowly turn the ring, pinion and motor backwards and the arm unwinds to rest on its own, typically in a few seconds. Stay clear of the arm and gears until it has stopped on the absorber. Then restore power; the firmware boots into IDLE once the home switches read closed. |
| DECOCK fails (motor or encoder fault) and the arm stays cocked | 1. Unplug the 12 V supply. 2. Short the two motor wires together at the driver terminals with a jumper wire: this turns the motor into a brake. 3. Clear the lane and stand beside the machine, not in front. 4. Tie a 1 m cord to the safety-pin handle and pull the pin out from there. The ring, still latched to the arm, unwinds slowly against the shorted motor. **If the drivetrain is broken** (stripped pinion, loose grub screw), pulling the pin lets the arm swing freely into the absorber: a dry fire, which the machine is designed to survive. That is why you pull from a metre away. Backing off the preload wing nuts alone does **not** make the machine safe: about 6 J of the cocking stroke remains in the springs. |
| Dry fire (no can) | Designed for it. The absorber takes 15.1 J at 5 m and the arm keeps SF 1.9. Inspect the absorber for oil leaks after any dry fire. |

## Pinch points while cocking

- **Ring gear and pinion:** the gear guard covers the ring teeth from 25° round to 312° and has a hood over the pinion mesh. The motor cover encloses the motor. A 70° arc of ring teeth at the front-bottom stays open, because the latch swings through it; it sits inside the frame behind the arm. Never run the machine without the guards, and never reach into the frame while it is powered.
- **Cup and arm path:** cocking is slow (about 1.3 s for 90 deg), but the motor is strong enough to hurt. The firmware stops on stall within 350 ms.
- **Escapement fingers:** can trap a fingertip between the rocker and a can. Load the magazine from the top only, never through the chute.

## Firmware safety features (tested in `firmware/launcher/test`)

- **Interlocks:**
  - Safety-pin sensor: blocks COCK, FIRE and DECOCK start.
  - Can-in-cup sensor: no FIRE on an empty cup.
  - Magazine-empty sensor: a press is refused with 3 beeps.
- **Fault detection:**
  - Real limit switches (arm home, arm cocked, ring home), not timing.
  - Stall detection from the encoder, plus a cock timeout.
  - Hold-lost detection while ARMED.
  - A sensor-conflict fault when both arm switches read closed.
- **Button link:** every press is authenticated (HMAC-SHA256 over a sequence number). Replayed or forged packets never fire.
- **FAULT behaviour:** the motor coasts or brakes, never drives, and the beacon shows the fault code.

## Legal (Italy)

This is a home-built toy machine, not a CE-marked product.
- **Private use:** using it on your own premises is your own responsibility.
- **Selling or giving the machine away:** this would make you its "fabbricante" under the Machinery Directive 2006/42/CE and the Toy Safety Directive (D.Lgs. 54/2011), with the CE marking duties that follow.
- **Selling the files:** this is different, but still check product-liability exposure (Codice del Consumo, artt. 114 ff.).
- **Public venues:** a bar using it would need its own risk assessment (D.Lgs. 81/2008).
