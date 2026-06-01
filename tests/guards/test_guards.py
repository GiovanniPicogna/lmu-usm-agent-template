import pytest


def test_find_data_missing_in_string():
    from src.validation.guards import find_data_missing
    assert find_data_missing("[DATA MISSING: some field]") == ["(root)"]


def test_find_data_missing_in_nested_dict():
    from src.validation.guards import find_data_missing
    data = {"a": {"b": "[DATA MISSING: x]", "c": "valid"}}
    assert find_data_missing(data) == ["a.b"]


def test_find_data_missing_in_list():
    from src.validation.guards import find_data_missing
    data = {"refs": ["2016A&A...594A.116H", "[DATA MISSING: bibcode]"]}
    assert find_data_missing(data) == ["refs[1]"]


def test_find_data_missing_clean():
    from src.validation.guards import find_data_missing
    assert find_data_missing({"domain": "disk", "hypothesis_ref": 1}) == []


def test_is_valid_bibcode_known_good():
    from src.validation.guards import is_valid_bibcode
    assert is_valid_bibcode("2016A&A...594A.116H")
    assert is_valid_bibcode("2001A&A...365L...1J")
    assert is_valid_bibcode("2009ARA&A..47..481A")


def test_is_valid_bibcode_bad_format():
    from src.validation.guards import is_valid_bibcode
    assert not is_valid_bibcode("arxiv:2604.04604")
    assert not is_valid_bibcode("10.1051/0004-6361/202348158")
    assert not is_valid_bibcode("Author2016")
    assert not is_valid_bibcode("")
    assert not is_valid_bibcode("2016A&A...594A.116")   # too short (18 chars)


def test_is_valid_iso8601_utc_good():
    from src.validation.guards import is_valid_iso8601_utc
    assert is_valid_iso8601_utc("2026-06-01T12:00:00Z")
    assert is_valid_iso8601_utc("2026-01-31T00:00:00Z")


def test_is_valid_iso8601_utc_bad():
    from src.validation.guards import is_valid_iso8601_utc
    assert not is_valid_iso8601_utc("2026-06-01 12:00:00")   # space not T
    assert not is_valid_iso8601_utc("2026-06-01T12:00:00")    # no trailing Z
    assert not is_valid_iso8601_utc("2026-06-01")             # date only
    assert not is_valid_iso8601_utc("[DATA MISSING]")


def test_is_valid_domain_good():
    from src.validation.guards import is_valid_domain
    for d in ("disk", "cosmological", "retrieval", "xray", "lss"):
        assert is_valid_domain(d)


def test_is_valid_domain_bad():
    from src.validation.guards import is_valid_domain
    assert not is_valid_domain("supernova")
    assert not is_valid_domain("Disk")   # case-sensitive
    assert not is_valid_domain("")
