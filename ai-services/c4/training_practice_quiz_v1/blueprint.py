"""Frozen practice-bank counts used to align synthetic quizzes with the live blueprint.

Counts were read from the C1 practice bank on 2026-10-18: 46 topics, 10 MCQs each,
28 Y3S1 and 18 Y3S2. Question text and answer keys are not copied here.
Items have no difficulty metadata.
"""

from __future__ import annotations

Y3S1 = (
    "af_best_practices_git",
    "af_framework_selection",
    "af_javascript_node",
    "af_mongodb",
    "af_react",
    "af_rest_express",
    "code_quality_solid",
    "communication_stakeholders",
    "debugging_profiling_config",
    "devices_trends_teams",
    "file_organization_indexing",
    "interaction_functional_design",
    "nosql_big_data",
    "object_relational_db",
    "project_integration_scope",
    "project_quality_management",
    "project_risk_management",
    "query_processing_tuning",
    "refactoring_best_practices",
    "schedule_cost_management",
    "structuring_prototyping",
    "transactions_concurrency",
    "unit_integration_testing",
    "user_research_synthesis",
    "ux_foundations_process",
    "ux_testing_heuristics",
    "visual_design_accessibility",
    "xml_databases",
)

Y3S2 = (
    "ds_architectures_sockets",
    "ds_cloud_microservices",
    "ds_components_formats",
    "ds_fault_tolerance_clocks",
    "ds_rpc_messaging",
    "ds_soa_web_services",
    "qm_coverage_complexity",
    "qm_functional_nonfunctional",
    "qm_size_complexity_metrics",
    "qm_stlc_automation",
    "qm_tdd_trends",
    "qm_testing_basics",
    "sa_evaluation_frameworks",
    "sa_overview_views",
    "sa_patterns_styles",
    "sa_quality_attributes",
    "sa_styles_real_world",
    "sa_tactics",
)

QUESTIONS_PER_TOPIC = 10


def topics_for(semester: str) -> tuple[str, ...]:
    if semester == "Y3S1":
        return Y3S1
    if semester == "Y3S2":
        return Y3S2
    return ()
