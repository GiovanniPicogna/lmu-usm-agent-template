# DustPy Parameters Reference

All parameters in `sim.ini` must be set **before** `sim.initialize()`.
All quantities are in **CGS units** unless a suffix states otherwise.

Table of contents:
1. [Stellar parameters — `sim.ini.star`](#1-stellar-parameters)
2. [Grid parameters — `sim.ini.grid`](#2-grid-parameters)
3. [Gas parameters — `sim.ini.gas`](#3-gas-parameters)
4. [Dust parameters — `sim.ini.dust`](#4-dust-parameters)
5. [Time / snapshot parameters — `sim.t`](#5-time--snapshot-parameters)
6. [Writer parameters — `sim.writer`](#6-writer-parameters)
7. [Cross-parameter constraints and interactions](#7-cross-parameter-constraints-and-interactions)

---

## 1. Stellar parameters

Namespace: `sim.ini.star`

| Parameter | Type | Default (CGS) | Default (physical) | Constraints | Notes |
|---|---|---|---|---|---|
| `M` | float | `1.9884e+33` g | 1 M☉ | > 0 | Sets dynamical timescales and Keplerian frequency throughout the disk |
| `R` | float | `1.3914e+11` cm | 2 R☉ | > 0 | Used in the default passively irradiated temperature profile; has no effect if `gas.T.updater` is replaced |
| `T` | float | `5772.0` K | 5772 K | > 0 | Effective temperature; enters the irradiation temperature profile together with `R`; has no effect if `gas.T.updater` is replaced |

Derived (read-only after `initialize()`):

| Field | Unit | Description |
|---|---|---|
| `sim.star.L` | erg/s | Bolometric luminosity, computed from `R` and `T` as L = 4πR²σT⁴ |

---

## 2. Grid parameters

Namespace: `sim.ini.grid`

| Parameter | Type | Default (CGS) | Default (physical) | Constraints | Notes |
|---|---|---|---|---|---|
| `Nr` | int | `100` | — | ≥ 5 (practical minimum) | Number of radial grid cells. Runtime scales roughly as O(Nr). Typical production runs: 100–300. |
| `rmin` | float | `1.4960e+13` cm | 1 AU | > 0, < `rmax` | Inner radial boundary. Must not be 0 (Keplerian singularity). |
| `rmax` | float | `1.4960e+16` cm | 1000 AU | > `rmin` | Outer radial boundary. |
| `Nmbpd` | int | `7` | — | **≥ 7** | Mass bins per decade. **Hard minimum of 7** — lower values produce inaccurate coagulation results (Drążkowska et al. 2014). Increasing to 10 roughly doubles runtime. |
| `mmin` | float | `1e-12` g | ~0.6 nm grain | > 0, < `mmax` | Minimum particle mass on the mass grid. Corresponds to smallest monomer size. |
| `mmax` | float | `1e+05` g | ~46 cm boulder | > `mmin` | Maximum particle mass on the mass grid. Should be set above the expected fragmentation barrier. |

Derived (read-only after `initialize()`):

| Field | Shape | Unit | Description |
|---|---|---|---|
| `sim.grid.r` | `(Nr,)` | cm | Radial cell centres (log-spaced) |
| `sim.grid.ri` | `(Nr+1,)` | cm | Radial cell interfaces; can be set manually before `initialize()` for custom grids |
| `sim.grid.m` | `(Nm,)` | g | Mass grid (strictly log-spaced; never modify directly) |
| `sim.grid.Nm` | scalar | — | Total number of mass bins = `Nmbpd × log10(mmax/mmin)` + 1 |
| `sim.grid.A` | `(Nr,)` | cm² | Annulus area of each radial cell = 2π r Δr |
| `sim.grid.OmegaK` | `(Nr,)` | 1/s | Keplerian angular velocity |

**Custom radial grid:** Set `sim.grid.ri` (a plain `np.ndarray`) before calling
`sim.initialize()`. The `r` centres are computed as geometric means of adjacent
interfaces. See `customisation.md §2` for the grid refinement helper.

---

## 3. Gas parameters

Namespace: `sim.ini.gas`

| Parameter | Type | Default (CGS) | Default (physical) | Constraints | Notes |
|---|---|---|---|---|---|
| `alpha` | float | `1e-3` | — | > 0, ≤ 0.1 | Shakura–Sunyaev turbulent viscosity parameter. Enters kinematic viscosity ν = α c_s H_p. Also used as the default for `dust.delta.rad`, `dust.delta.turb`, `dust.delta.vert` unless those are set independently. |
| `Mdisk` | float | `9.942e+31` g | 0.05 M☉ | > 0 | Initial gas disk mass. Normalises the Lynden-Bell & Pringle (1974) surface density profile. |
| `mu` | float | `3.847e-24` g | 2.3 m_proton | > 0 | Mean molecular weight of the gas. Affects sound speed and hence the pressure scale height. Default is 2.3 proton masses, appropriate for a H₂/He mixture. |
| `SigmaExp` | float | `-1.0` | — | any | Power-law index of the initial Σ_gas profile (Lynden-Bell & Pringle 1974). Typical values: −0.5 to −1.5. |
| `SigmaRc` | float | `8.976e+14` cm | 30 AU | > 0 | Critical cut-off radius of the self-similar surface density profile. Controls where the exponential taper begins. |

Derived gas fields (read-only after `initialize()`):

| Field | Shape | Unit | Description |
|---|---|---|---|
| `sim.gas.Sigma` | `(Nr,)` | g/cm² | Gas surface density (evolved quantity) |
| `sim.gas.SigmaFloor` | `(Nr,)` | g/cm² | Floor value (prevents Σ → 0 numerically) |
| `sim.gas.T` | `(Nr,)` | K | Midplane temperature (passively irradiated default) |
| `sim.gas.cs` | `(Nr,)` | cm/s | Isothermal sound speed |
| `sim.gas.Hp` | `(Nr,)` | cm | Pressure scale height |
| `sim.gas.nu` | `(Nr,)` | cm²/s | Kinematic viscosity |
| `sim.gas.eta` | `(Nr,)` | — | Pressure gradient parameter (sub-Keplerian measure) |
| `sim.gas.rho` | `(Nr,)` | g/cm³ | Midplane volume mass density |
| `sim.gas.alpha` | `(Nr,)` | — | Turbulent α (spatially uniform by default, updatable) |
| `sim.gas.v.rad` | `(Nr,)` | cm/s | Radial gas velocity (includes backreaction) |
| `sim.gas.v.visc` | `(Nr,)` | cm/s | Viscous accretion velocity |

---

## 4. Dust parameters

Namespace: `sim.ini.dust`

### 4a. Initial conditions

| Parameter | Type | Default (CGS) | Default (physical) | Constraints | Notes |
|---|---|---|---|---|---|
| `d2gRatio` | float | `0.01` | — | > 0, < 1 | Initial dust-to-gas mass ratio. Applied uniformly across the disk to set initial `dust.Sigma`. |
| `aIniMax` | float | `1e-4` cm | 1 µm | > 0 | Maximum grain size filled at t=0. Grains are initialised with an MRN-like size distribution (`distExp`) up to this size. |
| `distExp` | float | `-3.5` | −7/2 (MRN) | any | Power-law index of the initial grain size distribution n(a) ∝ a^distExp. Default is the Mathis, Rumpl & Nordsieck (1977) ISM distribution. |

### 4b. Collision physics

| Parameter | Type | Default (CGS) | Default (physical) | Constraints | Notes |
|---|---|---|---|---|---|
| `vFrag` | float | `100.0` cm/s | 1 m/s | > 0 | Fragmentation velocity threshold. Collisions above this speed fragment; below it they stick. Typical values: 100 cm/s (silicates) to 1000 cm/s (icy grains). Can be made spatially varying via `dust.v.frag.updater` (see ice lines example). |
| `rhoMonomer` | float | `1.67` g/cm³ | — | > 0 | Bulk (solid) density of a single monomer grain. Default is appropriate for silicate grains. Use ~1.0 g/cm³ for icy aggregates. Affects Stokes number via the particle mass–size relation. |
| `erosionMassRatio` | float | `10.0` | — | > 1 | Mass ratio threshold between full fragmentation and erosion. If m_large/m_small > this value, only the small particle fragments (erosion regime); otherwise both fragment fully. Must be set before `initialize()`. |
| `excavatedMass` | float | `1.0` | — | > 0 | In an erosive collision, the mass chipped off the larger particle in units of the smaller particle's mass. Default: 1 (equal-mass chip-off). |
| `fragmentDistribution` | float | `-1.8333` | −11/6 | < −1 | Power-law index γ of the fragment mass distribution n(m) dm ∝ m^γ dm. Default from Dohnanyi (1969). More negative = more small fragments. Must be < −1 for normalisability. |

### 4c. Particles allowed to drift initially

| Parameter | Type | Default | Constraints | Notes |
|---|---|---|---|---|
| `allowDriftingParticles` | bool | `False` | — | If `False`, particles in the outer disk with St large enough to drift inward from the start are removed from the initial condition. This prevents an initial particle wave propagating inward. Set to `True` only if you specifically want to study the initial drift wave. |

### 4d. Key derived dust fields (read-only after `initialize()`)

| Field | Shape | Unit | Description |
|---|---|---|---|
| `sim.dust.Sigma` | `(Nr, Nm)` | g/cm² | Dust surface density per mass bin — the primary evolved quantity |
| `sim.dust.SigmaFloor` | `(Nr, Nm)` | g/cm² | Floor value per bin |
| `sim.dust.a` | `(Nr, Nm)` | cm | Particle size per mass bin |
| `sim.dust.rho` | `(Nr, Nm)` | g/cm³ | Midplane volume mass density per mass bin |
| `sim.dust.rhos` | `(Nr, Nm)` | g/cm³ | Solid-state (bulk) density per mass bin |
| `sim.dust.St` | `(Nr, Nm)` | — | Stokes number per mass bin |
| `sim.dust.eps` | `(Nr,)` | — | Total dust-to-gas ratio (integrated over mass bins) |
| `sim.dust.H` | `(Nr, Nm)` | cm | Dust scale height per mass bin |
| `sim.dust.D` | `(Nr, Nm)` | cm²/s | Dust diffusivity per mass bin |
| `sim.dust.v.rad` | `(Nr, Nm)` | cm/s | Radial drift velocity per mass bin |
| `sim.dust.v.frag` | `(Nr,)` | cm/s | Fragmentation velocity (spatially varying if ice lines set) |
| `sim.dust.v.driftmax` | `(Nr,)` | cm/s | Maximum drift velocity (diagnostic) |
| `sim.dust.p.stick` | `(Nr, Nm, Nm)` | — | Sticking probability matrix |
| `sim.dust.p.frag` | `(Nr, Nm, Nm)` | — | Fragmentation probability matrix |

### 4e. Mixing / diffusion parameters

These are set directly on the simulation object (not via `sim.ini`), either
before or after `initialize()`:

| Field | Default | Notes |
|---|---|---|
| `sim.dust.delta.rad` | = `gas.alpha` | Radial diffusion parameter. Set independently to decouple radial diffusion strength from viscosity. |
| `sim.dust.delta.turb` | = `gas.alpha` | Turbulent relative velocity parameter. Affects grain–grain relative velocities and hence the coagulation/fragmentation boundary. |
| `sim.dust.delta.vert` | = `gas.alpha` | Vertical settling parameter. Controls the dust scale height H_dust = H_gas / sqrt(1 + St/delta_vert). |

---

## 5. Time / snapshot parameters

Set via `sim.t.snapshots` — a 1-D array of times in **seconds** at which
DustPy writes HDF5 output files. The first element must be the initial time
`sim.t` (which is `0.0` before `initialize()`).

| Attribute | Type | Default | Notes |
|---|---|---|---|
| `sim.t.snapshots` | `np.ndarray` | 0 + 10 snaps/decade from 1 kyr to 100 kyr | Array of absolute output times in **seconds**. Use `np.geomspace(...) * c.year` for logarithmically spaced snapshots. |

**Standard snapshot construction:**
```python
import numpy as np
from dustpy import constants as c

# 10 snapshots per decade from 1 kyr to 1 Myr (inclusive endpoints)
sim.t.snapshots = np.hstack([
    sim.t,
    np.geomspace(1e3, 1e6, num=31) * c.year   # 31 points = 10/decade over 3 decades
])
```

**Computing `num` from `snaps_per_decade`:**
```python
n_decades = np.log10(t_end_yr / t_start_yr)
num = int(snaps_per_decade * n_decades) + 1
```

---

## 6. Writer parameters

Set via `sim.writer` after creating the `Simulation` object.

| Attribute | Type | Default | Constraints | Notes |
|---|---|---|---|---|
| `sim.writer.datadir` | str | `"data"` | Valid path | Output directory for HDF5 files and dump file. Created automatically if absent. |
| `sim.writer.overwrite` | bool | `False` | — | If `False`, raises an error if `datadir` already contains output files. Set to `True` only after explicit user confirmation — overwriting destroys prior results. |

Output files written:
- `data{N:04d}.hdf5` — full simulation state at each snapshot time
- `frame.dmp` — binary dump file updated at each snapshot; used by `sim.load()` to resume

---

## 7. Cross-parameter constraints and interactions

**`Nmbpd` ≥ 7 is a hard requirement.** Lower values cause the mass redistribution
in sticking events to lose accuracy because the two adjacent mass bins that receive
the merged particle mass are too far apart. Results can differ by orders of magnitude
from the correct solution. Reference: Drążkowska et al. (2014).

**`mmax` should exceed the expected fragmentation barrier.** The fragmentation-limited
grain size is approximately:
```
a_frag ≈ (2/3π) × (Σ_gas / (ρ_s π)) × (v_frag / c_s)² × (1/α)
```
If `mmax` is too small, the largest mass bin acts as an artificial sink.
A safe choice is `mmax = 1e5` g (default) for typical disk conditions.

**`alpha` is shared across gas viscosity and dust diffusion by default.**
All three `dust.delta.*` parameters default to `gas.alpha`. If you want to
decouple them (e.g., turbulence-driven diffusion vs. laminar drift), set them
explicitly after `initialize()`:
```python
sim.initialize()
sim.dust.delta.rad[:]  = 1e-4   # weaker radial diffusion
sim.dust.delta.turb[:] = 1e-4   # weaker turbulent relative velocities
# delta.vert stays at alpha — settling unchanged
```

**`vFrag` and `rhoMonomer` together set the fragmentation barrier location.**
Higher `vFrag` or lower `rhoMonomer` push the barrier to larger grain sizes.
The fragmentation-limited Stokes number scales as St_frag ∝ v_frag² / (α c_s²).

**`erosionMassRatio` must be set before `initialize()`** because it enters the
pre-computed coagulation kernel matrices (`sim.dust.coagulation`). Changing it
after `initialize()` has no effect without recomputing the coagulation parameters.

**`allowDriftingParticles = False` (default) removes particles** in the outer disk
that would drift inward on a timescale shorter than one orbital period at the
start of the simulation. This avoids an unphysical initial transient. Only set
to `True` if you are specifically studying the initial drift wave.

**`SigmaRc` interacts with `rmin` and `rmax`.** If `SigmaRc` is set well inside
`rmin`, the disk mass is concentrated at small radii and the outer grid is
essentially empty. If `SigmaRc` >> `rmax`, the exponential taper has no effect
and the profile is a pure power law across the grid. A good rule of thumb:
`rmin` ≲ 0.1 × `SigmaRc` ≲ `rmax`.

**`t_start_yr` for snapshots should be ≥ 1 orbit at `rmin`.** The orbital period
at the inner boundary is P ≈ 2π / Ω_K(rmin). Writing output before one orbit
has elapsed is usually unnecessary and may capture the initialisation transient.
