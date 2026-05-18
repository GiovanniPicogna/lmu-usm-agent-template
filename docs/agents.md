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

Post-processes hydrodynamical simulation outputs from FARGO3D, PLUTO,
and Magneticum/GADGET. Provides:
- FARGO3D HDF5 and legacy binary `.dat` readers with code-unit → physical-unit conversion
- Magneticum/GADGET HDF5 reader with complete unit conversion table
- GadgetIO.jl subprocess call pattern
- Sanity checks: gap depth floors, planetary torque sign conventions,
  halo mass / ICM temperature ranges

```
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
