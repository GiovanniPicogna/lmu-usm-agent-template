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
| **Date** | 2026-06-02 |
| **Author** | Giovanni Picogna |
| **Tool** | Claude Code |
| **Model** | read at runtime from $CLAUDE_MODEL |
| **Mode** | referee-agent (ad-hoc, external manuscript) |
| **VS Code version** | N/A — Claude Code CLI |
| **Task ID** | `external_test_swain2026` |

---

## Context loaded by agent

List files or context the agent had access to:

- [ ] `.github/copilot-instructions.md` (auto-loaded)
- [ ] `AGENTS.md` (auto-loaded)
- [ ] Other files explicitly attached: _list here_

---

## Prompt(s) used

Copy the exact prompt(s) you gave the agent. If you iterated, include
each exchange in order.

### Prompt 1

```
use the referee-agent to check this work
/Users/giovanni/anaconda3/envs/py312/lib/python3.12/site-packages/
conversion_results/151610_0_merged_1778386364-1/
151610_0_merged_1778386364-1.md
```

### Agent response summary

_To be completed after the review is returned._

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
