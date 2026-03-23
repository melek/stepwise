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
    validator: Callable
    recovery: Callable[[dict, list[str]], dict]
    validator_kwargs: dict = field(default_factory=dict)


def _recover_screen_criterion(record: dict, failures: list[str]) -> dict:
    return {
        **record,
        "met": "unclear",
        "evidence": f"validation_failed: {'; '.join(failures)}",
        "recovery_applied": True,
    }


def _recover_screen_decision(record: dict, failures: list[str]) -> dict:
    return {
        **record,
        "decision": "exclude",
        "reasoning": f"decision_rule_violation: {'; '.join(failures)}",
        "recovery_applied": True,
    }


def _recover_extraction_field(record: dict, failures: list[str]) -> dict:
    return {
        **record,
        "value": "extraction_failed",
        "confidence": "low",
        "recovery_applied": True,
    }


def _recover_concept(record: dict, failures: list[str]) -> dict:
    return None


def _no_recovery(record: dict, failures: list[str]) -> dict:
    return {**record, "recovery_applied": True}


SCREEN_CRITERION = OracleContract(
    contract_id="SCREEN_CRITERION",
    validator=pc.validate_screening_criterion,
    recovery=_recover_screen_criterion,
)

SCREEN_DECISION = OracleContract(
    contract_id="SCREEN_DECISION",
    validator=pc.validate_screening_decision,
    recovery=_recover_screen_decision,
)

EXTRACT_FIELD = OracleContract(
    contract_id="EXTRACT_FIELD",
    validator=pc.validate_extraction_field,
    recovery=_recover_extraction_field,
    validator_kwargs={"parent_source": "full_text"},
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
        "record": validated or recovered record (with _validated_by provenance),
        "validation": {contract_id, timestamp, satisfied, failures, recovery_applied}
    }
    """
    all_kwargs = {**contract.validator_kwargs, **kwargs}
    satisfied, failures = contract.validator(record, **all_kwargs)

    if satisfied:
        result_record = dict(record)
    else:
        result_record = contract.recovery(record, failures)

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
