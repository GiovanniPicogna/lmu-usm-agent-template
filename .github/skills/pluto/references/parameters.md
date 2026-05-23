# PLUTO Skill — Full Parameter Reference
# Based on PLUTO v4.4-patch3 and compile_pluto_v4 / run_pluto_v4

---

## Compile parameters (`PLUTOCompileParams`)

Called by `scripts/compile_pluto.py`.

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `run_dir` | str | **required** | must exist | Path to PLUTO problem directory containing `definitions.h` (or numbered variants) |
| `pluto_dir` | str | `$PLUTO_DIR` | must exist | Path to PLUTO source tree |
| `config_num` | int | None | 1–99 | If given, copies `definitions_N.h` → `definitions.h` and `pluto_N.ini` → `pluto.ini`; tries zero-padded (`_01`) then bare (`_1`) |
| `arch` | str | auto-detected | — | `.defs` arch token from `$PLUTO_DIR/Config/`, e.g. `Darwin.gcc.defs`, `Linux.gcc.defs`, `Linux.mpicc.defs`. Auto-detected from `platform.system()` if omitted. |
| `make_jobs` | int | 4 | [1, 64] | Parallel `make -jN` jobs |
| `parallel` | bool | false | — | Prefer MPI `.defs` file (`Linux.mpicc.defs`); sets `PARALLEL=TRUE` via `CC=mpicc`. Binary is **still named `./pluto`** (never `pluto_mpi`). |
| `hdf5` | bool | false | — | Prefer HDF5-enabled `.defs` file. Required for `.dbl.h5` / `.flt.h5` output. |
| `force_compile` | bool | false | — | Force rebuild even if `./pluto` already exists |
| `setup_timeout` | int | 120 | [10, 600] | Timeout (s) for `setup.py` subprocess; increase for slow machines |
| `make_timeout` | int | 600 | [30, 3600] | Timeout (s) for `make` subprocess |
| `with_sb` | bool | false | XOR `with_fd` | `--with-sb` — shearing box module (§10.1) |
| `with_fargo` | bool | false | XOR `with_chombo` | `--with-fargo` — FARGO-MHD orbital advection (§10.2) |
| `with_fd` | bool | false | XOR `with_sb`, `with_chombo` | `--with-fd` — finite difference scheme (§10.4) |
| `with_chombo` | bool | false | XOR `with_fd`, `with_sb`, `with_fargo` | `--with-chombo` — AMR via Chombo library (Ch. 13). Requires g++ and gfortran. |
| `chombo_mpi` | bool | false | requires `with_chombo` | `--with-chombo: MPI=TRUE` — Chombo + MPI parallel AMR. Automatically sets `parallel=true`. |
| `with_cr_transport` | bool | false | — | `--with-cr_transport` — cosmic-ray transport (valid in setup.py source; omitted from `--help`) |

**Mutual exclusion rules (validated before calling setup.py):**

| Rule | Source |
|------|--------|
| `with_chombo` XOR `{with_fd, with_sb, with_fargo}` | `setup.py`: set-intersection check → `sys.exit(1)` |
| `with_sb` XOR `with_fd` | `setup.py`: explicit check → `sys.exit(1)` |
| `chombo_mpi=True` requires `with_chombo=True` | logical dependency |

**`--with-chombo` must be the last flag passed to setup.py.** `setup.py` executes
`break` immediately on matching it; anything after is silently ignored. This is
handled automatically by `_build_setup_argv()`.

---

## Run parameters (`PLUTOParams`)

Called by `scripts/run_pluto.py`. Parameters not listed here fall back to the
existing value in `pluto.ini` when omitted.

### Location

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `run_dir` | str | **required** | must exist | Path to compiled PLUTO run directory |
| `output_dir` | str | `run_dir` | — | Where snapshot files are written. Patches `output_dir` in `[Static Grid Output]`. Directory is created if absent. |

### Time control (patch `[Time]` in pluto.ini)

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `tstop` | float | keep existing | > 0 | Integration end time. **Mutually exclusive** with `checkpoint_times`. |
| `checkpoint_times` | list[float] | None | all > 0, ascending | Staged-run schedule. PLUTO is stopped and restarted at each value. Validated via `NDArrayAdapter(ndim=1, dtype="float64", gt=0)`. **Mutually exclusive** with `tstop`. |
| `cfl` | float | keep existing | [0.1, 0.9] | Courant number. Typical safe value: 0.3–0.4. |
| `cfl_max_var` | float | keep existing | > 1.0 | Max ratio dt^n / dt^{n-1} (time step growth limiter). Default in PLUTO: 1.1. |
| `first_dt` | float | keep existing | > 0 | Initial time step. Typical: 1e-6 to 1e-3. |

### Solver (patches `[Solver]` in pluto.ini)

| Name | Type | Default | Notes |
|---|---|---|---|
| `solver` | str | keep existing | Riemann solver token. Must be valid for the compiled physics module. See SKILL §5 table. |

### User parameters (patch `[Parameters]` in pluto.ini)

| Name | Type | Default | Notes |
|---|---|---|---|
| `parameters` | dict | `{}` | Key-value pairs for `[Parameters]`. Key names are problem-specific (defined in `init.c`). Count must match `USER_DEF_PARAMETERS` in `definitions.h` exactly. |

### Runtime flags (assembled on `./pluto` command line)

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `pluto_bin` | str | `"./pluto"` | — | Path to binary. PLUTO always produces `./pluto`; there is no `pluto_mpi`. |
| `ini_file` | str | None | — | `-i fname` — use alternative ini file instead of `pluto.ini` |
| `restart` | int | None | ≥ 0 | `-restart N` — restart from snapshot N (reads `.dbl` files). Exclusive with `h5restart`, `frestart`. |
| `h5restart` | int | None | ≥ 0 | `-h5restart N` — restart from HDF5 snapshot N (reads `.dbl.h5`). Exclusive with `restart`, `frestart`. |
| `frestart` | int | None | ≥ 0 | `-frestart N` — fluid-only restart; suppresses particle restart. Exclusive with `restart`, `h5restart`. |
| `maxsteps` | int | None | ≥ 1 | `-maxsteps N` — stop after N integration steps |
| `xres` | int | None | ≥ 1 | `-xres N` — override x1 resolution (aspect ratio preserved) |
| `no_write` | bool | false | — | `-no-write` — suppress all disk output (useful for timing) |

### MPI

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `n_procs` | int | 1 | [1, 512] | MPI rank count. Invoked as `mpirun -np N ./pluto`. |
| `decomp` | list[int] | None | product = `n_procs` | `-dec n1 [n2] [n3]` — explicit MPI domain decomposition. Product of all values must equal `n_procs`. |

### Compile integration

| Name | Type | Default | Notes |
|---|---|---|---|
| `config_num` | int | None | Config variant N for auto-compile |
| `auto_compile` | bool | true | Compile automatically if `./pluto` is missing |
| `force_compile` | bool | false | Force recompile before running |

### Background & monitoring

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `background` | bool | false | — | Launch and return immediately (single stage only). Writes PID and log files. |
| `monitor` | bool | false | — | Poll snapshots while running; log t, dt, nstep, rho_max/min per new snapshot. |
| `watch_interval` | float | 20.0 | [1, 3600] | Polling cadence in seconds |
| `plot_on_the_fly` | bool | false | — | Render density + velocity plots as snapshots appear |
| `plot_interval` | float | 30.0 | [1, 3600] | Minimum seconds between plot renders |
| `plot_output_dir` | str | `<output_dir>/live_plots` | — | Directory for monitor plots |
| `quiver_subsample` | int | 8 | [1, 128] | Velocity field downsampling factor for quiver overlay |

### Output directory options (patch `[Static Grid Output]`)

| Name | Type | Default | Notes |
|---|---|---|---|
| `log_dir` | str | None | Directory for parallel log files (`pluto.0.log` etc.) |

---

## Output descriptor files

PLUTO writes a `*.out` file for each enabled output format after every snapshot.
These are the **ground truth** for restart decisions.

`dbl.out` columns: `n  t  dt  nstep  [single_file]  [endian]  var1 var2 ...`

Where `n` is the snapshot index used with `-restart N`.

For Chombo-AMR: checkpoint files are `chk.nnnn.hdf5`; plot files are `data.nnnn.hdf5`.
Restart with `-restart N` (reads `chk.nnnn.hdf5`).
