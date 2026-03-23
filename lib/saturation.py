"""Stepwise saturation metrics.

Pure functions computing discovery and conceptual saturation using
exact rational arithmetic (fractions.Fraction). No file I/O.

Verified properties:
- Range: both saturation values in [0, 1]
- Zero denominator: returns 0 (not division-by-zero)
- Threshold correctness: termination iff saturation < threshold
- Feedback bound: returns false when iterations >= max
"""

from fractions import Fraction


def discovery_saturation(snowball_log: list[dict], depth: int) -> Fraction:
    """Compute discovery saturation at a given depth level.

    Returns |newly_included_at_depth| / |total_examined_at_depth|.
    Returns Fraction(0) when denominator is 0.
    """
    at_depth = [e for e in snowball_log if e.get("depth_level") == depth]
    denominator = len(at_depth)
    if denominator == 0:
        return Fraction(0)
    numerator = sum(
        1
        for e in at_depth
        if e.get("screening_decision") == "include" and not e.get("already_known", False)
    )
    return Fraction(numerator, denominator)


def conceptual_saturation(
    concepts: list[dict], last_k_paper_ids: set[str]
) -> Fraction:
    """Compute conceptual saturation.

    Returns |concepts first seen in last_k_paper_ids| / |total concepts|.
    Returns Fraction(0) when there are no concepts.
    """
    total = len(concepts)
    if total == 0:
        return Fraction(0)
    new_in_last_k = sum(
        1 for c in concepts if c.get("first_seen_in") in last_k_paper_ids
    )
    return Fraction(new_in_last_k, total)


def should_terminate_discovery(
    saturation: Fraction, threshold: Fraction
) -> bool:
    """Return True if discovery saturation is below threshold (should stop)."""
    return saturation < threshold


def should_feedback_loop(
    delta: Fraction,
    theta_c: Fraction,
    iterations: int,
    max_iterations: int,
) -> bool:
    """Return True if conceptual saturation warrants another feedback loop.

    Returns True iff delta >= theta_c AND iterations < max_iterations.
    """
    return delta >= theta_c and iterations < max_iterations
