# Beer Button + Launcher firmware

Two ESP32-C3 SuperMini boards talking ESP-NOW on WiFi channel 1 (no router, no scan).

```
firmware/
  common/     PlatformIO library "beer-common": portable C++17, no Arduino includes
    src/config.h          every timing constant / tunable (marked [MECH] where the mechanism decides)
    src/sha256.*, hmac.*  portable SHA-256 + HMAC-SHA256, constant-time compare
    src/protocol.*        37-byte packet pack/unpack, truncated 8-byte HMAC tag
    src/replay_guard.*    strictly increasing per-button sequence check
    src/launcher_sm.*     launcher state machine (Inputs -> tick(now_ms) -> Outputs), radio + replay rules
    src/button_logic.*    battery hysteresis, press timing, retry policy, pairing schedule, ACK checks
  button/     Beer Button: src/main.cpp (hardware glue only), test/ (Unity, native)
  launcher/   Launcher: src/main.cpp, src/hal_esp32.*, test/ (Unity, native, incl. plant simulation)
  run_tests.sh
```

Both projects pull `common/` in with `lib_deps = symlink://../common`. All logic is in `common/`, and the
native env runs with `test_build_src = no`, so the host tests exercise exactly the code that ships.

## Build, flash, test

```bash
. .venv/bin/activate                 # PlatformIO 6.2
cd firmware/button   && pio run -e esp32c3 -t upload && pio device monitor
cd firmware/launcher && pio run -e esp32c3 -t upload && pio device monitor   # 115200, USB CDC
cd firmware/launcher && pio test -e native     # 64 tests: crypto, protocol, replay, 35 SM scenarios
cd firmware/button   && pio test -e native     # 16 tests: button logic, button<->launcher radio checks
firmware/run_tests.sh                  # both esp32c3 builds + both native suites, non-zero on failure
firmware/run_tests.sh --native         # host tests only
```

Build flags (esp32c3): `-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1 -std=gnu++17` (replaces the
core's `gnu++11`). `-Wall -Wextra` apply to our sources only (`build_src_flags`, and the library's
`build.flags`), not to the framework. The sources compile against arduino-esp32 2.x (default with
`platform = espressif32`) and 3.x: the ESP-NOW receive callback and the LEDC API are switched on
`ESP_ARDUINO_VERSION_MAJOR`.

## Pin maps

### Beer Button

| GPIO | Function | Notes |
|---|---|---|
| 3 | Big switch to GND | external 1 MOhm pull-up to 3V3; deep-sleep wake on LOW (`esp_deep_sleep_enable_gpio_wakeup`) |
| 1 | Battery ADC | 1M/1M divider (x2); add 100 nF across the lower resistor (high-impedance source) |
| 4 | Haptic coin motor | NPN, active high; held LOW in deep sleep (`gpio_hold_en`); fit a 100k base pull-down anyway |
| 5 | Status LED | active high via 330 Ohm; held LOW in deep sleep |

### Launcher

| GPIO | Signal | Dir | Active | Notes |
|---|---|---|---|---|
| 0 | MOT RPWM | out | PWM 20 kHz | BTS7960 (IBT-2) RPWM: COCK / forward |
| 1 | MOT LPWM | out | PWM 20 kHz | BTS7960 LPWM: RETRACT / reverse. R_EN = L_EN = 3V3 |
| 2 | WARN | out | HIGH | MOSFET: 12 V buzzer + beacon. Strapping pin with a 10k pull-up, so it chirps at boot (expected) |
| 3 | ENC_A | in, pull-up | edges | motor Hall channel A, counted on both edges (CHANGE ISR) |
| 4 | SW_ARM_HOME | in, pull-up | LOW | arm on its forward stop |
| 5 | SW_ARM_COCKED | in, pull-up | LOW | arm/ring at the cocked angle (stays closed after FIRE until the ring leaves) |
| 6 | SW_RING_HOME | in, pull-up | LOW | cocking ring parked (its latch re-hooks the arm roller there) |
| 7 | SW_SAFETY_PIN | in, pull-up | LOW | pin INSERTED = safe: locks the ring; the hardware also cuts latch-servo power |
| 8 | SERVO_ESC | out | 50 Hz | escapement servo. Strapping pin; the SuperMini's on-board LED is on GPIO8 too |
| 9 | BTN_TEST | in, pull-up | LOW | BOOT button + external test button. Held during reset = download mode |
| 10 | SERVO_LATCH | out | 50 Hz | frame-mounted finger that trips the ring latch (HOLD / TRIP) |
| 20 | SNS_MAG_EMPTY | in, pull-up | HIGH = empty | IR reflective, LOW = can at magazine bottom |
| 21 | SNS_CAN_IN_CUP | in, pull-up | LOW | IR reflective looking into the cup at the cocked position. GPIO21 is U0TXD: the ROM bootloader drives it during reset, so put about 1 kOhm in series with the sensor output |

Motor drive (BTS7960): forward = RPWM PWM / LPWM 0, reverse = RPWM 0 / LPWM PWM, **Brake = both HIGH**
(both high-side switches on), "Coast" = both LOW. Because R_EN and L_EN are tied to 3V3, "both LOW" turns
both low-side switches on, which is also a brake. There is no true coast (see Open issues).
LEDC: channels 0/1 share timer 0 (20 kHz, 10 bit), channels 2/3 share timer 1 (50 Hz, 14 bit).

## Protocol

37 bytes, little-endian, packed:
`'BEER' | ver=1 | type | seq u32 | batt_mV u16 | flags | payload[16] | tag[8]`, where
`tag = HMAC-SHA256(key, bytes 0..28)[0..7]`, compared in constant time.
Types: 1 FIRE, 2 PAIR_REQ (payload = new 16-byte key, signed with that key), 3 PAIR_ACK (signed with the
new key, seq echoes the request), 4 ACK (signed with the paired key: payload[0] state, [1..4] acked seq,
[5] AckResult, [6] fault), 5 STATUS (request/response, read-only).

- **Replay:** FIRE must verify the HMAC, come from the paired MAC and have `seq > last_seq`. `seq == last_seq` is a
  retry: the launcher sends the ACK again and does not trigger. Older packets get no reply. `last_seq` goes to NVS
  once per accepted packet. Forged packets do not use up sequence numbers.
- **Button seq:** RTC copy across deep sleep. It is written to NVS on every press *before* transmit. After a cold
  boot the button uses NVS + 16.
- **Pairing security:** PAIR_REQ only proves the sender holds the key it hands over. Pairing is only as secure as
  the 30 s window opened by a 5 s press on the launcher, plus physical proximity. Anyone in radio range during that
  window can pair instead. Re-pairing resets `last_seq` to 0; packets signed with the old key no longer verify.

## Pairing procedure

1. Launcher in IDLE: hold BTN_TEST for at least 5 s (or type `pair` on the console). The beacon chirps once a
   second for up to 30 s.
2. Beer Button: hold the big button for at least 5 s. The LED blinks slowly. The button generates a new key with
   `esp_random`, keeps it as "pending" in NVS, and broadcasts PAIR_REQ every 500 ms for up to 30 s.
3. The launcher stores the button MAC and key in NVS, replies with PAIR_ACK and gives a triple beep. The button
   stores the launcher MAC and commits the key: two haptic pulses. On failure the LED blinks 3 times and the old
   pairing is kept.

Always open the launcher window first. A paired button sends a FIRE at the *start* of every press, before it can
tell the press will be long. While the launcher is in PAIRING, that FIRE is ACKed as "busy" and ignored.
If the PAIR_ACK is lost, the button's repeated PAIR_REQ (same key) is ACKed again even after the window closes.

## Launcher state machine

Mechanism (clay-pigeon-trap style): the motor-driven cocking ring carries a two-stage latch that hooks the
arm's catch roller. There is no frame sear and no retract before FIRE.

```
            trigger (radio FIRE / short BTN_TEST / "fire"); needs arm home, ring home, pin out, magazine
  IDLE -------------------------------------------------------------------------> WARN (50 ms)
   ^  \--refused (pin in / not home / magazine empty): beep + ACK, stay           | beacon 4 Hz ON and
   |                                                                              | motor FORWARD 100 % start together
   |   COCK: ring drags the latched arm until SW_ARM_COCKED (latch servo stays HOLD)
   |                                   | capture encoder count -> HOLD (P-control, both directions)
   |   FEED (holding): escapement RELEASE 250 ms -> CLOSED -> SNS_CAN_IN_CUP LOW stable 100 ms (<= 800 ms)
   |                                   v
   |   ARMED (holding): arm cocked & hold error <= 10 edges & can in cup & pin out & beacon >= 1500 ms (<= 1500 ms)
   |                                   v
   |   FIRE: latch servo TRIP + motor COAST at the same tick; SW_ARM_HOME within 400 ms;
   |         servo HOLD 300 ms after release
   |                                   v
   +-- RESET: motor REVERSE 100 % (unloaded) until SW_RING_HOME (<= 1500 ms), latch re-hooks the roller;
             beacon off >= 500 ms after HOLD and after the ring is parked; verify arm home, ring home

  COCK/FEED/ARMED/RESET faults -> FAULT (latch HOLD, escapement CLOSED, beacon 1 Hz, motor brake;
                                  kept braked while the arm is loaded)
  FEED / MAG_EMPTY / ARMED_TIMEOUT -> DECOCK automatically (needs pin out, else FAULT "remove safety pin")
  FAULT --(BTN_TEST >= 2 s | "clear")--> DECOCK if arm cocked / arm not home / ring not home, else IDLE
  IDLE  --(BTN_TEST >= 5 s | "pair")--> PAIRING --(PAIR_REQ | 30 s | short press)--> IDLE
  boot: SW_ARM_COCKED closed -> FAULT COCKED_AT_BOOT (nothing moves); arm/ring not home -> FAULT NOT_HOME
```

**HOLD** (FEED + ARMED): the encoder count at the SW_ARM_COCKED edge is the target. Inside +-3 edges the
motor brakes (both HIGH). Outside, it drives towards the target with `PWM = max(70 %, 10 %/edge)`, capped at
100 %. The 70 % minimum is above the static holding duty, which is about 1 - t_return/t_cock: 48 % at 4 m and
59 % at 5 m. That way a correction always wins against the load (see "encoder" below). HOLD_LOST is raised if the
error stays above 40 edges for 100 ms, or SW_ARM_COCKED opens for 30 ms. In simulation the ring stayed within
3 edges, and the estimate within 5 edges of the real position.

**DECOCK** (controlled release, never fires): motor REVERSE at 35 % with the arm still latched to the ring. No
servo action. It runs until SW_ARM_HOME and SW_RING_HOME are both closed; after 3000 ms, or on a stall, it raises
FAULT_DECOCK (manual intervention, beacon 1 Hz). It requires the safety pin OUT, because the pin locks the ring;
with the pin in the motor never moves. A can seen in the cup at the cocked angle is remembered. After a DECOCK the
next cycle skips the escapement, so a second can is never dropped onto it.

**Encoder:** only channel A is wired, counted on both edges. While driving, edges count in the commanded
direction. While not driving, they count as REVERSE, because the arm load is the only force on the ring and it
backdrives towards park.

Global rules, checked before any state logic every tick:
- Safety pin inserted in WARN, COCK, FEED, ARMED or DECOCK gives FAULT SAFETY_PIN_IN_DURING_SEQUENCE; the motor is
  braked in the same tick.
- SW_ARM_HOME and SW_ARM_COCKED both closed for 30 ms gives SENSOR_CONFLICT. This is not checked in FIRE/RESET,
  where the arm is home while the ring still sits at the cocked angle.
- Stall (COCK, RESET return, DECOCK): motor driven and fewer than `kStallMinEdges` encoder edges in any 150 ms
  window, after the first 200 ms of a motion. The threshold comes from `kEncPprMotor` and
  `kStallMinMotorRpm` = 500: 27 edges at 11 PPR, 40 at 16 PPR. This and the timeouts are the only over-current
  protection, plus the 5 A fuse.

Fault codes: STALL, COCK_TIMEOUT (2200 ms), RING_RETURN_TIMEOUT (1500 ms; was RETRACT_TIMEOUT), ARM_NOT_MOVING
(600 ms), FEED, NO_RELEASE (400 ms, no auto retry), SAFETY_PIN_IN_DURING_SEQUENCE, COCKED_AT_BOOT, DECOCK,
SENSOR_CONFLICT, MAG_EMPTY (mid-sequence), ARMED_TIMEOUT, NOT_HOME (boot / after RESET), HOLD_LOST.
A test asserts that every code is exercised.

**Power loss:** with power off, the latched arm can only unwind by backdriving the gearbox and motor. It is heavily
geared, so this is slow and low-energy. On the next boot, SW_ARM_COCKED closed gives FAULT COCKED_AT_BOOT. The user
removes the pin and holds TEST for 2 s to DECOCK. If the arm stopped part way, NOT_HOME is handled the same way.

Firmware structure: a 1 kHz FreeRTOS task ticks the SM and applies outputs. `loop()` does ESP-NOW RX/TX, NVS
writes (outside the lock, so a slow flash write never delays a control tick) and the console.
Console (115200): `status`, `fire`, `decock`, `pair`, `clear`; state changes are logged.

### Simulated timing (host tests)

Plant: cock 1.29 s (4 m) / 1.63 s (5 m), feed 0.45 s, trip 60 ms + fire 80 ms, ring return 0.67 s, plus
250 ms button wake and radio before the packet arrives.

| | 4 m | 5 m | limit |
|---|---|---|---|
| packet -> FIRE | 1743 ms | 2083 ms | <= 2250 (4 m) / <= 2350 (5 m) |
| press -> FIRE | 1993 ms | 2333 ms | |
| beacon before FIRE | 1743 ms | 2083 ms | >= 1500 |
| press -> back in IDLE | 3085 ms | 3422 ms | <= 8000 |

## Beer Button power budget (assumptions to verify with a current probe)

Awake time per press (nominal, ACK on first try):

| Step | Time |
|---|---|
| ROM + bootloader + app start | ~30-40 ms |
| NVS open/read + ADC (8 samples) | ~5 ms |
| WiFi STA + ESP-NOW init (no scan) | ~40-60 ms |
| NVS seq write | ~3-10 ms |
| TX + ACK | ~5-10 ms |
| Haptic pulse | 80 ms |
| Release debounce | >= 30 ms |
| **Total** | **~190-235 ms** (target < 250 ms) |

Worst case without an ACK: +4 x 120 ms of radio and 3 blinks (~450 ms). Low-battery warning: +~650 ms.
A press spends roughly 200 ms at ~80 mA on average, with WiFi TX peaks around 300 mA, so about 4-5 uAh per press.

Sleep current: ESP32-C3 deep sleep ~5 uA, plus the 1M/1M divider ~2 uA, plus the SuperMini LDO quiescent current
(tens of uA, which dominates). **Remove the SuperMini's red power LED** (~1-3 mA).
Low battery: below 3.45 V the flag is set; it clears at >= 3.60 V. The flag is kept in RTC memory.
A switch stuck closed for 60 s puts the button to sleep with a 60 s timer wake instead of the LOW-level wake, so
it does not wake-loop.

## Open issues / to confirm on the bench

1. **Not built with PlatformIO here.** The sandbox could not reach the PlatformIO registry, so the espressif32 and
   native platforms, toolchains and Unity were missing. The code was checked with host g++ (`-Wall -Wextra`, and
   `-Wconversion -Wshadow` for common/) using a Unity-compatible shim, and the Arduino sources were syntax-checked
   against stub headers for both 2.x and 3.x APIs. Run `firmware/run_tests.sh` once on a machine with the platforms.
2. **BTS7960 has no coast with EN tied high.** "Coast" (both LOW) turns both low sides on, which is also a brake.
   It only matters at FIRE, where the spec asks for coast at TRIP; the unloaded ring sees a low-side brake instead.
   A true coast needs R_EN/L_EN on a GPIO, and none is free.
3. **Holding current:** HOLD drives at least 70 % in short bursts, for up to about 1 s (feed) plus up to 1.5 s
   (ARMED) per shot. Check motor and driver temperature, and that 70 % beats the load at the 5 m setting.
   `kHoldMinPwmPct` has to stay above the static holding duty.
4. **Single-channel encoder:** if the motor ever loses to the load while driven forward, the motion is counted the
   wrong way. HOLD_LOST then relies on SW_ARM_COCKED opening, so its switch hysteresis must be about 20 edges or
   more. Wiring encoder channel B would remove this weakness, but no GPIO is free.
5. Encoder PPR (11 or 16): the stall threshold derives from it; both values pass the suite.
6. Servo pulse widths (`kLatch*Us`, `kEsc*Us`) are placeholders. TRIP release time is assumed to be 60 ms.
7. In FAULT the motor stays braked while the arm is loaded, so the arm unwinds slowly through the backdrivable
   gearbox (dynamic braking only). The safety pin locks the ring.
8. Single paired button. STATUS (type 5) is answered by the launcher but the button does not use it. The button
   has one LED, so the "red" low-battery pattern is 5 fast blinks.
