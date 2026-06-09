# src/validation/routing.py
from pathlib import Path
from typing import Any

from src.validation.guards import find_data_missing
from src.validation.handoff_models import (
    AnalysisHandoff,
    HypothesisHandoff,
    InterpretationHandoff,
    NextAction,
    RefereeHandoff,
    RefereeNextAction,
    SimulationHandoff,
)

DEFAULT_MAX_REVISION_ROUNDS = 3


class GateNotConfirmedError(Exception):
    pass


class DataMissingError(Exception):
    pass


def check_gate_1(handoff: HypothesisHandoff) -> None:
    """Raise GateNotConfirmedError if human Gate 1 has not been confirmed."""
    if not handoff.human_gate_1_confirmed:
        raise GateNotConfirmedError(
            "Gate 1 not confirmed: human_gate_1_confirmed must be True "
            "before @analytical-agent can consume this handoff."
        )


def check_gate_2(handoff: InterpretationHandoff) -> None:
    """Raise GateNotConfirmedError if human Gate 2 has not been confirmed."""
    if not handoff.human_gate_2_confirmed:
        raise GateNotConfirmedError(
            "Gate 2 not confirmed: human_gate_2_confirmed must be True "
            "before the pipeline can route to the next stage."
        )


def check_gate_3(handoff: RefereeHandoff) -> None:
    """Raise GateNotConfirmedError if human Gate 3 has not been confirmed."""
    if not handoff.human_gate_3_confirmed:
        raise GateNotConfirmedError(
            "Gate 3 not confirmed: human_gate_3_confirmed must be True "
            "before the pipeline can finalise or revise the manuscript."
        )


def referee_loop_decision(
    handoff: RefereeHandoff, max_revision_rounds: int = DEFAULT_MAX_REVISION_ROUNDS
) -> str:
    """Decide what follows a referee review (Gate 3 restructure).

    The paper-agent <-> referee-agent revision loop runs autonomously and
    bounded; the human (Gate 3) is consulted only once, on the converged draft,
    never inside the per-round loop.

    Parameters
    ----------
    handoff : RefereeHandoff
        The latest referee review.
    max_revision_rounds : int
        Hard cap on autonomous revision rounds before escalating to the human.

    Returns
    -------
    str
        ``'revise_autonomous'`` when the referee requested a revision and the
        round budget is not exhausted: loop back to ``@paper-agent`` WITHOUT a
        human gate. ``'human_gate_3'`` when the draft has converged (referee
        recommends accept), the referee recommends reject, or the revision
        budget is exhausted: escalate to the human for the single Gate 3
        accept/revise/reject decision.
    """
    if (
        handoff.next_action == RefereeNextAction.revise
        and handoff.revision_round < max_revision_rounds
    ):
        return "revise_autonomous"
    return "human_gate_3"


def check_no_data_missing(data: Any) -> None:
    """Raise DataMissingError if any [DATA MISSING] sentinel is found in data."""
    missing = find_data_missing(data)
    if missing:
        raise DataMissingError(f"[DATA MISSING] found at: {missing}. Resolve before proceeding.")


def check_abort_path(handoff: InterpretationHandoff, results_dir: Path) -> Path:
    """Return the expected abort_report.json path for an abort handoff."""
    if handoff.next_action != NextAction.abort:
        raise ValueError("check_abort_path called on non-abort handoff")
    return results_dir / handoff.task_id / "abort_report.json"


def check_analysis_files_exist(handoff: AnalysisHandoff) -> list[str]:
    """Return list of plot_paths that do not exist on disk."""
    return [p for p in handoff.plot_paths if not Path(p).exists()]


def check_simulation_files_readable(handoff: SimulationHandoff) -> list[str]:
    """Return list of output_files that are not readable on disk."""
    import os

    return [p for p in handoff.output_files if not os.access(p, os.R_OK)]
