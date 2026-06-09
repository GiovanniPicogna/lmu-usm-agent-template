"""
src/validation/astrophysics_stats_linter.py
============================================
Rule-based linter for astrophysics-specific statistical conventions.

Used by both the spectral-agent (at fit time, to catch mistakes early) and
the referee-agent (as an independent re-run, to verify the manuscript claims).
Because these checks are deterministic and LLM-free, the referee's run is
genuinely independent of the paper-agent's self-check.

Conventions enforced
--------------------
1. X-ray fit statistic:
   - C-stat (cstat / wstat / cash) is required when counts per bin < 25.
   - chi2 requires ≥ 25 counts per bin (Gaussian regime).
   Reference: Cash (1979 ApJ 228 939), Arnaud et al. (Sherpa documentation).

2. Confidence interval labelling:
   - X-ray spectral fitting: 90 % CI (standard in the X-ray community).
   - MCMC posteriors: 68 % CI (1σ equivalent).
   - General/default: 68 % CI.
   Reference: group convention, copilot-instructions.md §3.

3. MCMC convergence (Gelman–Rubin):
   - All chains must have R-hat < 1.1.
   Reference: Gelman & Rubin (1992 Stat. Sci. 7 457); handoff_schemas.md §MCMCHandoff.

4. Physical plausibility (hard bounds):
   - photon_index:  0 < Γ ≤ 5  (any standard X-ray source).
   - temperature_kev: kT ≥ 0.1 keV  (galaxy clusters / plasmas).
   - abundance_solar: Z ≥ 0  (non-negative metal abundance).
   Reference: group convention, copilot-instructions.md §9.

Units
-----
All input values are in the natural units of the parameter (keV for
temperature, dimensionless ratio for photon index and abundance).
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StatCheck:
    """Result of a single statistical convention check.

    Parameters
    ----------
    rule:
        Identifier of the rule that was evaluated.
    passed:
        ``True`` if the value satisfies the convention.
    message:
        Human-readable explanation of the result (pass *or* fail).
    """

    rule: str
    passed: bool
    message: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Minimum counts per bin required for the Gaussian (chi-squared) regime.
COUNTS_GAUSSIAN_THRESHOLD: float = 25.0

#: Gelman–Rubin R-hat convergence threshold (strict <).
GELMAN_RUBIN_THRESHOLD: float = 1.1

#: Standard CI percentage per domain.
CI_CONVENTION: dict[str, float] = {
    "xray": 90.0,
    "mcmc": 68.0,
    "general": 68.0,
}

#: Statistics valid for low-count X-ray fitting.
LOW_COUNT_STATS: frozenset[str] = frozenset({"cstat", "wstat", "cash"})

#: Statistics that require the Gaussian regime.
GAUSSIAN_STATS: frozenset[str] = frozenset({"chi2", "chi"})

#: Hard physical bounds: {param_name: (min_exclusive_or_inclusive, max_exclusive)}.
#: Tuples: (lower_bound, lower_inclusive, upper_bound, upper_inclusive).
_PHYSICAL_BOUNDS: dict[str, tuple[float, bool, float, bool]] = {
    # photon_index: Γ must be > 0 and ≤ 5
    "photon_index": (0.0, False, 5.0, True),
    # temperature_kev: kT ≥ 0.1 keV
    "temperature_kev": (0.1, True, 1000.0, True),
    # abundance_solar: Z ≥ 0
    "abundance_solar": (0.0, True, 100.0, True),
}

# ---------------------------------------------------------------------------
# Public check functions
# ---------------------------------------------------------------------------


def check_xray_fit_statistic(
    statistic: str,
    counts_per_bin: float,
) -> StatCheck:
    """Check that the chosen fit statistic is appropriate for the count rate.

    Parameters
    ----------
    statistic:
        Name of the fit statistic as reported in the manuscript
        (e.g. ``"cstat"``, ``"chi2"``).  Case-insensitive.
    counts_per_bin:
        Mean counts per spectral bin.

    Returns
    -------
    StatCheck with ``rule="xray_fit_statistic"``.
    """
    stat = statistic.lower().strip()
    low_counts = counts_per_bin < COUNTS_GAUSSIAN_THRESHOLD

    if stat in LOW_COUNT_STATS:
        return StatCheck(
            rule="xray_fit_statistic",
            passed=True,
            message=(
                f"{stat} is valid for all count regimes " f"(counts/bin={counts_per_bin:.1f})."
            ),
        )

    if stat in GAUSSIAN_STATS:
        if low_counts:
            return StatCheck(
                rule="xray_fit_statistic",
                passed=False,
                message=(
                    f"{stat} requires ≥{COUNTS_GAUSSIAN_THRESHOLD:.0f} counts/bin "
                    f"(Gaussian regime); got {counts_per_bin:.1f}. "
                    "Use cstat instead."
                ),
            )
        return StatCheck(
            rule="xray_fit_statistic",
            passed=True,
            message=(
                f"{stat} is valid: {counts_per_bin:.1f} counts/bin ≥ "
                f"{COUNTS_GAUSSIAN_THRESHOLD:.0f} (Gaussian regime satisfied)."
            ),
        )

    return StatCheck(
        rule="xray_fit_statistic",
        passed=False,
        message=(
            f"Unrecognised fit statistic '{statistic}'. "
            f"Expected one of: cstat, wstat, cash, chi2."
        ),
    )


def check_ci_convention(
    interval_pct: float,
    domain: str,
) -> StatCheck:
    """Check that the reported confidence interval percentage matches convention.

    Parameters
    ----------
    interval_pct:
        Reported CI percentage (e.g. ``90.0`` or ``68.0``).
    domain:
        Context of the interval.  Recognised values:
        ``"xray"`` (spectral fitting), ``"mcmc"`` (posterior), ``"general"``.

    Returns
    -------
    StatCheck with ``rule="ci_convention"``.
    """
    dom = domain.lower().strip()
    expected = CI_CONVENTION.get(dom, CI_CONVENTION["general"])

    if abs(interval_pct - expected) < 0.5:
        return StatCheck(
            rule="ci_convention",
            passed=True,
            message=(
                f"{interval_pct:.0f}% CI matches the {dom} convention "
                f"(expected {expected:.0f}%)."
            ),
        )

    return StatCheck(
        rule="ci_convention",
        passed=False,
        message=(
            f"{interval_pct:.0f}% CI does not match the {dom} convention. "
            f"Expected {expected:.0f}% for domain='{dom}'. "
            "State the convention explicitly if intentionally non-standard."
        ),
    )


def check_mcmc_convergence(r_hat_max: float) -> StatCheck:
    """Check Gelman–Rubin convergence criterion.

    Parameters
    ----------
    r_hat_max:
        Maximum R-hat value across all MCMC parameters.

    Returns
    -------
    StatCheck with ``rule="mcmc_convergence"``.
    """
    if r_hat_max < GELMAN_RUBIN_THRESHOLD:
        return StatCheck(
            rule="mcmc_convergence",
            passed=True,
            message=(
                f"R-hat_max = {r_hat_max:.4f} < {GELMAN_RUBIN_THRESHOLD} — "
                "chains have converged."
            ),
        )

    return StatCheck(
        rule="mcmc_convergence",
        passed=False,
        message=(
            f"R-hat_max = {r_hat_max:.4f} ≥ {GELMAN_RUBIN_THRESHOLD} — "
            "chains have not converged. Extend burn-in or run more steps."
        ),
    )


def check_physical_plausibility(
    param_name: str,
    value: float,
) -> StatCheck:
    """Check that a physical parameter value is within hard plausibility bounds.

    Parameters
    ----------
    param_name:
        Name of the parameter (e.g. ``"photon_index"``, ``"temperature_kev"``).
        Unknown parameter names pass with an informational note.
    value:
        Numerical value of the parameter in its natural units.

    Returns
    -------
    StatCheck with ``rule="physical_plausibility"``.
    """
    if param_name not in _PHYSICAL_BOUNDS:
        return StatCheck(
            rule="physical_plausibility",
            passed=True,
            message=(
                f"Unknown parameter '{param_name}' — no bounds check performed. "
                "Add bounds to _PHYSICAL_BOUNDS if this parameter should be linted."
            ),
        )

    lo, lo_incl, hi, hi_incl = _PHYSICAL_BOUNDS[param_name]

    lo_ok = (value >= lo) if lo_incl else (value > lo)
    hi_ok = (value <= hi) if hi_incl else (value < hi)

    if lo_ok and hi_ok:
        return StatCheck(
            rule="physical_plausibility",
            passed=True,
            message=f"{param_name} = {value} is within physical bounds [{lo}, {hi}].",
        )

    lo_sym = "[" if lo_incl else "("
    hi_sym = "]" if hi_incl else ")"
    return StatCheck(
        rule="physical_plausibility",
        passed=False,
        message=(
            f"{param_name} = {value} is outside physical bounds "
            f"{lo_sym}{lo}, {hi}{hi_sym}. Verify the fit converged correctly."
        ),
    )


def run_all_checks(
    statistic: str,
    counts_per_bin: float,
    ci_pct: float,
    ci_domain: str,
    r_hat_max: float,
    physical_params: dict[str, float] | None = None,
) -> list[StatCheck]:
    """Run all standard astrophysics statistical checks in one call.

    Parameters
    ----------
    statistic:
        Fit statistic name (e.g. ``"cstat"``, ``"chi2"``).
    counts_per_bin:
        Mean counts per spectral bin.
    ci_pct:
        Reported confidence interval percentage.
    ci_domain:
        Domain context for CI convention (``"xray"``, ``"mcmc"``, ``"general"``).
    r_hat_max:
        Maximum Gelman–Rubin R-hat across parameters.
    physical_params:
        Optional mapping of ``{param_name: value}`` for plausibility checks.

    Returns
    -------
    List of StatCheck results — one per rule, plus one per physical parameter.
    """
    checks: list[StatCheck] = [
        check_xray_fit_statistic(statistic, counts_per_bin),
        check_ci_convention(ci_pct, ci_domain),
        check_mcmc_convergence(r_hat_max),
    ]

    for name, val in (physical_params or {}).items():
        checks.append(check_physical_plausibility(name, val))

    return checks
