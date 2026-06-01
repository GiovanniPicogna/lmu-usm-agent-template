# tests/schemas/test_simulation_handoff.py
import pytest
from pydantic import ValidationError


def test_valid_simulation_parses(simulation_valid_data):
    from src.validation.handoff_models import SimulationHandoff

    s = SimulationHandoff.model_validate(simulation_valid_data)
    assert s.schema_name == "SimulationHandoff/v1"
    assert s.sanity_passed is True


def test_unknown_code_version_rejected(simulation_valid_data):
    from src.validation.handoff_models import SimulationHandoff

    simulation_valid_data["code_version"] = "unknown"
    with pytest.raises(ValidationError, match="unknown"):
        SimulationHandoff.model_validate(simulation_valid_data)


def test_unknown_skill_script_version_rejected(simulation_valid_data):
    from src.validation.handoff_models import SimulationHandoff

    simulation_valid_data["skill_script_version"] = "unknown"
    with pytest.raises(ValidationError, match="unknown"):
        SimulationHandoff.model_validate(simulation_valid_data)


def test_unknown_rho_units_rejected(simulation_valid_data):
    from src.validation.handoff_models import SimulationHandoff

    simulation_valid_data["diagnostics"]["rho_units"] = "unknown"
    with pytest.raises(ValidationError, match="unknown"):
        SimulationHandoff.model_validate(simulation_valid_data)


def test_sanity_not_passed_rejected(simulation_valid_data):
    from src.validation.handoff_models import SimulationHandoff

    simulation_valid_data["sanity_passed"] = False
    with pytest.raises(ValidationError, match="sanity_passed"):
        SimulationHandoff.model_validate(simulation_valid_data)
