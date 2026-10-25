// Per-button replay protection: a strictly increasing uint32 sequence number.
//
// The launcher keeps one guard for its (single) paired button and persists last()
// to NVS after every accepted packet. seq == last is a retry of the packet that was
// just handled (lost ACK): re-ACK, never re-trigger. seq < last is a replay.
// Re-pairing installs a fresh key, so the guard is reset to 0 at pairing time
// (packets signed with the old key fail the HMAC check anyway).
//
// Wrap-around is not handled: at one press per second, 2^32 takes 136 years.
#pragma once

#include <cstdint>

namespace beer {

enum class SeqVerdict : uint8_t {
  Fresh,      // seq > last: accept, act on it
  Duplicate,  // seq == last: retry of the last handled packet, re-ACK only
  Stale,      // seq < last (or seq == 0 before anything was accepted): reject
};

class ReplayGuard {
 public:
  explicit ReplayGuard(uint32_t last = 0) : last_(last) {}

  SeqVerdict check(uint32_t seq) const;

  // check() and, when Fresh, advance last to seq.
  SeqVerdict checkAndAccept(uint32_t seq);

  uint32_t last() const { return last_; }
  void reset(uint32_t last = 0) { last_ = last; }

 private:
  uint32_t last_;
};

const char* seqVerdictName(SeqVerdict v);

}  // namespace beer
