"""Stepwise orchestration — the phase transition table as a pure function.

The research skill runs `cli.py step` after each agent returns (and once to
begin). `step` reads the workspace, calls `decide`, applies the result and
tells the orchestrator what to do next: dispatch an agent, stop, or finish.
The table lives here rather than in skill prose, so the orchestrator never
has to judge whether to ask the user (#29): stops are computed, and there
are only two kinds.

Every state change is composed from the verified state machine in
`state.py`, so `decide` can only make transitions it allows.

Verified properties (lib/verified/decide.dfy):
- A clean postcondition pass never yields a stop, except the empty-corpus
  protocol fork after Phase 2.
- Every stop is DECISION (protocol fork) or RECOVERY (failure after retry).
- At most one automatic retry per phase; feedback iterations stay bounded.
"""

from dataclasses import dataclass
from fractions import Fraction

from . import state as st

PHASE_NAMES = {1: "search", 2: "screening", 3: "snowballing", 4: "extraction", 5: "synthesis"}
MAX_RETRIES = 1


@dataclass(frozen=True)
class Evidence:
    """What the workspace says about the current phase."""
    protocol_approved: bool
    postcondition_ok: bool | None = None  # evaluated only when status is in_progress
    failures: tuple[str, ...] = ()
    included_count: int = 0
    conceptual_saturation: Fraction | None = None
    conceptual_threshold: Fraction = Fraction(1, 10)
    max_feedback_iterations: int = 2


@dataclass(frozen=True)
class Decision:
    action: str                      # "dispatch" | "stop" | "done"
    state: dict                      # state-machine record to persist
    stop: str | None = None          # "DECISION" | "RECOVERY" when action == "stop"
    reason: str = ""
    events: tuple[dict, ...] = ()    # phase-log events to append, in order
    completed_phase: int | None = None
    preprocess: str | None = None    # "screening" | "synthesis", run before dispatch
    retry: bool = False
    failures: tuple[str, ...] = ()


def _stop(kind: str, state: dict, reason: str, events=(), failures=()) -> Decision:
    return Decision("stop", state, stop=kind, reason=reason, events=tuple(events),
                    failures=tuple(failures))


def _start(state: dict, events: list, completed: int | None, preprocess=None) -> Decision:
    """Start the current (pending) phase and dispatch its agent."""
    phase = state["current_phase"]
    events.append({"event": "phase_start", "phase": phase, "phase_name": PHASE_NAMES[phase]})
    return Decision("dispatch", st.start_phase(state, phase), events=tuple(events),
                    completed_phase=completed, preprocess=preprocess)


def _after_completion(state: dict, ev: Evidence, events: list, completed: int | None) -> Decision:
    """The phase is completed: apply the transition table."""
    phase = state["current_phase"]
    if phase == 5:
        return Decision("done", state, events=tuple(events), completed_phase=completed)
    if phase == 2 and ev.included_count == 0:
        events.append({"event": "phase_diagnostic", "phase": 2,
                       "reason": "No papers passed screening. Included corpus is empty."})
        return _stop("DECISION", st.diagnostic_transition(state),
                     "No papers passed screening, so the included corpus is empty. "
                     "Revise the protocol (search terms, criteria or date range) via "
                     "/stepwise:continue, or stop here.", events)
    if phase == 4:
        delta = ev.conceptual_saturation
        expanding = delta is not None and delta >= ev.conceptual_threshold
        if expanding and state["feedback_iterations"] < ev.max_feedback_iterations:
            nxt = st.feedback_loop(state, ev.max_feedback_iterations)
            events.append({"event": "saturation_check", "phase": 4, "type": "conceptual",
                           "saturation_metric": str(delta), "threshold": str(ev.conceptual_threshold),
                           "decision": "feedback_loop",
                           "feedback_iteration": nxt["feedback_iterations"]})
            return _start(nxt, events, completed)
        events.append({"event": "saturation_check", "phase": 4, "type": "conceptual",
                       "saturation_metric": None if delta is None else str(delta),
                       "threshold": str(ev.conceptual_threshold),
                       "decision": "proceed_to_synthesis"})
        return _start(st.transition_to_next(state), events, completed, preprocess="synthesis")
    preprocess = "screening" if phase == 1 else None
    return _start(st.transition_to_next(state), events, completed, preprocess=preprocess)


def decide(state: dict, ev: Evidence) -> Decision:
    """Next orchestration step for a state-machine record and its evidence."""
    phase, status = state["current_phase"], state["phase_status"]
    if phase == 0 or not ev.protocol_approved:
        return _stop("DECISION", state, "The protocol is not approved yet. Finish Phase 0 with the user.")
    if status == st.PhaseStatus.NEEDS_PROTOCOL_REVISION:
        return _stop("DECISION", state,
                     "No papers passed screening. Revise the protocol via /stepwise:continue, or stop here.")
    if status == st.PhaseStatus.FAILED:
        return _stop("RECOVERY", state,
                     f"Phase {phase} ({PHASE_NAMES[phase]}) failed after its retry. Fix the cause, "
                     f"then run `cli.py step --reset` to try again, or revise the protocol.")
    if status == st.PhaseStatus.PENDING:
        return _start(state, [], None, preprocess=None)
    if status == st.PhaseStatus.COMPLETED:
        return _after_completion(state, ev, [], None)

    # in_progress: an agent has returned (or a run was interrupted).
    if ev.postcondition_ok is None:
        raise ValueError("postconditions must be evaluated for an in_progress phase")
    if not ev.postcondition_ok:
        failed = st.fail_phase(state, phase)
        if state["retry_count"] < MAX_RETRIES:
            return Decision("dispatch", st.retry_phase(failed),
                            events=({"event": "phase_retry", "phase": phase,
                                     "phase_name": PHASE_NAMES[phase],
                                     "reason": "; ".join(ev.failures[:5])},),
                            retry=True, failures=ev.failures)
        return _stop("RECOVERY", failed,
                     f"Phase {phase} ({PHASE_NAMES[phase]}) failed its postconditions after one retry.",
                     events=[{"event": "phase_failed", "phase": phase,
                              "phase_name": PHASE_NAMES[phase],
                              "reason": "; ".join(ev.failures[:5])}],
                     failures=ev.failures)
    done = st.complete_phase(state, phase)
    events = [{"event": "phase_complete", "phase": phase, "phase_name": PHASE_NAMES[phase]}]
    return _after_completion(done, ev, events, phase)
