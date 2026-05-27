#!/usr/bin/env python3
"""
DustPy runner with Pydantic v2 parameter validation.

Usage (agent / JSON form):
    python run_dustpy.py --json '{"alpha_viscosity": 1e-3, "disk_mass_msun": 0.05}'

Usage (CLI form):
    python run_dustpy.py --alpha 1e-3 --disk-mass 0.05 --t-end 1e6
"""

import argparse
import json
import os
import sys
import time
import typing as ty

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator
from scientific_pydantic.numpy import NDArrayAdapter

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
M_SUN_G = 1.989e33  # grams
R_SUN_CM = 6.957e10  # cm
AU_TO_CM = 1.496e13  # cm / au
YR_TO_S = 3.1536e7  # s / yr


# ---------------------------------------------------------------------------
# Pydantic parameter model
# ---------------------------------------------------------------------------


class DustPyParams(BaseModel):
    alpha_viscosity: float = Field(default=1e-3, ge=1e-6, le=1e-1)
    disk_mass_msun: float = Field(default=0.05, gt=0.0, le=1.0)
    stellar_mass_msun: float = Field(default=1.0, gt=0.0, le=100.0)
    stellar_radius_rsun: float = Field(default=2.0, gt=0.0, le=1000.0)
    stellar_temperature_K: float = Field(default=5772.0, gt=100.0, le=1e6)
    dust_to_gas_ratio: float = Field(default=0.01, gt=0.0, le=0.5)
    r_in_au: float = Field(default=1.0, gt=0.0)
    r_out_au: float = Field(default=300.0, gt=0.0)
    N_r: int = Field(default=100, ge=10, le=500)
    # Mass grid resolution: must be >=7 (Drążkowska+ 2014); larger = slower.
    Nmbpd: int = Field(default=7, ge=7, le=20)
    # Gas surface density profile (Lynden-Bell & Pringle 1974)
    gas_sigma_exp: float = Field(default=-1.0, ge=-3.0, le=0.0)
    gas_sigma_rc_au: float = Field(default=60.0, gt=0.0)
    monomer_density_gcc: float = Field(default=1.67, gt=0.0, le=10.0)
    t_end_yr: float = Field(default=1e6, gt=0.0)
    fragmentation_velocity_ms: float = Field(default=10.0, gt=0.0, le=100.0)
    N_snapshots: int = Field(default=100, ge=10, le=1000)
    # Optional custom snapshot schedule; overrides N_snapshots when provided.
    # Accepts a JSON list ([1e4, 1e5, 1e6]) or a Python list / np.ndarray.
    snapshot_times_yr: ty.Optional[
        ty.Annotated[np.ndarray, NDArrayAdapter(ndim=1, dtype="float64", gt=0.0)]
    ] = None
    output_dir: str = Field(default="dustpy_out")

    @field_validator(
        "alpha_viscosity",
        "disk_mass_msun",
        "stellar_mass_msun",
        "stellar_radius_rsun",
        "stellar_temperature_K",
        "dust_to_gas_ratio",
        "r_in_au",
        "r_out_au",
        "gas_sigma_rc_au",
        "monomer_density_gcc",
        "t_end_yr",
        "fragmentation_velocity_ms",
        mode="before",
    )
    @classmethod
    def coerce_scientific_notation(cls, v):
        """Allow LLMs to pass floats as strings like '1e-3'."""
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                pass
        return v

    @model_validator(mode="after")
    def check_geometry_and_snapshots(self):
        if self.r_out_au <= self.r_in_au:
            raise ValueError(f"r_out_au ({self.r_out_au}) must be > r_in_au ({self.r_in_au})")
        # When a custom snapshot schedule is given, derive t_end_yr from it
        # so the caller does not have to supply both.
        if self.snapshot_times_yr is not None:
            self.t_end_yr = float(self.snapshot_times_yr.max())
        return self


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------


def run_dustpy_simulation(params: DustPyParams) -> str:
    """Run a DustPy simulation with validated params.  Returns a plain-text result string."""
    try:
        from dustpy import Simulation
    except ImportError:
        return "ERROR: dustpy not found — install with: pip install dustpy"

    t0 = time.time()

    os.makedirs(params.output_dir, exist_ok=True)

    sim = Simulation()

    # --- gas ---
    sim.ini.gas.alpha = params.alpha_viscosity
    sim.ini.gas.Mdisk = params.disk_mass_msun * M_SUN_G
    sim.ini.gas.SigmaExp = params.gas_sigma_exp
    sim.ini.gas.SigmaRc = params.gas_sigma_rc_au * AU_TO_CM

    # --- star ---
    # Note: sim.ini.star has M, R, T only.  Luminosity L is derived from R and T.
    sim.ini.star.M = params.stellar_mass_msun * M_SUN_G
    sim.ini.star.R = params.stellar_radius_rsun * R_SUN_CM
    sim.ini.star.T = params.stellar_temperature_K

    # --- dust ---
    sim.ini.dust.d2gRatio = params.dust_to_gas_ratio
    sim.ini.dust.vFrag = params.fragmentation_velocity_ms * 100.0  # m/s → cm/s
    sim.ini.dust.rhoMonomer = params.monomer_density_gcc

    # --- grid ---
    sim.ini.grid.Nr = params.N_r
    sim.ini.grid.Nmbpd = params.Nmbpd
    sim.ini.grid.rmin = params.r_in_au * AU_TO_CM
    sim.ini.grid.rmax = params.r_out_au * AU_TO_CM

    # --- output ---
    sim.writer.datadir = params.output_dir

    # Initialise before setting snapshots (ini parameters are frozen after this).
    sim.initialize()

    t_end_s = params.t_end_yr * YR_TO_S
    if params.snapshot_times_yr is not None:
        # Use the validated, typed ndarray directly (already in years)
        sim.t.snapshots = params.snapshot_times_yr * YR_TO_S
    else:
        sim.t.snapshots = np.geomspace(
            max(t_end_s / params.N_snapshots, YR_TO_S),  # first snap ≥ 1 yr
            t_end_s,
            params.N_snapshots,
        )

    sim.run()

    # --- post-processing summary ---
    t_wall = time.time() - t0

    # Final gas and dust mass
    try:
        final_gas_mass = float((sim.grid.A * sim.gas.Sigma).sum() / M_SUN_G)
        final_dust_mass = float((sim.grid.A * sim.dust.Sigma.sum(-1)).sum() / M_SUN_G)
    except Exception:
        final_gas_mass = float("nan")
        final_dust_mass = float("nan")

    # Maximum grain size at 10 au and 100 au
    def _amax_at_radius(r_au: float) -> float:
        try:
            r_cm = r_au * AU_TO_CM
            idx = int(np.argmin(np.abs(sim.grid.r - r_cm)))
            return float(sim.dust.a[idx, np.argmax(sim.dust.Sigma[idx])])
        except Exception:
            return float("nan")

    a_10 = _amax_at_radius(10.0)
    a_100 = _amax_at_radius(100.0)

    n_snaps = len([f for f in os.listdir(params.output_dir) if f.endswith(".hdf5")])

    return (
        f"SUCCESS: output_dir={params.output_dir}  t_end={params.t_end_yr:.2e}yr  "
        f"N_snaps={n_snaps}\n"
        f"  final_gas_mass={final_gas_mass:.3e} Msun  "
        f"final_dust_mass={final_dust_mass:.3e} Msun\n"
        f"  a_max_at_10au={a_10:.3e}cm  a_max_at_100au={a_100:.3e}cm\n"
        f"  wall_clock={t_wall:.1f}s"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run a DustPy dust-evolution simulation.")
    p.add_argument(
        "--json",
        metavar="JSON",
        help="JSON string or path with all parameters (overrides individual flags)",
    )
    p.add_argument("--alpha", type=float, dest="alpha_viscosity")
    p.add_argument("--disk-mass", type=float, dest="disk_mass_msun")
    p.add_argument("--stellar-mass", type=float, dest="stellar_mass_msun")
    p.add_argument("--stellar-radius", type=float, dest="stellar_radius_rsun")
    p.add_argument("--stellar-temperature", type=float, dest="stellar_temperature_K")
    p.add_argument("--d2g", type=float, dest="dust_to_gas_ratio")
    p.add_argument("--sigma-exp", type=float, dest="gas_sigma_exp")
    p.add_argument("--sigma-rc", type=float, dest="gas_sigma_rc_au")
    p.add_argument("--rho-monomer", type=float, dest="monomer_density_gcc")
    p.add_argument("--Nmbpd", type=int, dest="Nmbpd")
    p.add_argument("--r-in", type=float, dest="r_in_au")
    p.add_argument("--r-out", type=float, dest="r_out_au")
    p.add_argument("--N-r", type=int, dest="N_r")
    p.add_argument("--t-end", type=float, dest="t_end_yr")
    p.add_argument("--vfrag", type=float, dest="fragmentation_velocity_ms")
    p.add_argument("--N-snaps", type=int, dest="N_snapshots")
    p.add_argument(
        "--snapshot-times",
        dest="snapshot_times_yr",
        help="JSON array of snapshot times in years, e.g. '[1e4,1e5,1e6]'",
    )
    p.add_argument("--output-dir", type=str, dest="output_dir")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Build raw dict from individual flags (skip Nones)
    raw: dict = {k: v for k, v in vars(args).items() if v is not None and k != "json"}

    # JSON overrides everything
    if args.json:
        src = args.json.strip()
        if os.path.isfile(src):
            with open(src) as fh:
                raw = json.load(fh)
        else:
            raw = json.loads(src)

    try:
        params = DustPyParams(**raw)
    except Exception as exc:
        print(f"ERROR: parameter validation failed — {exc}", file=sys.stderr)
        sys.exit(1)

    result = run_dustpy_simulation(params)
    print(result)
    if result.startswith("ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
