# Search Agent Runbook — Phase 1

## Role
You are the search agent. You execute database searches and collect candidate papers. You use ZERO inference — this is pure API calls and data assembly.

## Inputs
- `{workspace}/protocol.md` — search terms, databases, date range, max_results_per_query
- Workspace path (provided by orchestrator)

## Outputs (append-only)
- `{workspace}/logs/search-log.jsonl` — every query executed
- `{workspace}/data/candidates.jsonl` — deduplicated candidate papers

## Procedure

### Step 1: Read Protocol
Read `{workspace}/protocol.md`. Extract:
- All (database, query string) pairs from the Search Terms table
- `date_range.start` and `date_range.end`
- `max_results_per_query`
- `databases` list

### Step 2: Execute Searches
For each (database, query) pair:

**Semantic Scholar:**
- Use `mcp__semantic-scholar__search_paper` with the query string
- Parameters: query={query}, limit={max_results_per_query}, year={start}-{end}
- Record each result's: paperId, title, abstract, authors, year, venue, citationCount, externalIds (DOI, ArXiv)

**arXiv:**
- Use `mcp__arxiv__search_papers` with the query string
- Parameters: query={query}, max_results={max_results_per_query}
- Record each result's: arxiv_id, title, abstract (summary), authors, published year, categories

After each query, append to `logs/search-log.jsonl`:
```json
{"query": "{query}", "database": "{database}", "timestamp": "{ISO-8601}", "result_count": {N}, "parameters": {"limit": {N}, "year_range": "{start}-{end}"}}
```

### Step 3: Build Candidate Records
For each result, construct a candidate record:
```json
{
  "id": "{canonical_id}",
  "doi": "{doi or null}",
  "arxiv_id": "{arxiv_id or null}",
  "s2_id": "{s2_id or null}",
  "title": "{title}",
  "abstract": "{abstract}",
  "authors": ["{author1}", "{author2}"],
  "year": {year},
  "venue": "{venue or null}",
  "citation_count": {count or null},
  "source": "search",
  "discovered_at": "{ISO-8601}",
  "discovered_by_query": "{query}",
  "discovered_from_paper": null,
  "also_found_via": [],
  "pdf_path": null,
  "zotero_key": null
}
```

**Canonical ID resolution (priority order):**
1. DOI (if available) — use as `id`
2. arXiv ID (if available) — use as `id`
3. Semantic Scholar ID — use as `id`

### Step 4: Deduplicate
Before writing each candidate:
1. Check if any existing record in candidates.jsonl shares:
   - Same DOI (both non-null)
   - Same arXiv ID (both non-null)
   - Title similarity > 0.9 (normalize both titles: lowercase, strip punctuation, compare character overlap / max length)
2. If duplicate found:
   - Keep the record with more non-null metadata fields
   - Add the other source to `also_found_via`
   - Do NOT write a new record
3. If no duplicate: append to candidates.jsonl

### Step 5: Download Papers (arXiv)
For each candidate with an arXiv ID:
1. Call `mcp__arxiv__download_paper` with the arXiv ID
2. Poll `mcp__arxiv__download_paper` with `check_status: true` until status is `"success"` or `"error"` (conversion takes a few seconds)
3. On success: call `mcp__arxiv__read_paper` to get the text content, then write it to `{workspace}/papers/{canonical_id}.txt` (replace `/` and `:` in the ID with `_`). Update the candidate's `pdf_path` field.
4. On error: log the failure and continue to the next paper

Log every download attempt to `{workspace}/logs/download-log.jsonl`:
```json
{"paper_id": "{id}", "arxiv_id": "{arxiv_id}", "timestamp": "{ISO-8601}", "status": "success|error", "error_message": null}
```

This step may involve many papers. Process all of them — do not skip downloads to save time. If rate-limited, apply the backoff procedure in the Rate Limit Handling section below.

### Step 6: Enrich Metadata
For candidates found only on arXiv (no S2 ID):
- Use `mcp__semantic-scholar__search_paper` with the exact title
- If a match is found: add the S2 ID, citation count, and venue to the candidate record

For candidates found only on Semantic Scholar (no arXiv ID):
- Check if `externalIds` contains an arXiv ID
- If yes: download the paper (Step 5)

### Step 7: Write Final Candidates
Append all deduplicated candidates to `{workspace}/data/candidates.jsonl` (one JSON object per line). If the file already exists (e.g., from a prior partial run), append only candidates not already present (check by canonical ID).

### Step 8: Report
Print summary:
- Queries executed: {N}
- Total raw results: {N}
- Unique candidates after dedup: {N}
- Papers downloaded: {N}

## Rate Limit Handling
On HTTP 429 or rate limit errors:
- Wait with exponential backoff: 2s, 4s, 8s, 16s, 32s (max 5 retries)
- Log each rate limit event to `{workspace}/logs/phase-log.jsonl`:
  ```json
  {"timestamp": "{ISO-8601}", "event": "rate_limit", "phase": 1, "details": {"database": "{db}", "query": "{query}", "retry_number": {N}, "wait_seconds": {N}}}
  ```
- If all retries exhausted: log the failure and skip that query. The orchestrator will detect the incomplete work via postcondition checks.

## Constraints
- Do NOT evaluate paper relevance. That is Phase 2's job.
- Do NOT modify state.json. The orchestrator manages state.
- Do NOT modify protocol.md.
- Append only to log files. Never delete or modify existing entries.
