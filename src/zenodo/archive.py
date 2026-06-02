"""File discovery and per-target archive bundling for Zenodo uploads.

Bundling each target directory into a single deterministic .zip keeps the
Zenodo record small (one file per target), avoids per-file rate limits, and
preserves the directory structure losslessly (no filename mangling).
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from src.zenodo.config import TargetConfig

logger = logging.getLogger(__name__)

_SKIP_NAMES = {".gitkeep", ".DS_Store"}


def collect_files(target: TargetConfig) -> list[Path]:
    """Recursively collect uploadable regular files under target.path.

    Parameters
    ----------
    target : TargetConfig
        Upload target configuration.

    Returns
    -------
    list[Path]
        Sorted regular files (housekeeping files excluded). Empty if the path
        does not exist.
    """
    root = target.path
    if not root.exists():
        logger.warning("Target path %s does not exist — skipping.", root)
        return []
    return sorted(
        f for f in root.rglob("*") if f.is_file() and f.name not in _SKIP_NAMES
    )


def bundle_target(target: TargetConfig, staging_dir: Path) -> Path | None:
    """Bundle all files under a target into a single deterministic .zip.

    Arcnames are relative to the target's *parent* directory, so the archive
    preserves the target's own name as a top-level folder (e.g. 'results/...').

    Parameters
    ----------
    target : TargetConfig
        Upload target configuration.
    staging_dir : Path
        Directory in which to write '<target.name>.zip'.

    Returns
    -------
    Path | None
        Path to the created zip, or None if the target has no files.
    """
    files = collect_files(target)
    if not files:
        return None

    out_path = staging_dir / f"{target.name}.zip"
    base = target.path.parent
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:  # already sorted -> deterministic entry order
            zf.write(file_path, arcname=str(file_path.relative_to(base)))
    logger.info("Bundled %d file(s) into %s", len(files), out_path)
    return out_path
