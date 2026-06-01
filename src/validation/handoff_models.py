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


# ── AnalyticalHandoff/v1 ──────────────────────────────────────────────────────


class CharacteristicScale(BaseModel):
    """A named characteristic scale with physical formula and optional reference."""

    value: float
    unit: str
    formula: str
    ref_bibcode: Optional[str] = None


class StabilityCriterion(BaseModel):
    """A named stability criterion with satisfaction status and margin."""

    name: str
    criterion: str
    satisfied: bool
    margin: float
    ref_bibcode: str


class PredictedObservableAnalytical(BaseModel):
    """A predicted observable quantity with uncertainty and formula reference."""

    name: str
    value: float
    unit: str
    uncertainty: float
    formula_ref: str


class AnalyticalHandoff(BaseModel):
    """AnalyticalHandoff/v1 — emitted by @analytical-agent after pre-analysis.

    Consumed by @setup-agent. Requires at least 2 characteristic_scales and
    1 stability_criterion. When linear_regime is False, nonlinear_trigger must
    be provided.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["AnalyticalHandoff/v1"] = Field(alias="schema")
    domain: Domain
    science_goal: str
    hypothesis_ref: int
    characteristic_scales: dict[str, CharacteristicScale]
    stability_criteria: list[StabilityCriterion]
    predicted_observables: list[PredictedObservableAnalytical]
    linear_regime: bool
    nonlinear_trigger: Optional[str] = None
    parameter_recommendations: dict[str, str] = {}
    benchmark_script: Optional[str] = None
    timestamp: str
    warnings: list[str] = []

    @field_validator("characteristic_scales")
    @classmethod
    def at_least_two_scales(cls, v: dict) -> dict:
        """Require at least 2 characteristic scale entries."""
        if len(v) < 2:
            raise ValueError("characteristic_scales must have at least 2 entries")
        return v

    @field_validator("stability_criteria")
    @classmethod
    def at_least_one_criterion(cls, v: list) -> list:
        """Require at least 1 stability criterion entry."""
        if len(v) < 1:
            raise ValueError("stability_criteria must have at least 1 entry")
        return v

    @model_validator(mode="after")
    def nonlinear_requires_trigger(self) -> "AnalyticalHandoff":
        """When linear_regime is False, nonlinear_trigger must be set."""
        if not self.linear_regime and self.nonlinear_trigger is None:
            raise ValueError("nonlinear_trigger is required when linear_regime is False")
        return self


# ── SimConfigHandoff/v1 ──────────────────────────────────────────────────────


class SimCode(str, Enum):
    """Valid simulation codes for SimConfigHandoff."""

    pluto = "PLUTO"
    fargo3d = "FARGO3D"
    dustpy = "DustPy"
    magneticum = "Magneticum"
    gadget = "GADGET"


class SimConfigHandoff(BaseModel):
    """SimConfigHandoff/v1 — emitted by @setup-agent after simulation configuration.

    Consumed by @simulation-agent, @retrieval-agent, or @spectral-agent.
    petitRADTRANS and Sherpa are not valid code values. When hpc_mode is True,
    slurm_script_path is required and run_cmd must be null.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["SimConfigHandoff/v1"] = Field(alias="schema")
    domain: Domain
    task_id: str
    hypothesis_ref: int
    analytical_ref: Optional[str] = None
    code: SimCode
    code_version: str
    config_path: str
    physics_params: dict = {}
    skill_invoked: Optional[str] = None
    hpc_mode: bool
    slurm_script_path: Optional[str] = None
    scheduler: Optional[Literal["slurm", "pbs"]] = None
    n_cores: int
    walltime_h: float
    run_cmd: Optional[str] = None
    validated: bool
    timestamp: str
    warnings: list[str] = []

    @field_validator("code_version")
    @classmethod
    def code_version_not_unknown(cls, v: str) -> str:
        """Reject the sentinel string 'unknown' as a code version."""
        if v == "unknown":
            raise ValueError("code_version must not be 'unknown'")
        return v

    @model_validator(mode="after")
    def hpc_constraints(self) -> "SimConfigHandoff":
        """Enforce HPC mode consistency: slurm_script_path required, run_cmd forbidden."""
        if self.hpc_mode:
            if self.slurm_script_path is None:
                raise ValueError("slurm_script_path required when hpc_mode is True")
            if self.run_cmd is not None:
                raise ValueError("run_cmd must be null when hpc_mode is True")
        return self

    @model_validator(mode="after")
    def validated_must_be_true(self) -> "SimConfigHandoff":
        """validated must be True before handing off to downstream agents."""
        if not self.validated:
            raise ValueError("validated must be True before handoff")
        return self
