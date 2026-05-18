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
├── agents/
│   ├── literature-agent.agent.md   # @literature-agent: ADS search & BibTeX
│   ├── simulation-agent.agent.md   # @simulation-agent: FARGO3D/PLUTO/Magneticum
│   ├── retrieval-agent.agent.md    # @retrieval-agent: petitRADTRANS CCF & dynesty
│   ├── spectral-agent.agent.md     # @spectral-agent: X-ray Sherpa/PyXSPEC fitting
│   └── mcmc-agent.agent.md         # @mcmc-agent: emcee/dynesty sampling & corner plots
├── workflows/
│   ├── pre-commit.yml              # CI: runs hooks on every PR
│   └── pages.yml                   # CI: builds & deploys GitHub Pages
├── dependabot.yml                  # Auto-updates Actions & pre-commit pins
└── ISSUE_TEMPLATE/
    ├── new_agent.yml               # Structured form to propose a new agent
    └── bug_report.yml              # Bug report form

.vscode/
└── settings.json             # MCP server config (ADS + optional others)

AGENTS.md                     # Project-specific context (fill in per project)
.gitignore                    # Astrophysics-aware gitignore
.pre-commit-config.yaml       # black, flake8, file-size guard, BibTeX DOI check
docs/                         # GitHub Pages site (Jekyll / minima)
├── index.md                  #   Landing page
├── agents.md                 #   Specialist agent documentation
├── skills.md                 #   Recommended agent skills by domain
└── _config.yml               #   Jekyll configuration
envs/
└── base.yml                  # Conda environment (Python 3.11 + full astro stack)
prompts/
└── TEMPLATE.md               # Prompt log template (copy for each task)
src/
└── utils/                    # Shared helpers (units, plotting, constants)
                              # Add domain subdirs as needed — see AGENTS.md
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

### 2. Set up the environment and pre-commit hooks

```bash
conda env create -f envs/base.yml
conda activate lmu-astro
pre-commit install          # installs hooks into .git/hooks/ — run once
```

After this, every `git commit` will automatically run `black`, `flake8`,
file-size checks, and BibTeX DOI validation — giving you instant local
feedback before pushing. The same checks also run in CI on every PR, so
collaborators who skip this step are still caught.

To run the hooks manually on all files at any time:

```bash
pre-commit run --all-files
```

### 3. Fill in AGENTS.md

Open `AGENTS.md` and replace every `<PLACEHOLDER>` with your project's
actual values: target name, ObsIDs, spectral model, redshift, nH, etc.

### 4. Set your ADS API token

```bash
# Add to your ~/.bashrc or ~/.zshrc:
export ADS_API_TOKEN="your_token_here"
# Get your token at: https://ui.adsabs.harvard.edu/user/settings/token
```

### 5. Open the project in VS Code

The MCP server starts automatically when VS Code loads. To verify:
- Open Copilot Chat
- Type: `@ads search_papers query:"intracluster medium sloshing" limit:3`
- You should get real ADS results, not hallucinated ones.

### 6. Use the specialist agents

In Copilot Chat or Agent Mode:

```
@literature-agent  Find all papers citing 2025A&A...703A.270R since 2025
                   and add them to paper/bibliography.bib

@simulation-agent  Read all FARGO3D snapshots in data/runs/disk_1Mjup/
                   and compute the azimuthally averaged gap depth as a
                   function of time for planet 0. Save to results/gaps/.

@simulation-agent  Load the Magneticum Box2/hr snapshot at z=0 and plot
                   the projected gas temperature map centred on the most
                   massive cluster. Save to plots/cosmo/.

@retrieval-agent   Run a petitRADTRANS CCF pipeline on
                   data/spectra/obs/wasp189b_K.fits using CO and H2O
                   templates. Parameters are in AGENTS.md.

@retrieval-agent   Execute a dynesty retrieval for WASP-189b (emission,
                   K-band) with nlive=500. Use the forward model in
                   src/analysis/retrieval.py.

@spectral-agent    Fit an absorbed APEC model to data/spectra/core/
                   using the parameters in AGENTS.md

@mcmc-agent        Sample posteriors for the core region fit in
                   results/fits/core.json and produce a corner plot
```

### 7. Log your prompts

Prompt logging is **automatic** whenever you use Agent Mode — the
instruction to create `prompts/<task>_<date>.md` as the first action
is in `.github/copilot-instructions.md`, which is loaded by every agent
(default Copilot agent and all specialist agents alike). You only need
to commit the file.

Here is the complete flow using `@spectral-agent` as an example:

**Step 1 — invoke the agent:**
```
@spectral-agent  Fit an absorbed apec model to data/spectra/obs/cluster_core/
                 in the 0.5–7.0 keV band. Parameters are in AGENTS.md.
```

**Step 2 — the agent's first action (automatic):**
Before touching any data, the agent runs:
```bash
cp prompts/TEMPLATE.md prompts/spectral_fit_cluster_core_20260515.md
```
and pre-fills the Metadata block and your exact prompt. It completes
the Output files table and validation checklist when the task finishes.

**Step 3 — commit everything together:**
```bash
git add prompts/spectral_fit_cluster_core_20260515.md \
        src/spectral/fit_core.py \
        results/fits/cluster_core.json \
        plots/cluster_core_spectrum.pdf
git commit -m "feat: X-ray spectral fit of cluster core [AI-assisted, claude-sonnet-4-6]"
```

**Step 4 — cite in your Methods section:**
> "Analysis scripts were drafted with GitHub Copilot (claude-sonnet-4-6,
> May 2026, VS Code Agent Mode). The exact prompts and all generated files
> are archived in `prompts/spectral_fit_cluster_core_20260515.md`
> (commit `abc1234`)."

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

## Agent skills

Skills are reusable instruction packages that extend the agent for specific
tasks without bloating the baseline. Install from:

→ **[K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)**

In Copilot Chat, activate a skill by name:
```
Use the scientific-visualization skill for this figure.
```

Recommended skills by domain are listed in
[`docs/skills.md`](https://giovannipicogna.github.io/lmu-usm-agent-template/skills)
and in §11 of `.github/copilot-instructions.md`.

---

## GitHub Pages

The `docs/` folder is automatically deployed to GitHub Pages on every push to `main`.

→ **https://giovannipicogna.github.io/lmu-usm-agent-template**

To enable Pages in a fork or your own copy of this template:
1. Go to **Settings → Pages**
2. Set **Source** to `GitHub Actions`
3. Push any change to trigger the first build

To add the presentation slides to the site, export the latest version
as PDF and commit it to `docs/`:
```bash
cp AI_Agents_Astrophysics_v4.pdf docs/slides.pdf
git add docs/slides.pdf && git commit -m "docs: add presentation slides"
```
Then link it from `docs/index.md`.

---

## Contributing

Suggestions and improvements welcome. Open an issue or PR.
Particularly useful additions:
- Agent for optical/radio image processing (`@imaging-agent`)
- NIRVANA-III output readers for disk simulations (name-dropped in `@simulation-agent` but not yet implemented)
- DustPy post-processing helpers (gap depth, drift flux, SED generation)
- Magneticum weak-lensing / SZ mock-observation pipeline
- GCM post-processing for hot-Jupiter atmospheric dynamics
- Euclid / DES weak-lensing pipeline integration
- A Chandra/CIAO reduction workflow example
