---
layout: page
title: Agents
nav_order: 2
---

# Specialist Agents

Each agent is a `.agent.md` file in `.github/agents/` that you invoke by name
in Copilot Chat or Agent Mode. Agents extend the group baseline in
`.github/copilot-instructions.md` with domain-specific workflows, code patterns,
and sanity checks.

---

## `@literature-agent`

Searches NASA ADS, retrieves BibTeX entries, and appends them to
`paper/bibliography.bib`. Uses the ADS MCP server; **never invents references**.

```
@literature-agent  Find all papers citing 2025A&A...703A.270R since 2025
                   and add them to paper/bibliography.bib
```

---

## `@simulation-agent`

Launches and post-processes hydrodynamical simulations from DustPy,
FARGO3D, PLUTO, and Magneticum/GADGET. Provides:
- **Simulation launching** via bundled skill scripts (DustPy, FARGO3D, PLUTO)
  with Pydantic-validated parameters and `SUCCESS` / `ERROR` exit protocol
- FARGO3D HDF5 and legacy binary `.dat` readers with code-unit → physical-unit conversion
- Magneticum/GADGET HDF5 reader with complete unit conversion table
- GadgetIO.jl subprocess call pattern
- Sanity checks: gap depth floors, planetary torque sign conventions,
  halo mass / ICM temperature ranges

Large code blocks (I/O functions, argparse skeleton, HDF5 saving pattern)
are extracted to [`.github/agents/references/`](.github/agents/references/):
- `output_conventions.md` — `read_fargo_field()`, `read_fargo_dat()`, `read_gadget_snap()`, `GADGET_UNITS`
- `code_conventions.md` — standard script skeleton, HDF5 saving, diagnostic figure naming

Handoff schema after a completed analysis: `SimulationHandoff/v1`
(see [`.github/shared/handoff_schemas.md`](.github/shared/handoff_schemas.md)).

```
@simulation-agent  Run a DustPy dust evolution simulation with alpha=1e-3,
                   disk mass 0.05 Msun, for 1 Myr. Save snapshots to data/dustpy/.

@simulation-agent  Read all FARGO3D snapshots in data/runs/disk_1Mjup/
                   and compute the azimuthally averaged gap depth as a
                   function of time for planet 0. Save to results/gaps/.

@simulation-agent  Load the Magneticum Box2/hr snapshot at z=0 and plot
                   the projected gas temperature map centred on the most
                   massive cluster. Save to plots/cosmo/.
```

---

## `@retrieval-agent`

Atmospheric retrievals for exoplanets observed with CARMENES, CRIRES+, and JWST.
Provides:
- petitRADTRANS Guillot 2010 T-P profile + `Radtrans` forward model skeleton
- CCF pipeline with `scipy.signal.correlate` and S/N-map normalisation
- `dynesty.DynamicNestedSampler` wrapper with convergence checks
- Mandatory sanity checks: CCF peak S/N > 3, RV offset ≤ 30 km/s from systemic,
  posterior unimodality test
- Output schema: HDF5 with species list, log-evidence, posterior samples,
  instrument metadata

```
@retrieval-agent   Run a petitRADTRANS CCF pipeline on
                   data/spectra/obs/wasp189b_K.fits using CO and H2O
                   templates. Parameters are in AGENTS.md.

@retrieval-agent   Execute a dynesty retrieval for WASP-189b (emission,
                   K-band) with nlive=500. Use the forward model in
                   src/analysis/retrieval.py.
```

---

## `@spectral-agent`

X-ray spectral fitting with Sherpa and PyXSPEC for XMM-Newton,
Chandra, and eROSITA data.

```
@spectral-agent    Fit an absorbed APEC model to data/spectra/core/
                   using the parameters in AGENTS.md
```

---

## `@mcmc-agent`

General-purpose MCMC runner for emcee and dynesty, with corner plots
and convergence diagnostics.

```
@mcmc-agent        Sample posteriors for the core region fit in
                   results/fits/core.json and produce a corner plot
```

---

## Research pipeline agents

The following seven agents together form the full 10-stage research pipeline
coordinated by `@pipeline-agent`. Three mandatory **human gates** prevent
automated progression without explicit user confirmation.

### `@pipeline-agent`

Full research pipeline orchestrator — runs a complete science workflow from
question to manuscript preparation. Coordinates all 13 agents in the correct
order, enforces all three human gates, creates prompt logs in `prompts/`, and
tracks pipeline stages via a live todo list.

```
@pipeline-agent    Investigate gap opening by a 1 MJup planet in a
                   protoplanetary disk around a 1 Msun star.
                   Target journal: A&A. HPC mode: SLURM on LRZ.

@pipeline-agent    Analyse thermodynamic structure of the Perseus cluster
                   core using XMM-Newton EPIC-pn data in data/spectra/.
                   Target journal: A&A. HPC mode: none.
```

---

### `@hypothesis-agent`

Generates and ranks testable scientific hypotheses via a three-round
internal debate (novelty + feasibility scoring). Requires `@literature-agent`
for bibliography support. Concludes with **Human Gate 1** — asks the user to
confirm the top hypothesis before passing to `@analytical-agent`.

```
@hypothesis-agent  Generate hypotheses for how planet mass affects
                   gap depth in dusty protoplanetary disks.
                   Domain: disk.

@hypothesis-agent  What mechanisms could explain the unusually low
                   ICM entropy in the Perseus cool core?
                   Domain: xray.
```

Output: `results/hypotheses/<task_id>_<date>.json` — `HypothesisHandoff/v1`.

---

### `@analytical-agent`

Performs analytical/linear/perturbative pre-analysis for a specific domain.
Computes characteristic scales (Hill radius, Jeans mass, scale height, …),
stability criteria (Crida K, Toomre Q, …), and linear-regime predictions.
Determines whether the problem is in the linear regime or requires nonlinear
simulation and why. Benchmark results are saved as a Python script for later
comparison against numerical output.

Supported domains and key quantities:
- **disk**: Hill radius, Crida K, type-I migration timescale, Stokes number, fragmentation barrier
- **cosmological**: virial temperature, Jeans mass, cooling time, NFW profile
- **retrieval**: scale height, transit depth amplitude, equilibrium temperature
- **xray**: emission measure, hydrostatic mass, sound crossing time
- **lss**: Fisher matrix, linear growth rate, transfer function

```
@analytical-agent  Compute analytical benchmarks for a 1 MJup planet
                   opening a gap in a disk with alpha=1e-3. Domain: disk.
                   HypothesisHandoff: results/hypotheses/gap_depth_20260601.json

@analytical-agent  Estimate the virial temperature and cooling time for
                   a galaxy cluster with M200=5e14 Msun at z=0.1.
                   Domain: xray.
```

Output: `results/analytical/<task_id>_<date>.json` + `<task_id>_<date>.py` — `AnalyticalHandoff/v1`.

---

### `@setup-agent`

Translates an `AnalyticalHandoff` into validated simulation configuration files
for any supported code, plus optional SLURM or PBS job scripts. Never submits
jobs automatically — only generates scripts for user review.

Supported codes: PLUTO, FARGO3D, DustPy, GADGET, petitRADTRANS, Sherpa.
Scheduler support: SLURM (`#SBATCH`) and PBS/Torque (`#PBS`).

```
@setup-agent   Create a FARGO3D parameter file for the gap-opening run.
               AnalyticalHandoff: results/analytical/gap_depth_20260601.json
               HPC mode: SLURM, 4 nodes × 32 cores, 48 h, LRZ SuperMUC-NG.

@setup-agent   Create a DustPy configuration and a PBS script for
               data/runs/ring_dust/ with the parameters from AGENTS.md.
               No HPC mode (local run).
```

Output: `data/runs/<task_id>/<code>.cfg` + (optional) `submit.sh` — `SimConfigHandoff/v1`.

---

### `@analysis-agent`

Post-processes simulation outputs for any domain, computes domain-specific
diagnostic metrics, generates publication-quality figures, and compares
numerical results against the analytical benchmarks from `AnalyticalHandoff`.

Domain diagnostics:
- **disk**: gap depth, Σ(R), planet torque, dust-to-gas ratio, max grain size
- **cosmological**: temperature/density projections via `yt`, FITS output
- **xray**: fit residuals, confidence contours, temperature maps, cooling time maps
- **retrieval**: CCF S/N map, T-P profile, mixing ratios
- **lss**: P(k) vs. linear theory, posterior corner plots

```
@analysis-agent  Post-process data/runs/disk_1Mjup/ at snapshot 200.
                 SimConfigHandoff: results/configs/gap_depth_20260601.json
                 AnalyticalHandoff: results/analytical/gap_depth_20260601.json

@analysis-agent  Fit XMM spectra in data/spectra/core/ and compare
                 temperatures with the analytical cooling-time benchmark.
```

Output: figures in `plots/`, `results/analysis/<task_id>_<date>.json` — `AnalysisHandoff/v1`.

---

### `@interpretation-agent`

Physical interpretation of numerical results. Cross-checks findings against
analytical theory and ADS literature (`@literature-agent` required).
Performs domain-specific physical plausibility checks. Decides next action
(`iterate | write | stop`) and enforces **Human Gate 2** — asks the user to
confirm before finalizing the decision.

```
@interpretation-agent  Interpret the gap depth results from
                        results/analysis/gap_depth_20260601.json.
                        AnalysisHandoff: results/analysis/gap_depth_20260601.json
                        AnalyticalHandoff: results/analytical/gap_depth_20260601.json

@interpretation-agent  Interpret the ICM temperature structure in the
                        Perseus cool core fit. Compare with the analytical
                        cooling time estimate.
```

Output: `results/interpretation/<task_id>_<date>.json` — `InterpretationHandoff/v1`.

---

### `@paper-agent`

Drafts a full scientific manuscript (LaTeX + PDF) from an `InterpretationHandoff`.
Writes sections sequentially (abstract → introduction → methods → results →
discussion → conclusions), passing each section as context to the next for
coherence. Inserts ADS-verified citations via `@literature-agent`. Compiles
LaTeX to PDF and produces an automated referee report scored 0–9.

Key constraints: numbers sourced exclusively from `AnalysisHandoff`; every
citation ADS-verified; LaTeX must compile before `PaperHandoff/v1` is emitted;
all claims cross-checked against `AnalysisHandoff.diagnostics`.

```
@paper-agent   Draft the manuscript for the gap-depth study.
               InterpretationHandoff: results/interpretation/gap_depth_20260526.json

@paper-agent   Draft the manuscript for the Perseus cluster X-ray analysis.
               InterpretationHandoff: results/interpretation/perseus_xray_20260601.json
```

Output: `paper/<task_id>_<date>/manuscript.pdf` + `referee_notes.md` — `PaperHandoff/v1`.

---

### `@referee-agent`

Independent scientific peer reviewer — evaluates a compiled manuscript for
**form** (structure, figures, clarity), **scientific soundness** (methods
valid, results match diagnostics, statistics appropriate), and **novelty**
relative to the ADS literature. Issues a journal-style recommendation
(`accept` / `minor_revision` / `major_revision` / `reject`) and enforces
**Human Gate 3**.

Key constraints: every novelty judgment is ADS-backed (bibcode retrieved this
session); soundness judged against `AnalysisHandoff.diagnostics`, not prose;
never recommend `accept` while `major_comments` is non-empty; never pre-populate
`human_gate_3_confirmed`. On `revise`, routes the manuscript back to
`@paper-agent` in revision mode (bounded loop: warns at `revision_round` = 2).

```
@referee-agent   results/paper/gap_depth_1mjup_20260601.json
```

Output: `results/referee/<task_id>_referee_<date>.json` + `referee_review.md` — `RefereeHandoff/v1`.

See [`ARCHITECTURE.md`](https://github.com/giovannipicogna/lmu-usm-agent-template/blob/main/ARCHITECTURE.md)
for the full pipeline diagram, agent roster, handoff schemas, and quality-gate
summary. The three anti-failure mechanisms below are embedded directly in
each agent file.

All analysis agents include three anti-failure mechanisms to prevent
silent hallucination in long sessions:

### Iron rules
Blockquoted `IRON RULE` markers in each agent file flag non-negotiable
constraints. Examples:

| Agent | Critical rules |
|---|---|
| `@simulation-agent` | No hallucinated numbers; read-only by default; test one snapshot before batch |
| `@spectral-agent` | No hallucinated fit results; C-stat on low-count data; model changes need confirmation |
| `@mcmc-agent` | Report 68% credible intervals (not 90%); never overwrite chain files; convergence check before reporting |
| `@paper-agent` | Numbers from `AnalysisHandoff` only; all citations ADS-verified; LaTeX must compile; claims cross-checked against diagnostics |
| `@retrieval-agent` | No species detection without a shuffled-template null test; species list from `AGENTS.md`; ΔlogZ < 0.1 before reporting |

### Anti-patterns tables
Each agent carries a four-row table — *Anti-Pattern \| Why It Fails \|
Correct Behaviour* — providing explicit negative examples at inference
time for the most common failure modes.

### Anti-leakage (`[DATA MISSING]`)
If data required for analysis is absent from the current session, agents
emit `[DATA MISSING: <description>]` and stop rather than substituting
values from training memory. `@literature-agent` uses the variant
`[CITATION MISSING: <query>]` when ADS returns no result.
