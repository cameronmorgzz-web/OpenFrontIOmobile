#!/usr/bin/env bash
# Build and run every firmware unit-test suite with the host C++ compiler (no PlatformIO needed).
# Same test sources as `pio test -e native`; uses tools/unity_host/unity.h instead of Unity.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="${TMPDIR:-/tmp}/beer_fw_tests"; mkdir -p "$out"
CXX="${CXX:-g++}"
FLAGS="-std=c++17 -O1 -Wall -Wextra -Werror -I$here/common/src -I$here/tools/unity_host"
common="$here/common/src/*.cpp"
fail=0; total=0
for t in "$here"/launcher/test/test_* "$here"/button/test/test_*; do
  name="$(basename "$t")"
  # shellcheck disable=SC2086
  $CXX $FLAGS -I"$t" "$t"/*.cpp $common -o "$out/$name"
  if "$out/$name" > "$out/$name.log"; then res=OK; else res=FAIL; fail=1; fi
  n=$(grep -c ":PASS" "$out/$name.log" || true); total=$((total + n))
  printf "%-22s %-4s %3d passed\n" "$name" "$res" "$n"
  [ "$res" = FAIL ] && grep -E ":FAIL" "$out/$name.log" || true
done
echo "TOTAL $total tests passed"; exit $fail
