// Packet pack/unpack, HMAC tag verification and rejection rules.
#include <unity.h>

#include <cstring>

#include "protocol.h"

using namespace beer::proto;

static const uint8_t kKey[kKeyLen] = {0x10, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x87,
                                      0x98, 0xA9, 0xBA, 0xCB, 0xDC, 0xED, 0xFE, 0x0F};
static const uint8_t kOtherKey[kKeyLen] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};

void setUp() {}
void tearDown() {}

void test_sizes() {
  TEST_ASSERT_EQUAL(29, kSignedLen);
  TEST_ASSERT_EQUAL(37, kPacketLen);
}

void test_fire_roundtrip_and_layout() {
  uint8_t buf[kPacketLen];
  pack(makeFire(0x01020304u, 3712, true), kKey, buf);
  // little-endian, packed layout
  TEST_ASSERT_EQUAL_HEX8_ARRAY("BEER", buf, 4);
  TEST_ASSERT_EQUAL_UINT8(1, buf[4]);
  TEST_ASSERT_EQUAL_UINT8(1, buf[5]);
  const uint8_t seq_le[4] = {0x04, 0x03, 0x02, 0x01};
  TEST_ASSERT_EQUAL_HEX8_ARRAY(seq_le, buf + 6, 4);
  TEST_ASSERT_EQUAL_UINT8(3712 & 0xFF, buf[10]);
  TEST_ASSERT_EQUAL_UINT8(3712 >> 8, buf[11]);
  TEST_ASSERT_EQUAL_UINT8(kFlagLowBattery, buf[12]);

  Packet p;
  TEST_ASSERT_EQUAL(ParseResult::Ok, unpack(buf, sizeof(buf), kKey, &p));
  TEST_ASSERT_EQUAL(PacketType::Fire, p.type);
  TEST_ASSERT_EQUAL_UINT32(0x01020304u, p.seq);
  TEST_ASSERT_EQUAL_UINT16(3712, p.batt_mv);
  TEST_ASSERT_EQUAL_UINT8(kFlagLowBattery, p.flags);
  for (size_t i = 0; i < kPayloadLen; ++i) TEST_ASSERT_EQUAL_UINT8(0, p.payload[i]);
}

void test_every_tampered_byte_rejected() {
  uint8_t buf[kPacketLen];
  pack(makeFire(77, 3900, false), kKey, buf);
  for (size_t i = 0; i < kPacketLen; ++i) {
    for (uint8_t bit = 0; bit < 8; ++bit) {
      uint8_t t[kPacketLen];
      std::memcpy(t, buf, sizeof(t));
      t[i] = static_cast<uint8_t>(t[i] ^ (1u << bit));
      TEST_ASSERT_NOT_EQUAL(ParseResult::Ok, unpack(t, sizeof(t), kKey, nullptr));
    }
  }
}

void test_tag_tamper_reports_bad_tag() {
  uint8_t buf[kPacketLen];
  pack(makeFire(5, 3900, false), kKey, buf);
  buf[kPacketLen - 1] ^= 0x01;
  TEST_ASSERT_EQUAL(ParseResult::BadTag, unpack(buf, sizeof(buf), kKey, nullptr));
  buf[kPacketLen - 1] ^= 0x01;
  buf[6] ^= 0x01;  // seq changed, tag kept
  TEST_ASSERT_EQUAL(ParseResult::BadTag, unpack(buf, sizeof(buf), kKey, nullptr));
}

void test_wrong_key_rejected() {
  uint8_t buf[kPacketLen];
  pack(makeFire(5, 3900, false), kKey, buf);
  TEST_ASSERT_EQUAL(ParseResult::BadTag, unpack(buf, sizeof(buf), kOtherKey, nullptr));
}

void test_wrong_magic_version_type_length() {
  uint8_t buf[kPacketLen + 1];
  pack(makeFire(5, 3900, false), kKey, buf);
  uint8_t t[kPacketLen + 1];

  std::memcpy(t, buf, kPacketLen);
  t[0] = 'X';
  TEST_ASSERT_EQUAL(ParseResult::BadMagic, unpack(t, kPacketLen, kKey, nullptr));

  std::memcpy(t, buf, kPacketLen);
  t[4] = 2;
  TEST_ASSERT_EQUAL(ParseResult::BadVersion, unpack(t, kPacketLen, kKey, nullptr));

  std::memcpy(t, buf, kPacketLen);
  t[5] = 0;
  TEST_ASSERT_EQUAL(ParseResult::BadType, unpack(t, kPacketLen, kKey, nullptr));
  t[5] = 6;
  TEST_ASSERT_EQUAL(ParseResult::BadType, unpack(t, kPacketLen, kKey, nullptr));

  TEST_ASSERT_EQUAL(ParseResult::BadLength, unpack(buf, kPacketLen - 1, kKey, nullptr));
  TEST_ASSERT_EQUAL(ParseResult::BadLength, unpack(buf, kPacketLen + 1, kKey, nullptr));
  TEST_ASSERT_EQUAL(ParseResult::BadLength, unpack(buf, 0, kKey, nullptr));
  TEST_ASSERT_EQUAL(ParseResult::BadLength, unpack(nullptr, kPacketLen, kKey, nullptr));
}

void test_unpack_does_not_write_output_on_failure() {
  uint8_t buf[kPacketLen];
  pack(makeFire(5, 3900, false), kKey, buf);
  Packet p;
  p.seq = 0xDEADBEEF;
  TEST_ASSERT_EQUAL(ParseResult::BadTag, unpack(buf, sizeof(buf), kOtherKey, &p));
  TEST_ASSERT_EQUAL_UINT32(0xDEADBEEF, p.seq);
}

void test_pair_req_self_signed() {
  uint8_t buf[kPacketLen];
  pack(makePairReq(9, 4000, kOtherKey), kOtherKey, buf);
  Packet p;
  TEST_ASSERT_EQUAL(ParseResult::Ok, unpackPairReq(buf, sizeof(buf), &p));
  TEST_ASSERT_EQUAL_HEX8_ARRAY(kOtherKey, p.payload, kKeyLen);

  // Signed with a different key than the one it carries -> rejected.
  pack(makePairReq(9, 4000, kOtherKey), kKey, buf);
  TEST_ASSERT_EQUAL(ParseResult::BadTag, unpackPairReq(buf, sizeof(buf), &p));

  // Swapping the embedded key without re-signing -> rejected.
  pack(makePairReq(9, 4000, kOtherKey), kOtherKey, buf);
  buf[13] ^= 0xFF;
  TEST_ASSERT_EQUAL(ParseResult::BadTag, unpackPairReq(buf, sizeof(buf), &p));

  // A FIRE is not a PAIR_REQ.
  pack(makeFire(1, 0, false), kKey, buf);
  TEST_ASSERT_EQUAL(ParseResult::BadType, unpackPairReq(buf, sizeof(buf), &p));
}

void test_ack_payload() {
  uint8_t buf[kPacketLen];
  pack(makeAck(0xA1B2C3D4u, 3, AckResult::RefusedMagEmpty, 0), kKey, buf);
  Packet p;
  TEST_ASSERT_EQUAL(ParseResult::Ok, unpack(buf, sizeof(buf), kKey, &p));
  TEST_ASSERT_EQUAL(PacketType::Ack, p.type);
  TEST_ASSERT_EQUAL_UINT8(3, ackState(p));
  TEST_ASSERT_EQUAL_UINT32(0xA1B2C3D4u, ackedSeq(p));
  TEST_ASSERT_EQUAL(AckResult::RefusedMagEmpty, ackResult(p));
  TEST_ASSERT_TRUE((p.flags & kFlagRefused) != 0);
  TEST_ASSERT_EQUAL_UINT8(0xD4, buf[13 + 1]);  // payload[1..4] = acked seq LE
  TEST_ASSERT_EQUAL_UINT8(0xA1, buf[13 + 4]);
}

void test_peek_routes_without_key() {
  uint8_t buf[kPacketLen];
  pack(makePairAck(3), kKey, buf);
  PacketType t = PacketType::Fire;
  TEST_ASSERT_EQUAL(ParseResult::Ok, peek(buf, sizeof(buf), &t));
  TEST_ASSERT_EQUAL(PacketType::PairAck, t);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_sizes);
  RUN_TEST(test_fire_roundtrip_and_layout);
  RUN_TEST(test_every_tampered_byte_rejected);
  RUN_TEST(test_tag_tamper_reports_bad_tag);
  RUN_TEST(test_wrong_key_rejected);
  RUN_TEST(test_wrong_magic_version_type_length);
  RUN_TEST(test_unpack_does_not_write_output_on_failure);
  RUN_TEST(test_pair_req_self_signed);
  RUN_TEST(test_ack_payload);
  RUN_TEST(test_peek_routes_without_key);
  return UNITY_END();
}
