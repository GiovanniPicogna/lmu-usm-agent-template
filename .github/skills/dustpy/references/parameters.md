# DustPy Skill — Full Parameter Reference

Called by `scripts/run_dustpy.py`. All parameters are optional; missing
parameters take the script default.

All quantities are in CGS internally; the table below uses human-friendly units
matching the CLI flags and JSON keys.

## Disk / star parameters

| Name | Type | Default | Constraint | Maps to `sim.ini` | Notes |
|---|---|---|---|---|---|
| `alpha_viscosity` | float | 1e-3 | [1e-6, 1e-1] | `gas.alpha` | Shakura-Sunyaev turbulent alpha |
| `disk_mass_msun` | float | 0.05 | (0, 1] | `gas.Mdisk` | Initial gas disk mass (M☉) |
| `gas_sigma_exp` | float | -1.0 | [-3, 0] | `gas.SigmaExp` | Power-law exponent of Lynden-Bell & Pringle (1974) profile |
| `gas_sigma_rc_au` | float | 60.0 | > 0 | `gas.SigmaRc` | Critical cut-off radius of gas profile (AU) |
| `stellar_mass_msun` | float | 1.0 | (0, 100] | `star.M` | In solar masses |
| `stellar_radius_rsun` | float | 2.0 | (0, 1000] | `star.R` | In solar radii; controls stellar luminosity via `L = 4πR²σT⁴` |
| `stellar_temperature_K` | float | 5772.0 | (100, 1e6] | `star.T` | Effective surface temperature (K); also sets luminosity |

## Dust parameters

| Name | Type | Default | Constraint | Maps to `sim.ini` | Notes |
|---|---|---|---|---|---|
| `dust_to_gas_ratio` | float | 0.01 | (0, 0.5] | `dust.d2gRatio` | Initial vertically integrated dust-to-gas mass ratio |
| `fragmentation_velocity_ms` | float | 10.0 | (0, 100] | `dust.vFrag` | Collision fragmentation threshold (m/s); DustPy default is 1 m/s (100 cm/s) |
| `monomer_density_gcc` | float | 1.67 | (0, 10] | `dust.rhoMonomer` | Monomer bulk density (g cm⁻³); use ~1.0 for icy grains, ~3.5 for silicates |

## Grid parameters

| Name | Type | Default | Constraint | Maps to `sim.ini` | Notes |
|---|---|---|---|---|---|
| `r_in_au` | float | 1.0 | > 0 | `grid.rmin` | Inner radial grid boundary (AU) |
| `r_out_au` | float | 300.0 | > r_in_au | `grid.rmax` | Outer radial grid boundary (AU) |
| `N_r` | int | 100 | [10, 500] | `grid.Nr` | Number of radial grid cells |
| `Nmbpd` | int | 7 | [7, 20] | `grid.Nmbpd` | Mass bins per decade; **must be ≥ 7** (Drążkowska+ 2014); strong performance impact |

## Time / output parameters

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `t_end_yr` | float | 1e6 | > 0 | Simulation end time (yr); auto-set to `snapshot_times_yr.max()` when that array is given |
| `N_snapshots` | int | 100 | [10, 1000] | Number of log-spaced snapshots; ignored when `snapshot_times_yr` is set |
| `snapshot_times_yr` | `np.ndarray` (1-D, float64) | None | all > 0 | Custom snapshot schedule (yr); validated via `NDArrayAdapter(ndim=1, dtype="float64", gt=0)` from **scientific-pydantic**; pass as JSON list `[1e4, 1e5, 1e6]` |
| `output_dir` | str | `"dustpy_out"` | — | Output directory (created if absent); HDF5 files named `data0000.hdf5`, `data0001.hdf5`, … |
