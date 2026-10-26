import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def manifest():
    return json.loads((ROOT / "cad" / "manifest.json").read_text())


@pytest.fixture(scope="session")
def root():
    return ROOT
