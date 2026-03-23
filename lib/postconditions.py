"""Scholar postcondition checks.

Pure validation functions for all 5 review phases. Each check takes parsed
data structures and returns (satisfied: bool, failures: list[str]).
No file I/O.

Verified properties:
- Soundness: satisfied == True implies all conditions hold
- Completeness: any failing condition yields satisfied == False with non-empty failures
- Determinism: same inputs → same output
"""

import re
from fractions import Fraction


# --- Result helper ---

def _result(failures: list[str]) -> tuple[bool, list[str]]:
    return (len(failures) == 0, failures)


# --- Per-record validators (used by oracle contracts) ---

_CRITERION_ID_PATTERN = re.compile(r"^[IE]C\d+$")

def validate_screening_criterion(record: dict) -> tuple[bool, list[str]]:
    """Validate a single criterion evaluation record."""
    failures = []
    if record.get("met") not in ("yes", "no", "unclear"):
        failures.append(f"met: {record.get('met')!r} not in {{yes, no, unclear}}")
    if not record.get("evidence"):
        failures.append("evidence: empty or missing")
    if record.get("source") not in ("abstract", "full_text"):
        failures.append(f"source: {record.get('source')!r} not in {{abstract, full_text}}")
    cid = record.get("criterion_id", "")
    if not _CRITERION_ID_PATTERN.match(cid):
        failures.append(f"criterion_id: {cid!r} does not match [IE]C\\d+")
    if record.get("criterion_type") not in ("inclusion", "exclusion"):
        failures.append(f"criterion_type: {record.get('criterion_type')!r} not in {{inclusion, exclusion}}")
    return _result(failures)


def validate_screening_decision(record: dict) -> tuple[bool, list[str]]:
    """Validate a complete screening decision record (biconditional rules).

    Composes over validate_screening_criterion for each evaluation.
    """
    failures = []
    decision = record.get("decision")
    if decision not in ("include", "exclude", "flag_for_full_text"):
        failures.append(f"decision: {decision!r} not in {{include, exclude, flag_for_full_text}}")
        return _result(failures)

    evals = record.get("criteria_evaluations", [])
    if not evals:
        failures.append("criteria_evaluations: empty or missing")
    if not record.get("reasoning"):
        failures.append("reasoning: empty or missing")
    if failures:
        return _result(failures)

    # Validate each constituent criterion record (composition)
    for i, ev in enumerate(evals):
        ok, ev_failures = validate_screening_criterion(ev)
        for ef in ev_failures:
            failures.append(f"criteria_evaluations[{i}]: {ef}")
    if failures:
        return _result(failures)

    ic_mets = [e["met"] for e in evals if e.get("criterion_type") == "inclusion"]
    ec_mets = [e["met"] for e in evals if e.get("criterion_type") == "exclusion"]
    all_ic_yes = all(m == "yes" for m in ic_mets)
    any_ec_yes = any(m == "yes" for m in ec_mets)
    any_ic_no = any(m == "no" for m in ic_mets)
    any_unclear = any(e["met"] == "unclear" for e in evals)

    if decision == "include":
        if not all_ic_yes:
            failures.append("Decision rule violation: include but not all IC met=yes")
        if any_ec_yes:
            failures.append("Decision rule violation: include but EC met=yes")
    elif decision == "exclude":
        if not (any_ec_yes or any_ic_no):
            failures.append("Decision rule violation: exclude but all IC met and no EC met")
    elif decision == "flag_for_full_text":
        if not any_unclear:
            failures.append("Decision rule violation: flag_for_full_text but no criterion unclear")
        if any_ec_yes:
            failures.append("Decision rule violation: flag_for_full_text but EC met=yes")

    return _result(failures)


# ============================================================
# Phase 1 — Search
# ============================================================

def check_all_queries_executed(
    protocol_queries: list[dict], search_log: list[dict]
) -> tuple[bool, list[str]]:
    """Every (database, query) pair in protocol has a matching search_log entry."""
    log_pairs = {(e["database"], e["query"]) for e in search_log}
    failures = []
    for pq in protocol_queries:
        key = (pq["database"], pq["query"])
        if key not in log_pairs:
            failures.append(f"Query not executed: {key[0]} / {key[1]}")
    return _result(failures)


def check_candidates_non_empty(candidates: list[dict]) -> tuple[bool, list[str]]:
    if not candidates:
        return (False, ["candidates.jsonl is empty"])
    return (True, [])


def check_no_duplicate_ids(candidates: list[dict]) -> tuple[bool, list[str]]:
    seen: dict[str, int] = {}
    duplicates = []
    for c in candidates:
        cid = c["id"]
        if cid in seen:
            duplicates.append(cid)
        seen[cid] = seen.get(cid, 0) + 1
    if duplicates:
        return (False, [f"Duplicate candidate IDs: {', '.join(set(duplicates))}"])
    return (True, [])


def check_minimum_metadata(candidates: list[dict]) -> tuple[bool, list[str]]:
    required = ["id", "title", "abstract", "authors", "year"]
    failures = []
    for c in candidates:
        missing = [f for f in required if not c.get(f)]
        if "authors" in [f for f in required if f not in missing]:
            if not c.get("authors"):
                missing.append("authors")
        if missing:
            failures.append(f"Candidate {c.get('id', '?')} missing: {', '.join(missing)}")
    return _result(failures)


def check_phase1_all(
    protocol_queries: list[dict],
    search_log: list[dict],
    candidates: list[dict],
) -> tuple[bool, list[str]]:
    all_failures = []
    for check_fn, args in [
        (check_all_queries_executed, (protocol_queries, search_log)),
        (check_candidates_non_empty, (candidates,)),
        (check_no_duplicate_ids, (candidates,)),
        (check_minimum_metadata, (candidates,)),
    ]:
        _, failures = check_fn(*args)
        all_failures.extend(failures)
    return _result(all_failures)


# ============================================================
# Phase 2 — Screening
# ============================================================

def check_all_candidates_screened(
    candidates: list[dict], screening_log: list[dict]
) -> tuple[bool, list[str]]:
    """Every candidate has a final include/exclude decision in screening_log."""
    final_decisions: set[str] = set()
    for entry in screening_log:
        if entry.get("decision") in ("include", "exclude"):
            final_decisions.add(entry["paper_id"])
    failures = []
    for c in candidates:
        if c["id"] not in final_decisions:
            failures.append(f"Candidate {c['id']} has no final screening decision")
    return _result(failures)


def check_included_consistency(
    included: list[dict], screening_log: list[dict]
) -> tuple[bool, list[str]]:
    """Every included paper has a screening entry with decision == include."""
    include_decisions = {
        e["paper_id"] for e in screening_log if e.get("decision") == "include"
    }
    failures = []
    for p in included:
        if p["id"] not in include_decisions:
            failures.append(f"Included paper {p['id']} has no 'include' screening decision")
    return _result(failures)


def check_no_orphan_inclusions(
    included: list[dict], candidates: list[dict]
) -> tuple[bool, list[str]]:
    """Every included paper exists in candidates."""
    candidate_ids = {c["id"] for c in candidates}
    failures = []
    for p in included:
        if p["id"] not in candidate_ids:
            failures.append(f"Included paper {p['id']} not found in candidates")
    return _result(failures)


def check_phase2_all(
    candidates: list[dict],
    screening_log: list[dict],
    included: list[dict],
) -> tuple[bool, list[str]]:
    all_failures = []
    for check_fn, args in [
        (check_all_candidates_screened, (candidates, screening_log)),
        (check_included_consistency, (included, screening_log)),
        (check_no_orphan_inclusions, (included, candidates)),
    ]:
        _, failures = check_fn(*args)
        all_failures.extend(failures)
    return _result(all_failures)


# ============================================================
# Phase 3 — Snowballing
# ============================================================

def check_termination_condition(
    snowball_log: list[dict],
    phase_log: list[dict],
    max_depth: int,
    threshold: Fraction,
) -> tuple[bool, list[str]]:
    """Termination: saturation < threshold OR max depth reached."""
    # Check max depth
    depths = [e.get("depth_level", 0) for e in snowball_log]
    max_depth_reached = max(depths) if depths else 0

    if max_depth_reached >= max_depth:
        return (True, [])

    # Check saturation from phase_log
    sat_events = [
        e for e in phase_log
        if e.get("event") == "saturation_check" and e.get("phase") == 3
    ]
    if sat_events:
        last = sat_events[-1]
        metric = last.get("saturation_metric")
        if metric is not None and Fraction(metric) < threshold:
            return (True, [])

    return (False, [
        f"Termination condition not met: max_depth_reached={max_depth_reached} "
        f"(max={max_depth}), no saturation event below threshold"
    ])


def check_all_seeds_examined(
    seed_papers: list[dict], snowball_log: list[dict]
) -> tuple[bool, list[str]]:
    """Every seed paper has forward and backward snowball entries."""
    forward_sources = {
        e["source_paper_id"] for e in snowball_log if e.get("direction") == "forward"
    }
    backward_sources = {
        e["source_paper_id"] for e in snowball_log if e.get("direction") == "backward"
    }
    failures = []
    for p in seed_papers:
        pid = p["id"]
        missing = []
        if pid not in forward_sources:
            missing.append("forward")
        if pid not in backward_sources:
            missing.append("backward")
        if missing:
            failures.append(f"Seed {pid} missing {', '.join(missing)} snowball entries")
    return _result(failures)


def check_truncation_logged(snowball_log: list[dict]) -> tuple[bool, list[str]]:
    """Truncated entries have non-null citation counts."""
    failures = []
    for e in snowball_log:
        if e.get("truncated"):
            if e.get("total_citations_available") is None or e.get("citations_retrieved") is None:
                failures.append(
                    f"Truncated entry for {e.get('source_paper_id')} "
                    f"missing citation counts"
                )
    return _result(failures)


def check_new_inclusions_recorded(
    snowball_log: list[dict],
    included: list[dict],
    candidates: list[dict],
) -> tuple[bool, list[str]]:
    """Every snowball include is in both included and candidates."""
    included_ids = {p["id"] for p in included}
    candidate_ids = {c["id"] for c in candidates}
    failures = []
    for e in snowball_log:
        if e.get("screening_decision") == "include":
            pid = e["discovered_paper_id"]
            if pid not in included_ids:
                failures.append(f"Snowball include {pid} not in included.jsonl")
            if pid not in candidate_ids:
                failures.append(f"Snowball include {pid} not in candidates.jsonl")
    return _result(failures)


def check_phase3_all(
    seed_papers: list[dict],
    snowball_log: list[dict],
    phase_log: list[dict],
    included: list[dict],
    candidates: list[dict],
    max_depth: int,
    threshold: Fraction,
) -> tuple[bool, list[str]]:
    all_failures = []
    for check_fn, args in [
        (check_termination_condition, (snowball_log, phase_log, max_depth, threshold)),
        (check_all_seeds_examined, (seed_papers, snowball_log)),
        (check_truncation_logged, (snowball_log,)),
        (check_new_inclusions_recorded, (snowball_log, included, candidates)),
    ]:
        _, failures = check_fn(*args)
        all_failures.extend(failures)
    return _result(all_failures)


# ============================================================
# Phase 4 — Extraction
# ============================================================

def check_all_papers_extracted(
    included: list[dict], extractions: list[dict]
) -> tuple[bool, list[str]]:
    extracted_ids = {e["paper_id"] for e in extractions}
    failures = []
    for p in included:
        if p["id"] not in extracted_ids:
            failures.append(f"Paper {p['id']} not extracted")
    return _result(failures)


def check_extraction_schema_valid(
    extractions: list[dict],
) -> tuple[bool, list[str]]:
    """Every extraction has source field and valid field entries."""
    valid_sources = {"full_text", "abstract"}
    valid_confidence = {"high", "medium", "low"}
    failures = []
    for ext in extractions:
        pid = ext.get("paper_id", "?")
        if ext.get("source") not in valid_sources:
            failures.append(f"Extraction {pid}: invalid or missing source field")
        for field in ext.get("fields", []):
            for key in ("field_name", "value", "source_location", "confidence"):
                if field.get(key) is None:
                    failures.append(f"Extraction {pid}: field entry missing '{key}'")
            if field.get("confidence") not in valid_confidence:
                failures.append(
                    f"Extraction {pid}: invalid confidence '{field.get('confidence')}'"
                )
    return _result(failures)


def check_concepts_non_empty(concepts: list[dict]) -> tuple[bool, list[str]]:
    if not concepts:
        return (False, ["concepts.jsonl is empty"])
    return (True, [])


def check_concept_matrix_exists(exists: bool) -> tuple[bool, list[str]]:
    if not exists:
        return (False, ["concept-matrix.md does not exist or is empty"])
    return (True, [])


def check_all_concepts_defined(
    extractions: list[dict], concepts: list[dict]
) -> tuple[bool, list[str]]:
    """Every concept_id referenced in extractions exists in concepts with a definition."""
    concept_map = {
        c["concept_id"]: c.get("definition", "")
        for c in concepts
    }
    failures = []
    for ext in extractions:
        for cid in ext.get("concepts_identified", []):
            if cid not in concept_map:
                failures.append(f"Concept {cid} referenced but not defined")
            elif not concept_map[cid]:
                failures.append(f"Concept {cid} has empty definition")
    return _result(failures)


def check_saturation_computed(phase_log: list[dict]) -> tuple[bool, list[str]]:
    for entry in phase_log:
        if (
            entry.get("event") == "saturation_check"
            and entry.get("phase") == 4
            and entry.get("saturation_metric") is not None
        ):
            return (True, [])
    return (False, ["No saturation_check event found for phase 4"])


def check_phase4_all(
    included: list[dict],
    extractions: list[dict],
    concepts: list[dict],
    concept_matrix_exists: bool,
    phase_log: list[dict],
) -> tuple[bool, list[str]]:
    all_failures = []
    for check_fn, args in [
        (check_all_papers_extracted, (included, extractions)),
        (check_extraction_schema_valid, (extractions,)),
        (check_concepts_non_empty, (concepts,)),
        (check_concept_matrix_exists, (concept_matrix_exists,)),
        (check_all_concepts_defined, (extractions, concepts)),
        (check_saturation_computed, (phase_log,)),
    ]:
        _, failures = check_fn(*args)
        all_failures.extend(failures)
    return _result(all_failures)


# ============================================================
# Phase 5 — Synthesis
# ============================================================

def check_all_papers_in_appendix(
    included: list[dict], appendix_keys: set[str]
) -> tuple[bool, list[str]]:
    """Every included paper's id or bibtex_key appears in Appendix A."""
    failures = []
    for p in included:
        pid = p["id"]
        bkey = p.get("bibtex_key", "")
        if pid not in appendix_keys and bkey not in appendix_keys:
            failures.append(f"Paper {pid} missing from Appendix A")
    return _result(failures)


def check_all_questions_addressed(
    protocol_questions: list[str], question_answers: list[dict]
) -> tuple[bool, list[str]]:
    valid_dispositions = {"answered", "partially_answered", "identified_as_gap"}
    answered_questions = {
        qa["question"]
        for qa in question_answers
        if qa.get("disposition") in valid_dispositions
    }
    failures = []
    for q in protocol_questions:
        if q not in answered_questions:
            failures.append(f"Question not addressed: {q[:80]}...")
    return _result(failures)


def check_question_answers_complete(
    protocol_questions: list[str], question_answers: list[dict]
) -> tuple[bool, list[str]]:
    qa_questions = {qa["question"] for qa in question_answers}
    failures = []
    for q in protocol_questions:
        if q not in qa_questions:
            failures.append(f"Missing question-answer entry: {q[:80]}...")
    return _result(failures)


def check_bibliography_consistent(
    bib_entry_count: int, review_citation_keys: set[str]
) -> tuple[bool, list[str]]:
    cite_count = len(review_citation_keys)
    if bib_entry_count != cite_count:
        return (False, [
            f"Bibliography has {bib_entry_count} entries but review has {cite_count} citation keys"
        ])
    return (True, [])


REQUIRED_HEADERS = {
    "Abstract", "Introduction", "Methodology", "Results",
    "Discussion", "Conclusion", "References", "Appendix A", "Appendix B",
}


def check_review_structure(
    review_section_headers: set[str],
) -> tuple[bool, list[str]]:
    missing = REQUIRED_HEADERS - review_section_headers
    if missing:
        return (False, [f"Missing section headers: {', '.join(sorted(missing))}"])
    return (True, [])


def check_appendix_row_count(
    appendix_a_row_count: int, included_count: int
) -> tuple[bool, list[str]]:
    if appendix_a_row_count != included_count:
        return (False, [
            f"Appendix A has {appendix_a_row_count} rows but included.jsonl has {included_count} records"
        ])
    return (True, [])


def check_phase5_all(
    included: list[dict],
    review_citation_keys: set[str],
    review_section_headers: set[str],
    protocol_questions: list[str],
    question_answers: list[dict],
    bib_entry_count: int,
    appendix_a_row_count: int,
    included_count: int,
    appendix_keys: set[str] | None = None,
) -> tuple[bool, list[str]]:
    all_failures = []
    if appendix_keys is None:
        appendix_keys = set()
    for check_fn, args in [
        (check_all_papers_in_appendix, (included, appendix_keys)),
        (check_all_questions_addressed, (protocol_questions, question_answers)),
        (check_question_answers_complete, (protocol_questions, question_answers)),
        (check_bibliography_consistent, (bib_entry_count, review_citation_keys)),
        (check_review_structure, (review_section_headers,)),
        (check_appendix_row_count, (appendix_a_row_count, included_count)),
    ]:
        _, failures = check_fn(*args)
        all_failures.extend(failures)
    return _result(all_failures)
