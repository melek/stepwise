"""Scholar export functions.

Phase A: PRISMA Mermaid flow diagram generation.
Phase B (future): RIS and CSV export of JSONL data.

Pure functions. No I/O.
"""


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
