// Beer Button decision logic (hardware-free, unit tested on the host).
#pragma once

#include <cstddef>
#include <cstdint>

#include "config.h"
#include "protocol.h"

namespace beer {
namespace btn {

// Low-battery flag with hysteresis: set below kBtnBattLowMv, cleared only at or
// above kBtnBattOkMv. The flag lives in RTC memory across deep sleeps.
bool updateLowBattery(bool was_low, uint16_t batt_mv, uint16_t low_mv = cfg::kBtnBattLowMv,
                      uint16_t ok_mv = cfg::kBtnBattOkMv);

// ADC reading (mV at the pin) -> battery mV through the divider, saturating.
uint16_t batteryMvFromAdc(uint32_t pin_mv_sum, uint8_t samples, uint8_t ratio = cfg::kBtnBattDividerRatio);

// Sequence number to use as "last sent" after boot.
//  warm boot (deep-sleep wake, RTC copy valid): the RTC copy.
//  cold boot (battery swap, reset): NVS value + safety jump, because the last NVS
//  write might not have completed before power was lost.
uint32_t bootSequence(bool rtc_valid, uint32_t rtc_seq, uint32_t nvs_seq,
                      uint32_t jump = cfg::kBtnSeqColdBootJump);

// Press timing. Feed it the switch level every few ms.
class PressTracker {
 public:
  enum class Event : uint8_t { None, LongPress, Released };

  explicit PressTracker(uint32_t long_ms = cfg::kBtnLongPressMs) : long_ms_(long_ms) {}

  void begin(bool pressed, uint32_t now);
  // LongPress is reported once, when the hold time reaches long_ms while still
  // pressed. Released is reported once on release.
  Event update(bool pressed, uint32_t now);

  bool pressed() const { return pressed_; }
  bool longReported() const { return long_reported_; }
  uint32_t heldMs(uint32_t now) const { return pressed_ ? now - press_start_ : last_hold_ms_; }

 private:
  uint32_t long_ms_;
  bool pressed_ = false;
  bool long_reported_ = false;
  uint32_t press_start_ = 0;
  uint32_t last_hold_ms_ = 0;
};

// FIRE transmit policy: one TX, then up to `retries` re-sends of the SAME seq,
// each followed by an ACK wait of `wait_ms`.
class RetryPolicy {
 public:
  enum class Action : uint8_t { Send, Wait, Acked, GiveUp };

  RetryPolicy(uint8_t retries = cfg::kBtnFireRetries, uint32_t wait_ms = cfg::kBtnAckWaitMs)
      : max_attempts_(static_cast<uint8_t>(retries + 1)), wait_ms_(wait_ms) {}

  void start(uint32_t now);
  // Call in a loop. Returns Send when the caller must transmit now (the policy
  // counts it as sent), Wait while an ACK may still come, Acked/GiveUp at the end.
  Action poll(uint32_t now, bool ack_received);

  uint8_t attempts() const { return attempts_; }
  uint8_t maxAttempts() const { return max_attempts_; }
  // Worst-case radio time for one press.
  uint32_t worstCaseMs() const { return static_cast<uint32_t>(max_attempts_) * wait_ms_; }

 private:
  uint8_t max_attempts_;
  uint32_t wait_ms_;
  uint8_t attempts_ = 0;
  uint32_t sent_at_ = 0;
  bool done_ = false;
  bool acked_ = false;
};

// Pairing broadcast schedule: PAIR_REQ every interval, give up after window.
class PairingSchedule {
 public:
  enum class Action : uint8_t { SendReq, Wait, Timeout };

  PairingSchedule(uint32_t window_ms = cfg::kBtnPairWindowMs,
                  uint32_t interval_ms = cfg::kBtnPairReqIntervalMs)
      : window_ms_(window_ms), interval_ms_(interval_ms) {}

  void start(uint32_t now);
  Action poll(uint32_t now);
  uint32_t requestsSent() const { return sent_; }

 private:
  uint32_t window_ms_;
  uint32_t interval_ms_;
  uint32_t start_ = 0;
  uint32_t last_ = 0;
  uint32_t sent_ = 0;
};

// What the user feels/sees after a press.
struct Feedback {
  uint32_t haptic_ms = 0;      // one pulse
  uint32_t led_on_ms = 0;      // LED with the pulse
  uint8_t nack_blinks = 0;     // no ACK: 3 short blinks
  uint8_t lowbatt_blinks = 0;  // after the ack/nack pattern: 5 fast blinks
};

Feedback decideFeedback(bool acked, bool low_battery);

// Wake causes the button firmware distinguishes.
enum class Wake : uint8_t { PowerOn, Press, Timer };

// Only a fresh press (GPIO wake, which is armed only after a release was seen) may send FIRE.
// A timer wake re-checks a switch that was stuck/held: it must never fire, whatever the switch reads.
inline bool shouldSendFire(Wake wake, bool paired) { return paired && wake == Wake::Press; }

// Radio checks done by the button. Both verify the HMAC with the given key, so a
// forged or replayed ACK for an older press is ignored.
//  ACK: signed with the paired key, payload acked-seq == the seq we just sent.
bool isAckFor(const uint8_t* buf, size_t len, const uint8_t key[proto::kKeyLen], uint32_t seq,
              proto::Packet* out = nullptr);
//  PAIR_ACK: signed with the NEW key we offered, echoing the PAIR_REQ seq.
bool isPairAckFor(const uint8_t* buf, size_t len, const uint8_t new_key[proto::kKeyLen], uint32_t req_seq);

}  // namespace btn
}  // namespace beer
