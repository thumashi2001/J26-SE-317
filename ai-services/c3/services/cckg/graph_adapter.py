"""
AdaptiveLearnSE Component 3 — Co-Evolving Curriculum Knowledge Graph (CCKG) Adapter
Implements GraphRAG retrieval for curriculum concepts, prerequisite graphs, and citations.
Operates against live Neo4j when available, with a deterministic in-memory ontology fallback.
"""

import logging
import os
from typing import Any

logger = logging.getLogger("c3.cckg.adapter")

# Authoritative In-Memory Curriculum Knowledge Graph (Synchronized with database/neo4j/cypher/)
CANONICAL_MODULES = {
    "SE3010": {"title": "Software Architecture & Design Patterns", "credits": 4},
    "SE3020": {"title": "Database Systems & Distributed Storage", "credits": 4},
    "SE3030": {"title": "Software Quality Assurance & Metrics", "credits": 4},
    "SE3040": {"title": "Enterprise Application Development", "credits": 4},
}

CANONICAL_TOPICS = {
    "TOPIC-SE3010-MOD": {"name": "Modular Abstraction & Decomposition", "module_id": "SE3010"},
    "TOPIC-SE3010-PAT": {"name": "Architectural Patterns & Styles", "module_id": "SE3010"},
    "TOPIC-SE3020-NORM": {"name": "Relational Schema Normalization", "module_id": "SE3020"},
    "TOPIC-SE3020-TRAN": {"name": "Transaction Isolation & ACID Properties", "module_id": "SE3020"},
    "TOPIC-SE3030-COV": {"name": "Structural Coverage & Control Flow Testing", "module_id": "SE3030"},
    "TOPIC-SE3030-MET": {"name": "Software Metrics & Quality Standards", "module_id": "SE3030"},
    "TOPIC-SE3040-API": {"name": "RESTful Service Design & Microservices", "module_id": "SE3040"},
}

CANONICAL_CONCEPTS = {
    "high cohesion": {
        "concept_id": "C-COHESION",
        "topic_id": "TOPIC-SE3010-MOD",
        "description": "Internal module coherence where all elements collaborate to perform a single well-defined task.",
        "prerequisites": [],
        "citation": "SLIIT SE3010 Lecture 03 (Modularity), Slide 14-22"
    },
    "loose coupling": {
        "concept_id": "C-COUPLING",
        "topic_id": "TOPIC-SE3010-MOD",
        "description": "Minimizing inter-module dependencies to permit independent evolution and testing.",
        "prerequisites": ["high cohesion"],
        "citation": "SLIIT SE3010 Lecture 03 (Modularity), Slide 14-22"
    },
    "microservices": {
        "concept_id": "C-MICROSERVICES",
        "topic_id": "TOPIC-SE3010-PAT",
        "description": "Distributed architectural pattern organizing applications into autonomous, independently deployable services.",
        "prerequisites": ["loose coupling"],
        "citation": "SLIIT SE3010 Lecture 07 (Microservices), Slide 04-18"
    },
    "statement coverage": {
        "concept_id": "C-STMT-COV",
        "topic_id": "TOPIC-SE3030-COV",
        "description": "Metric measuring the proportion of executable statements executed by a test suite.",
        "prerequisites": [],
        "citation": "SLIIT SE3030 Lecture 04 (White-Box Testing), Slide 08-19"
    },
    "branch coverage": {
        "concept_id": "C-BRNC-COV",
        "topic_id": "TOPIC-SE3030-COV",
        "description": "Metric measuring whether each decision branch outcome (true/false) has been exercised.",
        "prerequisites": ["statement coverage"],
        "citation": "SLIIT SE3030 Lecture 04 (White-Box Testing), Slide 08-19"
    },
    "test adequacy": {
        "concept_id": "C-TEST-ADEQ",
        "topic_id": "TOPIC-SE3030-COV",
        "description": "Criteria determining whether test suites sufficiently exercise program logic and failure modes.",
        "prerequisites": ["branch coverage"],
        "citation": "SLIIT SE3030 Lecture 05 (Test Adequacy & Mutation), Slide 02-14"
    },
    "relational normalization": {
        "concept_id": "C-NORMALIZATION",
        "topic_id": "TOPIC-SE3020-NORM",
        "description": "Systematic decomposition of relations to eliminate anomalies and redundancy (1NF, 2NF, 3NF, BCNF).",
        "prerequisites": [],
        "citation": "SLIIT SE3020 Lecture 02 (Normalization), Slide 10-35"
    },
    "acid transactions": {
        "concept_id": "C-ACID",
        "topic_id": "TOPIC-SE3020-TRAN",
        "description": "Database transaction guarantees: Atomicity, Consistency, Isolation, and Durability.",
        "prerequisites": [],
        "citation": "SLIIT SE3020 Lecture 06 (Transactions & Concurrency), Slide 05-28"
    }
}

CANONICAL_QUESTION_MAP = {
    "SE3010-Q01": {
        "module_id": "SE3010",
        "concepts": ["high cohesion", "loose coupling", "microservices"]
    },
    "DIAG-SE3010-001": {
        "module_id": "SE3030",
        "concepts": ["statement coverage", "branch coverage", "test adequacy"]
    }
}


class CCKGUnavailableError(RuntimeError):
    """Raised in strict mode when live Neo4j cannot be reached."""


class CCKGGraphAdapter:
    """Graph Adapter providing unified GraphRAG queries across live Neo4j and in-memory store."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        strict: bool | None = None,
    ):
        # strict: fail instead of silently using the in-memory ontology (required for real experiments)
        self.strict = strict if strict is not None else os.getenv("C3_CCKG_STRICT", "0") == "1"
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "change-me-in-development")  # matches docker-compose.yml
        self._driver = None
        self._is_live_neo4j = False
        self._init_connection()

    def _init_connection(self):
        try:
            import neo4j
            self._driver = neo4j.GraphDatabase.driver(
                self.uri, auth=(self.user, self.password), max_connection_lifetime=30
            )
            # Test connectivity with a quick verify
            self._driver.verify_connectivity()
            self._is_live_neo4j = True
            logger.info(f"Connected to live Neo4j CCKG at {self.uri}")
        except Exception as e:
            self._is_live_neo4j = False
            if self.strict:
                raise CCKGUnavailableError(f"Live Neo4j required (strict mode) but not reachable at {self.uri}: {e}") from e
            logger.info(f"Live Neo4j not reachable ({e}). Using canonical in-memory CCKG store.")

    @property
    def is_live(self) -> bool:
        return self._is_live_neo4j

    def status(self) -> dict[str, Any]:
        """Backend state for diagnostics; counts reflect the in-memory ontology actually loaded."""
        return {
            "is_live_neo4j": self._is_live_neo4j,
            "backend": "neo4j_live" if self._is_live_neo4j else "in_memory_cckg_ontology",
            "strict": self.strict,
            "modules_count": len(CANONICAL_MODULES),
            "concepts_count": len(CANONICAL_CONCEPTS),
        }

    def close(self):
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass

    def get_concept(self, concept_name: str) -> dict[str, Any] | None:
        """Retrieve concept metadata, prerequisite dependencies, and curriculum citations."""
        c_name = concept_name.lower().strip()
        if self._is_live_neo4j:
            try:
                with self._driver.session() as session:
                    res = session.run(
                        """
                        MATCH (c:Concept) WHERE toLower(c.name) = $name
                        OPTIONAL MATCH (p:Concept)-[:PREREQUISITE_OF]->(c)
                        OPTIONAL MATCH (c)-[:CITED_IN]->(r:CurriculumResource)
                        RETURN c.concept_id AS id, c.name AS name, c.description AS desc,
                               collect(DISTINCT p.name) AS prerequisites,
                               r.citation AS citation
                        """,
                        name=c_name
                    )
                    record = res.single()
                    if record and record["name"]:
                        return {
                            "concept_id": record["id"],
                            "name": record["name"],
                            "description": record["desc"],
                            "prerequisites": [p.lower() for p in record["prerequisites"] if p],
                            "citation": record["citation"] or "Curriculum Syllabus"
                        }
            except Exception as e:
                logger.warning(f"Neo4j query failed ({e}); falling back to in-memory store.")

        # In-memory store fallback
        if c_name in CANONICAL_CONCEPTS:
            data = CANONICAL_CONCEPTS[c_name]
            return {
                "concept_id": data["concept_id"],
                "name": c_name,
                "description": data["description"],
                "prerequisites": list(data["prerequisites"]),
                "citation": data["citation"]
            }
        return None

    def get_question_concepts(self, question_id: str) -> list[str]:
        """Get expected concepts evaluated by a question."""
        if self._is_live_neo4j:
            try:
                with self._driver.session() as session:
                    res = session.run(
                        """
                        MATCH (q:Question {question_id: $qid})-[:EVALUATES_CONCEPT]->(c:Concept)
                        RETURN c.name AS concept_name
                        """,
                        qid=question_id
                    )
                    concepts = [record["concept_name"].lower() for record in res]
                    if concepts:
                        return concepts
            except Exception as e:
                logger.warning(f"Neo4j question concept query failed ({e}).")

        # In-memory fallback
        if question_id in CANONICAL_QUESTION_MAP:
            return list(CANONICAL_QUESTION_MAP[question_id]["concepts"])
        return []

    def get_prerequisite_closure(self, concepts: list[str]) -> list[dict[str, Any]]:
        """Traverse transitive prerequisite graph closure for a set of concepts."""
        closure = []
        visited = set()

        def dfs(c_name: str):
            c_norm = c_name.lower().strip()
            if c_norm in visited:
                return
            visited.add(c_norm)
            info = self.get_concept(c_norm)
            if info:
                for prereq in info.get("prerequisites", []):
                    dfs(prereq)
                closure.append(info)

        for c in concepts:
            dfs(c)
        return closure

    def retrieve_graphrag_context(self, question_id: str, concepts: list[str] | None = None) -> dict[str, Any]:
        """
        Execute GraphRAG retrieval: extracts ontology nodes, prerequisite chains,
        definitions, and curriculum citations for question and related concepts.
        """
        target_concepts = set()
        if question_id:
            target_concepts.update(self.get_question_concepts(question_id))
        if concepts:
            target_concepts.update([c.lower().strip() for c in concepts])

        prereq_graph = self.get_prerequisite_closure(list(target_concepts))

        context_lines = []
        citations = []
        for node in prereq_graph:
            c_name = node["name"]
            c_desc = node.get("description", "")
            prereqs = node.get("prerequisites", [])
            cite = node.get("citation", "")

            line = f"Concept: {c_name.title()}."
            if prereqs:
                line += f" (Requires prerequisite: {', '.join(prereqs)})."
            if c_desc:
                line += f" Definition: {c_desc}"
            context_lines.append(line)
            if cite and cite not in citations:
                citations.append(cite)

        return {
            "question_id": question_id,
            "target_concepts": list(target_concepts),
            "graph_nodes_retrieved": len(prereq_graph),
            "prerequisite_chain": [n["name"] for n in prereq_graph],
            "graphrag_context_text": "\n".join(context_lines),
            "curriculum_citations": citations,
            "backend_provider": "neo4j_live" if self._is_live_neo4j else "in_memory_cckg_ontology"
        }


_adapter_instance = None


def get_cckg_adapter() -> CCKGGraphAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = CCKGGraphAdapter()
    return _adapter_instance
