import pytest
from pydantic import ValidationError


def test_valid_hypothesis_parses(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    h = HypothesisHandoff.model_validate(hypothesis_valid_data)
    assert h.schema_name == "HypothesisHandoff/v1"
    assert h.domain.value == "disk"
    assert len(h.hypotheses) == 1


def test_gate_is_false_on_emission(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    h = HypothesisHandoff.model_validate(hypothesis_valid_data)
    assert h.human_gate_1_confirmed is False


def test_top_hypothesis_must_equal_priority_rank_zero(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    hypothesis_valid_data["top_hypothesis_id"] = 99
    with pytest.raises(ValidationError, match="top_hypothesis_id"):
        HypothesisHandoff.model_validate(hypothesis_valid_data)


def test_hypotheses_must_have_at_least_one(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    hypothesis_valid_data["hypotheses"] = []
    with pytest.raises(ValidationError, match="1-5"):
        HypothesisHandoff.model_validate(hypothesis_valid_data)


def test_hypotheses_max_five(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    base = hypothesis_valid_data["hypotheses"][0].copy()
    hypothesis_valid_data["hypotheses"] = [{**base, "id": i} for i in range(1, 7)]
    hypothesis_valid_data["priority_rank"] = list(range(1, 7))
    hypothesis_valid_data["top_hypothesis_id"] = 1
    with pytest.raises(ValidationError, match="1-5"):
        HypothesisHandoff.model_validate(hypothesis_valid_data)


def test_invalid_domain_rejected(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    hypothesis_valid_data["domain"] = "supernova"
    with pytest.raises(ValidationError):
        HypothesisHandoff.model_validate(hypothesis_valid_data)


def test_empty_predicted_observables_rejected(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    hypothesis_valid_data["hypotheses"][0]["predicted_observables"] = []
    with pytest.raises(ValidationError, match="predicted_observable"):
        HypothesisHandoff.model_validate(hypothesis_valid_data)


def test_empty_literature_refs_rejected(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    hypothesis_valid_data["hypotheses"][0]["literature_refs"] = []
    with pytest.raises(ValidationError, match="literature_ref"):
        HypothesisHandoff.model_validate(hypothesis_valid_data)


def test_wrong_schema_name_rejected(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff
    hypothesis_valid_data["schema"] = "WrongSchema/v1"
    with pytest.raises(ValidationError):
        HypothesisHandoff.model_validate(hypothesis_valid_data)
