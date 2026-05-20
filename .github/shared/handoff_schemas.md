# Handoff Schemas

Structured JSON schemas for data passed between specialist agents.
Reference: [`ARCHITECTURE.md`](../../ARCHITECTURE.md).

---

## SimulationHandoff/v1

Emitted by `@simulation-agent` after a successful simulation run or analysis.
Consumed by `@spectral-agent` or `@mcmc-agent`.

```json
{
  "schema": "SimulationHandoff/v1",
  "run_dir": "<string — absolute path to run directory>",
  "code": "<FARGO3D | PLUTO | DustPy | Magneticum>",
  "code_version": "<string — git hash or release tag>",
  "output_dir": "<string — directory containing output files>",
  "output_files": ["<string>"],
  "diagnostics": {
    "n_snapshots": "<int>",
    "last_snap": "<int>",
    "t_end_code": "<float — final time in code units>",
    "rho_max": "<float — code units>",
    "rho_min": "<float — code units>",
    "wall_clock_s": "<float>"
  },
  "units": {
    "length": "<string — e.g. 'AU'>",
    "mass":   "<string — e.g. 'M_sun'>",
    "time":   "<string — e.g. 'yr'>"
  },
  "sanity_passed": "<bool>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `sanity_passed` must be `true` before handing off to a downstream agent.
  If `false`, the agent must report the failure and stop.
- `warnings` should be empty or contain only non-blocking advisories.
- `output_files` paths must be accessible from the receiving agent's working directory.

---

## SpectralFitHandoff/v1

Emitted by `@spectral-agent` after a converged spectral fit.
Consumed by `@mcmc-agent` for posterior refinement.

```json
{
  "schema": "SpectralFitHandoff/v1",
  "spectrum_file": "<string — path to .pha or .fits>",
  "background_file": "<string | null>",
  "energy_range_keV": [0.5, 7.0],
  "model": "<string — e.g. 'TBabs*apec'>",
  "best_fit": {
    "<param_name>": {
      "value": "<float>",
      "unit":  "<string>",
      "frozen": "<bool>"
    }
  },
  "fit_statistic": {
    "stat":  "<cstat | chi2 | wstat>",
    "value": "<float>",
    "dof":   "<int>"
  },
  "fit_passed_sanity": "<bool>",
  "parameter_grid": "<string | null — path to JSON grid file for MCMC>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `fit_passed_sanity` must be `true`; otherwise `@mcmc-agent` must refuse and report.
- For counts < 25 per bin, `stat` must be `cstat` — never `chi2`.
- `parameter_grid` is required when handing off to `@mcmc-agent`.

---

## MCMCHandoff/v1

Emitted by `@mcmc-agent` after convergence is confirmed.
Returned to `@paper-agent` or the user.

```json
{
  "schema": "MCMCHandoff/v1",
  "chain_file": "<string — path to .h5 emcee chain or dynesty .pkl>",
  "sampler": "<emcee | dynesty>",
  "n_walkers": "<int>",
  "n_steps": "<int>",
  "burn_in": "<int>",
  "converged": "<bool>",
  "gelman_rubin_max": "<float — worst R-hat across parameters>",
  "medians": {
    "<param_name>": "<float>"
  },
  "uncertainties_68": {
    "<param_name>": ["<float — -1sigma>", "<float — +1sigma>"]
  },
  "corner_plot": "<string — path to PDF or PNG>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `converged` must be `true` before reporting results.
  Gelman–Rubin R̂ < 1.1 for all parameters is the minimum threshold.
- Uncertainties are **68 % credible intervals** (1σ equivalent).
  Never report 90 % intervals unless the user explicitly requests them.
- `corner_plot` must exist on disk before emitting this handoff.
