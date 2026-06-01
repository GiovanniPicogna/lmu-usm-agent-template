# tests/schemas/test_simconfig_handoff.py
import pytest
from pydantic import ValidationError


def test_valid_simconfig_parses(simconfig_valid_data):
    from src.validation.handoff_models import SimConfigHandoff
    s = SimConfigHandoff.model_validate(simconfig_valid_data)
    assert s.schema_name == "SimConfigHandoff/v1"
    assert s.validated is True


def test_unknown_code_version_rejected(simconfig_valid_data):
    from src.validation.handoff_models import SimConfigHandoff
    simconfig_valid_data["code_version"] = "unknown"
    with pytest.raises(ValidationError, match="unknown"):
        SimConfigHandoff.model_validate(simconfig_valid_data)


def test_hpc_mode_requires_slurm_path(simconfig_valid_data):
    from src.validation.handoff_models import SimConfigHandoff
    simconfig_valid_data["hpc_mode"] = True
    simconfig_valid_data["slurm_script_path"] = None
    simconfig_valid_data["run_cmd"] = None
    with pytest.raises(ValidationError, match="slurm_script_path"):
        SimConfigHandoff.model_validate(simconfig_valid_data)


def test_hpc_mode_forbids_run_cmd(simconfig_valid_data):
    from src.validation.handoff_models import SimConfigHandoff
    simconfig_valid_data["hpc_mode"] = True
    simconfig_valid_data["slurm_script_path"] = "/tmp/job.slurm"
    simconfig_valid_data["run_cmd"] = "python run.py"
    with pytest.raises(ValidationError, match="run_cmd"):
        SimConfigHandoff.model_validate(simconfig_valid_data)


def test_unvalidated_config_rejected(simconfig_valid_data):
    from src.validation.handoff_models import SimConfigHandoff
    simconfig_valid_data["validated"] = False
    with pytest.raises(ValidationError, match="validated"):
        SimConfigHandoff.model_validate(simconfig_valid_data)


def test_invalid_code_rejected(simconfig_valid_data):
    from src.validation.handoff_models import SimConfigHandoff
    simconfig_valid_data["code"] = "petitRADTRANS"
    with pytest.raises(ValidationError):
        SimConfigHandoff.model_validate(simconfig_valid_data)
