# tests/agents/test_hooks_and_config.py
import os
import yaml
from pathlib import Path
import pytest

HOOKS_DIR = Path(".github/hooks/scripts")
INSTRUCTIONS_DIR = Path(".github/instructions")
WORKFLOWS_DIR = Path(".github/workflows")

EXPECTED_HOOKS = {
    "pre-bash-safety.sh",
    "pre-create-results.sh",
    "agent-stop-check.sh",
    "session-start.sh",
}


# ── Hook tests ────────────────────────────────────────────────────────────────


def test_hooks_directory_exists():
    assert HOOKS_DIR.exists(), f"Hooks directory not found: {HOOKS_DIR}"


def test_all_expected_hooks_exist():
    found = {f.name for f in HOOKS_DIR.glob("*.sh")}
    missing = EXPECTED_HOOKS - found
    assert not missing, f"Missing hook scripts: {missing}"


@pytest.mark.parametrize("hook_name", sorted(EXPECTED_HOOKS), ids=lambda n: n.replace(".sh", ""))
def test_hook_is_executable(hook_name):
    hook = HOOKS_DIR / hook_name
    if not hook.exists():
        pytest.skip(f"{hook_name} not found")
    assert os.access(hook, os.X_OK), f"{hook_name} is not executable (run: chmod +x {hook})"


def test_pre_bash_safety_blocks_rm_rf():
    content = (HOOKS_DIR / "pre-bash-safety.sh").read_text()
    assert (
        "rm -rf" in content or "rm_rf" in content.lower()
    ), "pre-bash-safety.sh must check for 'rm -rf' commands"


def test_pre_bash_safety_blocks_force_push():
    content = (HOOKS_DIR / "pre-bash-safety.sh").read_text()
    assert (
        "--force" in content or "force" in content.lower()
    ), "pre-bash-safety.sh must check for git push --force"


def test_pre_bash_safety_blocks_hpc_submission():
    content = (HOOKS_DIR / "pre-bash-safety.sh").read_text()
    hpc_cmds = {"sbatch", "qsub", "bsub"}
    found = [cmd for cmd in hpc_cmds if cmd in content]
    assert found, f"pre-bash-safety.sh must check for HPC submission commands ({hpc_cmds})"


def test_pre_bash_safety_emits_valid_json_schema():
    content = (HOOKS_DIR / "pre-bash-safety.sh").read_text()
    assert (
        "permissionDecision" in content or "hookSpecificOutput" in content
    ), "pre-bash-safety.sh must emit permissionDecision JSON to block commands"


# ── Python instruction tests ──────────────────────────────────────────────────


def test_python_instructions_file_exists():
    f = INSTRUCTIONS_DIR / "python.instructions.md"
    assert f.exists(), f"Python instructions not found at {f}"


def test_python_instructions_covers_key_conventions():
    content = (INSTRUCTIONS_DIR / "python.instructions.md").read_text()
    required_mentions = ["pathlib", "pytest", "ruff", "black", "astropy"]
    for mention in required_mentions:
        assert mention in content, f"python.instructions.md must mention '{mention}'"


# ── Workflow YAML validity tests ───────────────────────────────────────────────


def get_workflow_files() -> list[Path]:
    if not WORKFLOWS_DIR.exists():
        return []
    return sorted(WORKFLOWS_DIR.glob("*.yml"))


def test_workflows_directory_exists():
    assert WORKFLOWS_DIR.exists()


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.stem)
def test_workflow_is_valid_yaml(workflow_file):
    try:
        with open(workflow_file) as fh:
            data = yaml.safe_load(fh)
        assert data is not None, f"{workflow_file.name} parses as empty YAML"
    except yaml.YAMLError as exc:
        pytest.fail(f"{workflow_file.name} is invalid YAML: {exc}")


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.stem)
def test_workflow_has_on_trigger(workflow_file):
    with open(workflow_file) as fh:
        data = yaml.safe_load(fh)
    # PyYAML parses 'on' as True (boolean), so check both 'on' and True as keys
    assert "on" in data or True in data, f"{workflow_file.name} missing 'on:' trigger definition"
