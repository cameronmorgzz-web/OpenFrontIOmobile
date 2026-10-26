"""Gate 5: firmware unit tests on the host (same sources as `pio test -e native`)."""

import subprocess

from tests.conftest import ROOT


def test_firmware_host_tests():
    r = subprocess.run(["bash", str(ROOT / "firmware" / "tools" / "host_tests.sh")], capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TOTAL" in r.stdout
