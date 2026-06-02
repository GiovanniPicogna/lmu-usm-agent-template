import pytest
from pydantic import ValidationError


def test_valid_referee_parses(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    r = RefereeHandoff.model_validate(referee_valid_data)
    assert r.schema_name == "RefereeHandoff/v1"
    assert r.next_action == "revise"


def test_revise_without_comments_rejected(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    referee_valid_data["major_comments"] = []
    referee_valid_data["minor_comments"] = []
    with pytest.raises(ValidationError, match="comment"):
        RefereeHandoff.model_validate(referee_valid_data)


def test_reject_without_reason_rejected(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    referee_valid_data["recommendation"] = "reject"
    referee_valid_data["next_action"] = "reject"
    referee_valid_data["reject_reason"] = None
    with pytest.raises(ValidationError, match="reject_reason"):
        RefereeHandoff.model_validate(referee_valid_data)


def test_accept_with_major_comments_rejected(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    referee_valid_data["recommendation"] = "accept"
    referee_valid_data["next_action"] = "accept"
    referee_valid_data["major_comments"] = ["Rework the entire methods section."]
    with pytest.raises(ValidationError, match="accept"):
        RefereeHandoff.model_validate(referee_valid_data)


def test_reject_recommendation_with_accept_action_rejected(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    referee_valid_data["recommendation"] = "reject"
    referee_valid_data["next_action"] = "accept"
    referee_valid_data["reject_reason"] = "Result already published."
    with pytest.raises(ValidationError, match="reject"):
        RefereeHandoff.model_validate(referee_valid_data)


def test_major_revision_with_accept_action_rejected(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    referee_valid_data["recommendation"] = "major_revision"
    referee_valid_data["next_action"] = "accept"
    referee_valid_data["major_comments"] = ["Fundamental methodology flaw."]
    with pytest.raises(ValidationError, match="major_revision"):
        RefereeHandoff.model_validate(referee_valid_data)


def test_novelty_without_prior_work_refs_rejected(referee_valid_data):
    from src.validation.handoff_models import RefereeHandoff

    referee_valid_data["novelty"]["prior_work_refs"] = []
    with pytest.raises(ValidationError, match="prior_work_refs"):
        RefereeHandoff.model_validate(referee_valid_data)
