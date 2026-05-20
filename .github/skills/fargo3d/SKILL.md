---
name: fargo3d
description: >
  Patch a FARGO3D .par file and launch a planet-disk simulation.
  Use this skill to set disk structure (AspectRatio, Sigma0, Alpha, FlaringIndex),
  planet properties (PlanetMass), time integration (Tmax, DT, Ninterm), or grid
  resolution without manually editing files. Returns gap depth, planet torque,
  and wall-clock time. Trigger phrases: FARGO3D, disk simulation, planet migration,
  gap opening, planet torque, gasdens, .par file, Sigma0, AspectRatio, Alpha viscosity,
  planet-disk interaction, spiral arm, type I migration.
argument-hint: "Par file + parameters, e.g. 'setups/p_gap/p_gap.par Alpha=1e-3 PlanetMass=3e-4'"
---

# FARGO3D Skill

## When to Use

- Run a planet-disk interaction simulation (gap opening, migration, torques)
- Sweep disk parameters (aspect ratio, surface density, alpha viscosity) without
  recompiling — FARGO3D recompile is only needed when changing `NFLUIDS`, `MHD`, etc.
- Do **NOT** use this skill if you need to change compile-time flags in `src/`
  or switch the setup directory — those require recompilation

## Prerequisites

- The FARGO3D binary (`fargo3d`) must already be **compiled** and accessible
- A valid `.par` file must exist for the chosen setup
- `pip install scientific-pydantic` (used for numpy array validation; required even though `.par` values are scalars, as `NDArrayAdapter` is available for future array-typed extensions)

## Procedure

1. Collect the `.par` file path, output directory, and any parameter overrides.
2. Call the patch-and-run script:
   ```
   python ~/.agents/skills/fargo3d/scripts/run_fargo3d.py \
       --json '{"par_file": "setups/p_gap/p_gap.par", "output_dir": "out/run01",
                "Alpha": 1e-3, "PlanetMass": 3e-4, "Tmax": 200}'
   ```
   Individual flags:
   ```
   python ~/.agents/skills/fargo3d/scripts/run_fargo3d.py \
       --par-file setups/p_gap/p_gap.par --output-dir out/run01 \
       --Alpha 1e-3 --PlanetMass 3e-4 --Tmax 200
   ```
3. The script writes a patched `.par` to `output_dir`, launches `fargo3d`,
   and parses the final gas density and planet torque outputs.
4. Parse `SUCCESS:` / `ERROR:` prefix.

## Parameters

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `par_file` | str | **required** | must exist | Path to `.par` setup file |
| `output_dir` | str | **required** | — | Where FARGO3D writes `gasdens*.dat` etc. |
| `AspectRatio` | float | (from par) | (0, 1] | Disk scale-height ratio h/r |
| `Sigma0` | float | (from par) | > 0 | Surface density at 1 au (code units) |
| `Alpha` | float | (from par) | [0, 0.1] | Alpha-viscosity |
| `FlaringIndex` | float | (from par) | [0, 1] | Disk flaring index |
| `PlanetMass` | float | (from par) | ≥ 0 | Planet mass in stellar masses |
| `Tmax` | float | (from par) | > 0 | Max time in orbital periods |
| `Ninterm` | int | (from par) | ≥ 1 | Output cadence (steps between outputs) |
| `DT` | float | (from par) | > 0 | Time-step per orbit fraction |
| `Nx` | int | (from par) | [8, 4096] | Azimuthal resolution |
| `Ny` | int | (from par) | [8, 1024] | Radial resolution |
| `extra_params` | dict | `{}` | — | Any other `.par` key-value pairs |
| `fargo3d_bin` | str | `./fargo3d` | — | Path to FARGO3D executable |
| `n_procs` | int | 1 | [1, 512] | MPI rank count (CPU runs) |
| `gpu` | bool | False | — | Use GPU flag (`-m` instead of `-0`) |

## Output

```
SUCCESS: output_dir=<path>  wall_clock=<N>s
  n_outputs=<N>  last_orbit=<val>
  Sigma_min=<val>  Sigma_max=<val>  gap_depth=<frac>
  planet_torque=<val> (last output)
```

`gap_depth` = Σ_min / Σ_unperturbed (lower = deeper gap).

## Common Errors

| Message | Fix |
|---|---|
| `par_file not found` | Check path relative to working directory |
| `fargo3d binary not found` | Check `fargo3d_bin`; compile with `make` in FARGO3D root |
| `output_dir is required` | Always supply an explicit output directory |
| `Sigma0 must be > 0` | Provide a positive surface density value |
| `scientific_pydantic not found` | `pip install scientific-pydantic` |
| `MPI launch failed` | Check `mpirun` on PATH; try `n_procs=1` |
