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
   Read `references/parameters.md` for the full parameter table.
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

> Full table with types, defaults, and constraints: [`references/parameters.md`](references/parameters.md)

**Required:** `par_file`, `output_dir`
**Disk structure:** `AspectRatio` · `Sigma0` · `Alpha` · `FlaringIndex`
**Planet:** `PlanetMass`
**Time integration:** `Tmax` · `DT` · `Ninterm`
**Execution:** `fargo3d_bin` · `n_procs` · `gpu`
Use `extra_params: {"Key": value}` for any other `.par` entry.

## Source as context

**Ground parameter names, setups, and defaults in the actual FARGO3D checkout —
never recall them from training memory.** Parameter spellings, available setups,
and boundary-condition names differ between FARGO3D versions; a hallucinated
`.par` key is silently ignored by the code and your override never takes effect.
Before writing or patching a `.par`, grep the checkout (`$FARGO_ROOT`, read from
`AGENTS.md`):

```bash
# Available setups (the <setup>.par you can target)
ls "$FARGO_ROOT/setups/"

# Confirm a parameter exists and read its default for THIS setup
grep -n -i "Alpha\|Sigma0\|AspectRatio\|FlaringIndex" \
    "$FARGO_ROOT/setups/p_gap/p_gap.par"

# C ↔ .par variable bindings and compiled defaults (authoritative)
grep -rn "Alpha\|Sigma0\|PlanetMass" "$FARGO_ROOT/src/var.c"

# Valid boundary-condition labels for this setup
sed -n '1,40p' "$FARGO_ROOT/setups/p_gap/p_gap.bound" 2>/dev/null
```

A grepped fact from the checkout **overrides** any value in
`references/parameters.md` or model memory. If `$FARGO_ROOT` is unset or the key
is absent from the setup's `.par`, stop and emit
`[DATA MISSING: parameter <name> not found in <setup>.par]` rather than guessing.

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

---

## Mandatory workflow

For every FARGO3D task, follow this sequence:

1. **Confirm** the `.par` file path and output directory before launching.
2. **Read `references/parameters.md`** to verify parameter names and valid ranges.
3. **Patch** parameters via the run script — never edit `.par` files by hand.
4. **Sanity-check** `Sigma_min`, `Sigma_max`, and `gap_depth` from the `SUCCESS:` output.
5. **Emit `SimulationHandoff/v1`** after a successful run.

---

## Iron rules

- Never hardcode physical values — read them from `references/parameters.md`.
- Do **not** use this skill to change compile-time flags (`NFLUIDS`, `MHD`, etc.) — those require recompilation.
- Always supply an explicit `output_dir`; never let outputs overwrite an existing run directory without user confirmation.
- `Sigma0 > 0` and `AspectRatio > 0` are non-negotiable; reject runs with zero or negative values.
- Never submit HPC jobs without explicit user confirmation.
