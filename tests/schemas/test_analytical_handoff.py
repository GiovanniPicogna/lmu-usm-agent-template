# tests/schemas/test_analytical_handoff.py
import pytest
from pydantic import ValidationError


def test_valid_analytical_parses(analytical_valid_data):
    from src.validation.handoff_models import AnalyticalHandoff

    a = AnalyticalHandoff.model_validate(analytical_valid_data)
    assert a.schema_name == "AnalyticalHandoff/v1"
    assert a.linear_regime is True


def test_nonlinear_without_trigger_rejected(analytical_valid_data):
    from src.validation.handoff_models import AnalyticalHandoff

    analytical_valid_data["linear_regime"] = False
    analytical_valid_data["nonlinear_trigger"] = None
    with pytest.raises(ValidationError, match="nonlinear_trigger"):
        AnalyticalHandoff.model_validate(analytical_valid_data)


def test_nonlinear_with_trigger_accepted(analytical_valid_data):
    from src.validation.handoff_models import AnalyticalHandoff

    analytical_valid_data["linear_regime"] = False
    analytical_valid_data["nonlinear_trigger"] = "gap depth exceeds 90%; spiral arms form"
    a = AnalyticalHandoff.model_validate(analytical_valid_data)
    assert a.nonlinear_trigger is not None


def test_fewer_than_two_scales_rejected(analytical_valid_data):
    from src.validation.handoff_models import AnalyticalHandoff

    analytical_valid_data["characteristic_scales"] = {
        "hill_radius": analytical_valid_data["characteristic_scales"]["hill_radius"]
    }
    with pytest.raises(ValidationError, match="2 entries"):
        AnalyticalHandoff.model_validate(analytical_valid_data)


def test_empty_stability_criteria_rejected(analytical_valid_data):
    from src.validation.handoff_models import AnalyticalHandoff

    analytical_valid_data["stability_criteria"] = []
    with pytest.raises(ValidationError, match="1 entry"):
        AnalyticalHandoff.model_validate(analytical_valid_data)
