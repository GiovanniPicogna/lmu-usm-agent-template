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
