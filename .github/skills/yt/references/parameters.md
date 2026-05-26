# yt Analysis Parameters Reference

Full parameter table for `run_yt_analysis.py`.

---

## Required parameters

| Parameter | Type | Description |
|---|---|---|
| `snap` | `str` | Path to snapshot file or directory (HDF5, GADGET, PLUTO AMR, …) |
| `analysis` | `str` | Analysis type: `projection` \| `slice` \| `profile` \| `phase` \| `halo` |
| `out` | `str` | Output path (FITS, PDF, or JSON depending on analysis type) |

## Optional parameters — all analyses

| Parameter | Type | Default | Description |
|---|---|---|---|
| `field` | `str` | `"gas_temperature"` | Field to visualise or profile. Use yt canonical name: `gas_density`, `gas_temperature`, `gas_pressure`, `gas_entropy`, `gas_xray_emissivity` |
| `center` | `str \| list[float]` | `"max_density"` | Centre: `most_massive_halo` \| `max_density` \| `[x, y, z]` in code units |
| `cosmology_h` | `float` | read from snapshot | Hubble parameter h (overrides snapshot value if needed) |

## Projection / slice parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `axis` | `str` | `"z"` | Projection axis: `x` \| `y` \| `z` |
| `width_mpc` | `float` | `10.0` | Map half-width in Mpc (physical) |
| `weight_field` | `str` | `"gas_mass"` | Weight field for projection (use `null` for line-of-sight integral) |
| `resolution` | `int` | `512` | Image resolution in pixels per side |
| `colormap` | `str` | `"viridis"` | Matplotlib colormap (use `cividis` or `viridis` — never `jet`) |

## Profile parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `profile_fields` | `list[str]` | `["gas_density", "gas_temperature"]` | Fields to profile |
| `r_min_mpc` | `float` | `0.01` | Inner radius in Mpc |
| `r_max_mpc` | `float` | `5.0` | Outer radius in Mpc |
| `n_bins` | `int` | `64` | Number of radial bins |
| `weight_field` | `str` | `"gas_mass"` | Profile weight field |

## Phase diagram parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `x_field` | `str` | `"gas_density"` | Horizontal axis field |
| `y_field` | `str` | `"gas_temperature"` | Vertical axis field |
| `z_field` | `str` | `"gas_mass"` | Colour / weight field |
| `x_bins` | `int` | `128` | Bins on x-axis |
| `y_bins` | `int` | `128` | Bins on y-axis |

## Halo analysis parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `halo_id` | `int \| null` | `null` | Specific halo index (null → most massive) |
| `r_200_factor` | `float` | `1.0` | Analysis radius as multiple of R_200 |
| `halo_catalogue` | `str \| null` | `null` | Path to SUBFIND/AHF catalogue (optional) |

## Common field aliases

| User-friendly name | yt canonical tuple |
|---|---|
| `gas_temperature` | `("gas", "temperature")` |
| `gas_density` | `("gas", "density")` |
| `gas_pressure` | `("gas", "pressure")` |
| `gas_entropy` | `("gas", "entropy")` |
| `gas_mass` | `("gas", "mass")` |
| `stellar_mass` | `("stars", "particle_mass")` |
| `gas_metallicity` | `("gas", "metallicity")` |

## Constraints

- `resolution` ≥ 256 (warn if lower — map quality degrades)
- `width_mpc` > 0 and < box_size / 2
- `axis` must be `x`, `y`, or `z`
- For GADGET/Magneticum snapshots: yt 4.x reads `PartType0` (gas),
  `PartType1` (dark matter), `PartType4` (stars), `PartType5` (black holes)
- `colormap` must not be `jet` or `rainbow` (group standard)
