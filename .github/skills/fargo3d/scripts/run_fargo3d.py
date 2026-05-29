#!/usr/bin/env python3
"""
FARGO3D par-file patcher and runner with Pydantic v2 parameter validation.

Usage (agent / JSON form):
    python run_fargo3d.py --json '{"par_file": "setups/p_gap/p_gap.par",
                                   "output_dir": "out/run01", "Alpha": 1e-3}'

Usage (CLI form):
    python run_fargo3d.py --par-file setups/p_gap/p_gap.par \
                          --output-dir out/run01 --Alpha 1e-3 --PlanetMass 3e-4
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Pydantic parameter model
# ---------------------------------------------------------------------------


class FARGO3DParams(BaseModel):
    par_file: str
    output_dir: str

    # Disk / physical parameters (all optional — keep original if None)
    AspectRatio: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    Sigma0: Optional[float] = Field(default=None, gt=0.0)
    Alpha: Optional[float] = Field(default=None, ge=0.0, le=0.1)
    FlaringIndex: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    PlanetMass: Optional[float] = Field(default=None, ge=0.0)

    # Time integration
    # NOTE: use Ntot for setups that do NOT support Tmax (e.g. fargo, fargo_nu).
    # Tmax is accepted by some setups (p3diso etc.) but ignored with a warning
    # in others — always prefer Ntot when uncertain.  Pass only one of the two.
    Tmax: Optional[float] = Field(default=None, gt=0.0)
    Ntot: Optional[int] = Field(default=None, ge=1)   # total DT steps
    Ninterm: Optional[int] = Field(default=None, ge=1)
    DT: Optional[float] = Field(default=None, gt=0.0)

    # Grid
    Nx: Optional[int] = Field(default=None, ge=8, le=4096)
    Ny: Optional[int] = Field(default=None, ge=8, le=1024)

    # Extra / arbitrary .par keys
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    # Execution
    fargo3d_bin: str = "./fargo3d"
    n_procs: int = Field(default=1, ge=1, le=512)
    gpu: bool = False

    @field_validator(
        "AspectRatio",
        "Sigma0",
        "Alpha",
        "FlaringIndex",
        "PlanetMass",
        "Tmax",
        "DT",
        mode="before",
    )
    @classmethod
    def coerce_scientific_notation(cls, v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                pass
        return v

    @field_validator("extra_params", mode="before")
    @classmethod
    def coerce_extra_params(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def par_file_exists(self):
        if not os.path.isfile(self.par_file):
            raise ValueError(f"par_file not found: {self.par_file!r}")
        return self


# ---------------------------------------------------------------------------
# FARGO3D .par patcher
# ---------------------------------------------------------------------------


class FARGOParPatcher:
    """Read, patch, and write a FARGO3D .par file (KEY   VALUE per line)."""

    _KV_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S+)(.*?)$")

    def __init__(self, par_path: str):
        self.par_path = par_path
        with open(par_path) as fh:
            self.lines = fh.readlines()

    def _set(self, key: str, value: str) -> bool:
        """Set `key` to `value`.  Returns True if key was found and updated."""
        for i, line in enumerate(self.lines):
            if line.strip().startswith("#"):
                continue
            m = self._KV_RE.match(line)
            if m and m.group(2).upper() == key.upper():
                self.lines[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{value}\n"
                return True
        return False

    def apply(self, overrides: Dict[str, Any]) -> None:
        for key, value in overrides.items():
            if not self._set(key, str(value)):
                # Append new key
                self.lines.append(f"{key}    {value}\n")

    def write(self, dest: str) -> None:
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(dest, "w") as fh:
            fh.writelines(self.lines)

    def read_value(self, key: str) -> Optional[str]:
        for line in self.lines:
            if line.strip().startswith("#"):
                continue
            m = self._KV_RE.match(line)
            if m and m.group(2).upper() == key.upper():
                return m.group(4)
        return None


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------


def _parse_fargo_output(output_dir: str, sigma0_ref: Optional[float]) -> dict:
    """Parse last gasdens*.dat and planet files for diagnostics."""
    result = {
        "n_outputs": 0,
        "last_orbit": float("nan"),
        "Sigma_min": float("nan"),
        "Sigma_max": float("nan"),
        "gap_depth": float("nan"),
        "planet_torque": float("nan"),
    }

    out = Path(output_dir)
    if not out.is_dir():
        return result

    # Count gas density outputs (exclude *_2d.dat Stockholm reference files)
    dens_files = sorted(f for f in out.glob("gasdens*.dat") if "_2d" not in f.name)
    result["n_outputs"] = len(dens_files)
    if not dens_files:
        return result

    # Read last density file (azimuthal average for gap depth)
    last_dens = dens_files[-1]
    try:
        raw = np.fromfile(str(last_dens), dtype=np.float64)
        # Try to compute azimuthal average; fall back to raw if shape unknown
        nr, nphi = 128, 384
        if raw.size == nr * nphi:
            sigma = raw.reshape(nr, nphi).mean(axis=1)
        else:
            sigma = raw
        result["Sigma_min"] = float(sigma.min())
        result["Sigma_max"] = float(sigma.max())
        if sigma0_ref and sigma0_ref > 0:
            result["gap_depth"] = float(sigma.min() / sigma0_ref)
    except Exception:
        pass

    # Last orbit from summary or big planet file
    summary = out / "summary0.dat"
    if summary.is_file():
        try:
            with open(summary) as fh:
                lines = [line for line in fh.readlines() if line.strip()]
            if lines:
                result["last_orbit"] = float(lines[-1].split()[0])
        except Exception:
            pass

    # Planet torque from tqwk0.dat
    # Column layout (fargo_nu + STOCKHOLM, 10 cols):
    # 0:output_num  1-5:partial_torques  6:total_torque  7:work  8:work_res  9:time
    # Use last non-zero time row, col 6 = total torque.
    for fname in ("tqwk0.dat", "bigplanet0.dat"):
        fpath = out / fname
        if fpath.is_file():
            try:
                data = np.loadtxt(str(fpath))
                if data.ndim == 1:
                    data = data[np.newaxis, :]
                # Filter rows with non-zero time (col 9 if 10 cols, else col 0)
                time_col = 9 if data.shape[1] >= 10 else 0
                torque_col = 6 if data.shape[1] >= 10 else min(3, data.shape[1] - 1)
                nz = data[data[:, time_col] > 0]
                if len(nz) > 0:
                    result["planet_torque"] = float(nz[-1, torque_col])
                break
            except Exception:
                pass

    return result


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------


def _fargo3d_version(fargo_exe: str) -> str:
    """Return git hash of the FARGO3D source tree, or 'unknown'."""
    try:
        import subprocess as _sp
        src_dir = str(Path(fargo_exe).resolve().parent)
        return _sp.check_output(
            ["git", "-C", src_dir, "rev-parse", "--short", "HEAD"],
            text=True, stderr=_sp.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def run_fargo3d_simulation(params: FARGO3DParams) -> dict:
    os.makedirs(params.output_dir, exist_ok=True)

    # Build overrides dict from model (only non-None physical params)
    overrides: Dict[str, Any] = {}
    for attr in (
        "AspectRatio",
        "Sigma0",
        "Alpha",
        "FlaringIndex",
        "PlanetMass",
        "Tmax",
        "Ntot",
        "Ninterm",
        "DT",
        "Nx",
        "Ny",
    ):
        v = getattr(params, attr)
        if v is not None:
            overrides[attr] = v
    # Always use an absolute OutputDir so FARGO3D writes to the correct location
    # regardless of the cwd used to launch the binary (which is typically the
    # directory containing the FARGO3D executable, not the workspace root).
    overrides["OutputDir"] = str(Path(params.output_dir).resolve())
    overrides.update(params.extra_params)

    # Patch .par and write to output_dir
    patcher = FARGOParPatcher(params.par_file)
    patched_par = os.path.join(params.output_dir, Path(params.par_file).name)
    sigma0_ref = params.Sigma0 or (
        float(patcher.read_value("Sigma0") or "nan")
        if patcher.read_value("Sigma0")
        else None
    )
    patcher.apply(overrides)
    patcher.write(patched_par)

    # Resolve binary
    fargo_exe = params.fargo3d_bin
    if not os.path.isabs(fargo_exe):
        resolved = shutil.which(Path(fargo_exe).name)
        if resolved:
            fargo_exe = resolved

    if not os.path.isfile(fargo_exe):
        return {"status": "ERROR", "errors": [f"fargo3d binary not found: {fargo_exe!r}"]}

    # Build command
    # NOTE: FARGO3D flag semantics:
    #   -0  → OnlyInit (write initial condition only, NO time stepping) — do NOT use
    #   -m  → Merge output files from parallel ranks (harmless for sequential)
    #   (no flag) → sequential CPU run with full time evolution
    cmd: list[str] = []
    if params.n_procs > 1:
        cmd += ["mpirun", "-n", str(params.n_procs)]
    cmd += [fargo_exe]
    if params.gpu:
        cmd += ["-m"]  # GPU/parallel merge mode
    # Sequential CPU: pass par file directly — no flag that would set OnlyInit
    cmd += [os.path.abspath(patched_par)]

    t0 = time.time()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(fargo_exe) or ".",
    )
    t_wall = time.time() - t0

    if proc.returncode != 0:
        stderr_tail = "\n".join(proc.stderr.splitlines()[-15:])
        return {
            "status": "ERROR",
            "errors": [
                f"fargo3d exited with code {proc.returncode}",
                f"Last 15 lines of stderr:\n{stderr_tail}",
            ],
        }

    diag = _parse_fargo_output(params.output_dir, sigma0_ref)

    return {
        "status": "SUCCESS",
        "run_dir": str(params.output_dir),
        "output_dir": str(params.output_dir),
        "code": "FARGO3D",
        "git_hash": _fargo3d_version(fargo_exe),
        "n_snapshots": diag["n_outputs"],
        "last_orbit": diag["last_orbit"],
        "sigma_min": diag["Sigma_min"],
        "sigma_max": diag["Sigma_max"],
        "gap_depth": diag["gap_depth"],
        "planet_torque": diag["planet_torque"],
        "wall_time_s": round(t_wall, 1),
        "errors": [],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Patch a FARGO3D .par file and run.")
    p.add_argument(
        "--json", metavar="JSON", help="JSON string or file with all parameters"
    )
    p.add_argument("--par-file", dest="par_file")
    p.add_argument("--output-dir", dest="output_dir")
    p.add_argument("--AspectRatio", type=float)
    p.add_argument("--Sigma0", type=float)
    p.add_argument("--Alpha", type=float)
    p.add_argument("--FlaringIndex", type=float)
    p.add_argument("--PlanetMass", type=float)
    p.add_argument("--Tmax", type=float,
                   help="Max simulation time (code units). Not valid for all setups; "
                        "prefer --Ntot for fargo/fargo_nu.")
    p.add_argument("--Ntot", type=int,
                   help="Total number of DT steps (preferred over --Tmax for "
                        "fargo/fargo_nu setups).")
    p.add_argument("--Ninterm", type=int)
    p.add_argument("--DT", type=float)
    p.add_argument("--Nx", type=int)
    p.add_argument("--Ny", type=int)
    p.add_argument("--fargo3d-bin", dest="fargo3d_bin")
    p.add_argument("--n-procs", type=int, dest="n_procs")
    p.add_argument("--gpu", action="store_true")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    raw: dict = {k: v for k, v in vars(args).items() if v is not None and k != "json"}
    # argparse stores False for store_true when not set — keep it if gpu flag was passed
    if not args.gpu:
        raw.pop("gpu", None)

    if args.json:
        src = args.json.strip()
        if os.path.isfile(src):
            with open(src) as fh:
                raw = json.load(fh)
        else:
            raw = json.loads(src)

    try:
        params = FARGO3DParams(**raw)
    except Exception as exc:
        print(f"ERROR: parameter validation failed — {exc}", file=sys.stderr)
        sys.exit(1)

    result = run_fargo3d_simulation(params)
    print(json.dumps(result))
    if result.get("status") != "SUCCESS":
        sys.exit(1)


if __name__ == "__main__":
    main()
