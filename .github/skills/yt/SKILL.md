---
name: yt
description: >
  Volumetric analysis and visualisation of SPH and AMR astrophysical
  simulation snapshots. Load GADGET/Magneticum HDF5 snapshots or PLUTO/FARGO3D
  AMR outputs; compute projections, slices, radial profiles, phase diagrams,
  and derived fields; produce publication-quality maps.
  Trigger phrases: yt, yt.load, yt-project, SPH snapshot, AMR snapshot,
  Magneticum, GADGET HDF5, projection plot, temperature map, density slice,
  phase diagram, radial profile, sphere, halo analysis, yt analysis,
  yt ProjectionPlot, yt ProfilePlot, yt FITSImageData, gas temperature map,
  ICM thermodynamic map, halo gas fraction.
  Do NOT trigger for pure particle catalogues (use h5py directly) or
  when the snapshot format is a custom binary (use numpy.fromfile instead).
argument-hint: "Snapshot path and analysis task, e.g. 'data/snapshots/snap_144.hdf5 — projected temperature map'"
---

# yt Skill
# Turk et al. 2011, ApJS 192 9  •  https://yt-project.org
# Covers yt 4.x (Python 3.11+)

---

## When to Use

- Load and visualise Magneticum/GADGET HDF5 snapshots
- Compute projected maps (temperature, density, X-ray luminosity)
- Build radial profiles and phase diagrams of halos or substructure
- Derive custom fields (cooling time, entropy, X-ray emissivity)
- Produce FITS images for comparison with X-ray / optical observations
- Do **NOT** use for pure spectral fitting (use `sherpa` skill) or
  dust continuum post-processing (use `radmc3d` skill)

## Procedure

1. Collect parameters from the user.
   Read `references/parameters.md` for the full parameter table.

2. Call the run script:
   ```bash
   python ~/.agents/skills/yt/scripts/run_yt_analysis.py \
       --snap data/snapshots/snap_144.hdf5 \
       --analysis projection \
       --field gas_temperature \
       --center most_massive_halo \
       --width_mpc 10 \
       --out results/maps/z0_Tgas_projection.fits
   ```
   Or via `--json`:
   ```bash
   python ~/.agents/skills/yt/scripts/run_yt_analysis.py \
       --json '{"snap": "data/snapshots/snap_144.hdf5",
                "analysis": "projection",
                "field": "gas_temperature",
                "center": "most_massive_halo",
                "width_mpc": 10,
                "out": "results/maps/z0_Tgas_projection.fits"}'
   ```

3. Parse the last line: `SUCCESS: output=<path>` or `ERROR: <msg>`.

## Key yt operations

```python
import yt

# Load snapshot (auto-detects GADGET HDF5 / AREPO / PLUTO AMR / etc.)
ds = yt.load("data/snapshots/snap_144.hdf5")

# Cosmological info
print(ds.current_redshift, ds.hubble_constant, ds.omega_matter)

# Sphere around most massive halo
center = ds.find_max(("gas", "density"))[1]
sp = ds.sphere(center, (5, "Mpc"))

# Radial profile (density, temperature, entropy vs. radius)
prof = yt.create_profile(sp,
    ("index", "radius"),
    [("gas", "density"), ("gas", "temperature")],
    weight_field=("gas", "mass"))

# 2D projection
p = yt.ProjectionPlot(ds, "z", ("gas", "temperature"),
                      center=center, width=(10, "Mpc"),
                      weight_field=("gas", "mass"))
p.set_cmap("temperature", "RdBu_r")
p.save("plots/cosmo/z0_Tgas.pdf")

# FITS image for X-ray comparison
from yt.utilities.fits_image import FITSImageData
fi = FITSImageData(p.frb, fields=[("gas", "temperature")])
fi.writeto("results/maps/z0_Tgas.fits", overwrite=False)
```

## Custom fields

```python
# X-ray emissivity (0.5–7 keV band, approximate)
def xray_emissivity(field, data):
    n_e = data["gas", "number_density"]
    T = data["gas", "temperature"]
    # bremsstrahlung approximation: ε ∝ n² T^0.5
    import astropy.units as u
    return (n_e**2 * T**0.5).in_cgs()

ds.add_field(("gas", "xray_emissivity"), function=xray_emissivity,
             units="cm**-6 * K**0.5", sampling_type="cell")
```

## GADGET / Magneticum unit system

| Quantity | Code unit | Conversion |
|---|---|---|
| Length | kpc/h | `× h⁻¹ kpc → kpc` |
| Mass | 10¹⁰ M_sun/h | `× h⁻¹ × 10¹⁰ M_sun` |
| Velocity | km/s (physical) | direct |
| Temperature | K (already physical in HDF5) | direct |
| Density | 10¹⁰ M_sun h² kpc⁻³ | convert via yt |

yt handles these automatically for GADGET HDF5 datasets.
Always verify with `ds.length_unit`, `ds.mass_unit`, `ds.time_unit`.

## Parameters

> Full table with types, defaults, and constraints: [`references/parameters.md`](references/parameters.md)

**Key parameters:**
`snap` · `analysis` (`projection | slice | profile | phase | halo`) ·
`field` · `center` (`most_massive_halo | [x,y,z] | max_density`) ·
`width_mpc` · `axis` (`x | y | z`) · `weight_field` · `out`

## Sanity checks

- `ds.current_redshift` matches expected snapshot redshift (from `AGENTS.md`).
- ICM temperatures: 0.3–15 keV (3.5×10⁶ – 1.7×10⁸ K) for clusters.
- Gas density peak: ~10⁻²⁸ – 10⁻²⁵ g cm⁻³ in ICM.
- Warn if projection pixel count < 256² (low-resolution map).

## Mandatory workflow

For every yt analysis task, follow this sequence:

1. **Confirm** the snapshot path and check `ds.current_redshift` matches the expected value from `AGENTS.md`.
2. **Read `references/parameters.md`** to verify field names and analysis options.
3. **Run sanity checks** after loading: temperature range, density peak, projection pixel count.
4. **Save** all outputs to `results/maps/` (FITS) and `plots/` (PDF/PNG).
5. **Document** the snapshot redshift and field used in the output filename.

---

## Iron rules

- Always verify `ds.current_redshift` before analysis — never assume the snapshot index maps to a redshift.
- ICM temperatures outside 0.3–15 keV must be flagged as a warning before reporting results.
- Never use `yt` for pure spectral fitting — use the `sherpa` skill instead.
- Do not trigger this skill for pure particle catalogues (use `h5py` directly) or custom binary formats (use `numpy.fromfile`).
- Save FITS images to `results/maps/`; never write to `data/` raw directories.

---

## References

- Turk et al. 2011, ApJS 192 9 — 2011ApJS..192....9T
- Dolag et al. 2009 (Magneticum overview) — verify bibcode via ADS
