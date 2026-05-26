# Handoff Schemas

Structured JSON schemas for data passed between specialist agents.
Reference: [`ARCHITECTURE.md`](../../ARCHITECTURE.md).

---

## HypothesisHandoff/v1

Emitted by `@hypothesis-agent` after a completed three-round debate.
Consumed by `@analytical-agent`.

```json
{
  "schema": "HypothesisHandoff/v1",
  "science_goal": "<string — user's exact research question>",
  "domain": "<disk | cosmological | retrieval | xray | lss>",
  "hypotheses": [
    {
      "id": "<int>",
      "description": "<string — one-sentence physical mechanism>",
      "predicted_observables": ["<string — quantity with units>"],
      "parameters": {
        "<name>": {"value_or_range": "<string>", "unit": "<string>"}
      },
      "novelty_score": "<float 0–1>",
      "feasibility_score": "<float 0–1>",
      "literature_refs": ["<ADS bibcode>"]
    }
  ],
  "priority_rank": ["<int — hypothesis id ordered by priority>"],
  "top_hypothesis_id": "<int>",
  "debate_rounds": 3,
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `hypotheses` must contain at least 1 and at most 5 entries.
- Every hypothesis must have at least 1 `predicted_observables` entry with units.
- Every hypothesis must have at least 1 `literature_refs` ADS bibcode retrieved
  via `@literature-agent` in the same session.
- `domain` must match one of the five supported values exactly.

---

## AnalyticalHandoff/v1

Emitted by `@analytical-agent` after domain-specific analytical pre-analysis.
Consumed by `@setup-agent`.

```json
{
  "schema": "AnalyticalHandoff/v1",
  "domain": "<disk | cosmological | retrieval | xray | lss>",
  "science_goal": "<string>",
  "hypothesis_ref": "<int — top_hypothesis_id from HypothesisHandoff>",
  "characteristic_scales": {
    "<name>": {
      "value": "<float>",
      "unit": "<string>",
      "formula": "<string — e.g. 'r_H = a*(q/3)^(1/3)'>",
      "ref_bibcode": "<string | null>"
    }
  },
  "stability_criteria": [
    {
      "name": "<string>",
      "criterion": "<string — expression and threshold>",
      "satisfied": "<bool>",
      "margin": "<float — how far from the threshold>",
      "ref_bibcode": "<string>"
    }
  ],
  "predicted_observables": [
    {
      "name": "<string>",
      "value": "<float>",
      "unit": "<string>",
      "uncertainty": "<float>",
      "formula_ref": "<string>"
    }
  ],
  "linear_regime": "<bool>",
  "nonlinear_trigger": "<string | null — description of why linear theory breaks down>",
  "parameter_recommendations": {
    "<param>": "<string — recommended value or range with justification>"
  },
  "benchmark_script": "<string | null — path to .py evaluation script>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `linear_regime: false` requires a non-null `nonlinear_trigger`.
- `characteristic_scales` must include at least 2 entries.
- `stability_criteria` must include at least 1 entry.
- `predicted_observables` must correspond to `HypothesisHandoff.hypotheses[hypothesis_ref].predicted_observables`.

---

## SimConfigHandoff/v1

Emitted by `@setup-agent` after simulation configuration and optional HPC script generation.
Consumed by `@simulation-agent`, `@retrieval-agent`, or `@spectral-agent`.

```json
{
  "schema": "SimConfigHandoff/v1",
  "domain": "<disk | cosmological | retrieval | xray | lss>",
  "task_id": "<string — snake_case label>",
  "hypothesis_ref": "<int>",
  "analytical_ref": "<string | null — path to AnalyticalHandoff JSON>",
  "code": "<PLUTO | FARGO3D | DustPy | petitRADTRANS | Sherpa | GADGET>",
  "code_version": "<string — git hash or release tag; read from environment>",
  "config_path": "<string — absolute path to main config file>",
  "physics_params": {},
  "skill_invoked": "<string | null — path to skill script used>",
  "hpc_mode": "<bool>",
  "slurm_script_path": "<string | null>",
  "scheduler": "<slurm | pbs | null>",
  "n_cores": "<int>",
  "walltime_h": "<float>",
  "run_cmd": "<string | null — local run command; null if hpc_mode>",
  "validated": "<bool>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `validated` must be `true` before handing off. If physics sanity checks fail, stop.
- If `hpc_mode: true`, `slurm_script_path` must be non-null and the script must exist.
- `run_cmd` must be null when `hpc_mode: true` (never run locally and on HPC simultaneously).
- `code_version` must not be the string `"unknown"` — read from the environment.

---

## AnalysisHandoff/v1

Emitted by `@analysis-agent` after post-processing simulation outputs.
Consumed by `@interpretation-agent` or `@mcmc-agent`.

```json
{
  "schema": "AnalysisHandoff/v1",
  "domain": "<disk | cosmological | retrieval | xray | lss>",
  "task_id": "<string>",
  "output_dir": "<string>",
  "sim_config_ref": "<string — path to SimConfigHandoff JSON>",
  "diagnostics": {
    "<key>": {"value": "<float>", "unit": "<string>", "snapshot": "<int | null>"}
  },
  "plot_paths": ["<string>"],
  "data_hash": "<string — SHA256 of primary output file(s)>",
  "analytical_comparison": {
    "<metric>": {
      "analytical": "<float>",
      "numerical": "<float>",
      "unit": "<string>",
      "agreement_pct": "<float>"
    }
  },
  "sanity_passed": "<bool>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `sanity_passed` must be `true` before handing off to `@interpretation-agent`.
  If `false`, the agent must report the failure and stop.
- `plot_paths` must be non-empty; each path must exist on disk.
- `data_hash` must be computed from actual output files (not predicted).
- `analytical_comparison` must be populated if an `AnalyticalHandoff` was available.

---

## InterpretationHandoff/v1

Emitted by `@interpretation-agent` after physical interpretation and Human Gate 2.
Consumed by `@hypothesis-agent` (if `next_action: iterate`) or directly returned to user
(if `next_action: stop`).

```json
{
  "schema": "InterpretationHandoff/v1",
  "domain": "<disk | cosmological | retrieval | xray | lss>",
  "task_id": "<string>",
  "science_goal": "<string>",
  "findings": [
    {
      "statement": "<string>",
      "evidence": "<string — refers to AnalysisHandoff diagnostic key>",
      "confidence": "<high | medium | low>",
      "literature_refs": ["<ADS bibcode>"]
    }
  ],
  "hypothesis_match": "<confirmed | partial | refuted>",
  "analytical_agreement_summary": "<string>",
  "plausibility_flags": ["<string>"],
  "caveats": ["<string>"],
  "followup_suggestions": ["<string>"],
  "next_action": "<iterate | write | stop>",
  "human_gate_2_confirmed": "<bool>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `human_gate_2_confirmed` must be `true` before the user makes a final decision.
- `plausibility_flags` must be empty or explicitly acknowledged by the user before stopping work.
- `findings` must contain at least 1 entry with `literature_refs`.
- `hypothesis_match: refuted` requires `next_action: iterate` or `stop`.
  Never stop on refuted hypotheses without iteration.

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
Returned to the user or `@hypothesis-agent` for iteration.

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
