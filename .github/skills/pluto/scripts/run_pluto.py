#!/usr/bin/env python3
"""
PLUTO ini patcher and runner.
Mignone et al. 2007  —  https://plutocode.ph.unito.it
Based on PLUTO v4.4-patch3 (September 2024).

Usage (agent / JSON form):
    python run_pluto.py --json '{"run_dir": "runs/disk", "tstop": 500,
                                 "parameters": {"ALPHA": 1e-3}}'

    python run_pluto.py --json '{"run_dir": "runs/disk",
                                 "checkpoint_times": [100, 250, 500]}'

Usage (CLI form):
    python run_pluto.py --run-dir runs/disk --tstop 500 --n-procs 4
    python run_pluto.py --run-dir runs/disk --h5restart 12 --tstop 800
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import typing as ty
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

SYSCONF_NAME = "sysconf.out"  # written by compile_pluto.py
_SKILL_DIR = Path(__file__).resolve().parent


# ─── Pydantic model ───────────────────────────────────────────────────────────


class PLUTOParams(BaseModel):
    # ── Location ──────────────────────────────────────────────────────────────
    run_dir: str
    output_dir: Optional[str] = None

    # ── Time control (all patch [Time] in pluto.ini) ──────────────────────────
    tstop: Optional[float] = Field(default=None, gt=0.0)
    cfl: Optional[float] = Field(default=None, ge=0.1, le=0.9)
    cfl_max_var: Optional[float] = Field(default=None, gt=1.0)  # userguide §4.3
    first_dt: Optional[float] = Field(default=None, gt=0.0)

    # Staged run — mutually exclusive with tstop
    checkpoint_times: ty.Optional[ty.List[float]] = None

    # ── Solver (patches [Solver] in pluto.ini) ────────────────────────────────
    solver: Optional[str] = None  # e.g. "hll", "roe", "tvdlf"

    # ── User [Parameters] (patches [Parameters] in pluto.ini) ────────────────
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # ── Runtime flags (assembled on ./pluto command line) ─────────────────────
    # Binary is ALWAYS named './pluto' — MPI support is baked in at compile time
    pluto_bin: str = "./pluto"
    ini_file: Optional[str] = None  # -i fname  (alternative ini file)

    # Restart modes (mutually exclusive — validator enforces)
    restart: Optional[int] = Field(default=None, ge=0)  # -restart N  (reads .dbl)
    h5restart: Optional[int] = Field(default=None, ge=0)  # -h5restart N (reads .dbl.h5)
    frestart: Optional[int] = Field(default=None, ge=0)  # -frestart N (fluid-only)

    # Run control flags
    maxsteps: Optional[int] = Field(default=None, ge=1)  # -maxsteps N
    xres: Optional[int] = Field(default=None, ge=1)  # -xres N
    no_write: bool = False  # -no-write

    # ── MPI ───────────────────────────────────────────────────────────────────
    n_procs: int = Field(default=1, ge=1, le=512)
    decomp: Optional[List[int]] = None  # -dec n1 [n2] [n3]; product must == n_procs

    # ── Compile integration ───────────────────────────────────────────────────
    config_num: Optional[int] = Field(default=None, ge=1, le=99)
    auto_compile: bool = True
    force_compile: bool = False

    # ── Background / monitoring ───────────────────────────────────────────────
    background: bool = False
    monitor: bool = False
    watch_interval: float = Field(default=20.0, ge=1.0, le=3600.0)
    plot_on_the_fly: bool = False
    plot_interval: float = Field(default=30.0, ge=1.0, le=3600.0)
    plot_output_dir: Optional[str] = None
    quiver_subsample: int = Field(default=8, ge=1, le=128)

    # ── Output dir config (patches [Static Grid Output]) ─────────────────────
    log_dir: Optional[str] = None  # parallel log file directory

    # ── Validators ───────────────────────────────────────────────────────────

    @field_validator("tstop", "cfl", "cfl_max_var", "first_dt", mode="before")
    @classmethod
    def coerce_scientific_notation(cls, v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                pass
        return v

    @field_validator("parameters", "checkpoint_times", mode="before")
    @classmethod
    def coerce_json_fields(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def validate_all(self) -> "PLUTOParams":
        if not os.path.isdir(self.run_dir):
            raise ValueError(f"run_dir does not exist: {self.run_dir!r}")

        # pluto.ini must exist (we always patch from it)
        ini_name = self.ini_file or "pluto.ini"
        if not (Path(self.run_dir) / ini_name).is_file():
            raise ValueError(f"{ini_name!r} not found in run_dir: {self.run_dir!r}")

        # tstop XOR checkpoint_times
        if self.tstop is not None and self.checkpoint_times is not None:
            raise ValueError("Specify either 'tstop' or 'checkpoint_times', not both.")

        # At most one restart mode
        restart_modes = [x for x in (self.restart, self.h5restart, self.frestart) if x is not None]
        if len(restart_modes) > 1:
            raise ValueError(
                "Specify at most one of: restart, h5restart, frestart. "
                "They map to -restart, -h5restart, -frestart respectively."
            )

        # decomp product must equal n_procs
        if self.decomp is not None:
            product = 1
            for d in self.decomp:
                product *= d
            if product != self.n_procs:
                raise ValueError(
                    f"decomp product ({product}) must equal n_procs ({self.n_procs}). "
                    f"decomp={self.decomp}"
                )

        return self


# ─── pluto.ini patcher ────────────────────────────────────────────────────────


class PLUTOIniPatcher:
    """
    Minimal line-preserving patcher for pluto.ini.

    Reads the ini file once, patches values in-place, writes back.
    Preserves comments, whitespace alignment, and section ordering.

    Section matching is case-insensitive and ignores leading/trailing spaces.
    Key matching is case-insensitive.

    IMPORTANT: if a key is not found in the expected section, it is appended
    to that section — but for [Parameters] this can change the count seen by
    PLUTO. Always verify that [Parameters] entries in pluto.ini match the
    USER_DEF_PARAMETERS count in definitions.h (userguide §4.9).
    """

    _SECTION_RE = re.compile(r"^\[(.+)\]\s*$")
    _KEY_RE = re.compile(r"^(\s*)(\S+)(\s+)(.*?)(\s*)$")

    def __init__(self, ini_path: str):
        with open(ini_path) as fh:
            self.lines = fh.readlines()

    def _set_value(self, section: str, key: str, value: str) -> bool:
        in_section = False
        for i, line in enumerate(self.lines):
            sm = self._SECTION_RE.match(line)
            if sm:
                in_section = sm.group(1).strip().lower() == section.lower()
                continue
            if not in_section:
                continue
            km = self._KEY_RE.match(line)
            if km and km.group(2).lower() == key.lower():
                self.lines[i] = f"{km.group(1)}{km.group(2)}{km.group(3)}{value}\n"
                return True
        return False

    def _append_to_section(self, section: str, key: str, value: str) -> None:
        in_section = False
        insert_at = None
        for i, line in enumerate(self.lines):
            sm = self._SECTION_RE.match(line)
            if sm:
                if in_section:
                    insert_at = i
                    break
                in_section = sm.group(1).strip().lower() == section.lower()
        if in_section and insert_at is None:
            insert_at = len(self.lines)
        if insert_at is None:
            self.lines.append(f"\n[{section}]\n")
            insert_at = len(self.lines)
        self.lines.insert(insert_at, f"  {key}    {value}\n")

    def apply(self, params: PLUTOParams, effective_output_dir: str) -> None:
        """Apply all patchable fields from params to the loaded ini lines."""

        # [Time]
        if params.tstop is not None:
            if not self._set_value("Time", "tstop", str(params.tstop)):
                self._append_to_section("Time", "tstop", str(params.tstop))
        if params.cfl is not None:
            if not self._set_value("Time", "CFL", str(params.cfl)):
                self._append_to_section("Time", "CFL", str(params.cfl))
        if params.cfl_max_var is not None:
            if not self._set_value("Time", "CFL_max_var", str(params.cfl_max_var)):
                self._append_to_section("Time", "CFL_max_var", str(params.cfl_max_var))
        if params.first_dt is not None:
            if not self._set_value("Time", "first_dt", str(params.first_dt)):
                self._append_to_section("Time", "first_dt", str(params.first_dt))

        # [Solver]
        if params.solver is not None:
            if not self._set_value("Solver", "Solver", params.solver):
                self._append_to_section("Solver", "Solver", params.solver)

        # [Static Grid Output]  ← CORRECT section name (not "[Output]")
        if effective_output_dir != params.run_dir:
            if not self._set_value("Static Grid Output", "output_dir", effective_output_dir):
                self._append_to_section("Static Grid Output", "output_dir", effective_output_dir)
        if params.log_dir is not None:
            if not self._set_value("Static Grid Output", "log_dir", params.log_dir):
                self._append_to_section("Static Grid Output", "log_dir", params.log_dir)

        # [Parameters]
        for k, v in params.parameters.items():
            if not self._set_value("Parameters", k, str(v)):
                self._append_to_section("Parameters", k, str(v))

    def write(self, path: str) -> None:
        with open(path, "w") as fh:
            fh.writelines(self.lines)


# ─── Snapshot helpers ─────────────────────────────────────────────────────────


def _parse_last_snapshot(output_dir: str) -> dict:
    """
    Return metadata for the last written snapshot.

    Priority order:
      1. dbl.out descriptor (static grid, ground truth per userguide §4.6)
         Columns: n  t  dt  nstep  [single_file]  [endian]  var1 var2 ...
      2. *.dbl.h5 / *.flt.h5  (static grid HDF5)
      3. data.*.hdf5 / chk.*.hdf5  (Chombo-AMR)

    Returns dict with keys: n, t, dt, nstep, rho_max, rho_min
    """
    result = {
        "n": -1,
        "t": float("nan"),
        "dt": float("nan"),
        "nstep": -1,
        "rho_max": float("nan"),
        "rho_min": float("nan"),
    }

    # 1. dbl.out — always preferred (works for all static grid output formats)
    dbl_out = Path(output_dir) / "dbl.out"
    if dbl_out.is_file():
        lines = [line for line in dbl_out.read_text().splitlines() if line.strip()]
        if lines:
            parts = lines[-1].split()
            try:
                result["n"] = int(parts[0])
                result["t"] = float(parts[1])
                result["dt"] = float(parts[2])
                result["nstep"] = int(parts[3])
            except (IndexError, ValueError):
                pass
        # rho is not in dbl.out — skip to HDF5 for field stats if available
        # (fall through; we try HDF5 for rho_max/rho_min only)

    # 2. Static grid HDF5 (.dbl.h5 or .flt.h5) for field statistics
    try:
        import h5py

        h5_files = sorted(
            list(Path(output_dir).glob("*.dbl.h5")) + list(Path(output_dir).glob("*.flt.h5"))
        )
        if h5_files:
            with h5py.File(h5_files[-1]) as hf:
                # pyPLUTO HDF5 layout: variables are top-level datasets
                rho = hf.get("rho") or hf.get("Density") or hf.get("RHO")
                if rho is not None:
                    arr = rho[()]
                    result["rho_max"] = float(arr.max())
                    result["rho_min"] = float(arr.min())
            return result
    except Exception:
        pass

    # 3. Chombo-AMR plot files (data.nnnn.hdf5)
    try:
        import h5py

        chombo_files = sorted(Path(output_dir).glob("data.*.hdf5"))
        if chombo_files:
            last = chombo_files[-1]
            if result["n"] < 0:
                try:
                    result["n"] = int(last.stem.split(".")[1])
                except Exception:
                    pass
            with h5py.File(last) as hf:
                result["t"] = float(hf.attrs.get("time", hf.attrs.get("t", float("nan"))))
                rho = hf.get("rho") or hf.get("Density")
                if rho is not None:
                    arr = rho[()]
                    result["rho_max"] = float(arr.max())
                    result["rho_min"] = float(arr.min())
    except Exception:
        pass

    return result


def _find_latest_snapshot_index(output_dir: str) -> int:
    """
    Return the highest snapshot index from dbl.out, then HDF5 fallbacks.
    Returns -1 if no snapshots found.
    """
    # Primary: dbl.out
    dbl_out = Path(output_dir) / "dbl.out"
    if dbl_out.is_file():
        lines = [line for line in dbl_out.read_text().splitlines() if line.strip()]
        if lines:
            try:
                return int(lines[-1].split()[0])
            except Exception:
                pass

    # Static grid HDF5
    for pattern in ("*.dbl.h5", "*.flt.h5"):
        files = sorted(Path(output_dir).glob(pattern))
        if files:
            try:
                # filename: NNNN.dbl.h5  (PLUTO uses 4-digit zero-padded index)
                return int(files[-1].name.split(".")[0])
            except Exception:
                pass

    # Chombo-AMR plot files
    chombo = sorted(Path(output_dir).glob("data.*.hdf5"))
    if chombo:
        try:
            return int(chombo[-1].stem.split(".")[1])
        except Exception:
            pass

    return -1


# ─── pyPLUTO loader (try new API, fall back to legacy) ───────────────────────


def _load_snapshot_arrays(output_dir: str, snap_n: int):
    """
    Load rho, vx1, vx2 arrays from snapshot snap_n.
    Tries: pyPLUTO new API → pyPLUTO legacy → h5py direct.
    Returns (rho, vx1, vx2) or None.
    """
    # New pyPLUTO API (arXiv:2501.09748, pip install pypluto)
    try:
        import pyPLUTO as pp

        d = pp.Load(snap_n, w_dir=output_dir, datatype="dbl")
        return np.array(d.rho), np.array(d.vx1), np.array(d.vx2)
    except Exception:
        pass

    # Legacy pyPLUTO API (pload)
    try:
        import pyPLUTO as pp

        d = pp.pload(snap_n, w_dir=output_dir)
        return np.array(d.rho), np.array(d.vx1), np.array(d.vx2)
    except Exception:
        pass

    # Direct h5py fallback for static grid HDF5
    try:
        import h5py

        target = f"{snap_n:04d}.dbl.h5"
        h5path = Path(output_dir) / target
        if not h5path.is_file():
            # Try Chombo plot file
            h5path = Path(output_dir) / f"data.{snap_n:04d}.hdf5"
        if h5path.is_file():
            with h5py.File(h5path) as hf:
                rho = hf.get("rho") or hf.get("Density")
                vx1 = hf.get("vx1") or hf.get("Velocity1")
                vx2 = hf.get("vx2") or hf.get("Velocity2")
                if rho is not None and vx1 is not None and vx2 is not None:
                    return rho[()], vx1[()], vx2[()]
    except Exception:
        pass

    return None


# ─── Plotting ─────────────────────────────────────────────────────────────────


def _render_snapshot_plots(
    output_dir: str, plot_dir: str, snap_n: int, quiver_subsample: int
) -> Optional[str]:
    """
    Delegate to plot_pluto.py for geometry-aware, publication-quality output.
    Falls back to a simple inline imshow if plot_pluto.py is not available.
    """
    plot_script = Path(__file__).resolve().parent / "plot_pluto.py"
    if plot_script.is_file():
        try:
            payload = json.dumps(
                {
                    "run_dir": output_dir,
                    "snap": snap_n,
                    "variables": ["rho", "vx1"],
                    "velocity_overlay": True,
                    "quiver_subsample": quiver_subsample,
                    "output_dir": plot_dir,
                    "format": "png",
                    "dpi": 150,
                }
            )
            proc = subprocess.run(
                [sys.executable, str(plot_script), "--json", payload],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode == 0:
                # Return first output path mentioned in stdout
                for line in proc.stdout.splitlines():
                    if line.strip().endswith(".png"):
                        return line.strip()
                return plot_dir
        except Exception:
            pass  # fall through to inline fallback

    # ── Inline fallback (no geometry awareness; pixel-index axes) ──────────
    arrays = _load_snapshot_arrays(output_dir, snap_n)
    if arrays is None:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    rho, vx1, vx2 = arrays
    speed = np.sqrt(vx1 * vx1 + vx2 * vx2)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=150)
    axes[0].imshow(rho, origin="lower", cmap="viridis", aspect="auto")
    axes[0].set_title(f"rho  n={snap_n}")
    axes[1].imshow(speed, origin="lower", cmap="cividis", aspect="auto")
    axes[1].set_title(f"|v|  n={snap_n}")
    os.makedirs(plot_dir, exist_ok=True)
    out_path = os.path.join(plot_dir, f"snapshot_{snap_n:05d}.png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ─── Monitor sidecar ─────────────────────────────────────────────────────────


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _monitor_process(
    *,
    pid: int,
    output_dir: str,
    watch_interval: float,
    plot_on_the_fly: bool,
    plot_interval: float,
    plot_output_dir: str,
    quiver_subsample: int,
    monitor_log: str,
) -> None:
    last_snap = -1
    last_plot_t = 0.0
    with open(monitor_log, "a") as log:
        log.write(f"[monitor] started pid={pid}\n")
        log.flush()
        while _process_is_alive(pid):
            snap_n = _find_latest_snapshot_index(output_dir)
            if snap_n >= 0 and snap_n != last_snap:
                stats = _parse_last_snapshot(output_dir)
                log.write(
                    f"[monitor] snapshot={stats['n']}  t={stats['t']:.6g}  "
                    f"dt={stats['dt']:.3e}  nstep={stats['nstep']}  "
                    f"rho_max={stats['rho_max']:.3e}  rho_min={stats['rho_min']:.3e}\n"
                )
                log.flush()
                last_snap = snap_n

            now = time.time()
            if plot_on_the_fly and snap_n >= 0 and (now - last_plot_t) >= plot_interval:
                out = _render_snapshot_plots(output_dir, plot_output_dir, snap_n, quiver_subsample)
                if out:
                    log.write(f"[monitor] plot={out}\n")
                    log.flush()
                    last_plot_t = now
            time.sleep(watch_interval)
        log.write("[monitor] process finished\n")
        log.flush()


def _spawn_monitor_sidecar(params: PLUTOParams, output_dir: str, pid: int) -> str:
    plot_dir = params.plot_output_dir or os.path.join(output_dir, "live_plots")
    monitor_log = os.path.join(output_dir, "pluto_monitor.log")
    payload = {
        "pid": pid,
        "output_dir": output_dir,
        "watch_interval": params.watch_interval,
        "plot_on_the_fly": params.plot_on_the_fly,
        "plot_interval": params.plot_interval,
        "plot_output_dir": plot_dir,
        "quiver_subsample": params.quiver_subsample,
        "monitor_log": monitor_log,
    }
    subprocess.Popen(
        [sys.executable, __file__, "--monitor-json", json.dumps(payload)],
        cwd=params.run_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return monitor_log


def _monitor_from_payload(payload_json: str) -> int:
    p = json.loads(payload_json)
    _monitor_process(
        pid=int(p["pid"]),
        output_dir=str(p["output_dir"]),
        watch_interval=float(p["watch_interval"]),
        plot_on_the_fly=bool(p["plot_on_the_fly"]),
        plot_interval=float(p["plot_interval"]),
        plot_output_dir=str(p["plot_output_dir"]),
        quiver_subsample=int(p["quiver_subsample"]),
        monitor_log=str(p["monitor_log"]),
    )
    return 0


# ─── Compile helper ───────────────────────────────────────────────────────────


def _read_sysconf(run_dir: str) -> dict:
    """
    Read our extended sysconf.out written by compile_pluto_v4.
    Returns dict with keys: arch, config_num, binary, parallel, modules, compiled_at.
    Returns empty dict if file absent or malformed.
    """
    sc = Path(run_dir) / SYSCONF_NAME
    if not sc.is_file():
        return {}
    result = {}
    for line in sc.read_text().splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _compile_if_needed(params: PLUTOParams, pluto_exe: str) -> None:
    """
    Auto-compile if binary is missing or force_compile was requested.
    Reads sysconf.out to pass matching config_num and modules to the compile script.
    """
    needs_compile = params.force_compile or not os.path.isfile(pluto_exe)
    if not needs_compile:
        return
    if not params.auto_compile and not params.force_compile:
        return

    compile_script = str(_SKILL_DIR / "compile_pluto.py")
    sc = _read_sysconf(params.run_dir)

    cmd = [sys.executable, compile_script, "--run-dir", params.run_dir]

    # Use config_num from params; fall back to sysconf.out
    cfg = params.config_num or (
        int(sc["config_num"]) if sc.get("config_num", "none") != "none" else None
    )
    if cfg is not None:
        cmd += ["--config-num", str(cfg)]

    # Re-pass module flags recorded in sysconf.out
    modules = sc.get("modules", "none")
    if modules and modules != "none":
        for flag in modules.split():
            # Convert "--with-sb" → "--with-sb" (already correct); handle colon form
            if flag == "--with-chombo:":
                cmd.append("--with-chombo")
                cmd.append("--chombo-mpi")
            elif flag == "MPI=TRUE":
                pass  # already handled by --chombo-mpi above
            else:
                # "--with-sb" → "--with-sb"; strip leading dashes for argparse
                cmd.append(flag)

    # Propagate parallel if set
    if sc.get("parallel", "false") == "true":
        cmd.append("--parallel")

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=params.run_dir)
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-20:])
        raise RuntimeError(f"Auto-compile failed.\n{tail}")


# ─── Command builder ──────────────────────────────────────────────────────────


def _build_pluto_cmd(
    params: PLUTOParams, pluto_exe: str, tstop_override: Optional[float] = None
) -> list[str]:
    """
    Assemble the full command list for one PLUTO run stage.

    MPI: uses 'mpirun -np N' (portable; '-n' is OpenMPI-only).
    Decomposition: '-dec n1 [n2] [n3]' (userguide Table 1.3; NOT '-decomp').
    Binary: always './pluto' (never 'pluto_mpi').
    """
    cmd: list[str] = []
    if params.n_procs > 1:
        cmd += ["mpirun", "-np", str(params.n_procs)]

    cmd.append(pluto_exe)

    # Alternative ini file
    if params.ini_file:
        cmd += ["-i", params.ini_file]

    # Restart mode (at most one — validated by model)
    if params.restart is not None:
        cmd += ["-restart", str(params.restart)]
    elif params.h5restart is not None:
        cmd += ["-h5restart", str(params.h5restart)]
    elif params.frestart is not None:
        cmd += ["-frestart", str(params.frestart)]

    # Run control
    if params.maxsteps is not None:
        cmd += ["-maxsteps", str(params.maxsteps)]
    if params.xres is not None:
        cmd += ["-xres", str(params.xres)]
    if params.no_write:
        cmd.append("-no-write")

    # MPI domain decomposition: -dec n1 [n2] [n3]
    if params.decomp and params.n_procs > 1:
        cmd.append("-dec")
        cmd.extend(str(d) for d in params.decomp)

    return cmd


# ─── Atomic backup/restore ────────────────────────────────────────────────────


def _atomic_backup(path: Path) -> Optional[bytes]:
    """Return file contents as bytes, or None if file doesn't exist."""
    if path.is_file():
        return path.read_bytes()
    return None


def _atomic_restore(path: Path, original: Optional[bytes]) -> None:
    """Restore file to its original contents atomically."""
    if original is None:
        path.unlink(missing_ok=True)
        return
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "wb") as fh:
        fh.write(original)
    os.replace(tmp, path)


# ─── Single-stage runner ─────────────────────────────────────────────────────


def _run_single_stage(
    params: PLUTOParams,
    pluto_exe: str,
    output_dir: str,
    tstop: Optional[float],
    restart_n: Optional[int],
    is_h5restart: bool = False,
    is_frestart: bool = False,
) -> tuple[bool, str, dict]:
    """
    Run one PLUTO stage (single tstop).
    Patches pluto.ini, runs PLUTO, restores pluto.ini.
    Returns (success, message, snap_stats).
    """
    ini_name = params.ini_file or "pluto.ini"
    ini_path = Path(params.run_dir) / ini_name
    original_ini = _atomic_backup(ini_path)

    try:
        # Patch ini
        patcher = PLUTOIniPatcher(str(ini_path))
        stage_params = params.model_copy(update={"tstop": tstop} if tstop else {})
        patcher.apply(stage_params, output_dir)
        patcher.write(str(ini_path))

        # Build command
        cmd = _build_pluto_cmd(params, pluto_exe)
        # Inject stage restart
        if restart_n is not None:
            flag = "-h5restart" if is_h5restart else ("-frestart" if is_frestart else "-restart")
            # Remove existing restart flag if any (inserted by _build_pluto_cmd)
            for f in ("-restart", "-h5restart", "-frestart"):
                while f in cmd:
                    idx = cmd.index(f)
                    cmd.pop(idx)
                    cmd.pop(idx)
            cmd += [flag, str(restart_n)]

        t0 = time.monotonic()
        proc = subprocess.run(
            cmd,
            cwd=params.run_dir,
            capture_output=True,
            text=True,
        )
        wall = time.monotonic() - t0

    finally:
        _atomic_restore(ini_path, original_ini)

    snap = _parse_last_snapshot(output_dir)
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or "").splitlines()[-15:])
        return (
            False,
            (
                f"PLUTO exited {proc.returncode}  wall={wall:.1f}s\n"
                f"Last 15 lines stderr:\n{tail}"
            ),
            snap,
        )

    return True, f"wall_clock={wall:.1f}s", snap


# ─── Main simulation entry point ──────────────────────────────────────────────


def run_pluto_simulation(params: PLUTOParams) -> str:
    output_dir = params.output_dir or params.run_dir
    os.makedirs(output_dir, exist_ok=True)

    # Resolve binary (always './pluto' — PLUTO never produces 'pluto_mpi')
    pluto_exe = params.pluto_bin
    if not os.path.isabs(pluto_exe):
        pluto_exe = str(Path(params.run_dir) / pluto_exe.lstrip("./"))

    _compile_if_needed(params, pluto_exe)

    if not os.path.isfile(pluto_exe):
        return (
            f"ERROR: PLUTO binary not found at '{pluto_exe}'.\n"
            "Compile first with:\n"
            f"  python compile_pluto.py --run-dir {params.run_dir}"
        )

    # ── Background mode (single stage only) ───────────────────────────────────
    if params.background:
        ini_name = params.ini_file or "pluto.ini"
        ini_path = Path(params.run_dir) / ini_name
        original_ini = _atomic_backup(ini_path)
        try:
            patcher = PLUTOIniPatcher(str(ini_path))
            patcher.apply(params, output_dir)
            patcher.write(str(ini_path))

            cmd = _build_pluto_cmd(params, pluto_exe)
            run_log = os.path.join(output_dir, "pluto_run.log")
            pid_file = os.path.join(output_dir, "pluto_run.pid")
            log_fh = open(run_log, "a")
            proc = subprocess.Popen(
                cmd,
                cwd=params.run_dir,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
            )
            with open(pid_file, "w") as fh:
                fh.write(str(proc.pid))
        finally:
            _atomic_restore(ini_path, original_ini)

        monitor_log = "none"
        if params.monitor or params.plot_on_the_fly:
            monitor_log = _spawn_monitor_sidecar(params, output_dir, proc.pid)

        return (
            f"STARTED: pid={proc.pid}  run_dir={params.run_dir}\n"
            f"  log={run_log}\n"
            f"  pid_file={pid_file}\n"
            f"  monitor_log={monitor_log}"
        )

    # ── Staged run (checkpoint_times) ─────────────────────────────────────────
    if params.checkpoint_times is not None:
        stages = list(params.checkpoint_times)
        all_snaps = []
        total_wall = 0.0
        restart_n = params.restart  # None for fresh start; set between stages

        for i, stage_tstop in enumerate(stages):
            ok, msg, snap = _run_single_stage(
                params,
                pluto_exe,
                output_dir,
                tstop=stage_tstop,
                restart_n=restart_n,
                is_h5restart=(params.h5restart is not None and i == 0),
                is_frestart=(params.frestart is not None and i == 0),
            )
            # parse wall from msg
            try:
                total_wall += float(msg.split("wall_clock=")[1].split("s")[0])
            except Exception:
                pass
            all_snaps.append(snap)
            if not ok:
                return f"ERROR: stage {i+1}/{len(stages)} (tstop={stage_tstop}) failed.\n{msg}"
            # Restart next stage from the snapshot we just wrote
            restart_n = snap["n"] if snap["n"] >= 0 else None

        last = all_snaps[-1]
        return (
            f"SUCCESS: run_dir={params.run_dir}  stages={len(stages)}  "
            f"wall_clock={total_wall:.1f}s\n"
            f"  last_snapshot={last['n']}  t={last['t']:.4g} (code units)\n"
            f"  dt_last={last['dt']:.3e}  nstep={last['nstep']}\n"
            f"  rho_max={last['rho_max']:.3e}  rho_min={last['rho_min']:.3e}"
        )

    # ── Single-stage foreground run ────────────────────────────────────────────
    ok, msg, snap = _run_single_stage(
        params,
        pluto_exe,
        output_dir,
        tstop=params.tstop,
        restart_n=params.restart,
        is_h5restart=(params.h5restart is not None),
        is_frestart=(params.frestart is not None),
    )
    if not ok:
        return f"ERROR: {msg}"

    wall = float(msg.split("wall_clock=")[1].split("s")[0]) if "wall_clock=" in msg else 0.0
    return (
        f"SUCCESS: run_dir={params.run_dir}  stages=1  wall_clock={wall:.1f}s\n"
        f"  last_snapshot={snap['n']}  t={snap['t']:.4g} (code units)\n"
        f"  dt_last={snap['dt']:.3e}  nstep={snap['nstep']}\n"
        f"  rho_max={snap['rho_max']:.3e}  rho_min={snap['rho_min']:.3e}"
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Patch pluto.ini and run PLUTO.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--json", metavar="JSON", help="JSON string or path to JSON file with all parameters"
    )
    p.add_argument("--monitor-json", dest="monitor_json", help=argparse.SUPPRESS)

    # Location
    p.add_argument("--run-dir", dest="run_dir")
    p.add_argument("--output-dir", dest="output_dir")

    # Time
    p.add_argument("--tstop", type=float)
    p.add_argument("--cfl", type=float)
    p.add_argument("--cfl-max-var", type=float, dest="cfl_max_var")
    p.add_argument("--first-dt", type=float, dest="first_dt")
    p.add_argument(
        "--checkpoint-times", dest="checkpoint_times", help="JSON array, e.g. '[100,200,500]'"
    )

    # Solver / parameters
    p.add_argument("--solver")
    p.add_argument("--parameters", type=json.loads, help="JSON object, e.g. '{\"ALPHA\": 1e-3}'")

    # Runtime flags
    p.add_argument("--ini-file", dest="ini_file")
    p.add_argument("--restart", type=int)
    p.add_argument("--h5restart", type=int, dest="h5restart")
    p.add_argument("--frestart", type=int, dest="frestart")
    p.add_argument("--maxsteps", type=int, dest="maxsteps")
    p.add_argument("--xres", type=int, dest="xres")
    p.add_argument("--no-write", action="store_true", dest="no_write")
    p.add_argument("--pluto-bin", dest="pluto_bin")

    # MPI
    p.add_argument("--n-procs", type=int, dest="n_procs")
    p.add_argument(
        "--decomp",
        type=json.loads,
        help="JSON int array, e.g. '[2,2]'  (product must equal n_procs)",
    )

    # Compile integration
    p.add_argument("--config-num", type=int, dest="config_num")
    p.add_argument("--auto-compile", dest="auto_compile", action="store_true", default=None)
    p.add_argument("--no-auto-compile", dest="auto_compile", action="store_false")
    p.add_argument("--force-compile", action="store_true", dest="force_compile")

    # Background / monitoring
    p.add_argument("--background", action="store_true")
    p.add_argument("--monitor", action="store_true")
    p.add_argument("--watch-interval", type=float, dest="watch_interval")
    p.add_argument("--plot-on-the-fly", action="store_true", dest="plot_on_the_fly")
    p.add_argument("--plot-interval", type=float, dest="plot_interval")
    p.add_argument("--plot-output-dir", dest="plot_output_dir")
    p.add_argument("--quiver-subsample", type=int, dest="quiver_subsample")

    # Output dir extras
    p.add_argument("--log-dir", dest="log_dir")

    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.monitor_json:
        sys.exit(_monitor_from_payload(args.monitor_json))

    raw: dict = {
        k: v for k, v in vars(args).items() if v is not None and k not in {"json", "monitor_json"}
    }

    if args.json:
        src = args.json.strip()
        if os.path.isfile(src):
            with open(src) as fh:
                raw = json.load(fh)
        else:
            raw = json.loads(src)

    try:
        params = PLUTOParams(**raw)
    except Exception as exc:
        print(f"ERROR: parameter validation failed — {exc}", file=sys.stderr)
        sys.exit(1)

    result = run_pluto_simulation(params)
    print(result)
    sys.exit(1 if result.startswith("ERROR") else 0)


if __name__ == "__main__":
    main()
