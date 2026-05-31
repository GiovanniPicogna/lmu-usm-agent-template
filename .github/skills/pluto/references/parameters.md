# PLUTO Skill — Full Parameter Reference
# Based on PLUTO v4.4-patch3  •  See SKILL.md for routing and physics context

---

## File map

| File | Role |
|------|------|
| `SKILL.md` | Routing, physics context, safety rules, quick-ref |
| `parameters.md` | **This file** — full parameter tables |
| `examples.md` | Ready-to-run workflows |
| `compile_pluto.py` | Compile script |
| `run_pluto.py` | Run + patch script |
| `plot_pluto.py` | Post-run plotting script |
| `physics_config.md` | Written by compile script; records compile-time settings |

---

## Compile parameters (`PLUTOCompileParams`)

Called by `compile_pluto.py`.

### Location & toolchain

| Name | Type | Default | Constraint | Notes |
|------|------|---------|------------|-------|
| `run_dir` | str | **required** | must exist | PLUTO problem directory |
| `pluto_dir` | str | `$PLUTO_DIR` | must exist | PLUTO source tree root |
| `config_num` | int | None | 1–99 | Copies `definitions_N.h` → `definitions.h` and `pluto_N.ini` → `pluto.ini`; tries `_01` then `_1` padding |
| `arch` | str | auto | — | `.defs` token, e.g. `Linux.gcc.defs`, `Darwin.mpicc.defs` |
| `make_jobs` | int | 4 | [1,64] | `make -jN` parallelism |
| `force_compile` | bool | false | — | Rebuild even if `./pluto` exists |
| `setup_timeout` | int | 120 | [10,600] | Timeout (s) for `setup.py` subprocess |
| `make_timeout` | int | 600 | [30,3600] | Timeout (s) for `make` subprocess |

### Build configuration

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `parallel` | bool | false | Prefer `mpicc.defs`; sets `PARALLEL=TRUE`. Binary still named `./pluto`. |
| `hdf5` | bool | false | Prefer HDF5-enabled `.defs`; required for `.dbl.h5` / `.flt.h5` output |

### Module flags (passed to setup.py)

| Name | Flag | Default | Incompatible with |
|------|------|---------|------------------|
| `with_sb` | `--with-sb` | false | `with_fd` |
| `with_fargo` | `--with-fargo` | false | `with_chombo` |
| `with_fd` | `--with-fd` | false | `with_sb`, `with_chombo` |
| `with_chombo` | `--with-chombo` | false | `with_fd`, `with_sb`, `with_fargo` |
| `chombo_mpi` | `--with-chombo: MPI=TRUE` | false | same; implies `parallel=true`; requires g++ + gfortran |
| `with_cr_transport` | `--with-cr_transport` | false | — |

`--with-chombo` must be the **last** flag in the setup.py argv (setup.py `break`s on it).

---

## Run parameters (`PLUTOParams`)

Called by `run_pluto.py`.

### Location

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `run_dir` | str | **required** | Must contain `./pluto` binary and `pluto.ini` |
| `output_dir` | str | `run_dir` | Snapshot destination; patches `output_dir` in `[Static Grid Output]` |

### Time control  →  patches `[Time]`

| Name | Type | Default | Constraint | Notes |
|------|------|---------|------------|-------|
| `tstop` | float | keep | > 0 | End time. **Mutually exclusive** with `checkpoint_times`. |
| `checkpoint_times` | list[float] | None | all > 0, ascending | Staged-run schedule; PLUTO restarted at each value. **Mutually exclusive** with `tstop`. |
| `cfl` | float | keep | [0.1, 0.9] | Courant number. Safe default: 0.3–0.4. |
| `cfl_max_var` | float | keep | > 1.0 | Max dt^n / dt^{n-1} growth ratio. PLUTO default: 1.1. |
| `first_dt` | float | keep | > 0 | Initial timestep. Typical: 1e-6 to 1e-3. |

### Solver  →  patches `[Solver]`

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `solver` | str | keep | Must be valid for compiled PHYSICS. See SKILL.md §3.2. |

### User parameters  →  patches `[Parameters]`

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `parameters` | dict | `{}` | Keys from `init.c`; count must match `USER_DEF_PARAMETERS` in `definitions.h` |

### Runtime flags  →  `./pluto` command line

| Name | Type | Default | PLUTO flag | Notes |
|------|------|---------|-----------|-------|
| `pluto_bin` | str | `"./pluto"` | — | Always `./pluto`; no `pluto_mpi` exists |
| `ini_file` | str | None | `-i fname` | Alternative ini file |
| `restart` | int | None | `-restart N` | Read `.dbl` files. Exclusive with `h5restart`, `frestart`. |
| `h5restart` | int | None | `-h5restart N` | Read `.dbl.h5` files. |
| `frestart` | int | None | `-frestart N` | Fluid-only restart; suppress particle restart. |
| `maxsteps` | int | None | `-maxsteps N` | Stop after N steps. |
| `xres` | int | None | `-xres N` | Override x1 resolution; aspect ratio preserved. |
| `no_write` | bool | false | `-no-write` | Suppress all disk output. |

### MPI

| Name | Type | Default | Constraint | Notes |
|------|------|---------|------------|-------|
| `n_procs` | int | 1 | [1,512] | `mpirun -np N ./pluto` |
| `decomp` | list[int] | None | product = `n_procs` | `-dec n1 [n2] [n3]`; NOT `-decomp` |

### Output  →  patches `[Static Grid Output]`

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `log_dir` | str | None | Directory for `pluto.N.log` parallel log files |

### Compile integration

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `config_num` | int | None | Config variant for auto-compile |
| `auto_compile` | bool | true | Compile if `./pluto` missing |
| `force_compile` | bool | false | Force recompile before running |

### Background & monitoring

| Name | Type | Default | Constraint | Notes |
|------|------|---------|------------|-------|
| `background` | bool | false | — | Launch and return; writes PID + log |
| `monitor` | bool | false | — | Poll snapshots; log t, dt, nstep, ρ |
| `watch_interval` | float | 20.0 | [1,3600] | Poll cadence (seconds) |
| `plot_on_the_fly` | bool | false | — | Render plots as snapshots appear (calls `plot_pluto.py`) |
| `plot_interval` | float | 30.0 | [1,3600] | Min seconds between renders |
| `plot_output_dir` | str | `<output_dir>/live_plots` | — | Plot destination |
| `quiver_subsample` | int | 8 | [1,128] | Velocity quiver downsampling |

---

## Plot parameters (`PLUTOPlotParams`)

Called by `plot_pluto.py`.
Requires: `pyPLUTO` v4.4 (bundled in `$PLUTO_DIR/Tools/pyPLUTO/`).
Load data: `import pyPLUTO.pload as ppl; D = ppl.pload(N, w_dir=..., datatype=...)`

### Input

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `run_dir` | str | **required** | Must contain `dbl.out` and snapshot files |
| `snap` | int or list[int] or `"last"` or `"all"` | `"last"` | Snapshot(s) to plot; `"last"` uses `pyPLUTO.nlast_info()` |
| `datatype` | str | `"dbl"` | `"dbl"`, `"flt"`, `"dbl.h5"`, `"flt.h5"`, `"vtk"`, `"hdf5"` (AMR) |
| `physics_config` | str | `physics_config.md` | Written by compile script; auto-loads GEOMETRY and units |

### Variables

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `variables` | list[str] | `["rho"]` | Any pyPLUTO attribute: `rho`, `vx1`, `vx2`, `vx3`, `prs`, `Bx1`, `Bx2`, `Bx3`, `tr1`, … |
| `log_scale` | bool or list[bool] | `auto` | Apply log10; auto-detected for density/pressure |
| `velocity_overlay` | bool | false | Quiver of (vx1, vx2) projected to Cartesian in polar mode |
| `quiver_subsample` | int | 8 | [1,128] Velocity quiver downsampling factor |

### Geometry & projection

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `geometry` | str | from `physics_config.md` | `CARTESIAN`, `POLAR`, `SPHERICAL`, `CYLINDRICAL` |
| `polar_projection` | bool | auto | Project r-phi data to Cartesian x-y for disc view. Auto-enabled for POLAR. |
| `unit_length_cm` | float | from `physics_config.md` | `UNIT_LENGTH` in cm; sets axis labels (AU, pc, R☉ auto-detected) |
| `unit_density_cgs` | float | from `physics_config.md` | `UNIT_DENSITY` in g/cm³ |
| `unit_velocity_cgs` | float | from `physics_config.md` | `UNIT_VELOCITY` in cm/s |
| `physical_axes` | bool | true | Label axes in physical units; false = code-unit indices |

### Output

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `output_dir` | str | `run_dir/plots` | Plot destination |
| `format` | str | `"pdf"` | `"pdf"`, `"png"`, `"svg"` |
| `dpi` | int | 300 | [72, 1200] Resolution for raster formats |
| `colormap` | str | per-variable | `"viridis"` for density; `"RdBu_r"` for velocity; `"PuOr_r"` for B-field |
| `figsize` | list[float] | `[6, 5]` per panel | Figure size in inches |
| `show` | bool | false | Call `plt.show()` interactively (requires display) |

> **pyPLUTO v4.4 array layout**: `D.rho` has shape `(nx2, nx1)` — x2 is the first index.
> `plot_pluto.py` transposes internally; raw analysis code must account for this.

---

## pyPLUTO v4.4 API reference

```python
import pyPLUTO as pp            # top-level: nlast_info
import pyPLUTO.pload as ppl    # data loader class
import pyPLUTO.Image as img    # Image class for advanced plotting
import pyPLUTO.Tools as tl     # Tools class: congrid, gradient, etc.

# Last snapshot info
info = pp.nlast_info(w_dir="/path/")  # → {'nlast': N, 'time': t, 'dt': dt, 'Nstep': s}

# Load snapshot
D = ppl.pload(N, w_dir="/path/", datatype="dbl")
# D.rho, D.vx1, D.vx2, D.vx3, D.prs, D.Bx1 … — shape (nx2, nx1)
# D.x1, D.x2, D.x3  — 1-D cell-centre coords
# D.dx1, D.dx2, D.dx3 — cell widths
# D.SimTime           — simulation time
# D.NStep             — step number

# AMR at level 3 with zoom
D = ppl.pload(N, w_dir="/path/", datatype="hdf5", level=3,
              x1range=[0.5, 2.0], x2range=[0.4, 0.6])

# Image class (polar → Cartesian reproject)
I = img.Image()
I.pltSphData(D, w_dir="/path/", datatype="vtk", plvar="rho",
             logvar=True, rphi=True, x2cut=24)  # r-phi midplane slice

# Regrid arrays
T = tl.Tools()
newdims = (64, 64)
rho_c = T.congrid(D.rho, newdims, method="linear")
```

---

## Output descriptor format

`dbl.out` columns: `n  t  dt  nstep  [single_file]  [endian]  var1 var2 ...`

`n` = snapshot index used with `-restart N`.

For Chombo-AMR: checkpoints `chk.nnnn.hdf5`; plots `data.nnnn.hdf5`.
Restart from Chombo checkpoint: `-restart N` (reads `chk.nnnn.hdf5`).
