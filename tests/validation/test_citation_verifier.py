# tests/validation/test_citation_verifier.py
"""
TDD tests for src/validation/citation_verifier.py.

The citation verifier checks whether a stated claim is grounded in retrieved
source text (abstract or full text). It exists to catch the worst failure mode
in the pipeline: a genuine ADS bibcode lending false authority to a fabricated
prose claim.

API under test:
    verify_claim_against_source(
        bibcode: str,
        claim: str,
        source_text: str,
        min_similarity: float = 0.7,
    ) -> CitationVerificationResult

    CitationVerificationResult.fields:
        bibcode: str
        claim: str
        evidence_span: str | None   -- best matching window from source_text
        provenance: str             -- "full_text" | "abstract_only" | "ungrounded"
        verified: bool
        similarity: float           -- 0.0–1.0 best match score
"""
from src.validation.citation_verifier import (
    CitationVerificationResult,
    verify_claim_against_source,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BIBCODE = "2020A&A...641A...1P"

ABSTRACT = (
    "We present a measurement of the cosmic microwave background angular "
    "power spectrum from the Planck 2018 data release. The spectral index "
    "of scalar perturbations is n_s = 0.965 ± 0.004, consistent with "
    "slow-roll inflation. The optical depth to reionization is tau = 0.054."
)


# ---------------------------------------------------------------------------
# Exact and near-exact matches
# ---------------------------------------------------------------------------


def test_exact_substring_is_verified():
    """Verbatim substring of source → verified=True, span equals claim."""
    claim = "spectral index of scalar perturbations is n_s = 0.965"
    result = verify_claim_against_source(BIBCODE, claim, ABSTRACT)
    assert result.verified is True
    assert result.evidence_span is not None
    assert "0.965" in result.evidence_span


def test_fuzzy_match_above_threshold_is_verified():
    """Paraphrase with high word overlap should still verify."""
    # Slight rewording: "angular power spectrum" vs "power spectrum"
    claim = "cosmic microwave background power spectrum from Planck 2018"
    result = verify_claim_against_source(BIBCODE, claim, ABSTRACT, min_similarity=0.5)
    assert result.verified is True
    assert result.evidence_span is not None


def test_fabricated_claim_is_rejected():
    """A claim with no overlap in source → verified=False, evidence_span=None."""
    claim = "dark energy density is 0.73 and the Hubble constant is 72 km/s/Mpc"
    result = verify_claim_against_source(BIBCODE, claim, ABSTRACT)
    assert result.verified is False
    assert result.similarity < 0.7


def test_similarity_score_is_higher_for_exact_match():
    """Exact substring must produce higher similarity than a fabricated claim."""
    exact_claim = "optical depth to reionization is tau = 0.054"
    fake_claim = "the baryon acoustic oscillation scale is 147 Mpc at redshift 1100"
    exact_result = verify_claim_against_source(BIBCODE, exact_claim, ABSTRACT)
    fake_result = verify_claim_against_source(BIBCODE, fake_claim, ABSTRACT)
    assert exact_result.similarity > fake_result.similarity


# ---------------------------------------------------------------------------
# Provenance / empty source
# ---------------------------------------------------------------------------


def test_empty_source_text_marks_ungrounded():
    """When no source text is provided → verified=False, provenance='ungrounded'."""
    result = verify_claim_against_source(BIBCODE, "some claim", "")
    assert result.verified is False
    assert result.provenance == "ungrounded"
    assert result.evidence_span is None


def test_non_empty_source_is_not_ungrounded():
    """Any non-empty source text must not be marked 'ungrounded'."""
    result = verify_claim_against_source(BIBCODE, "n_s = 0.965", ABSTRACT)
    assert result.provenance != "ungrounded"


def test_provenance_caller_supplied_abstract_only():
    """Caller can pass provenance='abstract_only'; verifier must preserve it."""
    result = verify_claim_against_source(
        BIBCODE, "n_s = 0.965", ABSTRACT, provenance="abstract_only"
    )
    assert result.provenance == "abstract_only"


def test_provenance_caller_supplied_full_text():
    """Caller can pass provenance='full_text'; verifier must preserve it."""
    result = verify_claim_against_source(
        BIBCODE, "n_s = 0.965", ABSTRACT, provenance="full_text"
    )
    assert result.provenance == "full_text"


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_result_carries_bibcode_and_claim():
    """Output must echo the input bibcode and claim unchanged."""
    claim = "n_s = 0.965"
    result = verify_claim_against_source(BIBCODE, claim, ABSTRACT)
    assert result.bibcode == BIBCODE
    assert result.claim == claim


def test_result_is_citation_verification_result_instance():
    result = verify_claim_against_source(BIBCODE, "n_s = 0.965", ABSTRACT)
    assert isinstance(result, CitationVerificationResult)


def test_similarity_bounded_zero_to_one():
    """Similarity must always be in [0.0, 1.0]."""
    for claim in [
        "n_s = 0.965",
        "completely fabricated claim about wormholes",
        "",
    ]:
        result = verify_claim_against_source(BIBCODE, claim, ABSTRACT)
        assert 0.0 <= result.similarity <= 1.0


def test_empty_claim_does_not_raise():
    """Empty claim string must not crash — it cannot be verified."""
    result = verify_claim_against_source(BIBCODE, "", ABSTRACT)
    assert result.verified is False
