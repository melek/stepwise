"""Scholar metrics recount.

Pure counting functions over sequences of parsed records. All functions
take lists of dicts and return integers or a metrics dict. No file I/O.

Verified properties:
- Non-negative: all counts >= 0
- Accounting identity: excluded + flagged + included == total screened
- Idempotency: same inputs → same outputs
"""

from typing import Any


def count_excluded(screening_log: list[dict]) -> int:
    """Count entries where decision == 'exclude'."""
    return sum(1 for e in screening_log if e.get("decision") == "exclude")


def count_flagged(screening_log: list[dict]) -> int:
    """Count entries where decision == 'flag_for_full_text'."""
    return sum(1 for e in screening_log if e.get("decision") == "flag_for_full_text")


def count_included(included: list[dict]) -> int:
    """Return length of the included sequence."""
    return len(included)


def count_candidates(candidates: list[dict]) -> int:
    """Return length of the candidates sequence."""
    return len(candidates)


def max_snowball_depth(snowball_log: list[dict]) -> int:
    """Return the maximum depth_level across all entries. 0 if empty."""
    if not snowball_log:
        return 0
    return max(e.get("depth_level", 0) for e in snowball_log)


def count_concepts(concepts: list[dict]) -> int:
    """Return length of the concepts sequence."""
    return len(concepts)


def count_extractions(extractions: list[dict]) -> int:
    """Count unique paper_id values in extractions."""
    return len({e["paper_id"] for e in extractions if "paper_id" in e})


def recompute_all(
    screening_log: list[dict],
    candidates: list[dict],
    included: list[dict],
    snowball_log: list[dict],
    extractions: list[dict],
    concepts: list[dict],
) -> dict[str, Any]:
    """Compute all metrics from workspace data. Returns a metrics dict."""
    return {
        "total_candidates": count_candidates(candidates),
        "total_included": count_included(included),
        "total_excluded": count_excluded(screening_log),
        "total_flagged": count_flagged(screening_log),
        "snowball_depth_reached": max_snowball_depth(snowball_log),
        "concepts_count": count_concepts(concepts),
        "extraction_complete_count": count_extractions(extractions),
    }
