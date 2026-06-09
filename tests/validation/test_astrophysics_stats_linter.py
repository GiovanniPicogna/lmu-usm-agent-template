# tests/validation/test_astrophysics_stats_linter.py
"""
TDD tests for src/validation/astrophysics_stats_linter.py.

Rule-based checks for astrophysics-specific statistical conventions.
Used by both the spectral-agent (at fit time) and the referee-agent (as an
independent re-run). Deterministic and LLM-free — critical for independence.

API under test:
    StatCheck(rule: str, passed: bool, message: str)

    check_xray_fit_statistic(statistic: str, counts_per_bin: float) -> StatCheck
    check_ci_convention(interval_pct: float, domain: str) -> StatCheck
    check_mcmc_convergence(r_hat_max: float) -> StatCheck
    check_physical_plausibility(param_name: str, value: float) -> StatCheck
    run_all_checks(...) -> list[StatCheck]
"""
from src.validation.astrophysics_stats_linter import (
    StatCheck,
    check_ci_convention,
    check_mcmc_convergence,
    check_physical_plausibility,
    check_xray_fit_statistic,
    run_all_checks,
)


# ---------------------------------------------------------------------------
# check_xray_fit_statistic
# ---------------------------------------------------------------------------


def test_cstat_accepted_for_low_counts():
    """C-stat with <25 counts/bin is the correct choice — must pass."""
    result = check_xray_fit_statistic("cstat", counts_per_bin=8.0)
    assert result.passed is True


def test_chi2_rejected_for_low_counts():
    """chi2 with <25 counts/bin violates Gaussian approximation — must fail."""
    result = check_xray_fit_statistic("chi2", counts_per_bin=12.0)
    assert result.passed is False
    assert "cstat" in result.message.lower()


def test_chi2_accepted_for_high_counts():
    """chi2 with ≥25 counts/bin satisfies Gaussian regime — must pass."""
    result = check_xray_fit_statistic("chi2", counts_per_bin=30.0)
    assert result.passed is True


def test_cstat_accepted_for_high_counts():
    """C-stat is valid for any count rate — must pass even with high counts."""
    result = check_xray_fit_statistic("cstat", counts_per_bin=100.0)
    assert result.passed is True


def test_wstat_accepted_for_low_counts():
    """W-stat (background-subtracted C-stat) is valid for low counts."""
    result = check_xray_fit_statistic("wstat", counts_per_bin=5.0)
    assert result.passed is True


def test_unknown_statistic_fails_with_message():
    """An unrecognised statistic name must fail with an informative message."""
    result = check_xray_fit_statistic("r_squared", counts_per_bin=20.0)
    assert result.passed is False
    assert "r_squared" in result.message


def test_stat_check_carries_rule_name():
    result = check_xray_fit_statistic("cstat", counts_per_bin=10.0)
    assert result.rule == "xray_fit_statistic"


# ---------------------------------------------------------------------------
# check_ci_convention
# ---------------------------------------------------------------------------


def test_ninety_pct_ci_xray_domain_passes():
    """90 % CI is the X-ray astronomy convention — must pass in 'xray' domain."""
    result = check_ci_convention(interval_pct=90.0, domain="xray")
    assert result.passed is True


def test_sixty_eight_pct_ci_xray_domain_warns():
    """68 % CI in X-ray context is non-standard — must warn."""
    result = check_ci_convention(interval_pct=68.0, domain="xray")
    assert result.passed is False
    assert "90" in result.message


def test_sixty_eight_pct_ci_mcmc_domain_passes():
    """68 % (1σ) CI is the MCMC/posterior convention — must pass."""
    result = check_ci_convention(interval_pct=68.0, domain="mcmc")
    assert result.passed is True


def test_ninety_pct_ci_mcmc_domain_warns():
    """90 % CI reported for MCMC posterior is non-standard — must warn."""
    result = check_ci_convention(interval_pct=90.0, domain="mcmc")
    assert result.passed is False
    assert "68" in result.message


def test_sixty_eight_pct_ci_general_domain_passes():
    """68 % CI is acceptable in 'general' domain (default science convention)."""
    result = check_ci_convention(interval_pct=68.0, domain="general")
    assert result.passed is True


def test_ci_check_carries_rule_name():
    result = check_ci_convention(interval_pct=90.0, domain="xray")
    assert result.rule == "ci_convention"


# ---------------------------------------------------------------------------
# check_mcmc_convergence
# ---------------------------------------------------------------------------


def test_gelman_rubin_below_threshold_converged():
    """R-hat = 1.05 < 1.1 threshold → converged."""
    result = check_mcmc_convergence(r_hat_max=1.05)
    assert result.passed is True


def test_gelman_rubin_at_threshold_borderline():
    """R-hat exactly at 1.1 → must fail (strict <, not ≤)."""
    result = check_mcmc_convergence(r_hat_max=1.1)
    assert result.passed is False


def test_gelman_rubin_above_threshold_not_converged():
    """R-hat = 1.5 >> 1.1 → clearly not converged."""
    result = check_mcmc_convergence(r_hat_max=1.5)
    assert result.passed is False
    assert "1.1" in result.message


def test_gelman_rubin_perfect():
    """R-hat = 1.0 (ideal) → must pass."""
    result = check_mcmc_convergence(r_hat_max=1.0)
    assert result.passed is True


def test_convergence_check_carries_rule_name():
    result = check_mcmc_convergence(r_hat_max=1.05)
    assert result.rule == "mcmc_convergence"


# ---------------------------------------------------------------------------
# check_physical_plausibility
# ---------------------------------------------------------------------------


def test_photon_index_physical():
    """Γ = 1.7 is typical AGN/X-ray binary photon index — must pass."""
    result = check_physical_plausibility("photon_index", 1.7)
    assert result.passed is True


def test_photon_index_too_steep_fails():
    """Γ > 5 is physically implausible for any standard X-ray source."""
    result = check_physical_plausibility("photon_index", 6.5)
    assert result.passed is False
    assert "5" in result.message


def test_photon_index_negative_fails():
    """Negative photon index is unphysical."""
    result = check_physical_plausibility("photon_index", -0.5)
    assert result.passed is False


def test_temperature_physical_kev():
    """kT = 5.0 keV is a typical cluster ICM temperature — must pass."""
    result = check_physical_plausibility("temperature_kev", 5.0)
    assert result.passed is True


def test_temperature_too_low_kev():
    """kT < 0.1 keV for a galaxy cluster is implausible — must fail."""
    result = check_physical_plausibility("temperature_kev", 0.05)
    assert result.passed is False
    assert "0.1" in result.message


def test_abundance_physical():
    """Solar abundance Z = 0.3 Z_sun is physically reasonable — must pass."""
    result = check_physical_plausibility("abundance_solar", 0.3)
    assert result.passed is True


def test_abundance_negative_fails():
    """Negative metal abundance is unphysical."""
    result = check_physical_plausibility("abundance_solar", -0.1)
    assert result.passed is False


def test_unknown_param_passes_with_note():
    """Unknown parameter name must not raise — pass with an informational message."""
    result = check_physical_plausibility("my_custom_param", 42.0)
    assert result.passed is True
    assert "unknown" in result.message.lower()


def test_plausibility_check_carries_rule_name():
    result = check_physical_plausibility("photon_index", 1.7)
    assert result.rule == "physical_plausibility"


# ---------------------------------------------------------------------------
# run_all_checks
# ---------------------------------------------------------------------------


def test_run_all_checks_returns_list_of_stat_checks():
    """run_all_checks must return a non-empty list of StatCheck objects."""
    checks = run_all_checks(
        statistic="cstat",
        counts_per_bin=10.0,
        ci_pct=68.0,
        ci_domain="mcmc",
        r_hat_max=1.05,
        physical_params={"photon_index": 1.7, "temperature_kev": 3.0},
    )
    assert len(checks) >= 4
    assert all(isinstance(c, StatCheck) for c in checks)


def test_run_all_checks_all_pass_for_valid_inputs():
    checks = run_all_checks(
        statistic="cstat",
        counts_per_bin=10.0,
        ci_pct=90.0,
        ci_domain="xray",
        r_hat_max=1.02,
        physical_params={"photon_index": 1.8, "temperature_kev": 4.0},
    )
    failures = [c for c in checks if not c.passed]
    assert failures == [], f"Expected all checks to pass; failures: {failures}"


def test_run_all_checks_surfaces_failure():
    checks = run_all_checks(
        statistic="chi2",
        counts_per_bin=8.0,  # chi2 with low counts → fail
        ci_pct=90.0,
        ci_domain="xray",
        r_hat_max=1.02,
        physical_params={"photon_index": 1.8},
    )
    failures = [c for c in checks if not c.passed]
    assert len(failures) >= 1
    assert any(c.rule == "xray_fit_statistic" for c in failures)
