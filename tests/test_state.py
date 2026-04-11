"""Tests for lib/state.py — phase state machine transitions."""
import pytest

from lib.state import (
    PhaseStatus,
    make_state,
    start_phase,
    complete_phase,
    fail_phase,
    transition_to_next,
    retry_phase,
    diagnostic_transition,
    feedback_loop,
    is_review_complete,
)


# --- make_state ---

class TestMakeState:
    def test_defaults(self):
        s = make_state()
        assert s["current_phase"] == 0
        assert s["phase_status"] == "pending"
        assert s["feedback_iterations"] == 0
        assert s["retry_count"] == 0
        assert s["phase_completed"] == [False] * 6

    def test_custom_values(self):
        completed = [True, True, False, False, False, False]
        s = make_state(
            current_phase=2,
            phase_status="in_progress",
            feedback_iterations=1,
            retry_count=0,
            phase_completed=completed,
        )
        assert s["current_phase"] == 2
        assert s["phase_status"] == "in_progress"
        assert s["feedback_iterations"] == 1
        assert s["phase_completed"] == completed

    def test_phase_completed_is_copied(self):
        original = [False] * 6
        s = make_state(phase_completed=original)
        s["phase_completed"][0] = True
        assert original[0] is False

    def test_invalid_phase_too_low(self):
        with pytest.raises(ValueError, match="current_phase must be in"):
            make_state(current_phase=-1)

    def test_invalid_phase_too_high(self):
        with pytest.raises(ValueError, match="current_phase must be in"):
            make_state(current_phase=6)

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            make_state(phase_status="bogus")

    def test_negative_feedback_iterations(self):
        with pytest.raises(ValueError, match="feedback_iterations"):
            make_state(feedback_iterations=-1)

    def test_negative_retry_count(self):
        with pytest.raises(ValueError, match="retry_count"):
            make_state(retry_count=-1)

    def test_wrong_length_phase_completed(self):
        with pytest.raises(ValueError, match="exactly 6"):
            make_state(phase_completed=[False] * 5)


# --- start_phase ---

class TestStartPhase:
    def test_happy_path(self):
        s = make_state(current_phase=0, phase_status="pending")
        result = start_phase(s, 0)
        assert result["phase_status"] == PhaseStatus.IN_PROGRESS

    def test_wrong_phase_raises(self):
        s = make_state(current_phase=0, phase_status="pending")
        with pytest.raises(ValueError, match="Cannot start phase 1"):
            start_phase(s, 1)

    def test_not_pending_raises(self):
        s = make_state(current_phase=0, phase_status="in_progress")
        with pytest.raises(ValueError, match="expected pending"):
            start_phase(s, 0)


# --- complete_phase ---

class TestCompletePhase:
    def test_happy_path(self):
        s = make_state(current_phase=2, phase_status="in_progress")
        result = complete_phase(s, 2)
        assert result["phase_status"] == PhaseStatus.COMPLETED
        assert result["phase_completed"][2] is True

    def test_does_not_mutate_original(self):
        s = make_state(current_phase=0, phase_status="in_progress")
        result = complete_phase(s, 0)
        assert s["phase_completed"][0] is False
        assert result["phase_completed"][0] is True

    def test_wrong_phase_raises(self):
        s = make_state(current_phase=0, phase_status="in_progress")
        with pytest.raises(ValueError, match="Cannot complete phase 3"):
            complete_phase(s, 3)

    def test_not_in_progress_raises(self):
        s = make_state(current_phase=0, phase_status="pending")
        with pytest.raises(ValueError, match="expected in_progress"):
            complete_phase(s, 0)


# --- fail_phase ---

class TestFailPhase:
    def test_happy_path(self):
        s = make_state(current_phase=1, phase_status="in_progress")
        result = fail_phase(s, 1)
        assert result["phase_status"] == PhaseStatus.FAILED

    def test_wrong_phase_raises(self):
        s = make_state(current_phase=1, phase_status="in_progress")
        with pytest.raises(ValueError, match="Cannot fail phase 0"):
            fail_phase(s, 0)

    def test_not_in_progress_raises(self):
        s = make_state(current_phase=1, phase_status="pending")
        with pytest.raises(ValueError, match="expected in_progress"):
            fail_phase(s, 1)


# --- transition_to_next ---

class TestTransitionToNext:
    def test_happy_path(self):
        s = make_state(current_phase=0, phase_status="completed")
        result = transition_to_next(s)
        assert result["current_phase"] == 1
        assert result["phase_status"] == PhaseStatus.PENDING
        assert result["retry_count"] == 0

    def test_not_completed_raises(self):
        s = make_state(current_phase=0, phase_status="in_progress")
        with pytest.raises(ValueError, match="expected completed"):
            transition_to_next(s)

    def test_at_phase_5_raises(self):
        s = make_state(current_phase=5, phase_status="completed",
                       phase_completed=[True]*6)
        with pytest.raises(ValueError, match="already at phase 5"):
            transition_to_next(s)

    def test_resets_retry_count(self):
        s = make_state(current_phase=1, phase_status="completed", retry_count=1)
        result = transition_to_next(s)
        assert result["retry_count"] == 0


# --- retry_phase ---

class TestRetryPhase:
    def test_happy_path(self):
        s = make_state(current_phase=2, phase_status="failed", retry_count=0)
        result = retry_phase(s)
        assert result["phase_status"] == PhaseStatus.IN_PROGRESS
        assert result["retry_count"] == 1

    def test_not_failed_raises(self):
        s = make_state(current_phase=2, phase_status="in_progress")
        with pytest.raises(ValueError, match="expected failed"):
            retry_phase(s)

    def test_retry_exhausted_raises(self):
        s = make_state(current_phase=2, phase_status="failed", retry_count=1)
        with pytest.raises(ValueError, match="Retry exhausted"):
            retry_phase(s)


# --- diagnostic_transition ---

class TestDiagnosticTransition:
    def test_happy_path(self):
        s = make_state(current_phase=2, phase_status="completed")
        result = diagnostic_transition(s)
        assert result["phase_status"] == PhaseStatus.NEEDS_PROTOCOL_REVISION

    def test_wrong_phase_raises(self):
        s = make_state(current_phase=3, phase_status="completed")
        with pytest.raises(ValueError, match="only valid at phase 2"):
            diagnostic_transition(s)

    def test_not_completed_raises(self):
        s = make_state(current_phase=2, phase_status="in_progress")
        with pytest.raises(ValueError, match="expected completed"):
            diagnostic_transition(s)


# --- feedback_loop ---

class TestFeedbackLoop:
    def test_happy_path(self):
        s = make_state(current_phase=4, phase_status="completed",
                       feedback_iterations=0)
        result = feedback_loop(s, max_iterations=3)
        assert result["current_phase"] == 3
        assert result["phase_status"] == PhaseStatus.PENDING
        assert result["feedback_iterations"] == 1
        assert result["retry_count"] == 0

    def test_wrong_phase_raises(self):
        s = make_state(current_phase=3, phase_status="completed")
        with pytest.raises(ValueError, match="only valid at phase 4"):
            feedback_loop(s, max_iterations=3)

    def test_not_completed_raises(self):
        s = make_state(current_phase=4, phase_status="in_progress")
        with pytest.raises(ValueError, match="expected completed"):
            feedback_loop(s, max_iterations=3)

    def test_iterations_exhausted_raises(self):
        s = make_state(current_phase=4, phase_status="completed",
                       feedback_iterations=3)
        with pytest.raises(ValueError, match="Feedback iterations exhausted"):
            feedback_loop(s, max_iterations=3)

    def test_increments_feedback_iterations(self):
        s = make_state(current_phase=4, phase_status="completed",
                       feedback_iterations=1)
        result = feedback_loop(s, max_iterations=3)
        assert result["feedback_iterations"] == 2


# --- is_review_complete ---

class TestIsReviewComplete:
    def test_true_when_phase5_completed(self):
        s = make_state(current_phase=5, phase_status="completed",
                       phase_completed=[True]*6)
        assert is_review_complete(s) is True

    def test_false_when_not_phase5(self):
        s = make_state(current_phase=4, phase_status="completed")
        assert is_review_complete(s) is False

    def test_false_when_phase5_not_completed(self):
        s = make_state(current_phase=5, phase_status="in_progress")
        assert is_review_complete(s) is False


# --- Full lifecycle integration ---

class TestFullLifecycle:
    def test_phase_0_through_5(self):
        """Walk through phases 0-5 to verify forward progress."""
        s = make_state()
        for phase in range(6):
            s = start_phase(s, phase)
            s = complete_phase(s, phase)
            if phase < 5:
                s = transition_to_next(s)
        assert is_review_complete(s) is True

    def test_fail_and_retry(self):
        """Fail a phase, retry it, then complete."""
        s = make_state()
        s = start_phase(s, 0)
        s = fail_phase(s, 0)
        s = retry_phase(s)
        # now in_progress again
        s = complete_phase(s, 0)
        assert s["phase_status"] == PhaseStatus.COMPLETED
        assert s["retry_count"] == 1
