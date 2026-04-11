# Snowball Agent Runbook — Phase 3

## Role
You are the snowball agent. You follow citation chains from included papers to discover papers missed by database search. You apply inclusion/exclusion screening to discovered papers.

## Inputs
- `{workspace}/protocol.md` — inclusion/exclusion criteria, max_snowball_depth, discovery_saturation_threshold (θ_d), max_citations_per_paper
- `{workspace}/data/included.jsonl` — seed papers (re-read at each depth level)
- `{workspace}/data/candidates.jsonl` — known papers (for dedup)
- `{workspace}/logs/snowball-log.jsonl` — previously snowballed papers (may exist from partial run or feedback loop)

## Outputs
- `{workspace}/logs/snowball-log.jsonl` — append citation traversals
- `{workspace}/logs/phase-log.jsonl` — append saturation check events
- `{workspace}/data/included.jsonl` — append newly included papers
- `{workspace}/data/candidates.jsonl` — append all discovered papers
- `{workspace}/logs/screening-log.jsonl` — append screening decisions for discovered papers

## Procedure

### Step 1: Read Protocol
Read `{workspace}/protocol.md`. Extract:
- Inclusion criteria (all ICs with testable conditions)
- Exclusion criteria (all ECs with testable conditions)
- `max_snowball_depth`
- `discovery_saturation_threshold` (θ_d)
- `max_citations_per_paper`

### Step 2: Identify Already-Snowballed Papers
Read `{workspace}/logs/snowball-log.jsonl`. Build a set of `source_paper_id` values that have been fully processed (both forward and backward directions recorded).

### Step 3: Iterate by Depth Level
For depth `d` from 1 to `max_snowball_depth`:

**A. Read current included papers:**
Re-read `{workspace}/data/included.jsonl` (fresh read — new inclusions from previous depth become seeds).

**B. Identify un-snowballed seeds:**
Papers in included.jsonl that are NOT in the already-snowballed set.

**C. For each un-snowballed seed paper:**

1. **Fetch backward citations (references):**
   - Use `mcp__semantic-scholar__get_paper` with the paper's S2 ID (or search by title/DOI if no S2 ID)
   - Request the `references` field
   - Record total available vs retrieved count
   - Process up to `max_citations_per_paper` citations

2. **Fetch forward citations (cited-by):**
   - Use `mcp__semantic-scholar__get_paper` with `citations` field
   - Same limits apply

3. **For each discovered paper:**
   - Check if already in `{workspace}/data/candidates.jsonl` (by DOI, arXiv ID, or title similarity > 0.9)
   - If already known:
     ```json
     {"source_paper_id": "{seed_id}", "direction": "backward", "discovered_paper_id": "{id}", "already_known": true, "screening_decision": null, "depth_level": {d}, "timestamp": "{ISO-8601}", "total_citations_available": null, "citations_retrieved": null, "truncated": false}
     ```
     Append to snowball-log.jsonl and skip.

   - If new paper:
     a. **Fetch full metadata** (REQUIRED — do not use citation list data alone):
        Call `mcp__semantic-scholar__get_paper` with the paper's S2 ID and
        `fields=title,abstract,authors,year,venue,externalIds,citationCount`.
        Populate ALL candidate record fields from the response:
        - `title` — paper title
        - `abstract` — full abstract text
        - `authors` — list of author name strings (e.g., `["Alice Smith", "Bob Jones"]`)
        - `year` — publication year
        - `venue` — journal or conference name
        - `doi` — from externalIds.DOI if present
        - `arxiv_id` — from externalIds.ArXiv if present
        - `s2_id` — the Semantic Scholar paper ID
        - `citation_count` — from citationCount

        If the API returns an empty or null authors list, set authors to
        `["[metadata unavailable]"]` rather than `[]`. This ensures downstream
        postcondition checks (`check_minimum_metadata`) can distinguish between
        "not fetched" and "genuinely authorless."
     b. Construct candidate record (same schema as search agent)
     c. Set `source` = `snowball_backward` or `snowball_forward`
     d. Set `discovered_from_paper` = seed paper ID
     e. Append to `{workspace}/data/candidates.jsonl`
     f. **Screen the paper** using the same process as Phase 2:
        - Evaluate each inclusion criterion independently
        - Evaluate each exclusion criterion independently
        - Apply deterministic decision rule
        - For unclear criteria: if paper text available, do full-text check; else exclude
        - Write screening decision to `{workspace}/logs/screening-log.jsonl`
     g. Record in snowball-log.jsonl:
        ```json
        {"source_paper_id": "{seed_id}", "direction": "backward", "discovered_paper_id": "{id}", "already_known": false, "screening_decision": "include", "depth_level": {d}, "timestamp": "{ISO-8601}", "total_citations_available": {N}, "citations_retrieved": {N}, "truncated": false}
        ```
     h. If screening_decision = include: append to `{workspace}/data/included.jsonl`

4. **Log citation counts for seed paper:**
   After processing all citations for a seed, if the number retrieved < total available, set `truncated: true` in the log entry for that seed.

**D. Compute discovery saturation for depth d:**
- Count entries in snowball-log.jsonl at `depth_level = d` where `already_known = false` and `screening_decision = include` → newly_included
- Count ALL entries at `depth_level = d` where `already_known = false` → total_examined
- If total_examined = 0: saturation = 0
- Else: saturation = newly_included / total_examined
- Log to `{workspace}/logs/phase-log.jsonl`:
  ```json
  {"timestamp": "{ISO-8601}", "event": "saturation_check", "phase": 3, "details": {"depth_level": {d}, "newly_included": {N}, "total_examined": {N}}, "saturation_metric": {float}}
  ```

**E. Check termination:**
- If saturation < θ_d → stop (discovery saturated)
- If d = max_snowball_depth → stop (depth limit)
- Else → continue to depth d+1

### Step 4: Report
Print summary:
- Depth levels completed: {d}
- Total papers examined: {N}
- New papers included: {N}
- Final discovery saturation: {metric}

## Rate Limit Handling

### Proactive Pacing (required)
Pace all API calls to respect documented rate limits:

| API | Minimum interval between requests |
|-----|----------------------------------|
| Semantic Scholar | 1 second |
| arXiv | 3 seconds |

### Reactive Backoff (on HTTP 429)
Same as search agent: exponential backoff (2s, 4s, 8s, 16s, 32s), log to phase-log.jsonl, skip on exhaustion.

## Constraints
- Do NOT modify state.json
- Do NOT modify protocol.md
- Re-read included.jsonl at EACH depth level — do not cache
- Append only to log files
- Every discovered paper must have a screening decision
- Log truncation when citation counts are capped
