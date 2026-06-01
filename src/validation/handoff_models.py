"""Pydantic v2 models for inter-agent handoff schema validation.

Each class corresponds to a versioned JSON schema defined in
.github/shared/handoff_schemas.md. Validation rules mirror those docs.
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Domain(str, Enum):
    disk = "disk"
    cosmological = "cosmological"
    retrieval = "retrieval"
    xray = "xray"
    lss = "lss"


# ── HypothesisHandoff/v1 ──────────────────────────────────────────────────────


class HypothesisParameter(BaseModel):
    """A single named parameter with value/range and unit."""

    value_or_range: str
    unit: str


class HypothesisEntry(BaseModel):
    """One hypothesis emitted by the hypothesis-agent."""

    id: int
    description: str
    predicted_observables: list[str]
    parameters: dict[str, HypothesisParameter]
    novelty_score: float
    feasibility_score: float
    literature_refs: list[str]

    @field_validator("predicted_observables")
    @classmethod
    def at_least_one_observable(cls, v: list[str]) -> list[str]:
        """Require at least one predicted_observable entry with units."""
        if len(v) < 1:
            raise ValueError("at least 1 predicted_observable required")
        return v

    @field_validator("literature_refs")
    @classmethod
    def at_least_one_ref(cls, v: list[str]) -> list[str]:
        """Require at least one literature_ref ADS bibcode."""
        if len(v) < 1:
            raise ValueError("at least 1 literature_ref (ADS bibcode) required")
        return v


class HypothesisHandoff(BaseModel):
    """HypothesisHandoff/v1 — emitted by @hypothesis-agent after debate.

    The JSON key ``schema`` is aliased to ``schema_name`` because ``schema``
    is a reserved name on Pydantic's BaseModel class.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["HypothesisHandoff/v1"] = Field(alias="schema")
    science_goal: str
    domain: Domain
    hypotheses: list[HypothesisEntry]
    priority_rank: list[int]
    top_hypothesis_id: int
    debate_rounds: int
    human_gate_1_confirmed: bool
    timestamp: str
    warnings: list[str] = []

    @field_validator("hypotheses")
    @classmethod
    def validate_hypotheses_count(cls, v: list) -> list:
        """Enforce the 1–5 hypothesis constraint from the schema spec."""
        if not (1 <= len(v) <= 5):
            raise ValueError("hypotheses must contain 1-5 entries")
        return v

    @model_validator(mode="after")
    def validate_top_hypothesis_id(self) -> "HypothesisHandoff":
        """top_hypothesis_id must equal priority_rank[0]."""
        if self.priority_rank and self.top_hypothesis_id != self.priority_rank[0]:
            raise ValueError(
                f"top_hypothesis_id ({self.top_hypothesis_id}) must equal "
                f"priority_rank[0] ({self.priority_rank[0]})"
            )
        return self
