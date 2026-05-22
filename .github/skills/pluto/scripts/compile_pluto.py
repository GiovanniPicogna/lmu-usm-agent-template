#!/usr/bin/env python3
"""
PLUTO problem compiler — improved v2.
Mignone et al. 2007  —  https://plutocode.ph.unito.it

Usage (agent / JSON form):
    python compile_pluto.py --json '{"run_dir": "/path", "config_num": 1}'

Usage (CLI form):
    python compile_pluto.py --run-dir /path/to/Disk_Planet --config-num 1 --make-jobs 8
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ─── Constants ────────────────────────────────────────────────────────────────

SETUP_TIMEOUT   = 120   # seconds — setup.py should never take longer
MAKE_TIMEOUT    = 600   # seconds — 10 min is enough for even large problems
TAIL_LINES      = 25    # lines of output to include in error messages
SYSCONF_NAME    = "sysconf.out"   # written after successful compile


# ─── Pydantic model ───────────────────────────────────────────────────────────


class PLUTOCompileParams(BaseModel):
    run_dir:      str
    pluto_dir:    Optional[str] = None   # falls back to $PLUTO_DIR
    config_num:   Optional[int] = Field(default=None, ge=1, le=99)
    arch:         Optional[str] = None   # e.g. "Darwin.gcc.defs"; auto if None
    make_jobs:    int           = Field(default=4, ge=1, le=64)
    parallel:     bool          = False  # if True, prefer MPI .defs and expect pluto_mpi
    hdf5:         bool          = False  # if True, prefer HDF5-enabled .defs
    setup_timeout: int          = Field(default=SETUP_TIMEOUT, ge=10, le=600)
    make_timeout:  int          = Field(default=MAKE_TIMEOUT,  ge=30, le=3600)

    @model_validator(mode="after")
    def resolve_and_validate(self) -> "PLUTOCompileParams":
        # ── pluto_dir ────────────────────────────────────────────────────────
        if self.pluto_dir is None:
            env_dir = os.environ.get("PLUTO_DIR")
            if not env_dir:
                raise ValueError(
                    "pluto_dir not specified and $PLUTO_DIR is not set. "
                    "Set it with: export PLUTO_DIR=/path/to/PLUTO"
                )
            self.pluto_dir = env_dir

        for label, path in [("run_dir", self.run_dir), ("pluto_dir", self.pluto_dir)]:
            if not os.path.isdir(path):
                raise ValueError(f"{label} does not exist: {path!r}")

        # ── numbered config files ─────────────────────────────────────────────
        if self.config_num is not None:
            n = self.config_num
            # Accept both zero-padded (definitions_01.h) and bare (definitions_1.h)
            candidates_def = [
                Path(self.run_dir) / f"definitions_{n:02d}.h",
                Path(self.run_dir) / f"definitions_{n}.h",
            ]
            candidates_ini = [
                Path(self.run_dir) / f"pluto_{n:02d}.ini",
                Path(self.run_dir) / f"pluto_{n}.ini",
            ]
            if not any(p.is_file() for p in candidates_def):
                raise ValueError(
                    f"No definitions file for config_num={n} in {self.run_dir!r}. "
                    f"Tried: {[str(p) for p in candidates_def]}"
                )
            if not any(p.is_file() for p in candidates_ini):
                raise ValueError(
                    f"No ini file for config_num={n} in {self.run_dir!r}. "
                    f"Tried: {[str(p) for p in candidates_ini]}"
                )
        else:
            for fname in ("definitions.h", "pluto.ini"):
                if not (Path(self.run_dir) / fname).is_file():
                    raise ValueError(
                        f"{fname!r} not found in run_dir and config_num not given. "
                        "Either pass config_num or copy the files manually."
                    )
        return self


# ─── File helpers ─────────────────────────────────────────────────────────────


def _find_numbered_file(directory: str, stem_fmt: str, n: int) -> Path:
    """Return path for 'stem_01.ext' or 'stem_1.ext', whichever exists."""
    for fmt in (f"{stem_fmt}_{n:02d}", f"{stem_fmt}_{n}"):
        # stem_fmt should be like "definitions.h" split into stem+ext handled by caller
        pass
    raise FileNotFoundError  # caller does its own search above


def _atomic_copy(src: Path, dst: Path) -> None:
    """Write to a temp file in the same directory, then rename — atomic on POSIX."""
    dst_dir = dst.parent
    fd, tmp_path = tempfile.mkstemp(dir=dst_dir)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(src.read_bytes())
        os.replace(tmp_path, dst)   # atomic on POSIX
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


@contextmanager
def _backup_and_restore(paths: list[Path]):
    """
    Context manager: back up each path before the block, restore on any exception.
    Files that did not exist before are removed on restore.
    """
    backups: dict[Path, Optional[bytes]] = {}
    for p in paths:
        backups[p] = p.read_bytes() if p.exists() else None

    try:
        yield
    except Exception:
        # Restore originals
        for p, original in backups.items():
            if original is None:
                p.unlink(missing_ok=True)
            else:
                fd, tmp = tempfile.mkstemp(dir=p.parent)
                with os.fdopen(fd, "wb") as fh:
                    fh.write(original)
                os.replace(tmp, p)
        raise


# ─── Architecture detection ───────────────────────────────────────────────────


def _detect_arch(pluto_dir: str, parallel: bool = False, hdf5: bool = False) -> str:
    """
    Pick the most appropriate .defs file from Config/.

    Priority order (highest to lowest):
      1. Exact match for current OS + MPI if parallel=True
      2. Exact match for current OS (serial)
      3. First alphabetical .defs file
    """
    system = platform.system()
    config_dir = Path(pluto_dir) / "Config"
    if not config_dir.is_dir():
        raise FileNotFoundError(f"Config/ directory not found in pluto_dir: {pluto_dir!r}")

    all_defs = sorted(f.name for f in config_dir.iterdir() if f.suffix == ".defs")
    if not all_defs:
        raise FileNotFoundError(f"No .defs files in {config_dir}")

    # Preference lists for each OS
    prefs: dict[str, list[str]] = {
        "Darwin": [
            "Darwin.mpicc.defs" if parallel else "Darwin.gcc.defs",
            "Darwin.gcc.defs",
            "Darwin.mpicc.defs",
        ],
        "Linux": [
            "Linux.mpicc.defs" if parallel else "Linux.gcc.defs",
            "Linux.gcc.defs",
            "Linux.mpicc.defs",
            "Linux.icc.defs",
        ],
    }

    for candidate in prefs.get(system, []):
        if candidate in all_defs:
            return candidate

    # Fallback: first available
    return all_defs[0]


def _defs_has_parallel(run_dir: str, arch: str, pluto_dir: str) -> bool:
    """Read the .defs file and check if PARALLEL = TRUE."""
    defs_path = Path(pluto_dir) / "Config" / arch
    if not defs_path.is_file():
        # Fall back to the local makefile if present
        defs_path = Path(run_dir) / "makefile"
    if not defs_path.is_file():
        return False
    text = defs_path.read_text(errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("PARALLEL") and "=" in stripped:
            val = stripped.split("=", 1)[1].strip().upper()
            return val == "TRUE"
    return False


# ─── Stub makefile ────────────────────────────────────────────────────────────


def _write_stub_makefile(run_dir: str, pluto_dir: str, arch: str) -> None:
    """
    Write a minimal makefile stub that setup.py --auto-update can pick up.
    setup.py reads ARCH and PLUTO_DIR from the existing makefile when --auto-update
    is passed, so it skips the interactive arch-selection menu.

    NOTE: --auto-update reads the *existing* makefile's ARCH token; it does NOT
    re-run the full interactive setup. This means the stub must match exactly
    what setup.py expects, including the variable names ARCH and PLUTO_DIR.
    """
    stub = (
        f"ARCH         = {arch}\n"
        f"PLUTO_DIR    = {pluto_dir}\n"
    )
    (Path(run_dir) / "makefile").write_text(stub)


# ─── sysconf.out writer ───────────────────────────────────────────────────────


def _write_sysconf(run_dir: str, arch: str, config_num: Optional[int],
                   binary: str, parallel: bool) -> None:
    """Record last successful compile so run_pluto.py can read it."""
    content = (
        f"arch        = {arch}\n"
        f"config_num  = {config_num if config_num is not None else 'none'}\n"
        f"binary      = {binary}\n"
        f"parallel    = {str(parallel).lower()}\n"
        f"compiled_at = {time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
    )
    (Path(run_dir) / SYSCONF_NAME).write_text(content)


# ─── Subprocess helpers ───────────────────────────────────────────────────────


def _tail(text: str, n: int = TAIL_LINES) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:]) if lines else "(empty)"


def _run_or_error(
    cmd: list[str],
    cwd: str,
    env: dict,
    timeout: int,
    label: str,
) -> tuple[bool, str]:
    """
    Run a subprocess.  Returns (ok, message).
    On timeout, the process is killed and an error is returned.
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, (
            f"ERROR: {label} timed out after {timeout}s.\n"
            "Increase setup_timeout / make_timeout or check for interactive prompts."
        )
    except FileNotFoundError as exc:
        return False, f"ERROR: {label} — executable not found: {exc}"

    if proc.returncode != 0:
        combined = _tail(proc.stdout + "\n" + proc.stderr)
        return False, (
            f"ERROR: {label} failed (exit {proc.returncode}).\n"
            f"Last {TAIL_LINES} lines of output:\n{combined}"
        )
    return True, proc.stdout + proc.stderr


# ─── Main compile function ────────────────────────────────────────────────────


def compile_pluto(params: PLUTOCompileParams) -> str:
    run_dir   = Path(params.run_dir)
    pluto_dir = params.pluto_dir

    protected = [run_dir / "definitions.h", run_dir / "pluto.ini", run_dir / "makefile"]

    with _backup_and_restore(protected):
        # 1. Copy numbered config files → definitions.h / pluto.ini
        if params.config_num is not None:
            n = params.config_num
            for stem, ext, dst_name in [
                ("definitions", ".h",   "definitions.h"),
                ("pluto",       ".ini", "pluto.ini"),
            ]:
                src = next(
                    p for fmt in (f"{stem}_{n:02d}{ext}", f"{stem}_{n}{ext}")
                    if (p := run_dir / fmt).is_file()
                )
                _atomic_copy(src, run_dir / dst_name)

        # 2. Detect / confirm arch
        arch = params.arch or _detect_arch(pluto_dir, params.parallel, params.hdf5)

        # 3. Write stub makefile
        _write_stub_makefile(str(run_dir), pluto_dir, arch)

        # 4. Generate full makefile via setup.py --auto-update
        #
        #   --auto-update : reads existing ARCH from makefile stub, skips menus
        #   --no-curses   : documented in userguide §2.1; suppresses ncurses UI
        #                   (accepted by setup.py's menu module even if not in the
        #                   main argument loop — safe to include for all versions)
        #
        #   IMPORTANT: we run with sys.executable (same interpreter as this script)
        #   because on some systems `python` is Python 2 and setup.py must match.
        setup_script = str(Path(pluto_dir) / "setup.py")
        env = {**os.environ, "PLUTO_DIR": pluto_dir}

        ok, msg = _run_or_error(
            [sys.executable, setup_script, "--auto-update", "--no-curses"],
            cwd=str(run_dir),
            env=env,
            timeout=params.setup_timeout,
            label="setup.py --auto-update",
        )
        if not ok:
            return msg

        # 5. Compile
        t0 = time.monotonic()
        ok, msg = _run_or_error(
            ["make", f"-j{params.make_jobs}"],
            cwd=str(run_dir),
            env=env,
            timeout=params.make_timeout,
            label="make",
        )
        wall = time.monotonic() - t0
        if not ok:
            return msg

        # 6. Find binary — check for both serial and MPI variants
        binary_path: Optional[str] = None
        for candidate in ("pluto_mpi", "pluto"):  # prefer MPI if both exist
            p = run_dir / candidate
            if p.is_file():
                binary_path = str(p)
                break

        if binary_path is None:
            return (
                "ERROR: make reported success but no 'pluto' or 'pluto_mpi' binary "
                f"found in {run_dir}. Check make output:\n{_tail(msg)}"
            )

        # Infer whether this is a parallel build (for sysconf.out)
        is_parallel = "pluto_mpi" in binary_path or _defs_has_parallel(
            str(run_dir), arch, pluto_dir
        )

        # 7. Record compile state for run_pluto.py
        _write_sysconf(str(run_dir), arch, params.config_num, binary_path, is_parallel)

    # Successful compile — backups are kept as .bak files for audit
    return (
        f"SUCCESS: binary={binary_path}\n"
        f"  arch={arch}  config_num={params.config_num}  "
        f"parallel={is_parallel}  make_jobs={params.make_jobs}  "
        f"wall_clock={wall:.1f}s\n"
        f"  pluto_dir={pluto_dir}\n"
        f"  sysconf={run_dir / SYSCONF_NAME}"
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compile a PLUTO problem non-interactively.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--json",       metavar="JSON",
                   help="JSON string or path to JSON file with all parameters")
    p.add_argument("--run-dir",    dest="run_dir",
                   help="Path to PLUTO problem directory")
    p.add_argument("--pluto-dir",  dest="pluto_dir",
                   help="Path to PLUTO source tree (default: $PLUTO_DIR)")
    p.add_argument("--config-num", dest="config_num", type=int,
                   help="Config variant N: copies definitions_N.h and pluto_N.ini")
    p.add_argument("--arch",
                   help="Makefile arch token, e.g. Darwin.gcc.defs (auto-detected)")
    p.add_argument("--make-jobs",  dest="make_jobs", type=int, default=4,
                   help="Parallel make -jN jobs (default: 4)")
    p.add_argument("--parallel",   action="store_true", default=False,
                   help="Prefer MPI .defs file and expect pluto_mpi binary")
    p.add_argument("--hdf5",       action="store_true", default=False,
                   help="Prefer HDF5-enabled .defs file")
    p.add_argument("--setup-timeout", dest="setup_timeout", type=int,
                   default=SETUP_TIMEOUT,
                   help=f"Timeout for setup.py in seconds (default: {SETUP_TIMEOUT})")
    p.add_argument("--make-timeout",  dest="make_timeout",  type=int,
                   default=MAKE_TIMEOUT,
                   help=f"Timeout for make in seconds (default: {MAKE_TIMEOUT})")
    return p


def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    # Build raw dict from CLI flags (exclude None and the --json field itself)
    raw: dict = {k: v for k, v in vars(args).items()
                 if v is not None and k != "json"}

    # --json overrides individual CLI flags
    if args.json:
        src = args.json.strip()
        if os.path.isfile(src):
            with open(src) as fh:
                raw = json.load(fh)
        else:
            raw = json.loads(src)

    try:
        params = PLUTOCompileParams(**raw)
    except Exception as exc:
        print(f"ERROR: parameter validation failed — {exc}", file=sys.stderr)
        sys.exit(1)

    result = compile_pluto(params)
    print(result)
    sys.exit(1 if result.startswith("ERROR") else 0)


if __name__ == "__main__":
    main()
