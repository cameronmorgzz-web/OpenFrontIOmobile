// Launcher state machine. Hardware-agnostic: the caller samples the hardware into
// an Inputs struct, calls tick(inputs, now_ms) about every millisecond, and applies
// outputs() to the hardware. Radio frames go through onPacket(), which also
// enforces HMAC + replay rules; persistence is requested through takePersist().
//
// Mechanism (clay-pigeon-trap style): the motor-driven cocking ring carries a
// two-stage latch that hooks the arm's catch roller. COCK drags the latched arm to
// the cocked angle, where the motor HOLDS the ring position closed-loop on the
// encoder (backdrivable gearbox). FIRE trips the ring latch with a frame-mounted
// servo finger: the arm flies, the ring stays. RESET drives the ring back to park,
// where the latch snaps onto the arm's roller again.
//
//   IDLE -> WARN (50 ms: beacon + motor start) -> COCK (push until SW_ARM_COCKED)
//        -> FEED (hold + escapement) -> ARMED (hold) -> FIRE (TRIP, motor coast)
//        -> RESET (latch HOLD, ring return) -> IDLE
//   FEED / MAG_EMPTY / ARMED_TIMEOUT -> DECOCK (35 % reverse, arm stays latched) -> IDLE
//   other sequence faults -> FAULT (manual clear)
//   IDLE --(BTN_TEST >= 5 s)--> PAIRING --(PAIR_REQ | 30 s | short press)--> IDLE
//   FAULT --(BTN_TEST >= 2 s | "clear")--> DECOCK (arm/ring not home) or IDLE
#pragma once

#include <cstddef>
#include <cstdint>

#include "config.h"
#include "protocol.h"
#include "replay_guard.h"

namespace beer {
namespace launcher {

enum class State : uint8_t {
  Idle = 0,
  Warn,
  Cock,
  Feed,
  Armed,
  Fire,
  Reset,
  Decock,
  Fault,
  Pairing,
};

enum class FaultCode : uint8_t {
  None = 0,
  Stall,                      // < kStallMinEdges edges in a kStallWindowMs window while driving
  CockTimeout,                // SW_ARM_COCKED not reached in kCockTimeoutMs
  RingReturnTimeout,          // RESET: SW_RING_HOME not reached in kRingReturnTimeoutMs
  ArmNotMoving,               // SW_ARM_HOME still closed kArmMoveCheckMs after motor start
  Feed,                       // no can in the cup after the escapement cycle (jam / empty)
  NoRelease,                  // latch tripped but the arm did not reach home
  SafetyPinInDuringSequence,  // pin inserted between WARN and FIRE (or during DECOCK)
  CockedAtBoot,               // SW_ARM_COCKED closed at power-up
  Decock,                     // DECOCK timed out / stalled: manual intervention
  SensorConflict,             // SW_ARM_HOME and SW_ARM_COCKED both closed
  MagEmpty,                   // magazine empty discovered mid-sequence (at feed start)
  ArmedTimeout,               // ARMED preconditions not met within kArmedTimeoutMs
  NotHome,                    // arm/ring not home at boot or after RESET
  HoldLost,                   // the hold loop lost the cocked position
  Count                       // number of codes (keep last)
};

enum class MotorDir : uint8_t { Coast, Forward, Reverse, Brake };
enum class Latch : uint8_t { Hold, Trip };
enum class Escapement : uint8_t { Closed, Release };

struct Inputs {
  bool arm_home = false;       // SW_ARM_HOME closed
  bool arm_cocked = false;     // SW_ARM_COCKED closed (arm/ring at the cocked angle)
  bool ring_home = false;      // SW_RING_HOME closed (cocking ring parked)
  bool safety_pin_in = false;  // SW_SAFETY_PIN closed = pin inserted = safe (locks the ring)
  bool test_button = false;    // BTN_TEST pressed
  bool mag_empty = false;      // SNS_MAG_EMPTY HIGH
  bool can_in_cup = false;     // SNS_CAN_IN_CUP LOW
  uint32_t enc_edges = 0;      // free-running encoder edge counter (wraps)
};

struct Outputs {
  MotorDir motor = MotorDir::Coast;
  uint8_t pwm_pct = 0;  // only meaningful for Forward/Reverse
  bool warn = false;    // buzzer + beacon MOSFET
  Latch latch = Latch::Hold;
  Escapement esc = Escapement::Closed;
};

struct PairingRecord {
  bool valid = false;
  uint8_t mac[proto::kMacLen] = {};
  uint8_t key[proto::kKeyLen] = {};
};

struct PersistRequest {
  bool last_seq = false;  // write lastSeq() to NVS
  bool pairing = false;   // write pairing() to NVS
};

struct TxFrame {
  bool send = false;
  uint8_t dest[proto::kMacLen] = {};
  uint8_t data[proto::kPacketLen] = {};
  size_t len = 0;
};

enum class TriggerSource : uint8_t { Radio, TestButton, Serial };

struct RadioStats {
  uint32_t accepted = 0;
  uint32_t duplicates = 0;
  uint32_t stale = 0;
  uint32_t bad_frames = 0;  // length/magic/version/type
  uint32_t bad_tags = 0;
  uint32_t unknown_sender = 0;
};

const char* stateName(State s);
const char* faultName(FaultCode f);

class LauncherSM {
 public:
  void begin(const Inputs& in, uint32_t now, const PairingRecord& pairing, uint32_t last_seq);
  void tick(const Inputs& in, uint32_t now);
  const Outputs& outputs() const { return out_; }

  // Trigger requests. Return what the button is told in its ACK.
  proto::AckResult trigger(TriggerSource src, uint32_t now);
  bool requestClear(uint32_t now);   // = long press in FAULT / serial "clear"
  bool requestDecock(uint32_t now);  // serial "decock" (FAULT or IDLE)
  bool requestPairing(uint32_t now); // = long press in IDLE / serial "pair"

  // Handle one received ESP-NOW frame. tx is filled when a reply must be sent.
  void onPacket(const uint8_t mac[proto::kMacLen], const uint8_t* data, size_t len, uint32_t now,
                TxFrame* tx);

  PersistRequest takePersist();

  State state() const { return state_; }
  FaultCode fault() const { return state_ == State::Fault ? fault_ : FaultCode::None; }
  FaultCode lastFault() const { return last_fault_; }
  const char* message() const { return msg_; }
  const PairingRecord& pairing() const { return pairing_; }
  uint32_t lastSeq() const { return guard_.last(); }
  uint16_t lastButtonBattMv() const { return last_batt_mv_; }
  bool magEmptyFlag() const { return mag_empty_flag_; }
  bool canPreloaded() const { return preloaded_; }
  uint32_t cockStrokeEdges() const { return cock_stroke_edges_; }
  int32_t ringPosition() const { return ring_pos_; }  // encoder estimate, 0 = parked
  bool ringPositionKnown() const { return ring_pos_known_; }
  int32_t holdTarget() const { return hold_target_; }
  bool holding() const { return hold_active_; }
  const RadioStats& radioStats() const { return stats_; }

 private:
  enum class WarnPattern : uint8_t { Off, Fast, Slow, BeepMagEmpty, BeepRefuse, BeepPairOk, PairingChirp };
  enum class FeedStep : uint8_t { NotStarted, Release, Wait, Done, Failed };
  enum class FireStep : uint8_t { WaitRelease, Released };

  struct EdgeSample {
    uint32_t t;
    uint32_t edges;
  };
  static constexpr size_t kRingLen = 32;

  // transitions
  void setState(State s, uint32_t now);
  void enterIdle(uint32_t now);
  void enterFault(FaultCode code, uint32_t now, const char* msg = nullptr);
  void startDecock(uint32_t now);
  void faultThenDecock(FaultCode code, uint32_t now);
  void setPattern(WarnPattern p, uint32_t now);

  // per-state
  void tickIdle(uint32_t now);
  void tickWarn(uint32_t now);
  void tickCock(uint32_t now);
  void tickFeedState(uint32_t now);
  void tickArmed(uint32_t now);
  void tickFire(uint32_t now);
  void tickReset(uint32_t now);
  void tickDecock(uint32_t now);
  void tickFault(uint32_t now);
  void tickPairing(uint32_t now);

  // helpers
  void drive(MotorDir dir, uint8_t pwm, uint32_t now);
  void brake(uint32_t now);
  void brakeThenCoast(uint32_t now);
  bool motorDriving() const { return out_.motor == MotorDir::Forward || out_.motor == MotorDir::Reverse; }
  bool stalled(uint32_t now) const;
  void sampleEncoder(uint32_t now);
  void feedStart(uint32_t now);
  void feedTick(uint32_t now);
  bool canStable(uint32_t now) const;
  void holdTick(uint32_t now);
  bool holdLost(uint32_t now) const;
  bool holdSettled() const;
  bool warnOutput(uint32_t now);
  void handleTestButton(uint32_t now);
  bool sequenceState() const;
  void signTo(const uint8_t mac[proto::kMacLen], const proto::Packet& p, const uint8_t key[proto::kKeyLen],
              TxFrame* tx) const;

  // state
  State state_ = State::Idle;
  uint32_t state_since_ = 0;
  FaultCode fault_ = FaultCode::None;
  FaultCode last_fault_ = FaultCode::None;
  const char* msg_ = "";
  Inputs in_{};
  Outputs out_{};

  // warning beacon
  WarnPattern pattern_ = WarnPattern::Off;
  uint32_t pattern_start_ = 0;
  uint32_t seq_warn_start_ = 0;

  // motor bookkeeping
  uint32_t motion_start_ = 0;
  uint32_t brake_until_ = 0;
  bool hold_brake_ = false;
  EdgeSample ring_[kRingLen] = {};
  size_t ring_head_ = 0;
  size_t ring_count_ = 0;
  uint32_t last_enc_ = 0;
  int32_t ring_pos_ = 0;
  bool ring_pos_known_ = false;
  uint32_t cock_stroke_edges_ = cfg::kCockStrokeEdgesDefault;

  // position hold
  bool hold_active_ = false;
  int32_t hold_target_ = 0;
  bool hold_err_big_ = false;
  uint32_t hold_err_big_since_ = 0;
  bool cocked_lost_ = false;
  uint32_t cocked_lost_since_ = 0;

  // sequence
  uint32_t cock_start_ = 0;
  FeedStep feed_step_ = FeedStep::NotStarted;
  FaultCode feed_fail_ = FaultCode::None;
  uint32_t feed_t0_ = 0;
  bool can_low_ = false;
  uint32_t can_low_since_ = 0;
  bool preloaded_ = false;
  FireStep fire_step_ = FireStep::WaitRelease;
  uint32_t released_at_ = 0;
  bool ring_returned_ = false;
  uint32_t ring_returned_at_ = 0;
  bool mag_empty_flag_ = false;

  // inputs bookkeeping
  bool conflict_ = false;
  uint32_t conflict_since_ = 0;
  bool btn_raw_ = false;
  uint32_t btn_raw_since_ = 0;
  bool btn_ = false;
  uint32_t btn_press_start_ = 0;
  State btn_press_state_ = State::Idle;
  bool btn_consumed_ = false;

  // radio / persistence
  PairingRecord pairing_{};
  ReplayGuard guard_{};
  PersistRequest persist_{};
  uint16_t last_batt_mv_ = 0;
  RadioStats stats_{};
};

}  // namespace launcher
}  // namespace beer
