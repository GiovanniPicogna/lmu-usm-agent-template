"""Shared pytest fixtures for the Zenodo upload module tests."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def zenodo_yml_content() -> dict:
    """Minimal valid zenodo.yml content (no concept IDs)."""
    return {
        "sandbox_concept_id": None,
        "zenodo_concept_id": None,
        "metadata": {
            "upload_type": "dataset",
            "access_right": "open",
            "license": "cc-by-4.0",
        },
        "targets": {
            "results": {
                "path": "results/",
                "description": "Pipeline results",
                "include_sandbox": True,
                "include_production": True,
            },
            "plots": {
                "path": "plots/",
                "description": "Figures",
                "include_sandbox": True,
                "include_production": True,
            },
        },
    }


@pytest.fixture
def zenodo_yml(tmp_path: Path, zenodo_yml_content: dict) -> Path:
    """Write a valid zenodo.yml to a temp directory and return its path."""
    path = tmp_path / "zenodo.yml"
    with path.open("w") as fh:
        yaml.dump(zenodo_yml_content, fh, default_flow_style=False, sort_keys=False)
    return path


@pytest.fixture
def citation_cff(tmp_path: Path) -> Path:
    """Write a minimal CITATION.cff to a temp directory and return its path."""
    content = textwrap.dedent("""\
        cff-version: 1.2.0
        title: "Test Astrophysics Project"
        abstract: "A test project for Zenodo integration."
        version: "0.1.0"
        license: MIT
        keywords:
          - astrophysics
          - test
        authors:
          - family-names: Picogna
            given-names: Giovanni
            affiliation: "LMU Munich"
            orcid: "https://orcid.org/0000-0003-3754-1639"
    """)
    path = tmp_path / "CITATION.cff"
    path.write_text(content)
    return path


@pytest.fixture
def mock_deposit() -> dict:
    """Minimal Zenodo deposit API response for a draft deposit."""
    return {
        "id": 12345,
        "conceptrecid": "12344",
        "state": "unsubmitted",
        "title": "Test Astrophysics Project",
        "doi": "",
        "doi_url": "",
        "files": [],
        "links": {
            "bucket": "https://sandbox.zenodo.org/api/files/abc-bucket-id",
            "html": "https://sandbox.zenodo.org/deposit/12345",
            "publish": "https://sandbox.zenodo.org/api/deposit/depositions/12345/actions/publish",
            "latest_draft": "https://sandbox.zenodo.org/api/deposit/depositions/12345",
        },
        "metadata": {
            "title": "Test Astrophysics Project",
            "upload_type": "dataset",
        },
    }


@pytest.fixture
def mock_published_deposit(mock_deposit: dict) -> dict:
    """Minimal Zenodo deposit API response for a published deposit."""
    published = dict(mock_deposit)
    published["state"] = "done"
    published["doi"] = "10.5281/zenodo.12345"
    published["doi_url"] = "https://doi.org/10.5281/zenodo.12345"
    return published
