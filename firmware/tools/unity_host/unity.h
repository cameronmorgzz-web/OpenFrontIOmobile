// Minimal Unity-compatible header used ONLY by tools/host_tests.sh (plain g++, no PlatformIO).
// `pio test -e native` uses the real ThrowTheSwitch Unity; the test sources are identical.
#pragma once
#include <csetjmp>
#include <cstdio>
#include <cstring>
#include <cstdint>
struct UnityShim { int tests=0, fails=0; jmp_buf jb; const char* cur=""; };
inline UnityShim& U(){ static UnityShim u; return u; }
void setUp(); void tearDown();
#define UNITY_BEGIN() (U().tests=0,U().fails=0,0)
#define UNITY_END() (printf("\n%d Tests %d Failures 0 Ignored\n%s\n",U().tests,U().fails,U().fails?"FAIL":"OK"),U().fails)
#define RUN_TEST(fn) do{ U().tests++; U().cur=#fn; if(!setjmp(U().jb)){ setUp(); fn(); tearDown(); printf("%s:PASS\n",#fn);} }while(0)
#define UFAIL(line,msg) do{ printf("%s:%d:%s:FAIL: %s\n",__FILE__,line,U().cur,msg); U().fails++; longjmp(U().jb,1);}while(0)
#define TEST_FAIL_MESSAGE(m) UFAIL(__LINE__,m)
#define TEST_ASSERT_TRUE_MESSAGE(c,m) do{ if(!(c)) UFAIL(__LINE__,m);}while(0)
#define TEST_ASSERT_TRUE(c) TEST_ASSERT_TRUE_MESSAGE(c,#c)
#define TEST_ASSERT(c) TEST_ASSERT_TRUE(c)
#define TEST_ASSERT_FALSE(c) TEST_ASSERT_TRUE_MESSAGE(!(c),"expected false: " #c)
#define TEST_ASSERT_FALSE_MESSAGE(c,m) TEST_ASSERT_TRUE_MESSAGE(!(c),m)
#define UEQ(e,a,m) do{ long long _e=(long long)(e), _a=(long long)(a); if(_e!=_a){ char b[256]; snprintf(b,sizeof b,"Expected %lld Was %lld %s",_e,_a,m); UFAIL(__LINE__,b);} }while(0)
#define TEST_ASSERT_EQUAL(e,a) UEQ(e,a,"")
#define TEST_ASSERT_EQUAL_INT(e,a) UEQ(e,a,"")
#define TEST_ASSERT_EQUAL_UINT8(e,a) UEQ(e,a,"")
#define TEST_ASSERT_EQUAL_UINT16(e,a) UEQ(e,a,"")
#define TEST_ASSERT_EQUAL_UINT32(e,a) UEQ(e,a,"")
#define TEST_ASSERT_EQUAL_INT32(e,a) UEQ(e,a,"")
#define TEST_ASSERT_EQUAL_MESSAGE(e,a,m) UEQ(e,a,m)
#define TEST_ASSERT_EQUAL_UINT32_MESSAGE(e,a,m) UEQ(e,a,m)
#define TEST_ASSERT_EQUAL_INT_MESSAGE(e,a,m) UEQ(e,a,m)
#define TEST_ASSERT_NOT_EQUAL(e,a) do{ if((long long)(e)==(long long)(a)) UFAIL(__LINE__,"Expected Not-Equal");}while(0)
#define TEST_ASSERT_LESS_OR_EQUAL_MESSAGE(t,a,m) do{ long long _t=(long long)(t),_a=(long long)(a); if(!(_a<=_t)){char b[256]; snprintf(b,sizeof b,"Expected <= %lld Was %lld %s",_t,_a,m); UFAIL(__LINE__,b);} }while(0)
#define TEST_ASSERT_GREATER_OR_EQUAL_MESSAGE(t,a,m) do{ long long _t=(long long)(t),_a=(long long)(a); if(!(_a>=_t)){char b[256]; snprintf(b,sizeof b,"Expected >= %lld Was %lld %s",_t,_a,m); UFAIL(__LINE__,b);} }while(0)
#define TEST_ASSERT_LESS_OR_EQUAL(t,a) TEST_ASSERT_LESS_OR_EQUAL_MESSAGE(t,a,"")
#define TEST_ASSERT_GREATER_OR_EQUAL(t,a) TEST_ASSERT_GREATER_OR_EQUAL_MESSAGE(t,a,"")
#define TEST_ASSERT_GREATER_THAN(t,a) do{ if(!((long long)(a)>(long long)(t))) UFAIL(__LINE__,"Expected greater");}while(0)
#define TEST_ASSERT_LESS_THAN(t,a) do{ if(!((long long)(a)<(long long)(t))) UFAIL(__LINE__,"Expected less");}while(0)
#define TEST_ASSERT_EQUAL_HEX8_ARRAY(e,a,n) do{ if(memcmp((e),(a),(n))) UFAIL(__LINE__,"array mismatch");}while(0)
#define TEST_ASSERT_EQUAL_MEMORY(e,a,n) TEST_ASSERT_EQUAL_HEX8_ARRAY(e,a,n)
#define TEST_ASSERT_EQUAL_STRING(e,a) do{ if(strcmp((e),(a))) UFAIL(__LINE__,"string mismatch");}while(0)
#define TEST_MESSAGE(m) printf("%s\n",m)
