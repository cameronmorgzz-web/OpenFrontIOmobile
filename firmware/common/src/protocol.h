// Beer Button <-> Launcher packet format (ESP-NOW payload).
//
//   off len field
//    0   4  magic 'B','E','E','R'
//    4   1  version = 1
//    5   1  type (PacketType)
//    6   4  seq        (u32 LE)
//   10   2  batt_mV    (u16 LE)
//   12   1  flags
//   13  16  payload
//   29   8  tag = first 8 bytes of HMAC-SHA256(key, bytes 0..28)
//   ---------
//   37 bytes total
//
// PAIR_REQ carries the button's new 16-byte key in the payload and is signed with
// that same key: it only proves the sender holds the key it is handing over. Pairing
// is therefore only as secure as the 30 s pairing window and physical proximity.
// Every other packet is signed with the paired key; the launcher signs its ACKs so
// the button cannot be fooled by a fake ACK.
#pragma once

#include <cstddef>
#include <cstdint>

namespace beer {
namespace proto {

constexpr uint8_t kMagic[4] = {'B', 'E', 'E', 'R'};
constexpr uint8_t kVersion = 1;
constexpr size_t kKeyLen = 16;
constexpr size_t kPayloadLen = 16;
constexpr size_t kTagLen = 8;
constexpr size_t kSignedLen = 4 + 1 + 1 + 4 + 2 + 1 + kPayloadLen;  // 29
constexpr size_t kPacketLen = kSignedLen + kTagLen;                  // 37
constexpr size_t kMacLen = 6;

enum class PacketType : uint8_t {
  Fire = 1,
  PairReq = 2,
  PairAck = 3,
  Ack = 4,
  Status = 5,
};

// ACK payload layout: [0] launcher state code, [1..4] acked seq (LE),
// [5] AckResult, [6] fault code.
enum class AckResult : uint8_t {
  Accepted = 0,      // sequence started
  Duplicate = 1,     // same seq as last accepted: re-ACK, nothing done
  Busy = 2,          // launcher not IDLE: trigger ignored
  RefusedMagEmpty = 3,
  RefusedSafetyPin = 4,
  RefusedNotReady = 5,
};

// flags bits
constexpr uint8_t kFlagLowBattery = 0x01;  // button -> launcher
constexpr uint8_t kFlagRefused = 0x02;     // launcher -> button
constexpr uint8_t kFlagFault = 0x04;       // launcher -> button

struct Packet {
  PacketType type = PacketType::Fire;
  uint32_t seq = 0;
  uint16_t batt_mv = 0;
  uint8_t flags = 0;
  uint8_t payload[kPayloadLen] = {};
};

enum class ParseResult : uint8_t {
  Ok = 0,
  BadLength,
  BadMagic,
  BadVersion,
  BadType,
  BadTag,
};

const char* parseResultName(ParseResult r);

// Serialises p and appends the truncated HMAC tag computed with key.
void pack(const Packet& p, const uint8_t key[kKeyLen], uint8_t out[kPacketLen]);

// Checks length/magic/version/type only (no tag). Use to route a frame.
ParseResult peek(const uint8_t* buf, size_t len, PacketType* type_out);

// Full check including the tag with the given key. out is only written on Ok.
ParseResult unpack(const uint8_t* buf, size_t len, const uint8_t key[kKeyLen], Packet* out);

// PAIR_REQ: verifies the tag with the key embedded in its own payload.
ParseResult unpackPairReq(const uint8_t* buf, size_t len, Packet* out);

// Builders
Packet makeFire(uint32_t seq, uint16_t batt_mv, bool low_batt);
Packet makePairReq(uint32_t seq, uint16_t batt_mv, const uint8_t key[kKeyLen]);
Packet makePairAck(uint32_t seq);
Packet makeAck(uint32_t acked_seq, uint8_t state_code, AckResult result, uint8_t fault_code);

// ACK payload accessors
uint32_t ackedSeq(const Packet& ack);
uint8_t ackState(const Packet& ack);
AckResult ackResult(const Packet& ack);
uint8_t ackFault(const Packet& ack);

void putU32(uint8_t* p, uint32_t v);
uint32_t getU32(const uint8_t* p);

}  // namespace proto
}  // namespace beer
