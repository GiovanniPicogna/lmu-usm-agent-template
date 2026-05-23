# PLUTO Skill — Run Examples
# Based on PLUTO v4.4-patch3, compile_pluto_v4, run_pluto_v4

All compile/run commands below use
`$PLUTO_DIR/Test_Problems/HD/Disk_Planet/` as the reference run directory
(set PLUTO_DIR before running; do not pass it as a literal string in JSON).
It contains eight numbered config variants (`definitions_01.h` –
`definitions_08.h`, paired with `pluto_01.ini` – `pluto_08.ini`).

---

## 1. HD Disk–Planet — 2-D polar isothermal disk

2-D isothermal HD disk in polar geometry (r ∈ [0.4, 2.5], 256 × 768 cells).
Runtime-patchable `[Parameters]`: `Mplanet`, `Viscosity`, `MdiskCGS`, `Mstar`.

### Compile (config variant 1)

```bash
# CLI
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --config-num 1

# JSON (agent form — resolve $PLUTO_DIR before constructing the string)
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --json '{"run_dir": "/path/to/PLUTO/Test_Problems/HD/Disk_Planet",
             "config_num": 1}'
```

### Run with defaults (tstop from pluto_01.ini)

```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet"
```

### Override planet mass and extend to 10 orbital periods

```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "/path/to/Disk_Planet",
             "tstop": 10.0,
             "parameters": {"Mplanet": 100.0, "Viscosity": 1e14}}'
```

### Staged run with restarts at t = 2, 5, 10

```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "/path/to/Disk_Planet",
             "checkpoint_times": [2.0, 5.0, 10.0]}'
```

### Resume from snapshot 5, extend to t = 10

```bash
# dbl restart (reads .dbl files)
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --restart 5 --tstop 10.0

# HDF5 restart (reads .dbl.h5 files; requires binary compiled with hdf5=true)
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --h5restart 5 --tstop 10.0
```

### Parallel run — 4 MPI processes with decomposition

```bash
# Compile with MPI support
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --config-num 1 --parallel

# Run: mpirun -np 4 ./pluto -dec 2 2
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "/path/to/Disk_Planet",
             "tstop": 10.0,
             "n_procs": 4,
             "decomp": [2, 2],
             "parameters": {"Mplanet": 100.0}}'
```

### Stop after N steps (timing test)

```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --maxsteps 100 --no-write
```

### Background run with live monitoring

```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "/path/to/Disk_Planet",
             "tstop": 20.0,
             "background": true,
             "monitor": true,
             "plot_on_the_fly": true,
             "watch_interval": 30.0}'
```

---

## 2. HD Disk–Planet with FARGO orbital advection

```bash
# Compile with FARGO module
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --config-num 1 --with-fargo

# Run as normal — FARGO is activated via definitions.h at compile time
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --tstop 10.0
```

---

## 3. HD Disk–Planet with shearing box

```bash
# Compile with shearing box (mutually exclusive with --with-fd)
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" \
    --config-num 1 --with-sb

# JSON form
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --json '{"run_dir": "/path/to/Disk_Planet",
             "config_num": 1,
             "with_sb": true}'
```

---

## 4. MHD Disk Wind — 2-D axisymmetric disk wind

```bash
# Compile
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --run-dir "$PLUTO_DIR/Test_Problems/MHD/Disk_Wind" \
    --config-num 1

# Run with modified solver (roe → hll for robustness)
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "/path/to/MHD/Disk_Wind",
             "tstop": 5.0,
             "solver": "hll"}'
```

---

## 5. AMR — Chombo adaptive mesh refinement

```bash
# Prerequisites: g++ and gfortran must be installed (checked automatically)
# Chombo is incompatible with --with-fd, --with-sb, --with-fargo

# Serial AMR compile
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --json '{"run_dir": "/path/to/my_amr_problem",
             "with_chombo": true}'

# Parallel AMR compile (implies parallel=true)
python ~/.agents/skills/pluto/scripts/compile_pluto.py \
    --json '{"run_dir": "/path/to/my_amr_problem",
             "with_chombo": true,
             "chombo_mpi": true}'

# Run AMR simulation
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "/path/to/my_amr_problem",
             "tstop": 1.0,
             "n_procs": 4}'

# Restart AMR from Chombo checkpoint file chk.0005.hdf5
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "/path/to/my_amr_problem",
             "restart": 5,
             "tstop": 3.0}'
```

Note: Chombo-AMR restarts use `-restart N` which reads `chk.nnnn.hdf5`
checkpoint files (not `.dbl` files). AMR plot files are `data.nnnn.hdf5`.

---

## 6. Other useful test problems in `$PLUTO_DIR/Test_Problems/`

| Path | Physics | Notes |
|---|---|---|
| `HD/Disk_Vortex/` | HD polar | Rossby wave instability; good FARGO test |
| `HD/Jet/` | HD cylindrical | Jet propagation; try `roe` vs `hll` solvers |
| `MHD/Disk_Wind/` | MHD polar | Magnetically driven disk wind |
| `MHD/Orszag_Tang/` | MHD Cartesian | Classic MHD vortex; tests `hlld` solver |
| `RHD/Blast/` | RHD Cartesian | Relativistic blast wave |
| `RMHD/Rotor/` | RMHD Cartesian | Relativistic MHD rotor |
| `Particles/Dust/` | HD + dust | Dust-gas drag; fluid-only restart with `-frestart` |

---

## Common error patterns and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `ERROR: PLUTO binary not found` | Not compiled yet | Run compile script; or set `auto_compile=true` |
| `ERROR: make failed` (Chombo) | Missing g++ or gfortran | Install C++ and Fortran compilers |
| `PLUTO exited 1` immediately | Bad `[Parameters]` count | Count `USER_DEF_PARAMETERS` in `definitions.h`; must match pluto.ini exactly |
| `NaN` / `rho_min < 0` in log | Numerical instability | Reduce `cfl` (try 0.2); switch to `tvdlf`; reduce `first_dt` |
| `dt` decreasing every step | CFL violation or instability | Reduce `cfl`; check for supersonic inflow boundaries |
| Snapshots never written | Wrong section name patched | Verify `[Static Grid Output]` section exists in pluto.ini (not `[Output]`) |
| `decomp` product ≠ `n_procs` | Bad decomposition | Ensure n1 × n2 × n3 = n_procs |
| `mpirun: command not found` | MPI not on PATH | `module load openmpi`; or use `n_procs=1` |
