"""Unit tests for upload orchestration.

All ZenodoClient calls are replaced with MagicMock — no HTTP access.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from src.zenodo.config import load_config
from src.zenodo.upload import create_or_new_version, plan_uploads, upload_targets


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_client(mock_deposit):
    client = MagicMock()
    client.create_deposit.return_value = mock_deposit
    client.list_depositions.return_value = [mock_deposit]
    client.new_version.return_value = mock_deposit
    client.update_metadata.return_value = mock_deposit
    client.list_files.return_value = []
    client.upload_file.return_value = {"key": "results.zip"}
    return client


@pytest.fixture
def config(zenodo_yml, citation_cff):
    return load_config(config_path=zenodo_yml, citation_path=citation_cff)


def _make_target_files(config, tmp_path):
    """Point config targets at temp dirs and create one file under results/."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "handoff.json").write_text("{}")
    config.targets["results"].path = results_dir
    config.targets["plots"].path = tmp_path / "plots"  # missing -> 0 files
    return results_dir


# ── plan_uploads ──────────────────────────────────────────────────────────────


def test_plan_uploads_lists_eligible_files(config, tmp_path):
    _make_target_files(config, tmp_path)
    plan = plan_uploads(config, sandbox=True)
    assert len(plan["results"]) == 1
    assert plan["plots"] == []


def test_plan_uploads_respects_sandbox_flag(config, tmp_path):
    _make_target_files(config, tmp_path)
    config.targets["results"].include_sandbox = False
    plan = plan_uploads(config, sandbox=True)
    assert "results" not in plan


def test_plan_uploads_filters_by_target_names(config, tmp_path):
    _make_target_files(config, tmp_path)
    plan = plan_uploads(config, sandbox=True, target_names=["results"])
    assert set(plan) == {"results"}


# ── create_or_new_version ─────────────────────────────────────────────────────


def test_creates_new_deposit_when_no_concept_id(mock_client, config, zenodo_yml):
    deposit = create_or_new_version(mock_client, config, sandbox=True)
    mock_client.create_deposit.assert_called_once()
    assert deposit["id"] == 12345
    updated = yaml.safe_load(zenodo_yml.read_text())
    assert updated["sandbox_concept_id"] == "12344"


def test_creates_new_version_when_concept_id_exists(mock_client, config):
    config.sandbox_concept_id = "12344"
    deposit = create_or_new_version(mock_client, config, sandbox=True)
    mock_client.list_depositions.assert_called_once_with("12344")
    mock_client.new_version.assert_called_once()
    mock_client.create_deposit.assert_not_called()
    assert deposit["id"] == 12345


def test_new_version_clears_inherited_files(mock_client, config):
    config.sandbox_concept_id = "12344"
    mock_client.list_files.return_value = [{"id": "f1"}, {"id": "f2"}]
    create_or_new_version(mock_client, config, sandbox=True)
    assert mock_client.delete_file.call_count == 2


def test_raises_if_no_versions_found_for_concept_id(mock_client, config):
    config.sandbox_concept_id = "00000"
    mock_client.list_depositions.return_value = []
    with pytest.raises(RuntimeError, match="No deposits found"):
        create_or_new_version(mock_client, config, sandbox=True)


# ── upload_targets — bundle mode (default) ────────────────────────────────────


def test_upload_targets_bundles_by_default(mock_client, config, mock_deposit, tmp_path):
    _make_target_files(config, tmp_path)
    staging = tmp_path / "staging"
    staging.mkdir()

    uploaded = upload_targets(
        mock_client, mock_deposit, config, sandbox=True, staging_dir=staging
    )

    # one upload_file call with a .zip; results reports the source files bundled
    assert mock_client.upload_file.call_count == 1
    assert mock_client.upload_file.call_args.args[1].endswith(".zip")
    assert len(uploaded["results"]) == 1
    assert uploaded["plots"] == []


def test_upload_targets_skips_include_sandbox_false(mock_client, config, mock_deposit, tmp_path):
    _make_target_files(config, tmp_path)
    config.targets["results"].include_sandbox = False
    staging = tmp_path / "staging"
    staging.mkdir()

    uploaded = upload_targets(
        mock_client, mock_deposit, config, sandbox=True, staging_dir=staging
    )
    mock_client.upload_file.assert_not_called()
    assert not any(uploaded.values())


def test_upload_targets_filters_by_target_names(mock_client, config, mock_deposit, tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "data.json").write_text("{}")
    plots_dir = tmp_path / "plots"
    plots_dir.mkdir()
    (plots_dir / "fig.pdf").write_bytes(b"%PDF")
    config.targets["results"].path = results_dir
    config.targets["plots"].path = plots_dir
    staging = tmp_path / "staging"
    staging.mkdir()

    uploaded = upload_targets(
        mock_client, mock_deposit, config, sandbox=True,
        target_names=["results"], staging_dir=staging,
    )
    assert "results" in uploaded
    assert "plots" not in uploaded


# ── upload_targets — per-file mode ────────────────────────────────────────────


def test_upload_targets_per_file_encodes_separators(mock_client, config, mock_deposit, tmp_path):
    results_dir = tmp_path / "results"
    (results_dir / "sub").mkdir(parents=True)
    (results_dir / "sub" / "chain.h5").write_bytes(b"data")
    config.targets["results"].path = results_dir
    config.targets["plots"].path = tmp_path / "plots"

    upload_targets(mock_client, mock_deposit, config, sandbox=True, bundle=False)

    zenodo_name = mock_client.upload_file.call_args.args[1]
    assert "/" not in zenodo_name
    assert "__" in zenodo_name
