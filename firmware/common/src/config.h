// All timing constants and tunables for both boards, in one place.
//
// Values marked [MECH] depend on the real mechanism and must be confirmed on the
// bench (see firmware/README.md, "Open issues"). Times are milliseconds unless the
// name says otherwise.
#pragma once

#include <cstdint>

namespace beer {
namespace cfg {

// ---------------------------------------------------------------- radio ----
constexpr uint8_t kEspNowChannel = 1;  // fixed, no router, no scanning

// ------------------------------------------------------------- button ----
constexpr uint32_t kBtnAckWaitMs = 120;      // wait for a signed ACK after each TX
constexpr uint8_t kBtnFireRetries = 3;       // retries after the first TX (same seq)
constexpr uint32_t kBtnHapticPulseMs = 80;   // one haptic pulse on ACK
constexpr uint32_t kBtnAckLedMs = 80;        // LED on together with the haptic pulse
constexpr uint32_t kBtnNackBlinkOnMs = 60;   // "no ACK": 3 short blinks
constexpr uint32_t kBtnNackBlinkOffMs = 90;
constexpr uint8_t kBtnNackBlinks = 3;
constexpr uint32_t kBtnLowBattBlinkOnMs = 40;   // low battery: 5 fast blinks
constexpr uint32_t kBtnLowBattBlinkOffMs = 60;
constexpr uint8_t kBtnLowBattBlinks = 5;
constexpr uint32_t kBtnUnpairedBlinkMs = 1000;  // unpaired: one long blink
constexpr uint32_t kBtnLongPressMs = 5000;      // hold >= 5 s -> pairing
constexpr uint32_t kBtnPairWindowMs = 30000;    // pairing gives up after 30 s
constexpr uint32_t kBtnPairReqIntervalMs = 500; // PAIR_REQ broadcast period
constexpr uint32_t kBtnPairBlinkPeriodMs = 1000; // LED slow blink while pairing
constexpr uint32_t kBtnStuckReleaseMs = 60000;  // switch still LOW after this -> timer sleep
constexpr uint32_t kBtnStuckSleepMs = 60000;    // ...and retry after this long
constexpr uint32_t kBtnReleaseDebounceMs = 30;  // switch must read HIGH this long before sleep
constexpr uint16_t kBtnBattLowMv = 3450;        // below -> low battery
constexpr uint16_t kBtnBattOkMv = 3600;         // at/above -> low flag cleared (hysteresis)
constexpr uint8_t kBtnBattDividerRatio = 2;     // 1M/1M divider
constexpr uint8_t kBtnBattSamples = 8;          // ADC samples averaged
constexpr uint32_t kBtnSeqColdBootJump = 16;    // seq safety jump after a cold boot

// ----------------------------------------------------------- launcher ----
// Sequence / warning
constexpr uint32_t kWarnStateMs = 50;           // WARN: beacon + cock motor start together; WARN->COCK after 50 ms
constexpr uint32_t kWarnMinBeforeFireMs = 1500; // beacon must run this long before FIRE
constexpr uint32_t kWarnFastPeriodMs = 250;     // 4 Hz pattern during a sequence
constexpr uint32_t kWarnFastOnMs = 125;
constexpr uint32_t kWarnSlowPeriodMs = 1000;    // 1 Hz pattern in FAULT
constexpr uint32_t kWarnSlowOnMs = 200;

// Encoder [MECH: verify] -------------------------------------------------
// 37GB555 gearmotor Hall encoder, channel A only, counted on BOTH edges (CHANGE
// interrupt). PPR on the motor shaft is unverified: 11 or 16. Everything below
// that is expressed in edges is derived from it. Single channel = no direction:
// edges are attributed to the commanded direction while driving and to the load
// direction (REVERSE, the arm spring backdrives the ring) while not driving.
constexpr uint32_t kEncPprMotor = 11;
constexpr uint32_t kEncEdgesPerMotorRev = 2 * kEncPprMotor;

// Cocking-ring travel park -> cocked in motor-shaft revolutions. Estimate only
// (~60 motor revs); the SM re-learns it from the encoder on every cock (status).
constexpr uint32_t kCockStrokeMotorRevs = 60;
constexpr uint32_t kCockStrokeEdgesDefault = kCockStrokeMotorRevs * kEncEdgesPerMotorRev;

// COCK [MECH] (the latch servo stays at HOLD during COCK)
constexpr uint32_t kCockTimeoutMs = 2200;       // motor start -> SW_ARM_COCKED (5 m setting nominal 1.63 s)
constexpr uint32_t kBrakeMs = 50;               // brake before coast after a motion
// Stall detection is the ONLY over-current protection (BTS7960 has no current
// limit; 5 A fuse only), so the window is kept tight.
constexpr uint32_t kStallGraceMs = 200;         // no stall check during the first 200 ms of a motion
constexpr uint32_t kStallWindowMs = 150;        // sliding window...
constexpr uint32_t kStallMinMotorRpm = 500;     // ...motor slower than this = stalled (~1/6 of loaded speed)
constexpr uint32_t kStallMinEdgesRaw = kStallMinMotorRpm * kEncEdgesPerMotorRev * kStallWindowMs / 60000u;
constexpr uint32_t kStallMinEdges = kStallMinEdgesRaw < 5 ? 5 : kStallMinEdgesRaw;  // 27 @11 PPR, 40 @16 PPR
constexpr uint32_t kStallSampleMs = 10;         // sliding window resolution
constexpr uint32_t kArmMoveCheckMs = 600;       // SW_ARM_HOME must have opened by then
constexpr uint8_t kCockPwmPct = 100;

// HOLD at the cocked angle (FEED + ARMED) [MECH]: P-control on the encoder count
// captured at the SW_ARM_COCKED edge. The gearbox is backdrivable, so the arm load
// creeps the ring back unless the motor holds it.
constexpr uint32_t kHoldDeadbandEdges = 3;      // |error| <= 3 edges: brake (both HIGH)
constexpr uint32_t kHoldKpPctPerEdge = 10;      // PWM % per edge of error
// Minimum PWM while correcting. Must exceed the static holding duty
// (~1 - t_return/t_cock: 48 % at 4 m, 59 % at 5 m) so a forward correction always
// wins against the load; otherwise the single-channel encoder would count a
// losing (backwards) motion as forward and the estimate would drift.
constexpr uint8_t kHoldMinPwmPct = 70;
constexpr uint32_t kHoldMaxErrEdges = 40;       // error above this...
constexpr uint32_t kHoldLostMs = 100;           // ...for this long -> HOLD_LOST
constexpr uint32_t kCockedLostMs = 30;          // SW_ARM_COCKED open this long while holding -> HOLD_LOST
constexpr uint32_t kHoldSettledEdges = 10;      // FIRE only with |error| <= this

// FEED [MECH] (starts at the SW_ARM_COCKED edge, while holding)
constexpr uint32_t kEscReleaseMs = 450;         // escapement RELEASE dwell (horn 65->125 deg + can clears f1: <=0.23 s in sim)
constexpr uint32_t kFeedWaitMs = 800;           // after CLOSED, wait this long for the can
constexpr uint32_t kCanStableMs = 100;          // SNS_CAN_IN_CUP must be LOW this long

// ARMED / FIRE / RESET
constexpr uint32_t kArmedTimeoutMs = 1500;
constexpr uint32_t kFireReleaseTimeoutMs = 400; // latch TRIP -> SW_ARM_HOME (motor coasts from TRIP)
constexpr uint32_t kLatchHoldAfterMs = 300;     // after release, latch servo back to HOLD, ring return starts
constexpr uint32_t kWarnOffAfterMs = 500;       // beacon off >= this long after HOLD (and ring parked)
constexpr uint8_t kRingReturnPwmPct = 100;      // unloaded return
constexpr uint32_t kRingReturnTimeoutMs = 1500; // until SW_RING_HOME (nominal 0.67 s)

// DECOCK [MECH]: reverse with the arm still latched to the ring, no servo action.
constexpr uint8_t kDecockPwmPct = 35;
constexpr uint32_t kDecockTimeoutMs = 3000;     // until SW_ARM_HOME and SW_RING_HOME

// Inputs / UI
constexpr uint32_t kTestBtnDebounceMs = 20;
constexpr uint32_t kTestBtnShortMaxMs = 1000;   // released before this -> short press (trigger)
constexpr uint32_t kTestBtnClearMs = 2000;      // hold in FAULT -> clear / DECOCK
constexpr uint32_t kTestBtnPairMs = 5000;       // hold in IDLE -> PAIRING
constexpr uint32_t kPairWindowMs = 30000;
constexpr uint32_t kSensorConflictMs = 30;      // both arm switches LOW this long -> FAULT

// Beeper patterns (buzzer + beacon share one output)
constexpr uint8_t kBeepMagEmptyCount = 3;       // refusal: magazine empty
constexpr uint32_t kBeepMagEmptyOnMs = 100;
constexpr uint32_t kBeepMagEmptyOffMs = 100;
constexpr uint8_t kBeepRefuseCount = 2;         // refusal: safety pin in / not ready
constexpr uint32_t kBeepRefuseOnMs = 300;
constexpr uint32_t kBeepRefuseOffMs = 200;
constexpr uint8_t kBeepPairOkCount = 3;         // pairing success: triple beep
constexpr uint32_t kBeepPairOkOnMs = 80;
constexpr uint32_t kBeepPairOkOffMs = 120;
constexpr uint32_t kPairingChirpPeriodMs = 1000; // short chirp while PAIRING
constexpr uint32_t kPairingChirpOnMs = 40;

// Servo pulse widths, microseconds [MECH: calibrate on the bench]
constexpr uint16_t kLatchHoldUs = 1100;
constexpr uint16_t kLatchTripUs = 1900;
constexpr uint16_t kEscClosedUs = 1000;         // horn -8 deg: pushrod 8 deg past dead centre (locks)
constexpr uint16_t kEscStageUs = 1400;          // horn 65 deg
constexpr uint16_t kEscReleaseUs = 1730;        // horn 125 deg

// Motor PWM (BTS7960 / IBT-2: RPWM=GPIO0, LPWM=GPIO1, R_EN=L_EN=3V3)
constexpr uint32_t kMotorPwmHz = 20000;
constexpr uint32_t kServoPwmHz = 50;

}  // namespace cfg
}  // namespace beer
