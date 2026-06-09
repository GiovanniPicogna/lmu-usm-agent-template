"""
src/validation/citation_verifier.py
====================================
Content-level citation verification for the LMU Astrophysics pipeline.

Addresses the worst failure mode in LLM pipelines: a genuine ADS bibcode
lending false authority to a fabricated prose claim.  The literature-agent
retrieves verified bibcodes/BibTeX (metadata layer); this module checks
whether a stated claim is actually supported by the retrieved source text
(content layer).

Usage (called by the literature-agent after retrieving abstract/full text):

    result = verify_claim_against_source(
        bibcode="2020A&A...641A...1P",
        claim="The spectral index is n_s = 0.965",
        source_text=abstract_text,       # from ADS ads_library_documents
        provenance="abstract_only",      # or "full_text"
    )
    if not result.verified:
        # Surface as [DATA MISSING: CLAIM NOT GROUNDED — <bibcode>]

Units / assumptions
-------------------
- Similarity is a dimensionless ratio in [0.0, 1.0].
- Default min_similarity=0.7 is a conservative threshold; callers may lower
  it to 0.5 for paraphrase detection or raise to 0.95 for near-verbatim
  requirements.
- Text normalisation strips punctuation and collapses whitespace; it is
  not stemming — claim tokens must appear in the source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

Provenance = Literal["full_text", "abstract_only", "ungrounded"]


@dataclass(frozen=True)
class CitationVerificationResult:
    """Outcome of verifying one claim against one source text.

    Parameters
    ----------
    bibcode:
        ADS bibcode of the source paper.
    claim:
        The stated claim submitted for verification.
    evidence_span:
        The best-matching text window from *source_text*, or ``None`` when
        no match was found or the source was empty.
    provenance:
        ``"full_text"`` — caller supplied full article text.
        ``"abstract_only"`` — caller supplied only the abstract.
        ``"ungrounded"`` — no source text was available; the claim cannot
        be checked.
    verified:
        ``True`` when *similarity* ≥ *min_similarity* and source is non-empty.
    similarity:
        Best-window similarity score in [0.0, 1.0].
    """

    bibcode: str
    claim: str
    evidence_span: str | None
    provenance: str
    verified: bool
    similarity: float


def verify_claim_against_source(
    bibcode: str,
    claim: str,
    source_text: str,
    min_similarity: float = 0.7,
    provenance: str = "abstract_only",
) -> CitationVerificationResult:
    """Verify whether *claim* is grounded in *source_text*.

    Parameters
    ----------
    bibcode:
        ADS bibcode identifying the source paper.
    claim:
        Prose claim to verify (may be a direct quote or a paraphrase).
    source_text:
        Retrieved text to search — abstract or full text from ADS.
        Pass ``""`` when no text could be retrieved.
    min_similarity:
        Minimum SequenceMatcher ratio for ``verified=True``.
        Default 0.7 catches close paraphrases; raise to 0.95 for verbatim
        quote requirements.
    provenance:
        Caller-supplied provenance tag.  When *source_text* is empty this
        is overridden to ``"ungrounded"``.

    Returns
    -------
    CitationVerificationResult
        Always returns a result — never raises on bad input.
    """
    # --- Guard: empty source ------------------------------------------------
    if not source_text:
        return CitationVerificationResult(
            bibcode=bibcode,
            claim=claim,
            evidence_span=None,
            provenance="ungrounded",
            verified=False,
            similarity=0.0,
        )

    # --- Guard: empty claim -------------------------------------------------
    if not claim:
        return CitationVerificationResult(
            bibcode=bibcode,
            claim=claim,
            evidence_span=None,
            provenance=provenance,
            verified=False,
            similarity=0.0,
        )

    # --- Fast exact-substring check (case- and whitespace-normalised) -------
    norm_claim = _normalise(claim)
    norm_source = _normalise(source_text)

    if norm_claim in norm_source:
        # Map back to original text (approximate; normalization may shift offsets)
        span = _extract_span(source_text, claim)
        return CitationVerificationResult(
            bibcode=bibcode,
            claim=claim,
            evidence_span=span or claim,
            provenance=provenance,
            verified=True,
            similarity=1.0,
        )

    # --- Sliding-window fuzzy match ----------------------------------------
    best_sim, best_span = _best_window_similarity(norm_claim, norm_source, source_text)

    verified = best_sim >= min_similarity
    return CitationVerificationResult(
        bibcode=bibcode,
        claim=claim,
        evidence_span=best_span if verified else None,
        provenance=provenance,
        verified=verified,
        similarity=max(0.0, min(1.0, best_sim)),
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_span(source_text: str, claim: str) -> str | None:
    """Find the claim as a substring in source_text (case-insensitive)."""
    lower_source = source_text.lower()
    lower_claim = claim.lower()
    idx = lower_source.find(lower_claim)
    if idx >= 0:
        return source_text[idx : idx + len(claim)]
    return None


def _best_window_similarity(
    norm_claim: str,
    norm_source: str,
    orig_source: str,
) -> tuple[float, str | None]:
    """Find the source window that best matches *norm_claim*.

    Slides a window of size ``len(norm_claim)`` (±50 %) through
    *norm_source* and returns the maximum SequenceMatcher ratio together
    with the corresponding text window from *orig_source*.

    Returns
    -------
    (best_similarity, best_span | None)
    """
    claim_len = len(norm_claim)
    if claim_len == 0:
        return 0.0, None

    source_len = len(norm_source)
    if source_len < claim_len // 2:
        # Source is shorter than half the claim — score the whole source
        sim = SequenceMatcher(None, norm_claim, norm_source).ratio()
        return sim, orig_source if sim > 0 else None

    # Window sizes to try: exact claim length ± 50 %
    min_win = max(1, int(claim_len * 0.5))
    max_win = int(claim_len * 1.5)
    step = max(1, claim_len // 10)  # avoid scanning char-by-char on long texts

    best_sim = 0.0
    best_window_norm: str | None = None

    for win_size in range(min_win, min(max_win + 1, source_len + 1), step):
        for start in range(0, source_len - win_size + 1, step):
            window = norm_source[start : start + win_size]
            sim = SequenceMatcher(None, norm_claim, window, autojunk=False).ratio()
            if sim > best_sim:
                best_sim = sim
                best_window_norm = window

    # Map best window back to a readable span from orig_source (approximate)
    best_span: str | None = None
    if best_window_norm and best_sim > 0:
        # Search orig_source for the first ~20 chars of the best window
        search_prefix = best_window_norm[:20]
        idx = orig_source.lower().find(search_prefix)
        if idx >= 0:
            # Extend to match window length in original
            end = min(idx + len(best_window_norm) + 20, len(orig_source))
            best_span = orig_source[idx:end]

    return best_sim, best_span
