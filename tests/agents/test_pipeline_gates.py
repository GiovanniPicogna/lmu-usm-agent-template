# tests/agents/test_pipeline_gates.py
import pytest
from pathlib import Path


@pytest.fixture
def confirmed_hypothesis(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff

    data = {**hypothesis_valid_data, "human_gate_1_confirmed": True}
    return HypothesisHandoff.model_validate(data)


@pytest.fixture
def unconfirmed_hypothesis(hypothesis_valid_data):
    from src.validation.handoff_models import HypothesisHandoff

    return HypothesisHandoff.model_validate(hypothesis_valid_data)


@pytest.fixture
def confirmed_interpretation(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff

    data = {**interpretation_valid_data, "human_gate_2_confirmed": True}
    return InterpretationHandoff.model_validate(data)


@pytest.fixture
def unconfirmed_interpretation(interpretation_valid_data):
    from src.validation.handoff_models import InterpretationHandoff

    return InterpretationHandoff.model_validate(interpretation_valid_data)


# ── Gate 1 ────────────────────────────────────────────────────────────────────


def test_gate_1_passes_when_confirmed(confirmed_hypothesis):
    from src.validation.routing import check_gate_1

    check_gate_1(confirmed_hypothesis)  # must not raise


def test_gate_1_raises_when_not_confirmed(unconfirmed_hypothesis):
    from src.validation.routing import check_gate_1, GateNotConfirmedError

    with pytest.raises(GateNotConfirmedError, match="Gate 1"):
        check_gate_1(unconfirmed_hypothesis)


# ── Gate 2 ────────────────────────────────────────────────────────────────────


def test_gate_2_passes_when_confirmed(confirmed_interpretation):
    from src.validation.routing import check_gate_2

    check_gate_2(confirmed_interpretation)  # must not raise


def test_gate_2_raises_when_not_confirmed(unconfirmed_interpretation):
    from src.validation.routing import check_gate_2, GateNotConfirmedError

    with pytest.raises(GateNotConfirmedError, match="Gate 2"):
        check_gate_2(unconfirmed_interpretation)


@pytest.fixture
def confirmed_referee(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    data = {**referee_valid_data, "human_gate_3_confirmed": True}
    return RefereeHandoff.model_validate(data)


@pytest.fixture
def unconfirmed_referee(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    return RefereeHandoff.model_validate(referee_valid_data)


# ── Gate 3 ────────────────────────────────────────────────────────────────────


def test_gate_3_passes_when_confirmed(confirmed_referee):
    from src.validation.routing import check_gate_3

    check_gate_3(confirmed_referee)  # must not raise


def test_gate_3_raises_when_not_confirmed(unconfirmed_referee):
    from src.validation.routing import check_gate_3, GateNotConfirmedError

    with pytest.raises(GateNotConfirmedError, match="Gate 3"):
        check_gate_3(unconfirmed_referee)


# ── [DATA MISSING] guard ──────────────────────────────────────────────────────


def test_data_missing_guard_raises_on_sentinel():
    from src.validation.routing import check_no_data_missing, DataMissingError

    data = {"domain": "disk", "code_version": "[DATA MISSING: read from env]"}
    with pytest.raises(DataMissingError, match="code_version"):
        check_no_data_missing(data)


def test_data_missing_guard_passes_on_clean_data():
    from src.validation.routing import check_no_data_missing

    data = {"domain": "disk", "code_version": "v2.0-rc1"}
    check_no_data_missing(data)  # must not raise


# ── Abort path ────────────────────────────────────────────────────────────────


def test_abort_path_returns_correct_file(tmp_path, interpretation_valid_data):
    from src.validation.routing import check_abort_path
    from src.validation.handoff_models import InterpretationHandoff

    data = {
        **interpretation_valid_data,
        "hypothesis_match": "refuted",
        "next_action": "abort",
        "abort_reason": "Simulation diverged; could not proceed.",
    }
    handoff = InterpretationHandoff.model_validate(data)
    abort_file = check_abort_path(handoff, tmp_path)
    assert abort_file == tmp_path / "disk_gap_depth_1mjup" / "abort_report.json"


def test_abort_path_raises_on_non_abort(interpretation_valid_data):
    from src.validation.routing import check_abort_path
    from src.validation.handoff_models import InterpretationHandoff

    handoff = InterpretationHandoff.model_validate(interpretation_valid_data)
    with pytest.raises(ValueError, match="non-abort"):
        check_abort_path(handoff, Path("/tmp"))


# ── Gate 3 restructure: autonomous, bounded paper↔referee loop ────────────────


def _referee(referee_valid_data, **overrides):
    from src.validation.handoff_models import RefereeHandoff

    return RefereeHandoff.model_validate({**referee_valid_data, **overrides})


def test_referee_loop_revises_autonomously_within_budget(referee_valid_data):
    from src.validation.routing import referee_loop_decision

    handoff = _referee(referee_valid_data, next_action="revise", revision_round=1)
    assert referee_loop_decision(handoff, max_revision_rounds=3) == "revise_autonomous"


def test_referee_loop_escalates_to_human_when_budget_exhausted(referee_valid_data):
    from src.validation.routing import referee_loop_decision

    handoff = _referee(referee_valid_data, next_action="revise", revision_round=3)
    assert referee_loop_decision(handoff, max_revision_rounds=3) == "human_gate_3"


def test_referee_loop_escalates_to_human_on_accept(referee_valid_data):
    from src.validation.routing import referee_loop_decision

    handoff = _referee(
        referee_valid_data,
        recommendation="accept",
        next_action="accept",
        major_comments=[],
    )
    assert referee_loop_decision(handoff) == "human_gate_3"


def test_referee_loop_escalates_to_human_on_reject(referee_valid_data):
    from src.validation.routing import referee_loop_decision

    handoff = _referee(
        referee_valid_data,
        recommendation="reject",
        next_action="reject",
        reject_reason="Fatal methodological flaw in the gap-depth definition.",
    )
    assert referee_loop_decision(handoff) == "human_gate_3"
