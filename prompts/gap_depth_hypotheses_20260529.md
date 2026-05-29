# Prompt Log Template
#
# File:    prompts/TEMPLATE.md
# Purpose: Copy this file for each agent-assisted analysis task.
#          Rename to: prompts/<task_name>_<YYYYMMDD>.md
#          Commit alongside the code it generated.
#
# Why this matters: AI outputs are non-deterministic. This file is the
# provenance record that makes your AI-assisted analysis reproducible
# and disclosable in your Methods section.

---

## Metadata

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Author** | hypothesis-agent |
| **Tool** | GitHub Copilot Agent Mode |
| **Model** | claude-sonnet-4-6 |
| **Mode** | Agent Mode (hypothesis-agent) |
| **VS Code version** | latest |
| **Task ID** | `gap_depth_hypotheses` |

---

## Context loaded by agent

List files or context the agent had access to:

- [x] `.github/copilot-instructions.md` (auto-loaded)
- [x] `AGENTS.md` (auto-loaded)
- [x] ADS MCP: Kanagawa et al. 2015, 2016, 2017; Fung et al. 2014; Birnstiel et al. 2012; Stammler et al. 2023; Drążkowska et al. 2019; Zhang et al. 2018 (DSHARP); Tanaka et al. 2022

---

## Prompt(s) used

Copy the exact prompt(s) you gave the agent. If you iterated, include
each exchange in order.

### Prompt 1

```
You are the @hypothesis-agent for the LMU Astrophysics group.

Science question: "What mechanisms set the depth of a planet-carved gap in a
protoplanetary disc? Generate ranked, testable hypotheses varying planet mass,
disc viscosity, and dust fragmentation velocity."

Domain: disk / planet-formation

Instructions:
- Generate 3 ranked hypotheses with novelty and feasibility scores (1–5 each)
- For each hypothesis, state: the physical mechanism, the key parameter being
  varied, the observable prediction, and what simulation would test it
- Cross-check against Kanagawa et al. (2017), Fung et al. (2014), and
  Birnstiel et al. dust trapping literature
- Keep each hypothesis to 3–4 bullet points
- Do NOT invent bibcodes — flag any reference with [VERIFY IN ADS]
- Return ONLY the ranked hypothesis list with scores. No preamble.
```

### Agent response summary

Generated 3 ranked hypotheses (v_frag > α > M_p ordering) grounded in ADS
literature; saved handoff JSON to results/hypotheses/gap_depth_hypotheses_20260529.json.

---

## Output files generated

| File | Description | Committed? |
|------|-------------|-----------|
| `src/spectral/fit.py` | Sherpa fitting pipeline | ✅ yes |
| `results/fits/core.json` | Best-fit parameters | ✅ yes |
| `plots/core_spectrum.pdf` | Spectral fit figure | ✅ yes |
| `data/spectra/core.pha` | Raw spectrum (large) | ❌ git-ignored |

---

## Validation performed

- [ ] Script runs without errors on test data
- [ ] Numerical results match a manual cross-check (describe below)
- [ ] References verified in NASA ADS (no hallucinated citations)
- [ ] Physical results are plausible (state sanity checks below)
- [ ] Random seed logged in output file (if MCMC)
- [ ] No raw data files were modified

**Cross-check details**:

> _e.g. "Ran fit.py on ObsID 0123456789 core region. Agent-generated
> code returns kT = 4.2 ± 0.3 keV, consistent with Sanders et al. 2016
> (kT = 4.1 ± 0.4 keV) within 1σ. Verified by running same fit manually
> in XSPEC."_

---

## Issues found & fixes applied

_Document any errors the agent made and how they were corrected.
This is important provenance — do not delete mistakes from the log._

| Issue | How found | Fix applied |
|-------|-----------|-------------|
| _e.g. Agent used chi2 instead of cstat_ | Manual review | Corrected in fit.py line 47 |

---

## Methods disclosure text

_Draft statement for the paper's Methods section (adapt as needed):_

> "Initial analysis code was drafted with assistance from GitHub Copilot
> (GPT-4o, [MONTH YEAR], VS Code Agent Mode v[VERSION]).
> All code was reviewed, tested against known results, and validated by
> the authors. Literature references were retrieved and verified via the
> NASA ADS API (cbyrohl/mcp-server-ads). The authors take full
> responsibility for the accuracy of all results presented."
