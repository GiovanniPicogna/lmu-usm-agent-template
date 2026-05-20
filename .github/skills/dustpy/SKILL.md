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

1. Collect parameters from the user. Read `references/parameters.md` for the full
   parameter table with types, defaults, and constraints. Any parameter not supplied
   takes the script default.
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

> Full table with types, defaults, and constraints: [`references/parameters.md`](references/parameters.md)

**Key parameters:** `alpha_viscosity` · `disk_mass_msun` · `t_end_yr` ·
`fragmentation_velocity_ms` · `snapshot_times_yr` (array) · `output_dir`

**Array-valued parameter:** `snapshot_times_yr` must be a JSON list:
`"snapshot_times_yr": [1e4, 1e5, 1e6]`

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
