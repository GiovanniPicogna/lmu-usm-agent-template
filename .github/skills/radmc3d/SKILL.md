---
name: radmc3d
description: >
  Post-process dust and gas density grids from PLUTO, FARGO3D, or DustPy
  simulations with RADMC-3D radiative transfer. Produce synthetic dust
  continuum images, SEDs, scattered-light maps, and molecular line emission
  cubes for direct comparison with ALMA, VLA, and JWST observations.
  Trigger phrases: RADMC-3D, radmc3d, radiative transfer, synthetic image,
  dust continuum, SED, scattered light, thermal emission, ALMA synthetic
  observation, molecular line cube, radmc3dPy, image.out, sed.out, spectrum.out.
  Do NOT trigger for direct hydrodynamics or dust evolution — use the pluto,
  fargo3d, or dustpy skills for those.
argument-hint: "Run directory with density grids, e.g. 'data/runs/disk_1Mjup/ --wavelength_um 870'"
---

# RADMC-3D Skill
# Dullemond et al. 2012, Astrophysics Source Code Library, ascl:1202.015
# Covers RADMC-3D v2.0+

---

## When to Use

- Generate synthetic ALMA / VLA continuum images from hydrodynamical density grids
- Compute spectral energy distributions (SEDs) for comparison with photometry
- Produce scattered-light maps (H-band, J-band) for direct imaging comparisons
- Compute molecular line emission cubes (e.g., CO J=2–1) for kinematic studies
- Validate simulation density structures via forward modelling
- Do **NOT** use this skill for running the hydrodynamics itself —
  use the `pluto`, `fargo3d`, or `dustpy` skills for those

## Procedure

1. Collect parameters from the user.
   Read `references/parameters.md` for the full parameter table.
   Confirm: input density grid path, dust opacity table, wavelength(s),
   geometry (spherical or Cartesian), and output mode (image / SED / spectrum).

2. Call the run script:
   ```bash
   python ~/.agents/skills/radmc3d/scripts/run_radmc3d.py \
       --run_dir data/runs/disk_1Mjup/ \
       --wavelength_um 870 \
       --mode image \
       --npix 300 \
       --sizeau 400
   ```
   Or via `--json`:
   ```bash
   python ~/.agents/skills/radmc3d/scripts/run_radmc3d.py \
       --json '{"run_dir": "data/runs/disk_1Mjup/",
                "wavelength_um": 870,
                "mode": "image",
                "npix": 300,
                "sizeau": 400,
                "incl_deg": 25.0}'
   ```

3. The script:
   a. Reads density grids from `run_dir` (PLUTO `.dbl` / FARGO3D `.dat` /
      DustPy `.h5`); converts to RADMC-3D format.
   b. Writes `radmc3d.inp`, `amr_grid.inp`, `dust_density.inp`,
      `wavelength_micron.inp`, `dustopac.inp` to `run_dir/radmc3d/`.
   c. Runs `radmc3d image` / `radmc3d sed` / `radmc3d spectrum`.
   d. Reads `image.out` / `sed.out` with `radmc3dPy`; writes a
      `results/radmc3d/<run_name>_<mode>_<wavelength>um.fits` FITS image.
   e. Prints `SUCCESS: output=<path> peak_flux_Jy=<float>` or `ERROR: <msg>`.

4. Parse the last line: starts with `SUCCESS:` or `ERROR:`.
   On error, correct parameters and retry once; report traceback if still failing.

5. For beam convolution (synthetic ALMA observation), use `analysisUtils`
   or `astropy.convolution.Gaussian2DKernel`:
   ```python
   from astropy.convolution import Gaussian2DKernel, convolve_fft
   beam_sigma_pix = beam_arcsec / (pixel_scale_arcsec * 2.355)
   kernel = Gaussian2DKernel(beam_sigma_pix)
   convolved = convolve_fft(image, kernel)
   ```

## Parameters

> Full table with types, defaults, and constraints: [`references/parameters.md`](references/parameters.md)

**Key parameters:**
`run_dir` · `wavelength_um` (float or list) · `mode` (`image | sed | spectrum`) ·
`npix` · `sizeau` · `incl_deg` · `phi_deg` · `posang_deg` ·
`n_photons` (default 1e6) · `dust_opacity_file` · `output_dir`

## Output files

| File | Description |
|---|---|
| `radmc3d/radmc3d.inp` | Master RADMC-3D input |
| `radmc3d/dust_density.inp` | Dust density grid (converted) |
| `radmc3d/amr_grid.inp` | AMR / spherical grid |
| `radmc3d/image.out` | Raw image (ASCII) |
| `radmc3d/sed.out` | Raw SED (ASCII) |
| `results/radmc3d/<name>_image_<λ>um.fits` | Final FITS image |
| `results/radmc3d/<name>_sed.fits` | Final SED FITS table |

## Sanity checks

- Peak flux Jy/beam: should be > 0 and physically plausible for the
  wavelength and disk mass (e.g., ~1–100 mJy/beam at 870 µm for a 50 au disk).
- Image peak not at a corner: if brightest pixel is at edge, the grid is too small.
- SED turnover in Rayleigh-Jeans regime at the correct wavelength.
- Warn if `n_photons < 1e5` (high-noise images).

## Common workflows

### Synthetic ALMA continuum image from FARGO3D disk

```bash
# 1. Run FARGO3D to produce density outputs
python ~/.agents/skills/fargo3d/scripts/run_fargo3d.py \
    --run_dir data/runs/disk_1Mjup/

# 2. Post-process with RADMC-3D at 870 µm (ALMA Band 7)
python ~/.agents/skills/radmc3d/scripts/run_radmc3d.py \
    --json '{"run_dir": "data/runs/disk_1Mjup/",
             "wavelength_um": 870,
             "mode": "image",
             "npix": 500,
             "sizeau": 300,
             "incl_deg": 25.0,
             "n_photons": 1000000}'
```

### Multi-wavelength SED

```bash
python ~/.agents/skills/radmc3d/scripts/run_radmc3d.py \
    --run_dir data/runs/disk_1Mjup/ \
    --mode sed \
    --wavelength_um 0.5 1.0 10.0 100.0 870.0
```

## References

- Dullemond et al. 2012, RADMC-3D v2.0 — ascl:1202.015
- Birnstiel et al. 2018, ApJL 869 L45 (DSHARP opacity table — 2018ApJ...869L..45B)
- Huang et al. 2018, ApJL 869 L42 (DSHARP ALMA observations — 2018ApJ...869L..42H)
