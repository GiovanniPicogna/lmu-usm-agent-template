---
name: sherpa
description: >
  X-ray spectral fitting using CIAO Sherpa for XMM-Newton, Chandra, and
  eROSITA data. Load PHA spectra with ARF/RMF responses, define spectral
  models (TBabs*apec, TBabs*powerlaw, etc.), fit with C-stat, compute
  confidence intervals, and produce publication-quality spectral plots.
  Trigger phrases: sherpa, Sherpa, CIAO, X-ray spectral fitting, PHA spectrum,
  TBabs, apec, xspec, C-stat, fit spectrum, confidence interval, spectral model,
  fit .pha file, load_pha, set_model, fit(), conf(), covar(), plot_fit,
  XMM-Newton spectrum, Chandra spectrum, eROSITA spectrum, EPIC-pn, ACIS-S.
  Do NOT trigger for X-ray imaging analysis (use yt skill) or
  Python-only XSPEC via PyXSPEC (use this skill — it wraps both).
argument-hint: "Spectrum directory or .pha path and model, e.g. 'data/spectra/core/ --model tbabs*apec'"
---

# Sherpa Skill
# Freeman et al. 2001, SPIE 4477  •  https://cxc.cfa.harvard.edu/sherpa/
# Covers Sherpa 4.16+ (CIAO 4.16+)

---

## When to Use

- Fit absorbed thermal plasma models (TBabs * apec) to ICM spectra
- Fit absorbed power-law models (TBabs * powerlaw) to AGN spectra
- Fit multi-temperature or multi-component models (apec + apec, apec + powerlaw)
- Compute confidence intervals with `conf()` (more accurate than `covar()`)
- Perform spatially resolved spectral analysis (spectral mapping)
- Do **NOT** use for purely imaging-based analysis — use `yt` skill for those
- Do **NOT** use if counts < 10 per bin — flag and warn, report to user

## Procedure

1. Collect parameters. Read `references/parameters.md` for the full table.
   Confirm: spectrum path, background file, ARF/RMF paths, model string,
   `nH` (from `AGENTS.md` or HI4PI), redshift, fitting band.

2. Call the run script:
   ```bash
   python ~/.agents/skills/sherpa/scripts/run_sherpa.py \
       --spec data/spectra/core/core_src.pha \
       --bkg  data/spectra/core/core_bkg.pha \
       --model "tbabs*apec" \
       --nh 4.6e20 \
       --redshift 0.091 \
       --emin 0.5 --emax 7.0 \
       --out results/fits/core_fit.json
   ```
   Or via `--json`:
   ```bash
   python ~/.agents/skills/sherpa/scripts/run_sherpa.py \
       --json '{"spec": "data/spectra/core/core_src.pha",
                "bkg":  "data/spectra/core/core_bkg.pha",
                "model": "tbabs*apec",
                "nh": 4.6e20,
                "redshift": 0.091,
                "emin": 0.5, "emax": 7.0,
                "out": "results/fits/core_fit.json"}'
   ```

3. Parse the last line: `SUCCESS: stat=<cstat_val> dof=<int>` or `ERROR: <msg>`.
   On error, correct parameters and retry once; report traceback if still failing.

## Sherpa workflow

```python
from sherpa.astro.ui import *
import json, datetime

# ── Load data ────────────────────────────────────────────────────────────
load_pha(1, "data/spectra/core/core_src.pha")
load_bkg(1, "data/spectra/core/core_bkg.pha")

# ── Filter energy band ───────────────────────────────────────────────────
notice_id(1, 0.5, 7.0)       # keV

# ── Define model ─────────────────────────────────────────────────────────
set_model(1, xstbabs.abs1 * xsapec.plasma1)

# Always fix nH from AGENTS.md / HI4PI — never leave it free unless justified
abs1.nH = 0.046               # in units of 10²² cm⁻² → nH = 4.6×10²⁰ cm⁻²
abs1.nH.freeze()

plasma1.redshift = 0.091
plasma1.redshift.freeze()
plasma1.Abundanc = 0.3        # typical ICM metallicity — thaw if needed

# ── Set statistic — ALWAYS C-stat for PHA data ───────────────────────────
set_stat("cstat")             # NEVER chi2 for unbinned or low-count data
set_method("neldermead")      # robust for initial convergence

# ── Fit ───────────────────────────────────────────────────────────────────
fit(1)

# ── Confidence intervals at 90 % (X-ray astronomy standard) ────────────
# Note: 90 % CI is the standard for X-ray spectral fitting, consistent
# with the group convention in copilot-instructions.md §3.
set_conf_opt("sigma", 1.645)   # 90 % for 1 parameter of interest
conf(1)

# ── Sanity checks ────────────────────────────────────────────────────────
fit_result = get_fit_results()
assert fit_result.succeeded, "Fit did not converge"
assert fit_result.statval / fit_result.numpoints < 2, \
    f"Poor fit: C-stat/counts = {fit_result.statval/fit_result.numpoints:.2f}"

kT = plasma1.kT.val
assert 0.1 <= kT <= 20, f"kT = {kT} keV outside physical range [0.1, 20]"

# ── Save results ──────────────────────────────────────────────────────────
result = {
    "schema": "SpectralFitHandoff/v1",
    "spectrum_file": "data/spectra/core/core_src.pha",
    "model": "tbabs*apec",
    "best_fit": {
        "kT":  {"value": plasma1.kT.val,  "unit": "keV",    "frozen": False},
        "norm":{"value": plasma1.norm.val, "unit": "cm-5",   "frozen": False},
        "nH":  {"value": abs1.nH.val,      "unit": "1e22/cm2","frozen": True},
    },
    "fit_statistic": {
        "stat": "cstat",
        "value": fit_result.statval,
        "dof": fit_result.dof,
    },
    "fit_passed_sanity": True,
    "warnings": [],
}
# Write to timestamped file — never overwrite existing results
import pathlib
out = pathlib.Path(f"results/fits/core_fit_{datetime.date.today():%Y%m%d}.json")
out.write_text(json.dumps(result, indent=2))
print(f"SUCCESS: stat={fit_result.statval:.2f} dof={fit_result.dof}")
```

## Common model strings

| Science case | Model | Notes |
|---|---|---|
| ICM (single T) | `tbabs * apec` | Fix nH, redshift; thaw kT, norm |
| ICM (two T) | `tbabs * (apec + apec)` | Use for cool-core clusters |
| AGN power-law | `tbabs * powerlaw` | Fix nH; thaw Γ, norm |
| AGN + soft excess | `tbabs * (apec + powerlaw)` | kT typically 0.1–0.3 keV |
| Galactic diffuse | `apec` | No TBabs if foreground only |

## Parameters

> Full table with types, defaults, and constraints: [`references/parameters.md`](references/parameters.md)

**Key parameters:**
`spec` · `bkg` · `arf` · `rmf` · `model` · `nh` (cm⁻², scalar) ·
`redshift` · `emin` · `emax` · `abundances` (default `aspl` = Asplund 2009) ·
`conf_sigma` (default 1.645 = 90%) · `out`

## Sanity checks

- **Statistic**: always `cstat` for PHA fits. Never `chi2` unless data
  has been optimally grouped to ≥ 25 counts per bin (and even then prefer C-stat).
- **kT**: 0.1–20 keV. Flag if < 0.1 keV (unphysical for clusters) or > 20 keV.
- **Photon index Γ**: 1–4 for power-law fits. Flag if outside.
- **C-stat / dof** (approximate): warn if > 2.
- **nH**: always fixed from HI4PI (2016A&A...594A.116H) unless the fit
  explicitly requires a free column (e.g., intrinsic absorption).
- **Abundances**: use Asplund 2009 (2009ARA&A..47..481A) by default.
  Record in output if different.
- **Confidence intervals**: **90 % (1.645σ)** is the X-ray astronomy
  standard. State this in comments and output metadata.

## Confidence intervals — 90 % convention

X-ray spectral fitting reports **90 % confidence intervals** as the
group standard (see `copilot-instructions.md` §3). This differs from the
68 % (1σ) convention used for MCMC posteriors. Always label which
convention is used in result JSON and figure captions.

## Mandatory workflow

For every Sherpa spectral fitting task, follow this sequence:

1. **Confirm** spectrum, background, ARF/RMF paths, model string, `nH`, redshift, and fitting band.
2. **Read `references/parameters.md`** to verify all parameter names and valid ranges.
3. **Run on a single test spectrum** (`data/spectra/bkg_region/`) before running on the full grid.
4. **Check fit statistic** (C-stat preferred; never χ² when counts < 25 per bin).
5. **Emit `SpectralFitHandoff/v1`** after a converged fit; set `fit_passed_sanity: true` only after physical plausibility check.

---

## Iron rules

- Always use **C-stat** when counts per bin < 25; never use χ² silently.
- `nH` must be fixed from HI4PI (2016A&A...594A.116H) unless a free column is physically motivated.
- Report **90 % confidence intervals** (X-ray astronomy standard) — always label this in output.
- Reject runs with fewer than 10 counts per bin; flag and warn the user.
- Never invent observation metadata (ObsID, exposure time, calibration version) — read from FITS headers.

---

## References

- Freeman et al. 2001, SPIE 4477 — verify bibcode via ADS
- HI4PI Collaboration 2016, A&A 594 A116 — 2016A&A...594A.116H (nH source)
- Asplund et al. 2009, ARA&A 47 481 — 2009ARA&A..47..481A (abundances)
