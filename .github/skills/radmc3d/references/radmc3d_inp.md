# radmc3d.inp Parameter Reference

The `radmc3d.inp` file is an optional namelist placed in the RADMC-3D working
directory. Every parameter has a built-in default; you only need to set what
differs from the default. Parameters are written one per line as `key = value`.
RADMC-3D uses **CGS units** throughout.

---

## Monte Carlo photon counts

| Parameter | Default | Description |
|---|---|---|
| `nphot` | `100000` | Photon packages for thermal MC (`mctherm`). Increase for quiet temperature grids in complex geometries |
| `nphot_scat` | `100000` | Photon packages for scattering MC during image synthesis |
| `nphot_spec` | `10000` | Photon packages for SED/spectrum MC |
| `nphot_mono` | `100000` | Photon packages for `mcmono` (local radiation field) |
| `iseed` | `-17933201` | Random seed for all MC runs. Set explicitly for reproducible results |
| `countwrite` | `0` | Write MC progress every N photon packages (0 = off) |

---

## Scattering physics

| Parameter | Default | Description |
|---|---|---|
| `scattering_mode_max` | (auto from opacity) | Max scattering mode: 0 none · 1 isotropic · 2 Henyey-Greenstein · 3 tabulated · 4 pol-last-scat · 5 full Müller matrix |
| `mc_scat_maxtauabs` | `30` | MC photon is terminated after absorbing this optical depth. Lower to 5 for speed in optically thick regions |
| `dust_2daniso_nphi` | `360` | φ-angle resolution for 2D axisymmetric anisotropic scattering |
| `mc_weighted_photons` | `1` | Distribute equal photon counts per source, adjusting packet energies. Prevents waste from photons missing the grid |

---

## Modified Random Walk (for high optical depth)

| Parameter | Default | Description |
|---|---|---|
| `modified_random_walk` | `0` | Set to `1` to enable MRW. Uses diffusion approximation in cells with τ ≫ 1. Strongly recommended for embedded protostellar disks |

**Caveat**: MRW uses the Planck mean opacity, which is less accurate than the
Rosseland mean. It may produce artefacts near strong internal heat sources or
with wavelength-dependent opacities. Verify by comparing a run with/without MRW
on a small grid.

---

## Stellar sources

| Parameter | Default | Description |
|---|---|---|
| `istar_sphere` | `0` | 0 = point source · 1 = finite sphere with radius from `stars.inp`. Use 1 if disk material reaches the stellar surface |

---

## Parallelism

| Parameter | Default | Description |
|---|---|---|
| `setthreads` | `1` | Number of OpenMP threads for image/spectrum ray tracing. Does **not** parallelise `mctherm`. Requires RADMC-3D compiled with OpenMP (`-fopenmp`) |

---

## Ray-tracing quality

| Parameter | Default | Description |
|---|---|---|
| `camera_refine_criterion` | `1.0` | Aggressiveness of sub-pixel refinement for flux conservation. Lower = more refined (slower). Set `0` to disable refinement (use `nofluxcons` on command line instead) |
| `camera_spher_cavity_relsize` | `0.1` | Relative size of central cavity in spherical coordinates for the ray-tracer |

---

## Line radiative transfer

| Parameter | Default | Description |
|---|---|---|
| `incl_lines` | `0` | Set to `1` to enable line RT alongside dust |
| `lines_mode` | `1` | 1 = LTE · 3 = non-LTE (large velocity gradient / Sobolev) |
| `lines_maxdoppler` | `0.3` | Max Doppler shift per cell in units of line width. Increase if velocity gradients are large |
| `lines_slowlte` | `0` | Set to `1` for slow but more accurate LTE (useful for debugging) |

---

## Output format

| Parameter | Default | Description |
|---|---|---|
| `rto_style` | `1` | Output file style: 1 = ASCII (.out) · 2 = unformatted binary (.bout) · 3 = formatted binary |
| `writeimage_unformatted` | `0` | Set to `1` to write `image.bout` (binary). Faster for large images; `radmc3dPy` reads both |

---

## Minimal example radmc3d.inp

```ini
nphot             = 1000000
nphot_scat        = 100000
scattering_mode_max = 1
modified_random_walk = 1
istar_sphere      = 0
setthreads        = 4
iseed             = 42
```

## Full disk-simulation example radmc3d.inp

```ini
nphot               = 2000000    # high photon count for 3D disk
nphot_scat          = 200000
nphot_spec          = 50000
scattering_mode_max = 2          # Henyey-Greenstein for near-IR
modified_random_walk = 1
mc_scat_maxtauabs   = 5          # terminate deep-opacity photons early
istar_sphere        = 0
setthreads          = 8
iseed               = 42
camera_refine_criterion = 0.5
```
