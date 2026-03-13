"""Scholar section parser.

Pure functions for splitting markdown text into sections at heading
boundaries. No file I/O.

Verified properties:
- Coverage: every character belongs to exactly one section
- Contiguity: adjacent sections share boundaries (no gaps/overlaps)
- Ordering: section boundaries are monotonically increasing
- Heading level range: 0-6, 0 only for preamble
"""

import re


def parse_sections(text: str) -> list[dict]:
    """Parse markdown text into sections at heading boundaries.

    Returns list of dicts with keys: heading, level, start, end.
    Each section's text is text[start:end].
    """
    if not text:
        return []

    # Find all heading positions
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    headings = list(heading_pattern.finditer(text))

    if not headings:
        return [{"heading": "preamble", "level": 0, "start": 0, "end": len(text)}]

    sections = []

    # Preamble: text before first heading (if non-whitespace content exists)
    first_start = headings[0].start()
    if first_start > 0 and text[:first_start].strip():
        sections.append({
            "heading": "preamble",
            "level": 0,
            "start": 0,
            "end": first_start,
        })

    # Each heading starts a section
    for i, match in enumerate(headings):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        start = match.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        sections.append({
            "heading": heading_text,
            "level": level,
            "start": start,
            "end": end,
        })

    # If no preamble, ensure coverage starts at 0
    if sections and sections[0]["start"] > 0 and not text[:sections[0]["start"]].strip():
        sections[0] = {**sections[0], "start": 0}

    return sections


def find_sections_by_pattern(
    sections: list[dict], patterns: list[str]
) -> list[dict]:
    """Return sections whose heading matches any pattern (case-insensitive substring).

    Returns a subsequence of the input list (preserves order).
    """
    patterns_lower = [p.lower() for p in patterns]
    return [
        s for s in sections
        if any(p in s["heading"].lower() for p in patterns_lower)
    ]


# Field-to-section mapping: common extraction field names → likely heading patterns
FIELD_SECTION_MAP: dict[str, list[str]] = {
    "methodology": ["method", "approach", "design", "experimental", "procedure"],
    "results": ["result", "finding", "evaluation", "experiment"],
    "limitations": ["limitation", "threat", "weakness"],
    "contributions": ["contribution", "introduction", "abstract"],
    "future_work": ["future", "conclusion", "discussion"],
    "related_work": ["related", "background", "literature", "prior"],
    "dataset": ["data", "dataset", "corpus", "benchmark"],
    "metrics": ["metric", "measure", "evaluation"],
    "architecture": ["architecture", "system", "framework", "model", "design"],
    "theory": ["theory", "formal", "proof", "definition"],
}


def get_extraction_context(
    text: str, field_name: str, max_chars: int = 8000
) -> dict:
    """Get focused context for extracting a specific field.

    Returns {"sections_used": [heading, ...], "context": "text...", "source": "full_text"|"full_document"}.
    If field maps to known sections and those sections exist, returns only those sections' text.
    Otherwise returns the full text (truncated to max_chars).
    """
    sections = parse_sections(text)

    # Normalize field name for lookup
    field_key = field_name.lower().replace(" ", "_").replace("-", "_")
    patterns = FIELD_SECTION_MAP.get(field_key, [])

    if patterns:
        matched = find_sections_by_pattern(sections, patterns)
        if matched:
            context_parts = []
            headings_used = []
            total = 0
            for s in matched:
                section_text = text[s["start"]:s["end"]]
                if total + len(section_text) > max_chars:
                    remaining = max_chars - total
                    if remaining > 200:  # worth including partial
                        context_parts.append(section_text[:remaining])
                        headings_used.append(s["heading"])
                    break
                context_parts.append(section_text)
                headings_used.append(s["heading"])
                total += len(section_text)
            return {
                "sections_used": headings_used,
                "context": "".join(context_parts),
                "source": "full_text",
            }

    # Fallback: return full text (truncated)
    return {
        "sections_used": [s["heading"] for s in sections],
        "context": text[:max_chars],
        "source": "full_document",
    }
