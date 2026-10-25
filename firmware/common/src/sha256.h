// Small portable SHA-256 (FIPS 180-4). No dynamic allocation, no platform deps.
#pragma once

#include <cstddef>
#include <cstdint>

namespace beer {

class Sha256 {
 public:
  static constexpr size_t kDigestLen = 32;
  static constexpr size_t kBlockLen = 64;

  Sha256() { reset(); }
  void reset();
  void update(const uint8_t* data, size_t len);
  void finish(uint8_t out[kDigestLen]);

  // One-shot helper.
  static void hash(const uint8_t* data, size_t len, uint8_t out[kDigestLen]);

 private:
  void compress(const uint8_t block[kBlockLen]);

  uint32_t h_[8];
  uint8_t buf_[kBlockLen];
  size_t buf_len_;
  uint64_t total_len_;
};

}  // namespace beer
