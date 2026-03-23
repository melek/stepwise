"""Scholar deterministic preprocessing.

Pure functions that transform inference inputs to improve oracle performance.
No I/O. No inference calls. Deterministic: same inputs produce same outputs.

Applies the Proven decompose.py pattern: rewrite inputs before the oracle
touches them to make the oracle's task more tractable.
"""

import re

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
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _split_sentences(text: str) -> list[str]:
    if not text.strip():
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _score_sentence(sentence: str, keywords: list[str]) -> int:
    sentence_lower = sentence.lower()
    return sum(1 for kw in keywords if kw in sentence_lower)


def preprocess_for_screening(
    abstract: str, title: str, criteria: list[dict]
) -> list[dict]:
    """Produce focused evidence windows for each screening criterion."""
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

        scored = [(i, s, _score_sentence(s, keywords)) for i, s in enumerate(sentences)]
        matched = [kw for kw in keywords if any(kw in s.lower() for s in sentences)]

        middle = [x for x in scored if x[0] not in (0, len(sentences) - 1)]
        middle.sort(key=lambda x: x[2], reverse=True)
        top_middle = middle[:3]

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


def _build_co_occurrence_graph(extractions: list[dict]) -> dict[str, set[str]]:
    concept_papers: dict[str, set[str]] = {}
    for ext in extractions:
        pid = ext.get("paper_id", "")
        for cid in ext.get("concepts_identified", []):
            concept_papers.setdefault(cid, set()).add(pid)

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
    """Organize extraction data into themed briefs for synthesis."""
    concept_map = {c["concept_id"]: c for c in concepts}
    adj = _build_co_occurrence_graph(extractions)
    clusters = _find_clusters(adj)

    paper_concepts: dict[str, set[str]] = {}
    paper_data: dict[str, dict] = {}
    for ext in extractions:
        pid = ext["paper_id"]
        paper_concepts[pid] = set(ext.get("concepts_identified", []))
        paper_data[pid] = ext

    themes = []
    for cluster in clusters:
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

    themes.sort(key=lambda t: t["paper_count"], reverse=True)
    return {"themes": themes}
