# Prompt Log — FARGO3D Gap Analysis Post-Processing

## Metadata

| Field         | Value                                                    |
|---------------|----------------------------------------------------------|
| Date          | 2026-05-29                                               |
| Tool          | GitHub Copilot Agent Mode (@analysis-agent)              |
| Model         | Claude Sonnet 4.6                                        |
| Task ID       | `fargo_gap_analysis_20260529`                            |
| TDM source    | Local simulation output (not external web scraping)      |

## Prompt(s) used

Post-process FARGO3D disc simulation output from
`/Users/giovanni/Codes/fargo3d/data/runs/fargo_skill_test/`.
Key operations:
1. Read `gasdens0.dat` (shape 128×384) via `numpy.fromfile`
2. Azimuthally average → Σ(r)
3. Extract radial grid from `domain_y.dat` (Ny+1+2×NGHOST=135 entries)
4. Compute gap depth = Σ_gap / Σ₀ (SIGMASLOPE=0 → Σ₀=6.37e-4 everywhere)
5. Read `tqwk0.dat` torques
6. Save JSON summary and dark-background PDF/PNG plot

## Simulation parameters

| Parameter     | Value       |
|---------------|-------------|
| SETUP         | fargo       |
| SIGMA0        | 6.37e-4     |
| SIGMASLOPE    | 0           |
| ASPECTRATIO   | 0.05        |
| NU            | 1e-5        |
| PLANETMASS    | 9.548e-4 M★ |
| SPACING       | Lin         |
| NX (azi)      | 384         |
| NY (rad)      | 128         |
| YMIN/YMAX     | 0.4 / 2.5   |
| Snapshot      | 0 (t=0)     |

## Output files

| File | Description |
|------|-------------|
| `src/analysis/fargo_gap_analysis.py` | Main analysis script |
| `results/analysis/fargo_gap_analysis_20260529.json` | Summary JSON |
| `plots/fargo_sigma_profile.pdf` | Radial Σ(r) profile (PDF) |
| `plots/fargo_sigma_profile.png` | Radial Σ(r) profile (PNG, 300 dpi) |

## Validation performed

- [x] Verified `gasdens0.dat` byte count (393216 B = 128×384×8 B ✓)
- [x] Verified `domain_y.dat` shape (135 = 128 + 2×3 + 1 ✓)
- [x] Grid midpoints fall within [0.4, 2.5] au ✓
- [x] SIGMASLOPE=0 confirmed → Σ₀ = 6.37e-4 (flat profile)
- [x] Snapshot 0 = t=0 (initial condition, no gap expected, ratio ≈ 1)
- [x] JSON output file written and validated
- [x] Plot saved as PDF + PNG at 300 dpi
