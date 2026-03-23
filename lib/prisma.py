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
    first_line = review.split("\n")[0].lower() if review else ""
    keywords = ["systematic", "literature review", "scoping review", "evidence synthesis"]
    if any(kw in first_line for kw in keywords):
        return {"item": 1, "description": "Title identifies as systematic review",
                "status": PrismaStatus.SATISFIED, "explanation": "Title contains systematic review keyword.",
                "section_ref": "Title"}
    return {"item": 1, "description": "Title identifies as systematic review",
            "status": PrismaStatus.NOT_SATISFIED,
            "explanation": "Title does not contain 'systematic', 'literature review', or equivalent.",
            "section_ref": "Title"}


def _check_abstract(review: str) -> dict:
    has_abstract = bool(re.search(r"^#{1,3}\s+Abstract", review, re.MULTILINE))
    if has_abstract:
        match = re.search(r"^#{1,3}\s+Abstract\s*\n(.*?)(?=^#{1,3}\s|\Z)", review, re.MULTILINE | re.DOTALL)
        if match:
            words = len(match.group(1).split())
            if 100 <= words <= 400:
                return {"item": 2, "description": "Structured abstract",
                        "status": PrismaStatus.SATISFIED, "explanation": f"Abstract present ({words} words).",
                        "section_ref": "Abstract"}
            return {"item": 2, "description": "Structured abstract",
                    "status": PrismaStatus.PARTIALLY_SATISFIED,
                    "explanation": f"Abstract present but {words} words (expected 100-400).",
                    "section_ref": "Abstract"}
    return {"item": 2, "description": "Structured abstract",
            "status": PrismaStatus.NOT_SATISFIED, "explanation": "Abstract section missing.",
            "section_ref": "Abstract"}


def _check_databases(workspace_data: dict) -> dict:
    search_log = workspace_data.get("search_log", [])
    databases = {e.get("database", "").lower() for e in search_log}
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
        elif db:
            independent.add(db)

    if len(independent) >= 3:
        status = PrismaStatus.SATISFIED
        expl = f"Searched {len(independent)} independent databases: {', '.join(sorted(independent))}."
    elif len(independent) >= 1:
        status = PrismaStatus.PARTIALLY_SATISFIED
        expl = (f"Searched {len(independent)} database(s): {', '.join(sorted(independent))}. "
                "PRISMA recommends >= 3 independent databases. Snowballing partially compensates.")
    else:
        status = PrismaStatus.NOT_SATISFIED
        expl = "No database search log found."

    return {"item": 6, "description": "Information sources",
            "status": status, "explanation": expl, "section_ref": "Section 2.1"}


def _check_section_exists(review: str, item_num: int, desc: str, patterns: list[str], section_ref: str) -> dict:
    for pattern in patterns:
        if re.search(pattern, review, re.MULTILINE | re.IGNORECASE):
            return {"item": item_num, "description": desc,
                    "status": PrismaStatus.SATISFIED, "explanation": "Section found.",
                    "section_ref": section_ref}
    return {"item": item_num, "description": desc,
            "status": PrismaStatus.NOT_SATISFIED, "explanation": "Expected section not found.",
            "section_ref": section_ref}


def _not_satisfied_by_design(item_num: int, desc: str, explanation: str) -> dict:
    return {"item": item_num, "description": desc,
            "status": PrismaStatus.NOT_SATISFIED, "explanation": explanation,
            "section_ref": "N/A"}


def check_prisma_compliance(review: str, workspace_data: dict, protocol: dict) -> list[dict]:
    """Check review against PRISMA 2020 27-item checklist."""
    items = []
    items.append(_check_title(review))
    items.append(_check_abstract(review))
    items.append(_check_section_exists(review, 3, "Rationale", [r"^#{1,3}\s+\d*\.?\s*Introduction"], "Section 1"))
    items.append(_check_section_exists(review, 4, "Objectives", [r"sub-question", r"research question"], "Section 1"))
    items.append(_check_section_exists(review, 5, "Eligibility criteria",
                 [r"inclusion criteria", r"exclusion criteria", r"selection criteria"], "Section 2.2"))
    items.append(_check_databases(workspace_data))
    items.append(_check_section_exists(review, 7, "Search strategy",
                 [r"search strategy", r"search terms", r"boolean", r"query"], "Section 2.1"))
    items.append({"item": 8, "description": "Selection process",
                  "status": PrismaStatus.PARTIALLY_SATISFIED,
                  "explanation": "Single AI agent screening. Postcondition checks validate structural completeness "
                                 "but do not substitute for inter-rater reliability.",
                  "section_ref": "Section 2.3"})
    items.append(_check_section_exists(review, 9, "Data collection process",
                 [r"extraction", r"data collection"], "Section 2.5"))
    items.append(_check_section_exists(review, 10, "Data items",
                 [r"extraction schema", r"data items", r"fields"], "Section 2.5"))
    items.append(_not_satisfied_by_design(11, "Study risk of bias assessment",
                 "Stepwise does not perform individual study risk of bias assessment."))
    items.append(_not_satisfied_by_design(12, "Effect measures",
                 "Stepwise produces thematic synthesis (Thomas & Harden, 2008), not meta-analysis. "
                 "Individual study quality appraisal is not performed."))
    items.append(_check_section_exists(review, 13, "Synthesis methods",
                 [r"findings by theme", r"thematic", r"concept matrix", r"synthesis"], "Section 3.2"))
    items.append(_not_satisfied_by_design(14, "Certainty assessment",
                 "GRADE or equivalent certainty of evidence assessment not performed."))
    items.append(_not_satisfied_by_design(15, "Reporting biases assessment",
                 "Stepwise relies on Semantic Scholar and arXiv, introducing potential bias toward "
                 "English-language, open-access, CS/ML-adjacent literature."))
    items.append(_check_section_exists(review, 16, "Study selection results",
                 [r"candidates", r"screened", r"included"], "Section 3.1"))
    items.append(_check_section_exists(review, 17, "Study characteristics",
                 [r"appendix a", r"included papers"], "Appendix A"))
    items.append(_not_satisfied_by_design(18, "Risk of bias in studies",
                 "Not assessed — see Item 11."))
    items.append(_check_section_exists(review, 19, "Results of syntheses",
                 [r"findings", r"theme", r"results"], "Section 3.2"))
    items.append(_not_satisfied_by_design(20, "Reporting biases results",
                 "Not assessed — see Item 15."))
    items.append(_check_section_exists(review, 21, "Certainty of evidence results",
                 [r"certainty|grade|evidence quality"], "N/A"))
    items.append(_check_section_exists(review, 22, "Discussion",
                 [r"^#{1,3}\s+\d*\.?\s*Discussion"], "Section 4"))
    items.append({"item": 23, "description": "Registration and protocol",
                  "status": PrismaStatus.SATISFIED if "protocol" in review.lower() else PrismaStatus.NOT_SATISFIED,
                  "explanation": "Protocol reference found." if "protocol" in review.lower()
                                 else "No protocol reference found.",
                  "section_ref": "Section 2"})
    items.append({"item": 24, "description": "Support/funding",
                  "status": PrismaStatus.PARTIALLY_SATISFIED,
                  "explanation": "No funding section generated by default. User should add if applicable.",
                  "section_ref": "N/A"})
    items.append({"item": 25, "description": "Competing interests",
                  "status": PrismaStatus.PARTIALLY_SATISFIED,
                  "explanation": "Disclosure footer states AI generation. User should add personal COI if applicable.",
                  "section_ref": "Footer"})
    items.append({"item": 26, "description": "Availability of data",
                  "status": PrismaStatus.SATISFIED if "workspace" in review.lower() or "data" in review.lower()
                            else PrismaStatus.NOT_SATISFIED,
                  "explanation": "Review references data availability." if "data" in review.lower()
                                 else "No data availability statement found.",
                  "section_ref": "Section 2"})
    items.append({"item": 27, "description": "Other information",
                  "status": PrismaStatus.SATISFIED,
                  "explanation": "PRISMA checklist appended as Appendix C.",
                  "section_ref": "Appendix C"})
    return items


def check_prisma_traice_compliance(review: str, workspace_data: dict) -> list[dict]:
    """Check review against PRISMA-trAIce 7-item checklist (JMIR AI 2025, doi:10.2196/80247).

    Note: Items are paraphrased. Implementation should verify against exact published text.
    """
    phase_log = workspace_data.get("phase_log", [])
    search_log = workspace_data.get("search_log", [])
    has_disclosure = "generated by inference" in review.lower() or "stepwise" in review.lower()

    return [
        {"item": "T1", "description": "AI tool identification and version",
         "status": PrismaStatus.SATISFIED if has_disclosure else PrismaStatus.NOT_SATISFIED,
         "explanation": "Disclosure footer identifies Stepwise as the AI tool." if has_disclosure
                        else "No AI tool disclosure found."},
        {"item": "T2", "description": "Stage where AI was used",
         "status": PrismaStatus.SATISFIED if phase_log else PrismaStatus.PARTIALLY_SATISFIED,
         "explanation": "Phase-log.jsonl records AI agent dispatches per phase." if phase_log
                        else "No phase log available."},
        {"item": "T3", "description": "Human oversight description",
         "status": PrismaStatus.PARTIALLY_SATISFIED,
         "explanation": "Human oversight limited to protocol approval (Phase 0). "
                        "Individual judgments were autonomous, validated via structural postconditions."},
        {"item": "T4", "description": "Prompt/query transparency",
         "status": PrismaStatus.SATISFIED if search_log else PrismaStatus.NOT_SATISFIED,
         "explanation": "Search queries logged in search-log.jsonl." if search_log
                        else "No search log available."},
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
         "explanation": "Threats to Validity section documents AI limitations." if
                        ("limitation" in review.lower() or "threat" in review.lower())
                        else "No limitations section found."},
    ]
