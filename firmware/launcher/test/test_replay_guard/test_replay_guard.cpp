#include <unity.h>

#include "replay_guard.h"

using beer::ReplayGuard;
using beer::SeqVerdict;

void setUp() {}
void tearDown() {}

void test_fresh_guard_rejects_zero_accepts_one() {
  ReplayGuard g;
  TEST_ASSERT_EQUAL(SeqVerdict::Stale, g.check(0));
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.checkAndAccept(1));
  TEST_ASSERT_EQUAL_UINT32(1, g.last());
}

void test_increasing_accepted_and_gaps_allowed() {
  ReplayGuard g(16);
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.checkAndAccept(17));
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.checkAndAccept(18));
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.checkAndAccept(40));  // button cold-boot jump
  TEST_ASSERT_EQUAL_UINT32(40, g.last());
}

void test_equal_is_duplicate_and_does_not_advance() {
  ReplayGuard g(100);
  TEST_ASSERT_EQUAL(SeqVerdict::Duplicate, g.checkAndAccept(100));
  TEST_ASSERT_EQUAL(SeqVerdict::Duplicate, g.checkAndAccept(100));
  TEST_ASSERT_EQUAL_UINT32(100, g.last());
}

void test_older_is_stale() {
  ReplayGuard g(100);
  TEST_ASSERT_EQUAL(SeqVerdict::Stale, g.checkAndAccept(99));
  TEST_ASSERT_EQUAL(SeqVerdict::Stale, g.checkAndAccept(1));
  TEST_ASSERT_EQUAL(SeqVerdict::Stale, g.checkAndAccept(0));
  TEST_ASSERT_EQUAL_UINT32(100, g.last());
}

void test_retry_dedup_sequence() {
  // Button sends 5, ACK lost, retries 5 twice, then a new press 6.
  ReplayGuard g(4);
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.checkAndAccept(5));
  TEST_ASSERT_EQUAL(SeqVerdict::Duplicate, g.checkAndAccept(5));
  TEST_ASSERT_EQUAL(SeqVerdict::Duplicate, g.checkAndAccept(5));
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.checkAndAccept(6));
  TEST_ASSERT_EQUAL(SeqVerdict::Stale, g.checkAndAccept(5));  // late retry of the old press
}

void test_check_has_no_side_effect_and_reset() {
  ReplayGuard g(10);
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.check(11));
  TEST_ASSERT_EQUAL_UINT32(10, g.last());
  g.reset();
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.check(1));
  TEST_ASSERT_EQUAL(SeqVerdict::Fresh, g.check(0xFFFFFFFFu));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_fresh_guard_rejects_zero_accepts_one);
  RUN_TEST(test_increasing_accepted_and_gaps_allowed);
  RUN_TEST(test_equal_is_duplicate_and_does_not_advance);
  RUN_TEST(test_older_is_stale);
  RUN_TEST(test_retry_dedup_sequence);
  RUN_TEST(test_check_has_no_side_effect_and_reset);
  return UNITY_END();
}
