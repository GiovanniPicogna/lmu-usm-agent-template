# PLUTO Skill — Full Parameter Reference

## Compile parameters (`PLUTOCompileParams`)

Called by `scripts/compile_pluto.py`.

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `run_dir` | str | **required** | must exist | Path to PLUTO problem directory containing `definitions.h` (or numbered variants) |
| `pluto_dir` | str | `$PLUTO_DIR` | must exist | Path to PLUTO source tree |
| `config_num` | int | None | 1 – 99 | If given, copies `definitions_N.h` → `definitions.h` and `pluto_N.ini` → `pluto.ini` before compiling |
| `arch` | str | auto-detected | — | Makefile arch string from `$PLUTO_DIR/Config/`, e.g. `Darwin.gcc.defs`, `Linux.gcc.defs`. Auto-detected from `platform.system()` if omitted. |
| `make_jobs` | int | 4 | [1, 64] | Parallel `make -jN` jobs |

---

## Run parameters (`PLUTOParams`)

Called by `scripts/run_pluto.py`. Parameters marked **required** have no
default; all others fall back to the existing `pluto.ini` value when omitted.

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `run_dir` | str | **required** | must exist | Path to compiled PLUTO run directory |
| `output_dir` | str | `run_dir` | — | Where `.dbl` / HDF5 output is written |
| `tstop` | float | (keep existing) | > 0 | Single-stop end time (mutually exclusive with `checkpoint_times`) |
| `checkpoint_times` | `np.ndarray` (1-D, float64) | None | all > 0 | Staged-run schedule in code units; PLUTO is restarted at each stop automatically. Validated via `NDArrayAdapter(ndim=1, dtype="float64", gt=0)` from **scientific-pydantic**; pass as JSON list `[100, 200, 500]`. Mutually exclusive with `tstop`. |
| `cfl` | float | (keep existing) | [0.1, 0.9] | CFL safety factor |
| `first_dt` | float | (keep existing) | > 0 | First time-step |
| `solver` | str | (keep existing) | — | Riemann solver name, e.g. `roe`, `hll` |
| `parameters` | dict | `{}` | — | Key-value pairs for the `[Parameters]` section of `pluto.ini` |
| `n_procs` | int | 1 | [1, 512] | MPI rank count |
| `pluto_bin` | str | `"./pluto"` | — | Path to PLUTO executable |
| `restart` | int | None | ≥ 0 | Restart from snapshot number N (first stage only) |
