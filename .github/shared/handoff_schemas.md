# Handoff Schemas

Structured JSON schemas for data passed between specialist agents.
Reference: [`ARCHITECTURE.md`](../../ARCHITECTURE.md).

---

## Conventions

- All string fields use angle-bracket placeholders: `"<description>"`.
- `"<bool>"` means the literal JSON booleans `true` or `false` (not a string).
- `"<int>"` and `"<float>"` mean JSON numbers of the appropriate type.
- **`[DATA MISSING]`** is the required sentinel string for any field that cannot
  be populated from actual data in the current session. Never invent values.
  A handoff containing `[DATA MISSING]` is valid to emit but the receiving agent
  must not proceed past a blocking `[DATA MISSING]` without human intervention.
- All handoffs carry a `timestamp` field (ISO-8601 UTC). Populate at write time:
  `datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")`.

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
  "debate_rounds": "<int>",
  "human_gate_1_confirmed": "<bool>",
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `hypotheses` must contain at least 1 and at most 5 entries.
- Every hypothesis must have at least 1 `predicted_observables` entry with units
  in the parseable format `"<name>: <value_or_range> [unit]"`.
- Every hypothesis must have at least 1 `literature_refs` ADS bibcode retrieved
  via `@literature-agent` in the same session.
- `domain` must match one of the five supported values exactly.
- `top_hypothesis_id` must equal `priority_rank[0]`.
- `human_gate_1_confirmed` must be `true` before `@analytical-agent` consumes
  this handoff. Emit as `false`; update to `true` after explicit user confirmation.

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
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
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
  "code": "<PLUTO | FARGO3D | DustPy | Magneticum | GADGET>",
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
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `validated` must be `true` before handing off. If physics sanity checks fail, stop.
- If `hpc_mode: true`, `slurm_script_path` must be non-null and the script must exist.
- `run_cmd` must be null when `hpc_mode: true` (never run locally and on HPC simultaneously).
- `code_version` must not be the string `"unknown"` — read from the environment.
- `petitRADTRANS` and `Sherpa` are **not** valid `code` values here; retrieval agents
  use no config handoff, and spectral fitting emits `SpectralFitHandoff/v1` directly.

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
  "simulation_ref": "<string | null — path to SimulationHandoff JSON; null only if simulation was external or pre-existing>",
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
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `sanity_passed` must be `true` before handing off to `@interpretation-agent`.
  If `false`, the agent must report the failure and stop.
- `plot_paths` must be non-empty; each path must exist on disk.
- `data_hash` must be computed from actual output files (not predicted).
- `simulation_ref` should be non-null whenever the analysis agent ran against a
  `SimulationHandoff`-producing code; the receiving agent uses it to resolve
  `output_dir` and `output_files`.
- `analytical_comparison` must be populated (non-empty) when `simulation_ref`
  is non-null and an `AnalyticalHandoff` was available upstream; may be `{}`
  otherwise (not silently omitted).

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
  "next_action": "<iterate | write | mcmc | stop | abort>",
  "abort_reason": "<string | null — required when next_action is abort>",
  "human_gate_2_confirmed": "<bool>",
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `human_gate_2_confirmed` must be `true` before the user makes a final decision.
- `plausibility_flags` must be empty or explicitly acknowledged by the user before stopping work.
- `findings` must contain at least 1 entry with `literature_refs`.
- `hypothesis_match: refuted` requires `next_action: iterate` or `abort`.
  Never stop on refuted hypotheses without iteration or explicit abort.
- `next_action: abort` requires a non-null `abort_reason` and triggers writing
  `results/<task_id>/abort_report.json` (see pipeline-agent Stage 9 abort path).

---

## SimulationHandoff/v1

Emitted by `@simulation-agent` after a successful simulation run or analysis.
Consumed by `@spectral-agent` or `@mcmc-agent`.

```json
{
  "schema": "SimulationHandoff/v1",
  "task_id": "<string — snake_case label matching prompts/ log>",
  "run_dir": "<string — absolute path to run directory>",
  "run_manifest": "<string — absolute path to run_manifest.json>",
  "code": "<FARGO3D | PLUTO | DustPy | Magneticum>",
  "code_version": "<string — git hash or release tag; read from skill envelope>",
  "skill_script": "<string — absolute path to skill script used>",
  "skill_script_version": "<string — read from physics_config.md, sysconf.out, or git describe; never 'unknown'>",
  "param_file": "<string — absolute path to main config / par / setup file>",
  "param_file_md5": "<string — MD5 hex of param_file at launch time>",
  "output_dir": "<string — directory containing output files>",
  "output_files": ["<string — absolute paths verified readable by emitting agent>"],
  "diagnostics": {
    "n_snapshots": "<int>",
    "last_snap": "<int>",
    "t_end_code": "<float — final time in code units>",
    "rho_field": "<string — name of density field, e.g. 'gasdens' | 'rho' | 'Sigma_gas'>",
    "rho_units": "<string — code units of rho_max/rho_min, e.g. 'M_sun/AU^2'>",
    "rho_max": "<float — in rho_units>",
    "rho_min": "<float — in rho_units>",
    "wall_clock_s": "<float>"
  },
  "units": {
    "length": "<string — e.g. 'AU'>",
    "mass":   "<string — e.g. 'M_sun'>",
    "time":   "<string — e.g. 'yr'>",
    "density":"<string — e.g. 'M_sun/AU^2' for FARGO3D surface density>"
  },
  "sanity_passed": "<bool>",
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
  "warnings": ["<string — collected [SANITY WARN] messages from analysis step 4>"]
}
```

**Validation rules:**
- `sanity_passed` must be `true` before handing off to a downstream agent.
  If `false`, the agent must report the failure and stop.
- `warnings` should be empty or contain only non-blocking advisories.
- `output_files` must contain only absolute paths that have been verified readable
  (using `os.access(p, os.R_OK)`) in the **emitting** agent's session.
- `code_version` must not be the string `"unknown"` — read from `physics_config.md`,
  `sysconf.out`, or `git describe` in the code source tree.
- `skill_script_version` must not be `"unknown"` — same sources as `code_version`.
- `rho_units` must be explicitly populated — never leave it as `"unknown"`.
  Use the per-code convention table in `simulation-agent.agent.md § step 5`.
- `run_manifest` path must exist on disk; if absent, emit `[DATA MISSING: run_manifest.json]`.

---

## SpectralFitHandoff/v1

Emitted by `@spectral-agent` after a converged spectral fit.
Consumed by `@mcmc-agent` for posterior refinement.

```json
{
  "schema": "SpectralFitHandoff/v1",
  "spectrum_file": "<string — path to .pha or .fits>",
  "background_file": "<string | null>",
  "energy_range_keV": ["<float — low keV>", "<float — high keV>"],
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
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
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
  "seed": "<int — random seed passed to sampler; must match the 'seed' attribute stored in chain_file>",
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `converged` must be `true` before reporting results.
  Gelman–Rubin R̂ < 1.1 for all parameters is the minimum threshold.
- Uncertainties are **68 % credible intervals** (1σ equivalent).
  Never report 90 % intervals unless the user explicitly requests them.
- `corner_plot` must exist on disk before emitting this handoff.
- `seed` must be explicitly set and logged. Default: `42` (see `AGENTS.md` rule 6).
  The same value must be stored as an HDF5 attribute in `chain_file`.

---

## PaperHandoff/v1

Emitted by `@paper-agent` after a manuscript draft is compiled and auto-reviewed.
Returned to the user (or `@pipeline-agent` for logging).

```json
{
  "schema": "PaperHandoff/v1",
  "task_id": "<string>",
  "domain": "<disk | cosmological | retrieval | xray | lss>",
  "paper_dir": "<string — e.g. 'paper/gap_depth_1mjup_20260528/'>",
  "manuscript_tex": "<string — path to manuscript.tex>",
  "manuscript_pdf": "<string | null — null if compilation failed>",
  "bibliography_bib": "<string — path to .bib file, e.g. 'paper/bibliography.bib'>",
  "new_bibtex_keys": ["<string — ADS bibcode of entries added this session>"],
  "sections_written": [
    "abstract", "introduction", "methods", "results", "discussion", "conclusions"
  ],
  "n_figures": "<int>",
  "n_citations": "<int — entries added to bibliography this session>",
  "compilation_status": "<ok | errors>",
  "latex_errors": ["<string — verbatim pdflatex error lines>"],
  "todo_count": "<int — number of \\todo{} markers remaining>",
  "referee_report": "<string — path to referee_notes.md>",
  "referee_score": "<float 0–9>",
  "timestamp": "<ISO-8601 UTC string — when this handoff was written>",
  "warnings": ["<string>"]
}
```

**Validation rules:**
- `compilation_status: ok` requires `manuscript_pdf` to be non-null and the PDF to exist.
- `todo_count` must be 0 for a clean handoff; non-zero values require a warning.
- `referee_score < 5` requires a human review before the paper is considered ready.
- `new_bibtex_keys` must each be a valid ADS bibcode format
  (e.g. `2016A&A...594A.116H`), not a DOI or arXiv ID.
- `n_figures` must equal the number of `\includegraphics` calls in the compiled PDF.
