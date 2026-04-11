"""Tests for lib/saturation.py — saturation metrics with exact rational arithmetic."""
import pytest
from fractions import Fraction

from lib.saturation import (
    discovery_saturation,
    conceptual_saturation,
    should_terminate_discovery,
    should_feedback_loop,
)


# --- discovery_saturation ---

class TestDiscoverySaturation:
    def test_basic_computation(self):
        log = [
            {"depth_level": 1, "screening_decision": "include", "already_known": False},
            {"depth_level": 1, "screening_decision": "exclude"},
            {"depth_level": 1, "screening_decision": "include", "already_known": False},
            {"depth_level": 1, "screening_decision": "include", "already_known": True},
        ]
        # 2 newly included out of 4 examined at depth 1
        assert discovery_saturation(log, 1) == Fraction(2, 4)

    def test_empty_log(self):
        assert discovery_saturation([], 1) == Fraction(0)

    def test_no_entries_at_depth(self):
        log = [{"depth_level": 2, "screening_decision": "include", "already_known": False}]
        assert discovery_saturation(log, 1) == Fraction(0)

    def test_all_already_known(self):
        log = [
            {"depth_level": 1, "screening_decision": "include", "already_known": True},
            {"depth_level": 1, "screening_decision": "include", "already_known": True},
        ]
        assert discovery_saturation(log, 1) == Fraction(0, 2)

    def test_all_new_includes(self):
        log = [
            {"depth_level": 1, "screening_decision": "include", "already_known": False},
            {"depth_level": 1, "screening_decision": "include", "already_known": False},
        ]
        assert discovery_saturation(log, 1) == Fraction(1)

    def test_filters_by_depth(self):
        log = [
            {"depth_level": 1, "screening_decision": "include", "already_known": False},
            {"depth_level": 2, "screening_decision": "include", "already_known": False},
            {"depth_level": 2, "screening_decision": "exclude"},
        ]
        assert discovery_saturation(log, 2) == Fraction(1, 2)

    def test_returns_fraction_type(self):
        log = [{"depth_level": 1, "screening_decision": "exclude"}]
        result = discovery_saturation(log, 1)
        assert isinstance(result, Fraction)


# --- conceptual_saturation ---

class TestConceptualSaturation:
    def test_basic_computation(self):
        concepts = [
            {"concept_id": "c1", "first_seen_in": "p1"},
            {"concept_id": "c2", "first_seen_in": "p2"},
            {"concept_id": "c3", "first_seen_in": "p1"},
            {"concept_id": "c4", "first_seen_in": "p3"},
        ]
        last_k = {"p2", "p3"}
        # c2 and c4 first seen in last_k → 2/4
        assert conceptual_saturation(concepts, last_k) == Fraction(2, 4)

    def test_empty_concepts(self):
        assert conceptual_saturation([], {"p1"}) == Fraction(0)

    def test_no_overlap(self):
        concepts = [
            {"concept_id": "c1", "first_seen_in": "p1"},
            {"concept_id": "c2", "first_seen_in": "p2"},
        ]
        assert conceptual_saturation(concepts, {"p99"}) == Fraction(0, 2)

    def test_all_in_last_k(self):
        concepts = [
            {"concept_id": "c1", "first_seen_in": "p1"},
            {"concept_id": "c2", "first_seen_in": "p1"},
        ]
        assert conceptual_saturation(concepts, {"p1"}) == Fraction(1)

    def test_returns_fraction_type(self):
        concepts = [{"concept_id": "c1", "first_seen_in": "p1"}]
        result = conceptual_saturation(concepts, set())
        assert isinstance(result, Fraction)


# --- should_terminate_discovery ---

class TestShouldTerminateDiscovery:
    def test_below_threshold_terminates(self):
        assert should_terminate_discovery(Fraction(1, 10), Fraction(2, 10)) is True

    def test_above_threshold_continues(self):
        assert should_terminate_discovery(Fraction(3, 10), Fraction(2, 10)) is False

    def test_equal_to_threshold_does_not_terminate(self):
        """At exactly the threshold, saturation is NOT < threshold, so returns False."""
        assert should_terminate_discovery(Fraction(2, 10), Fraction(2, 10)) is False

    def test_zero_saturation(self):
        assert should_terminate_discovery(Fraction(0), Fraction(1, 10)) is True

    def test_zero_threshold(self):
        """Zero saturation is not < zero threshold."""
        assert should_terminate_discovery(Fraction(0), Fraction(0)) is False


# --- should_feedback_loop ---

class TestShouldFeedbackLoop:
    def test_delta_above_and_iterations_available(self):
        assert should_feedback_loop(
            delta=Fraction(3, 10),
            theta_c=Fraction(2, 10),
            iterations=0,
            max_iterations=3,
        ) is True

    def test_delta_equal_to_theta(self):
        """delta >= theta_c means equal should return True."""
        assert should_feedback_loop(
            delta=Fraction(2, 10),
            theta_c=Fraction(2, 10),
            iterations=0,
            max_iterations=3,
        ) is True

    def test_delta_below_theta(self):
        assert should_feedback_loop(
            delta=Fraction(1, 10),
            theta_c=Fraction(2, 10),
            iterations=0,
            max_iterations=3,
        ) is False

    def test_iterations_exhausted(self):
        assert should_feedback_loop(
            delta=Fraction(5, 10),
            theta_c=Fraction(2, 10),
            iterations=3,
            max_iterations=3,
        ) is False

    def test_iterations_at_max_minus_one(self):
        assert should_feedback_loop(
            delta=Fraction(5, 10),
            theta_c=Fraction(2, 10),
            iterations=2,
            max_iterations=3,
        ) is True

    def test_zero_max_iterations(self):
        """With max_iterations=0, feedback should never happen."""
        assert should_feedback_loop(
            delta=Fraction(1),
            theta_c=Fraction(0),
            iterations=0,
            max_iterations=0,
        ) is False
