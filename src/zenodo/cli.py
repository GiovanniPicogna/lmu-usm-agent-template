"""Click CLI for the Zenodo upload integration.

Entry point: python -m src.zenodo

Commands
--------
create   Plan/create a draft deposit (or new version) and upload files.
publish  Publish a draft deposit, assigning a permanent DOI (confirmation gated).
status   Show the current state of a deposit.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import click

from src.zenodo.client import ZenodoAPIError, ZenodoClient, ZenodoUploadError
from src.zenodo.config import load_config
from src.zenodo.upload import create_or_new_version, plan_uploads, upload_targets

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

_DEFAULT_ZENODO_YML = "zenodo.yml"
_DEFAULT_CITATION_CFF = "CITATION.cff"


def _get_token(sandbox: bool) -> str:
    """Read the API token from the environment or raise a ClickException."""
    env_var = "ZENODO_SANDBOX_TOKEN" if sandbox else "ZENODO_TOKEN"
    token = os.environ.get(env_var)
    if not token:
        raise click.ClickException(
            f"Environment variable {env_var!r} is not set.\n"
            "Create a token (scopes: deposit:write, deposit:actions) at:\n"
            "  Sandbox:    https://sandbox.zenodo.org/account/settings/applications/\n"
            "  Production: https://zenodo.org/account/settings/applications/\n"
            f"Then export {env_var}=<your-token>"
        )
    return token


@click.group()
def cli() -> None:
    """Upload research data to Zenodo or Zenodo Sandbox for open science."""


@cli.command()
@click.option(
    "--sandbox/--no-sandbox",
    default=True,
    show_default=True,
    help="Target Zenodo Sandbox (default) or production Zenodo.",
)
@click.option(
    "--target",
    "target_names",
    multiple=True,
    help="Restrict upload to these named targets (default: all applicable).",
)
@click.option(
    "--bundle/--no-bundle",
    default=True,
    show_default=True,
    help="Upload one .zip per target (default) or each file individually.",
)
@click.option("--dry-run", is_flag=True, help="Print the upload plan and exit without uploading.")
@click.option("--yes", is_flag=True, help="Skip the production-data confirmation prompt.")
@click.option("--config", "config_path", default=_DEFAULT_ZENODO_YML, show_default=True)
@click.option("--citation-cff", "citation_path", default=_DEFAULT_CITATION_CFF, show_default=True)
def create(
    sandbox: bool,
    target_names: tuple[str, ...],
    bundle: bool,
    dry_run: bool,
    yes: bool,
    config_path: str,
    citation_path: str,
) -> None:
    """Create a draft deposit (or a new version) and upload files."""
    token_required = not dry_run
    if token_required:
        token = _get_token(sandbox)

    config = load_config(config_path=Path(config_path), citation_path=Path(citation_path))
    names = list(target_names) or None

    plan = plan_uploads(config, sandbox=sandbox, target_names=names)
    total = sum(len(files) for files in plan.values())
    if total == 0:
        raise click.ClickException(
            "No files found to upload. Note that results/, plots/, and data/ are "
            "git-ignored — run this locally after generating outputs, or check your "
            "zenodo.yml target paths."
        )

    if dry_run:
        click.echo(
            f"DRY RUN — {total} file(s) would be uploaded to "
            f"{'Zenodo Sandbox' if sandbox else 'Zenodo (production)'}:"
        )
        for name, files in plan.items():
            click.echo(f"  [{name}] {len(files)} file(s)")
            for file_path in files:
                click.echo(f"      {file_path}")
        return

    if not sandbox and not yes:
        click.confirm(
            "You are about to upload to PRODUCTION Zenodo. Confirm you have PI "
            "approval and that the data is NOT proprietary or under embargo "
            "(see copilot-instructions.md §8, §10). Continue?",
            abort=True,
        )

    client = ZenodoClient(token=token, sandbox=sandbox)
    click.echo(f"Creating deposit on {'Zenodo Sandbox' if sandbox else 'Zenodo'}...")

    try:
        deposit = create_or_new_version(client, config, sandbox=sandbox)
        results = upload_targets(
            client, deposit, config, sandbox=sandbox, target_names=names, bundle=bundle
        )
    except (ZenodoAPIError, ZenodoUploadError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"  Deposit ID : {deposit['id']}")
    click.echo(f"  Concept ID : {deposit['conceptrecid']}")
    click.echo(f"  URL        : {deposit['links'].get('html', 'N/A')}")
    uploaded_total = sum(len(files) for files in results.values())
    for name, files in results.items():
        click.echo(f"  [{name}] {len(files)} file(s)")
    click.echo(f"Done — {uploaded_total} file(s) staged in the draft.")
    click.echo(
        f"\nTo publish: python -m src.zenodo publish --deposit-id {deposit['id']}"
        + ("" if sandbox else " --no-sandbox")
        + ("" if not sandbox else " --sandbox")
    )


@cli.command()
@click.option("--sandbox/--no-sandbox", default=True, show_default=True)
@click.option(
    "--deposit-id", required=True, type=int, help="Deposit ID to publish (printed by `create`)."
)
@click.option("--yes", is_flag=True, help="Skip the irreversible-publish confirmation prompt.")
def publish(sandbox: bool, deposit_id: int, yes: bool) -> None:
    """Publish a draft deposit, assigning a permanent DOI (irreversible)."""
    token = _get_token(sandbox)
    target_label = "Zenodo Sandbox" if sandbox else "PRODUCTION Zenodo"
    if not yes:
        click.confirm(
            f"Publishing deposit {deposit_id} on {target_label} is PERMANENT and "
            "assigns a citable DOI that cannot be deleted. Continue?",
            abort=True,
        )

    client = ZenodoClient(token=token, sandbox=sandbox)
    try:
        deposit = client.publish(deposit_id)
    except ZenodoAPIError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"  DOI : {deposit.get('doi', 'N/A')}")
    click.echo(f"  URL : {deposit.get('doi_url') or deposit['links'].get('html', 'N/A')}")
    click.echo("Published successfully.")


@cli.command()
@click.option("--sandbox/--no-sandbox", default=True, show_default=True)
@click.option("--deposit-id", required=True, type=int, help="Deposit ID to inspect.")
def status(sandbox: bool, deposit_id: int) -> None:
    """Show the current state of a deposit."""
    token = _get_token(sandbox)
    client = ZenodoClient(token=token, sandbox=sandbox)
    try:
        deposit = client.get_deposit(deposit_id)
    except ZenodoAPIError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Deposit {deposit_id}:")
    click.echo(f"  State      : {deposit.get('state', 'unknown')}")
    click.echo(f"  Title      : {deposit.get('title', 'N/A')}")
    click.echo(f"  Concept ID : {deposit.get('conceptrecid', 'N/A')}")
    click.echo(f"  DOI        : {deposit.get('doi') or 'not yet assigned'}")
    click.echo(f"  URL        : {deposit['links'].get('html', 'N/A')}")
    click.echo(f"  Files      : {len(deposit.get('files', []))}")
