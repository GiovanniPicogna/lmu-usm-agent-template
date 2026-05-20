---
name: pluto
description: >
  Patch pluto.ini parameters and launch a PLUTO (HD/MHD) simulation.
  Use this skill to override time, solver, or problem-specific [Parameters]
  in an existing PLUTO run directory without touching definitions.h or
  recompiling the binary. Returns last-snapshot diagnostics and wall-clock time.
  Trigger phrases: PLUTO code, pluto.ini, PLUTO simulation, tstop, CFL,
  HD simulation, MHD simulation, .dbl file, PLUTO snapshot, PLUTO run.
argument-hint: "Run directory and parameters to override, e.g. 'runs/disk_gap tstop=500 ALPHA=1e-3'"
---

# PLUTO Skill

## When to Use

- Run or resume a PLUTO (HD/MHD) simulation in an existing compiled run directory
- Adjust `tstop`, `CFL`, `first_dt`, the Riemann solver, or any `[Parameters]`
  entry **without** recompiling
- Do **NOT** use this skill to change `definitions.h`, grid geometry, or physics
  modules — those require recompilation (consult the `simulation-agent`)

## Prerequisites

- The PLUTO binary (`pluto` or `mpirun`) must already be **compiled** in `run_dir`
- A valid `pluto.ini` must exist in `run_dir`
- MPI must be available if `n_procs > 1`

## Procedure

1. Collect `run_dir` and any parameter overrides from the user.
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
3. The script backs up `pluto.ini`, patches the requested sections, launches PLUTO,
   then restores the original `pluto.ini` on exit.
4. Parse `SUCCESS:` / `ERROR:` prefix.  On error, show the last 15 lines of stderr.

## Parameters

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `run_dir` | str | **required** | must exist | Path to compiled PLUTO run dir |
| `output_dir` | str | `run_dir` | — | Where `.dbl` / HDF5 output is written |
| `tstop` | float | (keep existing) | > 0 | Single-stop end time (mutually exclusive with `checkpoint_times`) |
| `checkpoint_times` | `np.ndarray` (1-D) | None | all > 0 | Staged-run schedule in code units; PLUTO is restarted at each stop automatically. Validated via `NDArrayAdapter(ndim=1, dtype="float64", gt=0)` from **scientific-pydantic**; pass as JSON list `[100, 200, 500]`. Mutually exclusive with `tstop`. |
| `cfl` | float | (keep existing) | [0.1, 0.9] | CFL safety factor |
| `first_dt` | float | (keep existing) | > 0 | First time-step |
| `solver` | str | (keep existing) | — | Riemann solver name, e.g. `roe`, `hll` |
| `parameters` | dict | `{}` | — | Key-value pairs for `[Parameters]` section |
| `n_procs` | int | 1 | [1, 512] | MPI rank count |
| `pluto_bin` | str | `./pluto` | — | Path to PLUTO executable |
| `restart` | int | None | ≥ 0 | Restart from snapshot number N (first stage only) |

## Output

```
SUCCESS: run_dir=<path>  wall_clock=<N>s
  last_snapshot=<N>  t=<val> (code units)
  rho_max=<val>  rho_min=<val>
  warnings: <any stderr warnings>
```

## Common Errors

| Message | Fix |
|---|---|
| `pluto binary not found` | Check `pluto_bin` path; ensure binary is compiled |
| `pluto.ini not found` | Verify `run_dir` contains `pluto.ini` |
| `Specify either tstop or checkpoint_times` | Remove one of the two conflicting fields |
| `scientific_pydantic not found` | `pip install scientific-pydantic` |
| `section [Parameters] key not found` | Key will be appended; check spelling |
| `MPI launch failed` | Ensure `mpirun` is on PATH; try `n_procs=1` |
| `cfl must be in [0.1, 0.9]` | Use a value like 0.3 or 0.4 |
