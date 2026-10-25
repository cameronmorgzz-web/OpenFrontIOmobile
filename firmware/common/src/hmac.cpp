#include "hmac.h"

#include <cstring>

namespace beer {

void hmacSha256(const uint8_t* key, size_t key_len, const uint8_t* msg, size_t msg_len,
                uint8_t out[Sha256::kDigestLen]) {
  uint8_t k0[Sha256::kBlockLen];
  std::memset(k0, 0, sizeof(k0));
  if (key_len > Sha256::kBlockLen) {
    Sha256::hash(key, key_len, k0);
  } else if (key_len > 0) {
    std::memcpy(k0, key, key_len);
  }

  uint8_t pad[Sha256::kBlockLen];
  uint8_t inner[Sha256::kDigestLen];
  Sha256 s;

  for (size_t i = 0; i < Sha256::kBlockLen; ++i) pad[i] = static_cast<uint8_t>(k0[i] ^ 0x36);
  s.update(pad, sizeof(pad));
  s.update(msg, msg_len);
  s.finish(inner);

  for (size_t i = 0; i < Sha256::kBlockLen; ++i) pad[i] = static_cast<uint8_t>(k0[i] ^ 0x5c);
  s.update(pad, sizeof(pad));
  s.update(inner, sizeof(inner));
  s.finish(out);

  // Do not leave key material on the stack longer than needed.
  volatile uint8_t* vk = k0;
  for (size_t i = 0; i < sizeof(k0); ++i) vk[i] = 0;
}

bool constantTimeEqual(const uint8_t* a, const uint8_t* b, size_t len) {
  uint8_t diff = 0;
  for (size_t i = 0; i < len; ++i) diff = static_cast<uint8_t>(diff | (a[i] ^ b[i]));
  return diff == 0;
}

}  // namespace beer
