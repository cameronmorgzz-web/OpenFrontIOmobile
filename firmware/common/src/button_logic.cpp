#include "button_logic.h"

namespace beer {
namespace btn {

bool updateLowBattery(bool was_low, uint16_t batt_mv, uint16_t low_mv, uint16_t ok_mv) {
  if (was_low) return batt_mv < ok_mv;
  return batt_mv < low_mv;
}

uint16_t batteryMvFromAdc(uint32_t pin_mv_sum, uint8_t samples, uint8_t ratio) {
  if (samples == 0) return 0;
  const uint32_t mv = (pin_mv_sum / samples) * ratio;
  return mv > 0xFFFFu ? static_cast<uint16_t>(0xFFFFu) : static_cast<uint16_t>(mv);
}

uint32_t bootSequence(bool rtc_valid, uint32_t rtc_seq, uint32_t nvs_seq, uint32_t jump) {
  if (rtc_valid) {
    // Never go backwards even if NVS somehow holds a larger value.
    return rtc_seq >= nvs_seq ? rtc_seq : nvs_seq;
  }
  return nvs_seq + jump;
}

void PressTracker::begin(bool pressed, uint32_t now) {
  pressed_ = pressed;
  long_reported_ = false;
  press_start_ = now;
  last_hold_ms_ = 0;
}

PressTracker::Event PressTracker::update(bool pressed, uint32_t now) {
  if (pressed && !pressed_) {
    pressed_ = true;
    long_reported_ = false;
    press_start_ = now;
    return Event::None;
  }
  if (!pressed && pressed_) {
    pressed_ = false;
    last_hold_ms_ = now - press_start_;
    return Event::Released;
  }
  if (pressed_ && !long_reported_ && now - press_start_ >= long_ms_) {
    long_reported_ = true;
    return Event::LongPress;
  }
  return Event::None;
}

void RetryPolicy::start(uint32_t now) {
  attempts_ = 0;
  sent_at_ = now;
  done_ = false;
  acked_ = false;
}

RetryPolicy::Action RetryPolicy::poll(uint32_t now, bool ack_received) {
  if (done_) return acked_ ? Action::Acked : Action::GiveUp;
  if (ack_received && attempts_ > 0) {
    done_ = true;
    acked_ = true;
    return Action::Acked;
  }
  if (attempts_ == 0 || now - sent_at_ >= wait_ms_) {
    if (attempts_ >= max_attempts_) {
      done_ = true;
      return Action::GiveUp;
    }
    ++attempts_;
    sent_at_ = now;
    return Action::Send;
  }
  return Action::Wait;
}

void PairingSchedule::start(uint32_t now) {
  start_ = now;
  last_ = now;
  sent_ = 0;
}

PairingSchedule::Action PairingSchedule::poll(uint32_t now) {
  if (now - start_ >= window_ms_) return Action::Timeout;
  if (sent_ == 0 || now - last_ >= interval_ms_) {
    last_ = now;
    ++sent_;
    return Action::SendReq;
  }
  return Action::Wait;
}

Feedback decideFeedback(bool acked, bool low_battery) {
  Feedback f;
  if (acked) {
    f.haptic_ms = cfg::kBtnHapticPulseMs;
    f.led_on_ms = cfg::kBtnAckLedMs;
  } else {
    f.nack_blinks = cfg::kBtnNackBlinks;
  }
  if (low_battery) f.lowbatt_blinks = cfg::kBtnLowBattBlinks;
  return f;
}

bool isAckFor(const uint8_t* buf, size_t len, const uint8_t key[proto::kKeyLen], uint32_t seq,
              proto::Packet* out) {
  proto::Packet p;
  if (proto::unpack(buf, len, key, &p) != proto::ParseResult::Ok) return false;
  if (p.type != proto::PacketType::Ack || proto::ackedSeq(p) != seq) return false;
  if (out != nullptr) *out = p;
  return true;
}

bool isPairAckFor(const uint8_t* buf, size_t len, const uint8_t new_key[proto::kKeyLen], uint32_t req_seq) {
  proto::Packet p;
  if (proto::unpack(buf, len, new_key, &p) != proto::ParseResult::Ok) return false;
  return p.type == proto::PacketType::PairAck && p.seq == req_seq;
}

}  // namespace btn
}  // namespace beer
