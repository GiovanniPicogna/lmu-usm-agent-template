# tests/agents/test_agent_structure.py
import re
from pathlib import Path
import pytest

AGENTS_DIR = Path(".github/agents")
REQUIRED_SECTIONS = ["## Role", "## Iron rules", "## Anti-patterns"]
EXPECTED_AGENTS = {
    "pipeline-agent", "hypothesis-agent", "analytical-agent",
    "setup-agent", "simulation-agent", "analysis-agent",
    "interpretation-agent", "paper-agent", "literature-agent",
    "spectral-agent", "retrieval-agent", "mcmc-agent",
}


def get_agent_files() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*.agent.md"))


def test_all_expected_agent_files_exist():
    found = {f.stem.replace(".agent", "") for f in get_agent_files()}
    missing = EXPECTED_AGENTS - found
    assert not missing, f"Missing agent files for: {missing}"


def test_no_unexpected_agent_files():
    found = {f.stem.replace(".agent", "") for f in get_agent_files()}
    extra = found - EXPECTED_AGENTS
    assert not extra, f"Unexpected agent files (update EXPECTED_AGENTS if intentional): {extra}"


@pytest.mark.parametrize("agent_file", get_agent_files(), ids=lambda f: f.stem)
def test_agent_has_yaml_front_matter_with_name(agent_file):
    content = agent_file.read_text()
    assert content.startswith("---"), f"{agent_file.name} must start with YAML front matter"
    assert "name:" in content.split("---")[1], f"{agent_file.name} front matter missing 'name:'"


@pytest.mark.parametrize("agent_file", get_agent_files(), ids=lambda f: f.stem)
def test_agent_has_required_sections(agent_file):
    content = agent_file.read_text()
    for section in REQUIRED_SECTIONS:
        assert section in content, (
            f"{agent_file.name} missing required section: '{section}'"
        )


@pytest.mark.parametrize("agent_file", get_agent_files(), ids=lambda f: f.stem)
def test_agent_has_at_least_one_iron_rule(agent_file):
    content = agent_file.read_text()
    iron_rules = re.findall(r"> \*\*IRON RULE \d+", content)
    assert len(iron_rules) >= 1, (
        f"{agent_file.name} has no IRON RULE markers (expected '> **IRON RULE N')"
    )


@pytest.mark.parametrize("agent_file", get_agent_files(), ids=lambda f: f.stem)
def test_agent_iron_rules_are_sequentially_numbered(agent_file):
    content = agent_file.read_text()
    numbers = [int(m) for m in re.findall(r"> \*\*IRON RULE (\d+)", content)]
    if len(numbers) > 1:
        assert numbers == list(range(1, len(numbers) + 1)), (
            f"{agent_file.name} Iron Rules are not sequentially numbered: {numbers}"
        )


@pytest.mark.parametrize("agent_file", get_agent_files(), ids=lambda f: f.stem)
def test_agent_anti_patterns_section_has_table(agent_file):
    content = agent_file.read_text()
    if "## Anti-patterns" not in content:
        pytest.skip("No anti-patterns section")
    after_section = content.split("## Anti-patterns", 1)[1]
    assert "|" in after_section.split("##")[0], (
        f"{agent_file.name} anti-patterns section has no markdown table"
    )


_DATE_FORMAT_TOKENS = frozenset({"YYYYMMDD"})


@pytest.mark.parametrize("agent_file", get_agent_files(), ids=lambda f: f.stem)
def test_agent_does_not_contain_unfilled_placeholders(agent_file):
    content = agent_file.read_text()
    raw = re.findall(r"<[A-Z_]{3,}>", content)
    # <YYYYMMDD> is an intentional date-format token in output path templates, not a placeholder
    placeholders = [p for p in raw if p.strip("<>") not in _DATE_FORMAT_TOKENS]
    assert not placeholders, (
        f"{agent_file.name} contains unfilled placeholders: {placeholders}"
    )
