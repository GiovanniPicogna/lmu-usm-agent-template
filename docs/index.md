---
layout: home
title: Home
nav_order: 1
---

# LMU USM — AI Agent Configuration Template

A community template for using GitHub Copilot (and other AI coding agents)
in reproducible, citable astrophysics research at
**LMU Munich / Universitäts-Sternwarte München**.

**Template version**: 1.0 (May 2026) · **Status**: community draft

USM produces ~200 refereed astronomy papers per year (1,016 in 2021–2026 via NASA ADS).
Primary publication venues: *Astronomy & Astrophysics* (~54%), *MNRAS* (~16%), *ApJ* family (~11%), *Physical Review D* + *JCAP* (~10%).

[View on GitHub](https://github.com/GiovanniPicogna/lmu-usm-agent-template){: .btn }
[Use this template](https://github.com/GiovanniPicogna/lmu-usm-agent-template/generate){: .btn .btn-primary }
[▶ View Slides](slides.html){: .btn }
[📋 Pre-Meeting Poll](poll.html){: .btn }

---

## Presentation: AI Agents — How We Use Them, How We Cite Them

*Code & Coffee, LMU Astrophysics Department, May 2026*

A 30-slide reveal.js presentation covering GitHub Copilot Agent Mode, MCP & the ADS
server, pitfalls in AI-assisted research, reproducibility best practices, and journal
disclosure policies (MNRAS, A&A, ApJ, Nature, Science).

[▶ Open full-screen slides](slides.html){: .btn .btn-primary }

---

## What problem does this solve?

Without a shared baseline, every researcher using AI agents in their project
re-invents the same rules — how to cite references safely, how to avoid
uploading proprietary data, what unit conventions to use, how to log prompts
for reproducibility. Errors creep in; results become hard to reproduce.

This template encodes **group-level conventions** once so that every
Copilot / Claude / Gemini session starts from the same safe, reproducible baseline.

---

## Research domains covered

| Domain | Key codes |
|--------|-----------|
| Disk & planet formation | FARGO3D · PLUTO · NIRVANA-III · DustPy · RADMC-3D |
| Cosmological simulations | Magneticum · GADGET · yt · GadgetIO.jl |
| Exoplanet atmospheres | petitRADTRANS · CCF · dynesty · CARMENES · CRIRES+ · JWST |
| Large-scale structure | void statistics · SBI · Euclid pipelines |
| X-ray & galaxy clusters | XMM-Newton · Chandra · eROSITA · Sherpa · PyXSPEC |

---

## Specialist agents

| Agent | Invocation | Purpose |
|-------|-----------|---------|
| Literature | `@literature-agent` | ADS search, BibTeX retrieval |
| Simulation | `@simulation-agent` | FARGO3D / PLUTO / Magneticum I/O and post-processing |
| Retrieval | `@retrieval-agent` | petitRADTRANS forward model, CCF, dynesty |
| Spectral | `@spectral-agent` | X-ray Sherpa / PyXSPEC fitting |
| MCMC | `@mcmc-agent` | emcee / dynesty sampling, corner plots |
| Paper | `@paper-agent` | LaTeX manuscript drafting, ADS citations, compile + auto-review |

See the [Agents page](agents) for full documentation and example invocations.

---

## Quick start

```bash
# 1. Create your project from this template (click "Use this template" above)

# 2. Set up the conda environment
conda env create -f envs/base.yml
conda activate lmu-astro
pre-commit install

# 3. Fill in AGENTS.md with your project context
# 4. Set your ADS API token
export ADS_API_TOKEN="your_token_here"
# Get it at: https://ui.adsabs.harvard.edu/user/settings/token

# 5. Open in VS Code — Copilot loads the baseline automatically
```

---

## Safety rules built in

- **References**: never invented — always queried from the ADS MCP server
- **Proprietary data**: raw FITS / event lists are git-ignored by default
- **Reproducibility**: every agent task is logged in `prompts/`
- **CI**: black · flake8 · file-size guard · BibTeX DOI check run on every commit

---

## Agent skills

This template is designed to work with the
[K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)
skill library. Skills extend the agent's capabilities for specific tasks
(publication figures, literature reviews, statistical tests, etc.)
without cluttering the baseline instructions.

Recommended skills for USM groups are documented in
[`.github/copilot-instructions.md §11`](https://github.com/GiovanniPicogna/lmu-usm-agent-template/blob/main/.github/copilot-instructions.md).

---

## Contributing

Open an issue or PR on [GitHub](https://github.com/GiovanniPicogna/lmu-usm-agent-template).
All USM group members are welcome to contribute agents, skills recommendations,
or domain-specific AGENTS.md templates.
