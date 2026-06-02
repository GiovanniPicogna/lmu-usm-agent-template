"""Unit tests for ZenodoClient REST wrapper.

All HTTP calls are mocked via unittest.mock — no network access required.
The client funnels every call through self._session.request(method, url, ...),
so tests mock `client._session.request`.
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from src.zenodo.client import ZenodoAPIError, ZenodoClient, ZenodoUploadError


# ── helpers ───────────────────────────────────────────────────────────────────


def _ok(data, status_code: int = 200, headers: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = data
    return resp


def _err(status_code: int, message: str) -> MagicMock:
    resp = MagicMock()
    resp.ok = False
    resp.status_code = status_code
    resp.headers = {}
    resp.json.return_value = {"message": message}
    resp.text = message
    return resp


@pytest.fixture
def client() -> ZenodoClient:
    return ZenodoClient(token="test_token", sandbox=True, max_retries=2)


@pytest.fixture
def mock_session(client: ZenodoClient) -> MagicMock:
    mock = MagicMock()
    client._session = mock
    return mock


# ── URL selection + auth ──────────────────────────────────────────────────────


def test_sandbox_uses_sandbox_url():
    assert "sandbox.zenodo.org" in ZenodoClient(token="t", sandbox=True)._base_url


def test_production_uses_production_url():
    assert ZenodoClient(token="t", sandbox=False)._base_url == "https://zenodo.org/api"


def test_bearer_token_in_session_headers():
    c = ZenodoClient(token="my_secret", sandbox=True)
    assert c._session.headers["Authorization"] == "Bearer my_secret"


# ── _request: timeout + retry ─────────────────────────────────────────────────


def test_request_injects_default_timeout(client, mock_session):
    mock_session.request.return_value = _ok({})
    client.get_deposit(1)
    assert mock_session.request.call_args.kwargs["timeout"] == client.timeout


def test_request_retries_on_429_then_succeeds(client, mock_session, mock_deposit):
    mock_session.request.side_effect = [
        _err(429, "Too Many Requests"),
        _ok(mock_deposit),
    ]
    with patch("src.zenodo.client.time.sleep") as mock_sleep:
        result = client.get_deposit(12345)
    assert result["id"] == 12345
    assert mock_session.request.call_count == 2
    mock_sleep.assert_called_once()


def test_request_gives_up_after_max_retries(client, mock_session):
    mock_session.request.return_value = _err(429, "Too Many Requests")
    with patch("src.zenodo.client.time.sleep"):
        with pytest.raises(ZenodoAPIError) as exc:
            client.get_deposit(1)
    assert exc.value.status_code == 429
    # initial try + max_retries (2) = 3 calls
    assert mock_session.request.call_count == 3


# ── create_deposit ────────────────────────────────────────────────────────────


def test_create_deposit_posts_to_depositions_endpoint(client, mock_session, mock_deposit):
    mock_session.request.return_value = _ok(mock_deposit, status_code=201)
    metadata = {"title": "Test", "upload_type": "dataset", "creators": [{"name": "A, B"}]}

    result = client.create_deposit(metadata)

    method, url = mock_session.request.call_args.args
    assert method == "POST"
    assert url.endswith("/deposit/depositions")
    assert mock_session.request.call_args.kwargs["json"] == {"metadata": metadata}
    assert result["id"] == 12345


def test_create_deposit_raises_on_401(client, mock_session):
    mock_session.request.return_value = _err(401, "Invalid token")
    with pytest.raises(ZenodoAPIError) as exc:
        client.create_deposit({"title": "x"})
    assert exc.value.status_code == 401
    assert "Invalid token" in str(exc.value)


# ── get_deposit + update_metadata ─────────────────────────────────────────────


def test_get_deposit_fetches_by_id(client, mock_session, mock_deposit):
    mock_session.request.return_value = _ok(mock_deposit)
    result = client.get_deposit(12345)
    method, url = mock_session.request.call_args.args
    assert method == "GET"
    assert "/deposit/depositions/12345" in url
    assert result["id"] == 12345


def test_update_metadata_puts_metadata(client, mock_session, mock_deposit):
    mock_session.request.return_value = _ok(mock_deposit)
    client.update_metadata(12345, {"title": "New"})
    method, url = mock_session.request.call_args.args
    assert method == "PUT"
    assert url.endswith("/deposit/depositions/12345")
    assert mock_session.request.call_args.kwargs["json"] == {"metadata": {"title": "New"}}


# ── new_version (two requests: action, then latest_draft GET) ──────────────────


def test_new_version_follows_latest_draft_link(client, mock_session, mock_deposit):
    original = dict(mock_deposit)
    draft = dict(mock_deposit)
    draft["id"] = 67890
    mock_session.request.side_effect = [_ok(original), _ok(draft)]

    result = client.new_version(12345)

    first, second = mock_session.request.call_args_list
    assert first.args[0] == "POST"
    assert first.args[1].endswith("/12345/actions/newversion")
    assert second.args[0] == "GET"
    assert second.args[1] == original["links"]["latest_draft"]
    assert result["id"] == 67890


# ── list_files + delete_file ──────────────────────────────────────────────────


def test_list_files_returns_file_list(client, mock_session):
    mock_session.request.return_value = _ok([{"id": "f1", "filename": "a.json"}])
    files = client.list_files(12345)
    method, url = mock_session.request.call_args.args
    assert method == "GET"
    assert url.endswith("/deposit/depositions/12345/files")
    assert files[0]["id"] == "f1"


def test_delete_file_issues_delete(client, mock_session):
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 204
    resp.headers = {}
    mock_session.request.return_value = resp
    client.delete_file(12345, "f1")
    method, url = mock_session.request.call_args.args
    assert method == "DELETE"
    assert url.endswith("/deposit/depositions/12345/files/f1")


# ── upload_file (bucket PUT + checksum verification) ───────────────────────────


def test_upload_file_puts_to_bucket_url_and_verifies_checksum(client, mock_session, tmp_path):
    fpath = tmp_path / "results.zip"
    fpath.write_bytes(b"fake-archive")
    md5 = hashlib.md5(b"fake-archive").hexdigest()
    mock_session.request.return_value = _ok({"key": "results.zip", "checksum": f"md5:{md5}"})

    result = client.upload_file(
        bucket_url="https://sandbox.zenodo.org/api/files/bucket-abc",
        filename="results.zip",
        path=fpath,
    )

    method, url = mock_session.request.call_args.args
    assert method == "PUT"
    assert url == "https://sandbox.zenodo.org/api/files/bucket-abc/results.zip"
    assert result["key"] == "results.zip"


def test_upload_file_raises_on_checksum_mismatch(client, mock_session, tmp_path):
    fpath = tmp_path / "results.zip"
    fpath.write_bytes(b"fake-archive")
    mock_session.request.return_value = _ok({"key": "results.zip", "checksum": "md5:deadbeef"})

    with pytest.raises(ZenodoUploadError, match="[Cc]hecksum"):
        client.upload_file(
            bucket_url="https://sandbox.zenodo.org/api/files/bucket-abc",
            filename="results.zip",
            path=fpath,
        )


# ── publish ───────────────────────────────────────────────────────────────────


def test_publish_calls_actions_publish_endpoint(client, mock_session, mock_published_deposit):
    mock_session.request.return_value = _ok(mock_published_deposit)
    result = client.publish(12345)
    method, url = mock_session.request.call_args.args
    assert method == "POST"
    assert "12345/actions/publish" in url
    assert result["doi"] == "10.5281/zenodo.12345"


# ── list_depositions (sorted, newest first) ───────────────────────────────────


def test_list_depositions_queries_concept_id_sorted(client, mock_session, mock_deposit):
    mock_session.request.return_value = _ok([mock_deposit])
    results = client.list_depositions("12344")
    params = mock_session.request.call_args.kwargs["params"]
    assert params["q"] == "conceptrecid:12344"
    assert params["sort"] == "mostrecent"
    assert len(results) == 1


def test_error_includes_status_code_and_message(client, mock_session):
    mock_session.request.return_value = _err(403, "Forbidden — deposit is not yours")
    with pytest.raises(ZenodoAPIError) as exc:
        client.get_deposit(99999)
    assert "403" in str(exc.value)
    assert "Forbidden" in str(exc.value)
