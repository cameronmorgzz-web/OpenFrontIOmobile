# Pin maps

These tables follow the firmware. The source files are:

- Launcher: `firmware/launcher/src/hal_esp32.cpp` lines 18-30 (`kPin*` constants), set up in `hal::begin()` (lines 79-97).
- Button: `firmware/button/src/main.cpp` lines 34-37, set up in `setup()` (lines 297-304).

Net names on the launcher match the "Signal" column of the `firmware/README.md` pin table. `electronics/test_electronics.py`
checks both tables against the source. If this file and the firmware ever disagree, the firmware is right and this file
has to be fixed.

Both boards are ESP32-C3 SuperMinis. A SuperMini breaks out GPIO0-10, GPIO20 and GPIO21. The strapping pins are GPIO2, GPIO8
and GPIO9; the chip reads them at reset, and GPIO9 LOW at reset enters download mode. GPIO20/21 are UART0 RX/TX (U0RXD/U0TXD),
which the ROM bootloader uses. Both firmwares log over USB CDC (`ARDUINO_USB_CDC_ON_BOOT=1`), so the application never
uses UART0.

## Launcher

| GPIO | Firmware const | Net | Dir | Pull | Connected part | Notes |
|---|---|---|---|---|---|---|
| 0 | `kPinRpwm` | MOT_RPWM | out (PWM 20 kHz) | ext. 10k pull-down (R2) | IBT-2 RPWM | forward / COCK. The pull-down holds the bridge off while the pin floats (reset, flashing), because R_EN/L_EN are tied high |
| 1 | `kPinLpwm` | MOT_LPWM | out (PWM 20 kHz) | ext. 10k pull-down (R3) | IBT-2 LPWM | reverse / ring return / DECOCK. Same pull-down reason as GPIO0 |
| 2 | `kPinWarn` | WARN | out, active HIGH | ext. 10k pull-up to 3V3 (R4) | Q2 AO3400 gate (via 100 Ω) → 12 V buzzer + beacon | **Strapping pin**: it must be HIGH at reset, so the pull-up is required. As a result the beeper is on from reset until `hal::begin()` drives the pin LOW (line 82), and stays on in download mode |
| 3 | `kPinEncA` | ENC_A | in, interrupt on CHANGE | internal pull-up | 37GB555 Hall encoder channel A | power the encoder from 3V3 so its output never exceeds 3.3 V. Channel B is not connected. No RC filter |
| 4 | `kPinArmHome` | SW_ARM_HOME | in, active LOW | internal pull-up + 100 nF to GND | microswitch NO, COM to GND | LOW = arm on its forward stop |
| 5 | `kPinArmCocked` | SW_ARM_COCKED | in, active LOW | internal pull-up + 100 nF | microswitch NO | LOW = arm/ring at the cocked angle |
| 6 | `kPinRingHome` | SW_RING_HOME | in, active LOW | internal pull-up + 100 nF | microswitch NO | LOW = cocking ring parked |
| 7 | `kPinSafetyPin` | SW_SAFETY_PIN | in, active LOW | internal pull-up + 100 nF | safety-pin switch, pole A (NO) | LOW = pin inserted (safe). Pole B (NC) of the same actuator breaks the latch servo's V+ |
| 8 | `kPinServoEsc` | SERVO_ESC | out (50 Hz servo PWM) | on-board LED + resistor to 3V3 acts as pull-up | MG996R escapement servo SIG via 330 Ω | **Strapping pin**: it only matters when GPIO9 is LOW (download mode), where it must be HIGH, and the on-board LED pulls it HIGH. A servo input is high impedance, so it cannot pull the pin LOW. The on-board LED flickers with the servo PWM; this is cosmetic |
| 9 | `kPinTestBtn` | BTN_TEST | in, active LOW | internal pull-up (plus the board's BOOT circuit) | panel push button in parallel with the on-board BOOT button | **Strapping pin**: holding it at power-up enters download mode, which is safe because nothing moves. **No debounce capacitor** (a slow rise at reset could select download mode); the firmware debounces for 20 ms |
| 10 | `kPinServoLatch` | SERVO_LATCH | out (50 Hz servo PWM) | none | MG996R latch servo SIG via 330 Ω | the 330 Ω limits the current fed back into the unpowered servo while the safety pin cuts its V+ |
| 20 | `kPinMagEmpty` | SNS_MAG_EMPTY | in, LOW = can present | internal pull-up + ext. 10k to 3V3 | TCRT5000 module DO via 1k + BAT54 (cathode toward the module) | HIGH = magazine empty. U0RXD is only an input for the ROM, so there is no contention |
| 21 | `kPinCanInCup` | SNS_CAN_IN_CUP | in, LOW = can in cup | internal pull-up + ext. 10k to 3V3 | TCRT5000 module DO via **1k** + BAT54 | U0TXD: the ROM and the 2nd-stage bootloader drive it during boot. The 1k limits contention while the sensor pulls LOW to under 3 mA |

Every launcher GPIO the SuperMini breaks out is in use. Encoder channel B, R_EN/L_EN and the R_IS/L_IS current-sense
outputs have no pin left.

TCRT5000 levels: the modules run from +5V_LOGIC. Their LM393 output is open collector with an on-board pull-up to 5 V,
which is **not** 3.3 V-tolerant if wired directly. The BAT54 is reverse-biased when DO is HIGH, so the GPIO only sees the
3.3 V pull-up. When DO is LOW (about 0.1-0.2 V) the GPIO reads about 0.5 V (diode drop plus a little across the 1k). That
is below the C3's V_IL max of 0.25 x VDD (about 0.8 V). A 1N5819 also works in place of the BAT54.

## Button

| GPIO | Firmware const | Net | Dir | Pull | Connected part | Notes |
|---|---|---|---|---|---|---|
| 1 | `kPinBatt` | BATT_SENSE | in, ADC1_CH1 | none (divider) | VBAT → 1M → node → 1M → GND, plus 100 nF from node to GND | reads VBAT/2, so 4.2 V gives 2.1 V, inside the 11 dB ADC range. The 100 nF gives the ADC a low-impedance source |
| 3 | `kPinSwitch` | BTN_SWITCH | in, active LOW, deep-sleep wake | ext. 1 MΩ pull-up to 3V3 (`pinMode INPUT`) | microswitch NO to GND; optional 10 nF | deep-sleep GPIO wake only works on GPIO0-5, and GPIO3 is one of them. Use at most 10 nF: with the 1 MΩ pull-up, 100 nF would take about 0.1 s to rise |
| 4 | `kPinHaptic` | HAPTIC | out, active HIGH | ext. 100k base pull-down | 1k → NPN base. 1027 coin motor between +3V3 and the collector, 1N5819 across the motor | held LOW in deep sleep by `gpio_hold_en` (main.cpp:281) |
| 5 | `kPinLed` | STATUS_LED | out, active HIGH | none | 330 Ω → LED → GND | held LOW in deep sleep (main.cpp:280) |

Unused on the button: GPIO0, 2, 6, 7, 8, 9, 10, 20, 21. Desolder the SuperMini's red power LED.

## Findings for the firmware author

I have not edited any firmware. These are wiring consequences and possible improvements.

1. **Escapement and latch servos can move at the same time.** `firmware/common/src/launcher_sm.cpp:590-592` sends the
   escapement to CLOSED 450 ms after RELEASE. If the can landed during RELEASE (the sim says within 0.23 s), `canStable()`
   (`launcher_sm.cpp:598`, 100 ms, `config.h:96`) is already true. FEED then ends on the next tick, and ARMED trips the
   latch (`launcher_sm.cpp:385-391`) as soon as the 1.5 s warning has run, which it normally has by then (cock 1.29-1.63 s
   + 0.45 s). The escapement is still travelling 133° (about 0.35-0.4 s for an MG996R) when the latch servo starts.
   Electrically this fits the budget, because both servos are lightly loaded (see WIRING.md). Mechanically, the shot
   happens while the escapement pushrod has not yet locked past dead centre. Consider a minimum dwell of about 400 ms
   after CLOSED before FIRE.
2. **Both servos start together at power-up.** `hal_esp32.cpp:88-91` attaches both servo channels and commands
   CLOSED/HOLD in the same microsecond. This is the only planned simultaneous servo motion, and the worst-case inrush on
   the 5 V buck. Attaching the latch servo about 300 ms after the escapement servo would remove it.
3. **The bridge inputs float until LEDC is set up.** `hal_esp32.cpp:18-19, 84-87`: GPIO0/1 are undriven from reset until
   line 84, and during flashing. With R_EN = L_EN = 3V3 the bridge follows whatever they float to. The hardware fix is the
   10k pull-downs R2/R3 (in the wiring). Nothing to change in firmware.
4. **The beeper sounds during reset and flashing.** `hal_esp32.cpp:20, 80-82`: the GPIO2 strap pull-up turns the
   beeper on from reset until line 82. It stays on continuously in download mode, and also if the app hangs before
   `hal::begin()`. The code comment expects this. Flash with the 12 V brick unplugged (USB alone powers the ESP32; the
   buzzer then has no 12 V).
5. **Do not add capacitors to GPIO9.** `hal_esp32.cpp:27`: the test button sits on the BOOT strap pin, so it gets no RC
   debounce, and holding it at power-on enters download mode. This is already documented in firmware/README.md and is
   safe. Listed so nobody "fixes" it with a capacitor.
6. **GPIO21 / U0TXD needs its 1 kΩ series resistor.** `hal_esp32.cpp:30` matches the README. If a future build enables
   the UART0 console (`ARDUINO_USB_CDC_ON_BOOT=0`), GPIO21 becomes an output and stops working as a sensor input.
7. No pin conflicts or mismatches between `hal_esp32.cpp`, `button/src/main.cpp`, `config.h` comments and
   `firmware/README.md` were found.
