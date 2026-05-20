---
name: dustpy
description: >
  Run DustPy simulations of radial dust evolution, coagulation, and fragmentation
  in protoplanetary disks. Use this skill to compute grain-size distributions,
  Stokes numbers, radial drift timescales, and final dust/gas mass fractions under
  varying turbulence, disk mass, stellar properties, or fragmentation thresholds.
  Trigger phrases: dustpy, dust evolution, grain growth, fragmentation barrier,
  Stokes number, dust-to-gas ratio, radial drift, coagulation, particle size
  distribution, maximum grain size, dust mass evolution.
argument-hint: "Physical parameters, e.g. 'alpha=1e-3, disk mass 0.05 Msun, run 1 Myr'"
---

# DustPy Skill

## When to Use

- Simulate the coupled radial and size evolution of dust in a protoplanetary disk
- Explore the effect of turbulence (`alpha`), disk mass, stellar mass/luminosity, or
  fragmentation velocity on the steady-state grain-size distribution
- Generate grain-size snapshots for direct comparison with (sub-)mm continuum observations
- Do **NOT** use this skill for gas-only / 2-D / 3-D hydrodynamics, photoevaporation,
  planet-disk interaction, or MHD — use the `simulation-agent` for those

## Procedure

1. Collect parameters from the user.  Any parameter not supplied takes the script default.
2. Call the run script, preferring the `--json` form for robustness:
   ```
   python ~/.agents/skills/dustpy/scripts/run_dustpy.py \
       --json '{"alpha_viscosity": 1e-3, "disk_mass_msun": 0.05, "t_end_yr": 1e6}'
   ```
   Individual flags are also accepted:
   ```
   python ~/.agents/skills/dustpy/scripts/run_dustpy.py \
       --alpha 1e-3 --disk-mass 0.05 --t-end 1e6
   ```
3. The script initialises a `dustpy.Simulation`, applies all parameters, runs to
   `t_end`, writes HDF5 snapshots to `output_dir`, and prints a plain-text summary.
4. Parse the summary (last line starts with `SUCCESS:` or `ERROR:`).
   On error, correct parameters and retry once; if still failing, report the traceback.

## Parameters

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `alpha_viscosity` | float | 1e-3 | [1e-6, 1e-1] | Turbulence alpha |
| `disk_mass_msun` | float | 0.05 | (0, 1] | In solar masses |
| `stellar_mass_msun` | float | 1.0 | (0, 100] | In solar masses |
| `stellar_luminosity_lsun` | float | 1.0 | (0, 1e6] | In solar luminosities |
| `dust_to_gas_ratio` | float | 0.01 | (0, 0.5] | Initial ratio |
| `r_in_au` | float | 1.0 | > 0 | Inner grid edge (au) |
| `r_out_au` | float | 300.0 | > r_in_au | Outer grid edge (au) |
| `N_r` | int | 100 | [10, 500] | Radial grid cells |
| `t_end_yr` | float | 1e6 | > 0 | Simulation end time (yr); auto-set to `snapshot_times_yr.max()` when array is given |
| `fragmentation_velocity_ms` | float | 10.0 | (0, 100] | Fragmentation threshold (m/s) |
| `N_snapshots` | int | 100 | [10, 1000] | Evenly-spaced snapshots (ignored when `snapshot_times_yr` is set) |
| `snapshot_times_yr` | `np.ndarray` (1-D) | None | all > 0 | Custom snapshot schedule in years; validated via `NDArrayAdapter(ndim=1, dtype="float64", gt=0)` from **scientific-pydantic**; pass as JSON list `[1e4, 1e5, 1e6]` |
| `output_dir` | str | `dustpy_out` | — | Output directory path |

## Output

On success the script prints:
```
SUCCESS: output_dir=<path>  t_end=<yr>yr  N_snaps=<n>
  final_gas_mass=<X>e-02 Msun  final_dust_mass=<X>e-04 Msun
  a_max_at_10au=<X>cm  a_max_at_100au=<X>cm
  wall_clock=<N>s
```

## Common Errors

| Message | Fix |
|---|---|
| `r_out_au must be > r_in_au` | Swap or increase `r_out_au` |
| `dustpy not found` | `pip install dustpy` in the active env |
| `scientific_pydantic not found` | `pip install scientific-pydantic` |
| `AttributeError: ini.star.L` | Old DustPy (<0.8); set `stellar_luminosity_lsun=None` to skip |
| `t.snapshots shape mismatch` | Reduce `N_snapshots` or increase `t_end_yr` |
