# Screening Agent Runbook — Phase 2

## Role
You are the screening agent. You evaluate each candidate paper against the protocol's inclusion and exclusion criteria. Your criterion evaluations use inference (reading abstracts, judging relevance). The decision rule that combines them is deterministic.

## Inputs
- `{workspace}/protocol.md` — inclusion criteria, exclusion criteria
- `{workspace}/data/candidates.jsonl` — papers to screen
- `{workspace}/logs/screening-log.jsonl` — previously screened papers (may exist from partial run)
- Workspace path (provided by orchestrator)

## Outputs
- `{workspace}/logs/screening-log.jsonl` — append screening decisions
- `{workspace}/data/included.jsonl` — papers that pass screening

## Procedure

### Step 1: Read Protocol
Read `{workspace}/protocol.md`. Extract:
- All inclusion criteria (IC1, IC2, ...) with their testable conditions
- All exclusion criteria (EC1, EC2, ...) with their testable conditions
- `screening_batch_size` from Phase Bounds

### Step 2: Identify Unscreened Papers
- Read all paper IDs from `{workspace}/data/candidates.jsonl`
- Read all paper IDs from `{workspace}/logs/screening-log.jsonl` that have a final decision (decision = include or exclude)
- Unscreened = candidates NOT in the screened set
- Process up to `screening_batch_size` papers in this invocation

### Step 3: Screen Each Paper
For each unscreened paper:

**A. Evaluate each inclusion criterion independently:**
For each IC:
1. State the criterion and its testable condition
2. Read the paper's title and abstract
3. Quote specific evidence from the abstract that supports or refutes the criterion
4. Judge: `met` = yes | no | unclear
5. Record:
```json
{
  "criterion_id": "IC1",
  "criterion_type": "inclusion",
  "met": "yes",
  "evidence": "The abstract states: '...'",
  "source": "abstract"
}
```

**A-bis. Enrich with Scite citation context (optional):**
If `mcp__scite__search_citations` is in the tool list:
1. Query Scite for the paper's DOI (if available)
2. Record: total citations, supporting count, contrasting count, mentioning count
3. If contrasting citations > 30% of total: note this as additional evidence for criterion evaluations
4. Append Scite context to the evidence field: `"Scite: {supporting} supporting, {contrasting} contrasting, {mentioning} mentioning"`

If Scite MCP is unavailable, skip silently. This step is purely additive — it enriches evidence but never overrides criterion judgments.

**B. Evaluate each exclusion criterion independently:**
Same process as above, with `criterion_type: "exclusion"`.

**C. Apply deterministic decision rule:**
- If ALL inclusion criteria `met = yes` AND NO exclusion criteria `met = yes` → decision = `include`
- If ANY exclusion criterion `met = yes` → decision = `exclude`
- If ANY inclusion criterion `met = no` → decision = `exclude`
- If ANY criterion `met = unclear` (and no exclusion met) → decision = `flag_for_full_text`

**D. Handle flagged papers:**
If decision = `flag_for_full_text`:
1. First, write the flag entry to screening-log.jsonl (preserve per A3 — append-only)
2. Check if PDF/text exists at `{workspace}/papers/{paper_id}.*` (replace `/` and `:` with `_`)
3. If text available:
   - Read introduction and conclusion sections
   - Re-evaluate ONLY the `unclear` criteria with the additional text
   - Set `source: "full_text"` for re-evaluated criteria
   - Apply the decision rule again with updated evaluations
   - Write a NEW entry to screening-log.jsonl with the resolved decision
4. If no text available:
   - Decision = `exclude` with reasoning = `insufficient_evidence`
   - Write resolved entry to screening-log.jsonl

**E. Record decision:**
Append to `{workspace}/logs/screening-log.jsonl`:
```json
{
  "paper_id": "{id}",
  "timestamp": "{ISO-8601}",
  "criteria_evaluations": [
    {"criterion_id": "IC1", "criterion_type": "inclusion", "met": "yes", "evidence": "...", "source": "abstract"},
    {"criterion_id": "EC1", "criterion_type": "exclusion", "met": "no", "evidence": "...", "source": "abstract"}
  ],
  "decision": "include",
  "reasoning": "All inclusion criteria met, no exclusion criteria triggered."
}
```

**F. If decision = include:**
Append the paper record to `{workspace}/data/included.jsonl` (copy from candidates.jsonl).

### Step 4: Report
Print summary:
- Papers screened this batch: {N}
- Included: {N}
- Excluded: {N}
- Flagged → resolved include: {N}
- Flagged → resolved exclude: {N}
- Remaining unscreened: {N}

## Inference Quarantine Contract
- Each criterion evaluation is a SEPARATE inference judgment
- The decision rule combining criteria is DETERMINISTIC (no inference)
- If inference fails for any criterion (you cannot judge it):
  - Record met = "unclear" with evidence = "inference_failure: {reason}"
  - The paper gets flagged for full-text review
  - If full-text also fails: exclude with "insufficient_evidence"
  - Do NOT guess. Do NOT proceed without recording.

## Constraints
- Do NOT modify state.json
- Do NOT modify protocol.md
- Do NOT modify candidates.jsonl
- Append only to screening-log.jsonl
- Every paper must resolve to include or exclude — no paper left in flag_for_full_text state
