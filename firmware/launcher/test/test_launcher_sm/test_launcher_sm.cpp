// Launcher state machine scenarios against a simulated mechanism, 1 ms steps.
#include <unity.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <functional>
#include <set>

#include "config.h"
#include "launcher_sm.h"
#include "plant.h"
#include "protocol.h"

using namespace beer;
using namespace beer::launcher;
using proto::AckResult;
using sim::Plant;
using sim::PlantParams;

static const uint8_t kBtnMac[6] = {0x24, 0x0A, 0xC4, 0x11, 0x22, 0x33};
static const uint8_t kOtherMac[6] = {0x24, 0x0A, 0xC4, 0x99, 0x99, 0x99};
static const uint8_t kKey[16] = {0x5A, 0x11, 0x92, 0x03, 0xE4, 0x75, 0x26, 0xB7,
                                 0x48, 0xD9, 0x6A, 0xFB, 0x0C, 0x9D, 0x2E, 0xBF};
static const uint8_t kWrongKey[16] = {0xA5, 0xEE, 0x6D, 0xFC, 0x1B, 0x8A, 0xD9, 0x48,
                                      0xB7, 0x26, 0x95, 0x04, 0xF3, 0x62, 0xD1, 0x40};

// Fault codes seen by any test (checked by the last test).
static std::set<int> g_faults_seen;

// cock_ms from calc/RESULTS.md (motor torque-speed model, 4 m: 1.38 s, 5 m: 1.82 s)
static PlantParams plant4m() {
  PlantParams p;
  p.cock_ms = 1380;
  p.return_ms = 670;
  return p;
}
static PlantParams plant5m() {
  PlantParams p = plant4m();
  p.cock_ms = 1820;
  return p;
}

struct Rig {
  Plant p;
  LauncherSM sm;
  uint32_t now = 1000;
  PairingRecord pairing;

  // observations
  long first_warn = -1;
  long fire_at = -1;
  long esc_release_at = -1;
  long esc_closed_at = -1;   // last RELEASE -> CLOSED command
  Escapement prev_esc = Escapement::Closed;
  long cocked_at = -1;     // SW_ARM_COCKED edge seen by the SM (COCK -> FEED)
  bool coast_at_trip = false;
  bool drove_after_fault = false;
  bool latch_trip_while_driving = false;
  int max_hold_err_real = 0;  // |plant ring - stroke| while holding
  int max_hold_err_est = 0;   // |SM estimate - plant ring| while holding
  State prev = State::Idle;

  explicit Rig(const PlantParams& pp = plant4m()) : p(pp) {
    pairing.valid = true;
    std::memcpy(pairing.mac, kBtnMac, 6);
    std::memcpy(pairing.key, kKey, 16);
  }

  void boot(bool paired = true, uint32_t last_seq = 0) {
    sm.begin(p.inputs(), now, paired ? pairing : PairingRecord{}, last_seq);
    prev = sm.state();
  }

  bool driving() const {
    return sm.outputs().motor == MotorDir::Forward || sm.outputs().motor == MotorDir::Reverse;
  }

  void step() {
    sm.tick(p.inputs(), now);
    const Outputs& o = sm.outputs();
    if (o.warn && first_warn < 0) first_warn = now;
    if (sm.state() == State::Fire && o.latch == Latch::Trip && fire_at < 0) {
      fire_at = now;
      coast_at_trip = o.motor == MotorDir::Coast;
    }
    if (o.latch == Latch::Trip && driving()) latch_trip_while_driving = true;
    if (o.esc == Escapement::Release && esc_release_at < 0) esc_release_at = now;
    if (prev_esc == Escapement::Release && o.esc == Escapement::Closed) esc_closed_at = now;
    prev_esc = o.esc;
    if (prev == State::Cock && sm.state() == State::Feed && cocked_at < 0) cocked_at = now;
    if (sm.state() == State::Fault && driving()) drove_after_fault = true;
    if (sm.holding()) {
      const int real = static_cast<int>(std::lround(std::fabs(p.r - p.P.stroke)));
      const int est = static_cast<int>(std::lround(std::fabs(sm.ringPosition() - p.r)));
      if (real > max_hold_err_real) max_hold_err_real = real;
      if (est > max_hold_err_est) max_hold_err_est = est;
    }
    if (sm.lastFault() != FaultCode::None) g_faults_seen.insert(static_cast<int>(sm.lastFault()));
    prev = sm.state();
    p.step(o);
    ++now;
  }

  void run(uint32_t ms) {
    for (uint32_t i = 0; i < ms; ++i) step();
  }

  bool runUntil(const std::function<bool()>& pred, uint32_t max_ms) {
    for (uint32_t i = 0; i < max_ms; ++i) {
      if (pred()) return true;
      step();
    }
    return pred();
  }

  TxFrame sendRaw(const uint8_t* mac, const uint8_t* buf, size_t len) {
    TxFrame tx;
    sm.onPacket(mac, buf, len, now, &tx);
    return tx;
  }

  TxFrame sendFire(uint32_t seq, const uint8_t* key = kKey, const uint8_t* mac = kBtnMac) {
    uint8_t buf[proto::kPacketLen];
    proto::pack(proto::makeFire(seq, 3900, false), key, buf);
    return sendRaw(mac, buf, sizeof(buf));
  }

  void pressTest(uint32_t ms) {
    p.test_button = true;
    run(ms);
    p.test_button = false;
    run(30);
  }

  uint32_t motorMs() const { return p.motor_on_ms; }
};

// Decode an ACK frame with the paired key; fails the test if it is not one.
static proto::Packet ackOf(const TxFrame& tx, uint32_t seq) {
  TEST_ASSERT_TRUE_MESSAGE(tx.send, "expected an ACK");
  proto::Packet p;
  TEST_ASSERT_EQUAL(proto::ParseResult::Ok, proto::unpack(tx.data, tx.len, kKey, &p));
  TEST_ASSERT_EQUAL(proto::PacketType::Ack, p.type);
  TEST_ASSERT_EQUAL_UINT32(seq, proto::ackedSeq(p));
  TEST_ASSERT_TRUE(std::memcmp(tx.dest, kBtnMac, 6) == 0);
  return p;
}

static bool isIdle(Rig& r) { return r.sm.state() == State::Idle; }

void setUp() {}
void tearDown() {}

// ------------------------------------------------------------- scenario 1 --

static void nominalFromPacket(const PlantParams& pp, const char* label, long max_pkt_to_fire) {
  Rig r(pp);
  r.boot();
  r.run(100);
  const uint32_t t_press = r.now;
  r.run(250);  // button wake + WiFi/ESP-NOW init + air time
  const uint32_t t_pkt = r.now;
  const proto::Packet ack = ackOf(r.sendFire(17), 17);
  TEST_ASSERT_EQUAL(AckResult::Accepted, proto::ackResult(ack));
  TEST_ASSERT_TRUE(r.sm.takePersist().last_seq);
  TEST_ASSERT_EQUAL_UINT32(17, r.sm.lastSeq());

  TEST_ASSERT_TRUE(r.runUntil([&] { return r.fire_at >= 0; }, 5000));
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 8000));
  const long idle_at = r.now;

  const long warn_lead = r.fire_at - r.first_warn;
  const long latency_pkt = r.fire_at - static_cast<long>(t_pkt);
  const long latency_press = r.fire_at - static_cast<long>(t_press);
  const long cycle = idle_at - static_cast<long>(t_press);
  std::printf("[%s] warn lead %ld ms, packet->fire %ld ms, press->fire %ld ms, press->IDLE %ld ms, "
              "cocked %ld ms after packet, hold error real<=%d est<=%d edges\n",
              label, warn_lead, latency_pkt, latency_press, cycle, r.cocked_at - static_cast<long>(t_pkt),
              r.max_hold_err_real, r.max_hold_err_est);

  TEST_ASSERT_EQUAL_INT(static_cast<long>(t_pkt), r.first_warn);  // beacon on at trigger
  TEST_ASSERT_GREATER_OR_EQUAL_MESSAGE(1500, warn_lead, "warning must run >= 1500 ms before FIRE");
  TEST_ASSERT_LESS_OR_EQUAL_MESSAGE(max_pkt_to_fire, latency_pkt, "packet -> fire latency");
  TEST_ASSERT_LESS_OR_EQUAL_MESSAGE(8000, cycle, "cycle back to IDLE");
  TEST_ASSERT_EQUAL_INT_MESSAGE(r.cocked_at, r.esc_release_at, "feed starts at the SW_ARM_COCKED edge");
  TEST_ASSERT_TRUE_MESSAGE(r.p.staged_while_cocking, "escapement pre-staged during COCK");
  TEST_ASSERT_GREATER_OR_EQUAL_MESSAGE(400, r.fire_at - r.esc_closed_at, "escapement back at HOLD before FIRE");
  TEST_ASSERT_TRUE_MESSAGE(r.coast_at_trip, "motor must coast at the moment of TRIP");
  TEST_ASSERT_FALSE(r.latch_trip_while_driving);
  TEST_ASSERT_LESS_OR_EQUAL_MESSAGE(10, r.max_hold_err_real, "ring held at the cocked angle");
  TEST_ASSERT_LESS_OR_EQUAL_MESSAGE(10, r.max_hold_err_est, "encoder estimate tracks the ring");
  TEST_ASSERT_EQUAL_INT(1, r.p.launched);
  TEST_ASSERT_EQUAL_INT(0, r.p.misfed);
  TEST_ASSERT_EQUAL_INT(0, r.p.double_can);
  TEST_ASSERT_EQUAL_INT(9, r.p.mag);
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome() && r.p.latched);
  TEST_ASSERT_FALSE(r.sm.outputs().warn);
  TEST_ASSERT_EQUAL(Latch::Hold, r.sm.outputs().latch);
  TEST_ASSERT_EQUAL(FaultCode::None, r.sm.lastFault());
  TEST_ASSERT_LESS_OR_EQUAL(5, std::abs(static_cast<int>(r.sm.cockStrokeEdges()) - static_cast<int>(r.p.P.stroke)));
}

// 4 m: press -> fire <= 2.5 s (brief) = 0.25 s button wake/TX + 2.25 s packet -> fire.
void test_s1_nominal_cycle_from_button_packet_4m() { nominalFromPacket(plant4m(), "4m", 2250); }
// 5 m misses the 2.5 s target (KNOWN_LIMITATIONS.md); this pins the expected value instead.
void test_s1_nominal_cycle_from_button_packet_5m() { nominalFromPacket(plant5m(), "5m", 2550); }

void test_s1_two_cycles_back_to_back() {
  Rig r;
  r.boot();
  r.run(50);
  ackOf(r.sendFire(1), 1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 8000));
  ackOf(r.sendFire(2), 2);
  r.run(10);
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 8000));
  TEST_ASSERT_EQUAL_INT(2, r.p.launched);
  TEST_ASSERT_EQUAL_INT(8, r.p.mag);
}

void test_s1_hold_against_load_while_waiting() {
  // The can sensor only confirms late: the ring must hold the cocked angle against
  // the backdriving arm load for the whole wait, then fire normally.
  for (const PlantParams& pp : {plant4m(), plant5m()}) {
    Rig r(pp);
    r.p.can_sensor_dead = true;
    r.boot();
    r.sendFire(1);
    TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Feed; }, 3000));
    r.run(600);
    r.p.can_sensor_dead = false;
    TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 8000));
    TEST_ASSERT_EQUAL_INT(1, r.p.launched);
    TEST_ASSERT_LESS_OR_EQUAL(10, r.max_hold_err_real);
    TEST_ASSERT_LESS_OR_EQUAL(10, r.max_hold_err_est);
  }
}

void test_s1_hold_lost_when_motor_cannot_hold() {
  Rig r;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Feed; }, 3000));
  r.run(50);
  r.p.motor_dead = true;  // driver/motor failure: the arm load backdrives the ring
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 1000));
  TEST_ASSERT_EQUAL(FaultCode::HoldLost, r.sm.fault());
  TEST_ASSERT_LESS_THAN(0, r.fire_at);
  TEST_ASSERT_EQUAL(MotorDir::Brake, r.sm.outputs().motor);  // arm loaded: keep shorted
  r.p.motor_dead = false;
  r.pressTest(2100);  // clear -> DECOCK
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome());
  TEST_ASSERT_EQUAL_INT(0, r.p.launched);
}

// ------------------------------------------------------------- scenario 2 --

// A can that lands while the escapement is still in RELEASE must not trigger the shot before the
// escapement servo is back at HOLD (electronics review finding).
void test_s1_fast_can_waits_for_escapement_hold() {
  PlantParams pp = plant4m();
  pp.can_drop_ms = 40;
  Rig r(pp);
  r.boot();
  r.run(100);
  ackOf(r.sendFire(21), 21);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.fire_at >= 0; }, 6000));
  TEST_ASSERT_TRUE(r.esc_closed_at >= 0);
  TEST_ASSERT_GREATER_OR_EQUAL(400, r.fire_at - r.esc_closed_at);
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 8000));
  TEST_ASSERT_EQUAL_INT(1, r.p.launched);
}

void test_s2_manual_test_button_cycle() {
  Rig r;
  r.boot();
  r.run(50);
  const uint32_t t0 = r.now;
  r.pressTest(120);
  TEST_ASSERT_NOT_EQUAL(State::Idle, r.sm.state());
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r) && r.p.launched == 1; }, 8000));
  TEST_ASSERT_LESS_OR_EQUAL(8000, r.now - t0);
  TEST_ASSERT_GREATER_OR_EQUAL(1500, r.fire_at - r.first_warn);
}

void test_s2_test_button_one_to_five_seconds_does_nothing() {
  Rig r;
  r.boot();
  r.pressTest(2500);
  r.run(500);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  TEST_ASSERT_EQUAL_UINT32(0, r.motorMs());
}

// ------------------------------------------------------------- scenario 3 --

void test_s3_stall_during_cock() {
  Rig r;
  r.boot();
  r.sendFire(1);
  r.run(500);
  TEST_ASSERT_EQUAL(State::Cock, r.sm.state());
  r.p.motor_jammed = true;
  const uint32_t jam_at = r.now;
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 1000));
  std::printf("[stall] detected %u ms after jam (window %u ms, min %u edges)\n", r.now - jam_at,
              cfg::kStallWindowMs, cfg::kStallMinEdges);
  TEST_ASSERT_LESS_OR_EQUAL(cfg::kStallWindowMs + 2 * cfg::kStallSampleMs, r.now - jam_at);
  TEST_ASSERT_EQUAL(FaultCode::Stall, r.sm.fault());
  r.run(2000);
  TEST_ASSERT_FALSE(r.drove_after_fault);
}

void test_s3_stall_during_ring_return() {
  Rig r;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Reset; }, 4000));
  r.run(100);
  r.p.motor_jammed = true;
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 1000));
  TEST_ASSERT_EQUAL(FaultCode::Stall, r.sm.fault());
  TEST_ASSERT_EQUAL_INT(1, r.p.launched);
}

// ------------------------------------------------------------- scenario 4 --

void test_s4_cock_timeout_switch_never_closes() {
  PlantParams pp = plant4m();
  pp.end_stop_extra = 5000;  // encoder keeps counting past the cocked angle
  Rig r(pp);
  r.p.cock_switch_dead = true;
  r.boot();
  const uint32_t t0 = r.now;
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 4000));
  TEST_ASSERT_EQUAL(FaultCode::CockTimeout, r.sm.fault());
  TEST_ASSERT_EQUAL_UINT32(cfg::kCockTimeoutMs, r.now - 1 - t0);  // fault raised in tick now-1
  r.run(500);
  TEST_ASSERT_FALSE(r.drove_after_fault);
}

void test_s4_arm_not_moving() {
  Rig r;
  r.p.arm_home_stuck_low = true;
  r.boot();
  const uint32_t t0 = r.now;
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 2000));
  TEST_ASSERT_EQUAL(FaultCode::ArmNotMoving, r.sm.fault());
  TEST_ASSERT_EQUAL_UINT32(cfg::kArmMoveCheckMs, r.now - 1 - t0);
}

// ------------------------------------------------------------- scenario 5 --

void test_s5_empty_magazine_refused() {
  Rig r;
  r.p.mag = 0;
  r.boot();
  r.run(20);
  const proto::Packet ack = ackOf(r.sendFire(5), 5);
  TEST_ASSERT_EQUAL(AckResult::RefusedMagEmpty, proto::ackResult(ack));
  TEST_ASSERT_TRUE((ack.flags & proto::kFlagRefused) != 0);
  TEST_ASSERT_EQUAL_UINT8(static_cast<uint8_t>(State::Idle), proto::ackState(ack));
  bool beeped = false;
  for (int i = 0; i < 3000; ++i) {
    r.step();
    beeped = beeped || r.sm.outputs().warn;
    TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  }
  TEST_ASSERT_TRUE(beeped);
  TEST_ASSERT_FALSE(r.sm.outputs().warn);  // pattern ends
  TEST_ASSERT_EQUAL_UINT32(0, r.motorMs());
  TEST_ASSERT_TRUE(r.sm.magEmptyFlag());
  // Seq was consumed: a later retry is a duplicate, not a new trigger.
  TEST_ASSERT_EQUAL(AckResult::Duplicate, proto::ackResult(ackOf(r.sendFire(5), 5)));
}

// ------------------------------------------------------------- scenario 6 --

void test_s6_feed_jam_faults_then_decocks() {
  Rig r;
  r.p.esc_jammed = true;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Decock; }, 5000));
  TEST_ASSERT_EQUAL(FaultCode::Feed, r.sm.lastFault());
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome() && r.p.latched);
  TEST_ASSERT_EQUAL_INT(0, r.p.launched);
  TEST_ASSERT_FALSE(r.latch_trip_while_driving);
  TEST_ASSERT_EQUAL(Latch::Hold, r.sm.outputs().latch);
}

void test_s6_magazine_emptied_mid_sequence() {
  Rig r;
  r.boot();
  r.sendFire(1);
  r.run(400);
  r.p.mag = 0;  // cans removed while cocking
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Decock; }, 5000));
  TEST_ASSERT_EQUAL(FaultCode::MagEmpty, r.sm.lastFault());
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome());
  TEST_ASSERT_EQUAL_INT(0, r.p.launched);
}

// ------------------------------------------------------------- scenario 7 --

void test_s7_safety_pin_in_at_trigger_refused() {
  Rig r;
  r.p.safety_pin_in = true;
  r.boot();
  r.run(10);
  TEST_ASSERT_EQUAL(AckResult::RefusedSafetyPin, proto::ackResult(ackOf(r.sendFire(3), 3)));
  r.pressTest(100);
  r.run(2000);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  TEST_ASSERT_EQUAL_UINT32(0, r.motorMs());
}

void test_s7_safety_pin_inserted_during_cock_stops_within_one_tick() {
  Rig r;
  r.boot();
  r.sendFire(1);
  r.run(700);
  TEST_ASSERT_EQUAL(State::Cock, r.sm.state());
  TEST_ASSERT_TRUE(r.driving());
  r.p.safety_pin_in = true;
  r.sm.tick(r.p.inputs(), r.now);  // the very next tick
  TEST_ASSERT_FALSE(r.driving());
  TEST_ASSERT_EQUAL(State::Fault, r.sm.state());
  TEST_ASSERT_EQUAL(FaultCode::SafetyPinInDuringSequence, r.sm.fault());
  g_faults_seen.insert(static_cast<int>(r.sm.fault()));
  r.p.step(r.sm.outputs());
  ++r.now;
  r.run(1000);
  TEST_ASSERT_FALSE(r.drove_after_fault);
  TEST_ASSERT_EQUAL(MotorDir::Brake, r.sm.outputs().motor);  // arm loaded: kept shorted

  // Clear with the pin still in: refused, nothing moves.
  r.pressTest(2100);
  TEST_ASSERT_EQUAL(State::Fault, r.sm.state());
  TEST_ASSERT_EQUAL_STRING("remove safety pin to decock", r.sm.message());
  TEST_ASSERT_FALSE(r.drove_after_fault);
  // Pin out, clear: DECOCK lowers the latched arm.
  r.p.safety_pin_in = false;
  r.pressTest(2100);
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome());
}

void test_s7_safety_pin_inserted_while_holding() {
  Rig r;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Feed || r.sm.state() == State::Armed; }, 4000));
  r.p.safety_pin_in = true;
  r.step();
  TEST_ASSERT_EQUAL(FaultCode::SafetyPinInDuringSequence, r.sm.fault());
  TEST_ASSERT_FALSE(r.driving());
  TEST_ASSERT_EQUAL_INT(0, r.p.launched);
}

void test_s7_safety_pin_inserted_during_decock() {
  Rig r;
  r.p.esc_jammed = true;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Decock; }, 5000));
  r.run(100);
  r.p.safety_pin_in = true;
  r.step();
  TEST_ASSERT_EQUAL(FaultCode::SafetyPinInDuringSequence, r.sm.fault());
  TEST_ASSERT_FALSE(r.driving());
}

// ------------------------------------------------------------- scenario 8 --

void test_s8_latch_fails_to_release() {
  Rig r;
  r.p.latch_jammed = true;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 5000));
  TEST_ASSERT_EQUAL(FaultCode::NoRelease, r.sm.fault());
  TEST_ASSERT_EQUAL(Latch::Hold, r.sm.outputs().latch);
  TEST_ASSERT_GREATER_OR_EQUAL(cfg::kFireReleaseTimeoutMs, r.now - r.fire_at);
  bool warn_seen = false;
  for (int i = 0; i < 1500; ++i) {
    r.step();
    warn_seen = warn_seen || r.sm.outputs().warn;
    TEST_ASSERT_NOT_EQUAL(Latch::Trip, r.sm.outputs().latch);  // no automatic retry
  }
  TEST_ASSERT_TRUE(warn_seen);
  TEST_ASSERT_EQUAL(State::Fault, r.sm.state());
  TEST_ASSERT_EQUAL_INT(0, r.p.launched);
  // Latch freed by hand, clear -> DECOCK lowers the arm with the can.
  r.p.latch_jammed = false;
  r.pressTest(2100);
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome());
  TEST_ASSERT_EQUAL_INT(0, r.p.launched);
}

// ------------------------------------------------------------- scenario 9 --

void test_s9_replay_and_forgery_do_not_trigger() {
  Rig r;
  r.boot(true, 41);
  r.run(10);
  uint8_t pkt[proto::kPacketLen];
  proto::pack(proto::makeFire(42, 3900, false), kKey, pkt);
  ackOf(r.sendRaw(kBtnMac, pkt, sizeof(pkt)), 42);
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r) && r.p.launched == 1; }, 8000));
  const uint32_t motor_after_first = r.motorMs();

  // Same packet again later (captured and replayed): duplicate re-ACK, no trigger.
  r.run(5000);
  const proto::Packet dup = ackOf(r.sendRaw(kBtnMac, pkt, sizeof(pkt)), 42);
  TEST_ASSERT_EQUAL(AckResult::Duplicate, proto::ackResult(dup));
  // Older seq: silently dropped.
  TEST_ASSERT_FALSE(r.sendFire(30).send);
  TEST_ASSERT_FALSE(r.sendFire(41).send);
  // Tampered tag.
  uint8_t bad[proto::kPacketLen];
  proto::pack(proto::makeFire(43, 3900, false), kKey, bad);
  bad[proto::kPacketLen - 2] ^= 0x10;
  TEST_ASSERT_FALSE(r.sendRaw(kBtnMac, bad, sizeof(bad)).send);
  // Tampered seq with the old tag.
  std::memcpy(bad, pkt, sizeof(bad));
  bad[6] = 43;
  TEST_ASSERT_FALSE(r.sendRaw(kBtnMac, bad, sizeof(bad)).send);
  // Wrong key, wrong sender, wrong length.
  TEST_ASSERT_FALSE(r.sendFire(44, kWrongKey).send);
  TEST_ASSERT_FALSE(r.sendFire(45, kKey, kOtherMac).send);
  TEST_ASSERT_FALSE(r.sendRaw(kBtnMac, pkt, sizeof(pkt) - 1).send);
  r.run(3000);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  TEST_ASSERT_EQUAL_UINT32(motor_after_first, r.motorMs());
  TEST_ASSERT_EQUAL_INT(1, r.p.launched);
  TEST_ASSERT_EQUAL_UINT32(42, r.sm.lastSeq());
  TEST_ASSERT_EQUAL_UINT32(1, r.sm.radioStats().duplicates);
  TEST_ASSERT_EQUAL_UINT32(2, r.sm.radioStats().stale);
  TEST_ASSERT_EQUAL_UINT32(3, r.sm.radioStats().bad_tags);
  // The forged packets did not burn sequence numbers: the real 43 still works.
  TEST_ASSERT_EQUAL(AckResult::Accepted, proto::ackResult(ackOf(r.sendFire(43), 43)));
}

void test_s9_trigger_while_busy_is_acked_and_ignored() {
  Rig r;
  r.boot();
  ackOf(r.sendFire(1), 1);
  r.run(300);
  const proto::Packet busy = ackOf(r.sendFire(2), 2);
  TEST_ASSERT_EQUAL(AckResult::Busy, proto::ackResult(busy));
  TEST_ASSERT_EQUAL_UINT8(static_cast<uint8_t>(State::Cock), proto::ackState(busy));
  r.pressTest(100);  // test button while busy: ignored too
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 8000));
  r.run(3000);
  TEST_ASSERT_EQUAL_INT(1, r.p.launched);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
}

void test_s9_unpaired_launcher_ignores_fire() {
  Rig r;
  r.boot(false);
  TEST_ASSERT_FALSE(r.sendFire(1).send);
  r.run(1000);
  TEST_ASSERT_EQUAL_UINT32(0, r.motorMs());
}

// ------------------------------------------------------------ scenario 10 --

void test_s10_cocked_at_boot_then_clear_decocks() {
  Rig r;
  r.p.setCocked();
  r.p.can_in_cup = true;  // a can was loaded when power was lost
  r.p.safety_pin_in = true;
  r.boot();
  TEST_ASSERT_EQUAL(State::Fault, r.sm.state());
  TEST_ASSERT_EQUAL(FaultCode::CockedAtBoot, r.sm.fault());
  r.pressTest(100);         // short press: nothing
  ackOf(r.sendFire(1), 1);  // radio trigger: busy
  r.pressTest(2100);        // clear with pin in: refused
  r.run(2000);
  TEST_ASSERT_EQUAL(State::Fault, r.sm.state());
  TEST_ASSERT_EQUAL_UINT32(0, r.motorMs());

  r.p.safety_pin_in = false;
  r.pressTest(2100);
  TEST_ASSERT_EQUAL(State::Decock, r.sm.state());
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome() && r.p.latched);
  TEST_ASSERT_EQUAL_INT(0, r.p.launched);
  TEST_ASSERT_TRUE(r.p.can_in_cup);  // lowered, not thrown
  TEST_ASSERT_TRUE(r.sm.canPreloaded());

  // Next cycle throws the lowered can without dropping a second one, even with an
  // empty magazine.
  r.p.mag = 0;
  ackOf(r.sendFire(2), 2);
  TEST_ASSERT_EQUAL(State::Warn, r.sm.state());
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r) && r.p.launched == 1; }, 8000));
  TEST_ASSERT_EQUAL_INT(0, r.p.double_can);
  TEST_ASSERT_LESS_THAN(0, r.esc_release_at);  // escapement never opened
}

void test_s10_not_home_at_boot_decocks() {
  Rig r;
  r.p.r = r.p.a = 600;  // power lost mid-cock: arm latched half way
  r.boot();
  TEST_ASSERT_EQUAL(FaultCode::NotHome, r.sm.fault());
  TEST_ASSERT_TRUE(r.sm.requestClear(r.now));
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome());
}

// ------------------------------------------------------------ scenario 11 --

void test_s11_sensor_conflict() {
  Rig r;
  r.boot();
  r.run(100);
  r.p.force_arm_cocked_low = true;
  r.run(cfg::kSensorConflictMs - 5);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());  // short glitch tolerated
  r.run(10);
  TEST_ASSERT_EQUAL(FaultCode::SensorConflict, r.sm.fault());
  TEST_ASSERT_FALSE(r.sm.requestClear(r.now));
  r.p.force_arm_cocked_low = false;
  r.run(10);
  TEST_ASSERT_TRUE(r.sm.requestClear(r.now));
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  TEST_ASSERT_EQUAL_UINT32(0, r.motorMs());
}

void test_s11_sensor_conflict_at_boot() {
  Rig r;
  r.p.force_arm_cocked_low = true;
  r.boot();
  TEST_ASSERT_EQUAL(FaultCode::SensorConflict, r.sm.fault());
}

// ------------------------------------------------------------ scenario 12 --

void test_s12_ring_return_timeout() {
  Rig r;
  r.p.P.reverse_scale = 0.4;  // weak return: 0.67 s / 0.4 = 1.7 s > 1.5 s, encoder still counting
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 6000));
  TEST_ASSERT_EQUAL(FaultCode::RingReturnTimeout, r.sm.fault());
  TEST_ASSERT_EQUAL_INT(1, r.p.launched);
  // Mechanism repaired: clear -> DECOCK parks the ring.
  r.p.P.reverse_scale = 1.0;
  r.pressTest(2100);
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome() && r.p.latched);
}

void test_s12_decock_timeout() {
  Rig r;
  r.p.esc_jammed = true;  // -> FEED fault -> DECOCK
  r.boot();
  r.sendFire(1);
  r.run(300);
  r.p.arm_home_dead = true;  // ...which never sees the arm home
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Decock; }, 5000));
  const uint32_t t0 = r.now;
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 5000));
  TEST_ASSERT_EQUAL(FaultCode::Decock, r.sm.fault());
  TEST_ASSERT_LESS_OR_EQUAL(cfg::kDecockTimeoutMs + 1, r.now - t0);
  bool warn_seen = false;
  for (int i = 0; i < 1200; ++i) {
    r.step();
    warn_seen = warn_seen || r.sm.outputs().warn;
  }
  TEST_ASSERT_TRUE(warn_seen);
  TEST_ASSERT_FALSE(r.drove_after_fault);
}

void test_s12_decock_stall() {
  Rig r;
  r.p.setCocked();
  r.boot();
  r.p.motor_jammed = true;  // gearbox seized: DECOCK sees no encoder edges -> stall
  TEST_ASSERT_TRUE(r.sm.requestDecock(r.now));
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 4000));
  TEST_ASSERT_EQUAL(FaultCode::Decock, r.sm.fault());
}

void test_s12_armed_timeout_decocks() {
  Rig r;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Armed; }, 3000));
  r.p.can_sensor_dead = true;  // can fell out / sensor blind just before FIRE
  r.sm.tick(r.p.inputs(), r.now);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Decock; }, 5000));
  TEST_ASSERT_EQUAL(FaultCode::ArmedTimeout, r.sm.lastFault());
  TEST_ASSERT_TRUE(r.runUntil([&] { return isIdle(r); }, 5000));
  TEST_ASSERT_TRUE(r.p.armHome() && r.p.ringHome());
}

void test_s12_not_home_after_fire() {
  Rig r;
  r.boot();
  r.sendFire(1);
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Reset; }, 5000));
  r.p.arm_home_dead = true;  // switch broken by the shot
  TEST_ASSERT_TRUE(r.runUntil([&] { return r.sm.state() == State::Fault; }, 2000));
  TEST_ASSERT_EQUAL(FaultCode::NotHome, r.sm.fault());
  TEST_ASSERT_EQUAL_INT(1, r.p.launched);
}

// ------------------------------------------------------------ scenario 13 --

void test_s13_pairing_long_press_and_req() {
  Rig r;
  r.boot(false);
  r.p.test_button = true;
  r.run(cfg::kTestBtnPairMs + 30);
  TEST_ASSERT_EQUAL(State::Pairing, r.sm.state());
  r.p.test_button = false;
  r.run(50);
  TEST_ASSERT_EQUAL(State::Pairing, r.sm.state());  // release after long press does not cancel

  // A FIRE during pairing does nothing.
  TEST_ASSERT_FALSE(r.sendFire(1).send);
  // A forged PAIR_REQ (embedded key does not match the tag) is ignored.
  uint8_t req[proto::kPacketLen];
  proto::pack(proto::makePairReq(77, 3800, kKey), kWrongKey, req);
  TEST_ASSERT_FALSE(r.sendRaw(kBtnMac, req, sizeof(req)).send);
  TEST_ASSERT_EQUAL(State::Pairing, r.sm.state());

  proto::pack(proto::makePairReq(77, 3800, kKey), kKey, req);
  const TxFrame ack = r.sendRaw(kBtnMac, req, sizeof(req));
  TEST_ASSERT_TRUE(ack.send);
  proto::Packet pa;
  TEST_ASSERT_EQUAL(proto::ParseResult::Ok, proto::unpack(ack.data, ack.len, kKey, &pa));
  TEST_ASSERT_EQUAL(proto::PacketType::PairAck, pa.type);
  TEST_ASSERT_EQUAL_UINT32(77, pa.seq);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  const PersistRequest pr = r.sm.takePersist();
  TEST_ASSERT_TRUE(pr.pairing);
  TEST_ASSERT_TRUE(r.sm.pairing().valid);
  TEST_ASSERT_EQUAL_HEX8_ARRAY(kBtnMac, r.sm.pairing().mac, 6);
  TEST_ASSERT_EQUAL_HEX8_ARRAY(kKey, r.sm.pairing().key, 16);
  // Triple beep.
  int edges = 0;
  bool last = false;
  for (int i = 0; i < 1000; ++i) {
    r.step();
    if (r.sm.outputs().warn && !last) ++edges;
    last = r.sm.outputs().warn;
  }
  TEST_ASSERT_EQUAL_INT(3, edges);

  // Lost PAIR_ACK: the button repeats the request -> re-ACK, nothing else changes.
  TEST_ASSERT_TRUE(r.sendRaw(kBtnMac, req, sizeof(req)).send);
  TEST_ASSERT_FALSE(r.sm.takePersist().pairing);
  // A different key outside the window is not accepted.
  proto::pack(proto::makePairReq(78, 3800, kWrongKey), kWrongKey, req);
  TEST_ASSERT_FALSE(r.sendRaw(kBtnMac, req, sizeof(req)).send);
  TEST_ASSERT_EQUAL_HEX8_ARRAY(kKey, r.sm.pairing().key, 16);

  // Now paired: FIRE works.
  TEST_ASSERT_EQUAL(AckResult::Accepted, proto::ackResult(ackOf(r.sendFire(1), 1)));
}

void test_s13_pairing_window_expires() {
  Rig r;
  r.boot();
  TEST_ASSERT_TRUE(r.sm.requestPairing(r.now));
  r.run(cfg::kPairWindowMs - 10);
  TEST_ASSERT_EQUAL(State::Pairing, r.sm.state());
  r.run(20);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  TEST_ASSERT_EQUAL_STRING("pairing window expired", r.sm.message());
  TEST_ASSERT_FALSE(r.sm.takePersist().pairing);
}

void test_s13_pairing_cancelled_by_short_press() {
  Rig r;
  r.boot();
  TEST_ASSERT_TRUE(r.sm.requestPairing(r.now));
  r.pressTest(100);
  TEST_ASSERT_EQUAL(State::Idle, r.sm.state());
  TEST_ASSERT_EQUAL_UINT32(0, r.motorMs());
}

// --------------------------------------------------------------- coverage --

void test_every_fault_code_exercised() {
  for (int f = 1; f < static_cast<int>(FaultCode::Count); ++f) {
    char msg[96];
    std::snprintf(msg, sizeof(msg), "fault %s never exercised", faultName(static_cast<FaultCode>(f)));
    TEST_ASSERT_TRUE_MESSAGE(g_faults_seen.count(f) == 1, msg);
  }
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_s1_nominal_cycle_from_button_packet_4m);
  RUN_TEST(test_s1_nominal_cycle_from_button_packet_5m);
  RUN_TEST(test_s1_two_cycles_back_to_back);
  RUN_TEST(test_s1_hold_against_load_while_waiting);
  RUN_TEST(test_s1_hold_lost_when_motor_cannot_hold);
  RUN_TEST(test_s1_fast_can_waits_for_escapement_hold);
  RUN_TEST(test_s2_manual_test_button_cycle);
  RUN_TEST(test_s2_test_button_one_to_five_seconds_does_nothing);
  RUN_TEST(test_s3_stall_during_cock);
  RUN_TEST(test_s3_stall_during_ring_return);
  RUN_TEST(test_s4_cock_timeout_switch_never_closes);
  RUN_TEST(test_s4_arm_not_moving);
  RUN_TEST(test_s5_empty_magazine_refused);
  RUN_TEST(test_s6_feed_jam_faults_then_decocks);
  RUN_TEST(test_s6_magazine_emptied_mid_sequence);
  RUN_TEST(test_s7_safety_pin_in_at_trigger_refused);
  RUN_TEST(test_s7_safety_pin_inserted_during_cock_stops_within_one_tick);
  RUN_TEST(test_s7_safety_pin_inserted_while_holding);
  RUN_TEST(test_s7_safety_pin_inserted_during_decock);
  RUN_TEST(test_s8_latch_fails_to_release);
  RUN_TEST(test_s9_replay_and_forgery_do_not_trigger);
  RUN_TEST(test_s9_trigger_while_busy_is_acked_and_ignored);
  RUN_TEST(test_s9_unpaired_launcher_ignores_fire);
  RUN_TEST(test_s10_cocked_at_boot_then_clear_decocks);
  RUN_TEST(test_s10_not_home_at_boot_decocks);
  RUN_TEST(test_s11_sensor_conflict);
  RUN_TEST(test_s11_sensor_conflict_at_boot);
  RUN_TEST(test_s12_ring_return_timeout);
  RUN_TEST(test_s12_decock_timeout);
  RUN_TEST(test_s12_decock_stall);
  RUN_TEST(test_s12_armed_timeout_decocks);
  RUN_TEST(test_s12_not_home_after_fire);
  RUN_TEST(test_s13_pairing_long_press_and_req);
  RUN_TEST(test_s13_pairing_window_expires);
  RUN_TEST(test_s13_pairing_cancelled_by_short_press);
  RUN_TEST(test_every_fault_code_exercised);  // keep last
  return UNITY_END();
}
