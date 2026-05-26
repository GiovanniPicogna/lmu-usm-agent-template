# RADMC-3D Parameters Reference

Full parameter table for `run_radmc3d.py`.

---

## Required parameters

| Parameter | Type | Description |
|---|---|---|
| `run_dir` | `str` | Path to simulation run directory containing density output files |
| `mode` | `str` | Computation mode: `image` \| `sed` \| `spectrum` \| `mctherm` |
| `wavelength_um` | `float \| list[float]` | Wavelength(s) in µm. Required for `image` mode |

## Optional parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `npix` | `int` | `300` | Image size in pixels (square) |
| `sizeau` | `float` | `400` | Image half-size in AU |
| `incl_deg` | `float` | `0.0` | Inclination in degrees (0 = face-on) |
| `phi_deg` | `float` | `0.0` | Azimuthal viewing angle in degrees |
| `posang_deg` | `float` | `0.0` | Position angle of disk major axis on sky, degrees |
| `n_photons` | `int` | `1000000` | Number of photon packages for Monte Carlo |
| `n_photons_scat` | `int` | `n_photons` | Photon packages for scattering |
| `dust_opacity_file` | `str` | `"dsharp"` | Opacity table: `dsharp` (Birnstiel+2018) \| path to `.inp` file |
| `dust_to_gas` | `float` | `0.01` | Global dust-to-gas mass ratio (ignored if per-species densities provided) |
| `grain_size_cm` | `float \| null` | `null` | Single grain size in cm (overrides distribution) |
| `nfreq` | `int` | `200` | Number of frequency points for SED / spectrum mode |
| `lambda_min_um` | `float` | `0.1` | Minimum wavelength for SED (µm) |
| `lambda_max_um` | `float` | `1e7` | Maximum wavelength for SED (µm) |
| `thermal_monte_carlo` | `bool` | `true` | Run thermal Monte Carlo before imaging |
| `scattering_mode_max` | `int` | `1` | 0=no scat, 1=isotropic, 5=full Müller matrix |
| `output_dir` | `str` | `<run_dir>/radmc3d/` | Directory for RADMC-3D input/output files |
| `results_dir` | `str` | `results/radmc3d/` | Directory for processed FITS outputs |

## Grid parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `grid_type` | `str` | `spherical` | `spherical` \| `cartesian` |
| `n_r` | `int` | read from density file | Number of radial cells |
| `n_theta` | `int` | read from density file | Number of polar cells |
| `n_phi` | `int` | read from density file | Number of azimuthal cells |
| `r_in_au` | `float` | read from density file | Inner grid radius in AU |
| `r_out_au` | `float` | read from density file | Outer grid radius in AU |

## Input source detection

The script auto-detects the parent simulation code from `run_dir`:

| File found | Inferred code | Reader |
|---|---|---|
| `gasdens*.dat` | FARGO3D | `numpy.fromfile` binary |
| `*.dbl` + `pluto.ini` | PLUTO | `pyPLUTO` |
| `*.h5` with DustPy keys | DustPy | `h5py` |

## Constraints

- `n_photons` ≥ 1e5 (lower → noisy images; warn but do not block)
- `incl_deg` ∈ [0, 90] (0 = face-on, 90 = edge-on)
- `sizeau` > 0 and < disk outer radius
- `wavelength_um` > 0; for ALMA Band 7 use 870; for Band 6 use 1300
- `scattering_mode_max` = 5 required for scattered-light images (H/J band)
