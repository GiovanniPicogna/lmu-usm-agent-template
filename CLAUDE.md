# CLAUDE.md — LMU Munich Astrophysics / Universitäts-Sternwarte München

See @AGENTS.md for **project-specific context**: science goal, data paths,
simulation parameters, key commands, and per-project agent rules.

See @.github/copilot-instructions.md for **group-level conventions**:
coding standards, physical units & astropy.units usage, citation policy
(CRITICAL — never invent references; always use ADS MCP), figure style,
reproducibility requirements, data-handling rules, and the full list of
actions this agent must never do.

For bundled domain skills (dustpy, fargo3d, pluto, radmc3d, sherpa, yt),
see `.claude/skills/<name>/SKILL.md`.

See @.github/instructions/python.instructions.md for **Python coding standards**
(pathlib, ruff, black, pytest, error handling). Auto-applied by Copilot; must be
explicitly loaded here for Claude Code.

See @.github/shared/handoff_schemas.md for **inter-agent handoff schemas**: all
JSON contracts (HypothesisHandoff, AnalyticalHandoff, SimConfigHandoff,
SimulationHandoff, AnalysisHandoff, InterpretationHandoff, SpectralFitHandoff,
MCMCHandoff, PaperHandoff). Every agent emitting or consuming a handoff must
conform to these schemas.

All specialist agents live in `.claude/agents/<name>.agent.md` (symlinked from
`.github/agents/`). Agent references (analytical toolkit, code conventions,
output conventions) are in `.claude/agents/references/`.

Hooks (pre-bash safety, results-dir guard, session-start, agent-stop) are
configured in `.claude/settings.json` and execute automatically.
