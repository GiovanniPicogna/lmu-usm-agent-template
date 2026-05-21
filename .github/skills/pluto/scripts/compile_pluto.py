#!/usr/bin/env python3
"""
PLUTO problem compiler.

Copies definitions_N.h → definitions.h and pluto_N.ini → pluto.ini,
generates a full makefile non-interactively via setup.py --auto-update
--no-curses, then runs make.

Usage (agent / JSON form):
    python compile_pluto.py --json '{"run_dir": "/path/to/Disk_Planet",
                                     "pluto_dir": "/path/to/pluto-code",
                                     "config_num": 1}'

Usage (CLI form):
    python compile_pluto.py --run-dir /path/to/Disk_Planet --config-num 1

Requires:
    - $PLUTO_DIR set (or --pluto-dir flag)
    - A C compiler on PATH (gcc for Darwin/Linux)
    - pydantic >= 2.0
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Pydantic parameter model
# ---------------------------------------------------------------------------

class PLUTOCompileParams(BaseModel):
    run_dir: str
    pluto_dir: Optional[str] = None   # falls back to $PLUTO_DIR
    config_num: Optional[int] = Field(default=None, ge=1, le=99)
    arch: Optional[str] = None        # e.g. "Darwin.gcc.defs"; auto-detected if None
    make_jobs: int = Field(default=4, ge=1, le=64)

    @model_validator(mode="after")
    def resolve_and_validate(self):
        if not os.path.isdir(self.run_dir):
            raise ValueError(f"run_dir does not exist: {self.run_dir!r}")
        if self.pluto_dir is None:
            env_dir = os.environ.get("PLUTO_DIR")
            if env_dir is None:
                raise ValueError(
                    "pluto_dir not specified and $PLUTO_DIR env var is not set."
                )
            self.pluto_dir = env_dir
        if not os.path.isdir(self.pluto_dir):
            raise ValueError(f"pluto_dir does not exist: {self.pluto_dir!r}")
        if self.config_num is not None:
            n = self.config_num
            def_src = os.path.join(self.run_dir, f"definitions_{n:02d}.h")
            ini_src = os.path.join(self.run_dir, f"pluto_{n:02d}.ini")
            if not os.path.isfile(def_src):
                raise ValueError(
                    f"definitions_{n:02d}.h not found in run_dir: {self.run_dir!r}"
                )
            if not os.path.isfile(ini_src):
                raise ValueError(
                    f"pluto_{n:02d}.ini not found in run_dir: {self.run_dir!r}"
                )
        else:
            if not os.path.isfile(os.path.join(self.run_dir, "definitions.h")):
                raise ValueError(
                    "definitions.h not found in run_dir and config_num not given. "
                    "Either copy definitions_N.h manually or pass config_num."
                )
            if not os.path.isfile(os.path.join(self.run_dir, "pluto.ini")):
                raise ValueError(
                    "pluto.ini not found in run_dir and config_num not given."
                )
        return self


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_arch(pluto_dir: str) -> str:
    """Return the most appropriate .defs filename for the current OS."""
    system = platform.system()
    config_dir = os.path.join(pluto_dir, "Config")
    candidates = {
        "Darwin": ["Darwin.gcc.defs", "Darwin.mpicc.defs"],
        "Linux":  ["Linux.gcc.defs",  "Linux.mpicc.defs"],
    }
    for name in candidates.get(system, []):
        if os.path.isfile(os.path.join(config_dir, name)):
            return name
    # Generic fallback: first alphabetical .defs
    defs = sorted(f for f in os.listdir(config_dir) if f.endswith(".defs"))
    if defs:
        return defs[0]
    raise FileNotFoundError(f"No .defs files found in {config_dir}")


def _write_stub_makefile(run_dir: str, pluto_dir: str, arch: str) -> None:
    """Write a minimal stub so setup.py --auto-update picks up ARCH without prompting."""
    stub = (
        f"ARCH         = {arch}\n"
        f"PLUTO_DIR    = {pluto_dir}\n"
    )
    with open(os.path.join(run_dir, "makefile"), "w") as fh:
        fh.write(stub)


# ---------------------------------------------------------------------------
# Main compile function
# ---------------------------------------------------------------------------

def compile_pluto(params: PLUTOCompileParams) -> str:
    run_dir = params.run_dir
    pluto_dir = params.pluto_dir

    # 1. Copy numbered config files → definitions.h / pluto.ini
    if params.config_num is not None:
        n = params.config_num
        shutil.copy2(
            os.path.join(run_dir, f"definitions_{n:02d}.h"),
            os.path.join(run_dir, "definitions.h"),
        )
        shutil.copy2(
            os.path.join(run_dir, f"pluto_{n:02d}.ini"),
            os.path.join(run_dir, "pluto.ini"),
        )

    # 2. Detect / confirm arch
    arch = params.arch or _detect_arch(pluto_dir)

    # 3. Write stub makefile (ARCH + PLUTO_DIR); setup.py will fill in the rest
    _write_stub_makefile(run_dir, pluto_dir, arch)

    # 4. Generate full makefile non-interactively
    #    --auto-update  : skips interactive menus and uses stub ARCH
    #    --no-curses    : disables the curses terminal UI entirely
    setup_script = os.path.join(pluto_dir, "setup.py")
    env = {**os.environ, "PLUTO_DIR": pluto_dir}
    setup_proc = subprocess.run(
        [sys.executable, setup_script, "--auto-update", "--no-curses"],
        capture_output=True,
        text=True,
        cwd=run_dir,
        env=env,
    )
    if setup_proc.returncode != 0:
        return (
            f"ERROR: setup.py --auto-update failed (exit {setup_proc.returncode})\n"
            f"stderr (last 20 lines):\n"
            + "\n".join(setup_proc.stderr.splitlines()[-20:])
        )

    # 5. Compile
    t0 = time.time()
    make_proc = subprocess.run(
        ["make", f"-j{params.make_jobs}"],
        capture_output=True,
        text=True,
        cwd=run_dir,
    )
    wall = time.time() - t0

    if make_proc.returncode != 0:
        return (
            f"ERROR: make failed (exit {make_proc.returncode})\n"
            f"Last 20 lines of stderr:\n"
            + "\n".join(make_proc.stderr.splitlines()[-20:])
        )

    # 6. Verify binary was produced
    binary = os.path.join(run_dir, "pluto")
    if not os.path.isfile(binary):
        return (
            "ERROR: make succeeded but 'pluto' binary not found in run_dir. "
            "Check make output above."
        )

    return (
        f"SUCCESS: binary={binary}\n"
        f"  arch={arch}  config_num={params.config_num}  "
        f"make_jobs={params.make_jobs}  wall_clock={wall:.1f}s\n"
        f"  pluto_dir={pluto_dir}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compile a PLUTO problem non-interactively."
    )
    p.add_argument("--json", metavar="JSON",
                   help="JSON string or path to JSON file with all parameters")
    p.add_argument("--run-dir", dest="run_dir",
                   help="Path to PLUTO problem directory")
    p.add_argument("--pluto-dir", dest="pluto_dir",
                   help="Path to PLUTO source tree (default: $PLUTO_DIR)")
    p.add_argument("--config-num", dest="config_num", type=int,
                   help="Config variant N: copies definitions_N.h and pluto_N.ini")
    p.add_argument("--arch",
                   help="Makefile arch, e.g. Darwin.gcc.defs (auto-detected if omitted)")
    p.add_argument("--make-jobs", dest="make_jobs", type=int, default=4,
                   help="Parallel make jobs (default: 4)")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    raw: dict = {k: v for k, v in vars(args).items()
                 if v is not None and k != "json"}

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
    if result.startswith("ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
