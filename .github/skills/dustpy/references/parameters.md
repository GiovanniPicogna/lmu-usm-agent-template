# DustPy Skill — Full Parameter Reference

Called by `scripts/run_dustpy.py`. All parameters are optional; missing
parameters take the script default.

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `alpha_viscosity` | float | 1e-3 | [1e-6, 1e-1] | Turbulence alpha |
| `disk_mass_msun` | float | 0.05 | (0, 1] | In solar masses |
| `stellar_mass_msun` | float | 1.0 | (0, 100] | In solar masses |
| `stellar_luminosity_lsun` | float | 1.0 | (0, 1e6] | In solar luminosities |
| `dust_to_gas_ratio` | float | 0.01 | (0, 0.5] | Initial dust-to-gas mass ratio |
| `r_in_au` | float | 1.0 | > 0 | Inner grid edge (au) |
| `r_out_au` | float | 300.0 | > r_in_au | Outer grid edge (au) |
| `N_r` | int | 100 | [10, 500] | Radial grid cells |
| `t_end_yr` | float | 1e6 | > 0 | Simulation end time (yr); auto-set to `snapshot_times_yr.max()` when that array is given |
| `fragmentation_velocity_ms` | float | 10.0 | (0, 100] | Fragmentation threshold (m/s) |
| `N_snapshots` | int | 100 | [10, 1000] | Evenly-spaced snapshots; ignored when `snapshot_times_yr` is set |
| `snapshot_times_yr` | `np.ndarray` (1-D, float64) | None | all > 0 | Custom snapshot schedule in years; validated via `NDArrayAdapter(ndim=1, dtype="float64", gt=0)` from **scientific-pydantic**; pass as JSON list `[1e4, 1e5, 1e6]` |
| `output_dir` | str | `"dustpy_out"` | — | Output directory (created if absent) |
