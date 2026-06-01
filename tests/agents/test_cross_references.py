# tests/agents/test_cross_references.py
import re
from pathlib import Path
import pytest

ARCHITECTURE_MD = Path("ARCHITECTURE.md")
AGENTS_DIR = Path(".github/agents")
SKILLS_DIR = Path(".github/skills")
HANDOFFS_MD = Path(".github/shared/handoff_schemas.md")
CLAUDE_MD = Path("CLAUDE.md")

PIPELINE_AGENTS = {
    "hypothesis-agent",
    "analytical-agent",
    "setup-agent",
    "simulation-agent",
    "analysis-agent",
    "interpretation-agent",
    "paper-agent",
    "literature-agent",
    "spectral-agent",
    "retrieval-agent",
    "mcmc-agent",
}

KNOWN_SCHEMAS = {
    "HypothesisHandoff/v1",
    "AnalyticalHandoff/v1",
    "SimConfigHandoff/v1",
    "SimulationHandoff/v1",
    "AnalysisHandoff/v1",
    "InterpretationHandoff/v1",
    "SpectralFitHandoff/v1",
    "MCMCHandoff/v1",
    "PaperHandoff/v1",
}


# ── ARCHITECTURE.md ↔ agent files ────────────────────────────────────────────


def test_architecture_md_exists():
    assert ARCHITECTURE_MD.exists()


def test_all_pipeline_agents_have_agent_files():
    agent_files = {f.stem.replace(".agent", "") for f in AGENTS_DIR.glob("*.agent.md")}
    missing = PIPELINE_AGENTS - agent_files
    assert not missing, f"Agents listed in ARCHITECTURE.md have no .agent.md files: {missing}"


def test_architecture_references_all_expected_schemas():
    arch = ARCHITECTURE_MD.read_text()
    for schema in KNOWN_SCHEMAS:
        assert schema in arch, f"Schema {schema!r} not referenced in ARCHITECTURE.md"


# ── handoff_schemas.md completeness ──────────────────────────────────────────


def test_handoff_schemas_md_exists():
    assert HANDOFFS_MD.exists(), f"Handoff schemas file not found: {HANDOFFS_MD}"


def test_all_known_schemas_defined_in_handoff_schemas_md():
    content = HANDOFFS_MD.read_text()
    for schema in KNOWN_SCHEMAS:
        assert (
            schema in content
        ), f"Schema {schema!r} in KNOWN_SCHEMAS but not defined in handoff_schemas.md"


def test_handoff_schemas_md_has_validation_rules_for_each_schema():
    content = HANDOFFS_MD.read_text()
    for schema in KNOWN_SCHEMAS:
        section_header = f"## {schema}"
        if section_header not in content:
            pytest.fail(f"No section header '{section_header}' found in handoff_schemas.md")
        after_header = content.split(section_header, 1)[1]
        next_section = re.search(r"\n## ", after_header)
        section_text = after_header[: next_section.start()] if next_section else after_header
        assert (
            "Validation rules" in section_text or "**Validation rules" in section_text
        ), f"Schema {schema!r} is missing a 'Validation rules' block in handoff_schemas.md"


# ── ARCHITECTURE.md ↔ skill directories ──────────────────────────────────────


def test_skills_mentioned_in_architecture_have_directories():
    arch = ARCHITECTURE_MD.read_text()
    skill_names = re.findall(r"`(dustpy|fargo3d|pluto|radmc3d|sherpa|yt)`", arch)
    for skill in set(skill_names):
        assert (
            SKILLS_DIR / skill
        ).exists(), f"Skill `{skill}` ref. in ARCHITECTURE.md but no dir. at {SKILLS_DIR / skill}"


# ── Agent files ↔ handoff schemas ────────────────────────────────────────────


@pytest.mark.parametrize(
    "agent_file",
    sorted(AGENTS_DIR.glob("*.agent.md")),
    ids=lambda f: f.stem,
)
def test_agent_schema_references_are_valid(agent_file):
    content = agent_file.read_text()
    refs = re.findall(r"(\w+Handoff/v\d+)", content)
    invalid = [r for r in refs if r not in KNOWN_SCHEMAS]
    assert not invalid, (
        f"{agent_file.name} references unknown handoff schemas: {invalid}. "
        f"Valid schemas: {KNOWN_SCHEMAS}"
    )


# ── CLAUDE.md references ──────────────────────────────────────────────────────


def test_claude_md_references_python_instructions():
    content = CLAUDE_MD.read_text()
    assert (
        "python.instructions.md" in content
    ), "CLAUDE.md must reference .github/instructions/python.instructions.md"


def test_claude_md_references_handoff_schemas():
    content = CLAUDE_MD.read_text()
    assert (
        "handoff_schemas.md" in content or "shared" in content
    ), "CLAUDE.md must reference .github/shared/handoff_schemas.md"


def test_claude_agents_symlinks_cover_all_specialist_agents():
    claude_agents_dir = Path(".claude/agents")
    assert claude_agents_dir.exists(), ".claude/agents/ directory missing"
    symlinked = {f.stem.replace(".agent", "") for f in claude_agents_dir.glob("*.agent.md")}
    missing = PIPELINE_AGENTS - symlinked
    assert not missing, f"Specialist agents not symlinked into .claude/agents/: {missing}"
