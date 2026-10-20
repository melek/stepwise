"""Run every Dafny proof as part of the test suite.

The proofs only mean something if they run: `postcond_p1.dfy` sat broken
for months because nothing verified it. This test verifies each `.dfy`
file under `lib/verified/` and `spec/` and fails on any error. It is
skipped when `dafny` is not on PATH, so contributors without Dafny can
still run the rest of the suite.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PROOFS = sorted((REPO / "lib" / "verified").glob("*.dfy")) + sorted((REPO / "spec").glob("*.dfy"))
DAFNY = shutil.which("dafny")


@pytest.mark.skipif(DAFNY is None, reason="dafny not installed")
@pytest.mark.parametrize("proof", PROOFS, ids=lambda p: str(p.relative_to(REPO)))
def test_proof_verifies(proof):
    proc = subprocess.run([DAFNY, "verify", str(proof)], capture_output=True,
                          text=True, timeout=300)
    assert proc.returncode == 0 and " 0 errors" in proc.stdout, proc.stdout + proc.stderr


def test_proofs_found():
    assert PROOFS, "no .dfy files found; did the layout change?"
