# LMU USM — AI Agent Configuration Template

A first-draft template for using GitHub Copilot (and other AI agents)
in a reproducible, citable, and policy-compliant way in astrophysics research
at LMU Munich.

**Status**: community draft — open to contributions from all group members.  
**Maintainer**: LMU Astrophysics Group  
**Template version**: 1.0 (May 2026)

---

## What's in this repo

```
.github/
├── copilot-instructions.md   # Group-wide agent baseline (auto-loaded)
└── agents/
    ├── literature-agent.agent.md   # @literature-agent: ADS search & BibTeX
    └── spectral-agent.agent.md     # @spectral-agent: X-ray fitting pipeline

.vscode/
└── settings.json             # MCP server config (ADS + optional others)

AGENTS.md                     # Project-specific context (fill in per project)
.gitignore                    # Astrophysics-aware gitignore
prompts/
└── TEMPLATE.md               # Prompt log template (copy for each task)
```

---

## Quick start

### 1. Copy this template into your project

```bash
# Option A: use as a GitHub template (click "Use this template" above)

# Option B: copy files manually into an existing repo
cp .github/copilot-instructions.md  your-project/.github/
cp .github/agents/*.md              your-project/.github/agents/
cp .vscode/settings.json            your-project/.vscode/
cp AGENTS.md                        your-project/
cp prompts/TEMPLATE.md              your-project/prompts/
cp .gitignore                       your-project/   # merge carefully
```

### 2. Fill in AGENTS.md

Open `AGENTS.md` and replace every `<PLACEHOLDER>` with your project's
actual values: target name, ObsIDs, spectral model, redshift, nH, etc.

### 3. Set your ADS API token

```bash
# Add to your ~/.bashrc or ~/.zshrc:
export ADS_API_TOKEN="your_token_here"
# Get your token at: https://ui.adsabs.harvard.edu/user/settings/token
```

### 4. Open the project in VS Code

The MCP server starts automatically when VS Code loads. To verify:
- Open Copilot Chat
- Type: `@ads search_papers query:"intracluster medium sloshing" limit:3`
- You should get real ADS results, not hallucinated ones.

### 5. Use the specialist agents

In Copilot Chat or Agent Mode:

```
@literature-agent Find all papers citing 2007PhR...443....1M since 2020
                  and add them to paper/bibliography.bib

@spectral-agent   Fit an absorbed APEC model to data/spectra/core/
                  using the parameters in AGENTS.md
```

### 6. Log your prompts

Every time you use Agent Mode for a science task:

```bash
cp prompts/TEMPLATE.md prompts/spectral_fit_core_20260515.md
# Fill in the fields, then:
git add prompts/spectral_fit_core_20260515.md src/spectral/fit.py
git commit -m "feat: spectral fit of core region [AI-assisted, GPT-4o]"
```

---

## Journal disclosure

Use this text in your Methods section (adapt to your actual usage):

> "Analysis code was drafted with assistance from GitHub Copilot
> (GPT-4o, [Month Year], VS Code Agent Mode). Literature references
> were retrieved and verified via the NASA ADS API
> (cbyrohl/mcp-server-ads). All AI-generated content was reviewed and
> validated by the authors, who take full responsibility for all results."

---

## Security notes

- **Never** put API tokens in any committed file. Use environment variables.
- **Vet third-party agent skill files** before adding them: a malicious
  `.md` instruction file can override your safety rules or exfiltrate data.
  Treat agent files like code — read before you run.
- **Proprietary data**: raw XMM/Chandra observations under embargo must
  never be uploaded to any AI service. The `.gitignore` blocks FITS files
  from being committed, but you must also ensure VS Code's Copilot telemetry
  settings are appropriate for your institution.
  Check: `github.copilot.advanced.shareOpenTabsWithCopilot` (set to `false`
  if working with proprietary data).

---

## Contributing

Suggestions and improvements welcome. Open an issue or PR.
Particularly useful additions:
- Agents for MCMC / posterior analysis (`@mcmc-agent`)
- Agents for image processing (`@imaging-agent`)
- Instructions tuned for radio or optical astronomy
- A Chandra/CIAO reduction workflow example
