"""Unit tests for the Zenodo CLI.

Uses Click's CliRunner to invoke commands without a real terminal.
All client and orchestration calls are patched — no HTTP access.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.zenodo.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def env_sandbox() -> dict[str, str]:
    return {"ZENODO_SANDBOX_TOKEN": "fake-sandbox-token"}


def _nonempty_plan():
    return {"results": [Path("results/handoff.json")], "plots": []}


# ── token validation ──────────────────────────────────────────────────────────


def test_create_fails_without_sandbox_token(runner, zenodo_yml, citation_cff):
    # patch.dict(clear=True) fully resets os.environ so the token is never found.
    # CliRunner's env={} alone is insufficient: Click skips the empty-dict update
    # (if env: guard), leaving os.environ unchanged and any real token visible.
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(
            cli,
            ["create", "--sandbox", f"--config={zenodo_yml}", f"--citation-cff={citation_cff}"],
        )
    assert result.exit_code != 0
    assert "ZENODO_SANDBOX_TOKEN" in result.output


def test_create_fails_without_production_token(runner, zenodo_yml, citation_cff):
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(
            cli,
            [
                "create",
                "--no-sandbox",
                "--yes",
                f"--config={zenodo_yml}",
                f"--citation-cff={citation_cff}",
            ],
        )
    assert result.exit_code != 0
    assert "ZENODO_TOKEN" in result.output


# ── zero-files guard ──────────────────────────────────────────────────────────


def test_create_errors_when_no_files_to_upload(runner, zenodo_yml, citation_cff, env_sandbox):
    # Targets point at non-existent results/ and plots/ -> empty plan.
    with patch("src.zenodo.cli.plan_uploads", return_value={"results": [], "plots": []}):
        result = runner.invoke(
            cli,
            ["create", "--sandbox", f"--config={zenodo_yml}", f"--citation-cff={citation_cff}"],
            env=env_sandbox,
        )
    assert result.exit_code != 0
    assert "No files" in result.output


# ── dry-run ───────────────────────────────────────────────────────────────────


def test_create_dry_run_does_not_create_deposit(runner, zenodo_yml, citation_cff, env_sandbox):
    with (
        patch("src.zenodo.cli.plan_uploads", return_value=_nonempty_plan()),
        patch("src.zenodo.cli.create_or_new_version") as mock_create,
        patch("src.zenodo.cli.upload_targets") as mock_upload,
    ):
        result = runner.invoke(
            cli,
            [
                "create",
                "--sandbox",
                "--dry-run",
                f"--config={zenodo_yml}",
                f"--citation-cff={citation_cff}",
            ],
            env=env_sandbox,
        )
    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output
    assert "results/handoff.json" in result.output
    mock_create.assert_not_called()
    mock_upload.assert_not_called()


# ── create (happy path) ───────────────────────────────────────────────────────


def test_create_creates_deposit_and_uploads(
    runner, zenodo_yml, citation_cff, mock_deposit, env_sandbox
):
    with (
        patch("src.zenodo.cli.plan_uploads", return_value=_nonempty_plan()),
        patch("src.zenodo.cli.ZenodoClient") as mock_client_cls,
        patch("src.zenodo.cli.create_or_new_version", return_value=mock_deposit) as mock_create,
        patch(
            "src.zenodo.cli.upload_targets",
            return_value={"results": ["results/handoff.json"], "plots": []},
        ) as mock_upload,
    ):
        mock_client_cls.return_value = MagicMock()
        result = runner.invoke(
            cli,
            ["create", "--sandbox", f"--config={zenodo_yml}", f"--citation-cff={citation_cff}"],
            env=env_sandbox,
        )
    assert result.exit_code == 0, result.output
    assert "12345" in result.output
    assert "Done" in result.output
    mock_create.assert_called_once()
    mock_upload.assert_called_once()
    assert mock_client_cls.call_args.kwargs["sandbox"] is True


def test_create_production_requires_confirmation(runner, zenodo_yml, citation_cff, mock_deposit):
    """Without --yes, a production create must abort on the safety prompt."""
    env = {"ZENODO_TOKEN": "fake-prod-token"}
    with (
        patch("src.zenodo.cli.plan_uploads", return_value=_nonempty_plan()),
        patch("src.zenodo.cli.create_or_new_version", return_value=mock_deposit) as mock_create,
        patch("src.zenodo.cli.upload_targets", return_value={}),
        patch("src.zenodo.cli.ZenodoClient", return_value=MagicMock()),
    ):
        result = runner.invoke(
            cli,
            ["create", "--no-sandbox", f"--config={zenodo_yml}", f"--citation-cff={citation_cff}"],
            env=env,
            input="n\n",  # decline the confirmation
        )
    assert result.exit_code != 0
    assert "PI approval" in result.output
    mock_create.assert_not_called()


# ── publish (irreversible -> confirmation) ────────────────────────────────────


def test_publish_aborts_without_confirmation(runner, env_sandbox):
    with patch("src.zenodo.cli.ZenodoClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        result = runner.invoke(
            cli, ["publish", "--sandbox", "--deposit-id=12345"], env=env_sandbox, input="n\n"
        )
    assert result.exit_code != 0
    mock_client.publish.assert_not_called()


def test_publish_with_yes_outputs_doi(runner, mock_published_deposit, env_sandbox):
    with patch("src.zenodo.cli.ZenodoClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.publish.return_value = mock_published_deposit
        result = runner.invoke(
            cli, ["publish", "--sandbox", "--deposit-id=12345", "--yes"], env=env_sandbox
        )
    assert result.exit_code == 0, result.output
    assert "10.5281/zenodo.12345" in result.output
    mock_client.publish.assert_called_once_with(12345)


def test_publish_requires_deposit_id(runner, env_sandbox):
    result = runner.invoke(cli, ["publish", "--sandbox", "--yes"], env=env_sandbox)
    assert result.exit_code != 0
    assert "deposit-id" in result.output.lower() or "missing" in result.output.lower()


# ── status ────────────────────────────────────────────────────────────────────


def test_status_shows_state_and_concept_id(runner, mock_deposit, env_sandbox):
    with patch("src.zenodo.cli.ZenodoClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_deposit.return_value = mock_deposit
        result = runner.invoke(cli, ["status", "--sandbox", "--deposit-id=12345"], env=env_sandbox)
    assert result.exit_code == 0, result.output
    assert "unsubmitted" in result.output
    assert "12344" in result.output
    assert "Test Astrophysics Project" in result.output
