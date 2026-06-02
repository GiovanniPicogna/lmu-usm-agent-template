"""Configuration loader for Zenodo upload.

Reads zenodo.yml (upload config) and CITATION.cff (FAIR metadata source),
merges them, validates the access right, and persists concept IDs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_ZENODO_YML = Path("zenodo.yml")
_DEFAULT_CITATION_CFF = Path("CITATION.cff")


@dataclass
class TargetConfig:
    """Configuration for a single upload target directory."""

    name: str
    path: Path
    description: str
    include_sandbox: bool = True
    include_production: bool = True


@dataclass
class ZenodoConfig:
    """Parsed Zenodo upload configuration."""

    metadata: dict
    targets: dict[str, TargetConfig]
    sandbox_concept_id: str | None
    zenodo_concept_id: str | None
    config_path: Path


# ── CITATION.cff helpers ──────────────────────────────────────────────────────


def _parse_creators_from_cff(cff: dict) -> list[dict]:
    """Convert CITATION.cff authors to Zenodo creator dicts.

    Parameters
    ----------
    cff : dict
        Parsed CITATION.cff content.

    Returns
    -------
    list[dict]
        Creator dicts with 'name' and optionally 'affiliation' and 'orcid'
        (bare 16-char identifier, not the full URL).
    """
    creators = []
    for author in cff.get("authors", []):
        given = author.get("given-names", "")
        family = author.get("family-names", "")
        creator: dict = {"name": f"{family}, {given}".strip(", ")}
        if "affiliation" in author:
            creator["affiliation"] = author["affiliation"]
        if "orcid" in author:
            creator["orcid"] = author["orcid"].rstrip("/").split("/")[-1]
        creators.append(creator)
    return creators


# ── metadata merging + validation ─────────────────────────────────────────────


def _build_metadata(cfg: dict, cff: dict) -> dict:
    """Merge zenodo.yml metadata with CITATION.cff and validate access right.

    CITATION.cff wins for title, description, version, and creators; zenodo.yml
    wins for upload_type, access_right, license, and any embargo fields.
    Keywords from both sources are merged (CFF first), deduplicated.

    Raises
    ------
    ValueError
        If access_right is 'embargoed' without 'embargo_date', or 'restricted'
        without 'access_conditions'.
    """
    base = dict(cfg.get("metadata", {}))

    base["title"] = cff.get("title", base.get("title", "[DATA MISSING: add title to CITATION.cff]"))
    base["description"] = cff.get(
        "abstract", base.get("description", "[DATA MISSING: add abstract to CITATION.cff]")
    )
    if "version" in cff:
        base["version"] = str(cff["version"])

    creators = _parse_creators_from_cff(cff)
    base["creators"] = creators or [{"name": "[DATA MISSING: add authors to CITATION.cff]"}]

    merged_keywords = list(dict.fromkeys(cff.get("keywords", []) + base.get("keywords", [])))
    if merged_keywords:
        base["keywords"] = merged_keywords

    access_right = base.get("access_right", "open")
    if access_right == "embargoed" and not base.get("embargo_date"):
        raise ValueError(
            "metadata.access_right is 'embargoed' but metadata.embargo_date is missing. "
            'Add an ISO-8601 date (e.g. embargo_date: "2027-01-01").'
        )
    if access_right == "restricted" and not base.get("access_conditions"):
        raise ValueError(
            "metadata.access_right is 'restricted' but metadata.access_conditions is missing."
        )

    return base


# ── target parsing ────────────────────────────────────────────────────────────


def _parse_targets(cfg: dict) -> dict[str, TargetConfig]:
    """Parse the 'targets' section of zenodo.yml into TargetConfig objects."""
    targets: dict[str, TargetConfig] = {}
    for name, spec in cfg.get("targets", {}).items():
        targets[name] = TargetConfig(
            name=name,
            path=Path(spec["path"]),
            description=spec.get("description", ""),
            include_sandbox=spec.get("include_sandbox", True),
            include_production=spec.get("include_production", True),
        )
    return targets


# ── public API ────────────────────────────────────────────────────────────────


def load_config(
    config_path: Path = _DEFAULT_ZENODO_YML,
    citation_path: Path = _DEFAULT_CITATION_CFF,
) -> ZenodoConfig:
    """Load and validate the Zenodo upload configuration.

    Raises
    ------
    FileNotFoundError
        If zenodo.yml does not exist at config_path.
    ValueError
        If zenodo.yml has no 'targets', or an access-right field is incomplete.
    """
    if not config_path.exists():
        raise FileNotFoundError(
            f"zenodo.yml not found at {config_path}. It ships with the repo root; "
            "copy it into place and edit the targets."
        )

    cfg: dict = yaml.safe_load(config_path.read_text()) or {}

    cff: dict = {}
    if citation_path.exists():
        cff = yaml.safe_load(citation_path.read_text()) or {}
    else:
        logger.warning(
            "CITATION.cff not found at %s — metadata will be incomplete. "
            "Create one: https://citation-file-format.github.io/",
            citation_path,
        )

    if not cfg.get("targets"):
        raise ValueError(
            f"{config_path} must contain a non-empty 'targets' section. See zenodo.yml."
        )

    return ZenodoConfig(
        metadata=_build_metadata(cfg, cff),
        targets=_parse_targets(cfg),
        sandbox_concept_id=cfg.get("sandbox_concept_id") or None,
        zenodo_concept_id=cfg.get("zenodo_concept_id") or None,
        config_path=config_path,
    )


def save_concept_id(config_path: Path, sandbox: bool, concept_id: str) -> None:
    """Persist a concept ID back into zenodo.yml after deposit creation."""
    cfg: dict = yaml.safe_load(config_path.read_text()) or {}
    key = "sandbox_concept_id" if sandbox else "zenodo_concept_id"
    cfg[key] = concept_id
    with config_path.open("w") as fh:
        yaml.dump(cfg, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)
    logger.info("Saved %s=%s to %s", key, concept_id, config_path)
