# tests/schemas/test_analysis_handoff.py
import pytest
from pydantic import ValidationError


def test_valid_analysis_parses(analysis_valid_data):
    from src.validation.handoff_models import AnalysisHandoff

    a = AnalysisHandoff.model_validate(analysis_valid_data)
    assert a.schema_name == "AnalysisHandoff/v1"
    assert a.sanity_passed is True


def test_empty_plot_paths_rejected(analysis_valid_data):
    from src.validation.handoff_models import AnalysisHandoff

    analysis_valid_data["plot_paths"] = []
    with pytest.raises(ValidationError, match="non-empty"):
        AnalysisHandoff.model_validate(analysis_valid_data)


def test_sanity_not_passed_rejected(analysis_valid_data):
    from src.validation.handoff_models import AnalysisHandoff

    analysis_valid_data["sanity_passed"] = False
    with pytest.raises(ValidationError, match="sanity_passed"):
        AnalysisHandoff.model_validate(analysis_valid_data)
