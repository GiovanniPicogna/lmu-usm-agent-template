#!/usr/bin/env python3
"""
PLUTO problem compiler.
Mignone et al. 2007  —  https://plutocode.ph.unito.it
Based on PLUTO v4.4-patch3 (September 2024).

Usage (agent / JSON form):
    python compile_pluto.py --json '{
        "run_dir": "/path/to/Disk_Planet",
        "config_num": 1,
        "with_fargo": true,
        "with_sb": true
    }'

    python compile_pluto.py --json '{
        "run_dir": "/path",
        "with_chombo": true,
        "chombo_mpi": true
    }'

Usage (CLI form):
    python compile_pluto.py --run-dir /path --config-num 1 --with-fargo --with-sb
    python compile_pluto.py --run-dir /path --with-chombo --chombo-mpi
"""

from __future__ import annotations

import argparse
import json
import os
import platform

# import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ─── Constants ────────────────────────────────────────────────────────────────

SETUP_TIMEOUT = 120  # seconds — setup.py should never take longer
MAKE_TIMEOUT = 600  # seconds — 10 min is enough for even large problems
TAIL_LINES = 25  # lines of output to include in error messages
SYSCONF_NAME = "sysconf.out"  # written after successful compile
SKILL_VERSION = "pluto-v4.4-patch3"
_SKILL_DIR = Path(__file__).resolve().parent


# ─── Pydantic model ───────────────────────────────────────────────────────────


class PLUTOCompileParams(BaseModel):
    run_dir: str
    pluto_dir: Optional[str] = None  # falls back to $PLUTO_DIR
    config_num: Optional[int] = Field(default=None, ge=1, le=99)
    arch: Optional[str] = None  # e.g. "Darwin.gcc.defs"; auto if None
    make_jobs: int = Field(default=4, ge=1, le=64)
    parallel: bool = False  # prefer mpicc .defs; sets PARALLEL=TRUE (binary still named ./pluto)
    hdf5: bool = False  # prefer HDF5-enabled .defs

    # ── Physics module flags (passed to setup.py) ─────────────────────────────
    # Source: setup.py argument loop (Mignone et al.)
    # Mutual exclusions (enforced by setup.py; we validate here first):
    #   --with-chombo  XOR  any of {--with-fd, --with-sb, --with-fargo}
    #   --with-sb      XOR  --with-fd
    with_sb: bool = False  # --with-sb         shearing box module
    with_fargo: bool = False  # --with-fargo       FARGO-MHD module
    with_fd: bool = False  # --with-fd          finite difference scheme
    with_chombo: bool = False  # --with-chombo      AMR via Chombo library
    chombo_mpi: bool = False  # --with-chombo: MPI=TRUE  (Chombo + MPI)
    with_cr_transport: bool = False  # --with-cr_transport  (undocumented but valid)

    setup_timeout: int = Field(default=SETUP_TIMEOUT, ge=10, le=600)
    make_timeout: int = Field(default=MAKE_TIMEOUT, ge=30, le=3600)

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

        # ── Physics module mutual exclusions (from setup.py source) ──────────
        #
        #   Rule 1: --with-chombo is incompatible with --with-fd, --with-sb, --with-fargo
        #           (setup.py checks: cmset = {--with-fd,--with-sb,--with-fargo} & argv)
        #   Rule 2: --with-sb is incompatible with --with-fd
        #   Rule 3: chombo_mpi=True requires with_chombo=True
        #
        if self.with_chombo:
            conflicts = []
            if self.with_fd:
                conflicts.append("with_fd")
            if self.with_sb:
                conflicts.append("with_sb")
            if self.with_fargo:
                conflicts.append("with_fargo")
            if conflicts:
                raise ValueError(
                    f"with_chombo is incompatible with: {', '.join(conflicts)}. "
                    "Chombo (AMR) cannot be combined with fd, sb, or fargo modules."
                )

        if self.with_sb and self.with_fd:
            raise ValueError(
                "with_sb (shearing box) and with_fd (finite difference) are "
                "mutually exclusive — setup.py will exit with an error."
            )

        if self.chombo_mpi and not self.with_chombo:
            raise ValueError(
                "chombo_mpi=True requires with_chombo=True. "
                "Set with_chombo=True to enable the Chombo AMR module first."
            )

        # ── chombo_mpi implies parallel build ─────────────────────────────────
        if self.chombo_mpi:
            self.parallel = True

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
        os.replace(tmp_path, dst)  # atomic on POSIX
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

    Priority order:
      1. Exact OS match + MPI preference if parallel=True
      2. Exact OS match (serial)
      3. First alphabetical .defs file

    Note: PARALLEL=TRUE in the .defs file causes setup.py to link with mpicc
    and produce an MPI-capable binary — still named './pluto', not 'pluto_mpi'.
    """
    system = platform.system()
    config_dir = Path(pluto_dir) / "Config"
    if not config_dir.is_dir():
        raise FileNotFoundError(f"Config/ directory not found in pluto_dir: {pluto_dir!r}")

    all_defs = sorted(f.name for f in config_dir.iterdir() if f.suffix == ".defs")
    if not all_defs:
        raise FileNotFoundError(f"No .defs files in {config_dir}")

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
    return all_defs[0]


def _read_defs_flags(arch: str, pluto_dir: str) -> dict[str, bool]:
    """
    Read PARALLEL, USE_HDF5, USE_PNG from the chosen .defs file.

    These flags control whether the binary is MPI-capable, HDF5-capable, etc.
    The binary is ALWAYS named './pluto' regardless of these settings
    (userguide §1.4: 'for a single processor run ... ./pluto [flags]' /
     'for a parallel run ... mpirun [...] ./pluto [args]').
    """
    defs_path = Path(pluto_dir) / "Config" / arch
    result = {"PARALLEL": False, "USE_HDF5": False, "USE_PNG": False}
    if not defs_path.is_file():
        return result
    for line in defs_path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for key in result:
            if stripped.upper().startswith(key) and "=" in stripped:
                val = stripped.split("=", 1)[1].strip().upper().split()[0]
                result[key] = val == "TRUE"
    return result


# ─── setup.py argv builder ────────────────────────────────────────────────────


def _build_setup_argv(params: "PLUTOCompileParams") -> list[str]:
    """
    Assemble the argument list for setup.py from the module flags in params.

    CRITICAL ordering rules (from setup.py source code):
      1. --auto-update must be present (reads ARCH from makefile stub; skips menus).
      2. --no-curses should come before module flags. Per userguide Table 1.2,
         it 'disables the curses terminal control feature and uses a shell-based
         setup instead'. With --auto-update the interactive menu is skipped
         entirely, so --no-curses is redundant but harmless and safe to include.
      3. --with-chombo MUST be the LAST flag.
         Reason: setup.py does `break` immediately after matching it; any flag
         placed after --with-chombo is silently ignored.
      4. All other module flags come before --with-chombo.

    Mutual exclusions are validated by the Pydantic model_validator before
    this function is called.
    """
    argv = [
        "--auto-update",
        "--no-curses",  # switches to shell-based menu; harmless with --auto-update
    ]

    # Non-Chombo flags — order among these does not matter
    if params.with_sb:
        argv.append("--with-sb")
    if params.with_fargo:
        argv.append("--with-fargo")
    if params.with_fd:
        argv.append("--with-fd")
    if params.with_cr_transport:
        argv.append("--with-cr_transport")

    # --with-chombo MUST be last (setup.py breaks on it)
    if params.with_chombo:
        if params.chombo_mpi:
            argv.extend(["--with-chombo:", "MPI=TRUE"])
        else:
            argv.append("--with-chombo")

    return argv


def _active_modules(params: "PLUTOCompileParams") -> list[str]:
    """Return a sorted list of active module flag names for logging."""
    active = []
    if params.with_sb:
        active.append("--with-sb")
    if params.with_fargo:
        active.append("--with-fargo")
    if params.with_fd:
        active.append("--with-fd")
    if params.with_cr_transport:
        active.append("--with-cr_transport")
    if params.with_chombo:
        active.append("--with-chombo:MPI=TRUE" if params.chombo_mpi else "--with-chombo")
    return active


def _write_stub_makefile(run_dir: str, pluto_dir: str, arch: str) -> None:
    """
    Write a minimal makefile stub that setup.py --auto-update can pick up.
    setup.py reads ARCH and PLUTO_DIR from the existing makefile when --auto-update
    is passed, so it skips the interactive arch-selection menu.

    NOTE: --auto-update reads the *existing* makefile's ARCH token; it does NOT
    re-run the full interactive setup. This means the stub must match exactly
    what setup.py expects, including the variable names ARCH and PLUTO_DIR.
    """
    stub = f"ARCH         = {arch}\n" f"PLUTO_DIR    = {pluto_dir}\n"
    (Path(run_dir) / "makefile").write_text(stub)


# ─── sysconf.out writer ───────────────────────────────────────────────────────


def _write_sysconf(
    run_dir: str,
    arch: str,
    config_num: Optional[int],
    binary: str,
    parallel: bool,
    modules: Optional[list[str]] = None,
) -> None:
    """
    Write our extended sysconf.out for agent state tracking.

    Note: PLUTO's setup.py also writes a sysconf.out containing system info.
    Per the userguide (§1.3 footnote), that file 'does not have any specific
    purpose but may be helpful for the user'. We overwrite it with our richer
    version so run_pluto.py can read the last compile configuration.
    """
    content = (
        f"arch        = {arch}\n"
        f"config_num  = {config_num if config_num is not None else 'none'}\n"
        f"binary      = {binary}\n"
        f"parallel    = {str(parallel).lower()}\n"
        f"modules     = {' '.join(modules) if modules else 'none'}\n"
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
    run_dir = Path(params.run_dir)
    pluto_dir = params.pluto_dir

    # ── Chombo prerequisite check ─────────────────────────────────────────────
    # Chombo AMR requires C++ (g++) and Fortran (gfortran) in addition to C
    # (userguide Table 1.1). Check before attempting the build.
    if params.with_chombo:
        missing = []
        for compiler in ("g++", "gfortran"):
            proc = subprocess.run([compiler, "--version"], capture_output=True, text=True)
            if proc.returncode != 0:
                missing.append(compiler)
        if missing:
            return (
                f"ERROR: Chombo AMR build requires C++ and Fortran compilers. "
                f"Missing: {', '.join(missing)}. "
                f"Install with e.g. 'apt install g++ gfortran' or "
                f"'conda install gxx_linux-64 gfortran_linux-64'."
            )

    protected = [run_dir / "definitions.h", run_dir / "pluto.ini", run_dir / "makefile"]

    with _backup_and_restore(protected):
        # 1. Copy numbered config files → definitions.h / pluto.ini
        if params.config_num is not None:
            n = params.config_num
            for stem, ext, dst_name in [
                ("definitions", ".h", "definitions.h"),
                ("pluto", ".ini", "pluto.ini"),
            ]:
                src = next(
                    p
                    for fmt in (f"{stem}_{n:02d}{ext}", f"{stem}_{n}{ext}")
                    if (p := run_dir / fmt).is_file()
                )
                _atomic_copy(src, run_dir / dst_name)

        # 2. Detect / confirm arch
        arch = params.arch or _detect_arch(pluto_dir, params.parallel, params.hdf5)

        # 3. Read actual PARALLEL/USE_HDF5 from the .defs file
        defs_flags = _read_defs_flags(arch, pluto_dir)
        is_parallel = defs_flags["PARALLEL"]
        if params.parallel and not is_parallel:
            print(
                f"WARNING: parallel=True requested but arch '{arch}' has "
                f"PARALLEL=FALSE. Pass arch= explicitly to select an mpicc .defs.",
                file=sys.stderr,
            )

        # 4. Write stub makefile so --auto-update reads ARCH and PLUTO_DIR
        _write_stub_makefile(str(run_dir), pluto_dir, arch)

        # 5. Generate full makefile via setup.py
        #
        #   --auto-update: reads ARCH from stub makefile; skips interactive menu
        #   --no-curses:   switches to shell-based text menu (userguide Table 1.2)
        #                  redundant with --auto-update but harmless
        #   module flags:  correct order enforced by _build_setup_argv()
        #                  --with-chombo MUST be last (setup.py breaks on it)
        #
        #   sys.executable: ensures same Python interpreter (avoids 2/3 mismatch)
        setup_script = str(Path(pluto_dir) / "setup.py")
        env = {**os.environ, "PLUTO_DIR": pluto_dir}
        setup_argv = _build_setup_argv(params)
        modules = _active_modules(params)

        ok, msg = _run_or_error(
            [sys.executable, setup_script] + setup_argv,
            cwd=str(run_dir),
            env=env,
            timeout=params.setup_timeout,
            label=f"setup.py {' '.join(setup_argv)}",
        )
        if not ok:
            return msg

        # 6. Compile
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

        # 7. Verify binary.
        #
        #    PLUTO ALWAYS produces a binary named './pluto' regardless of whether
        #    PARALLEL=TRUE was set (userguide §1.4). There is NO 'pluto_mpi'.
        #    MPI support is baked in at compile time via CC=mpicc in the .defs.
        binary_path = str(run_dir / "pluto")
        if not (run_dir / "pluto").is_file():
            return (
                "ERROR: make reported success but './pluto' not found "
                f"in {run_dir}. Check make output:\n{_tail(msg)}"
            )

        # 8. Record compile state for agent state tracking
        _write_sysconf(str(run_dir), arch, params.config_num, binary_path, is_parallel, modules)

    modules_str = " ".join(modules) if modules else "none"

    # Write physics_config.md — parsed from definitions.h
    # read by run_pluto.py and plot_pluto.py for geometry-aware axes + units
    phys_cfg_path = "not written"
    try:
        sys.path.insert(0, str(_SKILL_DIR))
        from physics_config_writer import write_physics_config

        phys_cfg_path = write_physics_config(
            str(run_dir),
            extra={
                "arch": arch,
                "config_num": str(params.config_num) if params.config_num else "none",
                "binary": binary_path,
                "parallel": str(is_parallel).lower(),
                "modules": modules_str,
                "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "skill_version": SKILL_VERSION,
            },
        )
    except Exception as _pce:
        phys_cfg_path = f"not written ({_pce})"

    return (
        f"SUCCESS: binary={binary_path}\n"
        f"  arch={arch}  config_num={params.config_num}  "
        f"parallel={is_parallel}  make_jobs={params.make_jobs}  "
        f"wall_clock={wall:.1f}s\n"
        f"  modules={modules_str}\n"
        f"  pluto_dir={pluto_dir}\n"
        f"  sysconf={run_dir / SYSCONF_NAME}\n"
        f"  physics_config={phys_cfg_path}"
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compile a PLUTO problem non-interactively.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--json", metavar="JSON", help="JSON string or path to JSON file with all parameters"
    )
    p.add_argument("--run-dir", dest="run_dir", help="Path to PLUTO problem directory")
    p.add_argument(
        "--pluto-dir", dest="pluto_dir", help="Path to PLUTO source tree (default: $PLUTO_DIR)"
    )
    p.add_argument(
        "--config-num",
        dest="config_num",
        type=int,
        help="Config variant N: copies definitions_N.h and pluto_N.ini",
    )
    p.add_argument("--arch", help="Makefile arch token, e.g. Darwin.gcc.defs (auto-detected)")
    p.add_argument(
        "--make-jobs",
        dest="make_jobs",
        type=int,
        default=4,
        help="Parallel make -jN jobs (default: 4)",
    )
    p.add_argument(
        "--parallel",
        action="store_true",
        default=False,
        help="Prefer MPI .defs file (sets PARALLEL=TRUE via CC=mpicc). "
        "Binary is still named './pluto' (not 'pluto_mpi').",
    )
    p.add_argument(
        "--hdf5", action="store_true", default=False, help="Prefer HDF5-enabled .defs file"
    )

    # ── Physics module flags ──────────────────────────────────────────────────
    mod = p.add_argument_group(
        "physics modules",
        "Flags passed verbatim to setup.py. Mutual exclusions: "
        "--with-chombo XOR {--with-fd, --with-sb, --with-fargo}; "
        "--with-sb XOR --with-fd. "
        "--with-chombo is always placed LAST in setup.py argv (setup.py breaks on it).",
    )
    mod.add_argument(
        "--with-sb",
        dest="with_sb",
        action="store_true",
        default=False,
        help="Enable shearing box module (--with-sb)",
    )
    mod.add_argument(
        "--with-fargo",
        dest="with_fargo",
        action="store_true",
        default=False,
        help="Enable FARGO-MHD module (--with-fargo)",
    )
    mod.add_argument(
        "--with-fd",
        dest="with_fd",
        action="store_true",
        default=False,
        help="Enable finite difference scheme (--with-fd)",
    )
    mod.add_argument(
        "--with-chombo",
        dest="with_chombo",
        action="store_true",
        default=False,
        help="Enable AMR via Chombo library (--with-chombo)",
    )
    mod.add_argument(
        "--chombo-mpi",
        dest="chombo_mpi",
        action="store_true",
        default=False,
        help="Use MPI-enabled Chombo (--with-chombo: MPI=TRUE); implies --with-chombo",
    )
    mod.add_argument(
        "--with-cr-transport",
        dest="with_cr_transport",
        action="store_true",
        default=False,
        help="Enable cosmic-ray transport module (--with-cr_transport)",
    )
    p.add_argument(
        "--setup-timeout",
        dest="setup_timeout",
        type=int,
        default=SETUP_TIMEOUT,
        help=f"Timeout for setup.py in seconds (default: {SETUP_TIMEOUT})",
    )
    p.add_argument(
        "--make-timeout",
        dest="make_timeout",
        type=int,
        default=MAKE_TIMEOUT,
        help=f"Timeout for make in seconds (default: {MAKE_TIMEOUT})",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Build raw dict from CLI flags (exclude None and the --json field itself)
    raw: dict = {k: v for k, v in vars(args).items() if v is not None and k != "json"}

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
