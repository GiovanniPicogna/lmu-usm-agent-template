# Claude Code Pipeline Orchestrator

This file is the Claude Code equivalent of `.github/agents/pipeline-agent.agent.md`.
It implements the same 9-stage research pipeline using Claude Code's `Agent` tool
instead of Copilot's `@<name>` delegation syntax.

---

## How delegation works in Claude Code

Claude Code does not auto-load `.agent.md` files. Each sub-agent must be spawned
explicitly via the `Agent` tool with a self-contained prompt. The pattern is:

```
1. Read the specialist agent file:
      Read(".github/agents/<name>.agent.md")
   to extract its Role, Iron Rules, and Mandatory workflow.

2. Spawn it via the Agent tool, passing the model from the delegation table above:
      Agent(
        description="<stage> — <name>",
        model="<haiku|sonnet|opus>",   # see delegation table
        prompt="""
          <paste the agent's Role and Iron Rules verbatim>

          ## Your task
          <stage-specific instruction + handoff paths>

          ## Context files to read first
          - .github/shared/handoff_schemas.md
          - <any relevant handoff JSON from prior stage>
        """
      )

3. Parse the returned JSON handoff from the agent's stdout/output.
4. Verify required fields before proceeding to the next stage.
```

The prompt must be **self-contained** — the spawned agent has no memory of this
conversation and has not read any files yet.

---

## Delegation table

| Stage | Agent file | Model | Skill file (if any) | Handoff produced |
|---|---|---|---|---|
| 1 | `.github/agents/literature-agent.agent.md` | `haiku` | — | bibliography context |
| 2 | `.github/agents/hypothesis-agent.agent.md` | `opus` | — | `HypothesisHandoff/v1` |
| 3 | `.github/agents/analytical-agent.agent.md` | `opus` | — | `AnalyticalHandoff/v1` |
| 4 | `.github/agents/setup-agent.agent.md` | `sonnet` | — | `SimConfigHandoff/v1` |
| 5 | `.github/agents/simulation-agent.agent.md` | `sonnet` | `.github/skills/<code>/SKILL.md` | `SimulationHandoff/v1` |
| 6 | `.github/agents/analysis-agent.agent.md` | `sonnet` | — | `AnalysisHandoff/v1` |
| 7 | `.github/agents/interpretation-agent.agent.md` | `opus` | — | `InterpretationHandoff/v1` |
| 8b | `.github/agents/mcmc-agent.agent.md` | `sonnet` | — | `MCMCHandoff/v1` |
| 9 | `.github/agents/paper-agent.agent.md` | `sonnet` | — | `PaperHandoff/v1` |

---

## Prompt template for each delegation

Use this template verbatim, substituting the bracketed fields:

```
You are the [<agent Role, first sentence>] for the LMU Astrophysics group.

## Iron Rules
[paste Iron Rules from the agent file]

## Your task for this session
[stage-specific instruction]

## Inputs
- Handoff from prior stage: [absolute path to JSON]
- Handoff schema reference: .github/shared/handoff_schemas.md

## Required output
Emit a [<HandoffType>/v1] JSON to stdout, conforming exactly to the schema
in .github/shared/handoff_schemas.md.
Write the JSON to: [absolute path, e.g. results/handoffs/<task_id>_<stage>.json]

## Context
- Project root: [absolute path]
- Task ID: [snake_case label]
- Domain: [disk | cosmological | retrieval | xray | lss]
- Python interpreter: ~/anaconda3/envs/py312/bin/python
```

---

## Human gates

Both gates are **blocking** — do not spawn the next stage's agent until the user
replies in the main conversation.

**Gate 1** (between Stage 2 and 3): Present `HypothesisHandoff.hypotheses` ranked
by `priority_rank`. Ask: *"Proceed with hypothesis #N, modify, or choose another?"*

**Gate 2** (between Stage 7 and 8/9): Present `InterpretationHandoff.findings`
and `hypothesis_match`. Ask: *"Findings: [summary]. Recommendation: [next_action].
Confirm to proceed?"*

---

## Tracking

Use `TaskCreate` / `TaskUpdate` to track each stage as a task. Mark `in_progress`
when the agent is spawned, `completed` when its handoff JSON is verified.

---

## Pipeline logic

The full stage sequence, routing rules, handoff validation requirements, and
anti-patterns are defined in `.github/agents/pipeline-agent.agent.md`.
Read that file at the start of every pipeline run — do not duplicate its
content here.
