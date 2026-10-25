#include "replay_guard.h"

namespace beer {

SeqVerdict ReplayGuard::check(uint32_t seq) const {
  if (seq > last_) return SeqVerdict::Fresh;
  // last_ == 0 means "nothing accepted yet": seq 0 is never valid.
  if (seq == last_ && last_ != 0) return SeqVerdict::Duplicate;
  return SeqVerdict::Stale;
}

SeqVerdict ReplayGuard::checkAndAccept(uint32_t seq) {
  const SeqVerdict v = check(seq);
  if (v == SeqVerdict::Fresh) last_ = seq;
  return v;
}

const char* seqVerdictName(SeqVerdict v) {
  switch (v) {
    case SeqVerdict::Fresh: return "fresh";
    case SeqVerdict::Duplicate: return "duplicate";
    case SeqVerdict::Stale: return "stale";
  }
  return "?";
}

}  // namespace beer
