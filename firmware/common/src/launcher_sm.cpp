#include "launcher_sm.h"

#include <cstring>

#include "hmac.h"

namespace beer {
namespace launcher {

using proto::AckResult;
using proto::Packet;
using proto::PacketType;
using proto::ParseResult;

const char* stateName(State s) {
  switch (s) {
    case State::Idle: return "IDLE";
    case State::Warn: return "WARN";
    case State::Cock: return "COCK";
    case State::Feed: return "FEED";
    case State::Armed: return "ARMED";
    case State::Fire: return "FIRE";
    case State::Reset: return "RESET";
    case State::Decock: return "DECOCK";
    case State::Fault: return "FAULT";
    case State::Pairing: return "PAIRING";
  }
  return "?";
}

const char* faultName(FaultCode f) {
  switch (f) {
    case FaultCode::None: return "NONE";
    case FaultCode::Stall: return "STALL";
    case FaultCode::CockTimeout: return "COCK_TIMEOUT";
    case FaultCode::RingReturnTimeout: return "RING_RETURN_TIMEOUT";
    case FaultCode::ArmNotMoving: return "ARM_NOT_MOVING";
    case FaultCode::Feed: return "FEED";
    case FaultCode::NoRelease: return "NO_RELEASE";
    case FaultCode::SafetyPinInDuringSequence: return "SAFETY_PIN_IN_DURING_SEQUENCE";
    case FaultCode::CockedAtBoot: return "COCKED_AT_BOOT";
    case FaultCode::Decock: return "DECOCK";
    case FaultCode::SensorConflict: return "SENSOR_CONFLICT";
    case FaultCode::MagEmpty: return "MAG_EMPTY";
    case FaultCode::ArmedTimeout: return "ARMED_TIMEOUT";
    case FaultCode::NotHome: return "NOT_HOME";
    case FaultCode::HoldLost: return "HOLD_LOST";
    case FaultCode::Count: break;
  }
  return "?";
}

// ------------------------------------------------------------------ setup --

void LauncherSM::begin(const Inputs& in, uint32_t now, const PairingRecord& pairing, uint32_t last_seq) {
  in_ = in;
  out_ = Outputs{};
  last_enc_ = in.enc_edges;
  ring_pos_ = 0;
  ring_pos_known_ = in.ring_home;
  hold_active_ = false;
  pairing_ = pairing;
  guard_.reset(last_seq);
  btn_raw_ = in.test_button;
  btn_ = in.test_button;
  btn_raw_since_ = now;
  btn_consumed_ = true;  // a button held during boot does nothing until released
  conflict_ = false;
  can_low_ = false;
  preloaded_ = false;
  last_fault_ = FaultCode::None;
  pattern_ = WarnPattern::Off;
  mag_empty_flag_ = in.mag_empty;
  preloaded_ = in.arm_cocked && in.can_in_cup;

  if (in.arm_home && in.arm_cocked) {
    enterFault(FaultCode::SensorConflict, now);
  } else if (in.arm_cocked) {
    enterFault(FaultCode::CockedAtBoot, now, "arm cocked at boot: remove safety pin, hold TEST 2 s to decock");
  } else if (!in.arm_home || !in.ring_home) {
    enterFault(FaultCode::NotHome, now, "arm/ring not home at boot: remove pin, hold TEST 2 s to decock");
  } else {
    enterIdle(now);
  }
  out_.warn = warnOutput(now);
}

// ------------------------------------------------------------------- tick --

void LauncherSM::tick(const Inputs& in, uint32_t now) {
  in_ = in;

  // Encoder: channel A only. Driving -> commanded direction; not driving -> the
  // only force on the ring is the arm load, which backdrives it towards park.
  const uint32_t delta = in.enc_edges - last_enc_;
  last_enc_ = in.enc_edges;
  if (out_.motor == MotorDir::Forward) {
    ring_pos_ += static_cast<int32_t>(delta);
  } else {
    ring_pos_ -= static_cast<int32_t>(delta);
  }
  if (in.ring_home) {
    ring_pos_ = 0;
    ring_pos_known_ = true;
  }
  sampleEncoder(now);

  // A can seen in the cup at the cocked angle stays there until it is thrown
  // (even if the arm is lowered by DECOCK or unwinds in a FAULT): remember it so
  // the next cycle never drops a second can on top.
  if (in.arm_cocked && in.can_in_cup && state_ != State::Fire && state_ != State::Reset) preloaded_ = true;
  if (in.can_in_cup) {
    if (!can_low_) {
      can_low_ = true;
      can_low_since_ = now;
    }
  } else {
    can_low_ = false;
  }

  if (!in.arm_cocked) {
    if (!cocked_lost_) {
      cocked_lost_ = true;
      cocked_lost_since_ = now;
    }
  } else {
    cocked_lost_ = false;
  }

  if (in.arm_home && in.arm_cocked) {
    if (!conflict_) {
      conflict_ = true;
      conflict_since_ = now;
    }
  } else {
    conflict_ = false;
  }

  // Global safety rules, evaluated before any state logic so the motor stops in
  // the very tick the pin is seen.
  if (sequenceState() && in.safety_pin_in) {
    enterFault(FaultCode::SafetyPinInDuringSequence, now);
  } else if (state_ == State::Decock && in.safety_pin_in) {
    enterFault(FaultCode::SafetyPinInDuringSequence, now, "safety pin inserted during decock: remove pin to decock");
  }
  // After FIRE the arm is home while the ring still sits at the cocked angle, so
  // both switches are legitimately closed in FIRE/RESET.
  const bool conflict_checked = state_ != State::Fault && state_ != State::Fire && state_ != State::Reset;
  if (conflict_checked && conflict_ && now - conflict_since_ >= cfg::kSensorConflictMs) {
    enterFault(FaultCode::SensorConflict, now);
  }

  handleTestButton(now);

  switch (state_) {
    case State::Idle: tickIdle(now); break;
    case State::Warn: tickWarn(now); break;
    case State::Cock: tickCock(now); break;
    case State::Feed: tickFeedState(now); break;
    case State::Armed: tickArmed(now); break;
    case State::Fire: tickFire(now); break;
    case State::Reset: tickReset(now); break;
    case State::Decock: tickDecock(now); break;
    case State::Fault: tickFault(now); break;
    case State::Pairing: tickPairing(now); break;
  }

  out_.warn = warnOutput(now);
}

bool LauncherSM::sequenceState() const {
  return state_ == State::Warn || state_ == State::Cock || state_ == State::Feed || state_ == State::Armed;
}

// ------------------------------------------------------------ transitions --

void LauncherSM::setState(State s, uint32_t now) {
  state_ = s;
  state_since_ = now;
}

void LauncherSM::setPattern(WarnPattern p, uint32_t now) {
  pattern_ = p;
  pattern_start_ = now;
}

void LauncherSM::enterIdle(uint32_t now) {
  if (motorDriving()) brake(now);
  setState(State::Idle, now);
  fault_ = FaultCode::None;
  hold_brake_ = false;
  hold_active_ = false;
  out_.latch = Latch::Hold;
  out_.esc = Escapement::Closed;
  if (pattern_ == WarnPattern::Fast || pattern_ == WarnPattern::Slow || pattern_ == WarnPattern::PairingChirp) {
    setPattern(WarnPattern::Off, now);
  }
  msg_ = "";
}

void LauncherSM::enterFault(FaultCode code, uint32_t now, const char* msg) {
  setState(State::Fault, now);
  fault_ = code;
  last_fault_ = code;
  msg_ = msg != nullptr ? msg : faultName(code);
  hold_active_ = false;
  brake(now);
  // While the arm is loaded (not home) the ring is backdriven by the arm spring:
  // keep the motor shorted (both HIGH) so it unwinds as slowly as possible.
  hold_brake_ = !in_.arm_home;
  out_.latch = Latch::Hold;
  out_.esc = Escapement::Closed;
  setPattern(WarnPattern::Slow, now);
}

void LauncherSM::faultThenDecock(FaultCode code, uint32_t now) {
  last_fault_ = code;
  if (in_.safety_pin_in) {
    enterFault(code, now, "remove safety pin to decock");
    return;
  }
  startDecock(now);
  msg_ = faultName(code);
}

void LauncherSM::startDecock(uint32_t now) {
  setState(State::Decock, now);
  hold_brake_ = false;
  hold_active_ = false;
  out_.esc = Escapement::Closed;
  out_.latch = Latch::Hold;  // no servo action: the arm stays latched to the ring
  if (in_.arm_cocked) preloaded_ = preloaded_ || in_.can_in_cup;
  setPattern(WarnPattern::Fast, now);
  msg_ = "decocking";
  drive(MotorDir::Reverse, cfg::kDecockPwmPct, now);
}

// --------------------------------------------------------------- requests --

AckResult LauncherSM::trigger(TriggerSource src, uint32_t now) {
  (void)src;
  if (state_ != State::Idle) return AckResult::Busy;
  if (in_.safety_pin_in) {
    setPattern(WarnPattern::BeepRefuse, now);
    msg_ = "refused: safety pin inserted";
    return AckResult::RefusedSafetyPin;
  }
  if (!in_.arm_home || !in_.ring_home || in_.arm_cocked || conflict_) {
    setPattern(WarnPattern::BeepRefuse, now);
    msg_ = "refused: arm/ring not home";
    return AckResult::RefusedNotReady;
  }
  if (in_.mag_empty && !preloaded_) {
    mag_empty_flag_ = true;
    setPattern(WarnPattern::BeepMagEmpty, now);
    msg_ = "refused: magazine empty";
    return AckResult::RefusedMagEmpty;
  }
  setState(State::Warn, now);
  seq_warn_start_ = now;
  setPattern(WarnPattern::Fast, now);
  // The beacon and the (guarded) cocking motion start together: the 1500 ms
  // warning runs while the arm is being cocked.
  cock_start_ = now;
  out_.latch = Latch::Hold;
  drive(MotorDir::Forward, cfg::kCockPwmPct, now);
  feed_step_ = FeedStep::NotStarted;
  feed_fail_ = FaultCode::None;
  msg_ = "sequence started";
  return AckResult::Accepted;
}

bool LauncherSM::requestClear(uint32_t now) {
  if (state_ != State::Fault) return false;
  if (conflict_) {
    msg_ = "sensor conflict persists";
    return false;
  }
  if (in_.arm_cocked || !in_.arm_home || !in_.ring_home) {
    if (in_.safety_pin_in) {
      msg_ = "remove safety pin to decock";
      return false;
    }
    startDecock(now);
    return true;
  }
  enterIdle(now);
  return true;
}

bool LauncherSM::requestDecock(uint32_t now) {
  if (state_ != State::Fault && state_ != State::Idle) return false;
  if (!(in_.arm_cocked || !in_.arm_home || !in_.ring_home)) {
    msg_ = "nothing to decock";
    return false;
  }
  if (conflict_) {
    msg_ = "sensor conflict persists";
    return false;
  }
  if (in_.safety_pin_in) {
    msg_ = "remove safety pin to decock";
    return false;
  }
  startDecock(now);
  return true;
}

bool LauncherSM::requestPairing(uint32_t now) {
  if (state_ != State::Idle) return false;
  setState(State::Pairing, now);
  setPattern(WarnPattern::PairingChirp, now);
  msg_ = "pairing: press and hold the beer button 5 s";
  return true;
}

PersistRequest LauncherSM::takePersist() {
  const PersistRequest p = persist_;
  persist_ = PersistRequest{};
  return p;
}

// ---------------------------------------------------------------- states --

void LauncherSM::tickIdle(uint32_t now) {
  brakeThenCoast(now);
  out_.latch = Latch::Hold;
  out_.esc = Escapement::Closed;
  mag_empty_flag_ = in_.mag_empty;
}

void LauncherSM::tickWarn(uint32_t now) {
  tickCock(now);  // the push already runs, with all its fault checks
  if (state_ == State::Warn && now - state_since_ >= cfg::kWarnStateMs) {
    state_ = State::Cock;
    state_since_ = now;
  }
}

void LauncherSM::tickCock(uint32_t now) {
  out_.latch = Latch::Hold;
  drive(MotorDir::Forward, cfg::kCockPwmPct, now);
  if (in_.arm_cocked) {
    if (ring_pos_known_ && ring_pos_ > 0) cock_stroke_edges_ = static_cast<uint32_t>(ring_pos_);
    // Capture the position at the switch edge and hold it from now on.
    hold_active_ = true;
    hold_target_ = ring_pos_;
    hold_err_big_ = false;
    setState(State::Feed, now);
    holdTick(now);
    feedStart(now);
    return;
  }
  const uint32_t elapsed = now - cock_start_;
  if (elapsed >= cfg::kCockTimeoutMs) {
    enterFault(FaultCode::CockTimeout, now);
  } else if (elapsed >= cfg::kArmMoveCheckMs && in_.arm_home) {
    enterFault(FaultCode::ArmNotMoving, now);
  } else if (stalled(now)) {
    enterFault(FaultCode::Stall, now);
  }
}

void LauncherSM::tickFeedState(uint32_t now) {
  holdTick(now);
  feedTick(now);
  if (holdLost(now)) {
    enterFault(FaultCode::HoldLost, now);
  } else if (feed_step_ == FeedStep::Done) {
    setState(State::Armed, now);
  } else if (feed_step_ == FeedStep::Failed) {
    faultThenDecock(feed_fail_, now);
  }
}

void LauncherSM::tickArmed(uint32_t now) {
  holdTick(now);
  out_.esc = Escapement::Closed;
  if (holdLost(now)) {
    enterFault(FaultCode::HoldLost, now);
    return;
  }
  const bool ready = in_.arm_cocked && holdSettled() && in_.can_in_cup && !in_.safety_pin_in &&
                     now - seq_warn_start_ >= cfg::kWarnMinBeforeFireMs;
  if (ready) {
    setState(State::Fire, now);
    fire_step_ = FireStep::WaitRelease;
    hold_active_ = false;
    out_.latch = Latch::Trip;
    out_.motor = MotorDir::Coast;  // the ring stays, the arm flies
    out_.pwm_pct = 0;
    preloaded_ = false;
    msg_ = "fire";
  } else if (now - state_since_ >= cfg::kArmedTimeoutMs) {
    faultThenDecock(FaultCode::ArmedTimeout, now);
  }
}

void LauncherSM::tickFire(uint32_t now) {
  out_.motor = MotorDir::Coast;
  out_.pwm_pct = 0;
  switch (fire_step_) {
    case FireStep::WaitRelease:
      out_.latch = Latch::Trip;
      if (in_.arm_home) {
        released_at_ = now;
        fire_step_ = FireStep::Released;
      } else if (now - state_since_ >= cfg::kFireReleaseTimeoutMs) {
        enterFault(FaultCode::NoRelease, now, "latch tripped but arm did not release: no auto retry");
      }
      return;
    case FireStep::Released:
      if (now - released_at_ >= cfg::kLatchHoldAfterMs) {
        out_.latch = Latch::Hold;
        setState(State::Reset, now);
        ring_returned_ = false;
        drive(MotorDir::Reverse, cfg::kRingReturnPwmPct, now);
      }
      return;
  }
}

void LauncherSM::tickReset(uint32_t now) {
  out_.latch = Latch::Hold;
  if (!ring_returned_) {
    drive(MotorDir::Reverse, cfg::kRingReturnPwmPct, now);
    if (in_.ring_home) {
      brake(now);
      ring_returned_ = true;
    } else if (now - state_since_ >= cfg::kRingReturnTimeoutMs) {
      enterFault(FaultCode::RingReturnTimeout, now);
      return;
    } else if (stalled(now)) {
      enterFault(FaultCode::Stall, now, "stall during ring return");
      return;
    } else {
      return;
    }
  }
  brakeThenCoast(now);
  // Beacon stays on while the ring moves and for at least kWarnOffAfterMs after HOLD.
  if (now - state_since_ < cfg::kWarnOffAfterMs) return;
  mag_empty_flag_ = in_.mag_empty;
  if (!in_.arm_home || !in_.ring_home || in_.arm_cocked) {
    enterFault(FaultCode::NotHome, now, "arm/ring not home after fire");
  } else {
    enterIdle(now);
    msg_ = mag_empty_flag_ ? "magazine empty: next trigger refused" : "";
  }
}

void LauncherSM::tickDecock(uint32_t now) {
  out_.esc = Escapement::Closed;
  out_.latch = Latch::Hold;
  if (in_.arm_home && in_.ring_home) {
    brake(now);
    enterIdle(now);
    msg_ = "decocked";
    return;
  }
  drive(MotorDir::Reverse, cfg::kDecockPwmPct, now);
  if (now - state_since_ >= cfg::kDecockTimeoutMs) {
    enterFault(FaultCode::Decock, now, "decock timeout: manual intervention");
  } else if (stalled(now)) {
    enterFault(FaultCode::Decock, now, "decock stalled: manual intervention");
  }
}

void LauncherSM::tickFault(uint32_t now) {
  out_.motor = (hold_brake_ || now < brake_until_) ? MotorDir::Brake : MotorDir::Coast;
  out_.pwm_pct = 0;
  out_.latch = Latch::Hold;
  out_.esc = Escapement::Closed;
}

void LauncherSM::tickPairing(uint32_t now) {
  brakeThenCoast(now);
  if (now - state_since_ >= cfg::kPairWindowMs) {
    enterIdle(now);
    msg_ = "pairing window expired";
  }
}

// ---------------------------------------------------------------- motor --

void LauncherSM::drive(MotorDir dir, uint8_t pwm, uint32_t now) {
  if (out_.motor != dir) {  // a new motion: restart the stall window
    motion_start_ = now;
    ring_[0] = EdgeSample{now, in_.enc_edges};
    ring_head_ = 1;
    ring_count_ = 1;
  }
  out_.motor = dir;
  out_.pwm_pct = pwm;
}

void LauncherSM::brake(uint32_t now) {
  if (out_.motor != MotorDir::Brake) brake_until_ = now + cfg::kBrakeMs;
  out_.motor = MotorDir::Brake;
  out_.pwm_pct = 0;
}

void LauncherSM::brakeThenCoast(uint32_t now) {
  out_.motor = (hold_brake_ || now < brake_until_) ? MotorDir::Brake : MotorDir::Coast;
  out_.pwm_pct = 0;
}

void LauncherSM::sampleEncoder(uint32_t now) {
  if (!motorDriving()) return;
  if (ring_count_ > 0) {
    const EdgeSample& newest = ring_[(ring_head_ + kRingLen - 1) % kRingLen];
    if (now - newest.t < cfg::kStallSampleMs) return;
  }
  ring_[ring_head_] = EdgeSample{now, in_.enc_edges};
  ring_head_ = (ring_head_ + 1) % kRingLen;
  if (ring_count_ < kRingLen) ++ring_count_;
}

bool LauncherSM::stalled(uint32_t now) const {
  if (!motorDriving()) return false;
  if (now - motion_start_ < cfg::kStallGraceMs + cfg::kStallWindowMs) return false;
  for (size_t i = 0; i < ring_count_; ++i) {
    const EdgeSample& s = ring_[(ring_head_ + kRingLen - 1 - i) % kRingLen];
    if (now - s.t >= cfg::kStallWindowMs) {
      if (s.t - motion_start_ < cfg::kStallGraceMs) return false;
      return in_.enc_edges - s.edges < cfg::kStallMinEdges;
    }
  }
  return false;
}

// ------------------------------------------------------------------ hold --

void LauncherSM::holdTick(uint32_t now) {
  const int32_t err = hold_target_ - ring_pos_;
  const uint32_t mag = static_cast<uint32_t>(err < 0 ? -err : err);
  if (mag > cfg::kHoldMaxErrEdges) {
    if (!hold_err_big_) {
      hold_err_big_ = true;
      hold_err_big_since_ = now;
    }
  } else {
    hold_err_big_ = false;
  }
  if (mag <= cfg::kHoldDeadbandEdges) {
    brake(now);
    return;
  }
  uint32_t pwm = mag * cfg::kHoldKpPctPerEdge;
  if (pwm < cfg::kHoldMinPwmPct) pwm = cfg::kHoldMinPwmPct;
  if (pwm > 100) pwm = 100;
  drive(err > 0 ? MotorDir::Forward : MotorDir::Reverse, static_cast<uint8_t>(pwm), now);
}

bool LauncherSM::holdLost(uint32_t now) const {
  if (hold_err_big_ && now - hold_err_big_since_ >= cfg::kHoldLostMs) return true;
  return cocked_lost_ && now - cocked_lost_since_ >= cfg::kCockedLostMs;
}

bool LauncherSM::holdSettled() const {
  const int32_t err = hold_target_ - ring_pos_;
  return static_cast<uint32_t>(err < 0 ? -err : err) <= cfg::kHoldSettledEdges;
}

// ------------------------------------------------------------------ feed --

void LauncherSM::feedStart(uint32_t now) {
  feed_t0_ = now;
  feed_fail_ = FaultCode::None;
  if (preloaded_ || in_.can_in_cup) {
    // A can is already in the cup (lowered by a DECOCK): never drop a second one.
    feed_step_ = FeedStep::Wait;
    out_.esc = Escapement::Closed;
  } else if (in_.mag_empty) {
    feed_step_ = FeedStep::Failed;
    feed_fail_ = FaultCode::MagEmpty;
    out_.esc = Escapement::Closed;
  } else {
    feed_step_ = FeedStep::Release;
    out_.esc = Escapement::Release;
  }
}

void LauncherSM::feedTick(uint32_t now) {
  switch (feed_step_) {
    case FeedStep::Release:
      out_.esc = Escapement::Release;
      if (now - feed_t0_ >= cfg::kEscReleaseMs) {
        out_.esc = Escapement::Closed;
        feed_step_ = FeedStep::Wait;
        feed_t0_ = now;
      }
      return;
    case FeedStep::Wait:
      out_.esc = Escapement::Closed;
      if (canStable(now)) {
        feed_step_ = FeedStep::Done;
      } else if (now - feed_t0_ >= cfg::kFeedWaitMs) {
        feed_step_ = FeedStep::Failed;
        feed_fail_ = FaultCode::Feed;
      }
      return;
    case FeedStep::NotStarted:
    case FeedStep::Done:
    case FeedStep::Failed:
      out_.esc = Escapement::Closed;
      return;
  }
}

bool LauncherSM::canStable(uint32_t now) const { return can_low_ && now - can_low_since_ >= cfg::kCanStableMs; }

// ---------------------------------------------------------------- beeper --

namespace {
bool beeps(uint32_t t, uint8_t n, uint32_t on, uint32_t off, bool* finished) {
  const uint32_t period = on + off;
  if (t >= static_cast<uint32_t>(n) * period) {
    *finished = true;
    return false;
  }
  return t % period < on;
}
}  // namespace

bool LauncherSM::warnOutput(uint32_t now) {
  const uint32_t t = now - pattern_start_;
  bool finished = false;
  bool on = false;
  switch (pattern_) {
    case WarnPattern::Off: return false;
    case WarnPattern::Fast: return t % cfg::kWarnFastPeriodMs < cfg::kWarnFastOnMs;
    case WarnPattern::Slow: return t % cfg::kWarnSlowPeriodMs < cfg::kWarnSlowOnMs;
    case WarnPattern::PairingChirp: return t % cfg::kPairingChirpPeriodMs < cfg::kPairingChirpOnMs;
    case WarnPattern::BeepMagEmpty:
      on = beeps(t, cfg::kBeepMagEmptyCount, cfg::kBeepMagEmptyOnMs, cfg::kBeepMagEmptyOffMs, &finished);
      break;
    case WarnPattern::BeepRefuse:
      on = beeps(t, cfg::kBeepRefuseCount, cfg::kBeepRefuseOnMs, cfg::kBeepRefuseOffMs, &finished);
      break;
    case WarnPattern::BeepPairOk:
      on = beeps(t, cfg::kBeepPairOkCount, cfg::kBeepPairOkOnMs, cfg::kBeepPairOkOffMs, &finished);
      break;
  }
  if (finished) pattern_ = WarnPattern::Off;
  return on;
}

// ----------------------------------------------------------- test button --

void LauncherSM::handleTestButton(uint32_t now) {
  const bool raw = in_.test_button;
  if (raw != btn_raw_) {
    btn_raw_ = raw;
    btn_raw_since_ = now;
  }
  if (raw != btn_ && now - btn_raw_since_ >= cfg::kTestBtnDebounceMs) {
    btn_ = raw;
    if (btn_) {
      btn_press_start_ = btn_raw_since_;
      btn_press_state_ = state_;
      btn_consumed_ = false;
    } else {
      const uint32_t held = btn_raw_since_ - btn_press_start_;
      if (!btn_consumed_ && held < cfg::kTestBtnShortMaxMs) {
        if (btn_press_state_ == State::Idle && state_ == State::Idle) {
          trigger(TriggerSource::TestButton, now);
        } else if (btn_press_state_ == State::Pairing && state_ == State::Pairing) {
          enterIdle(now);
          msg_ = "pairing cancelled";
        }
      }
      btn_consumed_ = true;
    }
    return;
  }
  if (btn_ && !btn_consumed_) {
    const uint32_t held = now - btn_press_start_;
    if (btn_press_state_ == State::Fault && state_ == State::Fault && held >= cfg::kTestBtnClearMs) {
      btn_consumed_ = true;
      requestClear(now);
    } else if (btn_press_state_ == State::Idle && state_ == State::Idle && held >= cfg::kTestBtnPairMs) {
      btn_consumed_ = true;
      requestPairing(now);
    }
  }
}

// ----------------------------------------------------------------- radio --

void LauncherSM::signTo(const uint8_t mac[proto::kMacLen], const Packet& p, const uint8_t key[proto::kKeyLen],
                        TxFrame* tx) const {
  proto::pack(p, key, tx->data);
  std::memcpy(tx->dest, mac, proto::kMacLen);
  tx->len = proto::kPacketLen;
  tx->send = true;
}

void LauncherSM::onPacket(const uint8_t mac[proto::kMacLen], const uint8_t* data, size_t len, uint32_t now,
                          TxFrame* tx) {
  tx->send = false;
  PacketType type;
  if (proto::peek(data, len, &type) != ParseResult::Ok) {
    ++stats_.bad_frames;
    return;
  }

  if (type == PacketType::PairReq) {
    Packet req;
    if (proto::unpackPairReq(data, len, &req) != ParseResult::Ok) {
      ++stats_.bad_tags;
      return;
    }
    if (state_ == State::Pairing) {
      pairing_.valid = true;
      std::memcpy(pairing_.mac, mac, proto::kMacLen);
      std::memcpy(pairing_.key, req.payload, proto::kKeyLen);
      guard_.reset(0);  // new key: old packets cannot verify any more
      persist_.pairing = true;
      persist_.last_seq = true;
      signTo(mac, proto::makePairAck(req.seq), pairing_.key, tx);
      enterIdle(now);
      setPattern(WarnPattern::BeepPairOk, now);
      msg_ = "paired";
      return;
    }
    // Lost PAIR_ACK: the same button resends the key we already stored. Re-ACK,
    // change nothing.
    if (pairing_.valid && std::memcmp(mac, pairing_.mac, proto::kMacLen) == 0 &&
        constantTimeEqual(req.payload, pairing_.key, proto::kKeyLen)) {
      signTo(mac, proto::makePairAck(req.seq), pairing_.key, tx);
    }
    return;
  }

  if (!pairing_.valid || std::memcmp(mac, pairing_.mac, proto::kMacLen) != 0) {
    ++stats_.unknown_sender;
    return;
  }
  Packet p;
  if (proto::unpack(data, len, pairing_.key, &p) != ParseResult::Ok) {
    ++stats_.bad_tags;
    return;
  }

  if (p.type == PacketType::Fire) {
    const SeqVerdict v = guard_.check(p.seq);
    if (v == SeqVerdict::Stale) {
      ++stats_.stale;
      return;  // replay: no ACK, no action
    }
    const uint8_t state_code = static_cast<uint8_t>(state_);
    if (v == SeqVerdict::Duplicate) {
      ++stats_.duplicates;
      signTo(mac, proto::makeAck(p.seq, state_code, AckResult::Duplicate, static_cast<uint8_t>(fault())),
             pairing_.key, tx);
      return;
    }
    guard_.checkAndAccept(p.seq);
    persist_.last_seq = true;
    ++stats_.accepted;
    last_batt_mv_ = p.batt_mv;
    const AckResult r = trigger(TriggerSource::Radio, now);
    signTo(mac, proto::makeAck(p.seq, static_cast<uint8_t>(state_), r, static_cast<uint8_t>(fault())),
           pairing_.key, tx);
    return;
  }

  if (p.type == PacketType::Status) {
    Packet s;
    s.type = PacketType::Status;
    s.seq = p.seq;
    s.payload[0] = static_cast<uint8_t>(state_);
    s.payload[1] = static_cast<uint8_t>(fault());
    s.payload[2] = static_cast<uint8_t>(last_fault_);
    s.payload[3] = mag_empty_flag_ ? 1 : 0;
    if (fault() != FaultCode::None) s.flags |= proto::kFlagFault;
    signTo(mac, s, pairing_.key, tx);
  }
  // ACK / PAIR_ACK addressed to a launcher: ignore.
}

}  // namespace launcher
}  // namespace beer
