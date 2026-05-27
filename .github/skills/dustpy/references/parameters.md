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
| `mu_g` | float | 3.847e-24 | > 0 | `gas.mu` | Mean molecular weight of the gas (g); default ≈ 2.3 m_proton (molecular H₂) |
| `stellar_mass_msun` | float | 1.0 | (0, 100] | `star.M` | In solar masses |
| `stellar_radius_rsun` | float | 2.0 | (0, 1000] | `star.R` | In solar radii; controls stellar luminosity via `L = 4πR²σT⁴` |
| `stellar_temperature_K` | float | 5772.0 | (100, 1e6] | `star.T` | Effective surface temperature (K); also sets luminosity |

## Dust parameters

| Name | Type | Default | Constraint | Maps to `sim.ini` | Notes |
|---|---|---|---|---|---|
| `dust_to_gas_ratio` | float | 0.01 | (0, 0.5] | `dust.d2gRatio` | Initial vertically integrated dust-to-gas mass ratio |
| `fragmentation_velocity_ms` | float | 10.0 | (0, 100] | `dust.vFrag` | Collision fragmentation threshold (m/s); DustPy default is 1 m/s (= 100 cm/s) |
| `monomer_density_gcc` | float | 1.67 | (0, 10] | `dust.rhoMonomer` | Monomer bulk density (g cm⁻³); use ~1.0 for icy grains, ~3.5 for silicates |
| `a_ini_max_cm` | float | 1e-4 | > 0 | `dust.aIniMax` | Maximum initial grain size (cm; = 1 µm); initial distribution set up to this size using `dist_exp` power law |
| `allow_drifting_particles` | bool | False | — | `dust.allowDriftingParticles` | If `True`, initially super-Stokes drifting particles in outer disk are kept; `False` (default) removes them |
| `dist_exp` | float | -3.5 | — | `dust.distExp` | Initial grain-size distribution exponent n(a) ∝ a^distExp; default −3.5 is the MRN distribution (Mathis+ 1977) |
| `erosion_mass_ratio` | float | 10.0 | > 0 | `dust.erosionMassRatio` | Mass ratio threshold: collisions below this ratio produce full fragmentation; above it produce erosion |
| `excavated_mass` | float | 1.0 | > 0 | `dust.excavatedMass` | Mass chipped off larger particle in an erosive collision, in units of the smaller particle mass |
| `fragment_distribution` | float | −11/6 ≈ −1.833 | — | `dust.fragmentDistribution` | Fragment mass distribution exponent n(m)dm ∝ m^fragment_distribution dm; Dohnanyi (1969) default |

## Grid parameters

| Name | Type | Default | Constraint | Maps to `sim.ini` | Notes |
|---|---|---|---|---|---|
| `r_in_au` | float | 1.0 | > 0 | `grid.rmin` | Inner radial grid boundary (AU) |
| `r_out_au` | float | 300.0 | > r_in_au | `grid.rmax` | Outer radial grid boundary (AU); DustPy default is 1000 AU |
| `N_r` | int | 100 | [10, 500] | `grid.Nr` | Number of radial grid cells |
| `Nmbpd` | int | 7 | [7, 20] | `grid.Nmbpd` | Mass bins per decade; **must be ≥ 7** (Drążkowska+ 2014); strong performance impact |
| `mmin_g` | float | 1e-12 | > 0 | `grid.mmin` | Minimum particle mass (g); lower end of the logarithmic mass grid |
| `mmax_g` | float | 1e5 | > 0 | `grid.mmax` | Maximum particle mass (g); upper end of the logarithmic mass grid |

## Time / output parameters

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `t_end_yr` | float | 1e6 | > 0 | Simulation end time (yr); auto-set to `snapshot_times_yr.max()` when that array is given |
| `N_snapshots` | int | 100 | [10, 1000] | Number of log-spaced snapshots; ignored when `snapshot_times_yr` is set |
| `snapshot_times_yr` | `np.ndarray` (1-D, float64) | None | all > 0 | Custom snapshot schedule (yr); validated via `NDArrayAdapter(ndim=1, dtype="float64", gt=0)` from **scientific-pydantic**; pass as JSON list `[1e4, 1e5, 1e6]` |
| `output_dir` | str | `"dustpy_out"` | — | Output directory (created if absent); HDF5 files named `data0000.hdf5`, `data0001.hdf5`, … || `overwrite` | bool | False | — | If `True`, existing HDF5 files in `output_dir` are overwritten (`sim.writer.overwrite`) |

## Post-initialization fields

These are applied **after** `sim.initialize()` and must not be placed in `sim.ini`.
Set to `None` (default) to leave the DustPy default in place.

| Name | Type | Default | Constraint | Modifies | Notes |
|---|---|---|---|---|---|
| `delta_rad` | float | None (= alpha) | > 0 | `sim.dust.delta.rad` | Radial dust diffusion coefficient; by default equals `alpha_viscosity` |
| `delta_turb` | float | None (= alpha) | > 0 | `sim.dust.delta.turb` | Turbulent collision velocity parameter; by default equals `alpha_viscosity` |
| `delta_vert` | float | None (= alpha) | > 0 | `sim.dust.delta.vert` | Vertical settling mixing parameter; by default equals `alpha_viscosity` |
| `cfl_factor` | float | 0.1 | (0, 1] | `sim.t.cfl` | CFL safety factor for the adaptive timestep; reduce to improve accuracy at the cost of speed |

> **Tip — decoupled mixing**: In a layered disk with dead zone you may want
> `delta_turb ≪ alpha_viscosity` (low turbulent stirring) while keeping
> `alpha_viscosity` large for gas viscosity. Set independently via `delta_turb`.

> **Advanced post-init customisation** (not exposed as JSON keys — set in a
> custom script after `sim.initialize()`):
> - `sim.dust.delta.*` arrays can be set to radially varying profiles
> - `sim.gas.S.ext` — external gas source terms (e.g. infall, photoevaporation)
> - `sim.gas.torque.Lambda` — specific angular momentum injection (planetary gaps)
> - `sim.dust.S.ext` — external dust sink/source terms (planetesimal formation)
> - `sim.dust.backreaction.{A,B}` — dust-on-gas backreaction (off by default: A=1, B=0)
