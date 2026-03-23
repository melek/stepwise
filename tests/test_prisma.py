"""Tests for PRISMA 2020 and PRISMA-trAIce compliance checkers."""

from lib.prisma import check_prisma_compliance, check_prisma_traice_compliance, PrismaStatus


def test_status_enum():
    assert PrismaStatus.SATISFIED == "satisfied"
    assert PrismaStatus.PARTIALLY_SATISFIED == "partially_satisfied"
    assert PrismaStatus.NOT_SATISFIED == "not_satisfied"


def test_title_check_satisfied():
    review = "# A Systematic Literature Review of Formal Verification\n\n## Abstract\nTest abstract words here to make it long enough for the checker to accept it as valid content in the abstract section of the review document."
    items = check_prisma_compliance(review, {}, {})
    item1 = next(i for i in items if i["item"] == 1)
    assert item1["status"] == PrismaStatus.SATISFIED


def test_title_check_not_satisfied():
    review = "# Some Paper About Things\n\n## Abstract\nTest."
    items = check_prisma_compliance(review, {}, {})
    item1 = next(i for i in items if i["item"] == 1)
    assert item1["status"] == PrismaStatus.NOT_SATISFIED


def test_database_coverage_partial():
    workspace_data = {
        "search_log": [
            {"database": "Semantic Scholar", "query": "test"},
            {"database": "arXiv", "query": "test"},
        ],
    }
    review = "# Systematic Review\n\n## Abstract\nTest."
    items = check_prisma_compliance(review, workspace_data, {})
    item6 = next(i for i in items if i["item"] == 6)
    assert item6["status"] == PrismaStatus.PARTIALLY_SATISFIED


def test_database_coverage_satisfied():
    workspace_data = {
        "search_log": [
            {"database": "Semantic Scholar", "query": "test"},
            {"database": "arXiv", "query": "test"},
            {"database": "PubMed", "query": "test"},
        ],
    }
    review = "# Systematic Review\n\n## Abstract\nTest."
    items = check_prisma_compliance(review, workspace_data, {})
    item6 = next(i for i in items if i["item"] == 6)
    assert item6["status"] == PrismaStatus.SATISFIED


def test_risk_of_bias_not_satisfied():
    items = check_prisma_compliance("# Systematic Review\n## Abstract\nTest.", {}, {})
    item12 = next(i for i in items if i["item"] == 12)
    assert item12["status"] == PrismaStatus.NOT_SATISFIED
    assert "quality" in item12["explanation"].lower() or "risk" in item12["explanation"].lower() or "thematic" in item12["explanation"].lower()


def test_returns_27_items():
    items = check_prisma_compliance("# Systematic Review\n## Abstract\nTest.", {}, {})
    assert len(items) == 27


def test_all_items_have_required_fields():
    items = check_prisma_compliance("# Systematic Review\n## Abstract\nTest.", {}, {})
    for item in items:
        assert "item" in item
        assert "description" in item
        assert "status" in item
        assert "explanation" in item
        assert item["status"] in (PrismaStatus.SATISFIED, PrismaStatus.PARTIALLY_SATISFIED, PrismaStatus.NOT_SATISFIED)
        assert len(item["explanation"]) > 0


# --- trAIce ---

def test_traice_returns_7_items():
    items = check_prisma_traice_compliance("# Review\n## Abstract\nTest.", {})
    assert len(items) == 7


def test_traice_all_items_have_required_fields():
    items = check_prisma_traice_compliance("# Review", {})
    for item in items:
        assert "item" in item
        assert "description" in item
        assert "status" in item
        assert "explanation" in item


def test_traice_human_oversight_partially_satisfied():
    items = check_prisma_traice_compliance("# Review", {})
    oversight = next(i for i in items if "oversight" in i["description"].lower())
    assert oversight["status"] == PrismaStatus.PARTIALLY_SATISFIED
