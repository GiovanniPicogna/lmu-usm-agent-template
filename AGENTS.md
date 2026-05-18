# AGENTS.md — Project-Specific Agent Instructions
#
# File:    AGENTS.md  (repo root, or per-subdirectory)
# Purpose: Extends .github/copilot-instructions.md with context specific
#          to THIS project. Loaded by Copilot Coding Agent, Claude Code,
#          Gemini CLI, and any OpenAI Codex-compatible agent.
#
# ── Instructions ─────────────────────────────────────────────────────────────
# Replace all <PLACEHOLDER> fields before committing.
# Keep this file updated as the project evolves.
# Commit AGENTS.md in every PR that changes the science model or data.
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

**Primary simulation code**: <FARGO3D | PLUTO | NIRVANA-III | RAMSES | Magneticum | petitRADTRANS | other>
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
├── fits/           # JSON parameter files, chains (.h5)
├── maps/           # thermodynamic / column density maps (FITS)
└── populations/    # planet population outputs (HDF5 / CSV)
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
# ── Disk simulations ───────────────────────────────────────────────────────
# Generate FARGO3D parameter file from config
python src/simulation/setup.py --config configs/disk_1Mjup.json \
    --code fargo3d --out data/runs/disk_1Mjup/

# Post-process: compute dust surface density gap depth vs time
python src/analysis/dust.py --run data/runs/disk_1Mjup/ \
    --planet 0 --out results/gaps/disk_1Mjup_gap.json

# ── Cosmological simulations ────────────────────────────────────────────────
# Read Magneticum snapshot and compute halo mass function
python src/analysis/snap.py --snap data/snapshots/snap_144 \
    --box 352 --out results/populations/hmf_z0.json

# ── Atmospheric retrievals ──────────────────────────────────────────────────
# Run petitRADTRANS CCF on a CRIRES+ spectrum
python src/analysis/retrieval.py --obs data/spectra/obs/wasp189b_K.fits \
    --species CO H2O Fe --mode emission \
    --out results/fits/wasp189b_ccf.json

# Run full nested-sampling retrieval (dynesty)
python src/mcmc/sample.py --config results/fits/wasp189b_ccf.json \
    --sampler dynesty --nlive 500 --out results/mcmc/wasp189b_chains.h5

# ── X-ray spectral fitting ──────────────────────────────────────────────────
# Extract spectra for a given region
python src/reduction/xmm_reduce.py --obsid <0123456789> --out data/spectra/

# Run Sherpa fit
python src/analysis/spectral.py --spec data/spectra/core --model tbabs_apec \
    --nh 4.6e20 --redshift 0.091 --out results/fits/core.json

# ── MCMC (general) ──────────────────────────────────────────────────────────
python src/mcmc/sample.py --config results/fits/core.json \
    --sampler emcee --nwalkers 64 --nsteps 5000 \
    --out results/mcmc/core_chains.h5
```

---

## Agent behaviour rules (project-specific additions)

1. **Spectral fitting**: Always run `fit.py` on a single test spectrum
   (`data/spectra/bkg_region/`) before running on the full grid.
2. **MCMC**: Always set and log a random seed. Default: `seed = 42`.
   Store it in the output HDF5 as an attribute.
3. **Figures**: Use the colour scale defined in `src/utils/style.py`.
   Do not override it without discussion.
4. **Results files**: Write to `results/<category>/<descriptive_name>.json`
   or `.h5`. Never overwrite an existing results file — append a timestamp
   suffix instead: `core_fit_20260515.json`.
5. **ADS citations**: When adding a new reference, always call the ADS MCP
   `get_bibtex` tool and append the result to `paper/bibliography.bib`.

---

## MCP servers configured for this project

See `.vscode/settings.json` for the full MCP configuration.

| Server | Purpose | Requires |
|--------|---------|---------|
| `cbyrohl/mcp-server-ads` | Literature search, BibTeX retrieval | `ADS_API_TOKEN` env var |
| `adamzacharia/alma_mcp` | ALMA archive queries (if needed) | `ALMA_TOKEN` env var |

To get an ADS API token: https://ui.adsabs.harvard.edu/user/settings/token
