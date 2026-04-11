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

**Query syntax note:** Semantic Scholar's search endpoint accepts plain-text
keyword queries only. Boolean operators (AND, OR, NOT) and quoted phrases are
NOT supported — they will be treated as literal search terms. If the protocol
specifies Boolean queries for Semantic Scholar, convert them to space-separated
keywords before executing. Use the `fieldsOfStudy`, `year`, and `venue` API
parameters for structured filtering instead of query-level Boolean logic.

- Use `mcp__semantic-scholar__search_paper` with the query string
- Parameters: query={query}, limit={max_results_per_query}, year={start}-{end}
- Record each result's: paperId, title, abstract, authors, year, venue, citationCount, externalIds (DOI, ArXiv)

**arXiv:**
- Use `mcp__arxiv__search_papers` with the query string
- Parameters: query={query}, max_results={max_results_per_query}
- Record each result's: arxiv_id, title, abstract (summary), authors, published year, categories

**PubMed (if available):**
- Check if `mcp__pubmed__search` is in the tool list. If not, skip and log:
  ```json
  {"timestamp": "{ISO-8601}", "event": "pubmed_unavailable", "phase": 1, "details": {"reason": "MCP not configured"}}
  ```
- Use `mcp__pubmed__search` with the query string
- Parameters: query={query}, max_results={max_results_per_query}
- Record each result's: PMID, title, abstract, authors, year, journal, DOI
- Map PMID to canonical ID: use DOI if available, else `pmid:{PMID}`

**paper-search-mcp (if available):**
- Check if `mcp__paper_search__search_papers` is in the tool list. If not, skip and log:
  ```json
  {"timestamp": "{ISO-8601}", "event": "paper_search_unavailable", "phase": 1, "details": {"reason": "MCP not configured"}}
  ```
- Use `mcp__paper_search__search_papers` with the query string
- This searches 20+ databases simultaneously (IEEE Xplore, ACM, DBLP, CrossRef, OpenAlex, CORE, etc.)
- Deduplicate results against existing candidates using DOI matching
- Record source as "paper-search-mcp" in `discovered_by_query`

After each query, append to `logs/search-log.jsonl`:
```json
{"query": "{query}", "database": "{database}", "timestamp": "{ISO-8601}", "result_count": {N}, "parameters": {"limit": {N}, "year_range": "{start}-{end}"}}
```

Database names MUST use canonical form: `semantic_scholar`, `arxiv`, `pubmed`, `paper_search_mcp`.

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
1. Compute `safe_id` = canonical ID with `/` and `:` replaced by `_`
2. **Cache check:** If `~/research/.paper-cache/{safe_id}.txt` exists, copy it to `{workspace}/papers/{safe_id}.txt`, update `pdf_path`, log with `"status": "cache_hit"`, and skip to the next paper
3. Call `mcp__arxiv__download_paper` with the arXiv ID
4. Poll `mcp__arxiv__download_paper` with `check_status: true` until status is `"success"` or `"error"` (conversion takes a few seconds)
5. On success: call `mcp__arxiv__read_paper` to get the text content, then write it to `{workspace}/papers/{safe_id}.txt`. Also copy to `~/research/.paper-cache/{safe_id}.txt`. Update the candidate's `pdf_path` field.
6. On error: log the failure and continue to the next paper

Log every download attempt to `{workspace}/logs/download-log.jsonl`:
```json
{"paper_id": "{id}", "arxiv_id": "{arxiv_id}", "source": "arxiv", "timestamp": "{ISO-8601}", "status": "success|error", "error_message": null}
```

This step may involve many papers. Process all of them — do not skip downloads to save time. If rate-limited, apply the backoff procedure in the Rate Limit Handling section below.

### Step 6: Enrich Metadata
For candidates found only on arXiv (no S2 ID):
- Use `mcp__semantic-scholar__search_paper` with the exact title
- If a match is found: add the S2 ID, citation count, and venue to the candidate record

For candidates found only on Semantic Scholar (no arXiv ID):
- Check if `externalIds` contains an arXiv ID
- If yes: download the paper (Step 5)

### Step 6b: Download Papers (Unpaywall)
For each candidate that has a DOI but NO `pdf_path` (i.e., arXiv download was not available or failed):
1. Compute `safe_id` = canonical ID with `/` and `:` replaced by `_`
2. **Cache check:** If `~/research/.paper-cache/{safe_id}.txt` exists, copy it to `{workspace}/papers/{safe_id}.txt`, update `pdf_path`, log with `"status": "cache_hit"`, and skip to the next paper
3. Call `mcp__unpaywall__unpaywall_get_fulltext_links` with the candidate's DOI
4. If an open-access link is returned:
   a. Call `mcp__unpaywall__unpaywall_fetch_pdf_text` with the DOI
   b. Write the extracted text to `{workspace}/papers/{safe_id}.txt`. Also copy to `~/research/.paper-cache/{safe_id}.txt`.
   c. Update the candidate's `pdf_path` field
5. If no open-access link: skip (paper remains abstract-only)

Log every Unpaywall attempt to `{workspace}/logs/download-log.jsonl`:
```json
{"paper_id": "{id}", "doi": "{doi}", "source": "unpaywall", "timestamp": "{ISO-8601}", "status": "success|no_oa|error", "error_message": null}
```

Pace Unpaywall calls at 1 per second (Unpaywall's rate limit is 100K/day but requests politeness). If rate-limited, apply the same backoff procedure as arXiv.

**Note:** This step only runs if the Unpaywall MCP is available. If `mcp__unpaywall__unpaywall_get_fulltext_links` is not in the tool list, skip this step entirely and log:
```json
{"timestamp": "{ISO-8601}", "event": "unpaywall_unavailable", "phase": 1, "details": {"reason": "MCP not configured"}}
```

### Step 7: Write Final Candidates
Append all deduplicated candidates to `{workspace}/data/candidates.jsonl` (one JSON object per line). If the file already exists (e.g., from a prior partial run), append only candidates not already present (check by canonical ID).

### Step 8: Report
Print summary:
- Queries executed: {N}
- Total raw results: {N}
- Unique candidates after dedup: {N}
- Papers downloaded (arXiv): {N}
- Papers downloaded (Unpaywall): {N}
- Papers with full text: {N} / {total candidates}

## Rate Limit Handling

### Proactive Pacing (required)
Pace all API calls to respect documented rate limits. Do NOT fire requests as fast as possible and rely on 429 backoff.

| API | Minimum interval between requests |
|-----|----------------------------------|
| Semantic Scholar | 1 second |
| arXiv | 3 seconds |
| Unpaywall | 1 second |
| PubMed | 0.33 seconds (3 RPS) |
| Scite | 1 second |

Use `sleep` or equivalent between consecutive calls to the same API.

### Reactive Backoff (on HTTP 429)
If a 429 is received despite proactive pacing:
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
