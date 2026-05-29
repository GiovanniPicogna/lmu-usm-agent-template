"""Post-process a FARGO3D disc simulation.

Reads all snapshots from a FARGO3D binary output directory, computes
azimuthally-averaged surface density profiles, gap depth evolution,
and planet torque history.  Saves a two-panel diagnostic figure (PDF/PNG)
and a summary JSON file.

Usage
-----
python src/analysis/fargo_gap_analysis.py \
    --input-dir data/runs/fargo_nu_1Mjup \
    --output-json results/analysis/fargo_gap_analysis.json \
    --output-plot plots/disk/fargo_nu_1Mjup_gap
"""

from __future__ import annotations

import argparse
import datetime
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── Grid constants (from variables.par) ───────────────────────────────────────
N_RADIAL = 128     # NY
N_AZIMUTHAL = 384  # NX
NGHOST = 3         # FARGO3D NGHY (ghost cells per side in radial direction)

# ── Physical parameters ────────────────────────────────────────────────────────
Q_PLANET = 0.001   # M_p / M_star  (jupiter.cfg)
H_DISK = 0.05      # AspectRatio
ALPHA_DISK = 1e-3  # viscosity alpha


# ── Readers ───────────────────────────────────────────────────────────────────

def load_radial_grid(run_dir: Path) -> np.ndarray:
    """Return 1-D array of radial cell-centre coordinates [code units = AU].

    FARGO3D writes Ny + 2*NGHOST + 1 interface values including ghost zones.
    Physical interfaces are indices [NGHOST : NGHOST+Ny+1].
    """
    edges_all = np.loadtxt(run_dir / "domain_y.dat")
    edges = edges_all[NGHOST : NGHOST + N_RADIAL + 1]  # 129 real edges
    return 0.5 * (edges[:-1] + edges[1:])              # 128 cell centres


def load_sigma_profile(run_dir: Path, snap: int) -> np.ndarray:
    """Return azimuthally averaged Σ(r) [code units] for snapshot `snap`."""
    fpath = run_dir / f"gasdens{snap}.dat"
    field = np.fromfile(fpath, dtype=np.float64).reshape(N_RADIAL, N_AZIMUTHAL)
    return field.mean(axis=1)


def load_tqwk(run_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (time [code units], total_torque [code units]) from tqwk0.dat.

    Column layout (FARGO3D fargo_nu + STOCKHOLM):
    0: output_number  1-5: partial torques  6: total_torque
    7: work  8: work_res  9: cumulative_time
    """
    data = np.loadtxt(run_dir / "tqwk0.dat")
    mask = data[:, 9] > 0
    data = data[mask]
    _, idx = np.unique(data[:, 9], return_index=True)
    data = data[idx]
    return data[:, 9], data[:, 6]   # time, total_torque


# ── Kanagawa+ 2015 prediction ─────────────────────────────────────────────────

def kanagawa_gap_depth(q: float, h: float, alpha: float) -> float:
    """Steady-state Σ_gap / Σ_0 from Kanagawa et al. 2015, ApJ 806 L15.

    K = (M_p/M_*)^2 * (h/r)^{-5} * alpha^{-1}
    delta = 1 / (1 + 0.04 K)
    """
    k = (q ** 2) * (h ** -5) / alpha
    return 1.0 / (1.0 + 0.04 * k)


# ── Analysis ──────────────────────────────────────────────────────────────────

def run_analysis(input_dir: Path, output_json: Path, output_plot_stem: Path) -> dict:
    """Execute the full post-processing pipeline and return a summary dict."""
    t_start = time.perf_counter()

    run_dir = input_dir.resolve()
    r = load_radial_grid(run_dir)

    # Locate all non-2D snapshots
    snaps = sorted(
        int(p.stem.replace("gasdens", ""))
        for p in run_dir.glob("gasdens*.dat")
        if "2d" not in p.name
    )
    n_snaps = len(snaps)

    # DT = pi/10, Ninterm = 10  →  one output per pi code time = 0.5 orbital period
    dt_per_output = np.pi  # DT * Ninterm
    times_orbits = np.array([s * dt_per_output / (2.0 * np.pi) for s in snaps])

    # Initial reference profile
    sig0 = load_sigma_profile(run_dir, snaps[0])

    # Gap region for gap depth (planet at r=1 AU)
    gap_mask = (r >= 0.6) & (r <= 1.5)

    # Gap depth evolution
    gap_depths = []
    r_gaps = []
    for s in snaps:
        sig = load_sigma_profile(run_dir, s)
        idx_min = int(np.argmin(sig[gap_mask]))
        gap_depths.append(sig[gap_mask][idx_min] / sig0[gap_mask][idx_min])
        r_gaps.append(float(r[gap_mask][idx_min]))

    gap_depths = np.array(gap_depths)
    r_gaps = np.array(r_gaps)

    # Load all profiles (for the figure)
    all_profiles = {s: load_sigma_profile(run_dir, s) for s in snaps}

    # Torque
    t_torque, torque = load_tqwk(run_dir)
    t_torque_orbits = t_torque / (2.0 * np.pi)

    # Kanagawa prediction
    delta_kanagawa = kanagawa_gap_depth(Q_PLANET, H_DISK, ALPHA_DISK)

    # ── Figure ─────────────────────────────────────────────────────────────────
    output_plot_stem.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.subplots_adjust(wspace=0.32)
    cmap = plt.get_cmap("tab10")

    # Panel 1: Σ(r)/Σ_0(r) profiles at t=0, midpoint, end
    ax = axes[0]
    snap_subset = [snaps[0], snaps[n_snaps // 2], snaps[-1]]
    t_subset = [times_orbits[0], times_orbits[n_snaps // 2], times_orbits[-1]]
    for i, (s, t_orb) in enumerate(zip(snap_subset, t_subset)):
        ax.plot(r, all_profiles[s] / sig0, color=cmap(i),
                label=rf"$t = {t_orb:.1f}$ orbits", lw=1.5)
    ax.axhline(delta_kanagawa, color="red", ls="--", lw=1.2,
               label=rf"Kanagawa+15 steady state ($\delta={delta_kanagawa:.4f}$)")
    ax.axvline(1.0, color="gray", ls=":", lw=1.0, label="Planet ($r=1$ AU)")
    ax.set_xlabel(r"$r$ [AU]", fontsize=11)
    ax.set_ylabel(r"$\Sigma(r)\,/\,\Sigma_0(r)$", fontsize=11)
    ax.set_title("Surface density profile", fontsize=11)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_xlim(0.4, 2.5)
    ax.set_ylim(0, 2.0)
    ax.tick_params(labelsize=9)

    # Panel 2: gap depth vs time
    ax2 = axes[1]
    ax2.plot(times_orbits, gap_depths, "o-", color=cmap(0), ms=4, lw=1.5,
             label=r"$\Sigma_{\rm gap}/\Sigma_0$ (simulation)")
    ax2.axhline(delta_kanagawa, color="red", ls="--", lw=1.2,
                label="Kanagawa+15 steady state")
    ax2.set_xlabel(r"Time [orbits at $r=1$ AU]", fontsize=11)
    ax2.set_ylabel(r"$\Sigma_{\rm gap}/\Sigma_0$", fontsize=11)
    ax2.set_title("Gap depth evolution", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.set_ylim(0, 1.1)
    ax2.tick_params(labelsize=9)
    ax2.annotate(
        rf"$\delta={gap_depths[-1]:.3f}$ at $t={times_orbits[-1]:.0f}$ orbits",
        xy=(times_orbits[-1], gap_depths[-1]),
        xytext=(times_orbits[-1] * 0.45, gap_depths[-1] + 0.12),
        arrowprops=dict(arrowstyle="->", color="k", lw=0.8),
        fontsize=8,
    )

    fig.suptitle(
        r"FARGO3D: 1 $M_{\rm Jup}$, $h/r=0.05$, $\alpha=10^{-3}$",
        fontsize=12, y=1.01,
    )
    pdf_path = output_plot_stem.with_suffix(".pdf")
    png_path = output_plot_stem.with_suffix(".png")
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {pdf_path}, {png_path}")

    # ── Summary dict ───────────────────────────────────────────────────────────
    wall_clock = time.perf_counter() - t_start
    summary = {
        "agent": "analysis-agent",
        "task": "fargo_gap_depth_multi_snapshot",
        "date": datetime.date.today().isoformat(),
        "input_dir": str(run_dir),
        "code": "FARGO3D 2.0-41-gf3593281",
        "setup": "fargo_nu",
        "n_snapshots": n_snaps,
        "q_planet": Q_PLANET,
        "h_disk": H_DISK,
        "alpha": ALPHA_DISK,
        "gap_depth_last": round(float(gap_depths[-1]), 6),
        "r_gap_last_au": round(float(r_gaps[-1]), 4),
        "t_last_orbits": round(float(times_orbits[-1]), 4),
        "gap_depth_kanagawa_steady": round(float(delta_kanagawa), 6),
        "planet_torque_last": round(float(torque[-1]), 8) if len(torque) else None,
        "gap_depth_vs_time": {
            "t_orbits": times_orbits.tolist(),
            "delta": gap_depths.tolist(),
        },
        "figures": [str(pdf_path), str(png_path)],
        "wall_clock_s": round(wall_clock, 3),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"Results JSON: {output_json}")

    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point."""
    repo_root = Path(__file__).resolve().parents[2]

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path,
                   default=repo_root / "data" / "runs" / "fargo_nu_1Mjup")
    p.add_argument("--output-json", type=Path,
                   default=repo_root / "results" / "analysis" / "fargo_gap_analysis.json")
    p.add_argument("--output-plot", type=Path,
                   default=repo_root / "plots" / "disk" / "fargo_nu_1Mjup_gap")
    args = p.parse_args()

    summary = run_analysis(args.input_dir, args.output_json, args.output_plot)

    print(f"\nGap depth at {summary['t_last_orbits']:.1f} orbits : "
          f"{summary['gap_depth_last']:.4f}")
    print(f"Kanagawa+15 steady-state         : "
          f"{summary['gap_depth_kanagawa_steady']:.4f}")
    print(f"Planet total torque (last output): "
          f"{summary['planet_torque_last']:.4e}")


if __name__ == "__main__":
    main()
