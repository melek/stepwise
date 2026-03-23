"""Stepwise phase state machine.

Pure functions implementing the 6-phase state machine for systematic
literature reviews. All functions take and return plain data structures
(dicts) — no file I/O.

Verified properties:
- Forward progress: can only advance to phase N+1 from completed phase N
- No skipping: cannot complete phase N without completing N-1
- Feedback bound: feedback_iterations never exceeds max
- Retry bound: at most 1 retry per phase
- Terminal correctness: review done iff phase 5 completed
"""

from enum import Enum
from typing import Any


class PhaseStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_PROTOCOL_REVISION = "needs_protocol_revision"


def make_state(
    current_phase: int = 0,
    phase_status: str = "pending",
    feedback_iterations: int = 0,
    retry_count: int = 0,
    phase_completed: list[bool] | None = None,
) -> dict[str, Any]:
    """Create a new state record with validated fields."""
    if not 0 <= current_phase <= 5:
        raise ValueError(f"current_phase must be in [0, 5], got {current_phase}")
    PhaseStatus(phase_status)  # validates enum membership
    if feedback_iterations < 0:
        raise ValueError("feedback_iterations must be non-negative")
    if retry_count < 0:
        raise ValueError("retry_count must be non-negative")
    if phase_completed is None:
        phase_completed = [False] * 6
    if len(phase_completed) != 6:
        raise ValueError("phase_completed must have exactly 6 elements")
    return {
        "current_phase": current_phase,
        "phase_status": phase_status,
        "feedback_iterations": feedback_iterations,
        "retry_count": retry_count,
        "phase_completed": list(phase_completed),
    }


def start_phase(state: dict, phase: int) -> dict:
    """Set phase to in_progress. Requires phase == current_phase and status == pending."""
    if phase != state["current_phase"]:
        raise ValueError(
            f"Cannot start phase {phase}: current phase is {state['current_phase']}"
        )
    if state["phase_status"] != PhaseStatus.PENDING:
        raise ValueError(
            f"Cannot start phase: status is {state['phase_status']}, expected pending"
        )
    return {**state, "phase_status": PhaseStatus.IN_PROGRESS}


def complete_phase(state: dict, phase: int) -> dict:
    """Set phase to completed. Requires phase == current_phase and status == in_progress."""
    if phase != state["current_phase"]:
        raise ValueError(
            f"Cannot complete phase {phase}: current phase is {state['current_phase']}"
        )
    if state["phase_status"] != PhaseStatus.IN_PROGRESS:
        raise ValueError(
            f"Cannot complete phase: status is {state['phase_status']}, expected in_progress"
        )
    completed = list(state["phase_completed"])
    completed[phase] = True
    return {**state, "phase_status": PhaseStatus.COMPLETED, "phase_completed": completed}


def fail_phase(state: dict, phase: int) -> dict:
    """Set phase to failed. Requires phase == current_phase and status == in_progress."""
    if phase != state["current_phase"]:
        raise ValueError(
            f"Cannot fail phase {phase}: current phase is {state['current_phase']}"
        )
    if state["phase_status"] != PhaseStatus.IN_PROGRESS:
        raise ValueError(
            f"Cannot fail phase: status is {state['phase_status']}, expected in_progress"
        )
    return {**state, "phase_status": PhaseStatus.FAILED}


def transition_to_next(state: dict) -> dict:
    """Advance to next phase. Requires current phase completed and phase < 5."""
    if state["phase_status"] != PhaseStatus.COMPLETED:
        raise ValueError(
            f"Cannot transition: status is {state['phase_status']}, expected completed"
        )
    if state["current_phase"] >= 5:
        raise ValueError("Cannot transition: already at phase 5")
    return {
        **state,
        "current_phase": state["current_phase"] + 1,
        "phase_status": PhaseStatus.PENDING,
        "retry_count": 0,
    }


def diagnostic_transition(state: dict) -> dict:
    """Set needs_protocol_revision. Requires phase 2 completed (empty included corpus)."""
    if state["current_phase"] != 2:
        raise ValueError(
            f"Diagnostic transition only valid at phase 2, got {state['current_phase']}"
        )
    if state["phase_status"] != PhaseStatus.COMPLETED:
        raise ValueError(
            f"Cannot diagnose: status is {state['phase_status']}, expected completed"
        )
    return {**state, "phase_status": PhaseStatus.NEEDS_PROTOCOL_REVISION}


def feedback_loop(state: dict, max_iterations: int) -> dict:
    """Return to phase 3 for another snowball iteration. Requires phase 4 completed
    and feedback_iterations < max_iterations."""
    if state["current_phase"] != 4:
        raise ValueError(
            f"Feedback loop only valid at phase 4, got {state['current_phase']}"
        )
    if state["phase_status"] != PhaseStatus.COMPLETED:
        raise ValueError(
            f"Cannot feedback: status is {state['phase_status']}, expected completed"
        )
    if state["feedback_iterations"] >= max_iterations:
        raise ValueError(
            f"Feedback iterations exhausted: {state['feedback_iterations']} >= {max_iterations}"
        )
    return {
        **state,
        "current_phase": 3,
        "phase_status": PhaseStatus.PENDING,
        "feedback_iterations": state["feedback_iterations"] + 1,
        "retry_count": 0,
    }


def retry_phase(state: dict) -> dict:
    """Retry a failed phase. Requires status == failed and retry_count < 1."""
    if state["phase_status"] != PhaseStatus.FAILED:
        raise ValueError(
            f"Cannot retry: status is {state['phase_status']}, expected failed"
        )
    if state["retry_count"] >= 1:
        raise ValueError(
            f"Retry exhausted: retry_count is {state['retry_count']}"
        )
    return {
        **state,
        "phase_status": PhaseStatus.IN_PROGRESS,
        "retry_count": state["retry_count"] + 1,
    }


def is_review_complete(state: dict) -> bool:
    """Return True iff phase 5 is completed. Read-only — does not modify state."""
    return state["current_phase"] == 5 and state["phase_status"] == PhaseStatus.COMPLETED
