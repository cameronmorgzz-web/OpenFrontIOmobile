// HMAC-SHA256 (RFC 2104 / RFC 4231).
#pragma once

#include <cstddef>
#include <cstdint>

#include "sha256.h"

namespace beer {

void hmacSha256(const uint8_t* key, size_t key_len, const uint8_t* msg, size_t msg_len,
                uint8_t out[Sha256::kDigestLen]);

// Constant-time comparison: run time depends only on len, not on the data.
bool constantTimeEqual(const uint8_t* a, const uint8_t* b, size_t len);

}  // namespace beer
