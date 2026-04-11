"""Tests for synthesis claim validation — extraction completeness propagation.

Exercises validate_synthesis_claims from lib/postconditions.py, focusing on
the requirement that citations to low-completeness papers include a
[limited data] qualification marker.
"""
import pytest

from lib.postconditions import validate_synthesis_claims


class TestLowCompletenessQualification:
    """Paragraphs citing papers with low extraction completeness must include
    a [limited data] marker."""

    def test_missing_marker_fails(self):
        """Citation to a low-completeness paper WITHOUT [limited data] should fail."""
        paragraphs = [
            {
                "section": "Results",
                "text": "The approach showed promising outcomes [@smith2023].",
            }
        ]
        included_keys = {"smith2023"}
        extraction_completeness = {"smith2023": 0.3}  # below default 0.5

        satisfied, failures = validate_synthesis_claims(
            paragraphs, included_keys, extraction_completeness
        )
        assert satisfied is False
        assert len(failures) == 1
        assert "smith2023" in failures[0]
        assert "low data completeness" in failures[0]

    def test_with_marker_passes(self):
        """Citation to a low-completeness paper WITH [limited data] should pass."""
        paragraphs = [
            {
                "section": "Results",
                "text": (
                    "The approach showed promising outcomes [@smith2023] "
                    "[limited data]."
                ),
            }
        ]
        included_keys = {"smith2023"}
        extraction_completeness = {"smith2023": 0.3}

        satisfied, failures = validate_synthesis_claims(
            paragraphs, included_keys, extraction_completeness
        )
        assert satisfied is True
        assert failures == []

    def test_high_completeness_needs_no_marker(self):
        """Papers above the completeness threshold need no marker."""
        paragraphs = [
            {
                "section": "Discussion",
                "text": "Results align with prior work [@jones2024].",
            }
        ]
        included_keys = {"jones2024"}
        extraction_completeness = {"jones2024": 0.8}

        satisfied, failures = validate_synthesis_claims(
            paragraphs, included_keys, extraction_completeness
        )
        assert satisfied is True
        assert failures == []

    def test_limited_alias_also_accepted(self):
        """The source also accepts [limited] as an alternative marker."""
        paragraphs = [
            {
                "section": "Results",
                "text": "Preliminary findings [@low2023] [limited] suggest caution.",
            }
        ]
        included_keys = {"low2023"}
        extraction_completeness = {"low2023": 0.2}

        satisfied, failures = validate_synthesis_claims(
            paragraphs, included_keys, extraction_completeness
        )
        assert satisfied is True
        assert failures == []
