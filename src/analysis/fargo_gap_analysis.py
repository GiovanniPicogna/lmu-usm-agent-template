"""Post-process a FARGO3D disc simulation snapshot.

Computes the azimuthally-averaged surface density profile, gap depth,
and planet torque from binary output files.  Saves a summary JSON and
a dark-background radial profile figure.

Inputs
------
input_dir : Path
    Directory containing the FARGO3D binary output files.

Outputs
-------
results/analysis/fargo_gap_analysis_20260529.json
plots/fargo_sigma_profile.pdf
plots/fargo_sigma_profile.png
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np

# ── Simulation constants (from variables.par) ─────────────────────────────────
SNAPSHOT_INDEX = 0
N_RADIAL = 128         # NY
N_AZIMUTHAL = 384      # NX
NGHOST = 3             # FARGO3D default ghost-cell count
SIGMA_0 = 6.37e-4      # code units; SIGMASLOPE=0 → flat initial profile
PLANET_MASS_CODE = 9.548e-4  # M★ = 1 M_Jup / 1 M_sun

# ── Plot style ─────────────────────────────────────────────────────────────────
FIGURE_FACECOLOR = "#1a1a2e"
AXES_FACECOLOR = "#0d0d1a"
TEXT_COLOR = "white"
ACCENT_COLOR = "#e94560"
GRID_COLOR = "#3a3a5c"


def load_radial_grid(domain_y_path: Path) -> np.ndarray:
    """Return 1-D array of radial cell-centre coordinates in code units (au).

    FARGO3D writes Ny + 2*NGHOST + 1 interface values.  The physical
    interfaces are indices [NGHOST : NGHOST + Ny + 1]; cell centres are
    the midpoints of consecutive interface pairs.

    Parameters
    ----------
    domain_y_path : Path
        Path to ``domain_y.dat``.

    Returns
    -------
    r_centers : np.ndarray, shape (Ny,)
        Radial cell centres in code units (au for the fargo setup).
    """
    domain_y = np.fromfile(domain_y_path, dtype="float64", sep="\n")
    r_interfaces = domain_y[NGHOST : NGHOST + N_RADIAL + 1]
    r_centers = 0.5 * (r_interfaces[:-1] + r_interfaces[1:])
    return r_centers


def load_surface_density(gasdens_path: Path) -> np.ndarray:
    """Read a 2-D surface density array from a FARGO3D binary file.

    Parameters
    ----------
    gasdens_path : Path
        Path to the binary gas-density file (e.g. ``gasdens0.dat``).

    Returns
    -------
    sigma_2d : np.ndarray, shape (Ny, Nx)
        Surface density in code units.
    """
    raw = np.fromfile(gasdens_path, dtype="float64")
    expected_size = N_RADIAL * N_AZIMUTHAL
    if raw.size != expected_size:
        raise ValueError(
            f"Expected {expected_size} values in {gasdens_path.name}; "
            f"got {raw.size}.  Check NY and NX."
        )
    return raw.reshape(N_RADIAL, N_AZIMUTHAL)


def azimuthal_average(sigma_2d: np.ndarray) -> np.ndarray:
    """Return the azimuthal mean of a 2-D array along the azimuthal axis.

    Parameters
    ----------
    sigma_2d : np.ndarray, shape (Ny, Nx)
        2-D surface density.

    Returns
    -------
    sigma_avg : np.ndarray, shape (Ny,)
        Azimuthally averaged surface density.
    """
    return sigma_2d.mean(axis=1)


def compute_gap_depth(
    sigma_avg: np.ndarray,
    sigma_0: float,
) -> tuple[float, float]:
    """Compute the gap depth as Σ_gap / Σ_0.

    Parameters
    ----------
    sigma_avg : np.ndarray, shape (Ny,)
        Azimuthally averaged surface density profile.
    sigma_0 : float
        Unperturbed surface density at r = 1 au (code units).

    Returns
    -------
    gap_depth : float
        Σ_gap / Σ_0 (< 1 means a gap is present).
    gap_index : int
        Radial index of the minimum surface density.
    """
    gap_index = int(np.argmin(sigma_avg))
    gap_depth = float(sigma_avg[gap_index]) / sigma_0
    return gap_depth, gap_index


def load_torques(tqwk_path: Path) -> np.ndarray:
    """Load the torque file and return a 2-D array.

    FARGO3D writes one row per output time step.  Column 0 is time;
    the remaining columns are torque contributions.  The exact number
    of columns depends on the FARGO3D version and setup.

    Parameters
    ----------
    tqwk_path : Path
        Path to the torque file (e.g. ``tqwk0.dat``).

    Returns
    -------
    torque_data : np.ndarray, shape (n_steps, n_cols)
        Torque data array.
    """
    torque_data = np.loadtxt(tqwk_path)
    if torque_data.ndim == 1:
        torque_data = torque_data[np.newaxis, :]
    return torque_data


def make_sigma_profile_plot(
    r_centers: np.ndarray,
    sigma_avg: np.ndarray,
    gap_index: int,
    output_stem: Path,
) -> None:
    """Create and save a dark-background radial surface density profile.

    Parameters
    ----------
    r_centers : np.ndarray
        Radial cell centres in au.
    sigma_avg : np.ndarray
        Azimuthally averaged surface density in code units.
    gap_index : int
        Index of the minimum surface density (gap location).
    output_stem : Path
        Output path without extension; ``.pdf`` and ``.png`` are appended.
    """
    r_au = (r_centers * u.au).value

    fig, ax = plt.subplots(figsize=(8, 5), facecolor=FIGURE_FACECOLOR)
    ax.set_facecolor(AXES_FACECOLOR)

    ax.plot(r_au, sigma_avg, color=ACCENT_COLOR, lw=2, label=r"$\langle\Sigma\rangle_\phi$")
    ax.axvline(
        r_au[gap_index],
        color="gold",
        lw=1.2,
        ls="--",
        label=f"Gap minimum  r = {r_au[gap_index]:.2f} au",
    )
    ax.axhline(SIGMA_0, color="white", lw=0.8, ls=":", alpha=0.6, label=r"$\Sigma_0$")

    ax.set_xlabel("Radius [au]", color=TEXT_COLOR, fontsize=12)
    ax.set_ylabel(r"$\langle\Sigma\rangle_\phi$ [code units]", color=TEXT_COLOR, fontsize=12)
    ax.set_title(
        "FARGO3D — Azimuthal mean surface density  (snapshot 0)",
        color=TEXT_COLOR,
        fontsize=13,
    )

    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)
    ax.tick_params(colors=TEXT_COLOR, labelsize=10)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.grid(color=GRID_COLOR, ls="--", lw=0.5, alpha=0.5)

    legend = ax.legend(fontsize=10, facecolor=FIGURE_FACECOLOR, edgecolor=GRID_COLOR)
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)

    fig.tight_layout()
    fig.savefig(output_stem.with_suffix(".pdf"), dpi=300)
    fig.savefig(output_stem.with_suffix(".png"), dpi=300)
    plt.close(fig)


def count_snapshots(input_dir: Path) -> int:
    """Count how many gas-density snapshots are present in *input_dir*."""
    return len(list(input_dir.glob("gasdens*.dat")))


def run_analysis(input_dir: Path, output_json: Path, output_plot_stem: Path) -> dict:
    """Execute the full post-processing pipeline and return a summary dict.

    Parameters
    ----------
    input_dir : Path
        Directory containing FARGO3D binary outputs.
    output_json : Path
        Destination for the summary JSON file.
    output_plot_stem : Path
        Stem (no extension) for the output figure files.

    Returns
    -------
    summary : dict
        All computed diagnostics.
    """
    t_start = time.perf_counter()

    # ── Load data ──────────────────────────────────────────────────────────────
    r_centers = load_radial_grid(input_dir / "domain_y.dat")
    sigma_2d = load_surface_density(input_dir / f"gasdens{SNAPSHOT_INDEX}.dat")
    sigma_avg = azimuthal_average(sigma_2d)
    torque_data = load_torques(input_dir / f"tqwk{SNAPSHOT_INDEX}.dat")

    # ── Diagnostics ────────────────────────────────────────────────────────────
    gap_depth, gap_index = compute_gap_depth(sigma_avg, SIGMA_0)
    gap_location_au = float(r_centers[gap_index])
    n_torque_cols = torque_data.shape[1]
    planet_torque_last = float(torque_data[-1, -1])

    # ── Figure ─────────────────────────────────────────────────────────────────
    output_plot_stem.parent.mkdir(parents=True, exist_ok=True)
    make_sigma_profile_plot(r_centers, sigma_avg, gap_index, output_plot_stem)

    # ── Summary ────────────────────────────────────────────────────────────────
    wall_clock = time.perf_counter() - t_start
    n_snaps = count_snapshots(input_dir)

    summary = {
        "agent": "analysis-agent",
        "task": "fargo_gap_depth_post_processing",
        "input_dir": str(input_dir),
        "n_snapshots_found": n_snaps,
        "snapshot_analysed": SNAPSHOT_INDEX,
        "Sigma_gap_over_Sigma0": round(gap_depth, 6),
        "Sigma_gap_code_units": round(float(sigma_avg[gap_index]), 8),
        "Sigma_0_code_units": SIGMA_0,
        "gap_location_au": round(gap_location_au, 4),
        "n_torque_columns": n_torque_cols,
        "planet_torque_last": planet_torque_last,
        "output_json": str(output_json),
        "output_plot": str(output_plot_stem.with_suffix(".pdf")),
        "wall_clock_s": round(wall_clock, 3),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w") as file_handle:
        json.dump(summary, file_handle, indent=2)

    return summary


def main() -> None:
    """CLI entry point for ``fargo_gap_analysis.py``."""
    repo_root = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description="Post-process a FARGO3D snapshot and compute gap diagnostics."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("/Users/giovanni/Codes/fargo3d/data/runs/fargo_skill_test"),
        help="Path to the FARGO3D binary output directory.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=repo_root / "results" / "analysis" / "fargo_gap_analysis_20260529.json",
        help="Destination JSON file for the summary.",
    )
    parser.add_argument(
        "--output-plot",
        type=Path,
        default=repo_root / "plots" / "fargo_sigma_profile",
        help="Output figure stem (no extension; .pdf and .png are appended).",
    )
    args = parser.parse_args()

    summary = run_analysis(args.input_dir, args.output_json, args.output_plot)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
