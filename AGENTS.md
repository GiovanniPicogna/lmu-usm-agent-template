# AGENTS.md — Project-Specific Agent Instructions
#
# File:    AGENTS.md  (repo root; subdirectory AGENTS.md files are also
#          loaded by Codex CLI — nearer directory wins)
# Purpose: Primary cross-tool agent instructions for THIS project.
#          Loaded by: Copilot Coding Agent, Claude Code (fallback when no
#          CLAUDE.md is present), Gemini CLI, Codex CLI, Cursor, and Aider.
#          Stewarded by the Linux Foundation (agents.md); in use across
#          60,000+ open-source projects as the universal agent standard.
#          Group-level conventions (coding standards, citation policy,
#          figure style) live in .github/copilot-instructions.md.
#          This file carries only project-specific context: science goal,
#          data paths, simulation parameters, and per-project agent rules.
#
# Size:    Keep under ~300 lines. Codex CLI truncates at 64 KiB per file.
# Local:   Machine-specific overrides go in AGENTS.override.md (gitignored).
#
# ── Instructions ─────────────────────────────────────────────────────────────
# Replace all <PLACEHOLDER> fields before committing.
# Keep this file updated as the project evolves.
# Commit AGENTS.md in every PR that changes the science model or data.
#
# ── For agents reading this file ─────────────────────────────────────────────
# If any field below still contains angle-bracket placeholders such as
# <PROJECT_NAME> or <PI_NAME>, this project has not been configured yet.
# Do NOT substitute example values from your training data.
# Instead emit: [DATA MISSING: AGENTS.md not filled in — ask the user to
# complete the placeholders before proceeding.]
# ─────────────────────────────────────────────────────────────────────────────

## Project overview

**Project**: <PROJECT_NAME>
**PI**: <PI_NAME> (<pi@physik.lmu.de>)
**Group**: LMU Munich Astrophysics / Universitäts-Sternwarte München
**Domain**: <disk-sim | cosmological-sim | atm-retrieval | x-ray | lss-cosmo | other>
**Status**: <active | analysis | writing | published>
**Associated paper**: <Author et al. YYYY, Journal, arxiv:XXXX.XXXXX>

One-sentence science goal:
> <e.g. "Quantify dust trapping efficiency in planet-carved gaps using
> coupled FARGO3D + DustPy simulations of a Class II protoplanetary disk.">

---

## Data & simulation outputs

**Primary simulation code**: <FARGO3D | PLUTO | Magneticum | petitRADTRANS | other>
**Code version / commit**: <hash or tag>
**Run location** (HPC cluster, not in Git): <e.g. LRZ SuperMUC-NG, project ID xyz>

**Raw outputs** (local, git-ignored, regenerated on request):
```
data/
├── snapshots/      # binary HDF5 or GADGET snapshots  (disk-sim / cosmo)
├── dust/           # DustPy output files (.hdf5)       (disk-sim)
├── spectra/        # observed or synthetic spectra      (retrieval / X-ray)
│   ├── obs/        #   reduced instrumental spectra
│   └── model/      #   petitRADTRANS / RADMC-3D outputs
├── images/         # FITS images (X-ray, ALMA, optical) (X-ray / obs)
└── tables/         # ASCII / CSV / FITS catalogues
```

**Processed results** (committed if < 10 MB):
```
results/
├── hypotheses/     # HypothesisHandoff JSON files
├── analytical/     # AnalyticalHandoff JSON + benchmark scripts
├── analysis/       # AnalysisHandoff JSON files
├── interpretation/ # InterpretationHandoff JSON files
├── fits/           # spectral / MCMC parameter files, chains (.h5)
├── maps/           # thermodynamic / column density maps (FITS)
├── populations/    # planet population outputs (HDF5 / CSV)
└── <task_id>/      # per-run directory: abort_report.json, handoff chain
```

**Do not** read from or write to any path outside `data/`, `results/`,
and `plots/` unless explicitly instructed.

---

## Science model & physical assumptions

<!-- Fill in the block that matches your domain; delete the others. -->

### Disk / planet formation (FARGO3D · PLUTO · DustPy)
- **Stellar mass**: M★ = <1.0> M☉
- **Disk mass**: M_disk = <0.05> M☉
- **Viscosity parameter**: α = <1e-3> (constant Shakura-Sunyaev)
- **Dust-to-gas ratio**: initial ε = <0.01>
- **Grain size range**: a_min = <1e-4> cm, a_max = <10> cm
- **Fragmentation velocity**: v_frag = <10> m s⁻¹
- **Simulation domain**: R ∈ [<0.3>, <300>] au, N_r × N_φ = <512 × 1024>
- **Planets**: <list mass, semi-major axis, e.g. "1 MJup at 20 au">
- **Known numerical issues**: <e.g. "wave-killing zone at R < 0.4 au; do not analyse inside that radius">

### Cosmological simulation (Magneticum · GADGET)
- **Simulation box**: L = <352> Mpc/h, N_part = <2 × 1526³>
- **Run name**: <Box2/hr | Box0 | etc.>
- **Cosmology**: H₀ = <70.4> km s⁻¹ Mpc⁻¹, Ω_m = <0.272>, Ω_Λ = <0.728>, σ₈ = <0.809>
- **Snapshot redshifts of interest**: z = <0.0, 0.25, 0.5, 1.0>
- **Friends-of-friends / SUBFIND**: linking length b = <0.16>
- **Known issues**: <e.g. "snapshots 144–146 missing on LRZ; use z ≈ 0.06 instead of z = 0.07">

### Atmospheric retrieval (petitRADTRANS)
- **Planet / target**: <WASP-189 b>
- **Instrument**: <CRIRES+ K-band | CARMENES VIS | JWST NIRSpec G395H>
- **Retrieval mode**: <emission | transmission>
- **Species included**: <CO, H₂O, Fe, TiO — list all>
- **T-P profile**: <Guillot 2010 parametrisation | free-retrieval N layers>
- **Nested sampler**: <dynesty | PyMultiNest>, n_live = <500>
- **Reference wavelength mask**: <list any manually excluded regions, e.g. "2.29–2.31 µm (CO₂ telluric)">

### X-ray spectral fitting (Sherpa · PyXSPEC)
- **Source redshift**: z = <0.091>
- **Galactic absorption**: nH = <4.6e20> cm⁻² (fixed; HI4PI: 2016A&A...594A.116H)
- **Spectral model**: `TBabs * apec` (Asplund 2009 abundances: 2009ARA&A..47..481A)
- **Fitting statistic**: C-stat, **not** chi-squared
- **Fitting band**: 0.5–7.0 keV (EPIC-pn), 0.5–8.0 keV (ACIS-S)
- **Cosmology**: H₀ = 70, Ω_m = 0.3, Ω_Λ = 0.7 (`astropy.cosmology.FlatLambdaCDM`)

---

## Code structure

Only `src/utils/` is committed in the template.
Create the subdirectories relevant to **your** domain and delete this comment
once you have added them.

```
src/
└── utils/          # shared helpers (coords, units, plotting, constants)
                    # kept in all projects — do not remove
```

**Create as needed — delete the rest:**

| Domain | Add these subdirectories |
|---|---|
| Disk / planet formation | `simulation/` (setup & job scripts), `analysis/` (gap depth, dust, RADMC-3D) |
| Cosmological simulations | `simulation/` (snapshot I/O, halo finding), `analysis/` (maps, HMF, profiles) |
| Atmospheric retrievals | `analysis/` (CCF, forward model), `retrieval/` (dynesty wrapper, corner plots) |
| X-ray / galaxy clusters | `reduction/` (SAS / CIAO wrappers), `analysis/` (Sherpa, thermo maps) |
| MCMC / sampling (any) | `mcmc/` (emcee / dynesty sampling and posterior analysis) |

Example after filling in for a disk-simulation project:

```
src/
├── simulation/     # FARGO3D / PLUTO .par generation; HPC job scripts
│   ├── setup.py
│   └── submit.sh
├── analysis/       # gap depth, dust evolution, RADMC-3D post-processing
│   └── dust.py
└── utils/          # astropy units helpers, plot style, constants

results/            # fit results as JSON/HDF5 (committed if < 10 MB)
plots/              # publication figures (committed as PDF)
prompts/            # agent prompt logs (always committed)
```

When creating a new script:
1. Place it in the appropriate `src/` subdirectory.
2. Add a module docstring explaining its purpose, inputs, and outputs.
3. Add a corresponding prompt log entry to `prompts/` (see TEMPLATE).

---

## Key commands

```bash
# ── Environment setup ──────────────────────────────────────────────────────
conda env create -f envs/base.yml
conda activate py312
pre-commit install            # run style/BibTeX checks on every commit

# ── Bundled skill runners (use these directly or via agents) ────────────────
# DustPy — dust evolution
python .github/skills/dustpy/scripts/run_dustpy.py \
    --run_dir data/dust/<run_name> \
    --alpha 1e-3 --mdisk_msun 0.05 --t_end_yr 1e6

# DustPy — diagnostic plots
python .github/skills/dustpy/scripts/plot_dustpy.py \
    --run_dir data/dust/<run_name> --plot all --out plots/dust/<run_name>

# FARGO3D — planet–disk simulation
python .github/skills/fargo3d/scripts/run_fargo3d.py \
    --par data/runs/<run_name>/fargo.par \
    --params Sigma0=6e-4 AspectRatio=0.05 Mplanet=1.0

# PLUTO — HD/MHD disk simulation
python .github/skills/pluto/scripts/run_pluto.py \
    --json <params.json>                  # patches pluto.ini and launches
python .github/skills/pluto/scripts/compile_pluto.py \
    --problem <Test_Problems/HD/Disk_Planet> --with-fargo
python .github/skills/pluto/scripts/plot_pluto.py \
    --run data/runs/<run_name>/ --var rho --snap -1

# RADMC-3D — radiative transfer post-processing
python .github/skills/radmc3d/scripts/run_radmc3d.py \
    --setup data/radmc/<run_name>/ --mode image

# ── Literature (via @literature-agent) ────────────────────────────────────
# In Copilot Chat:
# @literature-agent Find all papers citing 2025A&A...703A.270R since 2025
#                   and append BibTeX to paper/bibliography.bib

# ── Full research pipeline ────────────────────────────────────────────────
# In Copilot (Agent Mode):
# @pipeline-agent  Science question: "How does planet mass affect gap depth?"
#                  Domain: disk  |  Compute mode: local
#
# In Claude Code (conversation prompt):
# Read .github/agents/pipeline-agent.agent.md and
# .claude/agents/pipeline-agent.md, then start the research pipeline.
# Science question: "How does planet mass affect gap depth?"
# Domain: disk | Compute mode: local
#
# The pipeline pauses at three mandatory human gates:
#   Gate 1 — after hypothesis generation (confirm which to pursue)
#   Gate 2 — after interpretation (choose: iterate / write→@paper-agent / mcmc / stop / abort)
#   Gate 3 — after peer review (confirm: accept / revise / reject)

# ── MCMC sampling (via @mcmc-agent) ───────────────────────────────────────
# @mcmc-agent  results/spectral/core_fit.json
#              sampler: emcee  nwalkers: 64  nsteps: 5000

# ── Paper writing (via @paper-agent) ──────────────────────────────────────
# Triggered by Gate 2 next_action: write
# @paper-agent  results/interpretation/<task_id>_<date>.json

# ── Zenodo data upload ────────────────────────────────────────────────────
# First-time setup: export ZENODO_SANDBOX_TOKEN and ZENODO_TOKEN in your shell.
# Edit zenodo.yml to customise targets (title/authors read from CITATION.cff).
# results/, plots/, data/ are git-ignored — run these locally.

python -m src.zenodo create  --sandbox --dry-run        # preview the upload plan
python -m src.zenodo create  --sandbox                  # upload zips to Sandbox
python -m src.zenodo publish --sandbox --deposit-id <ID> # citable DOI (confirms)
python -m src.zenodo status  --sandbox --deposit-id <ID> # inspect a deposit
python -m src.zenodo create  --no-sandbox               # production (PI approval)

# ── Pre-commit validation ─────────────────────────────────────────────────
pre-commit run --all-files
```

---

## Agent behaviour rules (project-specific additions)

### Pipeline
1. **Start with `@pipeline-agent`** for any new science question that requires
   simulation or retrieval. Do not invoke specialist agents directly unless
   you are continuing an already-started pipeline at a specific stage.
2. **Human gates are blocking.** Gate 1 (after hypothesis), Gate 2 (after
   interpretation), and Gate 3 (after peer review) require explicit user
   confirmation before the pipeline continues. Agents must not auto-proceed.
   Gate 2 options: `iterate`, `write`, `mcmc`, `stop`, `abort` (see
   `InterpretationHandoff.next_action`). Gate 3 options: `accept`, `revise`,
   `reject` (see `RefereeHandoff.next_action`).
3. **Handoff schemas are contracts.** Every inter-agent handoff must
   conform to the schema in `.github/shared/handoff_schemas.md`.
   `[DATA MISSING]` is the required placeholder for any field the agent
   cannot populate from actual data.
4. **Prompt logs are mandatory.** Create a log in `prompts/` at the start
   of every pipeline run using `cp prompts/TEMPLATE.md prompts/<task_id>_$(date +%Y%m%d).md`.
   Complete the Output files table and Validation checklist before closing.

### Analysis & fitting
5. **Spectral fitting**: Always run on a single test spectrum
   (`data/spectra/bkg_region/`) before running on the full grid.
6. **MCMC**: Always set and log a random seed. Default: `seed = 42`.
   Store it in the output HDF5 as an attribute.
7. **Figures**: Use the colour scale defined in `src/utils/style.py` if it
   exists; otherwise follow the group defaults in `copilot-instructions.md §5`
   (tab10 palette, cividis/viridis for 2D maps, 300 dpi, PDF output).

### Data & outputs
8. **Results files**: Write to `results/<category>/<descriptive_name>.json`
   or `.h5`. Never overwrite an existing results file — append a timestamp
   suffix instead: `core_fit_20260515.json`.
9. **HPC jobs**: `@setup-agent` generates SLURM/PBS scripts but does
   **not** submit them. Review the script, then submit manually.
   Confirm job IDs and wall-clock time in the prompt log.

### Citations
10. **ADS citations**: When adding a new reference, always call the ADS MCP
    `get_bibtex` tool and append the result to `paper/bibliography.bib`.
    Never hand-write BibTeX entries — the doi= field must be present and
    validated by pre-commit.

---

## MCP servers configured for this project

See `.vscode/settings.json` for the full MCP configuration.

| Server | Purpose | Requires |
|--------|---------|---------|
| `cbyrohl/mcp-server-ads` | Literature search, BibTeX retrieval | `ADS_API_TOKEN` env var |
| `adamzacharia/alma_mcp` | ALMA archive queries (uncomment to enable) | `ALMA_TOKEN` env var |
| `ProgramComputer/NASA-MCP-server` | General NASA data products (uncomment to enable) | — |
| `NASA-PDS/pds-mcp-server` | Planetary Data System archive (uncomment to enable) | — |

To get an ADS API token: https://ui.adsabs.harvard.edu/user/settings/token
