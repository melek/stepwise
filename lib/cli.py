#!/usr/bin/env python3
"""Stepwise CLI — thin I/O wrapper over verified pure functions.

This module handles JSONL parsing and filesystem access, then delegates
to the pure functions in state.py, metrics.py, saturation.py, and
postconditions.py. All output is JSON to stdout.

Usage:
    python3 cli.py metrics --workspace ~/research/my-project/
    python3 cli.py postcondition --phase 2 --workspace ~/research/my-project/
    python3 cli.py transition --action next --workspace ~/research/my-project/
    python3 cli.py transition --action feedback --max-iterations 2 --workspace ~/research/my-project/
    python3 cli.py transition --action diagnostic --workspace ~/research/my-project/
    python3 cli.py saturation --type discovery --depth 2 --workspace ~/research/my-project/
    python3 cli.py saturation --type conceptual --k 5 --workspace ~/research/my-project/
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

# The skills run this file by path (`python3 {PLUGIN_DIR}/lib/cli.py ...`),
# which leaves no package context for the relative imports below. Make the
# plugin root importable and adopt the `lib` package so both that form and
# `python3 -m lib.cli` work.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import lib  # noqa: E402,F401
    __package__ = "lib"

from . import export as exp
from . import metrics as m
from . import oracle_contracts as oc
from . import postconditions as pc
from . import preprocess as prep
from . import prisma as pr
from . import saturation as sat
from . import section_parser as sp
from . import state as st
from . import orchestrate as orch


# --- JSONL I/O helpers ---

def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, returning a list of dicts. Empty list if file missing."""
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def read_json(path: Path) -> dict:
    """Read a JSON file."""
    with open(path) as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    """Write a JSON file with pretty formatting."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Workspace data loaders ---

def load_workspace_data(workspace: Path) -> dict:
    """Load all workspace data files into a dict of lists."""
    return {
        "candidates": read_jsonl(workspace / "data" / "candidates.jsonl"),
        "included": read_jsonl(workspace / "data" / "included.jsonl"),
        "screening_log": read_jsonl(workspace / "logs" / "screening-log.jsonl"),
        "snowball_log": read_jsonl(workspace / "logs" / "snowball-log.jsonl"),
        "extractions": read_jsonl(workspace / "data" / "extractions.jsonl"),
        "concepts": read_jsonl(workspace / "data" / "concepts.jsonl"),
        "search_log": read_jsonl(workspace / "logs" / "search-log.jsonl"),
        "phase_log": read_jsonl(workspace / "logs" / "phase-log.jsonl"),
        "question_answers": read_jsonl(workspace / "data" / "question-answers.jsonl"),
    }


def parse_review_citations(workspace: Path) -> set[str]:
    """Extract [@key] citation keys from review.md, excluding backtick-escaped ones."""
    review_path = workspace / "review.md"
    if not review_path.exists():
        return set()
    text = review_path.read_text()
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Find citation keys, splitting multi-citations like [@key1; @key2]
    raw_matches = re.findall(r"\[@([^\]]+)\]", text)
    keys: set[str] = set()
    for match in raw_matches:
        for part in re.split(r";\s*@?", match):
            part = part.strip()
            if part:
                keys.add(part)
    return keys


def parse_review_headers(workspace: Path) -> set[str]:
    """Extract section headers from review.md."""
    review_path = workspace / "review.md"
    if not review_path.exists():
        return set()
    headers = set()
    for line in review_path.read_text().splitlines():
        match = re.match(r"^#{1,3}\s+(?:\d+\.?\s*)?(.+)", line)
        if match:
            header = match.group(1).strip()
            # Normalize: remove numbering like "3.2"
            header = re.sub(r"^\d+(\.\d+)*\.?\s*", "", header).strip()
            headers.add(header)
    return headers


def count_appendix_a_rows(workspace: Path) -> int:
    """Count data rows in Appendix A table of review.md."""
    review_path = workspace / "review.md"
    if not review_path.exists():
        return 0
    text = review_path.read_text()
    # Find Appendix A section
    match = re.search(r"(?:^|\n)#{1,3}\s+(?:Appendix A[:\s].*|Appendix A)\s*\n", text)
    if not match:
        return 0
    section_start = match.end()
    # Find next section header or end of file
    next_section = re.search(r"\n#{1,3}\s+", text[section_start:])
    section_end = section_start + next_section.start() if next_section else len(text)
    section_text = text[section_start:section_end]
    # Count table rows (lines starting with |, excluding header and separator)
    table_lines = [
        line for line in section_text.splitlines()
        if line.strip().startswith("|") and not re.match(r"^\s*\|[\s\-:|]+\|\s*$", line)
    ]
    # First table line is the header
    return max(0, len(table_lines) - 1)


def parse_appendix_keys(workspace: Path) -> set[str]:
    """Extract BibTeX keys from Appendix A table rows."""
    review_path = workspace / "review.md"
    if not review_path.exists():
        return set()
    text = review_path.read_text()
    match = re.search(r"(?:^|\n)#{1,3}\s+(?:Appendix A[:\s].*|Appendix A)\s*\n", text)
    if not match:
        return set()
    section_start = match.end()
    next_section = re.search(r"\n#{1,3}\s+", text[section_start:])
    section_end = section_start + next_section.start() if next_section else len(text)
    section_text = text[section_start:section_end]
    keys = set()
    for line in section_text.splitlines():
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", line):
            # Extract first cell content as key
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if cells and cells[0] not in ("Key", "ID"):
                keys.add(cells[0])
    return keys


def parse_protocol_questions(workspace: Path) -> list[str]:
    """Extract research sub-questions from protocol.md."""
    protocol_path = workspace / "protocol.md"
    if not protocol_path.exists():
        return []
    text = protocol_path.read_text()
    questions = []
    # Look for numbered sub-questions in the protocol
    for match in re.finditer(r"^\s*\d+\.\s+(.+)$", text, re.MULTILINE):
        q = match.group(1).strip()
        if "?" in q:
            questions.append(q)
    return questions


def parse_protocol_queries(workspace: Path) -> list[dict]:
    """Extract (database, query) pairs from protocol.md Search Terms table.

    Scoped to the ### Search Terms section only.  Normalizes database names
    to snake_case and strips backtick formatting and trailing category
    annotations from query text.
    """
    protocol_path = workspace / "protocol.md"
    if not protocol_path.exists():
        return []
    text = protocol_path.read_text()

    # Scope to Search Terms section (same pattern as count_appendix_a_rows)
    section_match = re.search(
        r"(?:^|\n)###\s+Search Terms\s*\n", text
    )
    if not section_match:
        return []
    section_start = section_match.end()
    next_section = re.search(r"\n#{1,3}\s+", text[section_start:])
    section_end = section_start + next_section.start() if next_section else len(text)
    section_text = text[section_start:section_end]

    queries = []
    for match in re.finditer(r"\|\s*(\w[\w\s]*?)\s*\|\s*(.+?)\s*\|", section_text):
        db = match.group(1).strip()
        query = match.group(2).strip()
        if db.lower() in ("database", "---", ""):
            continue
        # Strip backticks and trailing category annotations like (cs.SE, cs.FL)
        query = re.sub(r"^`|`$", "", query)
        query = re.sub(r"`\s*\([^)]*\)\s*$", "", query).strip()
        # Normalize database name
        db = _normalize_database(db)
        queries.append({"database": db, "query": query})
    return queries


_DB_CANONICAL = {
    "semantic scholar": "semantic_scholar",
    "arxiv": "arxiv",
    "pubmed": "pubmed",
    "paper-search-mcp": "paper_search_mcp",
}


BOUND_DEFAULTS = {
    "max_snowball_depth": 2,
    "discovery_saturation_threshold": Fraction(5, 100),
    "conceptual_saturation_k": 5,
    "conceptual_saturation_threshold": Fraction(1, 10),
    "max_feedback_iterations": 2,
}


def parse_protocol_bounds(text: str) -> dict:
    """Read the phase bounds from protocol.md text.

    The template stores them as table rows such as
    `| discovery_saturation_threshold (θ_d) | 0.05 |`; `name: value` and
    backticked forms are accepted too. Missing or unfilled values fall back
    to BOUND_DEFAULTS, the defaults the research skill documents.
    """
    bounds = dict(BOUND_DEFAULTS)
    for name, default in BOUND_DEFAULTS.items():
        match = re.search(rf"{name}\b[^|\n:]*[|:]\s*`?([0-9]+(?:\.[0-9]+)?)", text)
        if match:
            raw = match.group(1)
            bounds[name] = int(float(raw)) if isinstance(default, int) else Fraction(raw)
    return bounds


def read_protocol_bounds(workspace: Path) -> dict:
    path = workspace / "protocol.md"
    return parse_protocol_bounds(path.read_text()) if path.exists() else dict(BOUND_DEFAULTS)


def _normalize_database(name: str) -> str:
    """Normalize database name to canonical snake_case form."""
    return _DB_CANONICAL.get(name.lower().strip(), name.lower().strip().replace(" ", "_"))


# --- Command handlers ---

def cmd_metrics(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    data = load_workspace_data(workspace)
    result = m.recompute_all(
        screening_log=data["screening_log"],
        candidates=data["candidates"],
        included=data["included"],
        snowball_log=data["snowball_log"],
        extractions=data["extractions"],
        concepts=data["concepts"],
    )
    json.dump(result, sys.stdout, indent=2)
    print()


def evaluate_postconditions(workspace: Path, phase: int) -> tuple[bool, list[str]]:
    """Run the postcondition checks for one phase against a workspace."""
    data = load_workspace_data(workspace)

    if phase == 1:
        protocol_queries = parse_protocol_queries(workspace)
        satisfied, failures = pc.check_phase1_all(
            protocol_queries, data["search_log"], data["candidates"]
        )
    elif phase == 2:
        satisfied, failures = pc.check_phase2_all(
            data["candidates"], data["screening_log"], data["included"]
        )
    elif phase == 3:
        bounds = read_protocol_bounds(workspace)
        max_depth = bounds["max_snowball_depth"]
        threshold = bounds["discovery_saturation_threshold"]
        satisfied, failures = pc.check_phase3_all(
            seed_papers=data["included"],
            snowball_log=data["snowball_log"],
            phase_log=data["phase_log"],
            included=data["included"],
            candidates=data["candidates"],
            max_depth=max_depth,
            threshold=threshold,
        )
    elif phase == 4:
        concept_matrix_path = workspace / "concept-matrix.md"
        concept_matrix_exists = (
            concept_matrix_path.exists() and concept_matrix_path.stat().st_size > 0
        )
        satisfied, failures = pc.check_phase4_all(
            data["included"],
            data["extractions"],
            data["concepts"],
            concept_matrix_exists,
            data["phase_log"],
        )
    elif phase == 5:
        citation_keys = parse_review_citations(workspace)
        section_headers = parse_review_headers(workspace)
        protocol_questions = parse_protocol_questions(workspace)
        appendix_rows = count_appendix_a_rows(workspace)
        appendix_keys = parse_appendix_keys(workspace)
        bib_path = workspace / "references.bib"
        bib_count = 0
        if bib_path.exists():
            bib_count = len(re.findall(r"^@\w+\{", bib_path.read_text(), re.MULTILINE))
        # Parse output_format from protocol.md
        output_format = "kitchenham"
        protocol_path = workspace / "protocol.md"
        if protocol_path.exists():
            ptext = protocol_path.read_text()
            fmt_match = re.search(r"\|\s*output_format\s*\|\s*(\w+)", ptext)
            if fmt_match:
                output_format = fmt_match.group(1).strip()
        satisfied, failures = pc.check_phase5_all(
            data["included"],
            citation_keys,
            section_headers,
            protocol_questions,
            data["question_answers"],
            bib_count,
            appendix_rows,
            len(data["included"]),
            appendix_keys,
            output_format=output_format,
        )
    else:
        raise ValueError(f"Invalid phase: {phase}")
    return satisfied, failures


def cmd_postcondition(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    try:
        satisfied, failures = evaluate_postconditions(workspace, args.phase)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    json.dump({"satisfied": satisfied, "failures": failures}, sys.stdout, indent=2)
    print()


def cmd_transition(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    state_path = workspace / "state.json"
    state_data = read_json(state_path)

    # Extract state machine fields
    phase_completed = [False] * 6
    for entry in state_data.get("phase_history", []):
        if entry.get("completed_at") is not None:
            phase_completed[entry["phase"]] = True

    current = st.make_state(
        current_phase=state_data["current_phase"],
        phase_status=state_data["phase_status"],
        feedback_iterations=state_data.get("feedback_iterations", 0),
        retry_count=0,  # reset per transition
        phase_completed=phase_completed,
    )

    action = args.action
    if action == "next":
        new_state = st.transition_to_next(current)
    elif action == "start":
        new_state = st.start_phase(current, current["current_phase"])
    elif action == "complete":
        new_state = st.complete_phase(current, current["current_phase"])
    elif action == "fail":
        new_state = st.fail_phase(current, current["current_phase"])
    elif action == "retry":
        new_state = st.retry_phase(current)
    elif action == "diagnostic":
        new_state = st.diagnostic_transition(current)
    elif action == "feedback":
        max_iter = args.max_iterations or 2
        new_state = st.feedback_loop(current, max_iter)
    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))
        sys.exit(1)
        return

    # Apply changes back to state.json
    state_data["current_phase"] = new_state["current_phase"]
    state_data["phase_status"] = new_state["phase_status"]
    state_data["feedback_iterations"] = new_state["feedback_iterations"]
    state_data["updated_at"] = now_iso()
    write_json(state_path, state_data)

    json.dump({
        "current_phase": new_state["current_phase"],
        "phase_status": new_state["phase_status"],
        "feedback_iterations": new_state["feedback_iterations"],
    }, sys.stdout, indent=2)
    print()


def _machine_state(state_data: dict) -> dict:
    """The state-machine record for a state.json document."""
    phase_completed = [False] * 6
    for entry in state_data.get("phase_history", []):
        if entry.get("completed_at") is not None:
            phase_completed[entry["phase"]] = True
    return st.make_state(
        current_phase=state_data["current_phase"],
        phase_status=state_data["phase_status"],
        feedback_iterations=state_data.get("feedback_iterations", 0),
        retry_count=state_data.get("retry_count", 0),
        phase_completed=phase_completed,
    )


def _plain(value):
    return getattr(value, "value", value)


def cmd_step(args: argparse.Namespace) -> None:
    """Decide the next orchestration step, apply it, and print what to do.

    The orchestrator calls this once to begin and again after every agent
    returns. It runs the postconditions when a phase is in progress, applies
    the transition table (lib/orchestrate.py) to state.json and
    phase-log.jsonl, runs deterministic preprocessing, and prints one JSON
    instruction: dispatch a phase agent, stop (DECISION or RECOVERY), or done.
    """
    workspace = Path(args.workspace).expanduser()
    state_path = workspace / "state.json"
    state_data = read_json(state_path)
    ts = now_iso()
    log_events: list[dict] = []

    if args.reset:
        if state_data.get("phase_status") != st.PhaseStatus.FAILED:
            print(json.dumps({"error": "--reset only applies to a failed phase"}))
            sys.exit(1)
        state_data.update(phase_status="pending", retry_count=0, failure_reason=None)
        log_events.append({"event": "user_reset", "phase": state_data["current_phase"]})

    machine = _machine_state(state_data)
    phase = machine["current_phase"]
    bounds = read_protocol_bounds(workspace)

    ok, failures = None, []
    if machine["phase_status"] == st.PhaseStatus.IN_PROGRESS and 1 <= phase <= 5:
        ok, failures = evaluate_postconditions(workspace, phase)

    data = load_workspace_data(workspace)
    delta = None
    if phase == 4 and data["extractions"]:
        extractions = sorted(data["extractions"], key=lambda e: e.get("timestamp", ""))
        last_k = {e.get("paper_id") for e in extractions[-bounds["conceptual_saturation_k"]:]} - {None}
        delta = sat.conceptual_saturation(data["concepts"], last_k)

    decision = orch.decide(machine, orch.Evidence(
        protocol_approved=bool(state_data.get("protocol_approved")),
        postcondition_ok=ok,
        failures=tuple(failures),
        included_count=len(data["included"]),
        conceptual_saturation=delta,
        conceptual_threshold=bounds["conceptual_saturation_threshold"],
        max_feedback_iterations=bounds["max_feedback_iterations"],
    ))

    new = decision.state
    state_data.update(
        current_phase=new["current_phase"],
        phase_status=_plain(new["phase_status"]),
        feedback_iterations=new["feedback_iterations"],
        retry_count=new["retry_count"],
        updated_at=ts,
    )
    if decision.stop == "RECOVERY" and decision.failures:
        state_data["failure_reason"] = "; ".join(decision.failures[:5])
    elif decision.action == "dispatch" and not decision.retry:
        state_data["failure_reason"] = None

    history = state_data.setdefault("phase_history", [])
    for event in decision.events:
        if event["event"] == "phase_complete":
            for entry in reversed(history):
                if entry.get("phase") == event["phase"] and entry.get("completed_at") is None:
                    entry["completed_at"] = ts
                    break
        elif event["event"] == "phase_start":
            history.append({"phase": event["phase"], "started_at": ts, "completed_at": None,
                            "agent_id": None, "work_units_completed": 0, "notes": None})
        log_events.append(event)

    if decision.completed_phase is not None:
        metrics = state_data.setdefault("metrics", {})
        metrics.update(m.recompute_all(
            screening_log=data["screening_log"], candidates=data["candidates"],
            included=data["included"], snowball_log=data["snowball_log"],
            extractions=data["extractions"], concepts=data["concepts"],
        ))
        discovery = [e for e in data["phase_log"]
                     if e.get("event") == "saturation_check" and e.get("phase") == 3]
        if discovery:
            metrics["discovery_saturation"] = discovery[-1].get("saturation_metric")
        if decision.completed_phase == 4 and delta is not None:
            metrics["conceptual_saturation"] = float(delta)

    preprocess = None
    if decision.preprocess:
        try:
            preprocess = run_preprocess(workspace, decision.preprocess)
            log_events.append({"event": "preprocess", "type": decision.preprocess, **preprocess})
        except Exception as e:  # advisory: never blocks the run
            preprocess = {"error": str(e)}
            log_events.append({"event": "preprocess_failed", "type": decision.preprocess,
                               "error": str(e)})

    log_path = workspace / "logs" / "phase-log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        for event in log_events:
            f.write(json.dumps({"timestamp": ts, **event}) + "\n")
    write_json(state_path, state_data)

    out_phase = state_data["current_phase"]
    message = None
    if decision.action == "stop":
        prefix = "DECISION REQUIRED" if decision.stop == "DECISION" else "RECOVERY"
        message = f"{prefix}: {decision.reason}"
    json.dump({
        "action": decision.action,
        "phase": out_phase,
        "phase_name": orch.PHASE_NAMES.get(out_phase),
        "retry": decision.retry,
        "feedback_iteration": state_data["feedback_iterations"],
        "failures": list(decision.failures[:20]),
        "stop": decision.stop,
        "message": message,
        "completed_phase": decision.completed_phase,
        "metrics": state_data.get("metrics") if decision.completed_phase is not None else None,
        "preprocess": preprocess,
    }, sys.stdout, indent=2)
    print()


def cmd_saturation(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    data = load_workspace_data(workspace)

    if args.type == "discovery":
        depth = args.depth or 0
        result = sat.discovery_saturation(data["snowball_log"], depth)
        json.dump({
            "type": "discovery",
            "depth": depth,
            "saturation": str(result),
            "saturation_float": float(result),
        }, sys.stdout, indent=2)
    elif args.type == "conceptual":
        k = args.k or 5
        # Get last k papers by timestamp from extractions
        extractions = sorted(data["extractions"], key=lambda e: e.get("timestamp", ""))
        last_k_ids = ({e.get("paper_id") for e in extractions[-k:]} - {None}) if extractions else set()
        result = sat.conceptual_saturation(data["concepts"], last_k_ids)
        json.dump({
            "type": "conceptual",
            "k": k,
            "saturation": str(result),
            "saturation_float": float(result),
        }, sys.stdout, indent=2)
    else:
        print(json.dumps({"error": f"Unknown saturation type: {args.type}"}))
        sys.exit(1)
    print()


def cmd_parse_sections(args: argparse.Namespace) -> None:
    file_path = Path(args.file).expanduser()
    text = file_path.read_text()

    if args.field:
        result = sp.get_extraction_context(text, args.field, max_chars=args.max_chars)
        json.dump(result, sys.stdout, indent=2)
    else:
        sections = sp.parse_sections(text)
        output = [
            {
                "heading": s["heading"],
                "level": s["level"],
                "start": s["start"],
                "end": s["end"],
                "char_count": s["end"] - s["start"],
            }
            for s in sections
        ]
        json.dump(output, sys.stdout, indent=2)
    print()


def cmd_validate_inference(args: argparse.Namespace) -> None:
    if args.record:
        record = json.loads(args.record)
    elif args.file:
        record = json.loads(Path(args.file).read_text())
    else:
        print(json.dumps({"error": "Provide --record or --file"}))
        sys.exit(1)

    contracts = {
        "SCREEN_CRITERION": oc.SCREEN_CRITERION,
        "SCREEN_DECISION": oc.SCREEN_DECISION,
        "EXTRACT_FIELD": oc.EXTRACT_FIELD,
        "IDENTIFY_CONCEPTS": oc.IDENTIFY_CONCEPTS,
        "SYNTHESIZE_CLAIM": oc.SYNTHESIZE_CLAIM,
    }
    contract = contracts.get(args.contract)
    if not contract:
        print(json.dumps({"error": f"Unknown contract: {args.contract}"}))
        sys.exit(1)

    kwargs = {}
    if args.contract == "EXTRACT_FIELD" and args.parent_source:
        kwargs["parent_source"] = args.parent_source

    result = oc.validate_and_recover(record, contract, **kwargs)
    json.dump(result["validation"], sys.stdout, indent=2)
    print()


def _parse_protocol_criteria(workspace: Path) -> list[dict]:
    """Extract inclusion/exclusion criteria with testable conditions from protocol.md."""
    protocol_path = workspace / "protocol.md"
    if not protocol_path.exists():
        return []
    text = protocol_path.read_text()
    criteria = []
    # Match table rows: | IC1/EC1 | description | testable condition |
    for match in re.finditer(
        r"\|\s*([IE]C\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", text
    ):
        criteria.append({
            "criterion_id": match.group(1).strip(),
            "description": match.group(2).strip(),
            "testable_condition": match.group(3).strip(),
        })
    return criteria


def run_preprocess(workspace: Path, kind: str) -> dict:
    """Run deterministic preprocessing ("screening" or "synthesis"); return a summary."""
    data = load_workspace_data(workspace)

    if kind == "screening":
        # Parse criteria from protocol.md
        criteria = _parse_protocol_criteria(workspace)
        results = []
        for candidate in data["candidates"]:
            # A missing abstract is stored as null, not absent (issue #37).
            result = prep.preprocess_for_screening(
                candidate.get("abstract") or "",
                candidate.get("title") or "",
                criteria,
            )
            # Key each record to its paper; the abstract itself stays in
            # candidates.jsonl rather than repeating per criterion (#38).
            for r in result:
                r.pop("full_abstract", None)
                results.append({"paper_id": candidate.get("id"), **r})
        output_path = workspace / "data" / "preprocessed-screening.jsonl"
        with open(output_path, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        return {"written": str(output_path), "records": len(results)}

    result = prep.preprocess_for_synthesis(data["extractions"], data["concepts"])
    output_path = workspace / "data" / "preprocessed-synthesis.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    return {"written": str(output_path), "themes": len(result.get("themes", []))}


def cmd_preprocess(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    json.dump(run_preprocess(workspace, args.type), sys.stdout, indent=2)
    print()


def cmd_export(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    data = load_workspace_data(workspace)

    dataset_map = {
        "candidates": data["candidates"],
        "included": data["included"],
        "extractions": data["extractions"],
    }
    records = dataset_map.get(args.dataset, [])

    if args.format == "ris":
        output = exp.to_ris(records)
    elif args.format == "csv":
        default_fields = {
            "candidates": ["id", "title", "authors", "year", "venue", "doi", "source"],
            "included": ["id", "title", "authors", "year", "venue", "doi", "source"],
            "extractions": ["paper_id", "source", "timestamp"],
        }
        fields = default_fields.get(args.dataset, ["id", "title"])
        output = exp.to_csv(records, fields)

    output_path = workspace / f"exports/{args.dataset}.{args.format}"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(output)
    json.dump({"written": str(output_path), "records": len(records), "format": args.format},
              sys.stdout, indent=2)
    print()


def cmd_prisma(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    data = load_workspace_data(workspace)
    review_path = workspace / "review.md"
    review_text = review_path.read_text() if review_path.exists() else ""
    protocol = {}

    if args.type == "prisma2020":
        items = pr.check_prisma_compliance(review_text, data, protocol)
    elif args.type == "traice":
        items = pr.check_prisma_traice_compliance(review_text, data)
    else:
        print(json.dumps({"error": f"Unknown type: {args.type}"}))
        sys.exit(1)
        return

    json.dump(items, sys.stdout, indent=2)
    print()


# --- Argument parser ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Stepwise verified CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # metrics
    p_metrics = sub.add_parser("metrics", help="Recompute all metrics from workspace")
    p_metrics.add_argument("--workspace", required=True)

    # postcondition
    p_post = sub.add_parser("postcondition", help="Run postcondition checks for a phase")
    p_post.add_argument("--phase", type=int, required=True, choices=[1, 2, 3, 4, 5])
    p_post.add_argument("--workspace", required=True)

    # transition
    p_trans = sub.add_parser("transition", help="Execute a state transition")
    p_trans.add_argument(
        "--action", required=True,
        choices=["next", "start", "complete", "fail", "retry", "diagnostic", "feedback"],
    )
    p_trans.add_argument("--workspace", required=True)
    p_trans.add_argument("--max-iterations", type=int, default=2)

    # step
    p_step = sub.add_parser("step", help="Decide and apply the next orchestration step")
    p_step.add_argument("--workspace", required=True)
    p_step.add_argument("--reset", action="store_true",
                        help="After a RECOVERY stop: reset the failed phase to pending and retry")

    # saturation
    p_sat = sub.add_parser("saturation", help="Compute saturation metric")
    p_sat.add_argument("--type", required=True, choices=["discovery", "conceptual"])
    p_sat.add_argument("--workspace", required=True)
    p_sat.add_argument("--depth", type=int)
    p_sat.add_argument("--k", type=int)

    # parse-sections
    p_sections = sub.add_parser("parse-sections", help="Parse markdown text into sections")
    p_sections.add_argument("--file", required=True, help="Path to text file")
    p_sections.add_argument("--field", help="Optional: get extraction context for a specific field")
    p_sections.add_argument("--max-chars", type=int, default=8000, help="Max context chars (default 8000)")

    # validate-inference
    p_val = sub.add_parser("validate-inference", help="Validate a record against an oracle contract")
    p_val.add_argument("--contract", required=True,
                       choices=["SCREEN_CRITERION", "SCREEN_DECISION", "EXTRACT_FIELD",
                                "IDENTIFY_CONCEPTS", "SYNTHESIZE_CLAIM"])
    p_val.add_argument("--record", help="Inline JSON record")
    p_val.add_argument("--file", help="Path to JSON file containing record")
    p_val.add_argument("--parent-source", help="Parent extraction source (for EXTRACT_FIELD)")

    # preprocess
    p_prep = sub.add_parser("preprocess", help="Run deterministic preprocessing")
    p_prep.add_argument("--type", required=True, choices=["screening", "synthesis"])
    p_prep.add_argument("--workspace", required=True)

    # prisma
    p_prisma = sub.add_parser("prisma", help="Check PRISMA compliance")
    p_prisma.add_argument("--type", required=True, choices=["prisma2020", "traice"])
    p_prisma.add_argument("--workspace", required=True)

    # export
    p_exp = sub.add_parser("export", help="Export data to RIS or CSV format")
    p_exp.add_argument("--format", required=True, choices=["ris", "csv"])
    p_exp.add_argument("--dataset", required=True, choices=["candidates", "included", "extractions"])
    p_exp.add_argument("--workspace", required=True)

    args = parser.parse_args()
    handlers = {
        "metrics": cmd_metrics,
        "postcondition": cmd_postcondition,
        "transition": cmd_transition,
        "step": cmd_step,
        "saturation": cmd_saturation,
        "parse-sections": cmd_parse_sections,
        "validate-inference": cmd_validate_inference,
        "preprocess": cmd_preprocess,
        "prisma": cmd_prisma,
        "export": cmd_export,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
