# Architecture — LMU USM Agent Template

This document is the **single source of truth** for how agents interact,
what data flows between them, and what quality gates govern each stage.

---

## Agent roster

| Agent | File | Role | Handoff schema |
|---|---|---|---|
| `@paper-agent` | `paper-agent.agent.md` | Orchestrator — delegates sub-tasks to all specialist agents and assembles the manuscript | — |
| `@literature-agent` | `literature-agent.agent.md` | ADS search + BibTeX retrieval | — (appends to `bibliography.bib`) |
| `@simulation-agent` | `simulation-agent.agent.md` | Launch + post-process FARGO3D / PLUTO / DustPy / Magneticum | [`SimulationHandoff`](.github/shared/handoff_schemas.md#simulationhandoff) |
| `@spectral-agent` | `spectral-agent.agent.md` | X-ray spectral fitting (Sherpa / PyXSPEC) | [`SpectralFitHandoff`](.github/shared/handoff_schemas.md#spectralfithandoff) |
| `@retrieval-agent` | `retrieval-agent.agent.md` | Atmospheric retrievals (petitRADTRANS / dynesty) | — (writes HDF5 to `results/fits/`) |
| `@mcmc-agent` | `mcmc-agent.agent.md` | Posterior sampling + corner plots | [`MCMCHandoff`](.github/shared/handoff_schemas.md#mcmchandoff) |

All agents share the group baseline in `.github/copilot-instructions.md`
and project-specific context in `AGENTS.md`.

---

## Pipeline stages

```mermaid
flowchart TD
    U([User / @paper-agent]) --> L[@literature-agent]
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

Key schemas: `SimulationHandoff/v1`, `SpectralFitHandoff/v1`, `MCMCHandoff/v1`.

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
