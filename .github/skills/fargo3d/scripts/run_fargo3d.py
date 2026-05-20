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
    Tmax: Optional[float] = Field(default=None, gt=0.0)
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
        "AspectRatio", "Sigma0", "Alpha", "FlaringIndex",
        "PlanetMass", "Tmax", "DT",
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

    # Count gas density outputs
    dens_files = sorted(out.glob("gasdens*.dat"))
    result["n_outputs"] = len(dens_files)
    if not dens_files:
        return result

    # Read last density file
    last_dens = dens_files[-1]
    try:
        sigma = np.fromfile(str(last_dens), dtype=np.float64)
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

    # Planet torque: try tqwk0.dat (col 3) then bigplanet0.dat (col 3)
    for fname in ("tqwk0.dat", "bigplanet0.dat"):
        fpath = out / fname
        if fpath.is_file():
            try:
                data = np.loadtxt(str(fpath))
                if data.ndim == 2 and data.shape[1] >= 4:
                    result["planet_torque"] = float(data[-1, 3])
                break
            except Exception:
                pass

    return result


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_fargo3d_simulation(params: FARGO3DParams) -> str:
    os.makedirs(params.output_dir, exist_ok=True)

    # Build overrides dict from model (only non-None physical params)
    overrides: Dict[str, Any] = {}
    for attr in ("AspectRatio", "Sigma0", "Alpha", "FlaringIndex",
                 "PlanetMass", "Tmax", "Ninterm", "DT", "Nx", "Ny"):
        v = getattr(params, attr)
        if v is not None:
            overrides[attr] = v
    overrides["OutputDir"] = params.output_dir
    overrides.update(params.extra_params)

    # Patch .par and write to output_dir
    patcher = FARGOParPatcher(params.par_file)
    patched_par = os.path.join(params.output_dir, Path(params.par_file).name)
    sigma0_ref = params.Sigma0 or (
        float(patcher.read_value("Sigma0") or "nan") if patcher.read_value("Sigma0") else None
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
        return f"ERROR: fargo3d binary not found: {fargo_exe!r}"

    # Build command
    cmd: list[str] = []
    if params.n_procs > 1:
        cmd += ["mpirun", "-n", str(params.n_procs)]
    cmd += [fargo_exe]
    mode_flag = "-m" if params.gpu else "-0"
    cmd += [mode_flag, patched_par]

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
        return (
            f"ERROR: fargo3d exited with code {proc.returncode}\n"
            f"Last 15 lines of stderr:\n{stderr_tail}"
        )

    diag = _parse_fargo_output(params.output_dir, sigma0_ref)

    return (
        f"SUCCESS: output_dir={params.output_dir}  wall_clock={t_wall:.1f}s\n"
        f"  n_outputs={diag['n_outputs']}  last_orbit={diag['last_orbit']:.2f}\n"
        f"  Sigma_min={diag['Sigma_min']:.3e}  Sigma_max={diag['Sigma_max']:.3e}"
        f"  gap_depth={diag['gap_depth']:.4f}\n"
        f"  planet_torque={diag['planet_torque']:.3e} (last output)"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Patch a FARGO3D .par file and run.")
    p.add_argument("--json", metavar="JSON", help="JSON string or file with all parameters")
    p.add_argument("--par-file", dest="par_file")
    p.add_argument("--output-dir", dest="output_dir")
    p.add_argument("--AspectRatio", type=float)
    p.add_argument("--Sigma0", type=float)
    p.add_argument("--Alpha", type=float)
    p.add_argument("--FlaringIndex", type=float)
    p.add_argument("--PlanetMass", type=float)
    p.add_argument("--Tmax", type=float)
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
    print(result)
    if result.startswith("ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
