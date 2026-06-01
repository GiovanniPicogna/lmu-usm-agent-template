---
layout: page
title: Agent Skills
nav_order: 3
---

# Agent Skills

Agent skills are reusable instruction packages that extend the agent's
capabilities for specific tasks. They live in `~/.agents/skills/` on your
machine and are loaded on demand.

**Full catalog and installation instructions:**
→ [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)

---

## Bundled simulation skills (shipped with this template)

Three simulation launch skills are included in `.github/skills/` and are
used automatically by `@simulation-agent`. Each ships a Pydantic-validated
Python runner that patches configuration files, launches the simulation,
and returns a `SUCCESS` / `ERROR` status line.

| Skill | Simulation code | Use case |
|---|---|---|
| [`dustpy`](https://github.com/GiovanniPicogna/lmu-usm-agent-template/blob/main/.github/skills/dustpy/SKILL.md) | DustPy | Radial dust evolution, grain growth, fragmentation barrier, Stokes numbers, dust-to-gas mass fractions |
| [`fargo3d`](https://github.com/GiovanniPicogna/lmu-usm-agent-template/blob/main/.github/skills/fargo3d/SKILL.md) | FARGO3D | Planet–disk interaction, gap opening, type-I/II migration torques — patches `.par` file without recompiling |
| [`pluto`](https://github.com/GiovanniPicogna/lmu-usm-agent-template/blob/main/.github/skills/pluto/SKILL.md) | PLUTO | HD/MHD disk and jet simulations — overrides `pluto.ini` parameters without recompiling |

Each skill follows the **lean SKILL.md pattern**: the `SKILL.md` file stays
compact (trigger conditions, procedure, key parameters, output format, error
table). Full parameter tables and worked examples live in the skill's
`references/` subdirectory and are read by the agent on demand:

```
skills/<code>/
├── SKILL.md              # Lean — quick-scan essentials only
├── references/
│   ├── parameters.md     # Full parameter table (types, defaults, constraints)
│   └── examples.md       # Step-by-step run examples  (PLUTO only)
└── scripts/
    └── run_<code>.py     # Validated runner
```

**Prerequisites:**
- `dustpy`: `pip install dustpy scientific-pydantic`
- `fargo3d`: compiled binary (`fargo3d`) must already exist — the skill patches `.par` files
  and launches an existing binary; recompilation (e.g. when changing `NFLUIDS`, `MHD`, or
  setup directory) must be done manually with `make` in the FARGO3D root
- `pluto`: no pre-existing binary required — `compile_pluto.py` builds or rebuilds `./pluto`
  automatically when physics, geometry, dimensions, EOS, or module flags change; the skill's
  pre-flight checklist (STEP 0) determines whether recompilation is needed before each run

```bash
# Example: launch DustPy via simulation-agent
@simulation-agent  Run a dust evolution simulation with alpha=1e-3,
                   disk mass 0.05 Msun, fragmentation velocity 10 m/s,
                   for 1 Myr. Save snapshots to data/dustpy/run01/.
```

---

## Recommended skills for USM groups

### Universal (all groups)

| Skill | Best used for |
|-------|--------------|
| `astropy` | Coordinate transforms, FITS I/O, cosmological distances, WCS, time systems |
| `matplotlib` | Publication plots requiring fine-grained control over every element |
| `scientific-visualization` | Multi-panel journal figures (Nature/A&A style, colourblind-safe palettes, significance annotations) |
| `statistical-analysis` | Choosing appropriate tests, assumption checking, APA-formatted results |
| `paper-lookup` | Searching PubMed, arXiv, OpenAlex, Semantic Scholar, Crossref |
| `citation-management` | Verifying BibTeX, DOI → BibTeX conversion, reference accuracy |

### Disk & planet formation

| Skill | Best used for |
|-------|--------------|
| `database-lookup` | Querying SIMBAD, VizieR, ALMA archive, ExoFOP, Gaia DR3 |
| `exploratory-data-analysis` | First look at a new simulation output or observational data file |
| `scientific-schematics` | Disk structure diagrams, gap morphology schematics, protoplanetary disk cross-sections |

### Cosmological simulations

| Skill | Best used for |
|-------|--------------|
| `networkx` | Merger trees, substructure graphs, galaxy filament networks |
| `umap-learn` | Dimensionality reduction for halo/galaxy property distributions |
| `scikit-learn` | Classification / regression on simulation catalogues |
| `shap` | Interpreting ML models trained on halo catalogues |

### Atmospheric retrievals & high-res spectroscopy

| Skill | Best used for |
|-------|--------------|
| `statsmodels` | Frequentist inference, time-series detrending |
| `shap` | Interpreting ML-based retrieval or classification models |
| `database-lookup` | Querying ExoAtmospheres, HITRAN, ExoMol, NASA Exoplanet Archive |
| `aeon` | Time-series classification of stellar / planetary light curves |

### X-ray & galaxy clusters

| Skill | Best used for |
|-------|--------------|
| `scikit-survival` | Survival / time-to-event modelling (e.g. cluster cooling time distributions) |
| `scientific-visualization` | Thermodynamic maps, surface brightness profiles |

---

## How to use a skill

In Copilot Chat or Agent Mode, tell the agent which skill to load at the
start of a task:

```
Use the scientific-visualization skill for this figure.
Plot the dust surface density profile with Nature-journal styling and
save to plots/disk_sigma.pdf.
```

The agent reads the `SKILL.md` file and follows its step-by-step instructions.
Skills can be chained — e.g. `paper-lookup` to find references, then
`citation-management` to produce clean BibTeX.
