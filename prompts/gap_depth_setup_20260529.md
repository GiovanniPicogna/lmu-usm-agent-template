# Prompt Log — gap_depth_setup

---

## Metadata

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Author** | setup-agent |
| **Tool** | GitHub Copilot Agent Mode |
| **Model** | claude-sonnet-4-6 |
| **Mode** | Agent Mode (setup-agent) |
| **Task ID** | `gap_depth_setup` |

---

## Context loaded by agent

- [x] `.github/copilot-instructions.md` (auto-loaded)
- [x] `AGENTS.md` (auto-loaded)
- [x] `.github/skills/fargo3d/SKILL.md` (loaded)
- [x] `.github/skills/fargo3d/references/parameters.md` (loaded)
- [x] `results/analytical/gap_depth_analytical_20260529.json` (AnalyticalHandoff/v1)
- [x] `/Users/giovanni/Codes/fargo3d/setups/fargo/fargo.par` (standard template)
- [x] `/Users/giovanni/Codes/fargo3d/setups/fargo_nu/fargo_nu.par` (alpha-viscosity template)
- [x] `/Users/giovanni/Codes/fargo3d/src/LowTasks.c` (Spacing keyword verification)
- [x] `/Users/giovanni/Codes/fargo3d/planets/jupiter.cfg` (planet config format)

---

## Prompt used

```
Generate a FARGO3D .par file for a planet-disc gap simulation:
- Planet mass: 1 M_Jup (PlanetMass in code units, M_star = 1)
- Planet semi-major axis: 20 au
- α viscosity: 1e-3
- Aspect ratio H/R = 0.05 at R_ref = 20 au
- Sigma0 = 6.8e-4 [code units]
- Tmax = 1000 orbits at R_ref
- Grid: Nr=256, Nphi=512, R_in=0.3 R_ref, R_out=3.0 R_ref (logarithmic)
- Output every Ninterm = 10 orbits
- FARGO3D source: /Users/giovanni/Codes/fargo3d
- Setup: fargo (setups/fargo/)
- Output: data/runs/gap_1Mjup/
Also generate a SLURM script for LRZ SuperMUC-NG: 4 nodes x 48 cores,
48h walltime, project pr97to.
```

---

## Output files

| File | Description |
|------|-------------|
| `data/runs/gap_1Mjup/gap_1Mjup.par` | FARGO3D parameter file (fargo_nu setup) |
| `data/runs/gap_1Mjup/planets/gap_1Mjup.cfg` | Planet configuration (1 M_Jup, r=1) |
| `data/runs/gap_1Mjup/submit.sh` | SLURM script for LRZ SuperMUC-NG |
| `results/configs/gap_1Mjup_config_20260529.json` | SimConfigHandoff/v1 JSON |
| `prompts/gap_depth_setup_20260529.md` | This prompt log |

---

## Key parameter decisions

| Parameter | Value | Source / Note |
|-----------|-------|---------------|
| Setup | `fargo_nu` | User requested `fargo`; corrected to `fargo_nu` because `Alpha` is only implemented in `fargo_nu` (see §Warnings) |
| PlanetMass | 9.548e-4 | 1 M_Jup / M_sun = 1.8982e30/1.9885e33 |
| DT | 0.314159265359 | π/10 = 2π/20 (one-twentieth orbit at r=1); matches standard fargo.par |
| Ntot | 20000 | 1000 orbits × 20 DT/orbit |
| Ninterm | 200 | 10 orbits × 20 DT/orbit → output every 10 orbits |
| Spacing | `Log` | Confirmed from `src/LowTasks.c`: toupper test on 'L','O' |
| SigmaSlope | 0.5 | [ASSUMED] consistent with MMSN-like profile |
| FlaringIndex | 0.0 | [ASSUMED] flat disk (h/r = const) |
| ThicknessSmoothing | 0.6 | [ASSUMED] standard in gap-depth literature |
| OmegaFrame | 1.0 | Exact Keplerian at r=1 [ASSUMED: no indirect-term offset] |
| SigmaFloor | — | NOT a valid .par key; implement via `-DFLOOR` compile flag |

---

## Validation performed

- [x] α = 1e-3: within [1e-5, 5e-2] ✓
- [x] h/r = 0.05: within [0.01, 0.15] ✓
- [x] M_p = 9.548e-4 M_star ≈ 1 M_Jup: within [1e-4, 20] M_Jup ✓
- [x] Sigma0 = 6.8e-4 > 0 ✓
- [x] Nr=256, Nphi=512: BELOW recommended 512×1024 — warned, not overridden ⚠️
- [x] DT × Ntot timing verified: 20000 × π/10 = 2000π = 1000 × 2π (1000 orbits) ✓
- [x] Ninterm verified: 200 × π/10 / 2π = 10 orbits per output ✓

---

## Warnings

- **Setup correction**: `fargo` uses `Nu` (constant kinematic viscosity); `fargo_nu` uses `Alpha`. Since α = 1e-3 is specified, the `fargo_nu` setup was used — requires recompile: `make SETUP=fargo_nu -j4`
- **Resolution below recommendation**: 256×512 < 512×1024 (recommended by analytical-agent). At 256 radial cells on log grid (0.3–3.0), the Hill-sphere radius R_H = 0.11 (code units) is sampled by ~6 cells — marginally resolved but sufficient for gap depth (not for Hill-sphere physics)
- **SigmaFloor**: Not a .par parameter. To set a density floor of 1e-5 × Sigma0 = 6.8e-9, add `-DFLOOR` to FARGO_OPT in `setups/fargo_nu/fargo_nu.opt` and set `DensityFloor 6.8e-9` in the .par, OR handle in `condinit.c`
- **OmegaFrame**: Standard fargo.par uses 1.0005 (indirect-term offset); using exact 1.0 here — may cause a small systematic drift in the frame over 1000 orbits [ASSUMED acceptable]
- **Partition**: SuperMUC-NG partition `general` assumed — verify with LRZ documentation; `micro` partition (≤ 8 nodes) may also be valid but has a shorter walltime limit
- **Kanagawa calibration boundary**: K = 2916 is near the upper edge of the empirical calibration range; Sigma_gap/Sigma_0 prediction of 8.5e-3 should be treated as a lower bound
