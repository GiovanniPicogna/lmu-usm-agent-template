# RADMC-3D Parameters Reference

Full parameter table for `run_radmc3d.py`.
All physical quantities use CGS unless stated otherwise.

---

## Required parameters

| Parameter | Type | Description |
|---|---|---|
| `run_dir` | `str` | Path to simulation run directory containing density output files |
| `mode` | `str` | Computation mode: `image` \| `sed` \| `spectrum` \| `mctherm` \| `mcmono` |
| `wavelength_um` | `float \| list[float]` | Wavelength(s) in µm. Required for `image` mode; used as target wavelength(s) for `sed`/`spectrum` |

---

## Imaging parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `npix` | `int` | `300` | Image size in pixels (square). Use `npixx`/`npixy` for non-square |
| `sizeau` | `float` | `400` | Image half-size in AU (total width = 2 × sizeau) |
| `incl_deg` | `float` | `25.0` | Inclination angle in degrees (0 = face-on, 90 = edge-on) |
| `phi_deg` | `float` | `0.0` | Azimuthal camera angle in degrees |
| `posang_deg` | `float` | `0.0` | Position angle of disk major axis on sky, degrees (rotates image) |
| `dpc` | `float` | `140.0` | Source distance in parsec — used for FITS WCS headers and Jy/beam conversion |
| `secondorder` | `bool` | `false` | Enable second-order ray tracing (linear interpolation across cells); smoother but slower |
| `fluxcons` | `bool` | `true` | Enable recursive sub-pixel refinement for flux conservation (disable with `nofluxcons` for previews) |

---

## Monte Carlo photon counts

RADMC-3D uses separate photon budgets for each MC task. Tune independently.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_photons_therm` | `int` | `1_000_000` | Photon packages for thermal MC (`mctherm`). Increase for noisy temperature grids |
| `n_photons_scat` | `int` | `100_000` | Photon packages for scattering MC in image synthesis. Increase for scattered-light images |
| `n_photons_spec` | `int` | `10_000` | Photon packages for SED/spectrum MC |
| `n_photons_mono` | `int` | `100_000` | Photon packages for `mcmono` (local radiation field) |

**Minimum thresholds**: warn if `n_photons_therm < 1e5` (high-noise temperature grids).
For full-resolution polarimetric images, `n_photons_scat ≥ 1e6` is recommended.

---

## Scattering and opacity

| Parameter | Type | Default | Description |
|---|---|---|---|
| `scattering_mode_max` | `int` | `1` | Max scattering treatment: 0=none, 1=isotropic, 2=Henyey-Greenstein, 3=tabulated phase fn, 4=polarization last-scat, 5=full Müller matrix |
| `dust_opacity_file` | `str` | `"dsharp"` | Opacity table: `dsharp` (Birnstiel+2018) or path to a `dustkappa_*.inp` / `dustkapscatmat_*.inp` file |
| `modified_random_walk` | `bool` | `true` | Enable MRW for high optical depth cells (τ ≫ 1); strongly recommended for embedded disks |

---

## Dust density and vertical structure (FARGO3D reader)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dust_to_gas` | `float` | `0.01` | Global dust-to-gas mass ratio (applied to 2D surface density before vertical extrusion) |
| `aspect_ratio` | `float` | `0.05` | Disk aspect ratio h/r at the reference radius |
| `flaring_index` | `float` | `0.25` | Flaring exponent: h ∝ r^(1 + flaring_index) |
| `n_theta` | `int` | `64` | Number of polar (co-latitude) cells for the 3D theta grid |
| `sigma0_cgs` | `float` | `1.0` | Unit conversion factor: Σ [g/cm²] = Σ [code units] × sigma0_cgs. Read from FARGO3D .par file: Σ₀ = M_star / r₀² |
| `snapshot` | `int` | `-1` | Which FARGO3D output snapshot to use (−1 = last) |

---

## Stellar parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `r_star_rsun` | `float` | `2.0` | Stellar radius in solar radii |
| `m_star_msun` | `float` | `1.0` | Stellar mass in solar masses |
| `t_star_K` | `float` | `5778.0` | Stellar effective temperature in K (written as −T in `stars.inp` to trigger blackbody) |
| `istar_sphere` | `int` | `0` | 0 = point source (default); 1 = finite sphere (needed if disk extends to stellar surface) |

---

## Reproducibility and performance

| Parameter | Type | Default | Description |
|---|---|---|---|
| `iseed` | `int` | `-17933201` | RADMC-3D random seed for MC reproducibility. Written to `radmc3d.inp` |
| `setthreads` | `int` | `1` | Number of OpenMP threads for image synthesis (not mctherm). Install `libgomp` or compile with `-fopenmp` |

---

## Grid parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `grid_type` | `str` | `spherical` | `spherical` (coordinate type 100) \| `cartesian` (coordinate type 1) |
| `n_r` | `int` | read from density file | Number of radial cells |
| `n_theta` | `int` | `64` | Number of polar cells |
| `n_phi` | `int` | read from density file | Number of azimuthal cells |
| `r_in_au` | `float` | read from density file | Inner grid radius in AU |
| `r_out_au` | `float` | read from density file | Outer grid radius in AU |

---

## Wavelength grid for mctherm and SED

| Parameter | Type | Default | Description |
|---|---|---|---|
| `nfreq` | `int` | `200` | Number of frequency/wavelength points in global grid |
| `lambda_min_um` | `float` | `0.1` | Minimum wavelength for global grid (µm) |
| `lambda_max_um` | `float` | `1e7` | Maximum wavelength for global grid (µm) |

---

## Output control

| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip_mctherm` | `bool` | `false` | Skip thermal MC step. Use only for scattered-light images where dust temperature is not needed |
| `output_dir` | `str` | `<run_dir>/radmc3d/` | Working directory where RADMC-3D reads/writes its files |
| `results_dir` | `str` | `results/radmc3d/` | Directory for processed FITS outputs |
| `binary_output` | `bool` | `false` | Write `image.bout` / `spectrum.bout` (binary) instead of ASCII; faster for large images |

---

## Input source detection

The script auto-detects the parent simulation code from `run_dir`:

| File found | Inferred code | Reader |
|---|---|---|
| `gasdens*.dat` | FARGO3D | `numpy.fromfile` + domain files |
| `*.dbl` + `pluto.ini` | PLUTO | `pyPLUTO` or direct binary |
| `*.h5` with DustPy keys | DustPy | `h5py` |

---

## Constraints

- `n_photons_therm ≥ 1e5` (lower → noisy temperatures; warn but do not block)
- `incl_deg ∈ [0, 90]` (0 = face-on, 90 = edge-on; RADMC-3D uses 0–180 internally)
- `sizeau > 0` and `< disk outer radius`
- `wavelength_um > 0`; for ALMA Band 7 use 870; Band 6 use 1300; Band 3 use 3000
- `scattering_mode_max ∈ {0,1,2,3,4,5}`; modes 3–5 require `dustkapscatmat_*.inp`
- `dust_to_gas` should not exceed 0.1 without explicit physical justification
