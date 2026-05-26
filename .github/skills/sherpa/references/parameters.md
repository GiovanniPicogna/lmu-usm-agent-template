# Sherpa Parameters Reference

Full parameter table for `run_sherpa.py`.

---

## Required parameters

| Parameter | Type | Description |
|---|---|---|
| `spec` | `str` | Path to source PHA spectrum file (`.pha`) |
| `model` | `str` | Model string: e.g. `"tbabs*apec"`, `"tbabs*(apec+apec)"`, `"tbabs*powerlaw"` |
| `nh` | `float` | Galactic hydrogen column density in cm⁻² (e.g. `4.6e20`). Always read from `AGENTS.md` or HI4PI catalogue. |
| `out` | `str` | Output path for JSON result file |

## Optional parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `bkg` | `str \| null` | `null` | Background PHA file path (highly recommended for source extraction regions) |
| `arf` | `str \| null` | `null` | ARF file path. If null, script searches for `*.arf` in same directory as `spec` |
| `rmf` | `str \| null` | `null` | RMF file path. If null, script searches for `*.rmf` |
| `redshift` | `float` | `0.0` | Source redshift (applied to all spectral models) |
| `emin` | `float` | `0.5` | Minimum fitting energy in keV |
| `emax` | `float` | `7.0` | Maximum fitting energy in keV. Use 8.0 for Chandra ACIS-S |
| `abundances` | `str` | `"aspl"` | Abundance table: `aspl` (Asplund 2009, default) \| `angr` \| `wilm` |
| `stat` | `str` | `"cstat"` | Fit statistic: `cstat` (default, always for PHA data) \| `chi2gehrels` (only if ≥25 counts/bin) |
| `method` | `str` | `"neldermead"` | Optimisation: `neldermead` \| `levmar` \| `moncar` |
| `conf_sigma` | `float` | `1.645` | Confidence level in σ. Default 1.645 = 90% (X-ray astronomy standard) |
| `thaw_nh` | `bool` | `false` | Thaw nH in fit (only for intrinsic absorption studies; document reason) |
| `thaw_redshift` | `bool` | `false` | Thaw redshift (only if photometric z) |
| `abund_free` | `bool` | `false` | Thaw metallicity / Fe abundance |
| `grouping` | `int \| null` | `null` | Minimum counts per bin for grouping. If null, use unbinned data with C-stat |
| `kT_init` | `float` | `3.0` | Initial temperature guess in keV (for apec component) |
| `Gamma_init` | `float` | `1.8` | Initial photon index (for powerlaw component) |
| `norm_init` | `float` | `1e-4` | Initial normalisation for apec/powerlaw |
| `plot` | `bool` | `true` | Generate and save spectral plot to `plots/xray/<spec_name>_fit.pdf` |
| `verbose` | `bool` | `false` | Print Sherpa session log to stdout |

## Confidence interval convention

**Default `conf_sigma = 1.645` corresponds to 90% confidence** for
one parameter of interest (Δχ² = 2.706 / ΔC = 2.706).
This is the standard in X-ray astronomy (Chandra, XMM-Newton, eROSITA).

To obtain 68% (1σ) intervals (for comparison with MCMC posteriors), set:
```
conf_sigma = 1.0
```
Always document which convention is used in result files and figure captions.

## Supported model components (XSPEC models via Sherpa)

| Component | Sherpa name | Use |
|---|---|---|
| Galactic absorption | `xstbabs` | Milky Way ISM absorption (always use; fix nH) |
| Thermal plasma (single T) | `xsapec` | ICM, stellar corona, warm gas |
| Thermal plasma (multi-T) | `xsvapec` | Variable-abundance version of apec |
| Bremsstrahlung | `xsbremss` | Simple continuum approximation |
| Power law | `xspowerlaw` | AGN, non-thermal emission |
| Blackbody | `xsbbody` | Soft excess, NStar |
| Cold absorption | `xsphabs` | Alternative to TBabs; use TBabs by default |
| Partial covering | `xspcfabs` | Warm absorber, AGN |

## Constraints

- **Statistic**: must be `cstat` for unbinned PHA data. If grouped (≥25 cts/bin),
  `chi2gehrels` is acceptable but `cstat` is preferred.
- `emin` ≥ 0.3 keV for XMM EPIC-pn (below is calibration-uncertain).
- `emax` ≤ 10.0 keV for standard EPIC/ACIS analysis.
- `kT` fit result: warn if < 0.1 keV (suggests wrong model) or > 20 keV (poorly constrained).
- `Gamma` fit result: warn if < 1.0 or > 4.0.
- `nh` must never be set to 0. Minimum: 1e18 cm⁻².
- Results file must use timestamped filename: `<name>_fit_<YYYYMMDD>.json`.
  Never overwrite an existing result.
