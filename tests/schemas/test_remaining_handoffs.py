# tests/schemas/test_remaining_handoffs.py
import pytest
from pydantic import ValidationError


# ── SpectralFitHandoff ────────────────────────────────────────────────────────


def test_valid_spectralfit_parses(spectralfit_valid_data):
    from src.validation.handoff_models import SpectralFitHandoff

    s = SpectralFitHandoff.model_validate(spectralfit_valid_data)
    assert s.schema_name == "SpectralFitHandoff/v1"
    assert s.fit_passed_sanity is True


def test_spectralfit_sanity_not_passed_rejected(spectralfit_valid_data):
    from src.validation.handoff_models import SpectralFitHandoff

    spectralfit_valid_data["fit_passed_sanity"] = False
    with pytest.raises(ValidationError, match="fit_passed_sanity"):
        SpectralFitHandoff.model_validate(spectralfit_valid_data)


def test_spectralfit_invalid_stat_rejected(spectralfit_valid_data):
    from src.validation.handoff_models import SpectralFitHandoff

    spectralfit_valid_data["fit_statistic"]["stat"] = "mle"
    with pytest.raises(ValidationError):
        SpectralFitHandoff.model_validate(spectralfit_valid_data)


# ── MCMCHandoff ───────────────────────────────────────────────────────────────


def test_valid_mcmc_parses(mcmc_valid_data):
    from src.validation.handoff_models import MCMCHandoff

    m = MCMCHandoff.model_validate(mcmc_valid_data)
    assert m.schema_name == "MCMCHandoff/v1"
    assert m.converged is True
    assert m.seed == 42


def test_mcmc_not_converged_rejected(mcmc_valid_data):
    from src.validation.handoff_models import MCMCHandoff

    mcmc_valid_data["converged"] = False
    with pytest.raises(ValidationError, match="converged"):
        MCMCHandoff.model_validate(mcmc_valid_data)


def test_mcmc_gelman_rubin_too_high_rejected(mcmc_valid_data):
    from src.validation.handoff_models import MCMCHandoff

    mcmc_valid_data["gelman_rubin_max"] = 1.15
    with pytest.raises(ValidationError, match="1.1"):
        MCMCHandoff.model_validate(mcmc_valid_data)


def test_mcmc_gelman_rubin_at_threshold_rejected(mcmc_valid_data):
    from src.validation.handoff_models import MCMCHandoff

    mcmc_valid_data["gelman_rubin_max"] = 1.1
    with pytest.raises(ValidationError, match="1.1"):
        MCMCHandoff.model_validate(mcmc_valid_data)


# ── PaperHandoff ──────────────────────────────────────────────────────────────


def test_valid_paper_parses(paper_valid_data):
    from src.validation.handoff_models import PaperHandoff

    p = PaperHandoff.model_validate(paper_valid_data)
    assert p.schema_name == "PaperHandoff/v1"
    assert p.compilation_status.value == "ok"


def test_ok_status_without_pdf_rejected(paper_valid_data):
    from src.validation.handoff_models import PaperHandoff

    paper_valid_data["manuscript_pdf"] = None
    with pytest.raises(ValidationError, match="manuscript_pdf"):
        PaperHandoff.model_validate(paper_valid_data)


def test_errors_status_without_pdf_accepted(paper_valid_data):
    from src.validation.handoff_models import PaperHandoff

    paper_valid_data["compilation_status"] = "errors"
    paper_valid_data["manuscript_pdf"] = None
    paper_valid_data["latex_errors"] = ["Undefined control sequence \\foo"]
    p = PaperHandoff.model_validate(paper_valid_data)
    assert p.manuscript_pdf is None
