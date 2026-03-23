"""Scholar export functions.

Phase A: PRISMA Mermaid flow diagram generation.
Phase B: RIS and CSV export of JSONL data.

Pure functions. No I/O.
"""

import csv
import io


def generate_prisma_flow_diagram(metrics: dict) -> str:
    """Generate a PRISMA 2020-style flow diagram in Mermaid syntax."""
    sc = metrics.get("search_candidates", 0)
    sn = metrics.get("snowball_candidates", 0)
    dd = metrics.get("deduplicated", 0)
    sr = metrics.get("screened", 0)
    ex = metrics.get("excluded", 0)
    fl = metrics.get("flagged", 0)
    fe = metrics.get("ft_excluded", 0)
    inc = metrics.get("included", 0)

    return f"""```mermaid
graph TD
    A["Records identified through<br/>database searching<br/>(n = {sc})"] --> C["Records after deduplication<br/>(n = {dd})"]
    B["Records identified through<br/>snowballing<br/>(n = {sn})"] --> C
    C --> D["Records screened<br/>(n = {sr})"]
    D --> E["Records excluded<br/>(n = {ex})"]
    D --> F["Full-text assessed<br/>(n = {fl})"]
    F --> G["Studies included<br/>(n = {inc})"]
    F --> H["Full-text excluded<br/>with reasons<br/>(n = {fe})"]
```"""


def to_ris(records: list[dict]) -> str:
    """Convert paper records to RIS format.

    Produces RIS entries importable by Zotero, Mendeley, Covidence, Rayyan.
    """
    if not records:
        return ""

    lines = []
    for rec in records:
        lines.append("TY  - JOUR")
        if rec.get("title"):
            lines.append(f"TI  - {rec['title']}")
        for author in rec.get("authors", []):
            lines.append(f"AU  - {author}")
        if rec.get("year"):
            lines.append(f"PY  - {rec['year']}")
        if rec.get("venue"):
            lines.append(f"JO  - {rec['venue']}")
        if rec.get("doi"):
            lines.append(f"DO  - {rec['doi']}")
        if rec.get("abstract"):
            lines.append(f"AB  - {rec['abstract']}")
        if rec.get("id"):
            lines.append(f"ID  - {rec['id']}")
        lines.append("ER  -")
        lines.append("")

    return "\n".join(lines)


def to_csv(records: list[dict], fields: list[str]) -> str:
    """Convert paper records to CSV format.

    fields: list of field names to include as columns.
    Values containing commas are quoted per RFC 4180.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for rec in records:
        row = {}
        for f in fields:
            val = rec.get(f, "")
            if isinstance(val, list):
                val = "; ".join(str(v) for v in val)
            row[f] = val
        writer.writerow(row)
    return output.getvalue()
