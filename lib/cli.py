#!/usr/bin/env python3
"""Scholar CLI — thin I/O wrapper over verified pure functions.

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

from . import metrics as m
from . import postconditions as pc
from . import saturation as sat
from . import state as st


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
    # Find citation keys
    return set(re.findall(r"\[@([^\]]+)\]", text))


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
    """Extract (database, query) pairs from protocol.md search terms table."""
    protocol_path = workspace / "protocol.md"
    if not protocol_path.exists():
        return []
    text = protocol_path.read_text()
    queries = []
    # Match table rows with database | query pattern
    for match in re.finditer(r"\|\s*(\w[\w\s]*?)\s*\|\s*(.+?)\s*\|", text):
        db = match.group(1).strip()
        query = match.group(2).strip()
        if db.lower() not in ("database", "---", ""):
            queries.append({"database": db, "query": query})
    return queries


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


def cmd_postcondition(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    phase = args.phase
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
        state = read_json(workspace / "state.json")
        protocol = read_json(workspace / "protocol.md") if False else {}
        # Read bounds from protocol.md text
        protocol_path = workspace / "protocol.md"
        max_depth = 2
        threshold = Fraction(5, 100)
        if protocol_path.exists():
            ptext = protocol_path.read_text()
            md_match = re.search(r"max_snowball_depth[`\s:]*(\d+)", ptext)
            if md_match:
                max_depth = int(md_match.group(1))
            td_match = re.search(r"discovery_saturation_threshold[`\s:]*([0-9.]+)", ptext)
            if td_match:
                threshold = Fraction(td_match.group(1))
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
        bib_path = workspace / "references.bib"
        bib_count = 0
        if bib_path.exists():
            bib_count = len(re.findall(r"^@\w+\{", bib_path.read_text(), re.MULTILINE))
        satisfied, failures = pc.check_phase5_all(
            data["included"],
            citation_keys,
            section_headers,
            protocol_questions,
            data["question_answers"],
            bib_count,
            appendix_rows,
            len(data["included"]),
        )
    else:
        print(json.dumps({"error": f"Invalid phase: {phase}"}))
        sys.exit(1)
        return

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
        last_k_ids = {e["paper_id"] for e in extractions[-k:]} if extractions else set()
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


# --- Argument parser ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Scholar verified CLI")
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

    # saturation
    p_sat = sub.add_parser("saturation", help="Compute saturation metric")
    p_sat.add_argument("--type", required=True, choices=["discovery", "conceptual"])
    p_sat.add_argument("--workspace", required=True)
    p_sat.add_argument("--depth", type=int)
    p_sat.add_argument("--k", type=int)

    args = parser.parse_args()
    handlers = {
        "metrics": cmd_metrics,
        "postcondition": cmd_postcondition,
        "transition": cmd_transition,
        "saturation": cmd_saturation,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
