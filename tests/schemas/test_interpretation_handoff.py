# tests/schemas/test_interpretation_handoff.py
import pytest
from pydantic import ValidationError


def test_valid_interpretation_parses(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    i = InterpretationHandoff.model_validate(interpretation_valid_data)
    assert i.schema_name == "InterpretationHandoff/v1"
    assert i.hypothesis_match.value == "confirmed"
    assert i.next_action.value == "write"


def test_gate_2_is_false_on_emission(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    i = InterpretationHandoff.model_validate(interpretation_valid_data)
    assert i.human_gate_2_confirmed is False


def test_empty_findings_rejected(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    interpretation_valid_data["findings"] = []
    with pytest.raises(ValidationError, match="1 entry"):
        InterpretationHandoff.model_validate(interpretation_valid_data)


def test_finding_without_literature_refs_rejected(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    interpretation_valid_data["findings"][0]["literature_refs"] = []
    with pytest.raises(ValidationError, match="literature_ref"):
        InterpretationHandoff.model_validate(interpretation_valid_data)


def test_refuted_requires_iterate_or_abort(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    interpretation_valid_data["hypothesis_match"] = "refuted"
    interpretation_valid_data["next_action"] = "stop"
    with pytest.raises(ValidationError, match="refuted"):
        InterpretationHandoff.model_validate(interpretation_valid_data)


def test_refuted_with_iterate_accepted(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    interpretation_valid_data["hypothesis_match"] = "refuted"
    interpretation_valid_data["next_action"] = "iterate"
    i = InterpretationHandoff.model_validate(interpretation_valid_data)
    assert i.next_action.value == "iterate"


def test_abort_requires_reason(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    interpretation_valid_data["next_action"] = "abort"
    interpretation_valid_data["abort_reason"] = None
    with pytest.raises(ValidationError, match="abort_reason"):
        InterpretationHandoff.model_validate(interpretation_valid_data)


def test_abort_with_reason_accepted(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    interpretation_valid_data["hypothesis_match"] = "refuted"
    interpretation_valid_data["next_action"] = "abort"
    interpretation_valid_data["abort_reason"] = "Simulation diverged; fundamental blocker."
    i = InterpretationHandoff.model_validate(interpretation_valid_data)
    assert i.abort_reason is not None


def test_invalid_next_action_rejected(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff
    interpretation_valid_data["next_action"] = "publish"
    with pytest.raises(ValidationError):
        InterpretationHandoff.model_validate(interpretation_valid_data)
