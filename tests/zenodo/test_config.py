"""Unit tests for the Zenodo config loader.

Covers CITATION.cff parsing, zenodo.yml loading, metadata merging, access-right
validation, error cases, and concept-ID persistence.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from src.zenodo.config import (
    _parse_creators_from_cff,
    load_config,
    save_concept_id,
)


# ── _parse_creators_from_cff ──────────────────────────────────────────────────


def test_parse_creators_full_author(citation_cff):
    cff = yaml.safe_load(citation_cff.read_text())
    creators = _parse_creators_from_cff(cff)
    assert len(creators) == 1
    assert creators[0]["name"] == "Picogna, Giovanni"
    assert creators[0]["affiliation"] == "LMU Munich"
    assert creators[0]["orcid"] == "0000-0003-3754-1639"  # URL stripped


def test_parse_creators_strips_orcid_url():
    cff = {
        "authors": [
            {
                "family-names": "Smith",
                "given-names": "J",
                "orcid": "https://orcid.org/0000-0001-2345-6789",
            }
        ]
    }
    assert _parse_creators_from_cff(cff)[0]["orcid"] == "0000-0001-2345-6789"


def test_parse_creators_no_orcid_no_affiliation():
    cff = {"authors": [{"family-names": "Doe", "given-names": "Jane"}]}
    creator = _parse_creators_from_cff(cff)[0]
    assert creator["name"] == "Doe, Jane"
    assert "orcid" not in creator
    assert "affiliation" not in creator


def test_parse_creators_empty_authors_returns_empty_list():
    assert _parse_creators_from_cff({}) == []


# ── load_config — metadata from CFF ───────────────────────────────────────────


def test_load_config_reads_title_from_cff(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    assert config.metadata["title"] == "Test Astrophysics Project"


def test_load_config_reads_description_from_cff(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    assert config.metadata["description"] == "A test project for Zenodo integration."


def test_load_config_reads_version_from_cff(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    assert config.metadata["version"] == "0.1.0"


def test_load_config_preserves_upload_type_and_license(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    assert config.metadata["upload_type"] == "dataset"
    assert config.metadata["license"] == "cc-by-4.0"


def test_load_config_merges_keywords_from_cff_and_yml(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    keywords = config.metadata.get("keywords", [])
    assert "astrophysics" in keywords
    assert "test" in keywords


# ── load_config — targets ─────────────────────────────────────────────────────


def test_load_config_parses_target_paths(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    assert config.targets["results"].path == Path("results/")
    assert config.targets["plots"].path == Path("plots/")


def test_load_config_parses_target_flags(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    assert config.targets["results"].include_sandbox is True
    assert config.targets["results"].include_production is True


def test_load_config_null_concept_ids_when_not_set(zenodo_yml, citation_cff):
    config = load_config(config_path=zenodo_yml, citation_path=citation_cff)
    assert config.sandbox_concept_id is None
    assert config.zenodo_concept_id is None


# ── load_config — access-right validation ─────────────────────────────────────


def test_load_config_embargoed_without_date_raises(tmp_path, citation_cff):
    yml = tmp_path / "zenodo.yml"
    yml.write_text(
        "metadata:\n  upload_type: dataset\n  access_right: embargoed\n"
        "targets:\n  results:\n    path: results/\n    description: r\n"
    )
    with pytest.raises(ValueError, match="embargo_date"):
        load_config(config_path=yml, citation_path=citation_cff)


def test_load_config_embargoed_with_date_ok(tmp_path, citation_cff):
    yml = tmp_path / "zenodo.yml"
    yml.write_text(
        "metadata:\n  upload_type: dataset\n  access_right: embargoed\n"
        '  embargo_date: "2027-01-01"\n'
        "targets:\n  results:\n    path: results/\n    description: r\n"
    )
    config = load_config(config_path=yml, citation_path=citation_cff)
    assert config.metadata["embargo_date"] == "2027-01-01"


# ── load_config — error cases ─────────────────────────────────────────────────


def test_load_config_raises_file_not_found_when_zenodo_yml_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="zenodo.yml not found"):
        load_config(config_path=tmp_path / "zenodo.yml")


def test_load_config_raises_value_error_when_no_targets(tmp_path, citation_cff):
    bad = tmp_path / "zenodo.yml"
    bad.write_text("metadata:\n  upload_type: dataset\n")
    with pytest.raises(ValueError, match="targets"):
        load_config(config_path=bad, citation_path=citation_cff)


def test_load_config_missing_citation_cff_logs_warning(zenodo_yml, tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="src.zenodo.config"):
        load_config(config_path=zenodo_yml, citation_path=tmp_path / "no_CITATION.cff")
    assert any("CITATION.cff not found" in r.message for r in caplog.records)


# ── save_concept_id ───────────────────────────────────────────────────────────


def test_save_concept_id_writes_sandbox_id(zenodo_yml):
    save_concept_id(zenodo_yml, sandbox=True, concept_id="99999")
    updated = yaml.safe_load(zenodo_yml.read_text())
    assert updated["sandbox_concept_id"] == "99999"
    assert updated["zenodo_concept_id"] is None


def test_save_concept_id_writes_production_id(zenodo_yml):
    save_concept_id(zenodo_yml, sandbox=False, concept_id="88888")
    updated = yaml.safe_load(zenodo_yml.read_text())
    assert updated["zenodo_concept_id"] == "88888"
    assert updated["sandbox_concept_id"] is None


def test_save_concept_id_preserves_targets(zenodo_yml):
    save_concept_id(zenodo_yml, sandbox=True, concept_id="77777")
    updated = yaml.safe_load(zenodo_yml.read_text())
    assert "targets" in updated
