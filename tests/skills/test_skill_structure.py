# tests/skills/test_skill_structure.py
import re
from pathlib import Path
import pytest

SKILLS_DIR = Path(".github/skills")
EXPECTED_SKILLS = {"dustpy", "fargo3d", "pluto", "radmc3d", "sherpa", "yt"}
REQUIRED_SKILL_SECTIONS = ["## Iron rules", "## Mandatory workflow"]


def get_skill_dirs() -> list[Path]:
    return sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith("."))


def test_all_expected_skill_directories_exist():
    found = {d.name for d in get_skill_dirs()}
    missing = EXPECTED_SKILLS - found
    assert not missing, f"Missing skill directories: {missing}"


@pytest.mark.parametrize("skill_dir", get_skill_dirs(), ids=lambda d: d.name)
def test_skill_has_skill_md(skill_dir):
    assert (skill_dir / "SKILL.md").exists(), f"{skill_dir.name}/ missing SKILL.md"


@pytest.mark.parametrize("skill_dir", get_skill_dirs(), ids=lambda d: d.name)
def test_skill_md_has_yaml_front_matter_with_name(skill_dir):
    content = (skill_dir / "SKILL.md").read_text()
    assert content.startswith("---"), f"{skill_dir.name}/SKILL.md must start with YAML front matter"
    front_matter = content.split("---")[1]
    assert "name:" in front_matter, f"{skill_dir.name}/SKILL.md front matter missing 'name:'"
    assert (
        "description:" in front_matter
    ), f"{skill_dir.name}/SKILL.md front matter missing 'description:'"


@pytest.mark.parametrize("skill_dir", get_skill_dirs(), ids=lambda d: d.name)
def test_skill_md_has_required_sections(skill_dir):
    content = (skill_dir / "SKILL.md").read_text()
    for section in REQUIRED_SKILL_SECTIONS:
        assert (
            section in content
        ), f"{skill_dir.name}/SKILL.md missing required section: '{section}'"


@pytest.mark.parametrize("skill_dir", get_skill_dirs(), ids=lambda d: d.name)
def test_skill_scripts_are_non_empty(skill_dir):
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        pytest.skip(f"{skill_dir.name} has no scripts/ directory")
    scripts = list(scripts_dir.glob("*.py"))
    assert scripts, f"{skill_dir.name}/scripts/ exists but contains no .py files"
    for script in scripts:
        assert (
            script.stat().st_size > 500
        ), f"{script} looks suspiciously small ({script.stat().st_size} bytes) — may be empty"


@pytest.mark.parametrize("skill_dir", get_skill_dirs(), ids=lambda d: d.name)
def test_skill_script_paths_referenced_in_skill_md_exist(skill_dir):
    content = (skill_dir / "SKILL.md").read_text()
    script_refs = re.findall(r"\.github/skills/[^\s`'\"]+\.py", content)
    for ref in script_refs:
        path = Path(ref)
        assert path.exists(), f"{skill_dir.name}/SKILL.md references {ref} but file does not exist"


@pytest.mark.parametrize("skill_dir", get_skill_dirs(), ids=lambda d: d.name)
def test_skill_references_directory_if_present(skill_dir):
    refs_dir = skill_dir / "references"
    if not refs_dir.exists():
        pytest.skip(f"{skill_dir.name} has no references/ directory")
    ref_files = list(refs_dir.glob("*.md"))
    assert ref_files, f"{skill_dir.name}/references/ exists but contains no .md files"


@pytest.mark.parametrize("skill_name", ["pluto", "fargo3d"])
def test_disk_skill_documents_source_as_context(skill_name):
    """pluto and fargo3d skills must document the source-as-context pattern:
    grep the actual code checkout to ground parameter names rather than relying
    on the model's training memory.
    """
    content = (SKILLS_DIR / skill_name / "SKILL.md").read_text()
    assert (
        "source as context" in content.lower()
    ), f"{skill_name}/SKILL.md missing the 'Source as context' section"
    assert (
        "grep" in content
    ), f"{skill_name}/SKILL.md source-as-context must show a grep of the code checkout"
