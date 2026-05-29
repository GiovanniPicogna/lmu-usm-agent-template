# Prompt Log — gap_depth_analytical

---

## Metadata

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Author** | analytical-agent |
| **Tool** | GitHub Copilot Agent Mode |
| **Model** | claude-sonnet-4-6 |
| **Mode** | Agent Mode (analytical-agent) |
| **Task ID** | `gap_depth_analytical` |

---

## Context loaded by agent

- [x] `.github/copilot-instructions.md` (auto-loaded)
- [x] `AGENTS.md` (auto-loaded)
- [x] `results/hypotheses/gap_depth_hypotheses_20260529.json`
- [x] Literature: Kanagawa et al. (2016) PASJ 68, 43 [2016PASJ...68...43K] — K parameter and gap-depth formula

---

## Prompt used

```
Compute the gap-opening mass threshold and expected gap depth for a planet at 20 au
in a protoplanetary disc with α = 1e-3 and H/R = 0.05, using both the Kanagawa et al.
(2017) viscous criterion and the thermal criterion.  Stellar mass M★ = 1 M☉.
```

---

## Output files

| File | Description |
|------|-------------|
| `results/analytical/gap_depth_analytical_20260529.py` | Self-contained benchmark script |
| `results/analytical/gap_depth_analytical_20260529.json` | AnalyticalHandoff/v1 JSON |
| `prompts/gap_depth_analytical_20260529.md` | This prompt log |

---

## Key numerical results

| Quantity | Value | Formula |
|----------|-------|---------|
| M_gap thermal (R_H = H) | **0.393 M_Jup** | 3 M★ h³ |
| M_gap viscous (K = 25) | **0.093 M_Jup** | M★ √(25 h⁵ α) |
| K  (1 M_Jup) | **2916** | q² / (h⁵ α) |
| Σ_gap / Σ_0  (1 M_Jup) | **8.5 × 10⁻³** (118× depletion) | 1/(1 + 0.04K) |
| Regime | **NONLINEAR** (K / K_open = 116.6) | — |

---

## Validation performed

- [x] Script executed with zero errors (`python3 results/analytical/gap_depth_analytical_20260529.py`)
- [x] Units checked via `astropy.units` throughout — no bare floats
- [x] K = 2916 >> 25 → nonlinear flag set in handoff JSON
- [x] q/(3h³) = 2.55 → thermal criterion exceeded by factor ~2.6
- [x] Bibcode 2017PASJ...69...97K marked [VERIFY IN ADS]

---

## Warnings

- Kanagawa 0.04 prefactor from 2D isothermal simulations; 3D/non-isothermal correction ~20–30%
- K = 2916 near upper edge of empirical calibration range; Σ_gap/Σ_0 = 8.5e-3 is a lower bound
- Gap edges likely exceed RWI threshold at this depth (relevant to Hypothesis 2)
