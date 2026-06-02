"""Resilient wrapper around the Zenodo REST API v1.

Every HTTP call is funnelled through ``_request``, which injects a default
timeout and retries on HTTP 429 / 5xx with exponential backoff (honouring the
``Retry-After`` header). File uploads use the bucket (S3-like PUT) API and
verify the returned MD5 against the local file. Non-2xx responses raise
``ZenodoAPIError``; checksum mismatches raise ``ZenodoUploadError``.

Reference: https://developers.zenodo.org/
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_RETRY_STATUS = {429, 500, 502, 503, 504}
_CHUNK = 1 << 20  # 1 MiB


class ZenodoAPIError(Exception):
    """Raised when the Zenodo API returns a non-2xx response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Zenodo API error {status_code}: {message}")


class ZenodoUploadError(Exception):
    """Raised when an uploaded file fails post-upload integrity verification."""


def _md5(path: Path) -> str:
    """Compute the MD5 hex digest of a file, streaming in 1 MiB chunks."""
    digest = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ZenodoClient:
    """REST client for the Zenodo deposit API.

    Parameters
    ----------
    token : str
        Personal access token. Required scopes: deposit:write, deposit:actions.
    sandbox : bool
        True -> sandbox.zenodo.org (default). False -> zenodo.org (production).
    timeout : float
        Per-request timeout in seconds.
    max_retries : int
        Number of retries on transient (429 / 5xx) responses.
    """

    _BASE_URLS: dict[str, str] = {
        "sandbox": "https://sandbox.zenodo.org/api",
        "production": "https://zenodo.org/api",
    }

    def __init__(
        self, token: str, sandbox: bool = True, timeout: float = 60.0, max_retries: int = 3
    ) -> None:
        self._base_url = self._BASE_URLS["sandbox" if sandbox else "production"]
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        self.timeout = timeout
        self.max_retries = max_retries

    # ── internal ──────────────────────────────────────────────────────────────

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Issue an HTTP request with timeout and transient-error backoff."""
        kwargs.setdefault("timeout", self.timeout)
        response = self._session.request(method, url, **kwargs)
        for attempt in range(self.max_retries):
            if response.status_code not in _RETRY_STATUS:
                return response
            wait = float(response.headers.get("Retry-After", 2**attempt))
            logger.warning(
                "Transient %s from Zenodo; retry %d/%d in %.1fs",
                response.status_code,
                attempt + 1,
                self.max_retries,
                wait,
            )
            time.sleep(wait)
            response = self._session.request(method, url, **kwargs)
        return response

    def _raise_for_status(self, response: requests.Response) -> None:
        """Raise ZenodoAPIError if the response is not 2xx."""
        if not response.ok:
            try:
                message = response.json().get("message", response.text[:200])
            except ValueError:
                message = response.text[:200]
            raise ZenodoAPIError(response.status_code, message)

    # ── deposit management ────────────────────────────────────────────────────

    def create_deposit(self, metadata: dict) -> dict:
        """Create a new empty draft deposit.

        Parameters
        ----------
        metadata : dict
            Zenodo metadata (must include 'title', 'upload_type', 'creators').

        Returns
        -------
        dict
            Deposit resource with 'id', 'conceptrecid', and 'links'.
        """
        url = f"{self._base_url}/deposit/depositions"
        response = self._request("POST", url, json={"metadata": metadata})
        self._raise_for_status(response)
        deposit = response.json()
        logger.info("Created deposit %s (concept %s)", deposit["id"], deposit["conceptrecid"])
        return deposit

    def get_deposit(self, deposit_id: int) -> dict:
        """Fetch the current state of a deposit by numeric ID."""
        url = f"{self._base_url}/deposit/depositions/{deposit_id}"
        response = self._request("GET", url)
        self._raise_for_status(response)
        return response.json()

    def update_metadata(self, deposit_id: int, metadata: dict) -> dict:
        """Replace metadata on a draft deposit (full replacement)."""
        url = f"{self._base_url}/deposit/depositions/{deposit_id}"
        response = self._request("PUT", url, json={"metadata": metadata})
        self._raise_for_status(response)
        return response.json()

    def new_version(self, deposit_id: int) -> dict:
        """Open a new draft version of a published deposit.

        The Zenodo ``newversion`` action returns the *original* deposit; the new
        draft lives at ``links.latest_draft``. NOTE: the new draft inherits the
        previous version's files — callers must clear them (see upload.py).

        Parameters
        ----------
        deposit_id : int
            Deposit ID of the latest published version.

        Returns
        -------
        dict
            The new draft deposit resource.
        """
        url = f"{self._base_url}/deposit/depositions/{deposit_id}/actions/newversion"
        response = self._request("POST", url)
        self._raise_for_status(response)
        latest_draft_url = response.json()["links"]["latest_draft"]
        draft_response = self._request("GET", latest_draft_url)
        self._raise_for_status(draft_response)
        draft = draft_response.json()
        logger.info("Opened new version draft: deposit %s", draft["id"])
        return draft

    def list_files(self, deposit_id: int) -> list[dict]:
        """List files currently attached to a draft deposit."""
        url = f"{self._base_url}/deposit/depositions/{deposit_id}/files"
        response = self._request("GET", url)
        self._raise_for_status(response)
        return response.json()

    def delete_file(self, deposit_id: int, file_id: str) -> None:
        """Delete a single file from a draft deposit by its file ID."""
        url = f"{self._base_url}/deposit/depositions/{deposit_id}/files/{file_id}"
        response = self._request("DELETE", url)
        self._raise_for_status(response)
        logger.info("Deleted file %s from deposit %s", file_id, deposit_id)

    def upload_file(
        self, bucket_url: str, filename: str, path: Path, verify_checksum: bool = True
    ) -> dict:
        """Upload a file via the bucket API and verify its MD5.

        Parameters
        ----------
        bucket_url : str
            The 'bucket' URL from deposit['links']['bucket'].
        filename : str
            Filename as it will appear in the Zenodo record.
        path : Path
            Local file to upload.
        verify_checksum : bool
            If True, compare the API-returned MD5 against the local file's MD5.

        Returns
        -------
        dict
            File resource from the API (includes 'key' and 'checksum').

        Raises
        ------
        ZenodoUploadError
            If verify_checksum is True and the digests differ.
        """
        url = f"{bucket_url}/{filename}"
        with path.open("rb") as fh:
            response = self._request("PUT", url, data=fh)
        self._raise_for_status(response)
        result = response.json()
        if verify_checksum:
            remote = result.get("checksum", "")
            local = f"md5:{_md5(path)}"
            if remote and remote != local:
                raise ZenodoUploadError(
                    f"Checksum mismatch for {filename}: remote {remote} != local {local}"
                )
        logger.info("Uploaded %s -> %s", path, filename)
        return result

    def publish(self, deposit_id: int) -> dict:
        """Publish a draft deposit, assigning a permanent DOI (irreversible)."""
        url = f"{self._base_url}/deposit/depositions/{deposit_id}/actions/publish"
        response = self._request("POST", url)
        self._raise_for_status(response)
        deposit = response.json()
        logger.info("Published deposit %s — DOI: %s", deposit_id, deposit.get("doi", "N/A"))
        return deposit

    def list_depositions(self, concept_id: str) -> list[dict]:
        """List all versions for a concept ID, newest first.

        Parameters
        ----------
        concept_id : str
            Zenodo concept record ID (stable across versions).

        Returns
        -------
        list[dict]
            Deposit versions, sorted most-recent first.
        """
        url = f"{self._base_url}/deposit/depositions"
        params = {"q": f"conceptrecid:{concept_id}", "sort": "mostrecent", "size": 25}
        response = self._request("GET", url, params=params)
        self._raise_for_status(response)
        return response.json()
