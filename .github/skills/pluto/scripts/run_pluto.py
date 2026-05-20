#!/usr/bin/env python3
"""
PLUTO ini patcher and runner with Pydantic v2 parameter validation.

Usage (agent / JSON form):
    python run_pluto.py --json '{"run_dir": "runs/disk", "tstop": 500, "parameters": {"ALPHA": 1e-3}}'

Usage (CLI form):
    python run_pluto.py --run-dir runs/disk --tstop 500 --n-procs 4
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import typing as ty
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator
from scientific_pydantic.numpy import NDArrayAdapter


# ---------------------------------------------------------------------------
# Pydantic parameter model
# ---------------------------------------------------------------------------

class PLUTOParams(BaseModel):
    run_dir: str
    output_dir: Optional[str] = None          # defaults to run_dir
    tstop: Optional[float] = Field(default=None, gt=0.0)
    cfl: Optional[float] = Field(default=None, ge=0.1, le=0.9)
    first_dt: Optional[float] = Field(default=None, gt=0.0)
    solver: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    n_procs: int = Field(default=1, ge=1, le=512)
    pluto_bin: str = "./pluto"
    restart: Optional[int] = Field(default=None, ge=0)
    # Optional staged-run schedule: PLUTO is called once per checkpoint, with
    # automatic restarts between stops.  Mutually exclusive with `tstop`.
    checkpoint_times: ty.Optional[ty.Annotated[
        np.ndarray, NDArrayAdapter(ndim=1, dtype="float64", gt=0.0)
    ]] = None

    @field_validator("tstop", "cfl", "first_dt", mode="before")
    @classmethod
    def coerce_scientific_notation(cls, v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                pass
        return v

    @field_validator("parameters", mode="before")
    @classmethod
    def coerce_parameters(cls, v):
        """Accept a JSON string for parameters dict."""
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def run_dir_exists(self):
        if not os.path.isdir(self.run_dir):
            raise ValueError(f"run_dir does not exist: {self.run_dir!r}")
        ini = os.path.join(self.run_dir, "pluto.ini")
        if not os.path.isfile(ini):
            raise ValueError(f"pluto.ini not found in run_dir: {self.run_dir!r}")
        if self.tstop is not None and self.checkpoint_times is not None:
            raise ValueError(
                "Specify either 'tstop' or 'checkpoint_times', not both."
            )
        return self


# ---------------------------------------------------------------------------
# pluto.ini patcher
# ---------------------------------------------------------------------------

class PLUTOIniPatcher:
    """Line-based patcher for pluto.ini that preserves structure."""

    _SECTION_RE = re.compile(r"^\[(.+)\]\s*$")
    _KEY_RE = re.compile(r"^(\s*)(\S+)(\s+)(.*?)(\s*)$")

    def __init__(self, ini_path: str):
        self.ini_path = ini_path
        with open(ini_path) as fh:
            self.lines = fh.readlines()

    def _set_value(self, section: str, key: str, value: str) -> bool:
        """Overwrite the value of `key` inside `section`.  Returns True if found."""
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
                # Replace only the value part (column 4 of the match)
                self.lines[i] = f"{km.group(1)}{km.group(2)}{km.group(3)}{value}\n"
                return True
        return False

    def _append_to_section(self, section: str, key: str, value: str) -> None:
        """Append a new key=value line at the end of `section`."""
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
            # Section not found — append it
            self.lines.append(f"\n[{section}]\n")
            insert_at = len(self.lines)
        self.lines.insert(insert_at, f"  {key}    {value}\n")

    def apply(
        self,
        tstop: Optional[float] = None,
        cfl: Optional[float] = None,
        first_dt: Optional[float] = None,
        solver: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        if tstop is not None:
            if not self._set_value("Time", "tstop", str(tstop)):
                self._append_to_section("Time", "tstop", str(tstop))
        if cfl is not None:
            if not self._set_value("Time", "CFL", str(cfl)):
                self._append_to_section("Time", "CFL", str(cfl))
        if first_dt is not None:
            if not self._set_value("Time", "first_dt", str(first_dt)):
                self._append_to_section("Time", "first_dt", str(first_dt))
        if solver is not None:
            if not self._set_value("Solver", "Solver", solver):
                self._append_to_section("Solver", "Solver", solver)
        if output_dir is not None:
            if not self._set_value("Output", "output_dir", output_dir):
                self._append_to_section("Output", "output_dir", output_dir)
        if parameters:
            for k, v in parameters.items():
                if not self._set_value("Parameters", k, str(v)):
                    self._append_to_section("Parameters", k, str(v))

    def write(self, path: str) -> None:
        with open(path, "w") as fh:
            fh.writelines(self.lines)


# ---------------------------------------------------------------------------
# Snapshot parser helpers
# ---------------------------------------------------------------------------

def _parse_last_snapshot(run_dir: str) -> dict:
    """Return {'n': int, 't': float, 'rho_max': float, 'rho_min': float}."""
    result = {"n": -1, "t": float("nan"), "rho_max": float("nan"), "rho_min": float("nan")}

    # Try HDF5 first
    try:
        import h5py
        hdf_files = sorted(Path(run_dir).glob("data.*.hdf5"))
        if hdf_files:
            last = hdf_files[-1]
            result["n"] = int(last.stem.split(".")[1])
            with h5py.File(last) as hf:
                result["t"] = float(hf.attrs.get("t", float("nan")))
                rho = hf.get("rho") or hf.get("Density")
                if rho is not None:
                    arr = rho[()]
                    result["rho_max"] = float(arr.max())
                    result["rho_min"] = float(arr.min())
            return result
    except ImportError:
        pass
    except Exception:
        pass

    # Fall back to dbl.out
    dbl_out = os.path.join(run_dir, "dbl.out")
    if os.path.isfile(dbl_out):
        with open(dbl_out) as fh:
            lines = [l for l in fh.readlines() if l.strip()]
        if lines:
            last_line = lines[-1].split()
            try:
                result["n"] = int(last_line[0])
                result["t"] = float(last_line[1])
            except (IndexError, ValueError):
                pass
    return result


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_pluto_simulation(params: PLUTOParams) -> str:
    ini_path = os.path.join(params.run_dir, "pluto.ini")
    backup_path = ini_path + ".bak_skill"
    output_dir = params.output_dir or params.run_dir

    os.makedirs(output_dir, exist_ok=True)

    # Back up original ini
    shutil.copy2(ini_path, backup_path)

    try:
        patcher = PLUTOIniPatcher(ini_path)
        patcher.apply(
            tstop=params.tstop,
            cfl=params.cfl,
            first_dt=params.first_dt,
            solver=params.solver,
            parameters=params.parameters,
            output_dir=output_dir if output_dir != params.run_dir else None,
        )
        patcher.write(ini_path)

        # Build command
        pluto_exe = params.pluto_bin
        if not os.path.isabs(pluto_exe):
            pluto_exe = os.path.join(params.run_dir, pluto_exe.lstrip("./"))
        if not os.path.isfile(pluto_exe):
            pluto_exe = shutil.which("pluto") or params.pluto_bin

        cmd: list[str] = []
        if params.n_procs > 1:
            cmd += ["mpirun", "-n", str(params.n_procs)]
        cmd += [pluto_exe]
        if params.restart is not None:
            cmd += ["-restart", str(params.restart)]

        t0 = time.time()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=params.run_dir,
        )
        t_wall = time.time() - t0

    finally:
        # Always restore original ini
        shutil.move(backup_path, ini_path)

    if proc.returncode != 0:
        stderr_tail = "\n".join(proc.stderr.splitlines()[-15:])
        return (
            f"ERROR: PLUTO exited with code {proc.returncode}\n"
            f"Last 15 lines of stderr:\n{stderr_tail}"
        )

    snap = _parse_last_snapshot(output_dir)
    assert last_proc is not None
    warnings = [l for l in last_proc.stderr.splitlines() if "warn" in l.lower()]
    warn_str = "; ".join(warnings[:5]) if warnings else "none"
    n_stages = len(stops)

    return (
        f"SUCCESS: run_dir={params.run_dir}  stages={n_stages}  wall_clock={t_wall:.1f}s\n"
        f"  last_snapshot={snap['n']}  t={snap['t']:.4g} (code units)\n"
        f"  rho_max={snap['rho_max']:.3e}  rho_min={snap['rho_min']:.3e}\n"
        f"  warnings: {warn_str}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Patch pluto.ini and run PLUTO.")
    p.add_argument("--json", metavar="JSON", help="JSON string or file with all parameters")
    p.add_argument("--run-dir", dest="run_dir")
    p.add_argument("--output-dir", dest="output_dir")
    p.add_argument("--tstop", type=float)
    p.add_argument("--cfl", type=float)
    p.add_argument("--first-dt", type=float, dest="first_dt")
    p.add_argument("--solver")
    p.add_argument("--n-procs", type=int, dest="n_procs")
    p.add_argument("--pluto-bin", dest="pluto_bin")
    p.add_argument("--restart", type=int)
    p.add_argument(
        "--checkpoint-times",
        dest="checkpoint_times",
        help="JSON array of staged tstop values, e.g. '[100,200,500]'",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    raw: dict = {k: v for k, v in vars(args).items() if v is not None and k != "json"}

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
    if result.startswith("ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
