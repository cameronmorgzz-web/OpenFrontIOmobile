// Beer Button decision logic: battery hysteresis, press timing, retry policy,
// sequence persistence, pairing schedule, feedback.
#include <unity.h>

#include "button_logic.h"
#include "config.h"

using namespace beer;
using namespace beer::btn;

void setUp() {}
void tearDown() {}

void test_low_battery_hysteresis() {
  bool low = false;
  low = updateLowBattery(low, 3700);
  TEST_ASSERT_FALSE(low);
  low = updateLowBattery(low, 3451);
  TEST_ASSERT_FALSE(low);
  low = updateLowBattery(low, 3449);
  TEST_ASSERT_TRUE(low);
  // Recovers only at >= 3.60 V, not at 3.45..3.59 (load/temperature bounce).
  low = updateLowBattery(low, 3500);
  TEST_ASSERT_TRUE(low);
  low = updateLowBattery(low, 3599);
  TEST_ASSERT_TRUE(low);
  low = updateLowBattery(low, 3600);
  TEST_ASSERT_FALSE(low);
  low = updateLowBattery(low, 3500);
  TEST_ASSERT_FALSE(low);
}

void test_low_battery_noisy_readings_do_not_toggle() {
  bool low = true;
  int toggles = 0;
  const uint16_t readings[] = {3440, 3460, 3455, 3520, 3580, 3470, 3590, 3450};
  for (uint16_t mv : readings) {
    const bool n = updateLowBattery(low, mv);
    if (n != low) ++toggles;
    low = n;
  }
  TEST_ASSERT_EQUAL_INT(0, toggles);
}

void test_battery_divider_conversion() {
  TEST_ASSERT_EQUAL_UINT16(3700, batteryMvFromAdc(1850u * 8u, 8));
  TEST_ASSERT_EQUAL_UINT16(0, batteryMvFromAdc(1234, 0));
  TEST_ASSERT_EQUAL_UINT16(0xFFFF, batteryMvFromAdc(40000u * 4u, 4));
}

void test_boot_sequence_warm_and_cold() {
  TEST_ASSERT_EQUAL_UINT32(120, bootSequence(true, 120, 119));
  TEST_ASSERT_EQUAL_UINT32(130, bootSequence(true, 120, 130));  // never backwards
  TEST_ASSERT_EQUAL_UINT32(120 + cfg::kBtnSeqColdBootJump, bootSequence(false, 0, 120));
  TEST_ASSERT_EQUAL_UINT32(cfg::kBtnSeqColdBootJump, bootSequence(false, 0, 0));  // factory fresh
}

void test_long_press_detection() {
  PressTracker t;
  t.begin(true, 0);  // woke up with the switch held
  TEST_ASSERT_EQUAL(PressTracker::Event::None, t.update(true, 4999));
  TEST_ASSERT_EQUAL(PressTracker::Event::LongPress, t.update(true, 5000));
  TEST_ASSERT_EQUAL(PressTracker::Event::None, t.update(true, 6000));  // reported once
  TEST_ASSERT_EQUAL(PressTracker::Event::Released, t.update(false, 6100));
  TEST_ASSERT_EQUAL_UINT32(6100, t.heldMs(7000));
}

void test_short_press_is_not_long() {
  PressTracker t;
  t.begin(true, 1000);
  TEST_ASSERT_EQUAL(PressTracker::Event::None, t.update(true, 1150));
  TEST_ASSERT_EQUAL(PressTracker::Event::Released, t.update(false, 1200));
  TEST_ASSERT_FALSE(t.longReported());
  TEST_ASSERT_EQUAL_UINT32(200, t.heldMs(5000));
  // New press later starts a fresh timer.
  TEST_ASSERT_EQUAL(PressTracker::Event::None, t.update(true, 9000));
  TEST_ASSERT_EQUAL(PressTracker::Event::None, t.update(true, 13999));
  TEST_ASSERT_EQUAL(PressTracker::Event::LongPress, t.update(true, 14000));
}

void test_retry_policy_ack_on_first_try() {
  RetryPolicy r;
  r.start(0);
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Send, r.poll(0, false));
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Wait, r.poll(10, false));
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Acked, r.poll(15, true));
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Acked, r.poll(500, false));
  TEST_ASSERT_EQUAL_UINT8(1, r.attempts());
}

void test_retry_policy_gives_up_after_three_retries() {
  RetryPolicy r;  // 1 + 3 retries, 120 ms each
  r.start(0);
  int sends = 0;
  uint32_t gave_up_at = 0;
  for (uint32_t t = 0; t < 2000; ++t) {
    const RetryPolicy::Action a = r.poll(t, false);
    if (a == RetryPolicy::Action::Send) ++sends;
    if (a == RetryPolicy::Action::GiveUp) {
      gave_up_at = t;
      break;
    }
  }
  TEST_ASSERT_EQUAL_INT(4, sends);
  TEST_ASSERT_EQUAL_UINT32(4 * cfg::kBtnAckWaitMs, gave_up_at);
  TEST_ASSERT_EQUAL_UINT32(480, r.worstCaseMs());
}

void test_retry_policy_ack_on_retry() {
  RetryPolicy r;
  r.start(0);
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Send, r.poll(0, false));
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Wait, r.poll(119, false));
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Send, r.poll(120, false));
  TEST_ASSERT_EQUAL(RetryPolicy::Action::Acked, r.poll(130, true));
  TEST_ASSERT_EQUAL_UINT8(2, r.attempts());
}

void test_pairing_schedule() {
  PairingSchedule s;
  s.start(0);
  int reqs = 0;
  uint32_t t = 0;
  for (; t < 40000; ++t) {
    const PairingSchedule::Action a = s.poll(t);
    if (a == PairingSchedule::Action::SendReq) ++reqs;
    if (a == PairingSchedule::Action::Timeout) break;
  }
  TEST_ASSERT_EQUAL_UINT32(cfg::kBtnPairWindowMs, t);
  TEST_ASSERT_EQUAL_INT(cfg::kBtnPairWindowMs / cfg::kBtnPairReqIntervalMs, reqs);
}

void test_feedback_patterns() {
  Feedback f = decideFeedback(true, false);
  TEST_ASSERT_EQUAL_UINT32(80, f.haptic_ms);
  TEST_ASSERT_EQUAL_UINT8(0, f.nack_blinks);
  TEST_ASSERT_EQUAL_UINT8(0, f.lowbatt_blinks);
  f = decideFeedback(false, false);
  TEST_ASSERT_EQUAL_UINT32(0, f.haptic_ms);
  TEST_ASSERT_EQUAL_UINT8(3, f.nack_blinks);
  f = decideFeedback(true, true);
  TEST_ASSERT_EQUAL_UINT32(80, f.haptic_ms);
  TEST_ASSERT_EQUAL_UINT8(5, f.lowbatt_blinks);
  f = decideFeedback(false, true);
  TEST_ASSERT_EQUAL_UINT8(3, f.nack_blinks);
  TEST_ASSERT_EQUAL_UINT8(5, f.lowbatt_blinks);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_low_battery_hysteresis);
  RUN_TEST(test_low_battery_noisy_readings_do_not_toggle);
  RUN_TEST(test_battery_divider_conversion);
  RUN_TEST(test_boot_sequence_warm_and_cold);
  RUN_TEST(test_long_press_detection);
  RUN_TEST(test_short_press_is_not_long);
  RUN_TEST(test_retry_policy_ack_on_first_try);
  RUN_TEST(test_retry_policy_gives_up_after_three_retries);
  RUN_TEST(test_retry_policy_ack_on_retry);
  RUN_TEST(test_pairing_schedule);
  RUN_TEST(test_feedback_patterns);
  return UNITY_END();
}
