# LMU Astrophysics Group — Copilot Agent Instructions
#
# File:    .github/copilot-instructions.md
# Purpose: Repository-wide baseline for GitHub Copilot (all modes:
#          autocomplete, Chat, Agent Mode, Coding Agent).
#          Loaded automatically every session — no manual setup needed.
#
# Maintainer: LMU Astrophysics Group <astro@physik.lmu.de>
# Last updated: 2026-05
# Template version: 1.1
#
# ── How to customise ─────────────────────────────────────────────────────────
# This file encodes GROUP-LEVEL conventions that apply to every project.
# Project-specific context (target name, obs IDs, model assumptions) belongs
# in prompts/project_context.md or a project-level AGENTS.md.
# ─────────────────────────────────────────────────────────────────────────────

> **This repository** is the LMU Munich Astrophysics group template for new
> computational research projects. Fork it to scaffold a new project; fill in
> all `<PLACEHOLDER>` fields in `AGENTS.md` before your first agent session.
> Project-specific commands, HPC paths, and MCP servers are listed in
> `AGENTS.md` §"Key commands" and §"MCP servers configured for this project".

## 1. Identity & scientific domain

You are assisting researchers at the LMU Munich Astrophysics group
(Universitäts-Sternwarte München, USM).
Our work spans multiple computational domains:
- **Protoplanetary disk & planet formation**: radiation-hydrodynamics with
  FARGO3D, PLUTO, NIRVANA-III; dust evolution with DustPy; radiative
  transfer post-processing with RADMC-3D; planet population synthesis (NGPPS).
- **Cosmological simulations**: Magneticum (GADGET-based SPH); constrained
  simulations (SLOW suite); post-processing with yt, GadgetIO.jl (Julia),
  and h5py.
- **Exoplanet atmospheric science**: high-resolution spectroscopy (CARMENES,
  CRIRES+, JWST/NIRSpec); petitRADTRANS retrievals; cross-correlation
  spectroscopy; GCM modelling.
- **Large-scale structure & cosmological inference**: void statistics, weak
  lensing, SBI / neural posterior estimation, Euclid pipelines.
- **X-ray astronomy & galaxy clusters**: XMM-Newton, Chandra, eROSITA;
  Sherpa / PyXSPEC spectral fitting; thermodynamic maps.

Code you write will be used in published scientific papers.
Correctness and reproducibility are more important than speed.

## Repository structure

```
.github/
├── copilot-instructions.md   # group-wide conventions — loaded every session
├── instructions/             # scoped .instructions.md files (Python, notebooks, etc.)
└── skills/                   # bundled agent skills: dustpy, fargo3d, pluto, radmc3d, yt, sherpa
envs/                         # conda environment YAML files
data/                         # git-ignored — simulation outputs, FITS, HDF5 snapshots
docs/                         # GitHub Pages site (index.md, slides, skills catalogue)
paper/                        # bibliography.bib and manuscript drafts
plots/                        # publication figures (PDF/PNG); commit only final versions
prompts/                      # agent prompt logs — always committed (see §7)
results/                      # processed outputs < 10 MB (JSON/HDF5 fit results, maps)
src/
└── utils/                    # shared helpers: units, coordinates, plot style, constants
AGENTS.md                     # project-specific context — fill in before first session
ARCHITECTURE.md               # agent roster, research pipeline diagram, handoff schemas
```

For `src/`, add the domain subdirectories described in `AGENTS.md` §"Code structure"
when starting a project (`simulation/`, `analysis/`, `retrieval/`, `reduction/`, etc.).

## 2. Programming language & environment

- **Language**: Python 3.11+ by default. Julia (GadgetIO.jl) and shell
  scripts are acceptable for simulation I/O and pipeline tasks.
  Fortran interfaces exist in PLUTO/FARGO3D; do not rewrite them.
- **Package manager**: conda or mamba (environment files in `envs/`).
- **Key libraries by domain** (prefer these over ad-hoc alternatives):

  *Universal*
  - `astropy` — units, coordinates, FITS I/O, cosmology, tables
  - `numpy`, `scipy` — numerical work
  - `matplotlib` — all plots (see §5 for style rules)
  - `h5py` — HDF5 file I/O (simulation snapshots, spectral products)
  - `astroquery` — catalogue and archive queries

  *MCMC / posterior sampling*
  - `emcee` — ensemble sampler (general purpose)
  - `dynesty` — nested sampling (preferred for multi-modal posteriors
    and retrievals)
  - `corner` — MCMC posterior corner plots

  *Disk & planet formation post-processing*
  - `dustpy` — 1-D dust evolution (Birnstiel group standard)
  - `radmc3dPy` — Python interface to RADMC-3D radiative transfer
  - `fargopy` — FARGO3D output reader (if available); otherwise parse
    binary `.dat` files directly with `numpy.fromfile`

  *Cosmological simulation analysis*
  - `yt` — volumetric analysis and rendering of SPH/AMR snapshots
  - `h5py` — direct GADGET/Magneticum HDF5 snapshot access
  - Prefer `GadgetIO.jl` (Julia) for snapshot I/O in Julia workflows;
    call from Python via `subprocess` if needed

  *Atmospheric retrievals*
  - `petitRADTRANS` — forward model and retrieval (Molaverdikhani/Nortmann
    group standard)
  - `PyMultiNest` or `dynesty` — nested sampling back-end
  - `scipy.signal.correlate` — cross-correlation for CCF pipelines

  *X-ray spectral fitting*
  - `sherpa` or `xspec` (via PyXSPEC)

- **Avoid**: `pandas` for FITS tables (use `astropy.table`); raw `requests`
  for ADS queries (use the ADS MCP or `ads` Python library).

## 3. Physical units & numerical conventions

- Always use `astropy.units` (import as `u`) for physical quantities.
  Never hardcode unit conversions as magic numbers.
- SI units by default; CGS only where the literature convention demands it
  (e.g. erg s⁻¹ cm⁻² for X-ray flux).
- Report uncertainties at **1σ** (68% confidence) unless explicitly stated
  otherwise. Confidence intervals for spectral fitting: **90%** (standard
  in X-ray astronomy — state this clearly in comments and output).
  For MCMC posteriors: report **68% (1σ) credible intervals** — this is
  consistent with the global rule and is distinct from the 90% convention
  used for spectral fitting confidence contours.
- Propagate uncertainties explicitly. Do not silently drop error terms.
- When comparing fitted parameters across observations, always check and
  state whether errors are statistical only or include systematics.

## 4. Coding standards

- Write **docstrings** for every function and class (NumPy docstring format).
- Type hints on all public function signatures.
- Keep functions short (< 50 lines). Split complex pipelines into
  clearly named stages.
- No bare `except:` clauses. Catch specific exceptions; log the traceback.
- Print meaningful progress output for long-running fits or downloads
  (use `tqdm` or explicit `print` with flush=True).
- Test on a small data subset before running on the full dataset.
  Include a `--test` or `--dry-run` flag in scripts where appropriate.
- Scripts must be runnable from the command line with `argparse` or
  `click`; never hardcode paths.

## 5. Figures & visualisation

- Resolution: **300 dpi** for all saved figures.
- Colour palette: **matplotlib `tab10`** as default; use `cividis` or
  `viridis` for 2D maps (both are colourblind-safe and print well in
  greyscale). Never use `jet` or `rainbow`.
- Font size: ≥ 10 pt for axis labels, ≥ 8 pt for tick labels.
- Include a legend when more than one dataset is plotted.
- Save figures as **PDF** for vector graphics (publications) and PNG
  for quick inspection. Do both when in doubt.
- Always label axes with units: `r"Flux [erg s$^{-1}$ cm$^{-2}$]"`.

## 6. References & citations — CRITICAL

> ⚠️  This section is the most important safety rule in this file.

- **NEVER invent, guess, or reconstruct a reference.**
  If you do not have the exact bibcode or DOI, say so explicitly and
  suggest that the user verify via NASA ADS.
- When a reference is needed, query the **ADS MCP server** first
  (`search_papers`, `get_bibtex`). Only fall back to training-data
  knowledge if the MCP is unavailable, and flag this clearly.
- Use **ADS bibcode format** in comments and BibTeX:
  e.g. `2016A&A...594A.116H` (HI4PI), `2001A&A...365L...1J` (XMM launch).
- BibTeX keys: `AuthorYYYY` style, e.g. `HI4PI2016`, `Markevitch2007`.
- Do not cite arXiv preprints when a published version exists.
- When generating a `.bib` file, always include DOI and ADS bibcode
  as fields even if they are not standard BibTeX fields (add as `note`
  or custom field).

## 7. Reproducibility requirements

Every analysis script must be accompanied by a corresponding prompt
log in `prompts/`. See `prompts/TEMPLATE.md` for the required format.

**When operating in Agent Mode on any science task, create the prompt
log as your very first action — before writing code, running commands,
or reading data files:**

```bash
cp prompts/TEMPLATE.md prompts/<task_id>_$(date +%Y%m%d).md
```

Derive `task_id` as a short `snake_case` label from the user's request
(e.g. `spectral_fit_core`, `mcmc_wasp189b`, `disk_gap_depth_1mjup`).
Pre-fill the Metadata block (date, tool, model, task ID) and paste the
user's exact prompt into the "Prompt(s) used" section. Complete the
"Output files" table and "Validation performed" checklist at the end
of the task before marking it done.

At minimum, record:
- Date, tool name, and model version used
- The exact prompt(s) given to the agent
- Which output files were generated
- Validation steps performed

## 8. Data handling & privacy

- Raw observational data (FITS files, event lists) must not be committed
  to Git. Add `*.fits`, `*.fits.gz`, `*.evt` to `.gitignore`.
- Intermediate products (spectra, images) go in `data/` (git-ignored)
  or `results/` (selectively committed if small).
- Never upload proprietary or embargoed data to any AI service,
  cloud tool, or external API without PI approval.
- Simulated or public archival data may be used freely.

## 9. Error handling & self-correction

- If a script fails, print the full traceback and the input parameters
  that caused the failure before stopping.
- When running in Agent Mode: attempt to fix the error once automatically,
  then pause and explain what went wrong and what fix was applied.
  Do not silently retry more than twice.
- If a numerical result looks physically implausible (e.g. a photon index
  Γ > 5 or a temperature kT < 0.1 keV for a cluster), flag it as a
  warning and do not proceed without user confirmation.

## 10. What this agent must never do

- Invent author names, journal names, DOIs, or bibcodes.
- **Invent or guess observation metadata**: ObsIDs, exposure times, instrument
  modes, calibration versions, or pipeline version numbers must always be read
  from `AGENTS.md`, actual file headers (`astropy.io.fits`), or the relevant
  archive (Chandra, XMM, ALMA). Never reconstruct these from training data.
- Modify raw data files.
- Submit jobs to a cluster or remote machine without explicit user confirmation.
- Delete or overwrite existing results files (always write to a new path
  or prompt for confirmation).
- Use a non-deterministic random seed without logging it to the output.
- Silently subsample or filter data without documenting the selection.

## 11. Agent skills

Agent skills are reusable, domain-specific instruction packages that you
can activate on demand to extend your capabilities. There are two tiers:

**Bundled domain skills** (live in `.github/skills/`, no installation needed):
`dustpy`, `fargo3d`, `pluto`, `radmc3d`, `yt`, `sherpa`.
See `ARCHITECTURE.md` for the canonical list and trigger phrases.

**Community skills** (installed to `~/.agents/skills/`, loaded with `read_file`):

**Full catalog and installation instructions:**
→ https://github.com/K-Dense-AI/scientific-agent-skills

### Recommended community skills for USM groups

*Universal (all groups)*

| Skill | Invoke when… |
|-------|-------------|
| `astropy` | coordinate transforms, FITS I/O, cosmological distances, WCS |
| `matplotlib` | any publication plot needing fine-grained control |
| `scientific-visualization` | multi-panel journal figures (Nature/A&A style, colourblind palettes) |
| `statistical-analysis` | choosing and running statistical tests, power analysis |
| `paper-lookup` | searching PubMed / arXiv / OpenAlex / Semantic Scholar |
| `citation-management` | verifying BibTeX, converting DOIs, formatting references |

*Disk & planet formation*

| Skill | Invoke when… |
|-------|-------------|
| `database-lookup` | querying SIMBAD, VizieR, ALMA archive, ExoFOP |
| `exploratory-data-analysis` | first look at a new simulation output or data file |
| `scientific-schematics` | disk structure diagrams, gap morphology schematics |
| `dustpy` | **bundled** — 1-D dust evolution, grain growth, fragmentation barrier |
| `fargo3d` | **bundled** — planet–disk interaction, gap opening, type-I migration |
| `pluto` | **bundled** — HD/MHD disk & jet simulations, compile/run/plot |
| `radmc3d` | **bundled** — radiative transfer post-processing, synthetic ALMA images, SED, scattered-light maps |

*Cosmological simulations*

| Skill | Invoke when… |
|-------|-------------|
| `networkx` | building merger trees or substructure graphs |
| `umap-learn` | dimensionality reduction for halo/galaxy populations |
| `scikit-learn` | classification / regression on simulation catalogues |
| `yt` | **bundled** — volumetric analysis, projection maps, thermodynamic profiles of SPH/AMR snapshots |

*Atmospheric retrievals & high-res spectroscopy*

| Skill | Invoke when… |
|-------|-------------|
| `statsmodels` | frequentist inference, ARIMA detrending of time series |
| `shap` | interpreting ML-based retrieval or classification models |
| `database-lookup` | querying ExoAtmospheres, HITRAN, ExoMol line lists |

*X-ray & galaxy clusters*

| Skill | Invoke when… |
|-------|-------------|
| `imaging-data-commons` | accessing NCI / public X-ray / CT imaging datasets |
| `pydicom` | reading DICOM files from medical / detector calibration data |
| `sherpa` | **bundled** — X-ray spectral fitting, TBabs\*apec models, C-stat, confidence contours |

*Simulation pre-analysis (all domains)*

| Skill | Invoke when… |
|-------|-------------|
| `sympy` | analytical dispersion relations, stability criteria, linear perturbation theory, scaling laws |

### Using a skill

```python
# At the start of a task, tell the agent which skill to load:
# "Use the scientific-visualization skill for this figure."
# The agent will read the SKILL.md and follow its instructions.
```

## 12. Scoped Copilot instructions (Copilot-only)

Since July 2025, Copilot also supports glob-scoped instruction files that
activate only for matching file types or directories. Create them in
`.github/instructions/`:

```
.github/instructions/
├── python.instructions.md       # applyTo: "**/*.py"
├── simulation.instructions.md   # applyTo: "src/simulation/**"
└── notebooks.instructions.md    # applyTo: "**/*.ipynb"
```

Frontmatter example:

```markdown
---
applyTo: "**/*.py"
---
Always use type hints. Prefer `astropy.units.Quantity` over bare floats.
Never hardcode physical constants — import from `astropy.constants`.
```

Use scoped files for rules that apply only to a specific file type or
subdirectory (e.g., Python-only style rules, notebook-specific output
conventions), keeping this file focused on universal group conventions.
This is a Copilot-specific feature; it has no equivalent in `AGENTS.md`.
