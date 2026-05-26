#!/usr/bin/env python3
"""
PLUTO post-run plotter — v1.
Mignone et al. 2007  •  https://plutocode.ph.unito.it
Based on PLUTO v4.4-patch3  •  Requires pyPLUTO (arXiv:2501.09748)

Produces publication-quality figures from PLUTO snapshots:
  - Geometry-aware axes (r, φ, z, x, y in physical units from physics_config.md)
  - Multi-variable multi-panel layout, one file per snapshot
  - Optional velocity quiver overlay
  - Colorblind-safe palettes (viridis/cividis) at 300 dpi
  - PDF (vector) + PNG (raster) dual output
  - Works with: .dbl, .flt, .dbl.h5, .flt.h5, Chombo data.nnnn.hdf5

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

Outputs (one per snapshot):
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
from typing import Any, Dict, List, Optional, Union

import numpy as np

# ── Axis-label maps per geometry ─────────────────────────────────────────────

_AXIS_LABELS = {
    "CARTESIAN":   {1: "x",   2: "y",   3: "z"},
    "POLAR":       {1: "r",   2: r"$\phi$",  3: "z"},
    "SPHERICAL":   {1: "r",   2: r"$\theta$", 3: r"$\phi$"},
    "CYLINDRICAL": {1: "r",   2: "z",   3: r"$\phi$"},
}

_COLORMAPS = {
    "rho":  "viridis",  "Density": "viridis",
    "prs":  "inferno",  "Pressure": "inferno",
    "vx1":  "RdBu_r",   "vx2": "RdBu_r",   "vx3": "RdBu_r",
    "Bx1":  "PuOr_r",   "Bx2": "PuOr_r",   "Bx3": "PuOr_r",
    "tr1":  "plasma",   "tr2": "plasma",
    "_speed": "cividis",
    "_default": "viridis",
}

_SYMLOG_VARS = {"vx1", "vx2", "vx3", "Bx1", "Bx2", "Bx3"}   # signed; use symlog
_LOG_VARS    = {"rho", "prs", "Density", "Pressure"}           # positive; use log


def _cmap_for(varname: str) -> str:
    return _COLORMAPS.get(varname, _COLORMAPS["_default"])


# ── pyPLUTO loader ───────────────────────────────────────────────────────────

def _load_snapshot(run_dir: str, snap_n: int, datatype: str = "dbl"):
    """
    Load a PLUTO snapshot.  Returns pyPLUTO Data object or raises.
    Tries new API (pp.Load) then legacy (pp.pload).
    """
    try:
        import pyPLUTO as pp
        try:
            return pp.Load(snap_n, w_dir=run_dir, datatype=datatype)
        except TypeError:
            # Legacy API signature
            return pp.pload(snap_n, w_dir=run_dir, datatype=datatype)
    except ImportError:
        raise ImportError(
            "pyPLUTO is required for plot_pluto.py.\n"
            "Install with: pip install pypluto\n"
            "Reference: arXiv:2501.09748"
        )


def _get_array(d, varname: str) -> Optional[np.ndarray]:
    """Retrieve a variable array from a pyPLUTO Data object."""
    for attr in (varname, varname.lower(), varname.upper()):
        val = getattr(d, attr, None)
        if val is not None:
            return np.asarray(val)
    return None


def _get_coords(d, geometry: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (x1_grid, x2_grid) 1-D coordinate arrays from pyPLUTO Data.
    New pyPLUTO uses d.x1, d.x2; legacy uses d.x1, d.x2 too but may differ.
    """
    x1 = getattr(d, "x1", None)
    x2 = getattr(d, "x2", None)
    if x1 is None:
        # Try alternative attribute names
        x1 = getattr(d, "X1", getattr(d, "r",  np.arange(10)))
    if x2 is None:
        x2 = getattr(d, "X2", getattr(d, "phi", np.arange(10)))
    return np.asarray(x1), np.asarray(x2)


# ── Snapshot index helpers ────────────────────────────────────────────────────

def _all_snapshot_indices(run_dir: str, datatype: str) -> list[int]:
    """Return sorted list of all snapshot indices from dbl.out or file glob."""
    # Primary: *.out descriptor
    ext_map = {"dbl": "dbl", "flt": "flt", "dbl.h5": "dbl", "flt.h5": "flt"}
    desc_ext = ext_map.get(datatype, "dbl")
    desc = Path(run_dir) / f"{desc_ext}.out"
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
            return indices

    # Fallback: file glob
    patterns = {
        "dbl":    "*.dbl",
        "flt":    "*.flt",
        "dbl.h5": "*.dbl.h5",
        "flt.h5": "*.flt.h5",
        "vtk":    "*.vtk",
    }
    pat = patterns.get(datatype, "*.dbl")
    files = sorted(Path(run_dir).glob(pat))
    indices = []
    for f in files:
        # Chombo: data.0005.hdf5
        parts = f.name.split(".")
        try:
            indices.append(int(parts[-2] if len(parts) >= 3 else parts[0]))
        except ValueError:
            pass
    return sorted(set(indices))


def _last_snapshot_index(run_dir: str, datatype: str) -> int:
    idxs = _all_snapshot_indices(run_dir, datatype)
    return idxs[-1] if idxs else -1


# ── Unit helpers ──────────────────────────────────────────────────────────────

def _unit_label(key: str, unit_length_cm: Optional[float]) -> str:
    """Return a human-readable axis unit label."""
    if unit_length_cm is None:
        return " [code units]"
    au = 1.49597870700e13
    pc = 3.08567758149e18
    rsun = 6.96e10
    if abs(unit_length_cm - au) / au < 0.01:
        return " [AU]"
    if abs(unit_length_cm - pc) / pc < 0.01:
        return " [pc]"
    if abs(unit_length_cm - rsun) / rsun < 0.01:
        return r" [$R_\odot$]"
    # Generic: choose best SI prefix
    if unit_length_cm >= 1e18:
        return f" [×{unit_length_cm:.2e} cm]"
    return " [code units]"


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
    output_dir: str = "",
    fmt: str = "pdf",
    dpi: int = 300,
    colormap: Optional[str] = None,
    figsize: Optional[list[float]] = None,
    show: bool = False,
) -> list[str]:
    """
    Plot one snapshot.  Returns list of output file paths.
    One PDF/PNG file is produced per variable.
    """
    try:
        import matplotlib
        matplotlib.use("Agg" if not show else "TkAgg")
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        from matplotlib.ticker import LogFormatter
    except ImportError:
        raise ImportError("matplotlib is required: pip install matplotlib")

    d = _load_snapshot(run_dir, snap_n, datatype)
    x1, x2 = _get_coords(d, geometry)

    ax_labels = _AXIS_LABELS.get(geometry, {1: "x1", 2: "x2", 3: "x3"})
    unit_sfx  = _unit_label("length", unit_length_cm) if physical_axes else " [code]"

    os.makedirs(output_dir or Path(run_dir) / "plots", exist_ok=True)
    out_dir = output_dir or str(Path(run_dir) / "plots")

    # Build 2-D coordinate meshes for pcolormesh
    # pyPLUTO returns 1-D cell-centre arrays; we need 2-D for plotting
    X1, X2 = np.meshgrid(x1, x2, indexing="ij")

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
        fs   = figsize or [6.0, 5.0]

        fig, ax = plt.subplots(figsize=fs, dpi=dpi)

        # Geometry-aware transpose: arr shape may be (nx1, nx2) or (nx2, nx1)
        # pyPLUTO returns (nx2, nx1) for 2-D — transpose to match (x1, x2) meshes
        if arr.ndim == 2:
            if arr.shape == X1.shape:
                plot_arr = arr
            elif arr.T.shape == X1.shape:
                plot_arr = arr.T
            else:
                plot_arr = arr  # best effort
        else:
            # 1-D slice
            ax.plot(x1, arr)
            ax.set_xlabel(ax_labels.get(1, "x1") + unit_sfx, fontsize=11)
            ax.set_ylabel(varname, fontsize=11)
            ax.set_title(f"{varname}  |  n={snap_n}", fontsize=12)
        _save_and_close = lambda: None  # noqa: E731

        if arr.ndim == 2:
            if do_symlog:
                norm = mcolors.SymLogNorm(
                    linthresh=max(np.abs(plot_arr).max() * 1e-3, 1e-30),
                    vmin=plot_arr.min(), vmax=plot_arr.max(),
                )
                pcm = ax.pcolormesh(X1, X2, plot_arr, cmap=cmap, norm=norm, shading="auto")
            elif do_log:
                pos = plot_arr.copy()
                pos[pos <= 0] = np.nan
                norm = mcolors.LogNorm(vmin=np.nanmin(pos), vmax=np.nanmax(pos))
                pcm = ax.pcolormesh(X1, X2, pos, cmap=cmap, norm=norm, shading="auto")
            else:
                pcm = ax.pcolormesh(X1, X2, plot_arr, cmap=cmap, shading="auto")

            cbar = fig.colorbar(pcm, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label(varname, fontsize=10)

            # Velocity quiver overlay
            if velocity_overlay:
                vx1_arr = _get_array(d, "vx1")
                vx2_arr = _get_array(d, "vx2")
                if vx1_arr is not None and vx2_arr is not None:
                    vx1_2d = vx1_arr.T if vx1_arr.T.shape == X1.shape else vx1_arr
                    vx2_2d = vx2_arr.T if vx2_arr.T.shape == X1.shape else vx2_arr
                    qs = quiver_subsample
                    ny, nx = X1.shape
                    iy = slice(0, ny, qs)
                    ix = slice(0, nx, qs)
                    ax.quiver(
                        X1[iy, ix], X2[iy, ix],
                        vx1_2d[iy, ix], vx2_2d[iy, ix],
                        color="white", alpha=0.65, scale_units="xy",
                        width=0.002,
                    )

            ax.set_xlabel(ax_labels.get(1, "x1") + unit_sfx, fontsize=11)
            ax.set_ylabel(ax_labels.get(2, "x2") + unit_sfx, fontsize=11)
            ax.set_title(f"{varname}  |  n={snap_n}  t={getattr(d,'t',float('nan')):.4g}",
                         fontsize=12)
            ax.set_aspect("auto")

        fig.tight_layout()
        stem    = f"{varname}_n{snap_n:05d}"
        outpath = str(Path(out_dir) / f"{stem}.{fmt}")
        fig.savefig(outpath, dpi=dpi, bbox_inches="tight")
        if fmt != "png":
            # Always save a PNG companion for quick inspection
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
        run_dir:          str
        snap:             Union[int, List[int], str] = "last"
        variables:        List[str]                  = Field(default_factory=lambda: ["rho"])
        datatype:         str                        = "dbl"
        physics_config:   str                        = "physics_config.md"

        # Geometry & units (overridden by physics_config.md if present)
        geometry:         str                        = "CARTESIAN"
        unit_length_cm:   Optional[float]            = None
        unit_density_cgs: Optional[float]            = None
        unit_velocity_cgs: Optional[float]           = None
        physical_axes:    bool                       = True

        # Visual
        velocity_overlay: bool                       = False
        quiver_subsample: int                        = Field(default=8, ge=1, le=128)
        log_scale:        Optional[Union[bool, List[bool]]] = None
        colormap:         Optional[str]              = None
        figsize:          Optional[List[float]]      = None
        show:             bool                       = False

        # Output
        output_dir:       str                        = ""
        format:           str                        = "pdf"
        dpi:              int                        = Field(default=300, ge=72, le=1200)

        @model_validator(mode="after")
        def load_physics_config(self) -> "PLUTOPlotParams":
            if not os.path.isdir(self.run_dir):
                raise ValueError(f"run_dir does not exist: {self.run_dir!r}")

            # Load physics_config.md if present
            cfg_path = Path(self.run_dir) / self.physics_config
            if not cfg_path.is_file():
                # Try resolving as an absolute path
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
                    pass  # silently proceed without physics_config
            return self


# ── Main entry point ──────────────────────────────────────────────────────────

def _resolve_snaps(snap_arg: Union[int, list, str], run_dir: str, datatype: str) -> list[int]:
    if isinstance(snap_arg, int):
        return [snap_arg]
    if isinstance(snap_arg, list):
        return [int(s) for s in snap_arg]
    if snap_arg == "last":
        idx = _last_snapshot_index(run_dir, datatype)
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
    p.add_argument("--json",         metavar="JSON",
                   help="JSON string or path to JSON file with all parameters")
    p.add_argument("--run-dir",      dest="run_dir")
    p.add_argument("--snap",         nargs="+",
                   help="Snapshot index(es), 'last', or 'all'")
    p.add_argument("--variables",    nargs="+",     dest="variables",
                   help="Variable names: rho vx1 vx2 Bx1 prs …")
    p.add_argument("--datatype",     dest="datatype", default="dbl",
                   help="dbl, flt, dbl.h5, flt.h5, vtk (default: dbl)")
    p.add_argument("--physics-config", dest="physics_config",
                   default="physics_config.md")
    p.add_argument("--geometry",     dest="geometry")
    p.add_argument("--no-physical-axes", dest="physical_axes",
                   action="store_false", default=True)
    p.add_argument("--velocity-overlay", dest="velocity_overlay",
                   action="store_true")
    p.add_argument("--quiver-subsample", dest="quiver_subsample", type=int)
    p.add_argument("--log",          dest="log_scale", action="store_true",
                   default=None)
    p.add_argument("--colormap",     dest="colormap")
    p.add_argument("--output-dir",   dest="output_dir")
    p.add_argument("--format",       dest="format", default="pdf",
                   choices=["pdf", "png", "svg"])
    p.add_argument("--dpi",          type=int, dest="dpi", default=300)
    p.add_argument("--show",         action="store_true")
    return p


def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    raw: dict[str, Any] = {
        k: v for k, v in vars(args).items()
        if v is not None and k != "json"
    }

    # Normalise --snap
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
        if os.path.isfile(src):
            with open(src) as fh:
                raw = json.load(fh)
        else:
            raw = json.loads(src)

    if HAS_PYDANTIC:
        try:
            params = PLUTOPlotParams(**raw)
        except Exception as exc:
            print(f"ERROR: parameter validation failed — {exc}", file=sys.stderr)
            sys.exit(1)
        result = run_plot(params)
    else:
        # Pydantic not available — run without validation
        snap_arg = raw.get("snap", "last")
        snaps    = _resolve_snaps(snap_arg, raw["run_dir"], raw.get("datatype", "dbl"))
        out_dir  = raw.get("output_dir", str(Path(raw["run_dir"]) / "plots"))
        paths: list[str] = []
        for n in snaps:
            paths.extend(plot_snapshot(
                run_dir=raw["run_dir"], snap_n=n,
                variables=raw.get("variables", ["rho"]),
                geometry=raw.get("geometry", "CARTESIAN"),
                datatype=raw.get("datatype", "dbl"),
                velocity_overlay=raw.get("velocity_overlay", False),
                output_dir=out_dir,
                fmt=raw.get("format", "pdf"),
                dpi=raw.get("dpi", 300),
            ))
        result = f"SUCCESS: {len(paths)} plot(s) → {out_dir}"

    print(result)
    sys.exit(1 if result.startswith("ERROR") else 0)


if __name__ == "__main__":
    main()
