#!/usr/bin/env python3
"""
PLUTO post-run plotter.
Mignone et al. 2007  •  https://plutocode.ph.unito.it
Based on PLUTO v4.4  •  Requires pyPLUTO (bundled in PLUTO/Tools/pyPLUTO/)

Produces publication-quality figures from PLUTO snapshots:
  - Geometry-aware axes (r, φ, z, x, y in physical units from physics_config.md)
  - Multi-variable panels, one file per variable per snapshot
  - Optional velocity quiver overlay
  - Polar/Spherical r-phi projection to Cartesian for disc problems
  - Colorblind-safe palettes (viridis/cividis) at 300 dpi
  - PDF (vector) + PNG (raster) dual output
  - Works with: .dbl, .flt, .dbl.h5, .flt.h5, vtk, Chombo data.nnnn.hdf5

Usage:
    python plot_pluto.py --run-dir runs/disk --snap last
    python plot_pluto.py --run-dir runs/disk --snap 0 5 10 --variables rho prs
    python plot_pluto.py --run-dir runs/disk --snap all --variables rho Bx1 Bx2
    python plot_pluto.py --json '{
        "run_dir": "runs/disk",
        "snap": "last",
        "variables": ["rho", "vx1"],
        "velocity_overlay": true,
        "format": "pdf"}'

Outputs (one per variable per snapshot):
    <output_dir>/<varname>_n<NNNN>.<format>

physics_config.md (written by compile_pluto.py) is read for:
    GEOMETRY, UNIT_LENGTH_CGS, UNIT_DENSITY_CGS, UNIT_VELOCITY_CGS
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any, List, Optional, Union

import numpy as np

# ── pyPLUTO: bundled v4.4 API ────────────────────────────────────────────────
# Use:  import pyPLUTO.pload as ppl; D = ppl.pload(n, w_dir=..., datatype=...)
# NOT:  import pyPLUTO as pp; pp.pload(...)  — that calls the MODULE not the class
# nlast_info returns {'nlast': N, 'time': t, 'dt': dt, 'Nstep': s}


def _pypluto_load(run_dir: str, snap_n: int, datatype: str = "dbl"):
    """
    Load a PLUTO snapshot using pyPLUTO v4.4 API.
    Returns a pload object with attributes: rho, vx1, vx2, x1, x2, x3, Dt, SimTime …
    Raises ImportError if pyPLUTO is not installed.
    """
    try:
        import pyPLUTO.pload as ppl
    except ImportError:
        raise ImportError(
            "pyPLUTO is required for plot_pluto.py.\n"
            "Install the bundled version: pip install -e $PLUTO_DIR/Tools/pyPLUTO\n"
            "Or the PyPI version: pip install pypluto"
        )
    # Map 'dbl.h5' / 'flt.h5' to the correct datatype token for pload
    dtype_map = {
        "dbl": "dbl",
        "flt": "flt",
        "vtk": "vtk",
        "hdf5": "hdf5",
        "dbl.h5": "dbl",
        "flt.h5": "flt",
    }
    dt = dtype_map.get(datatype, datatype)
    return ppl.pload(snap_n, w_dir=run_dir, datatype=dt)


def _nlast_index(run_dir: str, datatype: str = "dbl") -> int:
    """Return the last snapshot index using pyPLUTO.nlast_info, then file-scan fallback."""
    # Primary: pyPLUTO.nlast_info (reads dbl.out / flt.out)
    try:
        import pyPLUTO as pp

        dt = {"dbl.h5": "dbl", "flt.h5": "flt"}.get(datatype, datatype)
        info = pp.nlast_info(w_dir=run_dir, datatype=dt if dt != "dbl" else None)
        return int(info["nlast"])
    except Exception:
        pass

    # Fallback: parse dbl.out / flt.out directly
    ext = "flt" if datatype.startswith("flt") else "dbl"
    desc = Path(run_dir) / f"{ext}.out"
    if desc.is_file():
        lines = [line for line in desc.read_text().splitlines() if line.strip()]
        if lines:
            try:
                return int(lines[-1].split()[0])
            except Exception:
                pass

    # Fallback: glob for data.NNNN.dbl etc.
    for pat in ("*.dbl.h5", "*.flt.h5", "*.dbl", "*.flt", "*.vtk", "data.*.hdf5"):
        files = sorted(Path(run_dir).glob(pat))
        if files:
            try:
                return int(files[-1].name.split(".")[1 if "data." in files[-1].name else 0])
            except Exception:
                pass
    return -1


# ── Axis-label maps per geometry ─────────────────────────────────────────────

_AXIS_LABELS = {
    "CARTESIAN": {1: "x", 2: "y", 3: "z"},
    "POLAR": {1: "r", 2: r"$\phi$ [rad]", 3: "z"},
    "SPHERICAL": {1: "r", 2: r"$\theta$ [rad]", 3: r"$\phi$ [rad]"},
    "CYLINDRICAL": {1: "r", 2: "z", 3: r"$\phi$ [rad]"},
}

_COLORMAPS = {
    "rho": "viridis",
    "Density": "viridis",
    "prs": "inferno",
    "Pressure": "inferno",
    "vx1": "RdBu_r",
    "vx2": "RdBu_r",
    "vx3": "RdBu_r",
    "Bx1": "PuOr_r",
    "Bx2": "PuOr_r",
    "Bx3": "PuOr_r",
    "tr1": "plasma",
    "tr2": "plasma",
    "_speed": "cividis",
    "_default": "viridis",
}

_SYMLOG_VARS = {"vx1", "vx2", "vx3", "Bx1", "Bx2", "Bx3"}
_LOG_VARS = {"rho", "prs", "Density", "Pressure"}


def _cmap_for(varname: str) -> str:
    return _COLORMAPS.get(varname, _COLORMAPS["_default"])


# ── Coordinate helpers ────────────────────────────────────────────────────────


def _get_array(d, varname: str) -> Optional[np.ndarray]:
    """Retrieve a variable array from a pyPLUTO pload object."""
    for attr in (varname, varname.lower(), varname.upper()):
        val = getattr(d, attr, None)
        if val is not None:
            arr = np.asarray(val)
            if arr.ndim > 0:  # reject empty
                return arr
    return None


def _get_coords(d) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (x1, x2, x3) 1-D coordinate arrays from a pload object."""
    x1 = np.asarray(getattr(d, "x1", np.arange(10)))
    x2 = np.asarray(getattr(d, "x2", np.arange(10)))
    x3 = np.asarray(getattr(d, "x3", np.array([0.0])))
    return x1, x2, x3


def _polar_to_cartesian(
    r: np.ndarray, phi: np.ndarray, arr: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Project a 2-D r-phi array onto a Cartesian (x, y) grid for pcolormesh.
    Returns (X_cart, Y_cart, arr_2d) on a regular Cartesian mesh.
    """
    R, PHI = np.meshgrid(r, phi, indexing="ij")  # shape (nr, nphi)
    X = R * np.cos(PHI)
    Y = R * np.sin(PHI)
    # arr from pload is shape (nx2, nx1) = (nphi, nr), so transpose → (nr, nphi)
    if arr.shape == (len(phi), len(r)):
        arr = arr.T
    return X, Y, arr


def _unit_label(unit_length_cm: Optional[float]) -> str:
    if unit_length_cm is None:
        return " [code]"
    au = 1.49597870700e13
    pc = 3.08567758149e18
    rsun = 6.96e10
    if abs(unit_length_cm - au) / au < 0.05:
        return " [AU]"
    if abs(unit_length_cm - pc) / pc < 0.05:
        return " [pc]"
    if abs(unit_length_cm - rsun) / rsun < 0.05:
        return r" [$R_\odot$]"
    return f" [×{unit_length_cm:.2e} cm]"


# ── Snapshot index helpers ────────────────────────────────────────────────────


def _all_snapshot_indices(run_dir: str, datatype: str) -> list[int]:
    ext = "flt" if datatype.startswith("flt") else ("vtk" if datatype == "vtk" else "dbl")
    desc = Path(run_dir) / f"{ext}.out"
    if desc.is_file():
        indices = []
        for line in desc.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    indices.append(int(line.split()[0]))
                except (IndexError, ValueError):
                    pass
        if indices:
            return sorted(set(indices))

    # Fallback: glob
    for pat in ("*.dbl.h5", "*.flt.h5", "*.dbl", "*.flt", "*.vtk"):
        files = sorted(Path(run_dir).glob(pat))
        if files:
            out = []
            for f in files:
                stem = f.name.split(".")[0]
                try:
                    out.append(int(stem))
                except ValueError:
                    pass
            if out:
                return sorted(set(out))

    # Chombo data.NNNN.hdf5
    chombo = sorted(Path(run_dir).glob("data.*.hdf5"))
    if chombo:
        out = []
        for f in chombo:
            try:
                out.append(int(f.name.split(".")[1]))
            except Exception:
                pass
        return sorted(set(out))

    return []


# ── Core plot function ────────────────────────────────────────────────────────


def plot_snapshot(
    *,
    run_dir: str,
    snap_n: int,
    variables: list[str],
    geometry: str = "CARTESIAN",
    unit_length_cm: Optional[float] = None,
    unit_density_cgs: Optional[float] = None,
    unit_velocity_cgs: Optional[float] = None,
    physical_axes: bool = True,
    datatype: str = "dbl",
    velocity_overlay: bool = False,
    quiver_subsample: int = 8,
    log_scale: Optional[Union[bool, list[bool]]] = None,
    polar_projection: bool = False,
    output_dir: str = "",
    fmt: str = "pdf",
    dpi: int = 300,
    colormap: Optional[str] = None,
    figsize: Optional[list[float]] = None,
    show: bool = False,
) -> list[str]:
    """
    Plot one PLUTO snapshot.  Returns list of output file paths.
    One PDF/PNG file per variable.

    polar_projection=True converts r-phi data to a Cartesian (x, y) display
    for POLAR and SPHERICAL geometries (disc midplane view).
    Automatically enabled for POLAR/SPHERICAL when geometry is detected.
    """
    try:
        import matplotlib

        matplotlib.use("Agg" if not show else "TkAgg")
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
    except ImportError:
        raise ImportError("matplotlib is required: pip install matplotlib")

    d = _pypluto_load(run_dir, snap_n, datatype)
    x1, x2, x3 = _get_coords(d)

    # Auto-enable polar projection for disc geometries
    do_polar = polar_projection or geometry in ("POLAR",)

    ax_labels = _AXIS_LABELS.get(geometry, {1: "x1", 2: "x2"})
    unit_sfx = _unit_label(unit_length_cm) if physical_axes else " [code]"

    out_dir = output_dir or str(Path(run_dir) / "plots")
    os.makedirs(out_dir, exist_ok=True)

    sim_time = getattr(d, "SimTime", getattr(d, "Dt", float("nan")))

    output_paths: list[str] = []

    for i, varname in enumerate(variables):
        arr = _get_array(d, varname)
        if arr is None:
            warnings.warn(f"Variable '{varname}' not found in snapshot {snap_n}; skipping.")
            continue

        arr = np.asarray(arr, dtype=float)

        # Determine log/symlog scaling
        if isinstance(log_scale, list):
            do_log = log_scale[i] if i < len(log_scale) else (varname in _LOG_VARS)
        elif log_scale is not None:
            do_log = bool(log_scale)
        else:
            do_log = varname in _LOG_VARS
        do_symlog = (varname in _SYMLOG_VARS) and not do_log

        cmap = colormap or _cmap_for(varname)
        fs = figsize or [6.0, 5.0]

        fig, ax = plt.subplots(figsize=fs, dpi=dpi)

        if arr.ndim == 1:
            ax.plot(x1, arr)
            ax.set_xlabel(ax_labels.get(1, "x1") + unit_sfx, fontsize=11)
            ax.set_ylabel(varname, fontsize=11)
            ax.set_title(f"{varname}  |  n={snap_n}  t={sim_time:.4g}", fontsize=12)

        elif arr.ndim == 2:
            # pload returns arrays as (nx2, nx1), i.e. (nphi/ntheta, nr)
            # Transpose so arr.shape == (nx1, nx2) = (nr, nphi) for pcolormesh
            if arr.shape == (len(x2), len(x1)):
                arr2d = arr.T  # → (nx1, nx2)
            elif arr.shape == (len(x1), len(x2)):
                arr2d = arr
            else:
                arr2d = arr  # best effort

            if do_polar:
                # Project r-phi onto Cartesian for disc visualization
                X, Y, arr2d = _polar_to_cartesian(x1, x2, arr2d)
                xlabel = f"x{unit_sfx}"
                ylabel = f"y{unit_sfx}"
            else:
                X, Y = np.meshgrid(x1, x2, indexing="ij")
                xlabel = ax_labels.get(1, "x1") + unit_sfx
                ylabel = ax_labels.get(2, "x2") + unit_sfx

            if do_symlog:
                linthresh = max(np.abs(arr2d).max() * 1e-3, 1e-30)
                norm = mcolors.SymLogNorm(linthresh=linthresh, vmin=arr2d.min(), vmax=arr2d.max())
                pcm = ax.pcolormesh(X, Y, arr2d, cmap=cmap, norm=norm, shading="auto")
            elif do_log:
                pos = arr2d.copy()
                pos[pos <= 0] = np.nan
                norm = mcolors.LogNorm(vmin=np.nanmin(pos), vmax=np.nanmax(pos))
                pcm = ax.pcolormesh(X, Y, pos, cmap=cmap, norm=norm, shading="auto")
            else:
                pcm = ax.pcolormesh(X, Y, arr2d, cmap=cmap, shading="auto")

            fig.colorbar(pcm, ax=ax, fraction=0.046, pad=0.04).set_label(varname, fontsize=10)

            # Velocity quiver overlay
            if velocity_overlay:
                vx1_arr = _get_array(d, "vx1")
                vx2_arr = _get_array(d, "vx2")
                if vx1_arr is not None and vx2_arr is not None:
                    # Transpose vx arrays the same way as the data
                    def _prep(v):
                        v = np.asarray(v, dtype=float)
                        return v.T if v.shape == (len(x2), len(x1)) else v

                    if do_polar:
                        # In polar, vx1=vr, vx2=vphi → project to Cartesian components
                        vr = _prep(vx1_arr)
                        vphi = _prep(vx2_arr)
                        # Use same R, PHI grids
                        R_g, PHI_g = np.meshgrid(x1, x2, indexing="ij")
                        vx_cart = vr * np.cos(PHI_g) - vphi * np.sin(PHI_g)
                        vy_cart = vr * np.sin(PHI_g) + vphi * np.cos(PHI_g)
                        vx_plot, vy_plot = vx_cart, vy_cart
                    else:
                        vx_plot = _prep(vx1_arr)
                        vy_plot = _prep(vx2_arr)

                    ny, nx = X.shape
                    qs = quiver_subsample
                    iy, ix = slice(0, ny, qs), slice(0, nx, qs)
                    ax.quiver(
                        X[iy, ix],
                        Y[iy, ix],
                        vx_plot[iy, ix],
                        vy_plot[iy, ix],
                        color="white",
                        alpha=0.65,
                        scale_units="xy",
                        width=0.002,
                    )

            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_title(f"{varname}  |  n={snap_n}  t={sim_time:.4g}", fontsize=12)
            ax.set_aspect("equal" if do_polar else "auto")

        fig.tight_layout()
        stem = f"{varname}_n{snap_n:05d}"
        outpath = str(Path(out_dir) / f"{stem}.{fmt}")
        fig.savefig(outpath, dpi=dpi, bbox_inches="tight")
        if fmt != "png":
            fig.savefig(str(Path(out_dir) / f"{stem}.png"), dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)
        output_paths.append(outpath)

    return output_paths


# ── Pydantic model ────────────────────────────────────────────────────────────

try:
    from pydantic import BaseModel, Field, model_validator

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

if HAS_PYDANTIC:

    class PLUTOPlotParams(BaseModel):
        run_dir: str
        snap: Union[int, List[int], str] = "last"
        variables: List[str] = Field(default_factory=lambda: ["rho"])
        datatype: str = "dbl"
        physics_config: str = "physics_config.md"

        # Geometry & units (overridden by physics_config.md if present)
        geometry: str = "CARTESIAN"
        unit_length_cm: Optional[float] = None
        unit_density_cgs: Optional[float] = None
        unit_velocity_cgs: Optional[float] = None
        physical_axes: bool = True

        # Visual
        velocity_overlay: bool = False
        quiver_subsample: int = Field(default=8, ge=1, le=128)
        log_scale: Optional[Union[bool, List[bool]]] = None
        colormap: Optional[str] = None
        figsize: Optional[List[float]] = None
        polar_projection: bool = False
        show: bool = False

        # Output
        output_dir: str = ""
        format: str = "pdf"
        dpi: int = Field(default=300, ge=72, le=1200)

        @model_validator(mode="after")
        def load_physics_config(self) -> "PLUTOPlotParams":
            if not os.path.isdir(self.run_dir):
                raise ValueError(f"run_dir does not exist: {self.run_dir!r}")

            # Load physics_config.md if present
            cfg_path = Path(self.run_dir) / self.physics_config
            if not cfg_path.is_file():
                cfg_path = Path(self.physics_config)

            if cfg_path.is_file():
                try:
                    sys.path.insert(0, str(Path(__file__).parent))
                    from physics_config_writer import read_physics_config

                    cfg = read_physics_config(self.run_dir)
                    if "GEOMETRY" in cfg and self.geometry == "CARTESIAN":
                        self.geometry = cfg["GEOMETRY"]
                    if "UNIT_LENGTH_CGS" in cfg and self.unit_length_cm is None:
                        self.unit_length_cm = float(cfg["UNIT_LENGTH_CGS"])
                    if "UNIT_DENSITY_CGS" in cfg and self.unit_density_cgs is None:
                        self.unit_density_cgs = float(cfg["UNIT_DENSITY_CGS"])
                    if "UNIT_VELOCITY_CGS" in cfg and self.unit_velocity_cgs is None:
                        self.unit_velocity_cgs = float(cfg["UNIT_VELOCITY_CGS"])
                except Exception:
                    pass

            # Auto-enable polar projection for disc geometry
            if self.geometry == "POLAR" and not self.polar_projection:
                self.polar_projection = True

            return self


# ── Main entry point ──────────────────────────────────────────────────────────


def _resolve_snaps(snap_arg: Union[int, list, str], run_dir: str, datatype: str) -> list[int]:
    if isinstance(snap_arg, int):
        return [snap_arg]
    if isinstance(snap_arg, list):
        return [int(s) for s in snap_arg]
    if snap_arg == "last":
        idx = _nlast_index(run_dir, datatype)
        return [idx] if idx >= 0 else []
    if snap_arg == "all":
        return _all_snapshot_indices(run_dir, datatype)
    try:
        return [int(snap_arg)]
    except ValueError:
        return []


def run_plot(params: "PLUTOPlotParams") -> str:
    snaps = _resolve_snaps(params.snap, params.run_dir, params.datatype)
    if not snaps:
        return f"ERROR: no snapshots found in {params.run_dir} for datatype={params.datatype}"

    out_dir = params.output_dir or str(Path(params.run_dir) / "plots")
    all_paths: list[str] = []
    errors: list[str] = []

    for n in snaps:
        try:
            paths = plot_snapshot(
                run_dir=params.run_dir,
                snap_n=n,
                variables=params.variables,
                geometry=params.geometry,
                unit_length_cm=params.unit_length_cm,
                unit_density_cgs=params.unit_density_cgs,
                unit_velocity_cgs=params.unit_velocity_cgs,
                physical_axes=params.physical_axes,
                datatype=params.datatype,
                velocity_overlay=params.velocity_overlay,
                quiver_subsample=params.quiver_subsample,
                log_scale=params.log_scale,
                polar_projection=params.polar_projection,
                output_dir=out_dir,
                fmt=params.format,
                dpi=params.dpi,
                colormap=params.colormap,
                figsize=params.figsize,
                show=params.show,
            )
            all_paths.extend(paths)
        except Exception as exc:
            errors.append(f"snapshot {n}: {exc}")

    msg = (
        f"SUCCESS: {len(all_paths)} plot(s) written to {out_dir}\n"
        f"  snapshots={snaps}\n"
        f"  variables={params.variables}\n"
        f"  format={params.format}  dpi={params.dpi}"
    )
    if errors:
        msg += "\n  ERRORS:\n" + "\n".join(f"    {e}" for e in errors)
    return msg


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Plot PLUTO snapshots (publication-quality).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--json", metavar="JSON")
    p.add_argument("--run-dir", dest="run_dir")
    p.add_argument("--snap", nargs="+")
    p.add_argument("--variables", nargs="+", dest="variables")
    p.add_argument(
        "--datatype",
        dest="datatype",
        default="dbl",
        help="dbl, flt, dbl.h5, flt.h5, vtk (default: dbl)",
    )
    p.add_argument("--physics-config", dest="physics_config", default="physics_config.md")
    p.add_argument("--geometry", dest="geometry")
    p.add_argument("--no-physical-axes", dest="physical_axes", action="store_false", default=True)
    p.add_argument("--velocity-overlay", dest="velocity_overlay", action="store_true")
    p.add_argument("--polar-projection", dest="polar_projection", action="store_true")
    p.add_argument("--quiver-subsample", dest="quiver_subsample", type=int)
    p.add_argument("--log", dest="log_scale", action="store_true", default=None)
    p.add_argument("--colormap", dest="colormap")
    p.add_argument("--output-dir", dest="output_dir")
    p.add_argument("--format", dest="format", default="pdf", choices=["pdf", "png", "svg"])
    p.add_argument("--dpi", type=int, dest="dpi", default=300)
    p.add_argument("--show", action="store_true")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    raw: dict[str, Any] = {k: v for k, v in vars(args).items() if v is not None and k != "json"}

    # Normalise --snap list
    if "snap" in raw and isinstance(raw["snap"], list):
        if len(raw["snap"]) == 1 and raw["snap"][0] in ("last", "all"):
            raw["snap"] = raw["snap"][0]
        else:
            try:
                raw["snap"] = [int(s) for s in raw["snap"]]
            except ValueError:
                raw["snap"] = raw["snap"][0]

    if args.json:
        src = args.json.strip()
        raw = json.load(open(src)) if os.path.isfile(src) else json.loads(src)

    if HAS_PYDANTIC:
        try:
            params = PLUTOPlotParams(**raw)
        except Exception as exc:
            print(f"ERROR: parameter validation failed — {exc}", file=sys.stderr)
            sys.exit(1)
        result = run_plot(params)
    else:
        snap_arg = raw.get("snap", "last")
        snaps = _resolve_snaps(snap_arg, raw["run_dir"], raw.get("datatype", "dbl"))
        out_dir = raw.get("output_dir", str(Path(raw["run_dir"]) / "plots"))
        paths: list[str] = []
        for n in snaps:
            paths.extend(
                plot_snapshot(
                    run_dir=raw["run_dir"],
                    snap_n=n,
                    variables=raw.get("variables", ["rho"]),
                    geometry=raw.get("geometry", "CARTESIAN"),
                    datatype=raw.get("datatype", "dbl"),
                    velocity_overlay=raw.get("velocity_overlay", False),
                    polar_projection=raw.get("polar_projection", False),
                    output_dir=out_dir,
                    fmt=raw.get("format", "pdf"),
                    dpi=raw.get("dpi", 300),
                )
            )
        result = f"SUCCESS: {len(paths)} plot(s) → {out_dir}"

    print(result)
    sys.exit(1 if result.startswith("ERROR") else 0)


if __name__ == "__main__":
    main()
