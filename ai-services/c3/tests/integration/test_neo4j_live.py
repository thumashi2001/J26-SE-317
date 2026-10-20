"""
Live Neo4j CCKG checks. Excluded from the default run; execute with:  python -m pytest -m neo4j -q
Requires `docker compose up -d neo4j` and `bash database/neo4j/scripts/load_cckg.sh`.
"""

from pathlib import Path

import pytest
from dotenv import dotenv_values

from services.cckg.graph_adapter import CCKGGraphAdapter, CCKGUnavailableError

pytestmark = pytest.mark.neo4j


@pytest.fixture(scope="module")
def live_adapter():
    # conftest points NEO4J_URI at a closed port for offline tests, so read the real settings from .env
    cfg = dotenv_values(Path(__file__).resolve().parents[2] / ".env")
    try:
        adapter = CCKGGraphAdapter(
            uri=cfg.get("NEO4J_URI") or "bolt://127.0.0.1:7687",
            user=cfg.get("NEO4J_USER") or "neo4j",
            password=cfg.get("NEO4J_PASSWORD") or "change-me-in-development",
            strict=True,
        )
    except CCKGUnavailableError as exc:
        pytest.fail(f"Neo4j is not reachable: {exc}")
    yield adapter
    adapter.close()


def test_adapter_is_actually_live(live_adapter):
    status = live_adapter.status()
    assert live_adapter.is_live is True
    assert status["backend"] == "neo4j_live"


def test_graph_contains_seeded_ontology_without_blank_nodes(live_adapter):
    with live_adapter._driver.session() as session:
        unlabeled = session.run("MATCH (n) WHERE size(labels(n)) = 0 RETURN count(n) AS n").single()["n"]
        concepts = session.run("MATCH (c:Concept) RETURN count(c) AS n").single()["n"]
    assert unlabeled == 0, "seed scripts created empty unlabelled nodes"
    assert concepts >= 8


def test_concept_and_prerequisites_come_from_neo4j(live_adapter):
    concept = live_adapter.get_concept("branch coverage")
    assert concept["concept_id"] == "C-BRNC-COV"
    assert "statement coverage" in concept["prerequisites"]
    assert concept["citation"]


def test_prerequisite_closure(live_adapter):
    names = [c["name"] for c in live_adapter.get_prerequisite_closure(["microservices"])]
    assert names.index("high cohesion") < names.index("loose coupling") < names.index("microservices")


def test_graphrag_context_reports_live_backend(live_adapter):
    res = live_adapter.retrieve_graphrag_context(question_id="DIAG-SE3010-001")
    assert res["backend_provider"] == "neo4j_live"
    assert res["target_concepts"]
