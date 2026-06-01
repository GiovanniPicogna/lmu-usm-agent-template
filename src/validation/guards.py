import re
from typing import Any

_DATA_MISSING_PREFIX = "[DATA MISSING"
_BIBCODE_RE = re.compile(r"^\d{4}[A-Za-z&.]{5}[A-Za-z\d.]{9}[A-Z]$")
_ISO8601_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_VALID_DOMAINS = frozenset({"disk", "cosmological", "retrieval", "xray", "lss"})


def find_data_missing(obj: Any, path: str = "") -> list[str]:
    """Return dotted paths of all [DATA MISSING] sentinel values in a nested structure.

    Parameters
    ----------
    obj : Any
        The object to search — may be a str, dict, list, or any scalar.
    path : str
        Dotted key path accumulated during recursion. Leave empty on initial call.

    Returns
    -------
    list[str]
        Dotted paths (e.g. ``"a.b"``, ``"refs[1]"``) where a ``[DATA MISSING``
        sentinel was found. Returns ``["(root)"]`` when ``obj`` itself is the
        sentinel string. Returns ``[]`` when no sentinels are present.
    """
    found: list[str] = []
    if isinstance(obj, str) and obj.startswith(_DATA_MISSING_PREFIX):
        found.append(path or "(root)")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found.extend(find_data_missing(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(find_data_missing(item, f"{path}[{i}]"))
    return found


def is_valid_bibcode(bibcode: str) -> bool:
    """Return True if bibcode matches the 19-character ADS bibcode format.

    Parameters
    ----------
    bibcode : str
        The candidate bibcode string.

    Returns
    -------
    bool
        ``True`` when the string matches ``YYYY<5 chars><9 chars><UPPERCASE>``.

    Examples
    --------
    >>> is_valid_bibcode("2016A&A...594A.116H")
    True
    >>> is_valid_bibcode("arxiv:2604.04604")
    False
    """
    return bool(_BIBCODE_RE.match(bibcode))


def is_valid_iso8601_utc(timestamp: str) -> bool:
    """Return True if timestamp is ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ).

    Parameters
    ----------
    timestamp : str
        The candidate timestamp string.

    Returns
    -------
    bool
        ``True`` only when the string matches ``YYYY-MM-DDTHH:MM:SSZ`` exactly.

    Examples
    --------
    >>> is_valid_iso8601_utc("2026-06-01T12:00:00Z")
    True
    >>> is_valid_iso8601_utc("2026-06-01 12:00:00")
    False
    """
    return bool(_ISO8601_UTC_RE.match(timestamp))


def is_valid_domain(domain: str) -> bool:
    """Return True if domain is one of the five supported pipeline domains.

    Parameters
    ----------
    domain : str
        The candidate domain string.

    Returns
    -------
    bool
        ``True`` for ``"disk"``, ``"cosmological"``, ``"retrieval"``,
        ``"xray"``, or ``"lss"`` (case-sensitive). ``False`` otherwise.
    """
    return domain in _VALID_DOMAINS
