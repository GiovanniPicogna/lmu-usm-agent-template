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
│   ├── mcmc-agent.agent.md         # @mcmc-agent: emcee/dynesty sampling & corner plots
│   └── references/                 # Large code blocks extracted from agent files
│       ├── output_conventions.md   #   FARGO3D/PLUTO/GADGET I/O functions + unit tables
│       └── code_conventions.md     #   Script skeleton, HDF5 saving, figure naming
├── shared/
│   └── handoff_schemas.md          # JSON schemas: Simulation/Spectral/MCMCHandoff v1
├── skills/                         # Bundled simulation launch skills
│   ├── dustpy/
│   │   ├── SKILL.md                #   DustPy: grain growth & radial drift
│   │   ├── references/
│   │   │   └── parameters.md       #   Full parameter table (lean SKILL.md pattern)
│   │   └── scripts/run_dustpy.py   #   Validated runner (Pydantic, SUCCESS/ERROR protocol)
│   ├── fargo3d/
│   │   ├── SKILL.md                #   FARGO3D: planet–disk interaction & gap opening
│   │   ├── references/
│   │   │   └── parameters.md       #   Full parameter table
│   │   └── scripts/run_fargo3d.py  #   Patches .par file, launches simulation
│   └── pluto/
│       ├── SKILL.md                #   PLUTO: HD/MHD disk & jet simulations
│       ├── references/
│       │   ├── parameters.md       #   Full parameter table
│       │   └── examples.md         #   Step-by-step run examples
│       └── scripts/run_pluto.py    #   Patches pluto.ini, launches simulation
├── workflows/
│   ├── pre-commit.yml              # CI: runs hooks on every PR
│   └── pages.yml                   # CI: builds & deploys GitHub Pages
├── dependabot.yml                  # Auto-updates Actions & pre-commit pins
└── ISSUE_TEMPLATE/
    ├── new_agent.yml               # Structured form to propose a new agent
    └── bug_report.yml              # Bug report form

.vscode/
└── settings.json             # MCP server config (ADS + optional others)

ARCHITECTURE.md               # Agent roster, pipeline diagram, handoff schemas overview
CHANGELOG.md                  # Design history (Keep a Changelog format)
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

### Bundled simulation launch skills

This template ships three simulation skills in `.github/skills/`. Each provides
a validated Python runner (`run_<code>.py`) with Pydantic parameter checking and
a `SUCCESS` / `ERROR` exit protocol that `@simulation-agent` parses automatically.

| Skill | Code | Use case | Key parameters | Prerequisite |
|---|---|---|---|---|
| [`dustpy`](.github/skills/dustpy/SKILL.md) | DustPy | Radial dust evolution, grain growth, fragmentation, Stokes numbers | `alpha_viscosity`, `disk_mass_msun`, `t_end_yr`, `snapshot_times_yr` | `pip install dustpy scientific-pydantic` |
| [`fargo3d`](.github/skills/fargo3d/SKILL.md) | FARGO3D | Planet–disk interaction, gap opening, type-I/II migration torques | `par_file`, `Alpha`, `PlanetMass`, `Sigma0`, `AspectRatio`, `Tmax` | Compiled `fargo3d` binary + valid `.par` file |
| [`pluto`](.github/skills/pluto/SKILL.md) | PLUTO | HD/MHD disk or jet simulations; parameter overrides without recompiling | `run_dir`, `tstop`, `CFL`, `[Parameters]` overrides, `n_procs` | Compiled `pluto` binary + valid `pluto.ini` |

Scripts accept individual flags or a single `--json` blob for multi-parameter calls:

```bash
# DustPy — 1 Myr dust evolution run
python .github/skills/dustpy/scripts/run_dustpy.py \
    --json '{"alpha_viscosity": 1e-3, "disk_mass_msun": 0.05, "t_end_yr": 1e6}'

# FARGO3D — planet-gap simulation, overriding planet mass and viscosity
python .github/skills/fargo3d/scripts/run_fargo3d.py \
    --json '{"par_file": "setups/p_gap/p_gap.par", "Alpha": 1e-3, "PlanetMass": 3e-4}'

# PLUTO — HD disk run in an existing compiled directory
python .github/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "runs/disk_gap", "tstop": 500.0, "parameters": {"ALPHA": 1e-3}}'
```

Skill files follow the **lean SKILL.md pattern**: `SKILL.md` contains the essentials
(trigger conditions, procedure, compact parameter summary, output format, error table).
Detailed parameter tables and worked examples live in each skill’s `references/`
subdirectory and are loaded by the agent on demand.

Recommended skills by domain are listed in
[`docs/skills.md`](https://giovannipicogna.github.io/lmu-usm-agent-template/skills)
and in §11 of `.github/copilot-instructions.md`.

---

## Agent reliability design

Each specialist agent includes three anti-failure mechanisms:

### Iron rules
Blockquoted `IRON RULE` markers inside every agent file flag non-negotiable
constraints that must hold even in long conversations (context rot).

| Agent | Critical rules |
|---|---|
| `@simulation-agent` | No hallucinated numbers; read-only by default; test before batch |
| `@spectral-agent` | No hallucinated fit results; C-stat on low counts; model changes need confirmation |
| `@mcmc-agent` | 68% intervals (not 90%); never overwrite chains; convergence before reporting |
| `@retrieval-agent` | No detections without null test; species list from `AGENTS.md`; convergence before reporting |

### Anti-patterns table
Each agent carries a four-row table with columns
*Anti-Pattern | Why It Fails | Correct Behaviour*, providing explicit
negative examples at inference time to counter the most common failure modes.

### Anti-leakage (`[DATA MISSING]`)
Every analysis agent's Role section includes a hard stop:
> If required data is not present in the current session, emit
> `[DATA MISSING: <path or description>]` and stop — do not substitute values from training memory.

`@literature-agent` uses the variant `[CITATION MISSING: <query>]` when ADS
returns no result. These markers make silent hallucination visible: a
`[DATA MISSING]` reply means the agent is correctly refusing to invent data
rather than producing a plausible-looking but fabricated result.

---

## Pipeline architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the complete picture:
Mermaid pipeline diagram, full agent roster table, three data-flow descriptions
(disk simulation, X-ray spectroscopy, atmospheric retrieval), and the quality-gate
summary that maps to the three anti-failure mechanisms above.

### Structured handoffs between agents

When one specialist agent finishes and a downstream agent needs its results, it
emits a **handoff JSON** whose schema is defined in
[`.github/shared/handoff_schemas.md`](.github/shared/handoff_schemas.md).
Three schemas are currently defined:

| Schema | Emitted by | Consumed by |
|---|---|---|
| `SimulationHandoff/v1` | `@simulation-agent` | `@spectral-agent`, `@mcmc-agent` |
| `SpectralFitHandoff/v1` | `@spectral-agent` | `@mcmc-agent` |
| `MCMCHandoff/v1` | `@mcmc-agent` | `@paper-agent`, user |

Each schema includes a `sanity_passed` / `converged` gate: the receiving
agent will refuse to proceed if the gate is `false`.

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
