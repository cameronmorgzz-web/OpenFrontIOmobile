#!/usr/bin/env bash
# Build both ESP32-C3 firmwares and run both native (host) Unity suites.
# Exits non-zero if any step fails. Usage:
#   firmware/run_tests.sh            # everything
#   firmware/run_tests.sh --native   # host tests only (no ESP32 toolchain needed)
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v pio >/dev/null 2>&1 && [ -f "$here/../.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . "$here/../.venv/bin/activate"
fi
if ! command -v pio >/dev/null 2>&1; then
  echo "error: PlatformIO (pio) not found" >&2
  exit 2
fi

native_only=0
[ "${1:-}" = "--native" ] && native_only=1

failures=()
step() {
  local name="$1"; shift
  echo "==> $name"
  if "$@"; then
    echo "<== $name: OK"
  else
    echo "<== $name: FAILED"
    failures+=("$name")
  fi
}

for proj in button launcher; do
  if [ "$native_only" -eq 0 ]; then
    step "$proj: pio run -e esp32c3" pio run -d "$here/$proj" -e esp32c3
  fi
  step "$proj: pio test -e native" pio test -d "$here/$proj" -e native
done

echo
if [ "${#failures[@]}" -ne 0 ]; then
  echo "FAILED: ${failures[*]}"
  exit 1
fi
echo "ALL OK"
