#include "hal_esp32.h"

#include <Arduino.h>
#include <esp_arduino_version.h>

#include <cstdint>

#include "config.h"

using namespace beer;
using beer::launcher::Escapement;
using beer::launcher::Latch;
using beer::launcher::MotorDir;

namespace {

// ------------------------------------------------------------------- pins --
constexpr uint8_t kPinRpwm = 0;          // BTS7960 RPWM (COCK / forward)
constexpr uint8_t kPinLpwm = 1;          // BTS7960 LPWM (RETRACT / reverse); R_EN = L_EN = 3V3
constexpr uint8_t kPinWarn = 2;          // N-MOSFET: 12 V buzzer + beacon (strapping pin, 10k pull-up)
constexpr uint8_t kPinEncA = 3;          // motor Hall encoder channel A
constexpr uint8_t kPinArmHome = 4;       // LOW = arm on its forward stop
constexpr uint8_t kPinArmCocked = 5;     // LOW = arm/ring at the cocked angle
constexpr uint8_t kPinRingHome = 6;      // SW_RING_HOME: LOW = cocking ring parked
constexpr uint8_t kPinSafetyPin = 7;     // LOW = safety pin inserted (safe, locks the ring)
constexpr uint8_t kPinServoEsc = 8;      // escapement servo (strapping pin, on-board LED)
constexpr uint8_t kPinTestBtn = 9;       // BOOT + external test button, LOW = pressed
constexpr uint8_t kPinServoLatch = 10;   // latch servo: finger trips the ring latch
constexpr uint8_t kPinMagEmpty = 20;     // IR: LOW = can at magazine bottom, HIGH = empty
constexpr uint8_t kPinCanInCup = 21;     // IR: LOW = can in cup

// LEDC channels: 0/1 share timer 0 (20 kHz motor), 2/3 share timer 1 (50 Hz servos).
constexpr uint8_t kChRpwm = 0;
constexpr uint8_t kChLpwm = 1;
constexpr uint8_t kChEsc = 2;
constexpr uint8_t kChLatch = 3;
constexpr uint8_t kMotorBits = 10;
constexpr uint32_t kMotorMax = (1u << kMotorBits) - 1;
constexpr uint8_t kServoBits = 14;
constexpr uint32_t kServoPeriodUs = 1000000u / cfg::kServoPwmHz;

volatile uint32_t g_enc_edges = 0;

void IRAM_ATTR encoderIsr() { g_enc_edges = g_enc_edges + 1; }

void pwmSetup(uint8_t pin, uint8_t ch, uint32_t freq, uint8_t bits) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttachChannel(pin, freq, bits, ch);
#else
  ledcSetup(ch, freq, bits);
  ledcAttachPin(pin, ch);
#endif
}

uint32_t g_last_duty[4] = {UINT32_MAX, UINT32_MAX, UINT32_MAX, UINT32_MAX};

void pwmWrite(uint8_t pin, uint8_t ch, uint32_t duty) {
  if (ch < 4) {
    if (g_last_duty[ch] == duty) return;  // apply() runs every ms: only touch LEDC on change
    g_last_duty[ch] = duty;
  }
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)ch;
  ledcWrite(pin, duty);
#else
  (void)pin;
  ledcWrite(ch, duty);
#endif
}

uint32_t servoDuty(uint16_t us) { return (static_cast<uint32_t>(us) << kServoBits) / kServoPeriodUs; }

bool low(uint8_t pin) { return digitalRead(pin) == LOW; }

}  // namespace

namespace hal {

void begin() {
  // Warning output first: GPIO2 has a 10k pull-up, so the beacon chirps until here.
  pinMode(kPinWarn, OUTPUT);
  digitalWrite(kPinWarn, LOW);

  pwmSetup(kPinRpwm, kChRpwm, cfg::kMotorPwmHz, kMotorBits);
  pwmSetup(kPinLpwm, kChLpwm, cfg::kMotorPwmHz, kMotorBits);
  pwmWrite(kPinRpwm, kChRpwm, 0);
  pwmWrite(kPinLpwm, kChLpwm, 0);
  // Servos one after the other: never two MG996R start-up surges on the 3 A buck at once.
  pwmSetup(kPinServoEsc, kChEsc, cfg::kServoPwmHz, kServoBits);
  pwmWrite(kPinServoEsc, kChEsc, servoDuty(cfg::kEscClosedUs));
  delay(300);
  pwmSetup(kPinServoLatch, kChLatch, cfg::kServoPwmHz, kServoBits);
  pwmWrite(kPinServoLatch, kChLatch, servoDuty(cfg::kLatchHoldUs));

  const uint8_t inputs[] = {kPinEncA,  kPinArmHome, kPinArmCocked, kPinRingHome,
                            kPinSafetyPin, kPinTestBtn, kPinMagEmpty, kPinCanInCup};
  for (uint8_t p : inputs) pinMode(p, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(kPinEncA), encoderIsr, CHANGE);
}

uint32_t encoderEdges() { return g_enc_edges; }

launcher::Inputs readInputs() {
  launcher::Inputs in;
  in.arm_home = low(kPinArmHome);
  in.arm_cocked = low(kPinArmCocked);
  in.ring_home = low(kPinRingHome);
  in.safety_pin_in = low(kPinSafetyPin);
  in.test_button = low(kPinTestBtn);
  in.mag_empty = !low(kPinMagEmpty);
  in.can_in_cup = low(kPinCanInCup);
  in.enc_edges = g_enc_edges;
  return in;
}

void apply(const launcher::Outputs& o) {
  const uint32_t duty = kMotorMax * o.pwm_pct / 100u;
  switch (o.motor) {
    case MotorDir::Forward:  // RPWM = PWM, LPWM = 0
      pwmWrite(kPinLpwm, kChLpwm, 0);
      pwmWrite(kPinRpwm, kChRpwm, duty);
      break;
    case MotorDir::Reverse:  // RPWM = 0, LPWM = PWM
      pwmWrite(kPinRpwm, kChRpwm, 0);
      pwmWrite(kPinLpwm, kChLpwm, duty);
      break;
    case MotorDir::Brake:  // both HIGH: both high-side switches on
      pwmWrite(kPinRpwm, kChRpwm, kMotorMax);
      pwmWrite(kPinLpwm, kChLpwm, kMotorMax);
      break;
    case MotorDir::Coast:  // both LOW (with EN tied high this is a low-side brake, see README)
      pwmWrite(kPinRpwm, kChRpwm, 0);
      pwmWrite(kPinLpwm, kChLpwm, 0);
      break;
  }
  pwmWrite(kPinServoLatch, kChLatch, servoDuty(o.latch == Latch::Trip ? cfg::kLatchTripUs : cfg::kLatchHoldUs));
  pwmWrite(kPinServoEsc, kChEsc, servoDuty(o.esc == Escapement::Release ? cfg::kEscReleaseUs
                                                 : o.esc == Escapement::Stage ? cfg::kEscStageUs : cfg::kEscClosedUs));
  digitalWrite(kPinWarn, o.warn ? HIGH : LOW);
}

}  // namespace hal
