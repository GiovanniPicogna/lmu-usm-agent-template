# Changelog

All significant changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [1.2.0] — 2026-05-20

### Added
- `ARCHITECTURE.md` — single source of truth for agent roster, Mermaid
  pipeline diagram, data-flow descriptions, and quality-gate summary.
- `.github/shared/handoff_schemas.md` — explicit JSON schemas
  (`SimulationHandoff/v1`, `SpectralFitHandoff/v1`, `MCMCHandoff/v1`)
  for data passed between specialist agents; includes validation rules.
- `.github/agents/references/output_conventions.md` — FARGO3D, PLUTO,
  and Magneticum/GADGET I/O functions extracted from `simulation-agent.agent.md`.
- `.github/agents/references/code_conventions.md` — argparse skeleton,
  HDF5 saving pattern, and diagnostic figure naming convention.
- `references/parameters.md` under each bundled simulation skill
  (`dustpy`, `fargo3d`, `pluto`) — full parameter tables with types,
  defaults, and constraints, extracted from the SKILL.md files.
- `references/examples.md` under the `pluto` skill — five step-by-step
  run examples plus a table of four standard test problems.
- `CHANGELOG.md` (this file).

### Changed
- `simulation-agent.agent.md` — replaced embedded FARGO3D/PLUTO/GADGET
  code blocks (~80 lines) with compact pointers to `references/`;
  agent file reduced from ~267 to ~190 lines.
- `dustpy/SKILL.md`, `fargo3d/SKILL.md`, `pluto/SKILL.md` — replaced
  inline parameter tables and the PLUTO examples section with pointers
  to `references/` (lean SKILL.md pattern).
- `README.md` — file tree updated with all new directories; new sections
  added for agent reliability design, bundled skills, lean SKILL.md
  pattern, and pipeline architecture.
- `docs/agents.md` — `@simulation-agent` description updated with launch
  capability and references/ pattern; new "Agent reliability design" section.
- `docs/skills.md` — new "Bundled simulation skills" section with skill
  table, prerequisites, and lean SKILL.md pattern description.

## [1.1.0] — 2026-05-20

### Added
- `IRON RULE` markers in `simulation-agent`, `spectral-agent`,
  `mcmc-agent`, and `retrieval-agent` (3 rules each).
- Anti-patterns table (4 rows: *Anti-Pattern | Why It Fails | Correct
  Behaviour*) in all four analysis agents.
- Anti-leakage `[DATA MISSING: …]` hard-stop rule in all analysis agents.
- `[CITATION MISSING: <query>]` variant in `literature-agent` for ADS
  queries that return no result.
- `handoffs:` frontmatter key in `simulation-agent.agent.md` listing
  downstream agents.
- Bundled simulation launch skills: `dustpy`, `fargo3d`, `pluto`
  with Pydantic-validated runner scripts and `SUCCESS` / `ERROR` protocol.
- `paper-agent.agent.md` — orchestrator agent for multi-agent paper-writing
  workflows.

### Changed
- `README.md` — "Agent reliability design" section added; skill table and
  bash examples for bundled simulation skills.
- `docs/agents.md` — `@simulation-agent` updated with launch capability.

## [1.0.0] — 2026-05-01

### Added
- Initial template release with five specialist agents: `literature-agent`,
  `simulation-agent`, `spectral-agent`, `retrieval-agent`, `mcmc-agent`.
- Group baseline in `.github/copilot-instructions.md`.
- `AGENTS.md` template with domain-specific placeholder sections.
- Pre-commit hooks: `black`, `flake8`, file-size guard, BibTeX DOI check.
- GitHub Actions: `pre-commit.yml` (CI), `pages.yml` (Jekyll deployment).
- GitHub Pages site (`docs/`) with Jekyll / minima.
- Conda environment `envs/base.yml`.
- `.vscode/settings.json` with ADS MCP server configuration.
