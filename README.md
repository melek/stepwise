# Stepwise

Autonomous systematic literature review as a Claude Code plugin. Implements the Kitchenham SLR protocol (Kitchenham & Charters, 2007) with Wohlin snowball sampling (Wohlin, 2014), PRISMA 2020 compliance checking (Page et al., 2021), and AI transparency reporting via PRISMA-trAIce.

The core idea: the *process* of conducting a literature review — phase transitions, termination, file routing, postcondition checking — is entirely deterministic. The *content* — relevance judgments, concept extraction, synthesis — uses LLM inference, quarantined behind named oracle contracts with validation gates. This separation (`P ∩ C = ∅`) means the review structure is auditable and reproducible independent of which model produced the judgments.

## Methodology

Six sequential phases, each with defined postconditions that must pass before the next phase begins:

| Phase | Name | Mode | Work |
|-------|------|------|------|
| 0 | Protocol Definition | Interactive | User and orchestrator collaboratively define research question, search strategy, inclusion/exclusion criteria, extraction schema, and phase bounds |
| 1 | Search | Autonomous | Execute Boolean queries against Semantic Scholar and arXiv; collect candidate corpus |
| 2 | Screening | Autonomous | Evaluate each candidate against inclusion/exclusion criteria; produce included corpus |
| 3 | Snowballing | Autonomous | Forward and backward citation traversal from included papers; screen new candidates; terminate on discovery saturation (`θ_d`) or max depth |
| 4 | Extraction | Autonomous | Extract protocol-defined fields from each included paper; identify concepts; check conceptual saturation (`θ_c`) — loop back to Phase 3 if concept space is still expanding |
| 5 | Synthesis | Autonomous | Thematic synthesis (Thomas & Harden, 2008); produce structured review with bibliography, concept matrix, and compliance appendices |

All state resides in the filesystem workspace (`~/research/{slug}/`). An agent with the workspace and runbooks can reconstruct where any review stands and resume from that point.

### Saturation

Both termination criteria use exact rational arithmetic (`fractions.Fraction`) to avoid floating-point drift:

- **Discovery saturation** (Phase 3): ratio of newly-included to total-examined papers at each snowball depth. Terminates when ratio < `θ_d`.
- **Conceptual saturation** (Phase 4→3 feedback): ratio of new concepts in the last *k* papers to total concept count. Loops back to Phase 3 when ratio ≥ `θ_c`, up to a bounded number of feedback iterations.

Both properties are specified and proved in Dafny (`spec/saturation.dfy`).

### Oracle Contracts

Every inference call in Phases 2–5 passes through a named contract before its output is written:

| Contract | Validates |
|----------|-----------|
| `SCREEN_CRITERION` | Single criterion evaluation (met/not-met/unclear, evidence, source) |
| `SCREEN_DECISION` | Complete screening decision (biconditional: include iff all IC met, no EC met) |
| `EXTRACT_FIELD` | Single extraction field (with confidence ceiling for abstract-only papers) |
| `IDENTIFY_CONCEPTS` | Concept record (slug format, definition length, frequency) |
| `SYNTHESIZE_CLAIM` | Citation integrity (every paragraph cited, no phantom references) |

Failed validation triggers documented recovery strategies (e.g., `met=unclear`, `extraction_failed`), not retries with weaker constraints. Every record carries `_validated_by` provenance metadata.

## Rate Limit Safety

API pacing is proactive — requests are spaced to stay under documented limits, not relying on 429 backoff alone.

| API | Pacing | Source |
|-----|--------|--------|
| Semantic Scholar | 1 req/s (unauth) or per key limit | S2 API docs |
| arXiv | 3s between requests | arXiv API Terms of Use |
| Unpaywall | 1 req/s | Politeness policy |
| PubMed | 3 req/s | NCBI E-utilities docs |

On HTTP 429 despite proactive pacing: exponential backoff (2s → 4s → 8s → 16s → 32s), max 5 retries. Each event logged to `phase-log.jsonl`. If retries exhaust, the agent terminates with partial work; the orchestrator detects incomplete output via postcondition failure and retries the phase (max 1 retry per phase, Dafny-proved bound).

## Verification

The state machine (phase transitions, retry bounds, status validity) and saturation properties are specified in Dafny with machine-checked proofs:

| File | Properties |
|------|------------|
| `spec/state.dfy` | Forward progress, no phase skipping, feedback bound, retry bound (≤1), terminal correctness, monotonic completion |
| `spec/saturation.dfy` | Range [0,1], zero-denominator safety, termination threshold, feedback bound |

Python implementations in `lib/` mirror the Dafny specs and are tested (85 tests, pytest).

## Installation

Stepwise is a Claude Code plugin. Install from the `cc-lab` marketplace:

```
claude plugin add stepwise@cc-lab
```

Requires MCP servers for Semantic Scholar and arXiv (both required). PubMed, Unpaywall, Scite, paper-search-mcp, and Zotero are optional.

### Usage

```
/stepwise:research "What approaches exist for X in domain Y?"
/stepwise:continue <slug>
/stepwise:status <slug>
```

Workspaces are created at `~/research/{slug}/`. The protocol is the single human-approved artifact; everything after Phase 0 runs autonomously.

## Example: Formal Methods for Nondeterministic Oracles

A completed review investigating how formal methods frameworks approach verification of systems with nondeterministic computational components (LLM inference as interchangeable oracles).

**Research question:** *How would formal methods frameworks approach the design and verification of software systems that incorporate nondeterministic computational components (such as LLM inference) as interchangeable oracles?*

**Sub-questions:**
1. Can postconditions be checked efficiently when the oracle's output space is finite but intractably large?
2. What contract-based approaches exist for specifying the deterministic/nondeterministic interface?
3. What techniques verify the deterministic framework while treating nondeterministic components as interchangeable?

**Results:**

| Metric | Value |
|--------|-------|
| Candidates examined | 1,839 |
| Included | 365 |
| Excluded | 168 |
| Snowball depth | 2 |
| Concepts identified | 49 |
| Feedback iterations | 0 (conceptual saturation reached) |
| Synthesis | 17,082 words, 6 themes, 365 citations |

**Phase timeline:**

| Phase | Duration | Work |
|-------|----------|------|
| Search | ~42 min | 8 queries across Semantic Scholar + arXiv |
| Screening | ~29 min | 210 candidates screened |
| Snowballing | ~104 min | 2 depth levels, 1,631 papers examined, 323 added |
| Extraction | ~29 min | 365 papers extracted, 38 initial concepts |
| Synthesis | ~29 min | Thematic synthesis with full bibliography |

Output: `~/research/formal-methods-nondeterministic-oracles/review.md`

## References

- Kitchenham, B. & Charters, S. (2007). *Guidelines for performing Systematic Literature Reviews in Software Engineering.* EBSE Technical Report.
- Wohlin, C. (2014). Guidelines for snowballing in systematic literature studies and a replication in software engineering. *EASE '14*.
- Page, M.J. et al. (2021). The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. *BMJ*, 372.
- Thomas, J. & Harden, A. (2008). Methods for the thematic synthesis of qualitative research in systematic reviews. *BMC Medical Research Methodology*, 8(45).
