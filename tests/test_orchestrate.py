"""Tests for the computed orchestration step (lib/orchestrate.py, `cli.py step`)."""
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

from lib import state as st
from lib.cli import parse_protocol_bounds
from lib.orchestrate import Evidence, decide

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "lib" / "cli.py"


def S(phase, status, retry=0, feedback=0):
    return st.make_state(current_phase=phase, phase_status=status,
                         retry_count=retry, feedback_iterations=feedback)


OK = Evidence(protocol_approved=True, postcondition_ok=True, included_count=3)
FAIL = Evidence(protocol_approved=True, postcondition_ok=False, failures=("x missing",))


# --- decide(): the transition table ---


def test_pending_dispatches_and_starts():
    d = decide(S(1, "pending"), Evidence(protocol_approved=True))
    assert d.action == "dispatch" and d.state["phase_status"] == "in_progress"
    assert [e["event"] for e in d.events] == ["phase_start"]


@pytest.mark.parametrize("phase", [1, 2, 3])
def test_clean_pass_advances_without_stopping(phase):
    d = decide(S(phase, "in_progress"), OK)
    assert d.action == "dispatch" and d.stop is None
    assert d.state["current_phase"] == phase + 1 and d.state["phase_status"] == "in_progress"
    assert d.completed_phase == phase


def test_phase1_pass_requests_screening_preprocess():
    assert decide(S(1, "in_progress"), OK).preprocess == "screening"


def test_first_failure_retries_once():
    d = decide(S(3, "in_progress"), FAIL)
    assert d.action == "dispatch" and d.retry and d.state["retry_count"] == 1
    assert d.state["current_phase"] == 3 and d.failures == ("x missing",)


def test_second_failure_is_recovery_stop():
    d = decide(S(3, "in_progress", retry=1), FAIL)
    assert d.action == "stop" and d.stop == "RECOVERY"
    assert d.state["phase_status"] == "failed"


def test_empty_corpus_after_screening_is_decision_stop():
    d = decide(S(2, "in_progress"), Evidence(protocol_approved=True, postcondition_ok=True,
                                              included_count=0))
    assert d.action == "stop" and d.stop == "DECISION"
    assert d.state["phase_status"] == "needs_protocol_revision"


def test_phase4_expanding_concepts_loops_back_to_phase3():
    ev = Evidence(protocol_approved=True, postcondition_ok=True, included_count=3,
                  conceptual_saturation=Fraction(2, 10), conceptual_threshold=Fraction(1, 10),
                  max_feedback_iterations=2)
    d = decide(S(4, "in_progress"), ev)
    assert d.action == "dispatch" and d.state["current_phase"] == 3
    assert d.state["feedback_iterations"] == 1


def test_phase4_feedback_bound_proceeds_to_synthesis():
    ev = Evidence(protocol_approved=True, postcondition_ok=True, included_count=3,
                  conceptual_saturation=Fraction(9, 10), max_feedback_iterations=2)
    d = decide(S(4, "in_progress", feedback=2), ev)
    assert d.state["current_phase"] == 5 and d.preprocess == "synthesis"


def test_phase4_saturated_proceeds_to_synthesis():
    ev = Evidence(protocol_approved=True, postcondition_ok=True, included_count=3,
                  conceptual_saturation=Fraction(1, 20))
    assert decide(S(4, "in_progress"), ev).state["current_phase"] == 5


def test_phase5_pass_is_done():
    d = decide(S(5, "in_progress"), OK)
    assert d.action == "done" and d.state["phase_status"] == "completed"


def test_interrupted_phase_with_complete_work_is_recovered():
    """#25 secondary: an in_progress phase whose postconditions pass is
    completed, not re-run."""
    d = decide(S(2, "in_progress"), OK)
    assert d.completed_phase == 2 and not d.retry


def test_unapproved_protocol_is_decision_stop():
    d = decide(S(1, "pending"), Evidence(protocol_approved=False))
    assert d.stop == "DECISION"


def test_failed_status_is_recovery_stop():
    assert decide(S(2, "failed", retry=1), OK).stop == "RECOVERY"


def test_in_progress_requires_evaluated_postconditions():
    with pytest.raises(ValueError):
        decide(S(1, "in_progress"), Evidence(protocol_approved=True))


# --- protocol bounds ---


def test_bounds_from_template_table_rows():
    text = """
| max_snowball_depth | 1 |
| discovery_saturation_threshold (θ_d) | 0.05 |
| conceptual_saturation_k (k) | 7 |
| conceptual_saturation_threshold (θ_c) | 0.15 |
| max_feedback_iterations | 3 |
"""
    b = parse_protocol_bounds(text)
    assert b["max_snowball_depth"] == 1
    assert b["discovery_saturation_threshold"] == Fraction(1, 20)
    assert b["conceptual_saturation_k"] == 7
    assert b["conceptual_saturation_threshold"] == Fraction(15, 100)
    assert b["max_feedback_iterations"] == 3


def test_bounds_from_colon_and_backtick_forms():
    b = parse_protocol_bounds("`max_snowball_depth`: 3\nmax_feedback_iterations: 1\n")
    assert b["max_snowball_depth"] == 3 and b["max_feedback_iterations"] == 1


def test_unfilled_bounds_fall_back_to_defaults():
    b = parse_protocol_bounds("| max_snowball_depth | [TODO] |\n")
    assert b["max_snowball_depth"] == 2


# --- cli.py step, run by path exactly as the skill does ---


def _run_step(ws, *extra):
    proc = subprocess.run([sys.executable, str(CLI), "step", "--workspace", str(ws), *extra],
                          capture_output=True, text=True, cwd="/")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _workspace(tmp_path, phase, status, **extra):
    ws = tmp_path / "ws"
    (ws / "data").mkdir(parents=True)
    (ws / "logs").mkdir()
    state = {"current_phase": phase, "phase_status": status, "protocol_approved": True,
             "feedback_iterations": 0, "metrics": {}, "phase_history": [], **extra}
    (ws / "state.json").write_text(json.dumps(state))
    (ws / "protocol.md").write_text("| max_snowball_depth | 1 |\n")
    return ws


def _state(ws):
    return json.loads((ws / "state.json").read_text())


def _events(ws):
    path = ws / "logs" / "phase-log.jsonl"
    return [json.loads(l)["event"] for l in path.read_text().splitlines()] if path.exists() else []


def test_cli_runs_by_path():
    proc = subprocess.run([sys.executable, str(CLI), "--help"], capture_output=True, text=True, cwd="/")
    assert proc.returncode == 0 and "step" in proc.stdout


def test_step_failure_retry_then_recovery_then_reset(tmp_path):
    ws = _workspace(tmp_path, 1, "pending")
    out = _run_step(ws)
    assert out["action"] == "dispatch" and out["phase"] == 1
    # Agent "returns" having written nothing: Phase 1 fails (no candidates).
    out = _run_step(ws)
    assert out["action"] == "dispatch" and out["retry"] and out["failures"]
    out = _run_step(ws)
    assert out["action"] == "stop" and out["stop"] == "RECOVERY"
    assert out["message"].startswith("RECOVERY:")
    assert _state(ws)["phase_status"] == "failed" and _state(ws)["failure_reason"]
    out = _run_step(ws, "--reset")
    assert out["action"] == "dispatch" and out["phase"] == 1
    assert _state(ws)["retry_count"] == 0
    assert _events(ws) == ["phase_start", "phase_retry", "phase_failed", "user_reset", "phase_start"]


def test_step_empty_screening_is_decision_stop(tmp_path):
    ws = _workspace(tmp_path, 2, "in_progress",
                    phase_history=[{"phase": 2, "started_at": "t", "completed_at": None}])
    out = _run_step(ws)
    assert out["action"] == "stop" and out["stop"] == "DECISION"
    assert out["message"].startswith("DECISION REQUIRED:")
    assert _state(ws)["phase_status"] == "needs_protocol_revision"
    assert _state(ws)["phase_history"][0]["completed_at"] is not None
