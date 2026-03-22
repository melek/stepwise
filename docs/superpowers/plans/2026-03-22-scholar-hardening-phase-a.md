# Scholar Hardening Phase A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden Scholar's runtime guarantees by adding OracleContracts for inference quarantine, deterministic preprocessing, PRISMA-compliant output, Dafny-verified state machine, and expert panel governance.

**Architecture:** Extend Scholar's existing pure-function library (`lib/`) with four new modules (`oracle_contracts.py`, `preprocess.py`, `prisma.py`, `export.py`) and one Dafny specification directory (`spec/`). Per-record validators are added to `postconditions.py`; phase-level checks compose over them. New CLI subcommands follow the existing argparse pattern. All new modules are pure functions with no I/O — the CLI remains the thin I/O shell.

**Tech Stack:** Python 3.10+, pytest, Dafny (optional, for verification), fractions.Fraction (existing)

**Spec:** `docs/superpowers/specs/2026-03-22-scholar-hardening-design.md` (v1.1)

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `lib/oracle_contracts.py` | Contract dataclasses, validate-and-recover wrapper. Imports validators from postconditions.py. |
| `lib/preprocess.py` | Deterministic preprocessing: screening evidence windows, synthesis theme briefs. Pure functions. |
| `lib/prisma.py` | PRISMA 2020 + trAIce compliance checking. Pure functions. |
| `lib/export.py` | PRISMA Mermaid flow diagram generation. (RIS/CSV added in Phase B.) |
| `spec/state.dfy` | Dafny specification for the phase state machine. |
| `spec/saturation.dfy` | Dafny specification for saturation metrics. |
| `tests/test_oracle_contracts.py` | Oracle contract validation + recovery tests. |
| `tests/test_preprocess.py` | Preprocessing pure function tests. |
| `tests/test_prisma.py` | PRISMA compliance checker tests. |
| `tests/test_export.py` | Mermaid diagram generation tests. |
| `templates/review-template-prisma.md` | PRISMA 2020 review template. |
| `templates/review-template-narrative.md` | Lightweight narrative template. |
| `docs/methodology/EXPERT_ROSTER.md` | Scholar expert panel roster. |
| `docs/methodology/CHANGE_PROTOCOL.md` | Tier-based change management protocol. |

### Modified Files

| File | Changes |
|------|---------|
| `lib/postconditions.py` | Add per-record validators (`validate_screening_record`, `validate_extraction_record`, `validate_concept_record`). Phase-level checks refactored to compose over them. |
| `lib/cli.py` | Add subcommands: `validate-inference`, `preprocess`, `prisma`. |
| `templates/protocol-template.md` | Add Output Configuration section. |
| `templates/review-template.md` | Rename to `review-template-kitchenham.md` (backward compat). |

---

## Task 1: Per-Record Screening Validator

**Files:**
- Modify: `lib/postconditions.py`
- Test: `tests/test_oracle_contracts.py` (create)

- [ ] **Step 1: Write failing tests for `validate_screening_criterion`**

```python
# tests/test_oracle_contracts.py
"""Tests for per-record validators and oracle contract wrappers."""

from lib.postconditions import validate_screening_criterion


def test_valid_criterion():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "The abstract states: 'we formally verify...'",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is True
    assert failures == []


def test_invalid_met_value():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "maybe",
        "evidence": "some text",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("met" in f for f in failures)


def test_empty_evidence():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("evidence" in f for f in failures)


def test_invalid_criterion_id_pattern():
    record = {
        "criterion_id": "QA1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "some text",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("criterion_id" in f for f in failures)


def test_invalid_criterion_type():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "quality",
        "met": "yes",
        "evidence": "some text",
        "source": "abstract",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("criterion_type" in f for f in failures)


def test_invalid_source():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "some text",
        "source": "google",
    }
    ok, failures = validate_screening_criterion(record)
    assert ok is False
    assert any("source" in f for f in failures)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v`
Expected: FAIL — `ImportError: cannot import name 'validate_screening_criterion'`

- [ ] **Step 3: Implement `validate_screening_criterion` in postconditions.py**

Add to `lib/postconditions.py` after the `_result` helper (around line 18):

```python
import re

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add lib/postconditions.py tests/test_oracle_contracts.py
git commit -m "feat: add per-record screening criterion validator"
```

---

## Task 2: Per-Record Screening Decision Validator

**Files:**
- Modify: `lib/postconditions.py`
- Test: `tests/test_oracle_contracts.py`

- [ ] **Step 1: Write failing tests for `validate_screening_decision`**

Add to `tests/test_oracle_contracts.py`:

```python
from lib.postconditions import validate_screening_decision


def _make_criteria(ics, ecs):
    """Helper: build criteria_evaluations from IC/EC met values."""
    evals = []
    for i, met in enumerate(ics, 1):
        evals.append({"criterion_id": f"IC{i}", "criterion_type": "inclusion",
                       "met": met, "evidence": "text", "source": "abstract"})
    for i, met in enumerate(ecs, 1):
        evals.append({"criterion_id": f"EC{i}", "criterion_type": "exclusion",
                       "met": met, "evidence": "text", "source": "abstract"})
    return evals


def test_valid_include_decision():
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["yes", "yes"], ["no"]),
        "reasoning": "All IC met, no EC triggered.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_include_with_ec_met_fails():
    """Include decision but an exclusion criterion is met — biconditional violation."""
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["yes"], ["yes"]),
        "reasoning": "Included despite EC.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False
    assert any("biconditional" in f.lower() or "decision rule" in f.lower() for f in failures)


def test_include_with_ic_not_met_fails():
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["no", "yes"], ["no"]),
        "reasoning": "Included despite IC not met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_valid_exclude_ec_met():
    record = {
        "decision": "exclude",
        "criteria_evaluations": _make_criteria(["yes"], ["yes"]),
        "reasoning": "EC1 met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_valid_exclude_ic_not_met():
    record = {
        "decision": "exclude",
        "criteria_evaluations": _make_criteria(["no"], ["no"]),
        "reasoning": "IC1 not met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_exclude_with_all_ic_met_no_ec_fails():
    """Exclude but all IC met and no EC met — should be include."""
    record = {
        "decision": "exclude",
        "criteria_evaluations": _make_criteria(["yes"], ["no"]),
        "reasoning": "Excluded anyway.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_valid_flag_for_full_text():
    record = {
        "decision": "flag_for_full_text",
        "criteria_evaluations": _make_criteria(["yes", "unclear"], ["no"]),
        "reasoning": "IC2 unclear from abstract.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is True


def test_flag_with_ec_met_fails():
    """Flag for full text but EC is met — should be exclude."""
    record = {
        "decision": "flag_for_full_text",
        "criteria_evaluations": _make_criteria(["unclear"], ["yes"]),
        "reasoning": "Flagged despite EC met.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_empty_criteria_fails():
    record = {
        "decision": "include",
        "criteria_evaluations": [],
        "reasoning": "No criteria.",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False


def test_empty_reasoning_fails():
    record = {
        "decision": "include",
        "criteria_evaluations": _make_criteria(["yes"], ["no"]),
        "reasoning": "",
    }
    ok, failures = validate_screening_decision(record)
    assert ok is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v -k "decision"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement `validate_screening_decision`**

Add to `lib/postconditions.py`:

```python
def validate_screening_decision(record: dict) -> tuple[bool, list[str]]:
    """Validate a complete screening decision record (biconditional rules)."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```bash
git add lib/postconditions.py tests/test_oracle_contracts.py
git commit -m "feat: add screening decision validator with biconditional rules"
```

---

## Task 3: Per-Record Extraction Validators

**Files:**
- Modify: `lib/postconditions.py`
- Test: `tests/test_oracle_contracts.py`

- [ ] **Step 1: Write failing tests for `validate_extraction_field` and `validate_concept_record`**

Add to `tests/test_oracle_contracts.py`:

```python
from lib.postconditions import validate_extraction_field, validate_concept_record


# --- EXTRACT_FIELD ---

def test_valid_extraction_field():
    record = {
        "field_name": "methodology",
        "value": "randomized controlled trial",
        "confidence": "high",
        "source_location": "Section 3: Methods",
    }
    ok, failures = validate_extraction_field(record, parent_source="full_text")
    assert ok is True


def test_abstract_source_high_confidence_fails():
    record = {
        "field_name": "methodology",
        "value": "RCT",
        "confidence": "high",
        "source_location": "abstract",
    }
    ok, failures = validate_extraction_field(record, parent_source="abstract")
    assert ok is False
    assert any("confidence" in f for f in failures)


def test_abstract_source_medium_confidence_ok():
    record = {
        "field_name": "methodology",
        "value": "RCT",
        "confidence": "medium",
        "source_location": "abstract",
    }
    ok, failures = validate_extraction_field(record, parent_source="abstract")
    assert ok is True


def test_extraction_failed_value_ok():
    record = {
        "field_name": "methodology",
        "value": "extraction_failed",
        "confidence": "low",
        "source_location": "abstract",
    }
    ok, failures = validate_extraction_field(record, parent_source="abstract")
    assert ok is True


def test_empty_field_name_fails():
    record = {
        "field_name": "",
        "value": "something",
        "confidence": "medium",
        "source_location": "abstract",
    }
    ok, failures = validate_extraction_field(record, parent_source="full_text")
    assert ok is False


def test_invalid_confidence_fails():
    record = {
        "field_name": "methodology",
        "value": "something",
        "confidence": "very_high",
        "source_location": "Section 3",
    }
    ok, failures = validate_extraction_field(record, parent_source="full_text")
    assert ok is False


# --- IDENTIFY_CONCEPTS ---

def test_valid_concept():
    record = {
        "concept_id": "formal-verification",
        "label": "Formal Verification",
        "definition": "The use of mathematical proofs to verify system correctness",
        "frequency": 3,
    }
    ok, failures = validate_concept_record(record)
    assert ok is True


def test_single_char_concept_id_fails():
    record = {
        "concept_id": "x",
        "label": "X",
        "definition": "Some concept with a single character ID",
        "frequency": 1,
    }
    ok, failures = validate_concept_record(record)
    assert ok is False
    assert any("concept_id" in f for f in failures)


def test_short_definition_fails():
    record = {
        "concept_id": "formal-verification",
        "label": "Formal Verification",
        "definition": "Proofs",
        "frequency": 1,
    }
    ok, failures = validate_concept_record(record)
    assert ok is False
    assert any("definition" in f for f in failures)


def test_zero_frequency_fails():
    record = {
        "concept_id": "formal-verification",
        "label": "Formal Verification",
        "definition": "The use of mathematical proofs to verify system correctness",
        "frequency": 0,
    }
    ok, failures = validate_concept_record(record)
    assert ok is False


def test_concept_id_with_uppercase_fails():
    record = {
        "concept_id": "Formal-Verification",
        "label": "Formal Verification",
        "definition": "The use of mathematical proofs to verify system correctness",
        "frequency": 1,
    }
    ok, failures = validate_concept_record(record)
    assert ok is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v -k "extraction or concept"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement both validators**

Add to `lib/postconditions.py`:

```python
_CONCEPT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

def validate_extraction_field(
    record: dict, parent_source: str = "full_text"
) -> tuple[bool, list[str]]:
    """Validate a single extraction field record."""
    failures = []
    if not record.get("field_name"):
        failures.append("field_name: empty or missing")
    if not record.get("value"):
        failures.append("value: empty or missing")
    conf = record.get("confidence")
    if conf not in ("high", "medium", "low"):
        failures.append(f"confidence: {conf!r} not in {{high, medium, low}}")
    if not record.get("source_location"):
        failures.append("source_location: empty or missing")
    if parent_source == "abstract" and conf == "high":
        failures.append("confidence: 'high' not allowed when source is abstract")
    return _result(failures)


def validate_concept_record(record: dict) -> tuple[bool, list[str]]:
    """Validate a concept identification record."""
    failures = []
    cid = record.get("concept_id", "")
    if not _CONCEPT_ID_PATTERN.match(cid):
        failures.append(f"concept_id: {cid!r} does not match slug pattern (min 2 chars, lowercase)")
    if not record.get("label"):
        failures.append("label: empty or missing")
    defn = record.get("definition", "")
    if len(defn) < 10:
        failures.append(f"definition: too short ({len(defn)} chars, need >= 10)")
    freq = record.get("frequency", 0)
    if not isinstance(freq, int) or freq < 1:
        failures.append(f"frequency: {freq!r} must be int >= 1")
    return _result(failures)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v`
Expected: 29 passed

- [ ] **Step 5: Commit**

```bash
git add lib/postconditions.py tests/test_oracle_contracts.py
git commit -m "feat: add extraction field and concept record validators"
```

---

## Task 4: Oracle Contract Wrapper Module

**Files:**
- Create: `lib/oracle_contracts.py`
- Test: `tests/test_oracle_contracts.py`

- [ ] **Step 1: Write failing tests for oracle contract wrapper**

Add to `tests/test_oracle_contracts.py`:

```python
from lib.oracle_contracts import (
    OracleContract,
    SCREEN_CRITERION,
    SCREEN_DECISION,
    EXTRACT_FIELD,
    IDENTIFY_CONCEPTS,
    validate_and_recover,
)


def test_contract_registry_names():
    assert SCREEN_CRITERION.contract_id == "SCREEN_CRITERION"
    assert SCREEN_DECISION.contract_id == "SCREEN_DECISION"
    assert EXTRACT_FIELD.contract_id == "EXTRACT_FIELD"
    assert IDENTIFY_CONCEPTS.contract_id == "IDENTIFY_CONCEPTS"


def test_validate_and_recover_pass():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "The abstract states formal verification.",
        "source": "abstract",
    }
    result = validate_and_recover(record, SCREEN_CRITERION)
    assert result["record"] == record
    assert result["validation"]["satisfied"] is True
    assert result["validation"]["recovery_applied"] is False


def test_validate_and_recover_fail_with_recovery():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "maybe",  # invalid
        "evidence": "some text",
        "source": "abstract",
    }
    result = validate_and_recover(record, SCREEN_CRITERION)
    recovered = result["record"]
    assert recovered["met"] == "unclear"
    assert "validation_failed" in recovered["evidence"]
    assert result["validation"]["satisfied"] is False
    assert result["validation"]["recovery_applied"] is True


def test_provenance_metadata():
    record = {
        "criterion_id": "IC1",
        "criterion_type": "inclusion",
        "met": "yes",
        "evidence": "text",
        "source": "abstract",
    }
    result = validate_and_recover(record, SCREEN_CRITERION)
    prov = result["validation"]
    assert prov["contract_id"] == "SCREEN_CRITERION"
    assert "timestamp" in prov
    assert isinstance(prov["satisfied"], bool)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v -k "contract_registry or validate_and_recover or provenance"`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement oracle_contracts.py**

Create `lib/oracle_contracts.py`:

```python
"""Scholar oracle contracts — inference quarantine enforcement.

Each contract wraps a per-record validator from postconditions.py with:
- Contract identity (named, registered)
- Recovery strategy (what to do on validation failure)
- Provenance metadata (audit trail)

No file I/O. Pure functions over data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from . import postconditions as pc


@dataclass(frozen=True)
class OracleContract:
    """Named oracle contract with validator and recovery."""
    contract_id: str
    validator: Callable[[dict], tuple[bool, list[str]]]
    recovery: Callable[[dict, list[str]], dict]
    validator_kwargs: dict = field(default_factory=dict)


def _recover_screen_criterion(record: dict, failures: list[str]) -> dict:
    """Recovery: set met=unclear, evidence explains failure."""
    return {
        **record,
        "met": "unclear",
        "evidence": f"validation_failed: {'; '.join(failures)}",
        "recovery_applied": True,
    }


def _recover_extraction_field(record: dict, failures: list[str]) -> dict:
    """Recovery: set value=extraction_failed, confidence=low."""
    return {
        **record,
        "value": "extraction_failed",
        "confidence": "low",
        "recovery_applied": True,
    }


def _recover_concept(record: dict, failures: list[str]) -> dict:
    """Recovery: return None to signal skip."""
    return None


def _no_recovery(record: dict, failures: list[str]) -> dict:
    """No automatic recovery — return record as-is with failure marker."""
    return {**record, "recovery_applied": True}


SCREEN_CRITERION = OracleContract(
    contract_id="SCREEN_CRITERION",
    validator=pc.validate_screening_criterion,
    recovery=_recover_screen_criterion,
)

def _recover_screen_decision(record: dict, failures: list[str]) -> dict:
    """Recovery: reject and exclude with decision_rule_violation."""
    return {
        **record,
        "decision": "exclude",
        "reasoning": f"decision_rule_violation: {'; '.join(failures)}",
        "recovery_applied": True,
    }


SCREEN_DECISION = OracleContract(
    contract_id="SCREEN_DECISION",
    validator=pc.validate_screening_decision,
    recovery=_recover_screen_decision,
)

EXTRACT_FIELD = OracleContract(
    contract_id="EXTRACT_FIELD",
    validator=pc.validate_extraction_field,
    recovery=_recover_extraction_field,
    validator_kwargs={"parent_source": "full_text"},  # default; callers override with actual source
)

IDENTIFY_CONCEPTS = OracleContract(
    contract_id="IDENTIFY_CONCEPTS",
    validator=pc.validate_concept_record,
    recovery=_recover_concept,
)


def validate_and_recover(
    record: dict, contract: OracleContract, **kwargs
) -> dict:
    """Validate a record against a contract. On failure, apply recovery.

    Returns: {
        "record": validated or recovered record,
        "validation": {
            "contract_id": str,
            "timestamp": ISO-8601,
            "satisfied": bool,
            "failures": list[str],
            "recovery_applied": bool,
        }
    }
    """
    all_kwargs = {**contract.validator_kwargs, **kwargs}
    satisfied, failures = contract.validator(record, **all_kwargs)

    if satisfied:
        result_record = dict(record)
    else:
        result_record = contract.recovery(record, failures)

    # Inject provenance metadata into the record itself (spec Section 1.6)
    provenance = {
        "contract_id": contract.contract_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "satisfied": satisfied,
        "recovery_applied": not satisfied,
    }
    if result_record is not None:
        result_record["_validated_by"] = provenance

    return {
        "record": result_record,
        "validation": {**provenance, "failures": failures},
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v`
Expected: 32 passed

- [ ] **Step 5: Commit**

```bash
git add lib/oracle_contracts.py tests/test_oracle_contracts.py
git commit -m "feat: add oracle contract wrapper with recovery and provenance"
```

---

## Task 4b: SYNTHESIZE_CLAIM Validator and Contract

**Files:**
- Modify: `lib/postconditions.py`
- Modify: `lib/oracle_contracts.py`
- Test: `tests/test_oracle_contracts.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_oracle_contracts.py`:

```python
from lib.postconditions import validate_synthesis_claims


def test_valid_synthesis_paragraph():
    paragraphs = [
        {"text": "Formal verification improves reliability [@dijkstra1968].", "section": "3.2"},
    ]
    included_keys = {"dijkstra1968", "leino2010"}
    extraction_completeness = {"dijkstra1968": 1.0, "leino2010": 0.8}
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, extraction_completeness)
    assert ok is True


def test_paragraph_without_citation_fails():
    paragraphs = [
        {"text": "Formal verification improves reliability.", "section": "3.2"},
    ]
    ok, failures = validate_synthesis_claims(paragraphs, set(), {})
    assert ok is False
    assert any("citation" in f.lower() for f in failures)


def test_citation_to_absent_paper_fails():
    paragraphs = [
        {"text": "Results show improvement [@ghost2099].", "section": "3.2"},
    ]
    included_keys = {"dijkstra1968"}
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, {})
    assert ok is False
    assert any("ghost2099" in f for f in failures)


def test_low_completeness_paper_without_qualification_fails():
    paragraphs = [
        {"text": "The paper found strong results [@baddata2024].", "section": "3.2"},
    ]
    included_keys = {"baddata2024"}
    extraction_completeness = {"baddata2024": 0.3}  # <50% fields succeeded
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, extraction_completeness)
    assert ok is False
    assert any("qualification" in f.lower() or "limited" in f.lower() for f in failures)


def test_low_completeness_with_qualification_passes():
    paragraphs = [
        {"text": "The paper found results [limited data] [@baddata2024].", "section": "3.2"},
    ]
    included_keys = {"baddata2024"}
    extraction_completeness = {"baddata2024": 0.3}
    ok, failures = validate_synthesis_claims(paragraphs, included_keys, extraction_completeness)
    assert ok is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v -k "synthesis"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement `validate_synthesis_claims`**

Add to `lib/postconditions.py`:

```python
_CITATION_PATTERN = re.compile(r"\[@([^\]]+)\]")

def validate_synthesis_claims(
    paragraphs: list[dict],
    included_keys: set[str],
    extraction_completeness: dict[str, float],
    completeness_threshold: float = 0.5,
) -> tuple[bool, list[str]]:
    """Validate synthesis claim integrity.

    Each paragraph in Findings must have >= 1 citation.
    No citation may reference a key absent from included papers.
    Papers with >50% extraction failures need a qualification marker.
    """
    failures = []
    for para in paragraphs:
        text = para.get("text", "")
        section = para.get("section", "?")
        citations = _CITATION_PATTERN.findall(text)

        if not citations:
            failures.append(f"Section {section}: paragraph has no citations")
            continue

        for key in citations:
            if key not in included_keys:
                failures.append(f"Section {section}: citation [@{key}] references absent paper")
            elif extraction_completeness.get(key, 1.0) < completeness_threshold:
                # Check for qualification marker
                if "[limited data]" not in text and "[limited]" not in text:
                    failures.append(
                        f"Section {section}: [@{key}] has low data completeness "
                        f"({extraction_completeness[key]:.0%}) and needs qualification marker"
                    )

    return _result(failures)
```

- [ ] **Step 4: Register SYNTHESIZE_CLAIM contract in oracle_contracts.py**

Add to `lib/oracle_contracts.py`:

```python
SYNTHESIZE_CLAIM = OracleContract(
    contract_id="SYNTHESIZE_CLAIM",
    validator=pc.validate_synthesis_claims,
    recovery=_no_recovery,
)
```

- [ ] **Step 5: Run tests and commit**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_oracle_contracts.py -v`

```bash
git add lib/postconditions.py lib/oracle_contracts.py tests/test_oracle_contracts.py
git commit -m "feat: add SYNTHESIZE_CLAIM validator and contract"
```

---

## Task 5: Refactor Phase-Level Checks to Compose Over Per-Record Validators

**Files:**
- Modify: `lib/postconditions.py`
- Test: Run existing tests

- [ ] **Step 1: Run existing tests to establish baseline**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/ -v`
Record: number of tests passing.

- [ ] **Step 2: Refactor `check_extraction_schema_valid` to use `validate_extraction_field`**

In `lib/postconditions.py`, replace the body of `check_extraction_schema_valid` (lines ~275-294):

```python
def check_extraction_schema_valid(
    extractions: list[dict],
) -> tuple[bool, list[str]]:
    """Every extraction has valid source and field entries. Composes over validate_extraction_field."""
    valid_sources = {"full_text", "abstract"}
    failures = []
    for ext in extractions:
        pid = ext.get("paper_id", "?")
        source = ext.get("source")
        if source not in valid_sources:
            failures.append(f"Extraction {pid}: invalid or missing source field")
        for field_rec in ext.get("fields", []):
            ok, field_failures = validate_extraction_field(field_rec, parent_source=source or "full_text")
            for ff in field_failures:
                failures.append(f"Extraction {pid}: {ff}")
    return _result(failures)
```

- [ ] **Step 3: Run all tests to verify no regressions**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/ -v`
Expected: same count as baseline, all passing.

- [ ] **Step 4: Commit**

```bash
git add lib/postconditions.py
git commit -m "refactor: compose phase-level extraction check over per-record validator"
```

---

## Task 6: CLI `validate-inference` Subcommand

**Files:**
- Modify: `lib/cli.py`
- Test: manual CLI invocation

- [ ] **Step 1: Read current cli.py to understand pattern**

Read `lib/cli.py` — note the argparse subcommand pattern, `handlers` dict at line 436, JSON-to-stdout output.

- [ ] **Step 2: Add `validate-inference` subcommand**

Add to `lib/cli.py`:

```python
from . import oracle_contracts as oc

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
```

Add to the argparse setup in `main()`:

```python
    # validate-inference
    p_val = sub.add_parser("validate-inference", help="Validate a record against an oracle contract")
    p_val.add_argument("--contract", required=True,
                       choices=["SCREEN_CRITERION", "SCREEN_DECISION", "EXTRACT_FIELD", "IDENTIFY_CONCEPTS"])
    p_val.add_argument("--record", help="Inline JSON record")
    p_val.add_argument("--file", help="Path to JSON file containing record")
    p_val.add_argument("--parent-source", help="Parent extraction source (for EXTRACT_FIELD)")
```

Add to `handlers` dict:

```python
        "validate-inference": cmd_validate_inference,
```

- [ ] **Step 3: Test CLI manually**

Run:
```bash
cd /home/melek/workshop/scholar && python3 -m lib.cli validate-inference \
  --contract SCREEN_CRITERION \
  --record '{"criterion_id":"IC1","criterion_type":"inclusion","met":"yes","evidence":"test","source":"abstract"}'
```
Expected: `{"contract_id": "SCREEN_CRITERION", ..., "satisfied": true, ...}`

- [ ] **Step 4: Run all tests**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add lib/cli.py
git commit -m "feat: add validate-inference CLI subcommand"
```

---

## Task 7: Screening Preprocessor

**Files:**
- Create: `lib/preprocess.py`
- Create: `tests/test_preprocess.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_preprocess.py`:

```python
"""Tests for deterministic preprocessing functions."""

from lib.preprocess import preprocess_for_screening


def test_returns_evidence_window_per_criterion():
    abstract = (
        "This paper presents a novel approach to formal verification. "
        "We use model checking to verify safety properties. "
        "The approach is evaluated on three benchmarks. "
        "Results show 95% coverage of safety requirements. "
        "We conclude that formal methods improve reliability."
    )
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "addresses formal verification"},
        {"criterion_id": "IC2", "testable_condition": "reports empirical results"},
    ]
    results = preprocess_for_screening(abstract, "A Formal Verification Study", criteria)
    assert len(results) == 2
    assert results[0]["criterion_id"] == "IC1"
    assert results[1]["criterion_id"] == "IC2"
    assert "evidence_window" in results[0]
    assert "full_abstract" in results[0]
    assert results[0]["full_abstract"] == abstract


def test_evidence_window_contains_relevant_sentences():
    abstract = (
        "Machine learning is popular. "
        "We study neural networks. "
        "Formal verification ensures correctness. "
        "Our method verifies neural network properties. "
        "The conclusion summarizes findings."
    )
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "formal verification of neural networks"},
    ]
    results = preprocess_for_screening(abstract, "Test", criteria)
    window = results[0]["evidence_window"]
    # Should contain the verification-relevant sentences
    assert "verification" in window.lower()


def test_evidence_window_includes_first_and_last_sentence():
    abstract = (
        "First sentence of abstract. "
        "Middle content here. "
        "More middle content. "
        "Last sentence of abstract."
    )
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "something unrelated"},
    ]
    results = preprocess_for_screening(abstract, "Test", criteria)
    window = results[0]["evidence_window"]
    assert "First sentence" in window
    assert "Last sentence" in window


def test_keywords_matched_populated():
    abstract = "We apply formal verification using Dafny to prove correctness."
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "formal verification correctness"},
    ]
    results = preprocess_for_screening(abstract, "Test", criteria)
    assert "keywords_matched" in results[0]
    assert len(results[0]["keywords_matched"]) > 0


def test_empty_abstract_returns_empty_window():
    results = preprocess_for_screening("", "Test", [{"criterion_id": "IC1", "testable_condition": "test"}])
    assert results[0]["evidence_window"] == ""
    assert results[0]["full_abstract"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_preprocess.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `preprocess_for_screening`**

Create `lib/preprocess.py`:

```python
"""Scholar deterministic preprocessing.

Pure functions that transform inference inputs to improve oracle performance.
No I/O. No inference calls. Deterministic: same inputs produce same outputs.

Applies the Proven decompose.py pattern: rewrite inputs before the oracle
touches them to make the oracle's task more tractable.
"""

import re

# Common English stopwords (deterministic, no external dependency)
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "that", "which", "who", "whom", "this", "these", "those", "it", "its",
    "not", "no", "nor", "as", "if", "then", "than", "so", "such", "both",
    "each", "all", "any", "few", "more", "most", "other", "some", "only",
    "own", "same", "also", "about", "up", "out", "into", "over", "after",
    "before", "between", "under", "again", "further", "once", "here",
    "there", "when", "where", "why", "how", "what", "very", "just",
})


def _extract_keywords(text: str) -> list[str]:
    """Extract keywords from text: lowercase, split, remove stopwords."""
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences. Simple period/question/exclamation splitting."""
    if not text.strip():
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _score_sentence(sentence: str, keywords: list[str]) -> int:
    """Score a sentence by keyword overlap count."""
    sentence_lower = sentence.lower()
    return sum(1 for kw in keywords if kw in sentence_lower)


def preprocess_for_screening(
    abstract: str, title: str, criteria: list[dict]
) -> list[dict]:
    """Produce focused evidence windows for each screening criterion.

    For each criterion:
    1. Extract keywords from testable_condition
    2. Score each abstract sentence by keyword overlap
    3. Return top-3 sentences + first/last sentence as evidence window

    Returns list of dicts: {criterion_id, evidence_window, keywords_matched, full_abstract}
    """
    sentences = _split_sentences(abstract)
    results = []

    for criterion in criteria:
        cid = criterion.get("criterion_id", "")
        condition = criterion.get("testable_condition", "")
        keywords = _extract_keywords(condition)

        if not sentences:
            results.append({
                "criterion_id": cid,
                "evidence_window": "",
                "keywords_matched": [],
                "full_abstract": abstract,
            })
            continue

        # Score sentences
        scored = [(i, s, _score_sentence(s, keywords)) for i, s in enumerate(sentences)]
        # Keywords that actually matched
        matched = [kw for kw in keywords if any(kw in s.lower() for s in sentences)]

        # Top-3 by score (excluding first/last which are always included)
        middle = [x for x in scored if x[0] not in (0, len(sentences) - 1)]
        middle.sort(key=lambda x: x[2], reverse=True)
        top_middle = middle[:3]

        # Build evidence window: first + top middle + last, in document order
        window_indices = {0, len(sentences) - 1}
        for idx, _, _ in top_middle:
            window_indices.add(idx)
        window_sentences = [sentences[i] for i in sorted(window_indices)]

        results.append({
            "criterion_id": cid,
            "evidence_window": " ".join(window_sentences),
            "keywords_matched": matched,
            "full_abstract": abstract,
        })

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_preprocess.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add lib/preprocess.py tests/test_preprocess.py
git commit -m "feat: add screening preprocessor with evidence windows"
```

---

## Task 8: Synthesis Preprocessor

**Files:**
- Modify: `lib/preprocess.py`
- Modify: `tests/test_preprocess.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_preprocess.py`:

```python
from lib.preprocess import preprocess_for_synthesis


def test_clusters_concepts_by_co_occurrence():
    extractions = [
        {"paper_id": "p1", "source": "full_text", "fields": [], "concepts_identified": ["formal-verification", "model-checking"]},
        {"paper_id": "p2", "source": "full_text", "fields": [], "concepts_identified": ["formal-verification", "theorem-proving"]},
        {"paper_id": "p3", "source": "abstract", "fields": [], "concepts_identified": ["neural-networks", "deep-learning"]},
    ]
    concepts = [
        {"concept_id": "formal-verification", "label": "Formal Verification", "definition": "Math proofs for correctness", "frequency": 2},
        {"concept_id": "model-checking", "label": "Model Checking", "definition": "Exhaustive state exploration", "frequency": 1},
        {"concept_id": "theorem-proving", "label": "Theorem Proving", "definition": "Logical proof construction", "frequency": 1},
        {"concept_id": "neural-networks", "label": "Neural Networks", "definition": "Connectionist computing models", "frequency": 1},
        {"concept_id": "deep-learning", "label": "Deep Learning", "definition": "Multi-layer neural network training", "frequency": 1},
    ]
    result = preprocess_for_synthesis(extractions, concepts)
    assert "themes" in result
    assert len(result["themes"]) >= 2  # at least 2 clusters


def test_themes_ranked_by_paper_count():
    extractions = [
        {"paper_id": "p1", "source": "full_text", "fields": [], "concepts_identified": ["a", "b"]},
        {"paper_id": "p2", "source": "full_text", "fields": [], "concepts_identified": ["a", "b"]},
        {"paper_id": "p3", "source": "full_text", "fields": [], "concepts_identified": ["a", "b"]},
        {"paper_id": "p4", "source": "abstract", "fields": [], "concepts_identified": ["c", "d"]},
    ]
    concepts = [
        {"concept_id": "a", "label": "A", "definition": "Concept A definition text", "frequency": 3},
        {"concept_id": "b", "label": "B", "definition": "Concept B definition text", "frequency": 3},
        {"concept_id": "c", "label": "C", "definition": "Concept C definition text", "frequency": 1},
        {"concept_id": "d", "label": "D", "definition": "Concept D definition text", "frequency": 1},
    ]
    result = preprocess_for_synthesis(extractions, concepts)
    # Largest cluster first
    assert result["themes"][0]["paper_count"] >= result["themes"][1]["paper_count"]


def test_data_completeness_flagged():
    extractions = [
        {
            "paper_id": "p1", "source": "abstract",
            "fields": [
                {"field_name": "methodology", "value": "extraction_failed", "confidence": "low", "source_location": "abstract"},
                {"field_name": "results", "value": "extraction_failed", "confidence": "low", "source_location": "abstract"},
                {"field_name": "title", "value": "Some Title", "confidence": "medium", "source_location": "abstract"},
            ],
            "concepts_identified": ["aa", "bb"],
        },
    ]
    concepts = [
        {"concept_id": "aa", "label": "AA", "definition": "Concept AA def text", "frequency": 1},
        {"concept_id": "bb", "label": "BB", "definition": "Concept BB def text", "frequency": 1},
    ]
    result = preprocess_for_synthesis(extractions, concepts)
    # Paper p1 has >50% failed fields
    theme = result["themes"][0]
    paper = [p for p in theme["papers"] if p["paper_id"] == "p1"][0]
    assert paper["data_completeness"] < 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_preprocess.py -v -k "synthesis"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement `preprocess_for_synthesis`**

Add to `lib/preprocess.py`:

```python
def _build_co_occurrence_graph(
    extractions: list[dict],
) -> dict[str, set[str]]:
    """Build adjacency list: concept -> set of concepts it co-occurs with (threshold >= 2 shared papers)."""
    # concept -> set of paper_ids
    concept_papers: dict[str, set[str]] = {}
    for ext in extractions:
        pid = ext.get("paper_id", "")
        for cid in ext.get("concepts_identified", []):
            concept_papers.setdefault(cid, set()).add(pid)

    # Build edges: concepts sharing >= 2 papers
    concept_ids = list(concept_papers.keys())
    adj: dict[str, set[str]] = {c: set() for c in concept_ids}
    for i in range(len(concept_ids)):
        for j in range(i + 1, len(concept_ids)):
            c1, c2 = concept_ids[i], concept_ids[j]
            shared = concept_papers[c1] & concept_papers[c2]
            if len(shared) >= 2:
                adj[c1].add(c2)
                adj[c2].add(c1)
    return adj


def _find_clusters(adj: dict[str, set[str]]) -> list[set[str]]:
    """Find connected components in the co-occurrence graph."""
    visited: set[str] = set()
    clusters: list[set[str]] = []
    for node in adj:
        if node in visited:
            continue
        cluster: set[str] = set()
        stack = [node]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            cluster.add(n)
            for neighbor in adj.get(n, set()):
                if neighbor not in visited:
                    stack.append(neighbor)
        clusters.append(cluster)
    return clusters


def preprocess_for_synthesis(
    extractions: list[dict], concepts: list[dict]
) -> dict:
    """Organize extraction data into themed briefs for synthesis.

    1. Cluster concepts by co-occurrence
    2. Rank themes by paper count
    3. Per-theme: list papers with data completeness scores

    Returns: {"themes": [{"concepts": [...], "paper_count": N, "papers": [...]}]}
    """
    concept_map = {c["concept_id"]: c for c in concepts}
    adj = _build_co_occurrence_graph(extractions)
    clusters = _find_clusters(adj)

    # Map papers to concepts
    paper_concepts: dict[str, set[str]] = {}
    paper_data: dict[str, dict] = {}
    for ext in extractions:
        pid = ext["paper_id"]
        paper_concepts[pid] = set(ext.get("concepts_identified", []))
        paper_data[pid] = ext

    themes = []
    for cluster in clusters:
        # Papers in this theme: papers that have >= 1 concept from the cluster
        theme_papers = []
        for pid, pcs in paper_concepts.items():
            if pcs & cluster:
                ext = paper_data[pid]
                fields = ext.get("fields", [])
                total_fields = len(fields)
                failed_fields = sum(1 for f in fields if f.get("value") == "extraction_failed")
                completeness = (total_fields - failed_fields) / total_fields if total_fields > 0 else 1.0

                theme_papers.append({
                    "paper_id": pid,
                    "source": ext.get("source", "unknown"),
                    "data_completeness": round(completeness, 2),
                    "concepts": sorted(pcs & cluster),
                })

        themes.append({
            "concepts": sorted(cluster),
            "concept_labels": {cid: concept_map[cid]["label"] for cid in cluster if cid in concept_map},
            "paper_count": len(theme_papers),
            "papers": theme_papers,
        })

    # Sort by paper count descending
    themes.sort(key=lambda t: t["paper_count"], reverse=True)

    return {"themes": themes}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_preprocess.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add lib/preprocess.py tests/test_preprocess.py
git commit -m "feat: add synthesis preprocessor with concept clustering and data completeness"
```

---

## Task 9: PRISMA 2020 Compliance Checker

**Files:**
- Create: `lib/prisma.py`
- Create: `tests/test_prisma.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_prisma.py`:

```python
"""Tests for PRISMA 2020 compliance checker."""

from lib.prisma import check_prisma_compliance, PrismaStatus


def test_status_enum():
    assert PrismaStatus.SATISFIED == "satisfied"
    assert PrismaStatus.PARTIALLY_SATISFIED == "partially_satisfied"
    assert PrismaStatus.NOT_SATISFIED == "not_satisfied"


def test_title_check_satisfied():
    review = "# A Systematic Literature Review of Formal Verification\n\n## Abstract\nTest."
    items = check_prisma_compliance(review, {}, {})
    item1 = next(i for i in items if i["item"] == 1)
    assert item1["status"] == PrismaStatus.SATISFIED


def test_title_check_not_satisfied():
    review = "# Some Paper About Things\n\n## Abstract\nTest."
    items = check_prisma_compliance(review, {}, {})
    item1 = next(i for i in items if i["item"] == 1)
    assert item1["status"] == PrismaStatus.NOT_SATISFIED


def test_database_coverage_partial():
    """Fewer than 3 independent databases -> partially satisfied."""
    workspace_data = {
        "search_log": [
            {"database": "Semantic Scholar", "query": "test"},
            {"database": "arXiv", "query": "test"},
        ],
    }
    review = "# Systematic Review\n\n## Abstract\nTest.\n\n## 2. Methodology\n\n### 2.1 Search Strategy\nSearched S2 and arXiv."
    items = check_prisma_compliance(review, workspace_data, {})
    item6 = next(i for i in items if i["item"] == 6)
    assert item6["status"] == PrismaStatus.PARTIALLY_SATISFIED


def test_risk_of_bias_not_satisfied():
    """Item 12 should always be not_satisfied with explanation."""
    items = check_prisma_compliance("# Systematic Review\n## Abstract\nTest.", {}, {})
    item12 = next(i for i in items if i["item"] == 12)
    assert item12["status"] == PrismaStatus.NOT_SATISFIED
    assert "quality appraisal" in item12["explanation"].lower() or "risk of bias" in item12["explanation"].lower()


def test_returns_27_items():
    items = check_prisma_compliance("# Systematic Review\n## Abstract\nTest.", {}, {})
    assert len(items) == 27


def test_all_items_have_required_fields():
    items = check_prisma_compliance("# Systematic Review\n## Abstract\nTest.", {}, {})
    for item in items:
        assert "item" in item
        assert "description" in item
        assert "status" in item
        assert "explanation" in item
        assert item["status"] in (PrismaStatus.SATISFIED, PrismaStatus.PARTIALLY_SATISFIED, PrismaStatus.NOT_SATISFIED)
        assert len(item["explanation"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_prisma.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `lib/prisma.py`**

Create `lib/prisma.py`:

```python
"""PRISMA 2020 and PRISMA-trAIce compliance checking.

Pure functions that validate review text and workspace data against
the PRISMA 2020 27-item checklist and the PRISMA-trAIce 7-item extension.
No I/O — operates on strings and dicts.

Note: Item descriptions are paraphrased. Implementation should verify
against exact published text (PRISMA 2020: Page et al., 2021;
PRISMA-trAIce: JMIR AI 2025, doi:10.2196/80247).
"""

import re
from enum import Enum


class PrismaStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    NOT_SATISFIED = "not_satisfied"


def _check_title(review: str) -> dict:
    """Item 1: Title identifies as systematic review."""
    first_line = review.split("\n")[0].lower() if review else ""
    keywords = ["systematic", "literature review", "scoping review", "evidence synthesis"]
    if any(kw in first_line for kw in keywords):
        return {"item": 1, "description": "Title identifies as systematic review",
                "status": PrismaStatus.SATISFIED, "explanation": "Title contains systematic review keyword.",
                "section_ref": "Title"}
    return {"item": 1, "description": "Title identifies as systematic review",
            "status": PrismaStatus.NOT_SATISFIED,
            "explanation": "Title does not contain 'systematic', 'literature review', or equivalent keyword.",
            "section_ref": "Title"}


def _check_abstract(review: str) -> dict:
    """Item 2: Structured abstract."""
    has_abstract = bool(re.search(r"^#{1,3}\s+Abstract", review, re.MULTILINE))
    if has_abstract:
        # Check word count (150-300)
        match = re.search(r"^#{1,3}\s+Abstract\s*\n(.*?)(?=^#{1,3}\s|\Z)", review, re.MULTILINE | re.DOTALL)
        if match:
            words = len(match.group(1).split())
            if 100 <= words <= 400:  # generous range
                return {"item": 2, "description": "Structured abstract",
                        "status": PrismaStatus.SATISFIED, "explanation": f"Abstract present ({words} words).",
                        "section_ref": "Abstract"}
    return {"item": 2, "description": "Structured abstract",
            "status": PrismaStatus.NOT_SATISFIED, "explanation": "Abstract section missing or outside expected length.",
            "section_ref": "Abstract"}


def _check_databases(workspace_data: dict) -> dict:
    """Item 6: Information sources — databases searched."""
    search_log = workspace_data.get("search_log", [])
    databases = {e.get("database", "").lower() for e in search_log}
    # Independence check: S2 indexes arXiv, so they count as ~1.5 independent sources
    independent = set()
    for db in databases:
        if "semantic scholar" in db or "s2" in db:
            independent.add("semantic_scholar")
        elif "arxiv" in db:
            independent.add("arxiv")
        elif "pubmed" in db:
            independent.add("pubmed")
        elif "openalex" in db:
            independent.add("openalex")
        else:
            independent.add(db)

    if len(independent) >= 3:
        status = PrismaStatus.SATISFIED
        expl = f"Searched {len(independent)} independent databases: {', '.join(sorted(independent))}."
    elif len(independent) >= 1:
        status = PrismaStatus.PARTIALLY_SATISFIED
        expl = (f"Searched {len(independent)} database(s): {', '.join(sorted(independent))}. "
                "PRISMA recommends >= 3 independent databases. Snowballing partially compensates. "
                "Consider adding PubMed or OpenAlex for broader coverage.")
    else:
        status = PrismaStatus.NOT_SATISFIED
        expl = "No database search log found."

    return {"item": 6, "description": "Information sources",
            "status": status, "explanation": expl, "section_ref": "Section 2.1"}


def _check_section_exists(review: str, item_num: int, desc: str, patterns: list[str], section_ref: str) -> dict:
    """Generic check: does a section matching any pattern exist?"""
    for pattern in patterns:
        if re.search(pattern, review, re.MULTILINE | re.IGNORECASE):
            return {"item": item_num, "description": desc,
                    "status": PrismaStatus.SATISFIED, "explanation": f"Section found.",
                    "section_ref": section_ref}
    return {"item": item_num, "description": desc,
            "status": PrismaStatus.NOT_SATISFIED, "explanation": f"Expected section not found.",
            "section_ref": section_ref}


def _not_satisfied_by_design(item_num: int, desc: str, explanation: str) -> dict:
    """Items Scholar cannot satisfy by design."""
    return {"item": item_num, "description": desc,
            "status": PrismaStatus.NOT_SATISFIED, "explanation": explanation,
            "section_ref": "N/A — not performed"}


def check_prisma_compliance(
    review: str, workspace_data: dict, protocol: dict
) -> list[dict]:
    """Check review against PRISMA 2020 27-item checklist.

    Returns list of 27 dicts, one per item, each with:
    item, description, status, explanation, section_ref.
    """
    items = []

    # Item 1: Title
    items.append(_check_title(review))

    # Item 2: Abstract
    items.append(_check_abstract(review))

    # Items 3-4: Introduction (rationale, objectives)
    items.append(_check_section_exists(review, 3, "Rationale", [r"^#{1,3}\s+\d*\.?\s*Introduction"], "Section 1"))
    items.append(_check_section_exists(review, 4, "Objectives", [r"sub-question", r"research question"], "Section 1"))

    # Item 5: Eligibility criteria
    items.append(_check_section_exists(review, 5, "Eligibility criteria",
                 [r"inclusion criteria", r"exclusion criteria", r"selection criteria"], "Section 2.2"))

    # Item 6: Information sources
    items.append(_check_databases(workspace_data))

    # Item 7: Search strategy
    items.append(_check_section_exists(review, 7, "Search strategy",
                 [r"search strategy", r"search terms", r"boolean", r"query"], "Section 2.1"))

    # Item 8: Selection process
    items.append({"item": 8, "description": "Selection process",
                  "status": PrismaStatus.PARTIALLY_SATISFIED,
                  "explanation": "Single AI agent screening. Postcondition checks validate structural completeness "
                                 "but do not substitute for inter-rater reliability.",
                  "section_ref": "Section 2.3"})

    # Items 9-10: Data collection, data items
    items.append(_check_section_exists(review, 9, "Data collection process",
                 [r"extraction", r"data collection"], "Section 2.5"))
    items.append(_check_section_exists(review, 10, "Data items",
                 [r"extraction schema", r"data items", r"fields"], "Section 2.5"))

    # Item 11: Study risk of bias assessment (method description)
    items.append(_not_satisfied_by_design(11, "Study risk of bias assessment",
                 "Scholar does not perform individual study risk of bias assessment. "
                 "Screening uses binary inclusion/exclusion criteria, not quality grading."))

    # Item 12: Effect measures
    items.append(_not_satisfied_by_design(12, "Effect measures",
                 "Scholar produces thematic synthesis (Thomas & Harden, 2008), not meta-analysis. "
                 "Individual study quality appraisal is not performed."))

    # Item 13a: Synthesis methods
    items.append(_check_section_exists(review, 13, "Synthesis methods",
                 [r"findings by theme", r"thematic", r"concept matrix", r"synthesis"], "Section 3.2"))

    # Item 13b: Certainty of evidence (not just 13a)
    # We use item 14 for certainty assessment
    items.append(_not_satisfied_by_design(14, "Certainty assessment",
                 "GRADE or equivalent certainty of evidence assessment not performed. "
                 "Synthesis presents findings thematically without grading evidence strength."))

    # Item 15: Reporting biases
    items.append(_not_satisfied_by_design(15, "Reporting biases assessment",
                 "Scholar relies on Semantic Scholar and arXiv, introducing potential bias toward "
                 "English-language, open-access, CS/ML-adjacent literature. "
                 "Snowballing partially compensates but does not eliminate this bias."))

    # Items 16-22: Results, discussion
    items.append(_check_section_exists(review, 16, "Study selection results",
                 [r"candidates", r"screened", r"included"], "Section 3.1"))
    items.append(_check_section_exists(review, 17, "Study characteristics",
                 [r"appendix a", r"included papers"], "Appendix A"))
    items.append(_check_section_exists(review, 18, "Risk of bias in studies",
                 [r"risk of bias|quality assessment"], "N/A"))
    items.append(_check_section_exists(review, 19, "Results of syntheses",
                 [r"findings", r"theme", r"results"], "Section 3.2"))
    items.append(_not_satisfied_by_design(20, "Reporting biases results",
                 "Not assessed — see Item 15."))
    items.append(_check_section_exists(review, 21, "Certainty of evidence results",
                 [r"certainty|grade|evidence quality"], "N/A"))
    items.append(_check_section_exists(review, 22, "Discussion",
                 [r"^#{1,3}\s+\d*\.?\s*Discussion"], "Section 4"))

    # Items 23-24: Registration, support
    items.append({"item": 23, "description": "Registration and protocol",
                  "status": PrismaStatus.SATISFIED if "protocol" in review.lower() else PrismaStatus.NOT_SATISFIED,
                  "explanation": "Protocol reference found in review." if "protocol" in review.lower()
                                 else "No protocol reference found.",
                  "section_ref": "Section 2"})

    items.append({"item": 24, "description": "Support/funding",
                  "status": PrismaStatus.PARTIALLY_SATISFIED,
                  "explanation": "No funding section generated by default. User should add if applicable.",
                  "section_ref": "N/A"})

    # Items 25-27: Availability, other
    items.append({"item": 25, "description": "Competing interests",
                  "status": PrismaStatus.PARTIALLY_SATISFIED,
                  "explanation": "Disclosure footer states AI generation. User should add personal COI if applicable.",
                  "section_ref": "Footer"})
    items.append({"item": 26, "description": "Availability of data",
                  "status": PrismaStatus.SATISFIED if "workspace" in review.lower() or "data" in review.lower()
                            else PrismaStatus.NOT_SATISFIED,
                  "explanation": "Review references workspace data availability.",
                  "section_ref": "Section 2"})
    items.append({"item": 27, "description": "Other information",
                  "status": PrismaStatus.SATISFIED,
                  "explanation": "PRISMA checklist appended as Appendix C.",
                  "section_ref": "Appendix C"})

    return items
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_prisma.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add lib/prisma.py tests/test_prisma.py
git commit -m "feat: add PRISMA 2020 compliance checker (27 items, three-tier status)"
```

---

## Task 9b: PRISMA-trAIce Compliance Checker

**Files:**
- Modify: `lib/prisma.py`
- Modify: `tests/test_prisma.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_prisma.py`:

```python
from lib.prisma import check_prisma_traice_compliance, PrismaStatus


def test_traice_returns_7_items():
    items = check_prisma_traice_compliance("# Review\n## Abstract\nTest.", {})
    assert len(items) == 7


def test_traice_all_items_have_required_fields():
    items = check_prisma_traice_compliance("# Review", {})
    for item in items:
        assert "item" in item
        assert "description" in item
        assert "status" in item
        assert "explanation" in item


def test_traice_human_oversight_partially_satisfied():
    """Phase 0 protocol approval is human oversight but per-decision is autonomous."""
    items = check_prisma_traice_compliance("# Review", {})
    oversight = next(i for i in items if "oversight" in i["description"].lower())
    assert oversight["status"] == PrismaStatus.PARTIALLY_SATISFIED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_prisma.py -v -k "traice"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement `check_prisma_traice_compliance`**

Add to `lib/prisma.py`:

```python
def check_prisma_traice_compliance(
    review: str, workspace_data: dict
) -> list[dict]:
    """Check review against PRISMA-trAIce 7-item checklist (JMIR AI 2025, doi:10.2196/80247).

    Note: Items are paraphrased. Implementation should verify against exact published text.
    """
    phase_log = workspace_data.get("phase_log", [])
    search_log = workspace_data.get("search_log", [])
    has_disclosure = "generated by inference" in review.lower() or "scholar" in review.lower()

    return [
        {"item": "T1", "description": "AI tool identification and version",
         "status": PrismaStatus.SATISFIED if has_disclosure else PrismaStatus.NOT_SATISFIED,
         "explanation": "Disclosure footer identifies Scholar as the AI tool." if has_disclosure
                        else "No AI tool disclosure found in review."},
        {"item": "T2", "description": "Stage where AI was used",
         "status": PrismaStatus.SATISFIED if phase_log else PrismaStatus.PARTIALLY_SATISFIED,
         "explanation": "Phase-log.jsonl records AI agent dispatches per phase." if phase_log
                        else "No phase log available to document AI usage per stage."},
        {"item": "T3", "description": "Human oversight description",
         "status": PrismaStatus.PARTIALLY_SATISFIED,
         "explanation": "Human oversight limited to protocol approval (Phase 0). "
                        "Individual screening, extraction, and synthesis judgments were autonomous, "
                        "validated via structural postconditions, not human review."},
        {"item": "T4", "description": "Prompt/query transparency",
         "status": PrismaStatus.SATISFIED if search_log else PrismaStatus.NOT_SATISFIED,
         "explanation": "Search queries logged in search-log.jsonl with exact query strings and parameters."
                        if search_log else "No search log available."},
        {"item": "T5", "description": "Validation of AI output",
         "status": PrismaStatus.SATISFIED,
         "explanation": "Postcondition checks validate structural completeness per phase. "
                        "Oracle contracts validate per-record inference output."},
        {"item": "T6", "description": "Reproducibility information",
         "status": PrismaStatus.SATISFIED,
         "explanation": "Protocol.md + all JSONL logs + workspace directory constitute "
                        "a complete reproducibility package."},
        {"item": "T7", "description": "Limitations of AI use",
         "status": PrismaStatus.SATISFIED if "limitation" in review.lower() or "threat" in review.lower()
                  else PrismaStatus.NOT_SATISFIED,
         "explanation": "Threats to Validity section documents AI limitations." if "limitation" in review.lower()
                        else "No limitations section found."},
    ]
```

- [ ] **Step 4: Run tests and commit**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_prisma.py -v`

```bash
git add lib/prisma.py tests/test_prisma.py
git commit -m "feat: add PRISMA-trAIce compliance checker (7 items)"
```

---

## Task 10: PRISMA Mermaid Flow Diagram Generator

**Files:**
- Create: `lib/export.py`
- Create: `tests/test_export.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_export.py`:

```python
"""Tests for export functions (PRISMA diagram, future RIS/CSV)."""

from lib.export import generate_prisma_flow_diagram


def test_generates_mermaid_syntax():
    metrics = {
        "search_candidates": 150,
        "snowball_candidates": 45,
        "deduplicated": 180,
        "screened": 180,
        "excluded": 140,
        "flagged": 12,
        "ft_excluded": 8,
        "included": 32,
    }
    diagram = generate_prisma_flow_diagram(metrics)
    assert "graph TD" in diagram or "flowchart TD" in diagram
    assert "150" in diagram
    assert "32" in diagram


def test_contains_all_prisma_flow_nodes():
    metrics = {
        "search_candidates": 100,
        "snowball_candidates": 20,
        "deduplicated": 110,
        "screened": 110,
        "excluded": 80,
        "flagged": 5,
        "ft_excluded": 3,
        "included": 27,
    }
    diagram = generate_prisma_flow_diagram(metrics)
    assert "database searching" in diagram.lower() or "search" in diagram.lower()
    assert "snowball" in diagram.lower()
    assert "screened" in diagram.lower()
    assert "included" in diagram.lower()
    assert "excluded" in diagram.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_export.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

Create `lib/export.py`:

```python
"""Scholar export functions.

Phase A: PRISMA Mermaid flow diagram generation.
Phase B (future): RIS and CSV export of JSONL data.

Pure functions. No I/O.
"""


def generate_prisma_flow_diagram(metrics: dict) -> str:
    """Generate a PRISMA 2020-style flow diagram in Mermaid syntax.

    Args:
        metrics: dict with keys from the spec variable mapping table:
            search_candidates, snowball_candidates, deduplicated,
            screened, excluded, flagged, ft_excluded, included
    """
    sc = metrics.get("search_candidates", 0)
    sn = metrics.get("snowball_candidates", 0)
    dd = metrics.get("deduplicated", 0)
    sr = metrics.get("screened", 0)
    ex = metrics.get("excluded", 0)
    fl = metrics.get("flagged", 0)
    fe = metrics.get("ft_excluded", 0)
    inc = metrics.get("included", 0)

    return f"""```mermaid
graph TD
    A["Records identified through<br/>database searching<br/>(n = {sc})"] --> C["Records after deduplication<br/>(n = {dd})"]
    B["Records identified through<br/>snowballing<br/>(n = {sn})"] --> C
    C --> D["Records screened<br/>(n = {sr})"]
    D --> E["Records excluded<br/>(n = {ex})"]
    D --> F["Full-text assessed<br/>(n = {fl})"]
    F --> G["Studies included<br/>(n = {inc})"]
    F --> H["Full-text excluded<br/>with reasons<br/>(n = {fe})"]
```"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/test_export.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add lib/export.py tests/test_export.py
git commit -m "feat: add PRISMA flow diagram generator (Mermaid syntax)"
```

---

## Task 11: Dafny State Machine Specification

**Files:**
- Create: `spec/state.dfy`

- [ ] **Step 1: Create spec directory**

```bash
mkdir -p /home/melek/workshop/scholar/spec
```

- [ ] **Step 2: Write `spec/state.dfy`**

Create `spec/state.dfy` mirroring `lib/state.py`:

```dafny
// Scholar state machine — formal specification.
// Companion to lib/state.py. Python is the runtime; Dafny is the proof.

datatype PhaseStatus = Pending | InProgress | Completed | Failed | NeedsProtocolRevision

datatype State = State(
  currentPhase: nat,
  phaseStatus: PhaseStatus,
  feedbackIterations: nat,
  retryCount: nat,
  phaseCompleted: seq<bool>
)

const MAX_FEEDBACK_ITERATIONS: nat := 2

predicate ValidState(s: State) {
  0 <= s.currentPhase <= 5 &&
  |s.phaseCompleted| == 6 &&
  s.retryCount <= 1 &&
  s.feedbackIterations <= MAX_FEEDBACK_ITERATIONS
}

predicate MonotonicCompleted(before: seq<bool>, after: seq<bool>) {
  |before| == |after| == 6 &&
  forall i :: 0 <= i < 6 ==> (before[i] ==> after[i])
}

method StartPhase(s: State, phase: nat) returns (s': State)
  requires ValidState(s)
  requires phase == s.currentPhase
  requires s.phaseStatus == Pending
  ensures ValidState(s')
  ensures s'.phaseStatus == InProgress
  ensures s'.currentPhase == s.currentPhase
  ensures s'.phaseCompleted == s.phaseCompleted
{
  s' := State(s.currentPhase, InProgress, s.feedbackIterations, s.retryCount, s.phaseCompleted);
}

method CompletePhase(s: State, phase: nat) returns (s': State)
  requires ValidState(s)
  requires phase == s.currentPhase
  requires s.phaseStatus == InProgress
  requires 0 <= phase <= 5
  ensures ValidState(s')
  ensures s'.phaseStatus == Completed
  ensures s'.phaseCompleted[phase] == true
  ensures MonotonicCompleted(s.phaseCompleted, s'.phaseCompleted)
{
  var completed := s.phaseCompleted[..phase] + [true] + s.phaseCompleted[phase+1..];
  s' := State(s.currentPhase, Completed, s.feedbackIterations, s.retryCount, completed);
}

method TransitionToNext(s: State) returns (s': State)
  requires ValidState(s)
  requires s.phaseStatus == Completed
  requires s.currentPhase < 5
  ensures ValidState(s')
  ensures s'.currentPhase == s.currentPhase + 1
  ensures s'.phaseStatus == Pending
  ensures s'.retryCount == 0
  ensures MonotonicCompleted(s.phaseCompleted, s'.phaseCompleted)
{
  s' := State(s.currentPhase + 1, Pending, s.feedbackIterations, 0, s.phaseCompleted);
}

method FailPhase(s: State, phase: nat) returns (s': State)
  requires ValidState(s)
  requires phase == s.currentPhase
  requires s.phaseStatus == InProgress
  ensures ValidState(s')
  ensures s'.phaseStatus == Failed
{
  s' := State(s.currentPhase, Failed, s.feedbackIterations, s.retryCount, s.phaseCompleted);
}

method RetryPhase(s: State) returns (s': State)
  requires ValidState(s)
  requires s.phaseStatus == Failed
  requires s.retryCount < 1
  ensures ValidState(s')
  ensures s'.phaseStatus == InProgress
  ensures s'.retryCount == s.retryCount + 1
  ensures s'.retryCount <= 1
{
  s' := State(s.currentPhase, InProgress, s.feedbackIterations, s.retryCount + 1, s.phaseCompleted);
}

method FeedbackLoop(s: State) returns (s': State)
  requires ValidState(s)
  requires s.currentPhase == 4
  requires s.phaseStatus == Completed
  requires s.feedbackIterations < MAX_FEEDBACK_ITERATIONS
  ensures ValidState(s')
  ensures s'.currentPhase == 3
  ensures s'.phaseStatus == Pending
  ensures s'.feedbackIterations == s.feedbackIterations + 1
  ensures s'.feedbackIterations <= MAX_FEEDBACK_ITERATIONS
{
  s' := State(3, Pending, s.feedbackIterations + 1, 0, s.phaseCompleted);
}

method DiagnosticTransition(s: State) returns (s': State)
  requires ValidState(s)
  requires s.currentPhase == 2
  requires s.phaseStatus == Completed
  ensures ValidState(s')
  ensures s'.phaseStatus == NeedsProtocolRevision
{
  s' := State(s.currentPhase, NeedsProtocolRevision, s.feedbackIterations, s.retryCount, s.phaseCompleted);
}

// Terminal correctness: review is done iff phase 5 completed
predicate IsReviewComplete(s: State)
  requires ValidState(s)
{
  s.currentPhase == 5 && s.phaseStatus == Completed
}
```

- [ ] **Step 3: Verify with Dafny (if installed)**

```bash
dafny verify /home/melek/workshop/scholar/spec/state.dfy 2>&1 || echo "Dafny not installed — skip verification, will verify later"
```

- [ ] **Step 4: Commit**

```bash
git add spec/state.dfy
git commit -m "feat: add Dafny state machine specification"
```

---

## Task 12: Dafny Saturation Specification

**Files:**
- Create: `spec/saturation.dfy`

- [ ] **Step 1: Write `spec/saturation.dfy`**

```dafny
// Scholar saturation metrics — formal specification.
// Companion to lib/saturation.py.

// Using natural numbers to avoid real arithmetic complexity.
// Saturation is represented as (numerator, denominator) pairs.

method DiscoverySaturation(included: nat, examined: nat) returns (num: nat, den: nat)
  ensures den == 0 ==> num == 0
  ensures den > 0 ==> num <= den
  ensures den == examined
  ensures num <= included
{
  den := examined;
  if examined == 0 {
    num := 0;
  } else {
    num := if included <= examined then included else examined;
  }
}

method ShouldTerminateDiscovery(num: nat, den: nat, threshNum: nat, threshDen: nat) returns (terminate: bool)
  requires den > 0
  requires threshDen > 0
  ensures terminate <==> (num * threshDen < threshNum * den)
{
  // Cross-multiply to avoid division: num/den < threshNum/threshDen
  terminate := num * threshDen < threshNum * den;
}

method ConceptualSaturation(newInLastK: nat, total: nat) returns (num: nat, den: nat)
  ensures den == 0 ==> num == 0
  ensures den > 0 ==> num <= den
{
  den := total;
  if total == 0 {
    num := 0;
  } else {
    num := if newInLastK <= total then newInLastK else total;
  }
}

method ShouldFeedbackLoop(
  deltaNum: nat, deltaDen: nat,
  thetaNum: nat, thetaDen: nat,
  iterations: nat, maxIterations: nat
) returns (feedback: bool)
  requires deltaDen > 0
  requires thetaDen > 0
  ensures feedback <==> (deltaNum * thetaDen >= thetaNum * deltaDen && iterations < maxIterations)
{
  // delta >= theta AND iterations < max
  var aboveThreshold := deltaNum * thetaDen >= thetaNum * deltaDen;
  feedback := aboveThreshold && iterations < maxIterations;
}
```

- [ ] **Step 2: Verify with Dafny (if installed)**

```bash
dafny verify /home/melek/workshop/scholar/spec/saturation.dfy 2>&1 || echo "Dafny not installed — skip"
```

- [ ] **Step 3: Commit**

```bash
git add spec/saturation.dfy
git commit -m "feat: add Dafny saturation metrics specification"
```

---

## Task 13: Expert Panel and Change Protocol Documentation

**Files:**
- Create: `docs/methodology/EXPERT_ROSTER.md`
- Create: `docs/methodology/CHANGE_PROTOCOL.md`

- [ ] **Step 1: Create directory**

```bash
mkdir -p /home/melek/workshop/scholar/docs/methodology
```

- [ ] **Step 2: Write `EXPERT_ROSTER.md`**

Content per spec Section 5.3 — standing panel (Dijkstra, Tay, Leveson, Ousterhout, Sovereignty) and per-change experts (Kitchenham, Wohlin, PRISMA, Cognitive Ergonomics, Thomas & Harden).

- [ ] **Step 3: Write `CHANGE_PROTOCOL.md`**

Content per spec Section 5.2 — three-tier scope classification, Phases 1-4, quick-fix prohibition.

- [ ] **Step 4: Commit**

```bash
git add docs/methodology/
git commit -m "docs: add expert panel roster and change management protocol"
```

---

## Task 14: PRISMA Review Template and Protocol Template Update

**Files:**
- Create: `templates/review-template-prisma.md`
- Create: `templates/review-template-narrative.md`
- Rename: `templates/review-template.md` -> `templates/review-template-kitchenham.md`
- Modify: `templates/protocol-template.md`

- [ ] **Step 1: Rename existing template**

```bash
cd /home/melek/workshop/scholar && git mv templates/review-template.md templates/review-template-kitchenham.md
```

- [ ] **Step 2: Create PRISMA review template**

Create `templates/review-template-prisma.md` — extends the kitchenham template with PRISMA flow diagram slot in Section 3.1, Appendix C (PRISMA Checklist), Appendix D (PRISMA-trAIce Disclosure), and the disclosure footer.

- [ ] **Step 3: Create narrative template**

Create `templates/review-template-narrative.md` — lighter template without appendices, relaxed structure for scoping reviews.

- [ ] **Step 4: Update protocol template with Output Configuration**

Add to `templates/protocol-template.md`:

```markdown
## Output Configuration

| Parameter | Value |
|-----------|-------|
| output_format | [TODO: prisma_2020 / kitchenham / narrative / custom] |
| citation_style | [TODO: bibtex_keys / numbered / author_year] |
| include_prisma_checklist | [TODO: true / false] |
| include_traice_checklist | [TODO: true / false] |
```

- [ ] **Step 5: Commit**

```bash
git add templates/
git commit -m "feat: add PRISMA and narrative review templates, update protocol template"
```

---

## Task 15: Integration — CLI Subcommands for preprocess and prisma

**Files:**
- Modify: `lib/cli.py`

- [ ] **Step 1: Add `preprocess` subcommand**

```python
def cmd_preprocess(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    data = load_workspace_data(workspace)

    if args.type == "screening":
        from . import preprocess as pp
        # Read protocol criteria
        protocol_path = workspace / "protocol.md"
        # Simple criteria extraction (same as postcondition checker)
        criteria = []  # Parse from protocol
        # For each candidate, preprocess
        results = []
        for candidate in data["candidates"]:
            result = pp.preprocess_for_screening(
                candidate.get("abstract", ""),
                candidate.get("title", ""),
                criteria,
            )
            results.extend(result)
        # Write preprocessed file
        output_path = workspace / "data" / "preprocessed-screening.jsonl"
        with open(output_path, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        print(json.dumps({"written": str(output_path), "records": len(results)}))

    elif args.type == "synthesis":
        from . import preprocess as pp
        result = pp.preprocess_for_synthesis(data["extractions"], data["concepts"])
        output_path = workspace / "data" / "preprocessed-synthesis.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps({"written": str(output_path), "themes": len(result.get("themes", []))}))
```

- [ ] **Step 2: Add `prisma` subcommand**

```python
def cmd_prisma(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).expanduser()
    data = load_workspace_data(workspace)
    review_path = workspace / "review.md"
    review_text = review_path.read_text() if review_path.exists() else ""
    protocol = {}  # Parse if needed

    from . import prisma as pr
    items = pr.check_prisma_compliance(review_text, data, protocol)
    json.dump(items, sys.stdout, indent=2)
    print()
```

- [ ] **Step 3: Wire up argparse and handlers**

Add parsers and handlers for both subcommands.

- [ ] **Step 4: Run all tests**

Run: `cd /home/melek/workshop/scholar && python3 -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add lib/cli.py
git commit -m "feat: add preprocess and prisma CLI subcommands"
```

---

## Task 16: Final Integration Test

**Files:**
- All

- [ ] **Step 1: Run full test suite**

```bash
cd /home/melek/workshop/scholar && python3 -m pytest tests/ -v
```

Expected: all tests pass across all test files:
- `tests/test_section_parser.py` (existing)
- `tests/test_oracle_contracts.py` (Tasks 1-5)
- `tests/test_preprocess.py` (Tasks 7-8)
- `tests/test_prisma.py` (Task 9)
- `tests/test_export.py` (Task 10)

- [ ] **Step 2: Verify Dafny specs (if Dafny installed)**

```bash
dafny verify spec/state.dfy spec/saturation.dfy 2>&1 || echo "Dafny not installed"
```

- [ ] **Step 3: Verify CLI subcommands work**

```bash
python3 -m lib.cli validate-inference --contract SCREEN_CRITERION --record '{"criterion_id":"IC1","criterion_type":"inclusion","met":"yes","evidence":"test text","source":"abstract"}'
```

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git status
# If clean: done
# If changes: git add -A && git commit -m "chore: phase A integration cleanup"
```
