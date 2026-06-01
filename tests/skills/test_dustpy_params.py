import subprocess
import sys
from pathlib import Path
import pytest

SCRIPT = Path(__file__).parents[2] / ".github/skills/dustpy/scripts/run_dustpy.py"

_dustpy_available = subprocess.run(
    [sys.executable, "-c", "import dustpy"],
    capture_output=True,
).returncode == 0


def _run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)] + args,
        capture_output=True,
        text=True,
        timeout=30,
    )
    last_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    return result.returncode, last_line


def test_script_exists():
    assert SCRIPT.exists(), f"DustPy script not found at {SCRIPT}"


def test_dry_run_emits_success_or_error_protocol(tmp_path):
    """Regardless of whether DustPy is installed, the last line must be SUCCESS or ERROR."""
    _, last = _run(["--run_dir", str(tmp_path / "run"), "--dry_run"])
    assert last.startswith("SUCCESS") or last.startswith("ERROR"), (
        f"Protocol violation: last stdout line must start with SUCCESS or ERROR, got: {last!r}"
    )


@pytest.mark.skipif(not _dustpy_available, reason="dustpy not installed in active environment")
def test_valid_params_succeed(tmp_path):
    _, last = _run([
        "--run_dir", str(tmp_path / "run"),
        "--dry_run",
        "--alpha", "1e-3",
        "--mdisk_msun", "0.05",
        "--t_end_yr", "1e4",
    ])
    assert last.startswith("SUCCESS"), f"Expected SUCCESS, got: {last!r}"


@pytest.mark.skipif(not _dustpy_available, reason="dustpy not installed in active environment")
def test_negative_alpha_rejected(tmp_path):
    _, last = _run([
        "--run_dir", str(tmp_path / "run"),
        "--dry_run",
        "--alpha", "-1.0",
    ])
    assert last.startswith("ERROR"), f"Expected ERROR for negative alpha, got: {last!r}"
