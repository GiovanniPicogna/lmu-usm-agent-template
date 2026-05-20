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

## Agent reliability design

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
