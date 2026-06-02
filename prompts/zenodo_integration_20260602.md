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
| **Mode** | executing-plans (superpowers skill) |
| **VS Code version** | N/A — Claude Code CLI |
| **Task ID** | `zenodo_integration` |

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
Add Zenodo (+ Sandbox) data upload for open research and reproducibility,
inspired by show-your.work. Check the plan devised in
docs/superpowers/plans/2026-06-02-zenodo-integration.md, provide insights
and additions and generate an improved plan.
```

### Agent response summary

v2 plan written fixing 11 defects vs v1 (empty deposits from git-ignored paths,
stale inherited files, no timeouts/retry, no integrity check, no dry-run,
no irreversible-publish guard, fragile CI). Then executed: created 5 source
modules, 66 mocked tests, 1 CI workflow, and updated env/pre-commit/docs.

### Prompt 2

```
/superpowers:executing-plans in docs/superpowers/plans/2026-06-02-zenodo-integration-v2.md
```

---

## Output files generated

| File | Description | Committed? |
|------|-------------|-----------|
| `src/zenodo/client.py` | Resilient Zenodo REST API wrapper | ✅ yes |
| `src/zenodo/config.py` | zenodo.yml + CITATION.cff loader | ✅ yes |
| `src/zenodo/archive.py` | File discovery + deterministic zip bundling | ✅ yes |
| `src/zenodo/upload.py` | Deposit orchestration (plan, version, upload) | ✅ yes |
| `src/zenodo/cli.py` | Click CLI (create/publish/status) | ✅ yes |
| `src/zenodo/__init__.py` | Public re-exports | ✅ yes |
| `src/zenodo/__main__.py` | `python -m src.zenodo` entry point | ✅ yes |
| `tests/zenodo/test_client.py` | 18 client tests (retry, checksum, versioning) | ✅ yes |
| `tests/zenodo/test_config.py` | 20 config tests (CFF, access-right, concept ID) | ✅ yes |
| `tests/zenodo/test_archive.py` | 7 archive tests (collect, bundle, determinism) | ✅ yes |
| `tests/zenodo/test_upload.py` | 11 orchestration tests (plan, clear, bundle) | ✅ yes |
| `tests/zenodo/test_cli.py` | 10 CLI tests (token, guard, dry-run, confirm) | ✅ yes |
| `zenodo.yml` | Project-root upload config template | ✅ yes |
| `.github/workflows/zenodo-upload.yml` | Two-job CI (perms, env gate, tag-safe) | ✅ yes |

---

## Validation performed

- [x] pytest tests/zenodo/ — 66 tests passed (all HTTP mocked)
- [x] pre-commit run check-yaml — zenodo-upload.yml passes
- [x] python -m src.zenodo --help — CLI entry point confirmed
- [x] No references added (no literature search needed for this task)
- [x] No raw data files were modified
- [x] Tokens are read from environment variables only (never hardcoded)

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
