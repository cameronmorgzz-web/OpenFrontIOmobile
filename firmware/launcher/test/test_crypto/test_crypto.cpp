// SHA-256 (FIPS 180-2 appendix B) and HMAC-SHA256 (RFC 4231) known-answer tests.
#include <unity.h>

#include <cstring>
#include <string>

#include "hmac.h"
#include "sha256.h"

using beer::Sha256;

static std::string hex(const uint8_t* p, size_t n) {
  static const char* d = "0123456789abcdef";
  std::string s;
  for (size_t i = 0; i < n; ++i) {
    s += d[p[i] >> 4];
    s += d[p[i] & 15];
  }
  return s;
}

static std::string sha(const std::string& m) {
  uint8_t out[32];
  Sha256::hash(reinterpret_cast<const uint8_t*>(m.data()), m.size(), out);
  return hex(out, 32);
}

static std::string hmac(const std::string& k, const std::string& m, size_t n = 32) {
  uint8_t out[32];
  beer::hmacSha256(reinterpret_cast<const uint8_t*>(k.data()), k.size(),
                   reinterpret_cast<const uint8_t*>(m.data()), m.size(), out);
  return hex(out, n);
}

void setUp() {}
void tearDown() {}

void test_sha256_abc() {
  TEST_ASSERT_EQUAL_STRING("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", sha("abc").c_str());
}

void test_sha256_empty() {
  TEST_ASSERT_EQUAL_STRING("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", sha("").c_str());
}

void test_sha256_448bit() {
  TEST_ASSERT_EQUAL_STRING("248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
                           sha("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq").c_str());
}

void test_sha256_million_a_streamed() {
  Sha256 s;
  uint8_t chunk[1000];
  std::memset(chunk, 'a', sizeof(chunk));
  for (int i = 0; i < 1000; ++i) s.update(chunk, sizeof(chunk));
  uint8_t out[32];
  s.finish(out);
  TEST_ASSERT_EQUAL_STRING("cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0", hex(out, 32).c_str());
}

void test_sha256_split_updates_match_oneshot() {
  const std::string m = "The quick brown fox jumps over the lazy dog, again and again and again!!";
  for (size_t split = 0; split <= m.size(); ++split) {
    Sha256 s;
    s.update(reinterpret_cast<const uint8_t*>(m.data()), split);
    s.update(reinterpret_cast<const uint8_t*>(m.data()) + split, m.size() - split);
    uint8_t out[32];
    s.finish(out);
    TEST_ASSERT_EQUAL_STRING(sha(m).c_str(), hex(out, 32).c_str());
  }
}

void test_hmac_rfc4231_case1() {
  TEST_ASSERT_EQUAL_STRING("b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7",
                           hmac(std::string(20, '\x0b'), "Hi There").c_str());
}

void test_hmac_rfc4231_case2() {
  TEST_ASSERT_EQUAL_STRING("5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843",
                           hmac("Jefe", "what do ya want for nothing?").c_str());
}

void test_hmac_rfc4231_case3() {
  TEST_ASSERT_EQUAL_STRING("773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe",
                           hmac(std::string(20, '\xaa'), std::string(50, '\xdd')).c_str());
}

void test_hmac_rfc4231_case4() {
  std::string key;
  for (int i = 1; i <= 25; ++i) key += static_cast<char>(i);
  TEST_ASSERT_EQUAL_STRING("82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b",
                           hmac(key, std::string(50, '\xcd')).c_str());
}

void test_hmac_rfc4231_case5_truncated() {
  TEST_ASSERT_EQUAL_STRING("a3b6167473100ee06e0c796c2955552b",
                           hmac(std::string(20, '\x0c'), "Test With Truncation", 16).c_str());
}

void test_hmac_rfc4231_case6_long_key() {
  TEST_ASSERT_EQUAL_STRING("60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54",
                           hmac(std::string(131, '\xaa'), "Test Using Larger Than Block-Size Key - Hash Key First").c_str());
}

void test_hmac_rfc4231_case7_long_key_long_data() {
  TEST_ASSERT_EQUAL_STRING(
      "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2",
      hmac(std::string(131, '\xaa'),
           "This is a test using a larger than block-size key and a larger than block-size data. The key needs "
           "to be hashed before being used by the HMAC algorithm.")
          .c_str());
}

void test_constant_time_equal() {
  const uint8_t a[8] = {1, 2, 3, 4, 5, 6, 7, 8};
  uint8_t b[8] = {1, 2, 3, 4, 5, 6, 7, 8};
  TEST_ASSERT_TRUE(beer::constantTimeEqual(a, b, 8));
  for (int i = 0; i < 8; ++i) {
    b[i] ^= 0x80;
    TEST_ASSERT_FALSE(beer::constantTimeEqual(a, b, 8));
    b[i] ^= 0x80;
  }
  TEST_ASSERT_TRUE(beer::constantTimeEqual(a, b, 0));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_sha256_abc);
  RUN_TEST(test_sha256_empty);
  RUN_TEST(test_sha256_448bit);
  RUN_TEST(test_sha256_million_a_streamed);
  RUN_TEST(test_sha256_split_updates_match_oneshot);
  RUN_TEST(test_hmac_rfc4231_case1);
  RUN_TEST(test_hmac_rfc4231_case2);
  RUN_TEST(test_hmac_rfc4231_case3);
  RUN_TEST(test_hmac_rfc4231_case4);
  RUN_TEST(test_hmac_rfc4231_case5_truncated);
  RUN_TEST(test_hmac_rfc4231_case6_long_key);
  RUN_TEST(test_hmac_rfc4231_case7_long_key_long_data);
  RUN_TEST(test_constant_time_equal);
  return UNITY_END();
}
