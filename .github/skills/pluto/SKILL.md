---
name: pluto
description: >
  Compile a PLUTO problem or patch pluto.ini and launch a PLUTO (HD/MHD) simulation.
  Use this skill to compile a PLUTO problem from its definitions.h, override time,
  solver, or problem-specific [Parameters] in an existing run directory.
  Returns last-snapshot diagnostics and wall-clock time.
  Trigger phrases: PLUTO code, pluto.ini, PLUTO simulation, tstop, CFL,
  HD simulation, MHD simulation, .dbl file, PLUTO snapshot, PLUTO run,
  compile PLUTO, definitions.h, make PLUTO.
argument-hint: "Run directory and task, e.g. 'runs/disk_gap compile config_num=1' or 'runs/disk_gap tstop=500 ALPHA=1e-3'"
---

# PLUTO Skill

## When to Use

- **Compile** a PLUTO problem from `definitions.h` (or a numbered variant `definitions_N.h`)
- **Run or resume** a compiled PLUTO simulation
- **Adjust** `tstop`, `CFL`, `first_dt`, Riemann solver, or any `[Parameters]`
  entry **without** recompiling
- Do **NOT** use this skill to change grid geometry or physics modules if a compiled binary already exists — those require calling the compile step again

## Prerequisites

- `$PLUTO_DIR` must point to the PLUTO source tree (or pass `--pluto-dir`)
- A C compiler (`gcc`) and `make` must be on `PATH`
- For the run step: a compiled `pluto` binary in `run_dir`
- MPI must be available if `n_procs > 1`

## Compile Procedure

1. Identify `run_dir` and the config variant (if any) from the user.
2. Call the compile script:
   ```bash
   python ~/.agents/skills/pluto/scripts/compile_pluto.py \
       --run-dir $PLUTO_DIR/Test_Problems/HD/Disk_Planet --config-num 1
   ```
   JSON form:
   ```bash
   python ~/.agents/skills/pluto/scripts/compile_pluto.py \
       --json '{"run_dir": "/path/to/Disk_Planet", "config_num": 1}'
   ```
3. The script:
   - Copies `definitions_01.h` → `definitions.h` and `pluto_01.ini` → `pluto.ini`
   - Auto-detects the host arch (Darwin / Linux) and writes a stub `makefile`
   - Calls `setup.py --auto-update --no-curses` to regenerate the full `makefile`
   - Runs `make -j4` (parallel)
4. Parse `SUCCESS:` / `ERROR:` prefix. On error, show the last 20 lines of stderr.

## Run Procedure

1. Collect `run_dir` and any parameter overrides from the user.
2. Compile policy (default):
  - Auto-compile if `pluto` binary is missing (`auto_compile=true` by default)
  - Recompile on demand with `force_compile=true`
  - If a numbered setup is required, pass `config_num=<N>`
  - Disable auto-compile only when you are sure the binary is valid: `auto_compile=false`
2. Call the patch-and-run script:
   ```
   python ~/.agents/skills/pluto/scripts/run_pluto.py \
       --json '{"run_dir": "runs/disk_gap", "tstop": 500.0, "parameters": {"ALPHA": 1e-3}}'
   ```
   Individual flags:
   ```
   python ~/.agents/skills/pluto/scripts/run_pluto.py \
       --run-dir runs/disk_gap --tstop 500.0 --n-procs 4
   ```
3. Background mode for long runs:
  ```
  python ~/.agents/skills/pluto/scripts/run_pluto.py \
     --json '{"run_dir": "runs/disk_gap", "tstop": 1000.0, "background": true, "monitor": true, "plot_on_the_fly": true}'
  ```
4. The script backs up `pluto.ini`, patches requested sections, launches PLUTO, then restores the original `pluto.ini`.
5. If `background=true`, parse `STARTED:` output and track:
  - `pid`
  - `pluto_run.log`
  - `pluto_run.pid`
  - optional `pluto_monitor.log`
6. Parse `SUCCESS:` / `ERROR:` prefix in foreground mode. On error, show the last 15 lines of stderr.

## Parameters

### Compile (`PLUTOCompileParams`)

| Name | Type | Default | Notes |
|---|---|---|---|
| `run_dir` | str | **required** | Path to PLUTO problem directory |
| `pluto_dir` | str | `$PLUTO_DIR` | Path to PLUTO source tree |
| `config_num` | int | None | Copies `definitions_N.h` + `pluto_N.ini` before compiling |
| `arch` | str | auto-detected | Makefile arch e.g. `Darwin.gcc.defs`, `Linux.gcc.defs` |
| `make_jobs` | int | 4 | Parallel `make -jN` jobs |

### Run (`PLUTOParams`)

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `run_dir` | str | **required** | must exist | Path to compiled PLUTO run dir |
| `output_dir` | str | `run_dir` | — | Where `.dbl` / HDF5 output is written |
| `tstop` | float | (keep existing) | > 0 | Single-stop end time (mutually exclusive with `checkpoint_times`) |
| `checkpoint_times` | `np.ndarray` (1-D) | None | all > 0 | Staged-run schedule in code units; pass as JSON list `[100, 200, 500]`. Mutually exclusive with `tstop`. |
| `cfl` | float | (keep existing) | [0.1, 0.9] | CFL safety factor |
| `first_dt` | float | (keep existing) | > 0 | First time-step |
| `solver` | str | (keep existing) | — | Riemann solver name, e.g. `roe`, `hll` |
| `parameters` | dict | `{}` | — | Key-value pairs for `[Parameters]` section |
| `n_procs` | int | 1 | [1, 512] | MPI rank count |
| `pluto_bin` | str | `./pluto` | — | Path to PLUTO executable |
| `restart` | int | None | ≥ 0 | Restart from snapshot number N (first stage only) |
| `config_num` | int | None | [1, 99] | Compile variant passed to `compile_pluto.py` when compile is triggered |
| `auto_compile` | bool | `true` | — | Compile automatically if binary is missing |
| `force_compile` | bool | `false` | — | Force a recompile before running |
| `background` | bool | `false` | — | Return immediately after launch; writes PID and log files |
| `monitor` | bool | `false` | — | Monitor snapshots while PLUTO runs |
| `watch_interval` | float | `20.0` | [1, 3600] | Polling cadence (seconds) for monitor loop |
| `plot_on_the_fly` | bool | `false` | — | Render density + velocity plots while snapshots appear |
| `plot_interval` | float | `30.0` | [1, 3600] | Minimum seconds between plot renders |
| `plot_output_dir` | str | `<output_dir>/live_plots` | — | Directory for generated monitor plots |
| `quiver_subsample` | int | `8` | [1, 128] | Vector-field downsampling for quiver overlay |

## Output

**Compile:**
```
SUCCESS: binary=<path>
  arch=<arch>  config_num=<N>  make_jobs=<N>  wall_clock=<N>s
  pluto_dir=<path>
```

**Run:**
```
SUCCESS: run_dir=<path>  wall_clock=<N>s
  last_snapshot=<N>  t=<val> (code units)
  rho_max=<val>  rho_min=<val>
  warnings: <any stderr warnings>
```

Background launch:
```
STARTED: pid=<pid> run_dir=<path>
  log=<output_dir>/pluto_run.log
  pid_file=<output_dir>/pluto_run.pid
  monitor_log=<output_dir>/pluto_monitor.log
```

## Common Errors

| Message | Fix |
|---|---|
| `PLUTO binary not found` | Run the compile step first; check `pluto_bin` path |
| `pluto.ini not found` | Verify `run_dir` contains `pluto.ini` |
| `definitions.h not found` | Pass `config_num` or copy manually |
| `setup.py --auto-update failed` | Check `$PLUTO_DIR`; ensure `setup.py` is executable |
| `make failed` | Install `gcc` / `make`; check compiler error in output |
| `Specify either tstop or checkpoint_times` | Remove one of the two conflicting fields |
| `scientific_pydantic not found` | `pip install scientific-pydantic` |
| `MPI launch failed` | Ensure `mpirun` is on PATH; try `n_procs=1` |
| `cfl must be in [0.1, 0.9]` | Use a value like 0.3 or 0.4 |
