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


# ── SimulationHandoff/v1 ──────────────────────────────────────────────────────


class SimCode2(str, Enum):
    """Valid simulation codes for SimulationHandoff."""

    fargo3d = "FARGO3D"
    pluto = "PLUTO"
    dustpy = "DustPy"
    magneticum = "Magneticum"


class SimDiagnostics(BaseModel):
    """Diagnostic metrics recorded after a simulation run."""

    n_snapshots: int
    last_snap: int
    t_end_code: float
    rho_field: str
    rho_units: str
    rho_max: float
    rho_min: float
    wall_clock_s: float

    @field_validator("rho_units")
    @classmethod
    def rho_units_not_unknown(cls, v: str) -> str:
        """Reject the sentinel string 'unknown' as rho_units."""
        if v == "unknown":
            raise ValueError("rho_units must not be 'unknown'")
        return v


class SimUnits(BaseModel):
    """Code unit system used in the simulation."""

    length: str
    mass: str
    time: str
    density: str


class SimulationHandoff(BaseModel):
    """SimulationHandoff/v1 — emitted by @simulation-agent after a successful run.

    Consumed by @spectral-agent or @mcmc-agent. code_version and
    skill_script_version must not be 'unknown'; rho_units must be explicit.
    sanity_passed must be True before handoff.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["SimulationHandoff/v1"] = Field(alias="schema")
    task_id: str
    run_dir: str
    run_manifest: str
    code: SimCode2
    code_version: str
    skill_script: str
    skill_script_version: str
    param_file: str
    param_file_md5: str
    output_dir: str
    output_files: list[str]
    diagnostics: SimDiagnostics
    units: SimUnits
    sanity_passed: bool
    timestamp: str
    warnings: list[str] = []

    @field_validator("code_version")
    @classmethod
    def code_version_not_unknown(cls, v: str) -> str:
        """Reject the sentinel string 'unknown' as code_version."""
        if v == "unknown":
            raise ValueError("code_version must not be 'unknown'")
        return v

    @field_validator("skill_script_version")
    @classmethod
    def skill_script_version_not_unknown(cls, v: str) -> str:
        """Reject the sentinel string 'unknown' as skill_script_version."""
        if v == "unknown":
            raise ValueError("skill_script_version must not be 'unknown'")
        return v

    @model_validator(mode="after")
    def sanity_passed_required(self) -> "SimulationHandoff":
        """sanity_passed must be True before handing off to downstream agents."""
        if not self.sanity_passed:
            raise ValueError("sanity_passed must be True before handoff")
        return self


# ── AnalysisHandoff/v1 ──────────────────────────────────────────────────────


class DiagnosticEntry(BaseModel):
    """A single diagnostic metric with value, unit, and optional snapshot index."""

    value: float
    unit: str
    snapshot: Optional[int] = None


class AnalyticalComparisonEntry(BaseModel):
    """Comparison between analytical prediction and numerical result."""

    analytical: float
    numerical: float
    unit: str
    agreement_pct: float


class AnalysisHandoff(BaseModel):
    """AnalysisHandoff/v1 — emitted by @analysis-agent after post-processing.

    Consumed by @interpretation-agent or @mcmc-agent. plot_paths must be
    non-empty and sanity_passed must be True before handoff.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["AnalysisHandoff/v1"] = Field(alias="schema")
    domain: Domain
    task_id: str
    output_dir: str
    sim_config_ref: str
    simulation_ref: Optional[str] = None
    diagnostics: dict[str, DiagnosticEntry] = {}
    plot_paths: list[str]
    data_hash: str
    analytical_comparison: dict[str, AnalyticalComparisonEntry] = {}
    sanity_passed: bool
    timestamp: str
    warnings: list[str] = []

    @field_validator("plot_paths")
    @classmethod
    def plot_paths_non_empty(cls, v: list) -> list:
        """Require at least one plot path."""
        if len(v) < 1:
            raise ValueError("plot_paths must be non-empty")
        return v

    @model_validator(mode="after")
    def sanity_passed_required(self) -> "AnalysisHandoff":
        """sanity_passed must be True before handing off to downstream agents."""
        if not self.sanity_passed:
            raise ValueError("sanity_passed must be True before handoff")
        return self


# ── InterpretationHandoff/v1 ──────────────────────────────────────────────────


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class HypothesisMatch(str, Enum):
    confirmed = "confirmed"
    partial = "partial"
    refuted = "refuted"


class NextAction(str, Enum):
    iterate = "iterate"
    write = "write"
    mcmc = "mcmc"
    stop = "stop"
    abort = "abort"


class Finding(BaseModel):
    """A single finding with evidence, confidence, and literature references."""

    statement: str
    evidence: str
    confidence: Confidence
    literature_refs: list[str]


class InterpretationHandoff(BaseModel):
    """InterpretationHandoff/v1 — emitted by @interpretation-agent after Gate 2.

    Consumed by @hypothesis-agent (next_action='iterate') or returned to the user.
    findings must contain at least 1 entry with at least 1 literature_ref.
    hypothesis_match='refuted' requires next_action='iterate' or 'abort'.
    next_action='abort' requires a non-null abort_reason.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["InterpretationHandoff/v1"] = Field(alias="schema")
    domain: Domain
    task_id: str
    science_goal: str
    findings: list[Finding]
    hypothesis_match: HypothesisMatch
    analytical_agreement_summary: str
    plausibility_flags: list[str] = []
    caveats: list[str] = []
    followup_suggestions: list[str] = []
    next_action: NextAction
    abort_reason: Optional[str] = None
    human_gate_2_confirmed: bool
    timestamp: str
    warnings: list[str] = []

    @field_validator("findings")
    @classmethod
    def validate_findings(cls, v: list[Finding]) -> list[Finding]:
        """Require at least 1 finding, each with at least 1 literature_ref."""
        if len(v) < 1:
            raise ValueError("findings must contain at least 1 entry")
        for f in v:
            if not f.literature_refs:
                raise ValueError("each finding must have at least 1 literature_ref")
        return v

    @model_validator(mode="after")
    def refuted_requires_iterate_or_abort(self) -> "InterpretationHandoff":
        """hypothesis_match='refuted' requires next_action='iterate' or 'abort'."""
        if self.hypothesis_match == HypothesisMatch.refuted and self.next_action not in (
            NextAction.iterate,
            NextAction.abort,
        ):
            raise ValueError("hypothesis_match='refuted' requires next_action='iterate' or 'abort'")
        return self

    @model_validator(mode="after")
    def abort_requires_reason(self) -> "InterpretationHandoff":
        """next_action='abort' requires a non-null abort_reason."""
        if self.next_action == NextAction.abort and self.abort_reason is None:
            raise ValueError("abort_reason is required when next_action is 'abort'")
        return self


# ── SpectralFitHandoff/v1 ─────────────────────────────────────────────────────


class FitStatistic(BaseModel):
    """Fit statistic type, value, and degrees of freedom."""

    stat: Literal["cstat", "chi2", "wstat"]
    value: float
    dof: int


class BestFitParam(BaseModel):
    """A single best-fit parameter with value, unit, and frozen flag."""

    value: float
    unit: str
    frozen: bool


class SpectralFitHandoff(BaseModel):
    """SpectralFitHandoff/v1 — emitted by @spectral-agent after a converged fit.

    Consumed by @mcmc-agent for posterior refinement. fit_passed_sanity must be
    True; for counts < 25 per bin stat must be 'cstat'. parameter_grid is
    required when handing off to @mcmc-agent.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["SpectralFitHandoff/v1"] = Field(alias="schema")
    spectrum_file: str
    background_file: Optional[str] = None
    energy_range_keV: list[float]
    model: str
    best_fit: dict[str, BestFitParam]
    fit_statistic: FitStatistic
    fit_passed_sanity: bool
    parameter_grid: Optional[str] = None
    timestamp: str
    warnings: list[str] = []

    @model_validator(mode="after")
    def sanity_passed_required(self) -> "SpectralFitHandoff":
        """fit_passed_sanity must be True before handoff to downstream agents."""
        if not self.fit_passed_sanity:
            raise ValueError("fit_passed_sanity must be True before handoff")
        return self


# ── MCMCHandoff/v1 ────────────────────────────────────────────────────────────


class Sampler(str, Enum):
    emcee = "emcee"
    dynesty = "dynesty"


class MCMCHandoff(BaseModel):
    """MCMCHandoff/v1 — emitted by @mcmc-agent after convergence is confirmed.

    Returned to the user or @hypothesis-agent for iteration. converged must be
    True and gelman_rubin_max must be strictly below 1.1 (R-hat threshold).
    Uncertainties are 68% credible intervals (1σ). seed must match HDF5 attr.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["MCMCHandoff/v1"] = Field(alias="schema")
    chain_file: str
    sampler: Sampler
    n_walkers: int
    n_steps: int
    burn_in: int
    converged: bool
    gelman_rubin_max: float
    medians: dict[str, float]
    uncertainties_68: dict[str, list[float]]
    corner_plot: str
    seed: int
    timestamp: str
    warnings: list[str] = []

    @model_validator(mode="after")
    def converged_required(self) -> "MCMCHandoff":
        """converged must be True before reporting results."""
        if not self.converged:
            raise ValueError("converged must be True before reporting results")
        return self

    @model_validator(mode="after")
    def gelman_rubin_threshold(self) -> "MCMCHandoff":
        """gelman_rubin_max must be strictly below 1.1 (Gelman-Rubin R-hat threshold)."""
        if self.gelman_rubin_max >= 1.1:
            raise ValueError(
                f"gelman_rubin_max {self.gelman_rubin_max} >= 1.1 (chain not converged)"
            )
        return self


# ── PaperHandoff/v1 ───────────────────────────────────────────────────────────


class CompilationStatus(str, Enum):
    ok = "ok"
    errors = "errors"


class PaperHandoff(BaseModel):
    """PaperHandoff/v1 — emitted by @paper-agent after manuscript compilation.

    Returned to the user (or @pipeline-agent for logging). When
    compilation_status is 'ok', manuscript_pdf must be non-null and exist.
    todo_count == 0 is required for a clean handoff. referee_score < 5
    requires human review.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["PaperHandoff/v1"] = Field(alias="schema")
    task_id: str
    domain: Domain
    paper_dir: str
    manuscript_tex: str
    manuscript_pdf: Optional[str] = None
    bibliography_bib: str
    new_bibtex_keys: list[str] = []
    sections_written: list[str]
    n_figures: int
    n_citations: int
    compilation_status: CompilationStatus
    latex_errors: list[str] = []
    todo_count: int
    referee_report: str
    referee_score: float
    timestamp: str
    warnings: list[str] = []

    @model_validator(mode="after")
    def ok_status_requires_pdf(self) -> "PaperHandoff":
        """manuscript_pdf must be non-null when compilation_status is 'ok'."""
        if self.compilation_status == CompilationStatus.ok and self.manuscript_pdf is None:
            raise ValueError("manuscript_pdf must be non-null when compilation_status is 'ok'")
        return self


# ── RefereeHandoff/v1 ─────────────────────────────────────────────────────────


class RefereeRecommendation(str, Enum):
    accept = "accept"
    minor_revision = "minor_revision"
    major_revision = "major_revision"
    reject = "reject"


class NoveltyVerdict(str, Enum):
    novel = "novel"
    incremental = "incremental"
    duplicate = "duplicate"


class RefereeNextAction(str, Enum):
    revise = "revise"
    accept = "accept"
    reject = "reject"


class RefereeSoundness(BaseModel):
    methods_valid: bool
    results_supported: bool
    stats_appropriate: bool
    comments: list[str] = []


class RefereeNovelty(BaseModel):
    verdict: NoveltyVerdict
    score: float
    closest_prior_work: str
    prior_work_refs: list[str]


class RefereeForm(BaseModel):
    structure_ok: bool
    figures_clear: bool
    clarity: float
    comments: list[str] = []


class RefereeHandoff(BaseModel):
    """RefereeHandoff/v1 — emitted by @referee-agent after peer review.

    Consumed by @pipeline-agent (Human Gate 3) and, when next_action='revise',
    by @paper-agent in revision mode. recommendation='accept' requires
    next_action='accept' and no major_comments; recommendation='reject' requires
    next_action in {revise, reject}. novelty.prior_work_refs must be non-empty
    (novelty judgments are ADS-backed).
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["RefereeHandoff/v1"] = Field(alias="schema")
    task_id: str
    domain: Domain
    paper_ref: str
    manuscript_tex: str
    manuscript_pdf: Optional[str] = None
    revision_round: int
    recommendation: RefereeRecommendation
    overall_score: float
    soundness: RefereeSoundness
    novelty: RefereeNovelty
    form: RefereeForm
    strengths: list[str] = []
    weaknesses: list[str] = []
    major_comments: list[str] = []
    minor_comments: list[str] = []
    referee_report: str
    ads_refs_checked: list[str] = []
    next_action: RefereeNextAction
    reject_reason: Optional[str] = None
    human_gate_3_confirmed: bool
    timestamp: str
    warnings: list[str] = []

    @field_validator("novelty")
    @classmethod
    def novelty_needs_refs(cls, value: RefereeNovelty) -> RefereeNovelty:
        """novelty.prior_work_refs must contain at least one ADS bibcode."""
        if not value.prior_work_refs:
            raise ValueError("novelty.prior_work_refs must contain at least 1 ADS bibcode")
        return value

    @model_validator(mode="after")
    def revise_requires_comments(self) -> "RefereeHandoff":
        """next_action='revise' requires at least one major or minor comment."""
        if self.next_action == RefereeNextAction.revise and not (
            self.major_comments or self.minor_comments
        ):
            raise ValueError("next_action='revise' requires at least one major or minor comments")
        return self

    @model_validator(mode="after")
    def reject_requires_reason(self) -> "RefereeHandoff":
        """next_action='reject' requires a non-null reject_reason."""
        if self.next_action == RefereeNextAction.reject and self.reject_reason is None:
            raise ValueError("next_action='reject' requires a non-null reject_reason")
        return self

    @model_validator(mode="after")
    def recommendation_consistent_with_action(self) -> "RefereeHandoff":
        """accept needs a clean action; reject must never be accepted."""
        if self.recommendation == RefereeRecommendation.accept and (
            self.next_action != RefereeNextAction.accept or self.major_comments
        ):
            raise ValueError(
                "recommendation='accept' requires next_action='accept' and no major_comments"
            )
        if self.recommendation == RefereeRecommendation.reject and self.next_action not in (
            RefereeNextAction.revise,
            RefereeNextAction.reject,
        ):
            raise ValueError("recommendation='reject' requires next_action in {revise, reject}")
        return self
