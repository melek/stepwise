# Scholar Hardening Design: Full Stack Verification + Capability Expansion

*Version 1.1 — 2026-03-22*

---

## 0. Purpose

This document specifies hardening changes to Scholar, an autonomous systematic literature review tool implemented as a Claude Code plugin. The changes apply the verified methodology from the UIDI/Atelier/Proven workspace to Scholar's runtime, and expand Scholar's data sources based on competitive landscape analysis.

The design is organized in two phases:

- **Phase A (Internal Hardening):** OracleContracts, deterministic preprocessing, PRISMA-compliant output, Dafny-verified state machine, expert panel governance.
- **Phase B (Capability Expansion):** PubMed MCP, Scite MCP, paper-search-mcp, citation hallucination detection, RIS/CSV export.

Phase A strengthens the guarantees Scholar already claims. Phase B closes capability gaps identified in the competitive survey.

### Governing Constraints

Two cross-cutting concerns govern every section:

1. **Tay's recall constraint.** Boolean search + snowballing has known recall limitations vs. semantic search. Every design decision must not reduce recall, and Phase B must actively improve it. (Source: Cochrane comparison study, Lau 2025 — Elicit sensitivity 39.5%; Aaron Tay's "Deep Research, Shallow Agency" critique.)

2. **Human readability.** PRISMA compliance serves the methodology; readability serves the reader. Both are required. The output must be accessible to a researcher encountering the review for the first time, not just to systematic review methodologists.

### Design Principles (inherited from workspace)

- **A1 (Deterministic-first):** Process logic contains zero inference. Content generation is quarantined behind validation gates.
- **A3 (Auditability):** Every decision is recorded. Records are append-only.
- **A4 (Atomicity / Cold-pickupability):** Workspace is complete state. Any agent can resume from the workspace alone.
- **A6 (Sovereignty):** All data local. Cloud APIs for discovery only.
- **A11 (Verifiability):** Every module classifiable as statically verifiable, runtime-monitored, or integration-tested.

---

## 1. OracleContracts for Inference Calls

### 1.0 Axiom Impact

- **Strengthens A1:** Inference quarantine becomes runtime-enforced via contracts, not just runbook convention.
- **Preserves A3:** Recovery actions produce visible markers in append-only logs, not silent skips.
- **Enables A11:** Each inference point is now classifiable as "runtime-monitored" with a named contract.

### 1.1 Problem

Scholar has 4 inference points: screening (Phase 2/3), extraction (Phase 4), concept identification (Phase 4), and synthesis (Phase 5). The runbooks describe inference quarantine as convention — "log evidence," "record confidence" — but there is no runtime enforcement. A sub-agent could skip logging or return malformed judgments, and the postcondition checker would not catch it until the phase ends.

### 1.2 Design

Create per-record validation functions in `lib/postconditions.py` as atomic validators. A new `lib/oracle_contracts.py` imports these validators and adds: contract identity, recovery strategy, and provenance metadata. No redundant logic — the phase-level checks in `postconditions.py` compose over the same atomic validators.

### 1.3 Contract Definitions

#### SCREEN_CRITERION

Validates a single criterion evaluation within a screening record. **Applies to both Phase 2 (screening) and Phase 3 (snowballing) — the snowball agent performs the same criterion-based assessment and must satisfy the same contracts.**

**Postconditions:**
- `met` in {yes, no, unclear}
- `evidence` is non-empty string
- `source` in {abstract, full_text}
- `criterion_id` matches pattern `^[IE]C\d+$`
- `criterion_type` in {inclusion, exclusion}

**Recovery:** On failure, set `met=unclear`, `evidence="validation_failed: {reason}"`. Paper proceeds to full-text review path.

#### SCREEN_DECISION

Validates a complete screening decision record. **Applies to both Phase 2 and Phase 3.**

**Postconditions:**
- `decision` in {include, exclude, flag_for_full_text}
- `criteria_evaluations` is non-empty list
- `reasoning` is non-empty string
- **Biconditional decision rule (per decision type):**
  - If `decision=include`: all IC have `met=yes` AND no EC has `met=yes`
  - If `decision=exclude`: at least one EC has `met=yes` OR at least one IC has `met=no`
  - If `decision=flag_for_full_text`: at least one criterion has `met=unclear` AND no EC has `met=yes`

**Recovery:** On biconditional violation, reject the decision. Agent must re-evaluate. If re-evaluation also fails, exclude with `reasoning="decision_rule_violation"`.

#### EXTRACT_FIELD

Validates a single field extraction.

**Postconditions:**
- `field_name` is non-empty string
- `value` is non-empty string or equals "extraction_failed"
- `confidence` in {high, medium, low}
- `source_location` is non-empty string
- **Confidence-source biconditional:**
  - If parent record `source=abstract`: `confidence != high` (abstract lacks sufficient detail for high confidence)
  - If parent record `source=full_text`: `confidence` may be any of {high, medium, low} (full text can support high confidence)

**Recovery:** On failure, set `value="extraction_failed"`, `confidence=low`, `recovery_applied=true`.

#### IDENTIFY_CONCEPTS

Validates a concept identification.

**Postconditions:**
- `concept_id` matches pattern `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (minimum 2 characters; single-character concepts are rejected as too ambiguous)
- `label` is non-empty string
- `definition` is non-empty string with length >= 10
- `frequency` >= 1

**Recovery:** On failure, skip concept. Log to phase-log.jsonl with event type `concept_validation_failed`.

#### SYNTHESIZE_CLAIM

Validates synthesis output integrity.

**Postconditions:**
- Every paragraph in Findings by Theme (review.md Section 3.2) contains >= 1 `[@key]` citation
- No `[@key]` references a bibtex_key absent from included papers
- Papers where > 50% of extraction fields have `value="extraction_failed"` are not cited in body text without a qualification marker (e.g., "[limited data]") — they may appear in Appendix A without qualification

**Recovery:** Flag non-compliant paragraphs. The synthesis agent appends qualification markers or moves citations to Appendix A. Not a full retry.

### 1.4 Downstream Propagation Model

Each recovery action writes a `recovery_applied: true` flag on the affected record. Downstream consumers check this flag:

| Recovery Point | Flag Location | Downstream Consumer | Required Behavior |
|---------------|--------------|--------------------|--------------------|
| SCREEN_CRITERION failure | screening-log entry | Screen agent decision rule | Criterion treated as `unclear`, triggers full-text review |
| EXTRACT_FIELD failure | extraction field entry | Synthesis agent | Paper cited only with qualification if >50% fields failed |
| IDENTIFY_CONCEPTS failure | phase-log event | Concept matrix builder | Missing concept not included in matrix |
| SYNTHESIZE_CLAIM failure | review.md inline marker | Human reader | Qualification visible in text |

### 1.5 CLI Integration

New CLI subcommand:

```bash
python3 lib/cli.py validate-inference --contract SCREEN_DECISION --record '{"decision":"include",...}' --workspace ~/research/my-project/
python3 lib/cli.py validate-inference --contract EXTRACT_FIELD --file /tmp/extraction.json --workspace ~/research/my-project/
```

Accepts `--record` (inline JSON) or `--file` (path to JSON file). Returns standard `{"satisfied": bool, "failures": [...]}` output. Follows existing CLI pattern (argparse subcommand, JSON to stdout).

### 1.6 Provenance

Every validated record gets a `_validated_by` metadata field:

```json
{
  "_validated_by": {
    "contract_id": "SCREEN_DECISION",
    "timestamp": "ISO-8601",
    "satisfied": true,
    "recovery_applied": false
  }
}
```

This satisfies LCARS Vision's provenance requirement and supports PRISMA-trAIce Item 5 (validation of AI output).

### 1.7 Module Architecture

```
postconditions.py (existing)
  +-- validate_screening_record()     [NEW — atomic per-record validator]
  +-- validate_extraction_record()    [NEW — atomic per-record validator]
  +-- validate_concept_record()       [NEW — atomic per-record validator]
  +-- check_phase2_all()              [EXISTING — composes over validate_screening_record]
  +-- check_phase4_all()              [EXISTING — composes over validate_extraction_record]

oracle_contracts.py (new)
  +-- imports validators from postconditions.py
  +-- OracleContract dataclass (contract_id, validators, recovery_strategy, provenance)
  +-- SCREEN_CRITERION, SCREEN_DECISION, EXTRACT_FIELD, IDENTIFY_CONCEPTS, SYNTHESIZE_CLAIM
  +-- validate_and_recover(record, contract) -> (validated_record, result)
```

No duplication. `postconditions.py` owns validation logic. `oracle_contracts.py` owns the contract-recovery-provenance wrapper.

---

## 2. Deterministic Preprocessing of Inference Inputs

### 2.0 Axiom Impact

- **Preserves A1:** Pure functions, zero inference calls. Deterministic-first applied to inference input preparation.
- **Preserves A2:** Preprocessed files are derived artifacts in the workspace, regenerable from raw data.
- **Preserves A3:** Raw data remains authoritative. Preprocessed files are additive, not replacing.

### 2.1 Problem

Scholar feeds raw text to inference agents. The quality of screening judgments and synthesis depends on how well relevant signal is surfaced in the input. The section parser (`lib/section_parser.py`) does this for extraction but not for screening or synthesis.

This applies Proven's `decompose.py` pattern: deterministic transformation of LLM inputs to make the oracle's task more tractable. Cognitive ergonomics applied to the LLM itself.

### 2.2 Design

Create `lib/preprocess.py` — pure functions (no I/O, no inference).

### 2.3 Screening Preprocessor

```python
def preprocess_for_screening(
    abstract: str, title: str, criteria: list[dict]
) -> list[dict]:
```

For each criterion:
1. **Keyword extraction** from the criterion's testable condition. Deterministic: split on whitespace, remove stopwords (hardcoded list), stem (Porter stemmer, deterministic).
2. **Sentence scoring** — score each abstract sentence by keyword overlap count.
3. **Evidence window** — top-3 sentences by score, plus first and last sentence (context anchors).
4. Return: `{"criterion_id": "IC1", "evidence_window": "...", "keywords_matched": [...], "full_abstract": "..."}`

The agent receives both the evidence window (focused attention) and the full abstract (no information loss). This is strictly additive — the agent can always fall back to the full abstract.

### 2.4 Synthesis Preprocessor

```python
def preprocess_for_synthesis(
    extractions: list[dict], concepts: list[dict], concept_matrix: list[dict]
) -> dict:
```

1. **Cluster concepts** by co-occurrence (papers sharing >= 2 concepts are linked; connected components form clusters). Graph operation, no inference.
2. **Rank clusters** by paper count (largest first). These become themes.
3. **Per-theme evidence brief:**
   - Papers in the theme, sorted by year
   - Per paper: extraction source (full_text / abstract), recovery_applied flag, key extracted fields
   - Data completeness score: % of fields successfully extracted
   - Consensus/conflict signals: if multiple papers have the same extraction field with different values, flag it
4. Return structured JSON brief.

This addresses Leveson's propagation concern: the synthesis agent sees data completeness *before* writing, not after. Papers with majority-failed extractions are visibly flagged in the brief.

### 2.5 CLI Integration

```bash
python3 lib/cli.py preprocess --type screening --workspace ~/research/my-project/
python3 lib/cli.py preprocess --type synthesis --workspace ~/research/my-project/
```

Output: `{workspace}/data/preprocessed-screening.jsonl` and `{workspace}/data/preprocessed-synthesis.json`. Raw data remains authoritative (A2, A3 preserved). Preprocessed files are derived artifacts, regenerable.

### 2.6 Runbook Changes

- **screen.md** Step 3A: "Before evaluating criteria, read the preprocessed evidence windows from `data/preprocessed-screening.jsonl`. Use the evidence window for focused evaluation; consult the full abstract if the window is insufficient."
- **synthesize.md** Step 1: "Read `data/preprocessed-synthesis.json` instead of raw JSONL files. The brief contains themed evidence organized by concept clusters, with data completeness flags."

The orchestrator skill runs `preprocess --type screening` after Phase 1 completes and before Phase 2 dispatch. Runs `preprocess --type synthesis` after Phase 4 completes and before Phase 5 dispatch.

---

## 3. PRISMA-Compliant Output Format

### 3.0 Axiom Impact

- **Supports A3:** PRISMA checklist makes auditability visible to external reviewers, not just workspace-internal.
- **Supports A7:** Reproducibility information (queries, decisions, logs) is surfaced in the PRISMA-trAIce appendix.
- **No axiom violations:** Output format changes are additive. Existing workspace structure unchanged.

### 3.1 Problem

Scholar's output is a custom markdown template that resembles Kitchenham's reporting structure but doesn't formally comply with PRISMA 2020 or PRISMA-trAIce. Researchers cannot validate compliance, hand off to team review tools, or submit without manual conversion.

### 3.2 Disclosure

Every Scholar review includes a footer disclosure:

> *This review was generated by inference with Scholar (autonomous systematic literature review, Claude Code plugin). Human oversight was limited to protocol approval (Phase 0). Individual screening, extraction, and synthesis judgments were made autonomously by AI agents and validated via structural postconditions, not human review.*

This is direct, honest, and satisfies PRISMA-trAIce Item 4 without burying the information in an appendix.

### 3.3 PRISMA 2020 Compliance Checker

New module: `lib/prisma.py` — pure functions.

```python
def check_prisma_compliance(
    review_text: str, workspace_data: dict, protocol: dict
) -> tuple[bool, list[dict]]:
```

Returns (all_satisfied, checklist) where each checklist entry is:

```json
{
  "item": 1,
  "description": "Title: identify as systematic review",
  "status": "satisfied | partially_satisfied | not_satisfied",
  "explanation": "string",
  "section_ref": "string (where in review.md)"
}
```

**Three-tier status model:**
- `satisfied` — item fully addressed
- `partially_satisfied` — item addressed with caveats (e.g., database coverage with <3 independent sources)
- `not_satisfied` — item not addressed, with explanation of why and what it would take

**No `not_applicable` for core SLR items.** Items 12 (risk of bias), 13b (certainty of evidence), and 15 (reporting biases) are marked `not_satisfied` with explicit explanations:

- Item 12: "Scholar performs binary inclusion/exclusion screening. Individual study quality appraisal (risk of bias) is not performed. This is a known limitation; the output is a thematic synthesis (Thomas & Harden, 2008), not a full SLR with quality grading."
- Item 13b: "Certainty of evidence (GRADE) assessment is not performed. The synthesis presents findings thematically without grading evidence strength."
- Item 15: "Scholar's reliance on Semantic Scholar and arXiv introduces potential bias toward English-language, open-access, and CS/ML-adjacent literature. Snowballing partially compensates but does not eliminate this bias."

**Database coverage check (Item 7):** If fewer than 3 independent databases are searched, status is `partially_satisfied` with explanation that snowballing compensates and listing the extensibility path (PubMed, OpenAlex MCPs).

**Inter-rater reliability (Item 8):** Marked `not_satisfied` with explanation: "Single AI agent screening. Postcondition checks validate structural completeness of screening decisions but do not substitute for inter-rater reliability. Dual-screening mode is a future capability."

### 3.4 PRISMA-trAIce Compliance Checker

```python
def check_prisma_traice_compliance(
    review_text: str, workspace_data: dict
) -> tuple[bool, list[dict]]:
```

Same checklist format. 7 items from the 2025 JMIR AI publication (PRISMA-trAIce, doi:10.2196/80247). Scholar's architecture satisfies most. **Note:** The items below are paraphrased for brevity. The implementation must use exact item text from the published checklist.

| trAIce Item | Scholar Feature | Status |
|------------|----------------|--------|
| AI tool identification | state.json, disclosure footer | satisfied |
| Stage where AI used | Phase-specific agents, phase-log.jsonl | satisfied |
| Human oversight | Phase 0 protocol approval + disclosure | partially_satisfied |
| Prompt/query transparency | search-log.jsonl, screening-log.jsonl | satisfied |
| Validation of AI output | postconditions + oracle contracts | satisfied |
| Reproducibility | protocol.md + all JSONL logs + workspace | satisfied |
| Limitations of AI use | Section 2.6 + disclosure footer | satisfied |

Human oversight is `partially_satisfied` because oversight is at the protocol level, not per-decision. The disclosure footer makes this explicit.

### 3.5 PRISMA Checker Integration

**Advisory, not blocking.** The PRISMA checker is not a Phase 5 postcondition. It runs after the Phase 5 postcondition passes and appends results to the review:

- **Appendix C: PRISMA 2020 Compliance Checklist** — full 27-item table with status and section references
- **Appendix D: PRISMA-trAIce Disclosure** — 7-item AI transparency checklist

The Phase 5 postcondition (`check_phase5_all`) validates structural completeness. The PRISMA checker validates methodological completeness. These are complementary concerns at different levels.

**Coordination point:** When the `prisma_2020` template is created (step A3), `REQUIRED_HEADERS` in `postconditions.py` must be updated to include Appendix C and Appendix D, or made configurable per `output_format`. The `kitchenham` format retains the current header set; `prisma_2020` extends it; `narrative` relaxes it.

### 3.6 PRISMA Flow Diagram

The synthesis agent generates a Mermaid-syntax PRISMA 2020 flow diagram in Section 3.1:

```mermaid
graph TD
    A[Records identified through database searching\nn = {search_candidates}] --> C[Records after deduplication\nn = {deduplicated}]
    B[Records identified through snowballing\nn = {snowball_candidates}] --> C
    C --> D[Records screened\nn = {screened}]
    D --> E[Records excluded\nn = {excluded}]
    D --> F[Full-text assessed\nn = {flagged}]
    F --> G[Studies included\nn = {included}]
    F --> H[Full-text excluded with reasons\nn = {ft_excluded}]
```

Values are computed from workspace metrics:

| Variable | Source | Metric |
|----------|--------|--------|
| `search_candidates` | candidates.jsonl | count where `source=search` |
| `snowball_candidates` | candidates.jsonl | count where `source` starts with `snowball_` |
| `deduplicated` | candidates.jsonl | total count (already deduplicated) |
| `screened` | screening-log.jsonl | count of final decisions |
| `excluded` | screening-log.jsonl | count where `decision=exclude` |
| `flagged` | screening-log.jsonl | count of `flag_for_full_text` entries |
| `ft_excluded` | screening-log.jsonl | count where initial `flag_for_full_text` resolved to `exclude` |
| `included` | included.jsonl | total count |

This is a recognizable PRISMA artifact that reviewers expect.

### 3.7 Configurable Output Formats

The protocol template (Phase 0) gets a new section:

```markdown
## Output Configuration

| Parameter | Default | Options |
|-----------|---------|---------|
| output_format | prisma_2020 | prisma_2020, kitchenham, narrative, custom |
| citation_style | bibtex_keys | bibtex_keys, numbered, author_year |
| include_prisma_checklist | true | true, false |
| include_traice_checklist | true | true, false |
```

- `prisma_2020` (default): Full PRISMA 2020 structure, flow diagram, checklists
- `kitchenham`: Current Scholar format (backward compatible)
- `narrative`: Lighter thematic synthesis for scoping reviews — no appendices, relaxed postconditions
- `custom`: User provides template in protocol.md

Format-specific templates: `templates/review-template-prisma.md`, `templates/review-template-kitchenham.md` (existing, renamed), `templates/review-template-narrative.md`.

### 3.8 Synthesis Self-Validation

After generating review.md but before terminating, the synthesis agent:

1. Runs PRISMA checker against its own output
2. For each `not_satisfied` item: appends a note to Section 2.6 (Threats to Validity) explaining the gap
3. For each `partially_satisfied` item: verifies the explanation text is present in the relevant section
4. Appends Appendix C and D
5. Does NOT retry synthesis — this is a completion step that adds compliance metadata to an already-complete review

### 3.9 Reference Implementation Output Standard

The `prisma_2020` format is the reference implementation. It follows Thomas & Harden's (2008) thematic synthesis methodology and maps to PRISMA 2020 reporting. The review must be:

- **Methodologically transparent:** Every decision traceable through JSONL logs
- **Structurally compliant:** PRISMA checklist appended with per-item status
- **Honestly disclosed:** AI role, limitations, and scope of human oversight stated clearly
- **Human-readable:** Findings organized thematically with clear topic sentences, consensus/contradiction/gap structure per theme, and citation discipline (cite foundational work, not bulk lists)

---

## 4. Dafny-Verified State Machine

### 4.0 Axiom Impact

- **Fulfills A11:** State machine and saturation module move from "tested" to "statically verified."
- **Preserves all axioms:** Dafny specs are companion artifacts. Runtime Python unchanged.

### 4.1 Problem

Scholar's `lib/state.py` implements a 6-phase state machine as pure functions with documented invariants. The properties are tested in Python but not formally proved. A formal proof would make Scholar the only research tool with a verified orchestration core.

### 4.2 Design

Write `spec/state.dfy` as a companion artifact to `lib/state.py`. The Dafny module mirrors the Python structure. Z3 proves the properties; the Python remains the runtime.

### 4.3 Properties to Verify

| Property | Python Enforcement | Dafny Proof |
|----------|-------------------|-------------|
| Forward progress: advance only N to N+1 | `ValueError` in `transition_to_next` | Proved for all states |
| No skipping: phase N+1 requires N completed | `phase_completed` list check | Proved by induction |
| Feedback bound: iterations <= max | `ValueError` in `feedback_loop` | Proved: counter monotonically increases, checked against bound |
| Retry bound: at most 1 retry per phase | `retry_count >= 1` check | Proved: retry_count in {0, 1} |
| Terminal correctness: done iff phase 5 completed | `is_review_complete` | Proved: only reachable via phase 5 + completed |
| Monotonic phase_completed: once True, stays True | Implicit in list operations | Proved as invariant across all transitions |
| Status enum validity: all transitions produce valid status | `PhaseStatus` enum | Proved: no transition produces invalid status |

### 4.4 Dafny Specification Sketch

```dafny
datatype PhaseStatus = Pending | InProgress | Completed | Failed | NeedsProtocolRevision

datatype State = State(
  currentPhase: nat,
  phaseStatus: PhaseStatus,
  feedbackIterations: nat,
  retryCount: nat,
  phaseCompleted: seq<bool>
)

// maxFeedbackIterations is a protocol-level constant, not hardcoded.
// The Dafny spec parameterizes it; the Python reads it from protocol.md.
const MAX_FEEDBACK_ITERATIONS: nat := 2  // default; matches protocol template

predicate ValidState(s: State) {
  0 <= s.currentPhase <= 5 &&
  |s.phaseCompleted| == 6 &&
  s.retryCount <= 1 &&
  s.feedbackIterations <= MAX_FEEDBACK_ITERATIONS
}

predicate MonotonicCompleted(before: seq<bool>, after: seq<bool>) {
  |before| == |after| &&
  forall i :: 0 <= i < |before| ==> (before[i] ==> after[i])
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
  s' := State(
    s.currentPhase + 1,
    Pending,
    s.feedbackIterations,
    0,
    s.phaseCompleted
  );
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
  s' := State(
    3,
    Pending,
    s.feedbackIterations + 1,
    0,
    s.phaseCompleted
  );
}
```

### 4.5 Saturation Module

`lib/saturation.py` uses `Fraction` arithmetic with documented range properties. Write `spec/saturation.dfy`:

- `discovery_saturation` returns value in [0, 1]
- Zero denominator returns 0 (not division error)
- `should_terminate_discovery`: true iff saturation < threshold
- `should_feedback_loop`: true iff delta >= theta_c AND iterations < max

These are small, pure functions — ideal Dafny targets.

### 4.6 File Placement

```
spec/
  state.dfy          # State machine proof
  saturation.dfy     # Saturation metrics proof
```

New `spec/` directory parallel to `lib/`. The `spec/` directory contains proof artifacts, not runtime code.

### 4.7 CI Integration

Optional test that runs `dafny verify spec/state.dfy spec/saturation.dfy`. Requires Dafny on PATH. Tests skip gracefully if Dafny is not installed (same pattern as Proven's optional verification).

### 4.8 What is NOT Verified

- `postconditions.py` — integration-level checks over workspace data, not amenable to static proof
- `cli.py` — I/O boundary (Proven methodology: separate I/O shell from verified core)
- `section_parser.py` — text processing with regex; tested, not proved
- `preprocess.py` — text processing; tested, not proved
- Agent behavior — nondeterministic; governed by oracle contracts, not static proof

---

## 5. Expert Panel and Change Management Protocol

### 5.1 Problem

Scholar has no governance for design changes. Modifications happen ad hoc, risking semantic contract violations.

### 5.2 Change Management Protocol

Adopted from UIDI. Every change begins with scope classification.

| Tier | Scope | Examples | Required Phases |
|------|-------|----------|-----------------|
| Tier 1 (Patch) | No behavioral change | Test fixes, doc edits, template tweaks | State what + why, implement |
| Tier 2 (Feature) | New/modified observable behavior | New MCP integration, new postcondition, new output format, new oracle contract | Phases 1-4 (full protocol) |
| Tier 3 (Architectural) | Pipeline structure, schema changes | New review phase, state machine modification, oracle contract schema change | Phases 1-4 with extended review |

**Phase 1 — Specification Review:** Read governing spec sections, state change in spec terms, identify semantic contracts.

**Phase 2 — Expert Panel Review:** Each panelist produces PASS / CONCERN / BLOCK with 2-4 sentence analysis. Any BLOCK stops progress.

**Phase 3 — Implementation Plan:** Numbered plan with test targets per semantic contract. User approves.

**Phase 4 — Implementation:** Execute in plan order. Run tests after each unit. If implementation reveals a Phase 1 gap, return to Phase 1.

### 5.3 Scholar Expert Panel

**Standing panel (every conference):**

| Panelist | Focus | Catches |
|----------|-------|---------|
| **Dijkstra** | Postcondition completeness, state machine correctness, oracle contract sufficiency, biconditional decision rules | Unstated preconditions, incomplete contracts |
| **Tay** (Research Librarian) | Recall, database coverage, PRISMA compliance, output interoperability, practitioner usability, sensitivity vs. precision | Insufficient database diversity, non-compliant PRISMA, dead-end formats |
| **Leveson** (STAMP/STPA) | Failure propagation through phases, recovery strategy adequacy, silent omission hazards, control structure analysis | Recovery that masks errors, plausible-but-wrong output propagation |
| **Ousterhout** (Module Design) | Module depth, duplication between lib/ modules, interface quality, information hiding | Shallow modules, overlapping validation logic, pass-through steps |
| **Sovereignty** | Data locality, inference provenance, workspace completeness (A2), append-only evidence (A3) | External dependencies, inference in process logic, implicit state |

**Per-change experts (selected by domain):**

| Expert | When |
|--------|------|
| **Kitchenham** | Changes to phase transitions, screening criteria, saturation metrics, SLR methodology |
| **Wohlin** | Changes to citation traversal, discovery saturation, snowballing procedure |
| **PRISMA** | Changes to synthesis output, review template, export formats, compliance checking |
| **Cognitive Ergonomics** | Changes to user-facing output, protocol interaction, progress reporting, review readability |
| **Thomas & Harden** | Changes to thematic synthesis methodology, concept clustering, theme organization |

### 5.4 File Placement

- `docs/methodology/EXPERT_ROSTER.md` — panel roster with focus areas and failure modes
- `docs/methodology/CHANGE_PROTOCOL.md` — tier classification and phase protocol

---

## 6. Phase B — Capability Expansion

### 6.1 PubMed MCP (Priority 1)

**Rationale:** PRISMA database coverage. PubMed is independent of Semantic Scholar's index. 36M+ biomedical citations. Free, no API key. Anthropic official integration.

**Integration:** Phase 1 search agent. Protocol template Search Terms table gets a PubMed row. Search runbook gets a PubMed query execution block. Deduplication via DOI matching (existing).

**Rate limiting:** 3 requests/second (NCBI E-utilities documented limit). Add to search runbook rate limit table.

### 6.2 Scite MCP (Priority 2)

**Rationale:** Screening and extraction quality. Smart Citations classify each citation as supporting, contrasting, or mentioning. No other data source provides citation sentiment.

**Integration:**
- Phase 2 screening: Query Scite for a paper's citation context. If other papers predominantly contrast its findings, this is evidence relevant to exclusion criteria evaluation.
- Phase 4 extraction: Scite's classification enriches the concept matrix with agreement/disagreement relationships between papers.

**Dependency:** Scite subscription required. Optional — Scholar degrades gracefully without it.

### 6.3 paper-search-mcp (Priority 3)

**Rationale:** Recall breadth. 20+ databases (IEEE Xplore, ACM, DBLP, CrossRef, OpenAlex, CORE, etc.). On PyPI.

**Integration:** Phase 1 search agent, same pattern as PubMed. The `search_papers` tool returns unified results.

**Dependency:** `pip install paper-search-mcp`. Optional.

### 6.4 Citation Hallucination Detection (Priority 4)

**Rationale:** GPT-4 hallucinates 18-28% of citations. 100+ hallucinated citations found in NeurIPS 2025 accepted papers. Scholar's synthesis agent writes prose that cites papers — hallucination is a real risk.

**Design:** New function in `postconditions.py`:

```python
def check_citation_grounding(
    review_citations: dict[str, str],  # bibtex_key -> surrounding sentence
    extractions: list[dict],
) -> tuple[bool, list[str]]:
```

For each body citation, extract the claim sentence. Match claim keywords against the cited paper's extraction fields. If keyword overlap is below threshold, flag as potentially ungrounded.

**Integration:** Called by `check_phase5_all`. Advisory — flags append to "Appendix E: Citation Verification Notes".

### 6.5 RIS/CSV Export (Priority 5)

**Rationale:** Interoperability with Covidence, Rayyan, Zotero, Mendeley.

**Design:** `lib/export.py` — pure functions:
- `to_ris(records: list[dict]) -> str`
- `to_csv(records: list[dict], fields: list[str]) -> str`

**CLI:**
```bash
python3 lib/cli.py export --format ris --dataset included --workspace ~/research/my-project/
python3 lib/cli.py export --format csv --dataset candidates --workspace ~/research/my-project/
```

`--dataset` in {candidates, included, extractions}. `--format` in {ris, csv}.

---

## 7. Implementation Order

### Phase A (Internal Hardening)

| Step | Section | New/Modified Files | Dependencies |
|------|---------|-------------------|--------------|
| A1 | Oracle Contracts | `lib/postconditions.py` (add per-record validators), `lib/oracle_contracts.py` (new), `lib/cli.py` (add validate-inference) | None |
| A2 | Deterministic Preprocessing | `lib/preprocess.py` (new), `lib/cli.py` (add preprocess), runbooks updated | A1 (recovery flags used by synthesis preprocessor) |
| A3 | PRISMA Output | `lib/prisma.py` (new), `lib/export.py` (new — module created with PRISMA Mermaid diagram generation only), `lib/cli.py` (add prisma), templates (new prisma/narrative), `skills/research/SKILL.md` (output config), runbooks updated | A2 (preprocessed synthesis uses data completeness) |
| A4 | Dafny Verification | `spec/state.dfy` (new), `spec/saturation.dfy` (new) | None (parallel to A1-A3) |
| A5 | Expert Panel | `docs/methodology/EXPERT_ROSTER.md` (new), `docs/methodology/CHANGE_PROTOCOL.md` (new) | None (parallel, documentation only) |

### Phase B (Capability Expansion)

| Step | Section | New/Modified Files | Dependencies |
|------|---------|-------------------|--------------|
| B1 | PubMed MCP | `runbooks/search.md`, `templates/protocol-template.md` | Phase A complete |
| B2 | Scite MCP | `runbooks/screen.md`, `runbooks/extract.md` | B1 |
| B3 | paper-search-mcp | `runbooks/search.md`, `templates/protocol-template.md` | B1 |
| B4 | Hallucination Detection | `lib/postconditions.py` | A1, A3 |
| B5 | RIS/CSV Export | `lib/export.py` (extend module created in A3 with `to_ris()` and `to_csv()`), `lib/cli.py` (add export subcommand) | A3 |

---

## 8. Test Strategy

### Unit Tests (per module)

- `tests/test_oracle_contracts.py` — contract validation with known-good and known-bad records, recovery behavior, provenance metadata
- `tests/test_preprocess.py` — keyword extraction, sentence scoring, evidence window construction, concept clustering, theme ranking
- `tests/test_prisma.py` — checklist generation, three-tier status model, flow diagram data
- `tests/test_export.py` — RIS/CSV format compliance, round-trip import verification

### Integration Tests

- End-to-end: protocol through synthesis with oracle contracts active, verify all records have `_validated_by` metadata
- PRISMA checker against a completed review workspace, verify checklist completeness
- Export → import into Zotero/reference manager (manual verification)

### Verification

- `dafny verify spec/state.dfy` — state machine properties
- `dafny verify spec/saturation.dfy` — saturation metric properties
- CI: skip gracefully if Dafny not installed

---

## 9. Properties This Design Must Satisfy

Extending Scholar's existing P1-P7:

**P8 — Inference Quarantine Enforcement:** For every record `r` written to workspace files by Phases 2-5 where the generating function uses inference, there exists a `_validated_by` metadata field where `_validated_by.contract_id` is a named OracleContract and `_validated_by.satisfied` is a boolean. If `_validated_by.satisfied == false`, then `_validated_by.recovery_applied == true` and the record contains the recovery output defined by the contract's recovery strategy. Formally: `forall r in workspace_records : uses_inference(r) ==> r._validated_by != null AND (r._validated_by.satisfied OR r._validated_by.recovery_applied)`.

**P9 — Preprocessing Determinism:** For all functions `f` in `preprocess.py`: `f(x) == f(x)` for all inputs `x` (referential transparency). No function in the module makes inference calls, network requests, or reads mutable state. Formally: `preprocess.py ∩ inference_calls = ∅`.

**P10 — PRISMA Transparency:** The output review.md includes a PRISMA 2020 checklist (Appendix C) with an entry for each of the 27 items. Each entry has `status` in {satisfied, partially_satisfied, not_satisfied} and a non-empty `explanation` string. No core SLR item uses a status outside this set. Formally: `forall item in prisma_checklist : item.status in {satisfied, partially_satisfied, not_satisfied} AND |item.explanation| > 0`.

**P11 — State Machine Soundness:** `dafny verify spec/state.dfy` and `dafny verify spec/saturation.dfy` succeed with zero errors. The Dafny specification covers all 7 state machine properties (forward progress, no skipping, feedback bound, retry bound, terminal correctness, monotonic completion, status validity) and all 4 saturation properties (range [0,1], zero-denominator safety, termination threshold, feedback bound).

**P12 — Export Fidelity:** For every record `r` in the source JSONL and every metadata field `f` in `r`: the corresponding RIS or CSV output contains `f`'s value. Formally: `forall r in source, f in r.fields : f in export(r).fields AND export(r).fields[f] == r.fields[f]`.
