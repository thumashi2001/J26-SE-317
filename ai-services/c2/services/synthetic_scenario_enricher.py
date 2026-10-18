
"""M11.2.6.2 - Scenario enrichment for synthetic paper drafts.

Development-only. Preserves unverified and pending-review status.
Does not modify source papers or write files.
"""

import hashlib
import json
from copy import deepcopy

from services.synthetic_dataset_exporter import SyntheticDatasetExporter


# Illustrative development scenarios, NOT lecturer-approved material.
SCENARIOS = {
    "database_systems": {
        "SQL Queries": [
            "A university database contains Student(student_id, name), "
            "Module(module_id, title), and Enrollment(student_id, module_id, grade). "
            "Retrieve students enrolled in more than two modules.",

            "A retail database contains Product(product_id, category, price) "
            "and Sale(sale_id, product_id, quantity). Calculate total "
            "sales revenue by category.",

            "A library database contains Book(book_id, title), "
            "Member(member_id, name), and Loan(book_id, member_id, due_date). "
            "Find members with overdue loans.",

            "An employee database contains Employee(emp_id, department_id, salary) "
            "and Department(department_id, name). Identify employees "
            "earning above their department average.",

            "An online booking database contains Reservation(reservation_id, "
            "customer_id, status) and Customer(customer_id, name). "
            "Find customers with no confirmed reservations.",
        ],
        "Database Normalization": [
            "An order table stores order_id, customer_id, customer_name, "
            "product_id, product_name, quantity, and unit_price. "
            "Identify dependencies and propose a normalized design.",

            "A student registration table stores student_id, student_name, "
            "module_id, module_title, lecturer_id, and lecturer_name. "
            "Examine update anomalies and normalization requirements.",

            "A hospital appointment table stores appointment_id, patient_id, "
            "patient_name, doctor_id, doctor_name, and clinic_room. "
            "Identify redundancy and suitable decomposition.",

            "An inventory table stores supplier_id, supplier_name, "
            "item_id, item_description, and supplier_contact. "
            "Discuss functional dependencies and lossless decomposition.",

            "A project allocation table stores project_id, project_name, "
            "employee_id, employee_name, department_id, and department_name. "
            "Evaluate normalization and dependency preservation.",
        ],
        "Transaction Management": [
            "Two users attempt to transfer funds from the same bank account "
            "simultaneously. Examine isolation and consistency requirements.",

            "An online store updates inventory and creates an order, but "
            "payment processing fails. Explain appropriate rollback behavior.",

            "Two transactions lock the Orders and Inventory tables in "
            "opposite orders. Analyze the resulting concurrency risk.",

            "A ticket booking system receives two requests for the final "
            "available seat. Propose a transaction strategy.",

            "A database server crashes after a transaction writes changes "
            "but before its commit acknowledgement. Discuss recovery.",
        ],
    }
}


class SyntheticScenarioEnricher:
    def __init__(self, scenarios=None):
        self.scenarios = (
            deepcopy(scenarios)
            if scenarios is not None
            else deepcopy(SCENARIOS)
        )

    def enrich(self, paper):
        if not isinstance(paper, dict):
            raise ValueError("Paper must be an object")

        if (
            paper.get("generation_mode") != "development_fixture"
            or paper.get("source_type") != "synthetic"
            or paper.get("release_status") != "not_approved"
            or paper.get("human_review_status") != "pending"
        ):
            raise ValueError(
                "Only pending development synthetic drafts can be enriched"
            )

        original_validation = SyntheticDatasetExporter().validate(paper)

        if not original_validation["valid"]:
            raise ValueError(
                "Source paper is invalid: "
                + "; ".join(original_validation["errors"])
            )

        enriched = deepcopy(paper)
        module_key = enriched["module_key"]
        module_scenarios = self.scenarios.get(module_key)

        if not isinstance(module_scenarios, dict):
            raise ValueError(
                f"No development scenarios for module: {module_key}"
            )

        used_scenarios = set()
        used_texts = set()
        enriched_count = 0

        for main in enriched["questions"]:
            for sub in main["subquestions"]:
                question = sub["question"]
                topic = question.get("topic")
                choices = module_scenarios.get(topic)

                if not isinstance(choices, list) or not choices:
                    raise ValueError(
                        f"No scenarios configured for topic: {topic}"
                    )

                selected = None

                for index, scenario in enumerate(choices):
                    if (
                        not isinstance(scenario, str)
                        or len(scenario.strip()) < 40
                    ):
                        raise ValueError(
                            f"Invalid scenario for topic: {topic}"
                        )

                    scenario_key = (topic, index)

                    if scenario_key not in used_scenarios:
                        selected = (index, scenario)
                        used_scenarios.add(scenario_key)
                        break

                if selected is None:
                    raise ValueError(
                        f"Insufficient unique scenarios for topic: {topic}"
                    )

                index, scenario = selected
                original_text = question["question_text"]

                enriched_text = (
                    f"Case study: {scenario}\n"
                    f"Task: {original_text}"
                )

                if enriched_text in used_texts:
                    raise ValueError(
                        "Duplicate enriched question text"
                    )

                used_texts.add(enriched_text)
                question["question_text"] = enriched_text
                question["scenario_id"] = (
                    f"{module_key}:{topic}:{index + 1}"
                )
                question["scenario_review_status"] = "pending"

                question["generation_provenance"][
                    "scenario_enricher"
                ] = "c2_scenario_enricher_v1"

                enriched_count += 1

        # Recompute paper ID so the enriched content does not
        # retain the original draft's identity.
        fingerprint = json.dumps(
            {
                "source_paper_id": paper["paper_id"],
                "questions": enriched["questions"],
                "enricher": "c2_scenario_enricher_v1",
            },
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )

        enriched["paper_id"] = (
            "SYN-PAPER-"
            + hashlib.sha256(
                fingerprint.encode("utf-8")
            ).hexdigest()[:16]
        )

        enriched["assembly_provenance"][
            "source_paper_id"
        ] = paper["paper_id"]

        enriched["assembly_provenance"][
            "scenario_enricher"
        ] = "c2_scenario_enricher_v1"

        validation = SyntheticDatasetExporter().validate(enriched)

        if not validation["valid"]:
            raise ValueError(
                "Enriched paper failed validation: "
                + "; ".join(validation["errors"])
            )

        return {
            "paper": enriched,
            "validation": validation,
            "enriched_question_count": enriched_count,
        }
