"""Frozen C1 practiseable topic registry for SE training protocol S1.

Catalogue ID: ``c1-practice-full-2026.10``
Scope decision: S1 — 46 current C1 practice IDs with semester eligibility masks.
This is an implementation scope choice, **not** proposal-PDF verification.

Source pins: see SOURCE_COMMIT / SOURCE_FILE_HASHES / CONTENT_MODULE_FILE_HASHES.
Re-audit confirmed identical 46-topic set/order/module/semester; SHA1 pins updated
for C1 restructure (practiceQuestions re-exports TOPICS). Do not remap v0 IDs.

Order = C1 ``content/index.js`` MODULES insertion
(csse → spm → uee → ds → dsys → sa → sepqm → af).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CATALOGUE_ID = "c1-practice-full-2026.10"
SCOPE_DECISION = "S1"
SOURCE_COMMIT = "11c4920a8f5e5ddbd9031a2deb76e07a2b47863e"
# Original freeze pins (pre-refactor of practiceQuestions → content modules).
SOURCE_FILE_HASHES_AT_FREEZE = {
    "backend/src/modules/c1/data/practiceQuestions.js": "047185d3840a74ea113c886e6ffbc82f4c82064e",
    "backend/src/modules/c1/data/content/index.js": "a7c3014434a815aeee32e650b04a6f1db476a063",
    "frontend/src/utils/topicLabels.js": "db3bc9e29065b802b36791c659ae6a0c05134738",
}
# Working-tree re-audit (same HEAD): topic set/order/module/semester still match;
# only file bytes drifted after practiceQuestions became a TOPICS re-export.
SOURCE_FILE_HASHES = {
    "backend/src/modules/c1/data/practiceQuestions.js": "132e6a9f7ec59cbd8920dd7d975a8d27f7936572",
    "backend/src/modules/c1/data/content/index.js": "adb1db0443072f30bfe618a214a39fc677aa79a7",
    "frontend/src/utils/topicLabels.js": "a604d11abd4102f4d616a24b437ce808d6e8a142",
}
CONTENT_MODULE_FILE_HASHES = {
    "backend/src/modules/c1/data/content/csse.js": "f98f228ac2a2395b054948688ce1ebae616e3e59",
    "backend/src/modules/c1/data/content/spm.js": "e1db25d0bfbaf9434cf7175ba095ce89b3f27d4a",
    "backend/src/modules/c1/data/content/uee.js": "84968a493568113a783f68464b2148696754e328",
    "backend/src/modules/c1/data/content/ds.js": "23ccd3b06141207bb4e508e50cb529d371f4e8f3",
    "backend/src/modules/c1/data/content/dsys.js": "7713f77c9e65cb0d0450abed8895df8fa00d767b",
    "backend/src/modules/c1/data/content/sa.js": "777ff413ea8e87214cc338bff2beafe34f466132",
    "backend/src/modules/c1/data/content/sepqm.js": "b0480e5c34dd576aa677e227788d85e843d218d2",
    "backend/src/modules/c1/data/content/af.js": "bceb0f2c73745956c52f0e9ec59e2871a6781197",
}
PROVENANCE_NOTE = (
    "Re-audit vs working tree at SOURCE_COMMIT: 46 topic IDs, MODULES order "
    "(csse→spm→uee→ds→dsys→sa→sepqm→af), module codes and Y3S1/Y3S2 membership "
    "identical to freeze. Diff is SHA1-only on the three originally pinned files; "
    "authoritative topic keys now live in content/*.js module files. "
    "Scope remains S1 — not changed."
)

# (topic_id, module_code, semester, label)
_ROWS: tuple[tuple[str, str, str, str], ...] = (
    ("interaction_functional_design", "SE3070", "Y3S1", "Interaction and Functional Design"),
    ("code_quality_solid", "SE3070", "Y3S1", "Code Quality, SOLID and Code Smells"),
    ("refactoring_best_practices", "SE3070", "Y3S1", "Best Practices and Refactoring"),
    ("unit_integration_testing", "SE3070", "Y3S1", "Unit, API and Integration Testing"),
    ("debugging_profiling_config", "SE3070", "Y3S1", "Debugging, Profiling and Configuration Management"),
    ("project_integration_scope", "SE3080", "Y3S1", "Project Integration and Scope Management"),
    ("schedule_cost_management", "SE3080", "Y3S1", "Schedule and Cost Management (incl. EVM)"),
    ("project_quality_management", "SE3080", "Y3S1", "Project Quality Management"),
    ("communication_stakeholders", "SE3080", "Y3S1", "Communication and Stakeholder Management"),
    ("project_risk_management", "SE3080", "Y3S1", "Project Risk Management"),
    ("ux_foundations_process", "SE3050", "Y3S1", "UX Foundations and Design Process"),
    ("user_research_synthesis", "SE3050", "Y3S1", "User Research and Synthesis"),
    ("structuring_prototyping", "SE3050", "Y3S1", "Structuring and Prototyping"),
    ("visual_design_accessibility", "SE3050", "Y3S1", "Visual Design and High-Fidelity Prototyping"),
    ("ux_testing_heuristics", "SE3050", "Y3S1", "Testing and Analysis of UX"),
    ("devices_trends_teams", "SE3050", "Y3S1", "Devices, Design Trends, Teams and Portfolio"),
    ("object_relational_db", "SE3060", "Y3S1", "Object-Relational Databases and PL/SQL"),
    ("file_organization_indexing", "SE3060", "Y3S1", "File Organization and Indexing"),
    ("query_processing_tuning", "SE3060", "Y3S1", "Query Processing and Physical Design Tuning"),
    ("xml_databases", "SE3060", "Y3S1", "XML in Databases"),
    ("transactions_concurrency", "SE3060", "Y3S1", "Transactions and Concurrency Control"),
    ("nosql_big_data", "SE3060", "Y3S1", "NoSQL, MongoDB and Big Data (Hadoop/MapReduce)"),
    ("ds_architectures_sockets", "SE3020", "Y3S2", "Distributed Architectures and Socket Programming"),
    ("ds_rpc_messaging", "SE3020", "Y3S2", "RPC/RMI and Asynchronous Communication"),
    ("ds_components_formats", "SE3020", "Y3S2", "Component Frameworks and Open Message Formats"),
    ("ds_soa_web_services", "SE3020", "Y3S2", "SOA, Web Services and Service Integration"),
    ("ds_cloud_microservices", "SE3020", "Y3S2", "Cloud Computing and Microservices"),
    ("ds_fault_tolerance_clocks", "SE3020", "Y3S2", "Fault Tolerance and Clock Synchronization"),
    ("sa_overview_views", "SE3030", "Y3S2", "Architecture Overview, Activities and Views"),
    ("sa_styles_real_world", "SE3030", "Y3S2", "Monolithic vs Distributed Styles and Real-World Architecture"),
    ("sa_quality_attributes", "SE3030", "Y3S2", "Quality Attributes and Scenarios"),
    ("sa_tactics", "SE3030", "Y3S2", "Quality Attribute Tactics"),
    ("sa_patterns_styles", "SE3030", "Y3S2", "Architectural Patterns and Styles"),
    ("sa_evaluation_frameworks", "SE3030", "Y3S2", "Evaluation, Trade-off Analysis (ATAM) and Frameworks"),
    ("qm_testing_basics", "SEPQM", "Y3S2", "Software Testing Basics and Specification-Based Test Design"),
    ("qm_functional_nonfunctional", "SEPQM", "Y3S2", "Functional and Non-Functional Testing"),
    ("qm_coverage_complexity", "SEPQM", "Y3S2", "Code Coverage and Cyclomatic Complexity"),
    ("qm_size_complexity_metrics", "SEPQM", "Y3S2", "Cognitive Functional Size and Weighted Composite Complexity"),
    ("qm_stlc_automation", "SEPQM", "Y3S2", "Software Testing Life Cycle and Test Automation"),
    ("qm_tdd_trends", "SEPQM", "Y3S2", "Test-Driven Development and Testing Trends"),
    ("af_best_practices_git", "SE3040", "Y3S1", "Best Practices and Version Control (Git)"),
    ("af_javascript_node", "SE3040", "Y3S1", "JavaScript and Node.js"),
    ("af_rest_express", "SE3040", "Y3S1", "RESTful Web Services and Express.js"),
    ("af_mongodb", "SE3040", "Y3S1", "NoSQL and MongoDB"),
    ("af_react", "SE3040", "Y3S1", "React (Parts 1 and 2)"),
    ("af_framework_selection", "SE3040", "Y3S1", "Framework Selection Strategies"),
)

ORDERED_TOPICS: tuple[str, ...] = tuple(r[0] for r in _ROWS)
TOPIC_MODULE: dict[str, str] = {r[0]: r[1] for r in _ROWS}
TOPIC_SEMESTER: dict[str, str] = {r[0]: r[2] for r in _ROWS}
TOPIC_LABEL: dict[str, str] = {r[0]: r[3] for r in _ROWS}
N_TOPICS = len(ORDERED_TOPICS)

Y3S1_TOPICS: tuple[str, ...] = tuple(t for t in ORDERED_TOPICS if TOPIC_SEMESTER[t] == "Y3S1")
Y3S2_TOPICS: tuple[str, ...] = tuple(t for t in ORDERED_TOPICS if TOPIC_SEMESTER[t] == "Y3S2")
Y3S1_INDICES: tuple[int, ...] = tuple(i for i, t in enumerate(ORDERED_TOPICS) if TOPIC_SEMESTER[t] == "Y3S1")
Y3S2_INDICES: tuple[int, ...] = tuple(i for i, t in enumerate(ORDERED_TOPICS) if TOPIC_SEMESTER[t] == "Y3S2")

assert N_TOPICS == 46
assert len(set(ORDERED_TOPICS)) == 46
assert len(Y3S1_TOPICS) == 28
assert len(Y3S2_TOPICS) == 18
assert set(TOPIC_SEMESTER.values()) == {"Y3S1", "Y3S2"}


def semester_eligibility_mask(semester: str) -> list[bool]:
    """True where topic belongs to the learner's semester."""
    if semester not in ("Y3S1", "Y3S2"):
        raise ValueError(f"unknown semester: {semester}")
    return [TOPIC_SEMESTER[t] == semester for t in ORDERED_TOPICS]


def catalogue_payload() -> dict[str, Any]:
    return {
        "catalogue_id": CATALOGUE_ID,
        "scope_decision": SCOPE_DECISION,
        "n_topics": N_TOPICS,
        "topics": list(ORDERED_TOPICS),
        "topic_modules": dict(TOPIC_MODULE),
        "topic_semesters": dict(TOPIC_SEMESTER),
        "topic_labels": dict(TOPIC_LABEL),
        "y3s1_topics": list(Y3S1_TOPICS),
        "y3s2_topics": list(Y3S2_TOPICS),
        "source_commit": SOURCE_COMMIT,
        "source_file_hashes": dict(SOURCE_FILE_HASHES),
        "source_file_hashes_at_freeze": dict(SOURCE_FILE_HASHES_AT_FREEZE),
        "content_module_file_hashes": dict(CONTENT_MODULE_FILE_HASHES),
        "provenance_note": PROVENANCE_NOTE,
        "note": (
            "S1 implementation scope: frozen 46 C1 practice IDs with semester masks. "
            "Not a claim that the C4 proposal PDF was verified. "
            "Do not map retired se-path-sim-v0 topic IDs onto these keys."
        ),
    }


def catalogue_hash() -> str:
    canonical = json.dumps(
        {
            "catalogue_id": CATALOGUE_ID,
            "topics": list(ORDERED_TOPICS),
            "topic_modules": dict(TOPIC_MODULE),
            "topic_semesters": dict(TOPIC_SEMESTER),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def topic_index(topic: str) -> int:
    return ORDERED_TOPICS.index(topic)


def validate_catalogue() -> dict[str, Any]:
    """Raise on integrity failure; return summary on success."""
    if N_TOPICS != 46:
        raise AssertionError(f"expected 46 topics, got {N_TOPICS}")
    if len(set(ORDERED_TOPICS)) != N_TOPICS:
        raise AssertionError("duplicate topic IDs")
    for t in ORDERED_TOPICS:
        if TOPIC_SEMESTER[t] not in ("Y3S1", "Y3S2"):
            raise AssertionError(f"bad semester for {t}")
        if not TOPIC_MODULE[t]:
            raise AssertionError(f"missing module for {t}")
    return {
        "ok": True,
        "n_topics": N_TOPICS,
        "catalogue_hash": catalogue_hash(),
        "y3s1": len(Y3S1_TOPICS),
        "y3s2": len(Y3S2_TOPICS),
    }
