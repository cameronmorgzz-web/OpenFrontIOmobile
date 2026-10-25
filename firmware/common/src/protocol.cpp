#include "protocol.h"

#include <cstring>

#include "hmac.h"

namespace beer {
namespace proto {
namespace {

constexpr size_t kOffMagic = 0;
constexpr size_t kOffVersion = 4;
constexpr size_t kOffType = 5;
constexpr size_t kOffSeq = 6;
constexpr size_t kOffBatt = 10;
constexpr size_t kOffFlags = 12;
constexpr size_t kOffPayload = 13;
constexpr size_t kOffTag = kSignedLen;

void computeTag(const uint8_t* signed_bytes, const uint8_t key[kKeyLen], uint8_t tag[kTagLen]) {
  uint8_t mac[Sha256::kDigestLen];
  hmacSha256(key, kKeyLen, signed_bytes, kSignedLen, mac);
  std::memcpy(tag, mac, kTagLen);
}

bool validType(uint8_t t) { return t >= 1 && t <= 5; }

void decode(const uint8_t* buf, Packet* out) {
  out->type = static_cast<PacketType>(buf[kOffType]);
  out->seq = getU32(buf + kOffSeq);
  out->batt_mv = static_cast<uint16_t>(buf[kOffBatt] | (buf[kOffBatt + 1] << 8));
  out->flags = buf[kOffFlags];
  std::memcpy(out->payload, buf + kOffPayload, kPayloadLen);
}

ParseResult verifyWith(const uint8_t* buf, const uint8_t key[kKeyLen]) {
  uint8_t tag[kTagLen];
  computeTag(buf, key, tag);
  return constantTimeEqual(tag, buf + kOffTag, kTagLen) ? ParseResult::Ok : ParseResult::BadTag;
}

}  // namespace

void putU32(uint8_t* p, uint32_t v) {
  p[0] = static_cast<uint8_t>(v);
  p[1] = static_cast<uint8_t>(v >> 8);
  p[2] = static_cast<uint8_t>(v >> 16);
  p[3] = static_cast<uint8_t>(v >> 24);
}

uint32_t getU32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

const char* parseResultName(ParseResult r) {
  switch (r) {
    case ParseResult::Ok: return "ok";
    case ParseResult::BadLength: return "bad-length";
    case ParseResult::BadMagic: return "bad-magic";
    case ParseResult::BadVersion: return "bad-version";
    case ParseResult::BadType: return "bad-type";
    case ParseResult::BadTag: return "bad-tag";
  }
  return "?";
}

void pack(const Packet& p, const uint8_t key[kKeyLen], uint8_t out[kPacketLen]) {
  std::memcpy(out + kOffMagic, kMagic, 4);
  out[kOffVersion] = kVersion;
  out[kOffType] = static_cast<uint8_t>(p.type);
  putU32(out + kOffSeq, p.seq);
  out[kOffBatt] = static_cast<uint8_t>(p.batt_mv);
  out[kOffBatt + 1] = static_cast<uint8_t>(p.batt_mv >> 8);
  out[kOffFlags] = p.flags;
  std::memcpy(out + kOffPayload, p.payload, kPayloadLen);
  computeTag(out, key, out + kOffTag);
}

ParseResult peek(const uint8_t* buf, size_t len, PacketType* type_out) {
  if (buf == nullptr || len != kPacketLen) return ParseResult::BadLength;
  if (std::memcmp(buf + kOffMagic, kMagic, 4) != 0) return ParseResult::BadMagic;
  if (buf[kOffVersion] != kVersion) return ParseResult::BadVersion;
  if (!validType(buf[kOffType])) return ParseResult::BadType;
  if (type_out != nullptr) *type_out = static_cast<PacketType>(buf[kOffType]);
  return ParseResult::Ok;
}

ParseResult unpack(const uint8_t* buf, size_t len, const uint8_t key[kKeyLen], Packet* out) {
  const ParseResult hdr = peek(buf, len, nullptr);
  if (hdr != ParseResult::Ok) return hdr;
  const ParseResult tag = verifyWith(buf, key);
  if (tag != ParseResult::Ok) return tag;
  if (out != nullptr) decode(buf, out);
  return ParseResult::Ok;
}

ParseResult unpackPairReq(const uint8_t* buf, size_t len, Packet* out) {
  PacketType t;
  const ParseResult hdr = peek(buf, len, &t);
  if (hdr != ParseResult::Ok) return hdr;
  if (t != PacketType::PairReq) return ParseResult::BadType;
  return unpack(buf, len, buf + kOffPayload, out);
}

Packet makeFire(uint32_t seq, uint16_t batt_mv, bool low_batt) {
  Packet p;
  p.type = PacketType::Fire;
  p.seq = seq;
  p.batt_mv = batt_mv;
  p.flags = low_batt ? kFlagLowBattery : 0;
  return p;
}

Packet makePairReq(uint32_t seq, uint16_t batt_mv, const uint8_t key[kKeyLen]) {
  Packet p;
  p.type = PacketType::PairReq;
  p.seq = seq;
  p.batt_mv = batt_mv;
  std::memcpy(p.payload, key, kKeyLen);
  return p;
}

Packet makePairAck(uint32_t seq) {
  Packet p;
  p.type = PacketType::PairAck;
  p.seq = seq;
  return p;
}

Packet makeAck(uint32_t acked_seq, uint8_t state_code, AckResult result, uint8_t fault_code) {
  Packet p;
  p.type = PacketType::Ack;
  p.seq = acked_seq;
  p.payload[0] = state_code;
  putU32(p.payload + 1, acked_seq);
  p.payload[5] = static_cast<uint8_t>(result);
  p.payload[6] = fault_code;
  if (result == AckResult::RefusedMagEmpty || result == AckResult::RefusedSafetyPin ||
      result == AckResult::RefusedNotReady) {
    p.flags |= kFlagRefused;
  }
  if (fault_code != 0) p.flags |= kFlagFault;
  return p;
}

uint32_t ackedSeq(const Packet& ack) { return getU32(ack.payload + 1); }
uint8_t ackState(const Packet& ack) { return ack.payload[0]; }
AckResult ackResult(const Packet& ack) { return static_cast<AckResult>(ack.payload[5]); }
uint8_t ackFault(const Packet& ack) { return ack.payload[6]; }

}  // namespace proto
}  // namespace beer
