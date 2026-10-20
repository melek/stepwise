# Postcondition Check Procedures

This document defines the checks the orchestrator runs after each phase completes. All checks are deterministic — they read workspace files and evaluate structural conditions. No inference.

The orchestrator executes these checks by reading the relevant files and verifying each condition. On failure, the orchestrator records the failure in `state.json` and follows the retry/transition logic defined here.

---

## Phase 1 — Search

**Files to read:**
- `protocol.md` — extract all query strings from the Search Terms table
- `logs/search-log.jsonl` — all search execution records
- `data/candidates.jsonl` — all candidate papers

**Checks:**

1. **All queries executed:** For each database in the Search Terms table of `protocol.md`, the number of distinct query executions in `search-log.jsonl` for that database is at least equal to the number of queries specified in the protocol for that database. Database names are normalized to canonical form (e.g., `Semantic Scholar` → `semantic_scholar`).
2. **Candidates non-empty:** `data/candidates.jsonl` contains at least one record.
3. **No duplicate canonical IDs:** Extract the `id` field from every record in `candidates.jsonl`. No two records share the same `id`.
4. **Minimum metadata:** Every record in `candidates.jsonl` has non-null values for: `id`, `title`, `abstract`, `authors`, `year`. A missing `abstract` is allowed when the record carries `metadata_gap: ["abstract"]` (the source API had none; screening excludes such papers under the insufficient-content criterion). If more than 25% of all records lack an abstract, tagged or not, the check fails: that points at the search itself, not at normal API gaps.

**On failure:** Retry phase once. If still failing, record failure reason in `state.json` and terminate.

---

## Phase 2 — Screening

**Files to read:**
- `data/candidates.jsonl` — all candidates
- `logs/screening-log.jsonl` — all screening decisions
- `data/included.jsonl` — papers that passed screening

**Checks:**

1. **All candidates screened:** For every paper in `candidates.jsonl`, there exists at least one entry in `screening-log.jsonl` where `entry.paper_id` matches `paper.id` AND `entry.decision` is either `include` or `exclude`. (Papers initially flagged as `flag_for_full_text` will have two entries — the flag and the resolved decision. Both are preserved per A3. Only the final decision matters for this check.)
2. **Included consistency:** Every paper in `included.jsonl` has a corresponding entry in `screening-log.jsonl` with `decision = include`.
3. **No orphan inclusions:** Every paper in `included.jsonl` exists in `candidates.jsonl`.

**Transition logic:**
- If `included.jsonl` is non-empty → transition to Phase 3
- If `included.jsonl` is empty → **diagnostic transition**: set `phase_status = needs_protocol_revision`. Report: "No papers passed screening. Review protocol criteria and search terms." The `/stepwise:continue` skill re-enters Phase 0.

**On failure (check failure, not empty included):** Retry phase once. If still failing, record failure reason and terminate.

---

## Phase 3 — Snowballing

**Files to read:**
- `protocol.md` — extract `max_snowball_depth`, `discovery_saturation_threshold` (θ_d)
- `data/included.jsonl` — included papers (read the set that existed at phase start)
- `logs/snowball-log.jsonl` — all snowball traversals
- `logs/phase-log.jsonl` — saturation check events

**Checks:**

1. **Termination condition met:** At least one of:
   - Discovery saturation: the last `saturation_check` event in `phase-log.jsonl` shows `saturation_metric < θ_d`
   - Maximum depth: `snowball_depth_reached` in the log equals `max_snowball_depth` from protocol
2. **All seed papers examined:** For every paper in `included.jsonl` that was a seed, there exist entries in `snowball-log.jsonl` with that paper as `source_paper_id` for both `direction: forward` and `direction: backward`. An empty-result marker (`discovered_paper_id: null`, `note: "empty_array_from_api"`) counts for its direction. Papers discovered at the deepest `depth_level` snowballing reached are terminal and exempt, whether it stopped at `max_snowball_depth` or on discovery saturation. IDs match across all of a paper's ID forms (`id`, `doi`, `arxiv_id`, `s2_id`), ignoring `doi:`/`s2:`/`arxiv:` prefixes and case.
3. **Truncation logged:** For any snowball-log entry where `truncated = true`, `total_citations_available` and `citations_retrieved` are both non-null.
4. **New inclusions recorded:** Every paper with `screening_decision = include` in `snowball-log.jsonl` exists in both `data/included.jsonl` and `data/candidates.jsonl`, matched across ID forms as in check 2 (a paper logged under its S2 ID may be stored under a promoted DOI).

**On failure:** Retry phase once. If still failing, record failure and terminate.

---

## Phase 4 — Extraction

**Files to read:**
- `data/included.jsonl` — all included papers
- `data/extractions.jsonl` — extraction records
- `data/concepts.jsonl` — concept vocabulary
- `concept-matrix.md` — paper × concept matrix
- `logs/phase-log.jsonl` — saturation check events
- `protocol.md` — extract `conceptual_saturation_k` (k), `conceptual_saturation_threshold` (θ_c), `max_feedback_iterations`

**Checks:**

1. **All papers extracted:** For every paper in `included.jsonl`, there exists at least one record in `extractions.jsonl` where `entry.paper_id` matches `paper.id`.
2. **Extraction schema valid:** Every extraction record has a `source` field (`"full_text"` or `"abstract"`). Every entry in the `fields` array has all four required keys: `field_name` (string), `value` (string), `source_location` (string), `confidence` (one of `"high"`, `"medium"`, `"low"`). No key may be null or missing.
3. **Concepts non-empty:** `data/concepts.jsonl` contains at least one record.
4. **Concept matrix exists:** `concept-matrix.md` exists and is non-empty.
5. **All concepts defined:** Every `concept_id` referenced in any extraction record exists in `concepts.jsonl` with a non-empty `definition`.
6. **Conceptual saturation computed:** There exists a `saturation_check` event in `phase-log.jsonl` for the current phase with a non-null `saturation_metric`.

**Transition logic (computed by orchestrator after checks pass):**

Compute conceptual saturation: `Δ(n, k) = |new concepts in last k papers| / |total concepts|`
- Read `concepts.jsonl`, sort by `first_seen_at`
- Count concepts where `first_seen_at` is among the last `k` extracted papers
- Divide by total concept count

Decision:
- If `Δ(n, k) ≥ θ_c` AND feedback iterations < `max_feedback_iterations` → transition back to Phase 3. New included papers from this extraction round become snowball seeds.
- If `Δ(n, k) < θ_c` OR feedback iterations ≥ `max_feedback_iterations` → transition to Phase 5.

Record the saturation metric and transition decision in `state.json` and `phase-log.jsonl`.

**On failure:** Retry phase once. If still failing, record failure and terminate.

---

## Phase 5 — Synthesis

**Files to read:**
- `data/included.jsonl` — all included papers
- `review.md` — the literature review document
- `references.bib` — BibTeX bibliography
- `protocol.md` — extract research sub-questions
- `data/question-answers.jsonl` — sub-question mapping

**Checks:**

1. **All papers in Appendix A:** For every paper in `included.jsonl`, `paper.id` or the paper's BibTeX key appears in Appendix A of `review.md`. (Body citation coverage is not required — Appendix A is the completeness guarantee.)
2. **All questions addressed:** For every sub-question in `protocol.md`, there exists an entry in `question-answers.jsonl` with `disposition` in `{answered, partially_answered, identified_as_gap}`.
3. **Question-answers complete:** `question-answers.jsonl` has an entry for every sub-question in the protocol.
4. **Bibliography consistent:** The number of entries in `references.bib` equals the number of unique `[@...]` citation keys in `review.md`. When counting citation keys in `review.md`, only count keys inside actual citation brackets `[@...]` — exclude any occurrences inside backtick-escaped code spans or code blocks.
5. **Review structure:** `review.md` contains all required section headers: Abstract, Introduction, Methodology, Results, Discussion, Conclusion, References, Appendix A, Appendix B.
6. **Appendix A row count:** The number of data rows in Appendix A's included-papers table (excluding the header row and separator row) equals the number of records in `data/included.jsonl`.

**On failure:** Retry phase once. If still failing, record failure and terminate.

---

## Phase Transition Decision Table

| Current Phase | Postcondition Result | Condition | Next Action |
|---------------|---------------------|-----------|-------------|
| 1 | Pass | — | Transition to Phase 2 |
| 1 | Fail | First failure | Retry Phase 1 |
| 1 | Fail | Second failure | Record failure, terminate |
| 2 | Pass | `included.jsonl` non-empty | Transition to Phase 3 |
| 2 | Pass | `included.jsonl` empty | Set `needs_protocol_revision`, terminate |
| 2 | Fail | First failure | Retry Phase 2 |
| 2 | Fail | Second failure | Record failure, terminate |
| 3 | Pass | — | Transition to Phase 4 |
| 3 | Fail | First failure | Retry Phase 3 |
| 3 | Fail | Second failure | Record failure, terminate |
| 4 | Pass | `Δ(n,k) ≥ θ_c` AND iterations < max | Transition to Phase 3 (feedback loop) |
| 4 | Pass | `Δ(n,k) < θ_c` OR iterations ≥ max | Transition to Phase 5 |
| 4 | Fail | First failure | Retry Phase 4 |
| 4 | Fail | Second failure | Record failure, terminate |
| 5 | Pass | — | Mark review complete |
| 5 | Fail | First failure | Retry Phase 5 |
| 5 | Fail | Second failure | Record failure, terminate |

---

## Saturation Metric Computation

### Discovery Saturation (Phase 3)

Computed at each snowball depth level.

```
θ_discovery = |newly_included_at_depth_d| / |newly_examined_at_depth_d|
```

- Read `snowball-log.jsonl`, filter by `depth_level = d`
- Count entries where `screening_decision = include` AND `already_known = false` → numerator
- Count entries where `already_known = false` and `discovered_paper_id` is non-null → denominator. Already-known papers and empty-result markers are not new examinations.
- If denominator = 0, saturation = 0 (terminate)
- Compare against protocol's `discovery_saturation_threshold` (θ_d)
- If `θ_discovery < θ_d` → discovery saturated, terminate snowballing

### Conceptual Saturation (Phase 4)

Computed after all extractions complete.

```
Δ(n, k) = |concepts first seen in last k extracted papers| / |total concepts|
```

- Read `concepts.jsonl`, get all concepts sorted by `first_seen_at`
- Read `extractions.jsonl`, get the last `k` papers extracted (by timestamp)
- Count concepts whose `first_seen_in` is one of those `k` papers → numerator
- Total concept count → denominator
- If denominator = 0, saturation = 0 (proceed to Phase 5)
- Compare against protocol's `conceptual_saturation_threshold` (θ_c)
- If `Δ(n, k) ≥ θ_c` → concept space still expanding, loop back to Phase 3
- If `Δ(n, k) < θ_c` → concept space stable, proceed to Phase 5
