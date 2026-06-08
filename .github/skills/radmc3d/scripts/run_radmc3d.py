#!/usr/bin/env python3
"""
RADMC-3D radiative transfer wrapper for LMU protoplanetary disk simulations.

Reads FARGO3D / DustPy / PLUTO density outputs, converts them to RADMC-3D
spherical format, runs thermal Monte Carlo and image/SED/spectrum synthesis,
and writes FITS output for comparison with ALMA/VLA/JWST observations.

Supported input codes
---------------------
FARGO3D : gasdens*.dat + domain_r.dat + domain_y.dat in run_dir
DustPy  : *.h5 with DustPy HDF5 structure in run_dir
PLUTO   : *.dbl + pluto.ini in run_dir  (stub — extend as needed)

Required outputs
----------------
  results/radmc3d/<run_name>_image_<λ>um.fits   (mode=image)
  results/radmc3d/<run_name>_sed.fits            (mode=sed or spectrum)
  results/radmc3d/dust_temperature.dat           (mode=mctherm)

Terminal output (last line always starts with SUCCESS: or ERROR:)

Usage
-----
  python run_radmc3d.py --run_dir data/runs/disk_1Mjup/ --wavelength_um 870
  python run_radmc3d.py --json '{"run_dir": "data/runs/disk_1Mjup/", ...}'
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.io import fits


# ── physical constants and unit factors ──────────────────────────────────────

AU_TO_CM: float = u.au.to(u.cm)
RSUN_TO_CM: float = u.Rsun.to(u.cm)
MSUN_TO_G: float = u.Msun.to(u.g)


# ── amr_grid.inp ─────────────────────────────────────────────────────────────


def write_amr_grid(
    output_dir: Path,
    r_interfaces_cm: np.ndarray,
    theta_interfaces: np.ndarray,
    phi_interfaces: np.ndarray,
) -> None:
    """
    Write amr_grid.inp for a regular (style 0) spherical grid.

    Parameters
    ----------
    r_interfaces_cm : np.ndarray
        Radial cell-wall positions in cm, length nr+1.
    theta_interfaces : np.ndarray
        Co-latitude cell-wall positions in radians, length ntheta+1.
    phi_interfaces : np.ndarray
        Azimuthal cell-wall positions in radians, length nphi+1.
    """
    nr = len(r_interfaces_cm) - 1
    nt = len(theta_interfaces) - 1
    np_ = len(phi_interfaces) - 1

    with open(output_dir / "amr_grid.inp", "w") as f:
        f.write("1\n")  # iformat
        f.write("0\n")  # grid style: regular, no AMR
        f.write("100\n")  # coordinate system: spherical
        f.write("0\n")  # gridinfo: no extra info
        f.write("1 1 1\n")  # all three dimensions active
        f.write(f"{nr} {nt} {np_}\n")
        for r in r_interfaces_cm:
            f.write(f"{r:.6e}\n")
        for t in theta_interfaces:
            f.write(f"{t:.6e}\n")
        for p in phi_interfaces:
            f.write(f"{p:.6e}\n")


# ── wavelength_micron.inp ─────────────────────────────────────────────────────


def write_wavelength_grid(output_dir: Path, wavelengths_um: list[float]) -> None:
    """Write wavelength_micron.inp sorted in ascending order."""
    wl_sorted = sorted(set(wavelengths_um))
    with open(output_dir / "wavelength_micron.inp", "w") as f:
        f.write(f"{len(wl_sorted)}\n")
        for lam in wl_sorted:
            f.write(f"{lam:.6e}\n")


def make_thermal_wavelength_grid(target_um: list[float]) -> list[float]:
    """
    Build a broad wavelength grid suitable for mctherm.

    Covers 0.1 µm (stellar UV) through 10 mm (far-IR emission) with the
    user-requested wavelengths included.
    """
    grid = np.concatenate(
        [
            np.logspace(-1, 1, 20),  # 0.1–10 µm   stellar / scattered light
            np.logspace(1, 4, 60),  # 10 µm–10 mm  dust thermal emission
        ]
    )
    return sorted(set(grid.tolist() + [float(w) for w in target_um]))


# ── stars.inp ────────────────────────────────────────────────────────────────


def write_stars(
    output_dir: Path,
    r_star_rsun: float,
    m_star_msun: float,
    t_star_K: float,
    wavelengths_um: list[float],
) -> None:
    """
    Write stars.inp for a single blackbody star at the grid origin.

    A negative effective temperature in stars.inp triggers RADMC-3D's
    built-in blackbody spectrum computation (no flux grid needed).

    Parameters
    ----------
    r_star_rsun : float  Stellar radius in solar radii.
    m_star_msun : float  Stellar mass in solar masses.
    t_star_K    : float  Effective temperature in K.
    wavelengths_um : list[float]  Wavelength grid (must match wavelength_micron.inp).
    """
    r_cm = r_star_rsun * RSUN_TO_CM
    m_g = m_star_msun * MSUN_TO_G
    nlam = len(wavelengths_um)

    with open(output_dir / "stars.inp", "w") as f:
        f.write("2\n")  # iformat
        f.write(f"1 {nlam}\n\n")  # nstars  nlam
        f.write(f"{r_cm:.6e} {m_g:.6e} 0.0 0.0 0.0\n\n")  # r m x y z
        for lam in sorted(wavelengths_um):
            f.write(f"{lam:.6e}\n")
        f.write(f"\n{-abs(t_star_K):.6e}\n")  # negative T → blackbody


# ── radmc3d.inp ───────────────────────────────────────────────────────────────


def write_radmc3d_inp(
    output_dir: Path,
    n_photons_therm: int = 1_000_000,
    n_photons_scat: int = 100_000,
    n_photons_spec: int = 10_000,
    scattering_mode_max: int = 1,
    modified_random_walk: bool = True,
    istar_sphere: int = 0,
    setthreads: int = 1,
    iseed: int = -17933201,
    incl_lines: bool = False,
    lines_mode: int = 1,
) -> None:
    """Write radmc3d.inp runtime control file."""
    with open(output_dir / "radmc3d.inp", "w") as f:
        f.write(f"nphot               = {n_photons_therm}\n")
        f.write(f"nphot_scat          = {n_photons_scat}\n")
        f.write(f"nphot_spec          = {n_photons_spec}\n")
        f.write(f"scattering_mode_max = {scattering_mode_max}\n")
        f.write(f"istar_sphere        = {istar_sphere}\n")
        f.write(f"iseed               = {iseed}\n")
        if modified_random_walk:
            f.write("modified_random_walk = 1\n")
        if setthreads > 1:
            f.write(f"setthreads          = {setthreads}\n")
        if incl_lines:
            f.write("incl_lines          = 1\n")
            f.write(f"lines_mode          = {lines_mode}\n")


# ── dustopac.inp ──────────────────────────────────────────────────────────────


def write_dustopac(output_dir: Path, opacity_name: str = "dsharp") -> None:
    """
    Write dustopac.inp referencing a single dust species.

    Uses opacity type 1 (dustkappa_<name>.inp file with κ_abs, κ_scat, g).
    """
    with open(output_dir / "dustopac.inp", "w") as f:
        f.write("2\n")  # iformat
        f.write("1\n")  # number of species
        f.write("=" * 76 + "\n")
        f.write("1\n")  # opacity type: dustkappa file
        f.write("0\n")  # not grain-aligned
        f.write(f"{opacity_name}\n")
        f.write("-" * 76 + "\n")


# ── dust_density.inp ──────────────────────────────────────────────────────────


def write_dust_density(output_dir: Path, rho_3d: np.ndarray) -> None:
    """
    Write dust_density.inp for a single dust species.

    Parameters
    ----------
    rho_3d : np.ndarray
        Volume density in g/cm³, shape (nr, ntheta, nphi).
        RADMC-3D spherical ordering: r outermost, phi innermost.
    """
    nr, nt, np_ = rho_3d.shape
    ncells = nr * nt * np_

    with open(output_dir / "dust_density.inp", "w") as f:
        f.write("1\n")  # iformat
        f.write(f"{ncells}\n")  # total number of cells
        f.write("1\n")  # number of dust species
        # r outermost, theta middle, phi innermost
        flat = rho_3d.reshape(-1)
        for val in flat:
            f.write(f"{val:.6e}\n")


# ── FARGO3D reader ────────────────────────────────────────────────────────────


def read_fargo3d_grid(run_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Read FARGO3D radial and azimuthal cell-wall positions.

    Returns
    -------
    r_interfaces : np.ndarray  Radial interfaces in AU (from domain_r.dat).
    phi_interfaces : np.ndarray  Azimuthal interfaces in radians (domain_y.dat).
    """
    r_file = run_dir / "domain_r.dat"
    if not r_file.exists():
        raise FileNotFoundError(
            f"domain_r.dat not found in {run_dir}. " "This file must be present for FARGO3D runs."
        )
    r_interfaces = np.loadtxt(str(r_file))

    phi_file = run_dir / "domain_y.dat"
    if phi_file.exists():
        phi_interfaces = np.loadtxt(str(phi_file))
    else:
        # Fall back to uniform grid
        nr = len(r_interfaces) - 1
        phi_interfaces = np.linspace(0.0, 2.0 * np.pi, nr + 1)

    return r_interfaces, phi_interfaces


def read_fargo3d_sigma(
    run_dir: Path,
    snapshot: int,
    nr: int,
    nphi: int,
    sigma0_cgs: float,
) -> np.ndarray:
    """
    Read FARGO3D gas surface density and return it in g/cm².

    Parameters
    ----------
    snapshot : int   Index into sorted gasdens*.dat list; -1 = last.
    sigma0_cgs : float  Code-unit scaling factor: Σ[g/cm²] = Σ[code] × sigma0_cgs.
                  Compute from the .par file: sigma0_cgs = M_star[g] / r0[cm]².
    """
    dens_files = sorted(run_dir.glob("gasdens*.dat"))
    if not dens_files:
        raise FileNotFoundError(f"No gasdens*.dat files in {run_dir}")

    target = dens_files[snapshot]
    sigma_code = np.fromfile(str(target), dtype=np.float64).reshape(nr, nphi)
    return sigma_code * sigma0_cgs


def extrude_sigma_to_3d(
    sigma_gcm2: np.ndarray,
    r_interfaces_au: np.ndarray,
    theta_interfaces: np.ndarray,
    phi_interfaces: np.ndarray,
    dust_to_gas: float,
    aspect_ratio: float,
    flaring_index: float,
) -> np.ndarray:
    """
    Extrude 2D surface density to 3D volume density using a Gaussian vertical profile.

    ρ(r, θ, φ) = Σ_d / (√2π h(r)) × exp(−z²/(2h²))

    where z = r cos θ and h(r) = h₀ r^(1+β) with h₀ = aspect_ratio × r_ref^(-β).

    Parameters
    ----------
    sigma_gcm2 : np.ndarray   Gas surface density in g/cm², shape (nr, nphi).
    r_interfaces_au : np.ndarray  Radial cell walls in AU.
    theta_interfaces : np.ndarray  Co-latitude cell walls in radians.
    phi_interfaces : np.ndarray  Azimuth cell walls in radians.
    dust_to_gas : float  Dust-to-gas mass ratio.
    aspect_ratio : float  h/r at the reference radius (midpoint of radial grid).
    flaring_index : float  h ∝ r^(1 + flaring_index).

    Returns
    -------
    np.ndarray  Dust volume density in g/cm³, shape (nr, ntheta, nphi).
    """
    nr = len(r_interfaces_au) - 1
    ntheta = len(theta_interfaces) - 1

    r_centers_au = 0.5 * (r_interfaces_au[:-1] + r_interfaces_au[1:])
    r_centers_cm = r_centers_au * AU_TO_CM
    r_ref_cm = r_centers_cm[nr // 2]

    theta_centers = 0.5 * (theta_interfaces[:-1] + theta_interfaces[1:])

    rho_dust = np.zeros((nr, ntheta, sigma_gcm2.shape[1]))

    for ir in range(nr):
        r_cm = r_centers_cm[ir]
        # Scale height at this radius
        h_cm = aspect_ratio * r_ref_cm * (r_cm / r_ref_cm) ** (1.0 + flaring_index)

        sigma_dust = dust_to_gas * sigma_gcm2[ir, :]  # (nphi,)  g/cm²
        norm = sigma_dust / (np.sqrt(2.0 * np.pi) * h_cm)  # (nphi,)

        z_cm = r_cm * np.cos(theta_centers)  # (ntheta,)  vertical height

        for it in range(ntheta):
            rho_dust[ir, it, :] = norm * np.exp(-0.5 * (z_cm[it] / h_cm) ** 2)

    return rho_dust


def make_theta_grid(
    r_interfaces_au: np.ndarray, aspect_ratio: float, flaring_index: float, n_theta: int
) -> np.ndarray:
    """
    Build co-latitude (theta) cell-wall array centred on the midplane (π/2).

    The opening is set to ±4 scale heights at the outer grid edge.
    """
    r_au = r_interfaces_au[-1]  # outer radius
    r_ref_au = r_interfaces_au[len(r_interfaces_au) // 2]
    h_over_r_outer = aspect_ratio * (r_au / r_ref_au) ** flaring_index
    theta_half = min(4.0 * h_over_r_outer, np.pi / 4.0)

    theta_mid = np.pi / 2.0
    return np.linspace(theta_mid - theta_half, theta_mid + theta_half, n_theta + 1)


# ── DustPy reader ─────────────────────────────────────────────────────────────


def read_dustpy_density(run_dir: Path, snapshot: int, dust_to_gas: float) -> tuple:
    """
    Read dust surface density from a DustPy HDF5 output file.

    Returns sigma_gcm2 (nr, nphi=1), r_interfaces_au, phi_interfaces.
    DustPy produces 1D radial grids; we broadcast to a single phi cell.
    """
    import h5py  # local import to avoid hard dependency when not using DustPy

    h5_files = sorted(run_dir.glob("*.h5"))
    if not h5_files:
        raise FileNotFoundError(f"No .h5 files found in {run_dir}")

    target = h5_files[snapshot]
    with h5py.File(str(target), "r") as f:
        # DustPy stores dust surface density under Dust/Sigma
        if "Dust" in f and "Sigma" in f["Dust"]:
            sigma_dust = f["Dust/Sigma"][:]  # shape (nr, nspec) in g/cm²
            sigma_total = sigma_dust.sum(axis=-1)  # sum over grain sizes
        elif "gas" in f and "Sigma" in f["gas"]:
            sigma_gas = f["gas/Sigma"][:]
            sigma_total = dust_to_gas * sigma_gas
        else:
            raise KeyError(
                f"Cannot locate surface density in {target}. "
                "Expected Dust/Sigma or gas/Sigma groups."
            )

        if "grid" in f and "r" in f["grid"]:
            r_interfaces_au = f["grid/r_i"][:] / AU_TO_CM  # cm → AU
        else:
            raise KeyError(f"Cannot find grid/r_i in {target}")

    # Broadcast 1D radial profile to a single azimuthal cell
    sigma_2d = sigma_total[:, np.newaxis]  # (nr, 1)
    phi_interfaces = np.array([0.0, 2.0 * np.pi])

    return sigma_2d, r_interfaces_au, phi_interfaces


# ── opacity helper ────────────────────────────────────────────────────────────


def install_opacity(radmc3d_dir: Path, opacity_name: str) -> None:
    """
    Copy or locate the dust opacity file into radmc3d_dir.

    Search order:
      1. Absolute path supplied by user
      2. Skill opacities directory (alongside this script)
      3. Current working directory
      4. Writes a minimal stub and emits a warning (allows testing without opacities)
    """
    if opacity_name == "dsharp":
        fname = "dustkappa_dsharp.inp"
    else:
        fname = Path(opacity_name).name

    if (radmc3d_dir / fname).exists():
        return  # already present

    search = [
        Path(opacity_name) if Path(opacity_name).is_absolute() else None,
        Path(__file__).parent.parent / "opacities" / fname,
        Path.home() / ".agents/skills/radmc3d/opacities" / fname,
        Path("opacities") / fname,
    ]
    for candidate in search:
        if candidate is not None and candidate.exists():
            shutil.copy(str(candidate), str(radmc3d_dir / fname))
            return

    print(
        f"WARNING: Opacity file '{fname}' not found. "
        "Download DSHARP opacities from https://github.com/birnstiel/dsharp_opac "
        "and place dustkappa_dsharp.inp in the radmc3d directory. "
        "A minimal placeholder has been written — results will be unphysical.",
        file=sys.stderr,
    )
    _write_placeholder_opacity(radmc3d_dir / fname)


def _write_placeholder_opacity(path: Path) -> None:
    """Write a two-point opacity stub so RADMC-3D can start."""
    with open(path, "w") as f:
        f.write("2\n")  # iformat: lambda, kappa_abs, kappa_scat, g
        f.write("2\n")  # nwav
        f.write("1.0      1.0  0.1  0.0\n")
        f.write("10000.0  0.1  0.0  0.0\n")


# ── subprocess runner ─────────────────────────────────────────────────────────


def run_radmc3d_command(radmc3d_dir: Path, args: list[str]) -> None:
    """Run a radmc3d command in radmc3d_dir. Raises RuntimeError on failure."""
    cmd = ["radmc3d"] + args
    result = subprocess.run(cmd, cwd=str(radmc3d_dir), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"radmc3d {' '.join(args)} failed (exit {result.returncode}):\n"
            f"{result.stderr}\n{result.stdout}"
        )


# ── output readers ────────────────────────────────────────────────────────────


def image_to_fits(
    radmc3d_dir: Path,
    output_fits: Path,
    dpc: float,
) -> float:
    """
    Read image.out with radmc3dPy and write a FITS file.

    Returns the peak flux in Jy/pixel.
    """
    try:
        import radmc3dPy.image as rimage
    except ImportError as exc:
        raise ImportError(
            "radmc3dPy is required to read RADMC-3D output. " "Install with: pip install radmc3dPy"
        ) from exc

    im = rimage.readImage(str(radmc3d_dir / "image.out"))
    im.writeFits(str(output_fits), dpc=dpc)
    return float(np.nanmax(im.imageJyppix))


def spectrum_to_fits(radmc3d_dir: Path, output_fits: Path) -> float:
    """
    Read spectrum.out and write a FITS binary table.

    Both `radmc3d sed` and `radmc3d spectrum` write output to spectrum.out.
    Returns the peak flux in Jy.
    """
    spec_file = radmc3d_dir / "spectrum.out"
    if not spec_file.exists():
        raise FileNotFoundError(
            f"spectrum.out not found in {radmc3d_dir}. "
            "Run 'radmc3d sed' or 'radmc3d spectrum' first."
        )

    # spectrum.out format: header lines, then wavelength[µm]  flux[erg/s/cm²/Hz]
    data = np.loadtxt(str(spec_file), skiprows=3)
    wavelength_um = data[:, 0]
    flux_jy = data[:, 1] * 1.0e23  # erg/s/cm²/Hz → Jy

    col_lam = fits.Column(name="wavelength_um", format="D", array=wavelength_um, unit="micron")
    col_flux = fits.Column(name="flux_Jy", format="D", array=flux_jy, unit="Jy")
    hdu = fits.BinTableHDU.from_columns([col_lam, col_flux])
    hdu.writeto(str(output_fits), overwrite=False)
    return float(np.nanmax(flux_jy))


# ── main pipeline ─────────────────────────────────────────────────────────────


def setup_and_run(params: dict) -> tuple[str, float]:
    """
    Full RADMC-3D pipeline: read density → write inputs → mctherm → image/SED.

    Returns (output_path, peak_flux_jy).
    """
    run_dir = Path(params["run_dir"])
    if not run_dir.exists():
        raise FileNotFoundError(f"run_dir not found: {run_dir}")

    mode = params.get("mode", "image")
    wavelength_um_raw = params.get("wavelength_um", [870.0])
    if isinstance(wavelength_um_raw, (int, float)):
        wavelength_um_raw = [float(wavelength_um_raw)]
    wavelength_um = [float(w) for w in wavelength_um_raw]

    radmc3d_dir = run_dir / "radmc3d"
    radmc3d_dir.mkdir(parents=True, exist_ok=True)

    results_dir = Path(params.get("results_dir", "results/radmc3d"))
    results_dir.mkdir(parents=True, exist_ok=True)

    # ── detect simulation type and read density ───────────────────────────

    if any(run_dir.glob("gasdens*.dat")):
        sim_type = "fargo3d"
    elif any(run_dir.glob("*.h5")):
        sim_type = "dustpy"
    elif (run_dir / "pluto.ini").exists() or any(run_dir.glob("*.dbl")):
        raise NotImplementedError(
            "PLUTO reader is not yet implemented. "
            "Write amr_grid.inp and dust_density.inp manually and call "
            "run_radmc3d.py with a pre-populated radmc3d/ directory."
        )
    else:
        raise ValueError(
            f"Cannot detect simulation type in {run_dir}. "
            "Expected: gasdens*.dat (FARGO3D), *.h5 (DustPy), or *.dbl + pluto.ini (PLUTO)."
        )

    aspect_ratio = float(params.get("aspect_ratio", 0.05))
    flaring_index = float(params.get("flaring_index", 0.25))
    dust_to_gas = float(params.get("dust_to_gas", 0.01))
    n_theta = int(params.get("n_theta", 64))

    if sim_type == "fargo3d":
        r_interfaces_au, phi_interfaces = read_fargo3d_grid(run_dir)
        nr = len(r_interfaces_au) - 1
        nphi = len(phi_interfaces) - 1

        # sigma0_cgs = M_star[g] / r0[cm]² — read from .par or accept as param
        sigma0_cgs = float(params.get("sigma0_cgs", 1.0))
        if sigma0_cgs == 1.0:
            print(
                "WARNING: sigma0_cgs = 1.0 (default). "
                "Set sigma0_cgs = M_star[g] / r0[cm]² from your FARGO3D .par file "
                "to obtain physically correct surface densities.",
                file=sys.stderr,
            )

        sigma_gcm2 = read_fargo3d_sigma(
            run_dir,
            snapshot=int(params.get("snapshot", -1)),
            nr=nr,
            nphi=nphi,
            sigma0_cgs=sigma0_cgs,
        )

    elif sim_type == "dustpy":
        sigma_gcm2, r_interfaces_au, phi_interfaces = read_dustpy_density(
            run_dir,
            snapshot=int(params.get("snapshot", -1)),
            dust_to_gas=dust_to_gas,
        )

    theta_interfaces = make_theta_grid(r_interfaces_au, aspect_ratio, flaring_index, n_theta)
    rho_3d = extrude_sigma_to_3d(
        sigma_gcm2,
        r_interfaces_au,
        theta_interfaces,
        phi_interfaces,
        dust_to_gas=dust_to_gas,
        aspect_ratio=aspect_ratio,
        flaring_index=flaring_index,
    )

    # ── build wavelength grid and write input files ───────────────────────

    wl_mctherm = make_thermal_wavelength_grid(wavelength_um)
    r_cm = r_interfaces_au * AU_TO_CM

    write_amr_grid(radmc3d_dir, r_cm, theta_interfaces, phi_interfaces)
    write_wavelength_grid(radmc3d_dir, wl_mctherm)
    write_stars(
        radmc3d_dir,
        r_star_rsun=float(params.get("r_star_rsun", 2.0)),
        m_star_msun=float(params.get("m_star_msun", 1.0)),
        t_star_K=float(params.get("t_star_K", 5778.0)),
        wavelengths_um=wl_mctherm,
    )
    write_dust_density(radmc3d_dir, rho_3d)
    write_dustopac(radmc3d_dir, params.get("dust_opacity_file", "dsharp"))
    write_radmc3d_inp(
        radmc3d_dir,
        n_photons_therm=int(params.get("n_photons_therm", 1_000_000)),
        n_photons_scat=int(params.get("n_photons_scat", 100_000)),
        n_photons_spec=int(params.get("n_photons_spec", 10_000)),
        scattering_mode_max=int(params.get("scattering_mode_max", 1)),
        modified_random_walk=bool(params.get("modified_random_walk", True)),
        istar_sphere=int(params.get("istar_sphere", 0)),
        setthreads=int(params.get("setthreads", 1)),
        iseed=int(params.get("iseed", -17933201)),
    )

    install_opacity(radmc3d_dir, params.get("dust_opacity_file", "dsharp"))

    # ── run thermal Monte Carlo ───────────────────────────────────────────

    if not params.get("skip_mctherm", False):
        run_radmc3d_command(radmc3d_dir, ["mctherm"])
        temp_file = radmc3d_dir / "dust_temperature.dat"
        if not temp_file.exists():
            raise RuntimeError(
                "mctherm ran but dust_temperature.dat was not created. "
                "Check RADMC-3D stdout for errors."
            )

    if mode == "mctherm":
        return str(radmc3d_dir / "dust_temperature.dat"), 0.0

    # ── run image / sed / spectrum ────────────────────────────────────────

    run_name = run_dir.name

    if mode == "image":
        incl = float(params.get("incl_deg", 25.0))
        phi = float(params.get("phi_deg", 0.0))
        posang = float(params.get("posang_deg", 0.0))
        npix = int(params.get("npix", 300))
        sizeau = float(params.get("sizeau", 400.0))

        run_radmc3d_command(
            radmc3d_dir,
            [
                "image",
                "lambda",
                str(wavelength_um[0]),
                "incl",
                str(incl),
                "phi",
                str(phi),
                "posang",
                str(posang),
                "npix",
                str(npix),
                "sizeau",
                str(sizeau),
            ],
        )

        lam_int = int(round(wavelength_um[0]))
        output_fits = results_dir / f"{run_name}_image_{lam_int}um.fits"
        dpc = float(params.get("dpc", 140.0))
        peak_flux = image_to_fits(radmc3d_dir, output_fits, dpc=dpc)
        return str(output_fits), peak_flux

    elif mode in ("sed", "spectrum"):
        run_radmc3d_command(radmc3d_dir, [mode])
        output_fits = results_dir / f"{run_name}_{mode}.fits"
        peak_flux = spectrum_to_fits(radmc3d_dir, output_fits)
        return str(output_fits), peak_flux

    else:
        raise ValueError(f"Unknown mode '{mode}'. Choose from: image | sed | spectrum | mctherm")


# ── CLI ───────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="RADMC-3D wrapper for LMU disk simulations")
    p.add_argument(
        "--json", type=str, help="JSON string with all parameters (overrides all other flags)"
    )
    p.add_argument("--run_dir", type=str)
    p.add_argument("--mode", default="image", choices=["image", "sed", "spectrum", "mctherm"])
    p.add_argument("--wavelength_um", type=float, nargs="+", default=[870.0])
    p.add_argument("--npix", type=int, default=300)
    p.add_argument("--sizeau", type=float, default=400.0)
    p.add_argument("--incl_deg", type=float, default=25.0)
    p.add_argument("--phi_deg", type=float, default=0.0)
    p.add_argument("--posang_deg", type=float, default=0.0)
    p.add_argument(
        "--dpc",
        type=float,
        default=140.0,
        help="Source distance in parsec (for FITS WCS and Jy conversion)",
    )
    p.add_argument("--n_photons_therm", type=int, default=1_000_000)
    p.add_argument("--n_photons_scat", type=int, default=100_000)
    p.add_argument("--scattering_mode_max", type=int, default=1)
    p.add_argument("--dust_opacity_file", type=str, default="dsharp")
    p.add_argument("--dust_to_gas", type=float, default=0.01)
    p.add_argument(
        "--sigma0_cgs",
        type=float,
        default=1.0,
        help="FARGO3D code-unit conversion: Sigma[g/cm2] = Sigma[code] * sigma0_cgs",
    )
    p.add_argument("--aspect_ratio", type=float, default=0.05)
    p.add_argument("--flaring_index", type=float, default=0.25)
    p.add_argument("--n_theta", type=int, default=64)
    p.add_argument("--r_star_rsun", type=float, default=2.0)
    p.add_argument("--m_star_msun", type=float, default=1.0)
    p.add_argument("--t_star_K", type=float, default=5778.0)
    p.add_argument("--iseed", type=int, default=-17933201)
    p.add_argument("--setthreads", type=int, default=1)
    p.add_argument(
        "--snapshot", type=int, default=-1, help="Which simulation snapshot to use (-1 = last)"
    )
    p.add_argument(
        "--skip_mctherm",
        action="store_true",
        help="Skip thermal Monte Carlo (for scattered-light images)",
    )
    p.add_argument("--results_dir", type=str, default="results/radmc3d")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.json:
        params = json.loads(args.json)
    else:
        params = vars(args)
        params.pop("json", None)

    if not params.get("run_dir"):
        parser.print_help(sys.stderr)
        print("ERROR: --run_dir is required", file=sys.stderr)
        sys.exit(1)

    n_photons = params.get("n_photons_therm", 1_000_000)
    if int(n_photons) < 100_000:
        print(
            f"WARNING: n_photons_therm={n_photons} is below the recommended minimum "
            "of 100000. Dust temperatures may be noisy.",
            file=sys.stderr,
        )

    try:
        output_path, peak_flux = setup_and_run(params)
        print(f"SUCCESS: output={output_path} peak_flux_Jy={peak_flux:.4e}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
