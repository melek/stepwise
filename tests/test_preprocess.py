"""Tests for deterministic preprocessing functions."""

from lib.preprocess import preprocess_for_screening, preprocess_for_synthesis


# --- Screening preprocessor ---

def test_returns_evidence_window_per_criterion():
    abstract = (
        "This paper presents a novel approach to formal verification. "
        "We use model checking to verify safety properties. "
        "The approach is evaluated on three benchmarks. "
        "Results show 95% coverage of safety requirements. "
        "We conclude that formal methods improve reliability."
    )
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "addresses formal verification"},
        {"criterion_id": "IC2", "testable_condition": "reports empirical results"},
    ]
    results = preprocess_for_screening(abstract, "A Formal Verification Study", criteria)
    assert len(results) == 2
    assert results[0]["criterion_id"] == "IC1"
    assert results[1]["criterion_id"] == "IC2"
    assert "evidence_window" in results[0]
    assert "full_abstract" in results[0]
    assert results[0]["full_abstract"] == abstract


def test_evidence_window_contains_relevant_sentences():
    abstract = (
        "Machine learning is popular. "
        "We study neural networks. "
        "Formal verification ensures correctness. "
        "Our method verifies neural network properties. "
        "The conclusion summarizes findings."
    )
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "formal verification of neural networks"},
    ]
    results = preprocess_for_screening(abstract, "Test", criteria)
    window = results[0]["evidence_window"]
    assert "verification" in window.lower()


def test_evidence_window_includes_first_and_last_sentence():
    abstract = (
        "First sentence of abstract. "
        "Middle content here. "
        "More middle content. "
        "Last sentence of abstract."
    )
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "something unrelated"},
    ]
    results = preprocess_for_screening(abstract, "Test", criteria)
    window = results[0]["evidence_window"]
    assert "First sentence" in window
    assert "Last sentence" in window


def test_keywords_matched_populated():
    abstract = "We apply formal verification using Dafny to prove correctness."
    criteria = [
        {"criterion_id": "IC1", "testable_condition": "formal verification correctness"},
    ]
    results = preprocess_for_screening(abstract, "Test", criteria)
    assert "keywords_matched" in results[0]
    assert len(results[0]["keywords_matched"]) > 0


def test_empty_abstract_returns_empty_window():
    results = preprocess_for_screening("", "Test", [{"criterion_id": "IC1", "testable_condition": "test"}])
    assert results[0]["evidence_window"] == ""
    assert results[0]["full_abstract"] == ""


# --- Synthesis preprocessor ---

def test_clusters_concepts_by_co_occurrence():
    extractions = [
        {"paper_id": "p1", "source": "full_text", "fields": [], "concepts_identified": ["formal-verification", "model-checking"]},
        {"paper_id": "p2", "source": "full_text", "fields": [], "concepts_identified": ["formal-verification", "theorem-proving"]},
        {"paper_id": "p3", "source": "abstract", "fields": [], "concepts_identified": ["neural-networks", "deep-learning"]},
    ]
    concepts = [
        {"concept_id": "formal-verification", "label": "Formal Verification", "definition": "Math proofs for correctness", "frequency": 2},
        {"concept_id": "model-checking", "label": "Model Checking", "definition": "Exhaustive state exploration", "frequency": 1},
        {"concept_id": "theorem-proving", "label": "Theorem Proving", "definition": "Logical proof construction", "frequency": 1},
        {"concept_id": "neural-networks", "label": "Neural Networks", "definition": "Connectionist computing models", "frequency": 1},
        {"concept_id": "deep-learning", "label": "Deep Learning", "definition": "Multi-layer neural network training", "frequency": 1},
    ]
    result = preprocess_for_synthesis(extractions, concepts)
    assert "themes" in result
    assert len(result["themes"]) >= 2


def test_themes_ranked_by_paper_count():
    extractions = [
        {"paper_id": "p1", "source": "full_text", "fields": [], "concepts_identified": ["aa", "bb"]},
        {"paper_id": "p2", "source": "full_text", "fields": [], "concepts_identified": ["aa", "bb"]},
        {"paper_id": "p3", "source": "full_text", "fields": [], "concepts_identified": ["aa", "bb"]},
        {"paper_id": "p4", "source": "abstract", "fields": [], "concepts_identified": ["cc", "dd"]},
    ]
    concepts = [
        {"concept_id": "aa", "label": "A", "definition": "Concept A definition text", "frequency": 3},
        {"concept_id": "bb", "label": "B", "definition": "Concept B definition text", "frequency": 3},
        {"concept_id": "cc", "label": "C", "definition": "Concept C definition text", "frequency": 1},
        {"concept_id": "dd", "label": "D", "definition": "Concept D definition text", "frequency": 1},
    ]
    result = preprocess_for_synthesis(extractions, concepts)
    assert result["themes"][0]["paper_count"] >= result["themes"][1]["paper_count"]


def test_data_completeness_flagged():
    extractions = [
        {
            "paper_id": "p1", "source": "abstract",
            "fields": [
                {"field_name": "methodology", "value": "extraction_failed", "confidence": "low", "source_location": "abstract"},
                {"field_name": "results", "value": "extraction_failed", "confidence": "low", "source_location": "abstract"},
                {"field_name": "title", "value": "Some Title", "confidence": "medium", "source_location": "abstract"},
            ],
            "concepts_identified": ["aa", "bb"],
        },
    ]
    concepts = [
        {"concept_id": "aa", "label": "AA", "definition": "Concept AA def text", "frequency": 1},
        {"concept_id": "bb", "label": "BB", "definition": "Concept BB def text", "frequency": 1},
    ]
    result = preprocess_for_synthesis(extractions, concepts)
    theme = result["themes"][0]
    paper = [p for p in theme["papers"] if p["paper_id"] == "p1"][0]
    assert paper["data_completeness"] < 0.5
