// Button-side radio checks against the real launcher logic: the button only
// believes ACKs signed with its key for the seq it just sent.
#include <unity.h>

#include <cstring>

#include "button_logic.h"
#include "launcher_sm.h"
#include "protocol.h"

using namespace beer;

static const uint8_t kBtnMac[6] = {0x34, 0x85, 0x18, 0x01, 0x02, 0x03};
static const uint8_t kKey[16] = {9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 11, 22, 33, 44, 55, 66};
static const uint8_t kEvilKey[16] = {0};

void setUp() {}
void tearDown() {}

static launcher::LauncherSM pairedLauncher() {
  launcher::LauncherSM sm;
  launcher::Inputs in;
  in.arm_home = true;
  in.ring_home = true;
  launcher::PairingRecord pr;
  pr.valid = true;
  std::memcpy(pr.mac, kBtnMac, 6);
  std::memcpy(pr.key, kKey, 16);
  sm.begin(in, 0, pr, 0);
  sm.tick(in, 1);
  return sm;
}

void test_genuine_ack_accepted() {
  launcher::LauncherSM sm = pairedLauncher();
  uint8_t fire[proto::kPacketLen];
  proto::pack(proto::makeFire(17, 3900, false), kKey, fire);
  launcher::TxFrame tx;
  sm.onPacket(kBtnMac, fire, sizeof(fire), 2, &tx);
  TEST_ASSERT_TRUE(tx.send);
  proto::Packet ack;
  TEST_ASSERT_TRUE(btn::isAckFor(tx.data, tx.len, kKey, 17, &ack));
  TEST_ASSERT_EQUAL(proto::AckResult::Accepted, proto::ackResult(ack));
}

void test_ack_for_other_seq_rejected() {
  uint8_t buf[proto::kPacketLen];
  proto::pack(proto::makeAck(16, 0, proto::AckResult::Accepted, 0), kKey, buf);
  TEST_ASSERT_FALSE(btn::isAckFor(buf, sizeof(buf), kKey, 17));  // replayed old ACK
}

void test_forged_ack_rejected() {
  uint8_t buf[proto::kPacketLen];
  proto::pack(proto::makeAck(17, 0, proto::AckResult::Accepted, 0), kEvilKey, buf);
  TEST_ASSERT_FALSE(btn::isAckFor(buf, sizeof(buf), kKey, 17));
  proto::pack(proto::makeAck(17, 0, proto::AckResult::Accepted, 0), kKey, buf);
  buf[20] ^= 1;
  TEST_ASSERT_FALSE(btn::isAckFor(buf, sizeof(buf), kKey, 17));
  // A PAIR_ACK is not an ACK.
  proto::pack(proto::makePairAck(17), kKey, buf);
  TEST_ASSERT_FALSE(btn::isAckFor(buf, sizeof(buf), kKey, 17));
}

void test_pair_ack_must_be_signed_with_new_key() {
  launcher::LauncherSM sm = pairedLauncher();
  TEST_ASSERT_TRUE(sm.requestPairing(5));
  const uint8_t new_key[16] = {0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
                               0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF};
  uint8_t req[proto::kPacketLen];
  proto::pack(proto::makePairReq(200, 3800, new_key), new_key, req);
  launcher::TxFrame tx;
  sm.onPacket(kBtnMac, req, sizeof(req), 6, &tx);
  TEST_ASSERT_TRUE(tx.send);
  TEST_ASSERT_TRUE(btn::isPairAckFor(tx.data, tx.len, new_key, 200));
  TEST_ASSERT_FALSE(btn::isPairAckFor(tx.data, tx.len, kKey, 200));     // old key
  TEST_ASSERT_FALSE(btn::isPairAckFor(tx.data, tx.len, new_key, 199));  // other request
  // After re-pairing, packets with the old key no longer work.
  uint8_t fire[proto::kPacketLen];
  proto::pack(proto::makeFire(300, 3900, false), kKey, fire);
  sm.onPacket(kBtnMac, fire, sizeof(fire), 7, &tx);
  TEST_ASSERT_FALSE(tx.send);
}

void test_retry_with_same_seq_gets_duplicate_ack() {
  launcher::LauncherSM sm = pairedLauncher();
  uint8_t fire[proto::kPacketLen];
  proto::pack(proto::makeFire(17, 3900, false), kKey, fire);
  launcher::TxFrame tx;
  sm.onPacket(kBtnMac, fire, sizeof(fire), 2, &tx);  // first ACK "lost"
  sm.onPacket(kBtnMac, fire, sizeof(fire), 120, &tx);
  proto::Packet ack;
  TEST_ASSERT_TRUE(btn::isAckFor(tx.data, tx.len, kKey, 17, &ack));
  TEST_ASSERT_EQUAL(proto::AckResult::Duplicate, proto::ackResult(ack));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_genuine_ack_accepted);
  RUN_TEST(test_ack_for_other_seq_rejected);
  RUN_TEST(test_forged_ack_rejected);
  RUN_TEST(test_pair_ack_must_be_signed_with_new_key);
  RUN_TEST(test_retry_with_same_seq_gets_duplicate_ack);
  return UNITY_END();
}
