"""Upload orchestration for Zenodo deposits.

Plans uploads (which files would go where), creates or versions deposits
(clearing files inherited by a new version), and executes uploads either as one
zip per target (default) or file-by-file.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from src.zenodo.archive import bundle_target, collect_files
from src.zenodo.client import ZenodoClient
from src.zenodo.config import ZenodoConfig, save_concept_id

logger = logging.getLogger(__name__)


def _eligible(config: ZenodoConfig, sandbox: bool, target_names: list[str] | None):
    """Yield (name, TargetConfig) pairs eligible for this upload context."""
    for name, target in config.targets.items():
        if target_names is not None and name not in target_names:
            continue
        if sandbox and not target.include_sandbox:
            continue
        if not sandbox and not target.include_production:
            continue
        yield name, target


def plan_uploads(
    config: ZenodoConfig,
    sandbox: bool,
    target_names: list[str] | None = None,
) -> dict[str, list[Path]]:
    """Return the files that would be uploaded, keyed by target name.

    Pure (no network, no deposit). Used by --dry-run and the zero-files guard.
    """
    return {
        name: collect_files(target) for name, target in _eligible(config, sandbox, target_names)
    }


def create_or_new_version(client: ZenodoClient, config: ZenodoConfig, sandbox: bool) -> dict:
    """Create a new deposit, or open a fresh new version of an existing concept.

    First call (no concept ID): creates a deposit and persists the concept ID to
    zenodo.yml. Later calls: open a new draft from the latest published version,
    clear the files it inherited, and refresh its metadata.

    Raises
    ------
    RuntimeError
        If a concept ID is stored but no deposits can be found for it.
    """
    concept_id = config.sandbox_concept_id if sandbox else config.zenodo_concept_id

    if concept_id is None:
        deposit = client.create_deposit(config.metadata)
        save_concept_id(config.config_path, sandbox=sandbox, concept_id=deposit["conceptrecid"])
        logger.info("New deposit: id=%s concept=%s", deposit["id"], deposit["conceptrecid"])
        return deposit

    versions = client.list_depositions(concept_id)
    if not versions:
        raise RuntimeError(
            f"No deposits found for concept_id={concept_id!r}. The zenodo.yml may be "
            "stale — clear the concept_id and run `create` again."
        )

    draft = client.new_version(versions[0]["id"])
    for inherited in client.list_files(draft["id"]):
        client.delete_file(draft["id"], inherited["id"])
    draft = client.update_metadata(draft["id"], config.metadata)
    logger.info("New version draft: id=%s (inherited files cleared)", draft["id"])
    return draft


def _upload_bundled(client, bucket_url, name, target, files, staging_dir) -> list[str]:
    """Bundle a target into one zip and upload it; return the source files."""
    zip_path = bundle_target(target, staging_dir)
    if zip_path is None:
        return []
    client.upload_file(bucket_url, zip_path.name, zip_path)
    return [str(f) for f in files]


def _upload_per_file(client, bucket_url, target, files) -> list[str]:
    """Upload each file individually, flattening '/' to '__' in the key."""
    uploaded: list[str] = []
    for file_path in files:
        rel = file_path.relative_to(target.path.parent)
        client.upload_file(bucket_url, str(rel).replace("/", "__"), file_path)
        uploaded.append(str(file_path))
    return uploaded


def upload_targets(
    client: ZenodoClient,
    deposit: dict,
    config: ZenodoConfig,
    sandbox: bool,
    target_names: list[str] | None = None,
    bundle: bool = True,
    staging_dir: Path | None = None,
) -> dict[str, list[str]]:
    """Upload all eligible targets to a draft deposit.

    Parameters
    ----------
    client : ZenodoClient
        Authenticated client.
    deposit : dict
        Draft deposit (must have links.bucket).
    config : ZenodoConfig
        Parsed configuration.
    sandbox : bool
        Selects include_sandbox vs include_production eligibility.
    target_names : list[str] | None
        Restrict to these targets. None = all eligible.
    bundle : bool
        True (default): one .zip per target. False: file-by-file.
    staging_dir : Path | None
        Where to write zips in bundle mode. None -> a temp directory.

    Returns
    -------
    dict[str, list[str]]
        Target name -> list of local source file paths uploaded.
    """
    bucket_url = deposit["links"]["bucket"]
    planned = plan_uploads(config, sandbox=sandbox, target_names=target_names)

    if bundle and staging_dir is None:
        staging_dir = Path(tempfile.mkdtemp(prefix="zenodo_"))

    results: dict[str, list[str]] = {}
    for name, files in planned.items():
        if not files:
            logger.warning("Target %r: no files under %s", name, config.targets[name].path)
            results[name] = []
            continue
        if bundle:
            results[name] = _upload_bundled(
                client, bucket_url, name, config.targets[name], files, staging_dir
            )
        else:
            results[name] = _upload_per_file(client, bucket_url, config.targets[name], files)
        logger.info("Target %r: uploaded %d file(s)", name, len(results[name]))

    return results
