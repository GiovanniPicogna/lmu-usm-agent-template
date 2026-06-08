---
name: radmc3d
description: >
  Post-process dust and gas density grids from PLUTO, FARGO3D, or DustPy
  simulations with RADMC-3D radiative transfer. Produce synthetic dust
  continuum images, SEDs, scattered-light maps, polarization maps, and
  molecular/atomic line emission cubes for direct comparison with ALMA,
  VLA, and JWST observations. Use whenever the user mentions RADMC-3D,
  radmc3d, radiative transfer post-processing, synthetic images from
  hydrodynamics, dust continuum, SEDs, scattered light, thermal emission,
  dust temperature structure, molecular line cubes, channel maps, ALMA
  synthetic observations, beam convolution, radmc3dPy, image.out,
  spectrum.out, mctherm, optical depth maps, or tau surfaces.
  Do NOT trigger for direct hydrodynamics or dust evolution — use the
  pluto, fargo3d, or dustpy skills for those.
argument-hint: "Run directory with density grids, e.g. 'data/runs/disk_1Mjup/ --mode image --wavelength_um 870'"
---

# RADMC-3D Skill
# Dullemond et al. 2012, Astrophysics Source Code Library, ascl:1202.015
# Covers RADMC-3D v2.0+  (CGS units throughout)

---

## When to Use

- Generate synthetic ALMA / VLA / JWST continuum images from hydrodynamical density grids
- Compute spectral energy distributions (SEDs) for comparison with photometry
- Produce scattered-light maps (H-band, J-band) for direct imaging comparisons
- Compute molecular/atomic line emission cubes (e.g. CO J=2–1) for kinematic studies
- Generate optical depth, tau-surface, or column density diagnostic maps
- Compute dust temperature structures via thermal Monte Carlo (`mctherm`)
- Compute local radiation field at each cell (`mcmono`, for chemistry coupling)
- Do **NOT** use for running the hydrodynamics — use `pluto`, `fargo3d`, or `dustpy` skills

---

## RADMC-3D Workflow

RADMC-3D operates in a strict sequence. **Never skip steps.**

```
Step 1 — Set up input files in a working directory
           ├── amr_grid.inp             (grid cell-wall coordinates)
           ├── dust_density.inp         (one or more dust species, g/cm³)
           ├── stars.inp                (stellar source: position, radius, spectrum)
           ├── wavelength_micron.inp    (global wavelength grid in µm)
           ├── dustopac.inp             (opacity species table)
           ├── dustkappa_*.inp          (κ_abs, κ_scat, g tables per species)
           └── radmc3d.inp              (runtime settings; all have defaults)

Step 2 — Compute dust temperatures  ← REQUIRED before thermal imaging
           radmc3d mctherm
           → writes dust_temperature.dat

Step 3 — Produce output
           radmc3d image lambda 870 incl 25 phi 0 npix 300 sizeau 400
           radmc3d sed
           radmc3d spectrum
           radmc3d mcmono    (local radiation field for chemistry)
```

**Scattered-light images** (no thermal emission): skip `mctherm`; set
`scattering_mode_max ≥ 2` and pass `noscat` / `inclstar` as needed.

**Line RT**: add `gas_velocity.inp`, `gas_temperature.inp`,
`numberdens_<mol>.inp`, `molecule_<mol>.inp` (LAMDA format), and `lines.inp`
before imaging; set `incl_lines = 1` and `lines_mode` in `radmc3d.inp`.

---

## Procedure

1. Confirm parameters from the user.
   Read `references/parameters.md` for the full CLI parameter table.
   Read `references/radmc3d_inp.md` for `radmc3d.inp` settings.
   Confirm: input density grid path, dust opacity table, wavelength(s),
   geometry (spherical or Cartesian), output mode (image / SED / spectrum).

2. Call the run script:
   ```bash
   python .github/skills/radmc3d/scripts/run_radmc3d.py \
       --run_dir data/runs/disk_1Mjup/ \
       --wavelength_um 870 \
       --mode image \
       --npix 300 \
       --sizeau 400 \
       --incl_deg 25.0
   ```
   Or via `--json` for full parameter control:
   ```bash
   python .github/skills/radmc3d/scripts/run_radmc3d.py \
       --json '{"run_dir": "data/runs/disk_1Mjup/",
                "wavelength_um": 870,
                "mode": "image",
                "npix": 300,
                "sizeau": 400,
                "incl_deg": 25.0,
                "n_photons_therm": 1000000,
                "scattering_mode_max": 1,
                "dpc": 140.0}'
   ```

3. The script:
   a. Reads density grids from `run_dir` (PLUTO `.dbl` / FARGO3D `.dat` /
      DustPy `.h5`); converts to RADMC-3D spherical format.
   b. Writes `radmc3d.inp`, `amr_grid.inp`, `dust_density.inp`,
      `wavelength_micron.inp`, `dustopac.inp`, `stars.inp` into `run_dir/radmc3d/`.
   c. Runs `radmc3d mctherm` → `dust_temperature.dat`.
   d. Runs `radmc3d image` / `radmc3d sed` / `radmc3d spectrum`.
   e. Reads `image.out` / `spectrum.out` with `radmc3dPy`; writes
      `results/radmc3d/<run_name>_<mode>_<wavelength>um.fits`.
   f. Prints `SUCCESS: output=<path> peak_flux_Jy=<float>` or `ERROR: <msg>`.

4. Parse the last line: starts with `SUCCESS:` or `ERROR:`.
   On error, correct parameters and retry once; report full traceback if still failing.

---

## Reading Outputs with radmc3dPy

Use `radmc3dPy` for all output reading — it handles unit conversions correctly.

```python
import radmc3dPy.image as rimage
import radmc3dPy.analyze as ranalyze

# Read image (stored internally in erg/s/cm²/Hz/sr)
im = rimage.readImage('radmc3d/image.out')
print(im.image.shape)        # (npix, npix, nwav)
print(im.imageJyppix)        # Jy/pixel array

# Beam convolution (built-in; preferred over manual astropy convolution)
# fwhm in arcsec, dpc = source distance in parsec
im.imConv(dpc=140.0, fwhm=[0.04, 0.04], pa=0.0)   # 40 mas beam at 140 pc

# Write FITS with WCS headers
im.writeFits('results/radmc3d/disk_870um.fits',
             dpc=140.0, coord='18h00m00s -23d00m00s')

# Read SED / spectrum  (output file is always spectrum.out for both modes)
s = ranalyze.readSpectrum('radmc3d/spectrum.out')
# s[:,0] = wavelength [µm],  s[:,1] = flux [erg/s/cm²/Hz]

# Channel maps (line RT) — moment maps
moment0 = im.getMomentMap(momnum=0)   # integrated intensity
moment1 = im.getMomentMap(momnum=1)   # intensity-weighted velocity
```

**Unit note**: RADMC-3D outputs intensity in erg/s/cm²/Hz/sr.
Conversion to Jy/pixel: `I_Jy/pix = I × (dx × dy) / d² × 10²³`
where dx, dy are pixel sizes in cm and d is the source distance in cm.

---

## Key radmc3d.inp Settings

The `radmc3d.inp` file controls runtime behaviour. Minimal example:

```ini
nphot             = 1000000   # photon packages for mctherm
nphot_scat        = 100000    # photon packages for scattering MC
nphot_spec        = 10000     # photon packages for spectrum
scattering_mode_max = 1       # 0=none 1=isotropic 2=HG 3=tabulated 4=pol-last 5=full-Müller
modified_random_walk = 1      # enable MRW for high optical depth (τ ≫ 1)
istar_sphere      = 0         # 0=point source  1=finite sphere
setthreads        = 4         # OpenMP threads
```

Full reference: `references/radmc3d_inp.md`

---

## Scattering Mode Reference

| `scattering_mode_max` | Physics | Required opacity file | Use case |
|---|---|---|---|
| 0 | No scattering | `dustkappa_*.inp` (κ_abs only) | Fast optically-thin thermal emission |
| 1 | Isotropic | `dustkappa_*.inp` with κ_scat | Standard ALMA mm continuum |
| 2 | Henyey-Greenstein anisotropic | `dustkappa_*.inp` with κ_scat + g | Moderate near-IR scatter |
| 3 | Tabulated phase function | `dustkapscatmat_*.inp` | Accurate scattered light |
| 4 | Polarization (last scattering only) | `dustkapscatmat_*.inp` | Polarised thermal emission |
| 5 | Full Müller matrix polarization | `dustkapscatmat_*.inp` | H/J-band scattered-light + polarimetry |

- ALMA Band 7 (870 µm) continuum: mode 1 is sufficient
- Near-IR scattered light (H/J-band): use mode 5 with `dustkapscatmat_*.inp`
- **The mode used must match the opacity file supplied** — modes 3–5 require
  the full scattering matrix files; modes 0–2 use the simpler `dustkappa_*.inp`

---

## Parameters

> Full CLI parameter table: [`references/parameters.md`](references/parameters.md)
> Full `radmc3d.inp` reference: [`references/radmc3d_inp.md`](references/radmc3d_inp.md)

**Key CLI parameters:**
`run_dir` · `wavelength_um` · `mode` (`image | sed | spectrum | mctherm | mcmono`) ·
`npix` · `sizeau` · `incl_deg` · `phi_deg` · `posang_deg` · `dpc` ·
`n_photons_therm` (default 1e6) · `n_photons_scat` (default 1e5) ·
`scattering_mode_max` · `dust_opacity_file` · `skip_mctherm`

---

## Output Files

| File | Description |
|---|---|
| `radmc3d/radmc3d.inp` | Runtime settings |
| `radmc3d/amr_grid.inp` | Grid cell-wall coordinates (spherical/Cartesian) |
| `radmc3d/dust_density.inp` | Dust density grid (all species, g/cm³) |
| `radmc3d/stars.inp` | Stellar source (position, radius, mass, spectrum) |
| `radmc3d/wavelength_micron.inp` | Global wavelength grid |
| `radmc3d/dustopac.inp` | Opacity species list |
| `radmc3d/dustkappa_*.inp` | Dust opacity tables (κ_abs, κ_scat, g) |
| `radmc3d/dust_temperature.dat` | Dust temperatures from mctherm |
| `radmc3d/image.out` | Raw image (ASCII default; `.bout` if binary) |
| `radmc3d/spectrum.out` | Raw SED or spectrum (ASCII; both `sed` and `spectrum` modes write here) |
| `results/radmc3d/<name>_image_<λ>um.fits` | Processed FITS image with WCS |
| `results/radmc3d/<name>_sed.fits` | Processed SED as FITS binary table |

**Binary variants**: pass `imageunform` on the command line or set
`rto_style = 3` in `radmc3d.inp` to write `.binp/.bdat/.bout` files for
faster I/O on large grids. `radmc3dPy` reads both formats automatically.

---

## Sanity Checks

- `dust_temperature.dat` must exist and contain T > 0 everywhere before imaging.
- Peak flux > 0 and physically plausible: ~1–100 mJy/beam at 870 µm for a
  typical 50 au protoplanetary disk at 140 pc.
- Image peak not at the edge: if the brightest pixel is on the border,
  `sizeau` is too small — increase it.
- SED turns over at the expected colour temperature for the grain population.
- `nphot ≥ 1e5` for thermal MC; warn but do not block if lower.
- `scattering_mode_max` must match the opacity file type.
- After `mctherm`, max temperature should be near the stellar effective
  temperature at the innermost grid cell.
- Verify that `nr × nθ × nφ` in `amr_grid.inp` equals the cell count in
  `dust_density.inp`.

---

## Common Workflows

### Synthetic ALMA continuum image from FARGO3D disk

```bash
python .github/skills/radmc3d/scripts/run_radmc3d.py \
    --json '{"run_dir":   "data/runs/disk_1Mjup/",
             "wavelength_um": 870,
             "mode":      "image",
             "npix":      500,
             "sizeau":    300,
             "incl_deg":  25.0,
             "dpc":       140.0,
             "n_photons_therm": 1000000,
             "scattering_mode_max": 1}'
```

See also the bundled RADMC-3D example for FARGO3D integration:
`examples/run_ppdisk_fargo3d_1/problem_setup.py` in the RADMC-3D repository.

### Multi-wavelength SED

```bash
python .github/skills/radmc3d/scripts/run_radmc3d.py \
    --run_dir data/runs/disk_1Mjup/ \
    --mode sed \
    --wavelength_um 0.5 1.0 10.0 100.0 870.0 1300.0
```

### Scattered-light image (H-band, 1.6 µm)

```bash
python .github/skills/radmc3d/scripts/run_radmc3d.py \
    --json '{"run_dir":   "data/runs/disk_1Mjup/",
             "wavelength_um": 1.6,
             "mode":      "image",
             "scattering_mode_max": 5,
             "npix":      500,
             "sizeau":    300,
             "incl_deg":  40.0,
             "skip_mctherm": true}'
```

### Optical depth / column density map (diagnostic)

```bash
# Run RADMC-3D directly for a tau map
cd data/runs/disk_1Mjup/radmc3d/
radmc3d image lambda 870 incl 25 npix 300 sizeau 400 tracetau
# image.out now contains optical depth τ instead of intensity

# Column density map (g/cm²)
radmc3d image lambda 870 incl 0 npix 300 sizeau 400 tracecolumn

# Tau = 1 surface (outputs 3D position of τ=1 surface)
radmc3d image lambda 870 incl 25 npix 300 sizeau 400 tausurf 1.0
```

### Beam convolution and FITS export

```python
import radmc3dPy.image as rimage

im = rimage.readImage('radmc3d/image.out')
# Built-in convolution: fwhm in arcsec
im.imConv(dpc=140.0, fwhm=[0.04, 0.04], pa=0.0)
im.writeFits('results/radmc3d/disk_870um_convolved.fits', dpc=140.0)
```

### Second-order ray tracing (smoother images)

```bash
radmc3d image lambda 870 incl 25 npix 300 sizeau 400 secondorder
```

### OpenMP parallel image synthesis

```bash
radmc3d image lambda 870 incl 25 npix 300 sizeau 400 setthreads 8
```

---

## Line Radiative Transfer

For molecular/CO line cubes, additional input files are required:

| File | Description |
|---|---|
| `numberdens_co.inp` | CO number density per cell (molecules/cm³) |
| `gas_temperature.inp` | Gas temperature per cell (K); can equal dust T |
| `gas_velocity.inp` | 3-component velocity field (v_r, v_θ, v_φ) in cm/s |
| `microturbulence.inp` | Turbulent line broadening per cell (cm/s); optional |
| `molecule_co.inp` | Molecular data in LAMDA format |
| `lines.inp` | Specifies which molecules and transitions to compute |

Required additions to `radmc3d.inp`:
```ini
incl_lines  = 1     # enable line RT
lines_mode  = 1     # 1 = LTE   3 = non-LTE (large velocity gradient)
```

Obtain molecular data from the LAMDA database:
https://home.strw.leidenuniv.nl/~moldata/

Run with a velocity window around the line:
```bash
radmc3d image iline 2 imolspec 1 widthkms 10 linenlam 40 incl 25 npix 200 sizeau 300
```

---

## Mandatory Workflow

For every RADMC-3D task, follow this sequence:

1. **Confirm** input density grid path, geometry, and output mode.
2. **Read** `references/parameters.md` and `references/radmc3d_inp.md`.
3. **Run a single-wavelength test image** before batch processing.
4. **Verify** `dust_temperature.dat` exists after `mctherm` before imaging.
5. **Sanity-check** output: flux > 0, no NaN pixels, image size matches `npix`.
6. **Save** all outputs to `results/maps/` or `results/spectra/model/`.

---

## Iron Rules

- Always run `mctherm` before thermal imaging — `dust_temperature.dat` must exist.
- Use a validated dust opacity table (DSHARP preferred); never invent opacity values.
- Set `nphot ≥ 100000` for thermal MC; warn if lower.
- Match `scattering_mode_max` to the opacity file type (see table above).
- Both `radmc3d sed` and `radmc3d spectrum` write output to `spectrum.out` — not `sed.out`.
- Do not trigger this skill for hydrodynamics — use `pluto`, `fargo3d`, or `dustpy`.
- Never overwrite existing `image.out` or `dust_temperature.dat` without user confirmation.
- RADMC-3D uses CGS units internally; use `astropy.units` for all conversions.
- Never hardcode distance in pc or source coordinates — accept them as parameters.

---

## References

- Dullemond et al. 2012, RADMC-3D v2.0 — ascl:1202.015
  (verify exact ADS bibcode via ADS MCP before citing)
- Birnstiel et al. 2018, ApJL 869 L45 — DSHARP opacity table (2018ApJ...869L..45B)
- Huang et al. 2018, ApJL 869 L42 — DSHARP ALMA survey (2018ApJ...869L..42H)
- LAMDA molecular database: https://home.strw.leidenuniv.nl/~moldata/
- RADMC-3D FARGO3D example: examples/run_ppdisk_fargo3d_1/ in the repository
