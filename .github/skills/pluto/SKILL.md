---
name: pluto
description: >
  Compile, configure, and run PLUTO (HD/MHD/RHD/RMHD) simulations.
  Use when the user mentions: PLUTO code, pluto.ini, definitions.h,
  PLUTO simulation, tstop, CFL, Riemann solver, .dbl/.h5/.vtk output,
  snapshot, restart, compile PLUTO, make PLUTO, pyPLUTO, plutoplot,
  MHD wind, disc simulation, init.c, setup.py, PLUTO_DIR.
  Do NOT use for non-PLUTO CFD codes (Athena, RAMSES, FARGO, GADGET).
argument-hint: >
  Run directory + task, e.g.:
  'runs/disk_planet  compile  config_num=1'
  'runs/disk_planet  tstop=500  ALPHA=1e-3  n_procs=4'
  'runs/disk_planet  restart=12  tstop=800'
---

# PLUTO Simulation Skill
# Mignone et al. 2007 — https://plutocode.ph.unito.it

## 0. Chain-of-Thought Checklist (run mentally before every action)

Before executing ANYTHING, answer these five questions in order:

1. **What is the user's actual goal?**
   (reach a target time? test a new solver? resume a crashed run?)
2. **Does a compiled binary already exist in `run_dir`?**
   (check for `./pluto` or `./pluto_mpi` before deciding to compile)
3. **Will the requested change require recompilation?**
   (grid geometry, physics module, dimensionality → YES;
    tstop, CFL, solver, [Parameters] values → NO)
4. **What output files already exist?**
   (inspect `*.out` descriptor files and highest `.dbl` / `.h5` index
    before choosing restart vs. fresh start)
5. **Is the change reversible?**
   (always back up `pluto.ini` and `definitions.h` before patching)

Only after answering all five should you call a script.

---

## 1. PLUTO Architecture — What the Agent Must Know

```
run_dir/
├── definitions.h        ← physics module, dimensionality, geometry (COMPILE-TIME)
├── definitions_N.h      ← numbered variants; copy → definitions.h before compiling
├── init.c               ← initial/boundary conditions (COMPILE-TIME)
├── pluto.ini            ← grid, solver, output, [Parameters] (RUNTIME — patchable)
├── pluto_N.ini          ← numbered ini variants (paired with definitions_N.h)
├── pluto                ← compiled binary (serial)
├── pluto_mpi            ← compiled binary (MPI parallel)
├── *.out                ← descriptor files (grid info, variable names, file offsets)
├── *.dbl / *.h5 / *.vtk ← snapshot data files
└── sysconf.out          ← records last compile configuration
```

**CRITICAL rules:**
- `definitions.h` changes → **must recompile** — never patch at runtime
- `pluto.ini` changes → **no recompile needed** — patch safely
- `[Parameters]` in `pluto.ini` are user-defined names from `init.c` — they vary per problem
- The restart flag is a **command-line argument**, NOT a `pluto.ini` entry:
  `./pluto -restart N` (N = snapshot number to restart from)
- MPI decomposition is specified on the command line:
  `mpirun -np 4 ./pluto_mpi -no-x2par` (or with `-decomp n1 n2 n3`)
- Output format (`.dbl`, `.h5`, `.vtk`) is set in `pluto.ini [Output]` — check before reading

---

## 2. Decision Tree: Compile vs. Run vs. Patch

```
User request
    │
    ├─ "change grid / geometry / physics / dimensionality"
    │       └─► COMPILE (must; binary invalid after these changes)
    │
    ├─ "change tstop / CFL / first_dt / solver / [Parameters]"
    │       └─► PATCH pluto.ini only, then RUN (no compile)
    │
    ├─ "resume / restart / continue"
    │       └─► find highest snapshot N in run_dir
    │           └─► RUN with -restart N
    │
    ├─ "compile config N" or "definitions_N.h"
    │       └─► COMPILE with config_num=N
    │
    └─ binary missing?
            └─► auto-compile, then RUN
```

---

## 3. Compile Procedure

### 3a. When to compile

Compile if ANY of the following are true:
- No `./pluto` or `./pluto_mpi` binary exists in `run_dir`
- `force_compile=true` was requested
- `definitions.h` was changed (geometry, physics module, dimensionality,
  number of passive scalars, EOS, divergence cleaning method, AMR on/off)
- `config_num` differs from what `sysconf.out` records

**Do NOT compile** if only `pluto.ini` values or `[Parameters]` changed.

### 3b. Compile steps

```bash
# Step 1 (if config_num=N): copy numbered variant
cp definitions_N.h definitions.h
cp pluto_N.ini    pluto.ini          # if pluto_N.ini exists

# Step 2: run setup.py to regenerate the makefile
python $PLUTO_DIR/setup.py --auto-update --no-curses

# Step 3: parallel build
make -j${make_jobs:-4}

# Step 4: verify binary exists
ls -lh pluto pluto_mpi 2>/dev/null
```

Script call:
```bash
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --run-dir /path/to/problem \
    --config-num 1 \
    --make-jobs 4
```

JSON form:
```bash
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --json '{"run_dir": "/path/to/problem", "config_num": 1, "make_jobs": 4}'
```

**Parse output:** look for `SUCCESS:` or `ERROR:` prefix. On error, show last 20 lines.

---

## 4. pluto.ini Patch Procedure

**Always back up before patching:**
```bash
cp pluto.ini pluto.ini.bak.$(date +%Y%m%d_%H%M%S)
```

`pluto.ini` has named sections in square brackets. Patch only the relevant key:

```ini
[Time]
tstop          500.0        # ← patch this
first_dt       1.e-4
CFL            0.4          # ← or this

[Solver]
Solver         roe           # ← or this (hll, hllc, roe, tvdlf, etc.)

[Parameters]
ALPHA          1.e-3        # ← user-defined; name comes from init.c
MPLANET        1.0
```

**Geometry / grid block** (`[Grid]`) — **NEVER patch at runtime**; requires recompile.

---

## 5. Run Procedure

### 5a. Determine restart vs. fresh start

```bash
# Find highest existing snapshot
ls *.dbl 2>/dev/null | sort -V | tail -1
# or check the .out descriptor:
tail -1 dbl.out   # format: snapshot_num  time  dt  nstep  ...  filename(s)
```

If snapshots exist and user wants to continue → use `-restart N`.

### 5b. Assemble the command line

```bash
# Serial fresh start:
./pluto

# Serial restart from snapshot 12:
./pluto -restart 12

# MPI fresh start, 4 procs:
mpirun -np 4 ./pluto_mpi

# MPI restart, explicit decomposition (x1=2, x2=2 procs):
mpirun -np 4 ./pluto_mpi -restart 12 -decomp 2 2

# Use alternative ini file:
./pluto -i custom.ini

# Grid-only mode (no computation, useful for sanity-check):
./pluto --makegrid
```

### 5c. Script call

```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{
      "run_dir":    "runs/disk_planet",
      "tstop":      500.0,
      "cfl":        0.3,
      "parameters": {"ALPHA": 1e-3, "MPLANET": 1.0},
      "n_procs":    4,
      "restart":    12,
      "background": false
    }'
```

Background / long run:
```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{
      "run_dir":         "runs/disk_planet",
      "tstop":           1000.0,
      "background":      true,
      "monitor":         true,
      "plot_on_the_fly": true,
      "watch_interval":  30.0
    }'
```

---

## 6. Staged / Checkpoint Runs

Use `checkpoint_times` (not `tstop`) to run in stages — useful for saving intermediate
states or changing parameters mid-run. **Mutually exclusive with `tstop`.**

```json
{
  "run_dir": "runs/disk_planet",
  "checkpoint_times": [100, 250, 500, 1000],
  "parameters": {"ALPHA": 1e-3}
}
```

The script restarts from the previous checkpoint at each stage automatically.
Each stage appends to the existing output (PLUTO's default behaviour).

---

## 7. Output Reading — Sanity Check After Every Run

After a run completes, always read and report the last snapshot diagnostics:

```bash
# Read the .out descriptor to find last snapshot:
tail -5 dbl.out        # columns: n  t  dt  nstep  [file_info]
tail -5 tabulated.dat  # runtime diagnostics (if enabled in pluto.ini)
grep "PLUTO" pluto_run.log | tail -10   # scan for warnings

# Check for common pathologies:
grep -i "nan\|inf\|negative\|overflow\|diverge" pluto_run.log | head -20
```

**Raise a warning (do not silently proceed) if any of:**
- `rho_min < 0` or `NaN` in any variable
- Wall-clock time per snapshot > 10× the first few snapshots (CFL crash incoming)
- `dt` decreasing monotonically for > 5 consecutive snapshots (instability)
- Any `WARNING` or `! Fatal` line in the log

### Post-run analysis — recommend PyPLUTO

```python
# PyPLUTO (new, official — arXiv:2501.09748, pip install pypluto):
import pyPLUTO as pp
d = pp.Load(12, w_dir="runs/disk_planet/", datatype="dbl")
# d.rho, d.vx1, d.vx2, d.Bx3, d.x1, d.x2 ...

# plutoplot (alternative, lightweight):
import plutoplot as ppt
sim = ppt.Simulation("runs/disk_planet/")
frame = sim[12]   # snapshot 12; frame.rho, frame.grid.x1, etc.
```

Always report: last snapshot number, last `t` (code units), `rho_max`, `rho_min`.

---

## 8. Parameters Reference Table

### Compile (`PLUTOCompileParams`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `run_dir` | str | **required** | Path to PLUTO problem directory |
| `pluto_dir` | str | `$PLUTO_DIR` | PLUTO source tree root |
| `config_num` | int | None | Copy `definitions_N.h` + `pluto_N.ini` before compiling |
| `arch` | str | auto-detect | Makefile arch token, e.g. `Linux.gcc.defs`, `Darwin.gcc.defs` |
| `make_jobs` | int | 4 | `-jN` parallelism for `make` |
| `force_compile` | bool | false | Force rebuild even if binary exists |

### Run (`PLUTORunParams`)

| Parameter | Type | Default | Constraint | Description |
|-----------|------|---------|------------|-------------|
| `run_dir` | str | **required** | must exist | Problem directory with compiled binary |
| `output_dir` | str | `run_dir` | — | Where snapshots are written |
| `tstop` | float | keep existing | > 0 | End time; **mutually exclusive** with `checkpoint_times` |
| `checkpoint_times` | list[float] | None | all > 0, ascending | Staged end-times; **mutually exclusive** with `tstop` |
| `cfl` | float | keep existing | [0.1, 0.9] | CFL safety factor |
| `first_dt` | float | keep existing | > 0 | First timestep size |
| `solver` | str | keep existing | — | Riemann solver: `roe`, `hll`, `hllc`, `tvdlf`, `ct` (MHD) |
| `parameters` | dict | `{}` | — | `[Parameters]` key-value pairs (problem-specific names) |
| `n_procs` | int | 1 | [1, 512] | MPI rank count; requires `./pluto_mpi` binary |
| `decomp` | list[int] | None | product = n_procs | Explicit MPI decomposition [n1, n2, n3] |
| `pluto_bin` | str | `./pluto` | — | Binary path; auto-switches to `./pluto_mpi` if n_procs > 1 |
| `ini_file` | str | `pluto.ini` | — | Alternative ini file (`-i` flag) |
| `restart` | int | None | ≥ 0 | Restart from snapshot N |
| `config_num` | int | None | [1, 99] | Config variant for auto-compile |
| `auto_compile` | bool | true | — | Compile automatically if binary missing |
| `force_compile` | bool | false | — | Force recompile before running |
| `background` | bool | false | — | Launch and return immediately |
| `monitor` | bool | false | — | Poll snapshots while running |
| `watch_interval` | float | 20.0 | [1, 3600] | Polling cadence (seconds) |
| `plot_on_the_fly` | bool | false | — | Render density + velocity plots during run |
| `plot_interval` | float | 30.0 | [1, 3600] | Minimum seconds between renders |
| `plot_output_dir` | str | `<output_dir>/live_plots` | — | Directory for monitor plots |
| `quiver_subsample` | int | 8 | [1, 128] | Downsampling factor for velocity quiver |

---

## 9. Output Format

### Compile success
```
SUCCESS: binary=<path>
  arch=<arch>  config_num=<N|none>  make_jobs=<N>  wall_clock=<N>s
  pluto_dir=<path>
```

### Run success
```
SUCCESS: run_dir=<path>  wall_clock=<N>s
  last_snapshot=<N>  t=<val> (code units)
  rho_max=<val>  rho_min=<val>
  dt_last=<val>  nstep=<N>
  warnings: <any stderr warnings, or "none">
```

### Background launch
```
STARTED: pid=<pid>  run_dir=<path>
  log=<output_dir>/pluto_run.log
  pid_file=<output_dir>/pluto_run.pid
  monitor_log=<output_dir>/pluto_monitor.log  (if monitor=true)
```

---

## 10. Error Handling

| Error message | Root cause | Fix |
|---------------|-----------|-----|
| `PLUTO binary not found` | Not compiled yet | Run compile step; or set `auto_compile=true` |
| `pluto.ini not found` | Wrong `run_dir` | Verify path; check for `pluto_N.ini` variants |
| `definitions.h not found` | Missing header | Pass `config_num` or copy manually |
| `setup.py --auto-update failed` | Bad `$PLUTO_DIR` or Python 2 vs 3 mismatch | Check env var; try `python3 $PLUTO_DIR/setup.py` |
| `make failed` | Missing gcc / make | Install build tools; check compiler error |
| `Specify either tstop or checkpoint_times` | Both fields provided | Remove one |
| `MPI launch failed` | `mpirun` not on PATH | Check `which mpirun`; try `n_procs=1` |
| `cfl must be in [0.1, 0.9]` | Out-of-range CFL | Use 0.3–0.4 as safe default |
| `scientific_pydantic not found` | Missing dependency | `pip install scientific-pydantic` |
| `NaN / negative density in log` | Numerical instability | Reduce CFL; switch to more diffusive solver (e.g. `hll`); check `first_dt` |
| `restart file not found` | Snapshot N doesn't exist | Check `dbl.out` for valid snapshot indices |
| `decomp product ≠ n_procs` | Decomposition mismatch | Ensure n1 × n2 × n3 = n_procs |

---

## 11. Physics Module Quick Reference

(from `definitions.h` — COMPILE-TIME, cannot be changed at runtime)

| Module | `PHYSICS` token | Typical use |
|--------|----------------|-------------|
| Classical HD | `HD` | Disc, wind, shock problems |
| Classical MHD | `MHD` | Magnetised disc, jet, ISM |
| Relativistic HD | `RHD` | Relativistic jets, GRB |
| Relativistic MHD | `RMHD` | GRMHD-adjacent problems |

**Geometry options** (also compile-time):
`CARTESIAN`, `CYLINDRICAL`, `POLAR`, `SPHERICAL`

**Riemann solvers** (runtime-switchable in `pluto.ini`):
`tvdlf` (most robust), `hll`, `hllc`, `roe` (most accurate), `ct` (MHD only)

---

## 12. Safety Rules — Agent Must Never Violate

1. **Never modify `definitions.h` without immediately triggering a recompile.**
2. **Never overwrite an existing `pluto.ini` without first making a timestamped backup.**
3. **Never start a fresh run in a directory that has existing snapshots without explicit user confirmation** — this would overwrite results. Instead: ask whether to restart from the last snapshot or clean the directory.
4. **Never change `[Grid]` in `pluto.ini` at runtime** — grid is set at compile time via `definitions.h` and only the number of grid points can be adjusted; changing geometry requires recompile.
5. **Never assume `[Parameters]` key names** — they are defined in `init.c` and vary per problem. Always read the existing `pluto.ini` first to discover the actual key names before patching.
6. **Never launch with `n_procs > 1` using the serial binary `./pluto`** — use `./pluto_mpi` (compiled with MPI support).
