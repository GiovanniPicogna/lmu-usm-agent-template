"""Zenodo upload integration for LMU Astrophysics research projects.

Provides a REST API client, configuration loader, archive bundler, and CLI for
uploading simulation outputs, results, and figures to Zenodo Sandbox
(intermediate) or Zenodo production (publication-ready).

Usage:
    python -m src.zenodo --help
"""

from src.zenodo.client import ZenodoAPIError, ZenodoClient, ZenodoUploadError
from src.zenodo.config import TargetConfig, ZenodoConfig, load_config, save_concept_id

__all__ = [
    "ZenodoAPIError",
    "ZenodoUploadError",
    "ZenodoClient",
    "TargetConfig",
    "ZenodoConfig",
    "load_config",
    "save_concept_id",
]
