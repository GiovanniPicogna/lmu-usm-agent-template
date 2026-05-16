# LMU Astrophysics Group — Copilot Agent Instructions
#
# File:    .github/copilot-instructions.md
# Purpose: Repository-wide baseline for GitHub Copilot (all modes:
#          autocomplete, Chat, Agent Mode, Coding Agent).
#          Loaded automatically every session — no manual setup needed.
#
# Maintainer: LMU Astrophysics Group <astro@physik.lmu.de>
# Last updated: 2026-05
# Template version: 1.0
#
# ── How to customise ─────────────────────────────────────────────────────────
# This file encodes GROUP-LEVEL conventions that apply to every project.
# Project-specific context (target name, obs IDs, model assumptions) belongs
# in prompts/project_context.md or a project-level AGENTS.md.
# ─────────────────────────────────────────────────────────────────────────────

## 1. Identity & scientific domain

You are assisting researchers at the LMU Munich Astrophysics group.
Our work spans X-ray astronomy, galaxy clusters, cosmology, and
multi-wavelength data analysis. Code you write will be used in published
scientific papers. Correctness and reproducibility are more important
than speed.

## 2. Programming language & environment

- **Language**: Python 3.11+ exclusively unless a task explicitly requires
  something else (e.g. a Fortran legacy interface).
- **Package manager**: conda or mamba (environment files in `envs/`).
- **Key libraries** (prefer these over ad-hoc alternatives):
  - `astropy` — units, coordinates, FITS I/O, cosmology, tables
  - `numpy`, `scipy` — numerical work
  - `matplotlib` — all plots (see §5 for style rules)
  - `emcee` — MCMC sampling
  - `corner` — MCMC posterior corner plots
  - `sherpa` or `xspec` (via PyXSPEC) — X-ray spectral fitting
  - `astroquery` — catalogue and archive queries
  - `h5py` — HDF5 file I/O for large datasets
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
