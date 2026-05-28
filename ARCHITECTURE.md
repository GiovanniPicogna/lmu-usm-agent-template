# Architecture — LMU USM Agent Template

This document is the **single source of truth** for how agents interact,
what data flows between them, and what quality gates govern each stage.

---

## Agent roster

### Research pipeline agents (new)

| Agent | File | Role | Handoff schema |
|---|---|---|---|
| `@pipeline-agent` | `pipeline-agent.agent.md` | Full 9-stage research pipeline orchestrator; enforces both human gates | — |
| `@hypothesis-agent` | `hypothesis-agent.agent.md` | Science question → ranked testable hypotheses via 3-round internal debate | [`HypothesisHandoff/v1`](.github/shared/handoff_schemas.md#hypothesishandoffv1) |
| `@analytical-agent` | `analytical-agent.agent.md` | Analytical / linear / perturbative pre-analysis; benchmarks for simulation comparison | [`AnalyticalHandoff/v1`](.github/shared/handoff_schemas.md#analyticalhandoffv1) |
| `@setup-agent` | `setup-agent.agent.md` | Translate `AnalyticalHandoff` to validated simulation configs + optional SLURM/PBS scripts | [`SimConfigHandoff/v1`](.github/shared/handoff_schemas.md#simconfighandoffv1) |
| `@analysis-agent` | `analysis-agent.agent.md` | Post-process simulation outputs + compare against analytical benchmarks | [`AnalysisHandoff/v1`](.github/shared/handoff_schemas.md#analysishandoffv1) |
| `@interpretation-agent` | `interpretation-agent.agent.md` | Physical interpretation + ADS comparison + next-action decision | [`InterpretationHandoff/v1`](.github/shared/handoff_schemas.md#interpretationhandoffv1) |
| `@paper-agent` | `paper-agent.agent.md` | Manuscript drafting (LaTeX), ADS citations, figure captions, compile + auto-review | [`PaperHandoff/v1`](.github/shared/handoff_schemas.md#paperhandoffv1) |

### Specialist agents (pre-existing)

| Agent | File | Role | Handoff schema |
|---|---|---|---|
| `@literature-agent` | `literature-agent.agent.md` | ADS search + BibTeX retrieval | — (appends to `bibliography.bib`) |
| `@simulation-agent` | `simulation-agent.agent.md` | Launch + post-process FARGO3D / PLUTO / DustPy / Magneticum | [`SimulationHandoff/v1`](.github/shared/handoff_schemas.md#simulationhandoffv1) |
| `@spectral-agent` | `spectral-agent.agent.md` | X-ray spectral fitting (Sherpa / PyXSPEC) | [`SpectralFitHandoff/v1`](.github/shared/handoff_schemas.md#spectralfithandoffv1) |
| `@retrieval-agent` | `retrieval-agent.agent.md` | Atmospheric retrievals (petitRADTRANS / dynesty) | — (writes HDF5 to `results/fits/`) |
| `@mcmc-agent` | `mcmc-agent.agent.md` | Posterior sampling + corner plots | [`MCMCHandoff/v1`](.github/shared/handoff_schemas.md#mcmchandoffv1) |

All agents share the group baseline in `.github/copilot-instructions.md`
and project-specific context in `AGENTS.md`.

---

## Research pipeline (full 9-stage)

The full research pipeline is orchestrated by `@pipeline-agent`.
Two mandatory **human gates** prevent automated progression without user confirmation.

```mermaid
flowchart TD
    U([User]) --> P[@pipeline-agent]
    P --> L[@literature-agent]
    P --> H[@hypothesis-agent]
    H -->|HypothesisHandoff/v1| GATE1{{⚠ Human Gate 1\nConfirm top hypothesis}}
    GATE1 --> A[@analytical-agent]
    A -->|AnalyticalHandoff/v1| S[@setup-agent]
    S -->|SimConfigHandoff/v1| SIM["@simulation-agent\n@retrieval-agent\n@spectral-agent"]
    SIM -->|SimulationHandoff / SpectralFitHandoff| AN[@analysis-agent]
    AN -->|AnalysisHandoff/v1| I[@interpretation-agent]
    I -->|InterpretationHandoff/v1| GATE2{{⚠ Human Gate 2\nConfirm write / iterate}}
    GATE2 -->|next_action: iterate| H
    GATE2 -->|next_action: write| WR[@paper-agent]
    WR -->|PaperHandoff/v1| DONE([Done])
    GATE2 -->|next_action: stop| DONE

    style WR fill:#cfc,stroke:#060,color:#000

    style GATE1 fill:#f9f,stroke:#a00,color:#000
    style GATE2 fill:#f9f,stroke:#a00,color:#000
```

### Stage summary

| Stage | Agent | Output |
|---|---|---|
| 1 QUESTION | `@pipeline-agent` | Creates `prompts/<task_id>_<date>.md` |
| 2 LITERATURE | `@literature-agent` | Appends to `paper/bibliography.bib` |
| 3 HYPOTHESIS | `@hypothesis-agent` | `results/hypotheses/<task_id>_<date>.json` |
| **Gate 1** | User | Confirm top hypothesis |
| 4 ANALYTICAL | `@analytical-agent` | `results/analytical/<task_id>_<date>.py` + JSON |
| 5 SETUP | `@setup-agent` | Config files in `data/runs/<task_id>/` + optional SLURM/PBS script |
| 6 SIMULATE | `@simulation-agent` / `@retrieval-agent` / `@spectral-agent` | Binary/HDF5 outputs in `data/` |
| 7 ANALYSE | `@analysis-agent` | Figures in `plots/` + `AnalysisHandoff` JSON |
| 8 INTERPRET | `@interpretation-agent` | `results/interpretation/<task_id>_<date>.json` |
| **Gate 2** | User | Confirm iterate / write / stop |
| 9 WRITE | `@paper-agent` | `paper/<task_id>_<date>/manuscript.pdf` + `referee_notes.md` |

---

## Legacy pipeline stages (pre-pipeline-agent)

```mermaid
flowchart TD
    U([User]) --> L[@literature-agent]
    U --> S[@simulation-agent]
    U --> R[@retrieval-agent]
    U --> X[@spectral-agent]

    L -->|bibliography.bib| U

    S -->|SimulationHandoff| X
    S -->|SimulationHandoff| M[@mcmc-agent]
    X -->|SpectralFitHandoff| M
    R -->|results/fits/*.h5| M

    M -->|MCMCHandoff| U

    subgraph "Simulation pipeline"
        S
    end
    subgraph "Spectroscopy pipeline"
        X
        R
    end
    subgraph "Statistics"
        M
    end
```

---

## Data flow

### Disk / planet-formation workflow

```
@simulation-agent  →  SimulationHandoff  →  @mcmc-agent
     │                                            │
 runs/disk_gap/                          results/fits/gap_depth.json
 data/snapshots/                         plots/corner_gap_alpha.pdf
```

1. `@simulation-agent` launches FARGO3D / PLUTO / DustPy via the bundled
   skill scripts and saves binary outputs to `data/`.
2. Post-processing produces a `SimulationHandoff` JSON (gap depth,
   surface density profile, wall-clock time, unit metadata).
3. `@mcmc-agent` samples posteriors over the parameter grid and writes an
   `MCMCHandoff` JSON with medians, 68 % credible intervals, and corner plot path.

### X-ray spectroscopy workflow

```
@spectral-agent  →  SpectralFitHandoff  →  @mcmc-agent
      │                                           │
 data/spectra/                           results/fits/core.json
 results/fits/core.json                  plots/corner_nH_kT.pdf
```

1. `@spectral-agent` fits the spectrum (Sherpa / PyXSPEC), performs sanity
   checks, and writes a `SpectralFitHandoff` with best-fit parameters and
   a parameter grid for MCMC.
2. `@mcmc-agent` refines the posterior and produces a corner plot.

### Atmospheric retrieval workflow

```
@retrieval-agent  →  results/fits/<planet>_dynesty.h5  →  @mcmc-agent
```

1. `@retrieval-agent` runs petitRADTRANS CCF and dynesty retrieval, saving
   posterior samples directly as HDF5 (no intermediate handoff schema needed
   — dynesty already provides full posterior).

---

## Handoff schemas

Structured JSON schemas for inter-agent data passing are defined in
[`.github/shared/handoff_schemas.md`](.github/shared/handoff_schemas.md).

Key schemas: `SimulationHandoff/v1`, `SpectralFitHandoff/v1`, `MCMCHandoff/v1`, `PaperHandoff/v1`.

---

## Quality gates

Every specialist agent enforces three anti-failure mechanisms:

| Gate | Mechanism | Description |
|---|---|---|
| **IRON RULEs** | Blockquoted markers in each `.agent.md` | Non-negotiable constraints that hold even in long conversations (context rot) |
| **Anti-patterns table** | Four-row table per agent | Explicit negative examples with *Why It Fails* + *Correct Behaviour* columns |
| **Anti-leakage** | `[DATA MISSING: …]` hard stop | Agents halt and flag rather than fabricate missing data from training memory |

See the `## Iron rules` and `## Anti-patterns` sections in each agent file
and the `## Agent reliability design` section in `README.md`.

---

## References pattern for large code blocks

Agent files and skill files follow the **lean references/ pattern**:
inline code exceeding ~15 lines is extracted to a `references/` subdirectory
and loaded on demand, keeping the agent/skill file itself scannable.

| Location | Contents |
|---|---|
| `.github/agents/references/` | Simulation I/O functions and code conventions for `@simulation-agent` |
| `.github/skills/<code>/references/` | Full parameter tables and worked examples for each skill |
| `.github/shared/` | Cross-agent shared artefacts (handoff schemas) |
