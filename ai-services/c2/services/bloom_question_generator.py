"""M21 — Bloom's Taxonomy-Controlled Question Generator.

Generates examination questions grounded in SLIIT Year 3 SE curriculum taxonomies,
with cognitive depth controlled across all six Bloom Revised Taxonomy levels:
Remember, Understand, Apply, Analyze, Evaluate, Create.

Research Integrity Principles:
- Honestly labeled method: 'curriculum_grounded_bloom_template_v1'.
- Strictly marked as is_authentic: False.
- Transparent validation metrics with explicit limitations.
- Preserves all 8 canonical modules and approved curriculum taxonomies.
"""

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.bloom_question_validator import BloomQuestionValidator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = PROJECT_ROOT / "config" / "curriculum_taxonomies.json"
CONTENT_BANK_PATH = PROJECT_ROOT / "config" / "m16_expanded_content_bank.json"

CANONICAL_MODULE_NAMES = {
    "database_systems": "Database Systems",
    "software_architecture": "Software Architecture",
    "software_engineering_process_quality_management": "Software Engineering Process and Quality Management",
    "case_studies_software_engineering": "Case Studies in Software Engineering",
    "application_frameworks": "Application Frameworks",
    "distributed_systems": "Distributed Systems",
    "software_project_management": "Software Project Management",
    "user_experience_engineering": "User Experience Engineering",
}


# Module key aliases to support legacy naming
MODULE_ALIASES = {
    "case_studies_in_software_engineering": "case_studies_software_engineering",
    "software_engineering_process_and_quality_management": "software_engineering_process_quality_management",
}

# Real-world SE scenario seeds by domain
DOMAIN_SCENARIOS: Dict[str, Dict[str, List[str]]] = {
    "database_systems": {
        "normalization_schema_design": [
            "An equipment rental company maintains rental contracts, customer accounts, equipment inventories, maintenance records, and insurance policies in an unnormalized table: R(ContractID, CustomerID, CustomerName, EquipmentID, Model, DailyRate, RentalDate, ReturnDate, TotalFee).",
            "A clinical trial management platform stores volunteer subjects, investigational drug regimens, laboratory test results, and attending clinicians in an unnormalized spreadsheet: TrialLog(SubjectID, SubjectName, TrialCode, RegimenID, DrugDosage, DoctorID, DoctorName, ClinicBranch, VisitDate).",
            "A university examination management division tracks student course enrollments, module codes, lecturer allocations, and semester grade submissions in a consolidated relation: GradeReport(StudentID, StudentName, CourseCode, CourseName, LecturerID, OfficeRoom, AssessmentType, MarksObtained, Grade).",
            "An international freight shipping platform records shipping containers, consignee details, vessel schedules, customs clearance certificates, and port transit checkpoints in a single relation: CargoRecord(ContainerNo, ConsigneeID, ConsigneeName, VesselID, VesselFlag, PortOfLoading, PortOfDischarge, CustomsCode, ETA).",
        ],
        "sql_queries": [
            "An e-commerce marketplace database consists of tables: Customers(CustomerID, Name, City, LoyaltyTier), Orders(OrderID, CustomerID, OrderDate, TotalAmount, Status), and OrderDetails(OrderDetailID, OrderID, ProductID, Quantity, UnitPrice).",
            "A metropolitan transit authority database maintains: Routes(RouteID, RouteNumber, Origin, Destination), BusFleet(BusID, Capacity, ModelYear), Drivers(DriverID, DriverName, LicenseType), and ScheduledTrips(TripID, RouteID, BusID, DriverID, DepartureTime, DelayMinutes).",
        ],
        "database_indexing": [
            "A fintech ledger table recording over 40 million transactions suffers from high read latency on statements queried by AccountID, TransactionDate, and Status.",
            "A healthcare telemetry system continuously inserts 5,000 vital sensor readings per second while clinicians run real-time anomaly queries filtered by PatientID and HeartRate threshold.",
        ],
        "transaction_concurrency": [
            "An online airline seat reservation service allows concurrent booking agents to check and purchase the final remaining first-class seat on a flight simultaneously.",
            "A banking core system processes automated scheduled loan deductions concurrently with point-of-sale debit card authorizations against the same checking account.",
        ],
    },
    "software_architecture": {
        "architectural_patterns": [
            "A national healthcare diagnostics portal needs to transition from a legacy monolithic application into an event-driven microservices architecture handling electronic health records, appointment bookings, and telemetry streaming.",
            "An enterprise supply-chain management system requires high availability and resilient asynchronous messaging across regional distribution hubs.",
        ],
    },
    "application_frameworks": {
        "react_component_architecture": [
            "A collaborative kanban board application built with React experiences frequent unnecessary re-renders when task cards are dragged and dropped across columns.",
            "A financial trading terminal interface requires state management that coordinates live WebSocket price feeds, historical chart caches, and order placement modals.",
        ],
    },
}


class BloomQuestionGenerator:
    """Generates Bloom-controlled examination questions grounded in curriculum taxonomy."""

    def __init__(
        self,
        curriculum_path: Optional[Path] = None,
        content_bank_path: Optional[Path] = None,
    ):
        self.curriculum_path = Path(curriculum_path or CURRICULUM_PATH)
        self.content_bank_path = Path(content_bank_path or CONTENT_BANK_PATH)
        self.validator = BloomQuestionValidator(curriculum_path=self.curriculum_path)
        self._curriculum_cache: Optional[Dict[str, Any]] = None
        self._content_bank_cache: Optional[Dict[str, Any]] = None

    def _load_curriculum(self) -> Dict[str, Any]:
        if self._curriculum_cache is not None:
            return self._curriculum_cache
        if not self.curriculum_path.exists():
            return {}
        with open(self.curriculum_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        modules = {}
        for mod in data.get("modules", []):
            modules[mod["module_key"]] = mod
            for alias in mod.get("aliases", []):
                modules[alias] = mod
        self._curriculum_cache = modules
        return modules

    def _canonicalize_module(self, module_key: str) -> str:
        key = module_key.strip().lower()
        key = MODULE_ALIASES.get(key, key)
        curriculum = self._load_curriculum()
        if key in curriculum:
            return curriculum[key]["module_key"]
        return key

    def get_module_topics(self, module_key: str) -> List[Dict[str, Any]]:
        """Get the available curriculum topics for a module."""
        canon_key = self._canonicalize_module(module_key)
        curriculum = self._load_curriculum()
        mod = curriculum.get(canon_key)
        if not mod:
            return []
        return [
            {
                "topic_id": t.get("topic_id"),
                "topic_name": t.get("topic_name"),
                "subtopics": t.get("subtopics", []),
            }
            for t in mod.get("topics", [])
        ]

    def _select_scenario(self, module_key: str, topic_id: str) -> str:
        """Select a domain scenario from specific banks or generate a contextual seed."""
        module_scenarios = DOMAIN_SCENARIOS.get(module_key, {})
        for key, sc_list in module_scenarios.items():
            if key in topic_id or topic_id in key:
                return random.choice(sc_list)

        curriculum = self._load_curriculum()
        mod = curriculum.get(module_key, {})
        topic = next((t for t in mod.get("topics", []) if t.get("topic_id") == topic_id), None)
        topic_name = topic.get("topic_name", topic_id) if topic else topic_id
        module_name = CANONICAL_MODULE_NAMES.get(module_key, module_key.replace("_", " ").title())

        subtopic = ""
        if topic and topic.get("subtopics"):
            subtopic = f" involving {random.choice(topic['subtopics'])}"

        return (
            f"An enterprise software organization is deploying an engineering solution for {module_name}, "
            f"specifically focusing on {topic_name}{subtopic} in a high-throughput production environment."
        )

    def _generate_remember_question(
        self,
        module_key: str,
        topic_name: str,
        topic_info: Dict[str, Any],
        marks: int,
        question_type: str,
        difficulty: str,
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        subtopics = topic_info.get("subtopics", [])
        sub1 = subtopics[0] if len(subtopics) > 0 else f"{topic_name} core principles"
        sub2 = subtopics[1] if len(subtopics) > 1 else f"{topic_name} primary structures"

        if question_type == "structured":
            m1 = max(2, marks // 2)
            m2 = marks - m1
            subquestions = [
                {
                    "part": "a",
                    "subquestion_text": f"Define the fundamental concept of {topic_name} and state its primary role in software systems.",
                    "marks": m1,
                    "bloom_level": "remember",
                },
                {
                    "part": "b",
                    "subquestion_text": f"List and state the formal definitions of four essential characteristics or components associated with {sub1} and {sub2}.",
                    "marks": m2,
                    "bloom_level": "remember",
                },
            ]
            text = (
                f"Question on {topic_name}:\n\n"
                f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
                f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]"
            )
        else:
            subquestions = []
            text = (
                f"State the formal definition of {topic_name}. List the key principles and primary terminology "
                f"governing {sub1} and {sub2} in software engineering [{marks} Marks]."
            )

        marking_guide = (
            f"- Accurate formal definition of {topic_name} (50% marks).\n"
            f"- Correct listing of key concepts and terminology ({sub1}, {sub2}) (50% marks)."
        )
        return text, subquestions, marking_guide

    def _generate_understand_question(
        self,
        module_key: str,
        topic_name: str,
        topic_info: Dict[str, Any],
        marks: int,
        question_type: str,
        difficulty: str,
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        subtopics = topic_info.get("subtopics", [])
        sub1 = subtopics[0] if len(subtopics) > 0 else "underlying principles"
        sub2 = subtopics[1] if len(subtopics) > 1 else "alternative mechanisms"

        if question_type == "structured":
            m1 = max(2, marks // 2)
            m2 = marks - m1
            subquestions = [
                {
                    "part": "a",
                    "subquestion_text": f"Explain why {topic_name} is essential when developing robust software solutions, outlining the problems that arise if it is neglected.",
                    "marks": m1,
                    "bloom_level": "understand",
                },
                {
                    "part": "b",
                    "subquestion_text": f"Describe the operational difference between {sub1} and {sub2}. Contrast their respective mechanisms with an illustrative example.",
                    "marks": m2,
                    "bloom_level": "understand",
                },
            ]
            text = (
                f"Consider the principles of {topic_name} in software engineering:\n\n"
                f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
                f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]"
            )
        else:
            subquestions = []
            text = (
                f"Explain the technical rationale behind {topic_name}. Describe how {sub1} operates, "
                f"and contrast its purpose and trade-offs against {sub2} [{marks} Marks]."
            )

        marking_guide = (
            f"- Comprehensive explanation of {topic_name} mechanisms and problem domain (40% marks).\n"
            f"- Accurate contrast and conceptual comparison between {sub1} and {sub2} (60% marks)."
        )
        return text, subquestions, marking_guide

    def _generate_apply_question(
        self,
        module_key: str,
        topic_id: str,
        topic_name: str,
        scenario: str,
        marks: int,
        question_type: str,
        difficulty: str,
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        if "normalization" in topic_id or "schema" in topic_id:
            m1 = 3
            m2 = 4
            m3 = max(1, marks - (m1 + m2))
            if marks < 8:
                m1 = marks // 2
                m2 = marks - m1
                subquestions = [
                    {
                        "part": "a",
                        "subquestion_text": "Identify the primary key, candidate keys, and all functional dependencies present in the relation based on the scenario description.",
                        "marks": m1,
                        "bloom_level": "apply",
                    },
                    {
                        "part": "b",
                        "subquestion_text": "Apply relational normalization rules to decompose the table into Third Normal Form (3NF). List all resulting relations with their primary and foreign keys.",
                        "marks": m2,
                        "bloom_level": "apply",
                    },
                ]
                text = (
                    f"Scenario:\n{scenario}\n\n"
                    f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
                    f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]"
                )
            else:
                subquestions = [
                    {
                        "part": "a",
                        "subquestion_text": "Identify the candidate keys and write out all functional dependencies holding on the relation from the given scenario.",
                        "marks": m1,
                        "bloom_level": "apply",
                    },
                    {
                        "part": "b",
                        "subquestion_text": "Demonstrate step-by-step how to decompose the relation into Third Normal Form (3NF). Explicitly specify the attributes, primary keys, and foreign keys for each resulting relation.",
                        "marks": m2,
                        "bloom_level": "apply",
                    },
                    {
                        "part": "c",
                        "subquestion_text": "Verify whether the decomposition is lossless-join and explain whether functional dependency preservation is satisfied.",
                        "marks": m3,
                        "bloom_level": "apply",
                    },
                ]
                text = (
                    f"Consider the following business scenario:\n{scenario}\n\n"
                    f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
                    f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]\n"
                    f"(c) {subquestions[2]['subquestion_text']} [{m3} Marks]"
                )
            marking_guide = (
                "- Identification of candidate keys and all functional dependencies (30% marks).\n"
                "- Step-by-step 3NF decomposition with correct foreign key linkages (40% marks).\n"
                "- Lossless join verification and dependency preservation proof (30% marks)."
            )
            return text, subquestions, marking_guide

        # General apply question
        m1 = max(2, marks // 2)
        m2 = marks - m1
        subquestions = [
            {
                "part": "a",
                "subquestion_text": f"Apply the practical techniques of {topic_name} to execute the primary operations required by this scenario.",
                "marks": m1,
                "bloom_level": "apply",
            },
            {
                "part": "b",
                "subquestion_text": f"Demonstrate step-by-step computation or code formulation to resolve the requirements, highlighting key parameters and edge cases.",
                "marks": m2,
                "bloom_level": "apply",
            },
        ]
        text = (
            f"Scenario:\n{scenario}\n\n"
            f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
            f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]"
        )
        marking_guide = f"- Correct implementation and application of {topic_name} techniques to the scenario ({marks} Marks)."
        return text, subquestions, marking_guide

    def _generate_analyze_question(
        self,
        module_key: str,
        topic_name: str,
        scenario: str,
        marks: int,
        question_type: str,
        difficulty: str,
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        m1 = max(2, marks // 2)
        m2 = marks - m1
        subquestions = [
            {
                "part": "a",
                "subquestion_text": f"Analyze the system performance and data flow in the provided scenario to diagnose potential bottlenecks, anomalies, or failure points.",
                "marks": m1,
                "bloom_level": "analyze",
            },
            {
                "part": "b",
                "subquestion_text": f"Deconstruct the trade-offs between two competing implementation approaches for {topic_name}, examining how they impact resource utilization and reliability.",
                "marks": m2,
                "bloom_level": "analyze",
            },
        ]
        text = (
            f"System Context:\n{scenario}\n\n"
            f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
            f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]"
        )
        marking_guide = (
            f"- Rigorous root-cause analysis and anomaly diagnosis (50% marks).\n"
            f"- Thorough deconstruction of competing architectural and implementation trade-offs (50% marks)."
        )
        return text, subquestions, marking_guide

    def _generate_evaluate_question(
        self,
        module_key: str,
        topic_name: str,
        scenario: str,
        marks: int,
        question_type: str,
        difficulty: str,
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        m1 = max(2, marks // 2)
        m2 = marks - m1
        subquestions = [
            {
                "part": "a",
                "subquestion_text": f"Critique the proposed architectural decision in the scenario. Identify at least three flaws or vulnerabilities with respect to {topic_name}.",
                "marks": m1,
                "bloom_level": "evaluate",
            },
            {
                "part": "b",
                "subquestion_text": f"Justify and defend a recommended alternative strategy. Provide concrete technical criteria to evaluate why your proposal is superior.",
                "marks": m2,
                "bloom_level": "evaluate",
            },
        ]
        text = (
            f"Engineering Proposal Review:\n{scenario}\n\n"
            f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
            f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]"
        )
        marking_guide = (
            f"- Critical evaluation and identification of technical shortcomings (50% marks).\n"
            f"- Methodical justification and technical defense of the recommended strategy (50% marks)."
        )
        return text, subquestions, marking_guide

    def _generate_create_question(
        self,
        module_key: str,
        topic_name: str,
        scenario: str,
        marks: int,
        question_type: str,
        difficulty: str,
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        m1 = max(3, marks // 2)
        m2 = marks - m1
        subquestions = [
            {
                "part": "a",
                "subquestion_text": f"Design an end-to-end technical architecture or relational schema for {topic_name} that fully satisfies the operational constraints of the scenario.",
                "marks": m1,
                "bloom_level": "create",
            },
            {
                "part": "b",
                "subquestion_text": f"Formulate the complete data models, interface contracts, and error-handling protocols required to integrate this solution reliably.",
                "marks": m2,
                "bloom_level": "create",
            },
        ]
        text = (
            f"Design Brief:\n{scenario}\n\n"
            f"(a) {subquestions[0]['subquestion_text']} [{m1} Marks]\n"
            f"(b) {subquestions[1]['subquestion_text']} [{m2} Marks]"
        )
        marking_guide = (
            f"- Original, coherent architectural design meeting all constraints (60% marks).\n"
            f"- Complete specification of data models, schemas, and resilience protocols (40% marks)."
        )
        return text, subquestions, marking_guide

    def _generate_mcq_options(
        self,
        topic_name: str,
        bloom_level: str,
    ) -> List[Dict[str, Any]]:
        """Generate four distinct MCQ options for the topic and Bloom level."""
        return [
            {
                "option_id": "A",
                "option_text": f"It eliminates all insertion, update, and deletion anomalies while strictly preserving functional dependencies in {topic_name}.",
                "is_correct": True,
                "rationale": "Correct technical property and definition under the relational model.",
            },
            {
                "option_id": "B",
                "option_text": f"It reduces query execution time by introducing redundant duplicate attributes across all foreign key joins.",
                "is_correct": False,
                "rationale": "Incorrect: Normalization minimizes duplicate data, not introduces deliberate duplicates.",
            },
            {
                "option_id": "C",
                "option_text": f"It replaces primary key constraints with sequential full table scans on indexed columns.",
                "is_correct": False,
                "rationale": "Incorrect: Full table scans are an access path, not an architectural benefit of schema design.",
            },
            {
                "option_id": "D",
                "option_text": f"It enforces transaction isolation levels exclusively through pessimistic locking mechanisms.",
                "is_correct": False,
                "rationale": "Incorrect: Concurrency control mechanisms are distinct from logical schema normalization.",
            },
        ]

    def generate_question(
        self,
        *,
        module_key: str,
        topic_id: str,
        bloom_level: str = "apply",
        difficulty: str = "medium",
        question_type: str = "structured",
        marks: int = 10,
        lecturer_instructions: str = "",
    ) -> Dict[str, Any]:
        """Generate an authentic-aligned Bloom's Taxonomy examination question."""
        canon_module = self._canonicalize_module(module_key)
        curriculum = self._load_curriculum()

        if canon_module not in curriculum:
            raise ValueError(f"Unknown or unsupported module: '{module_key}'")

        mod = curriculum[canon_module]
        topic = next((t for t in mod.get("topics", []) if t.get("topic_id") == topic_id), None)
        if not topic:
            # Flexible matching by substring, tokens, or topic name
            needle = topic_id.lower().strip()
            clean_needle = needle.replace("_", " ")
            for t in mod.get("topics", []):
                t_id = t.get("topic_id", "").lower()
                t_name = t.get("topic_name", "").lower()
                if (
                    needle == t_id
                    or needle in t_id
                    or t_id in needle
                    or clean_needle in t_name
                    or t_name in clean_needle
                    or any(part in t_id for part in needle.split("_") if len(part) >= 4)
                ):
                    topic = t
                    break

            if not topic:
                raise ValueError(
                    f"Topic '{topic_id}' not found in curriculum taxonomy for '{canon_module}'"
                )


        norm_bloom = bloom_level.strip().lower()
        if norm_bloom not in ("remember", "understand", "apply", "analyze", "evaluate", "create"):
            raise ValueError(
                f"Invalid Bloom level '{bloom_level}'. Must be one of: "
                "Remember, Understand, Apply, Analyze, Evaluate, Create."
            )

        if not isinstance(marks, int) or marks <= 0:
            raise ValueError("Marks must be a positive integer.")

        norm_diff = difficulty.strip().lower()
        if norm_diff not in ("easy", "medium", "hard"):
            norm_diff = "medium"

        norm_type = question_type.strip().lower()
        if norm_type not in ("structured", "short_answer", "essay", "mcq"):
            norm_type = "structured"

        scenario = self._select_scenario(canon_module, topic["topic_id"])
        if lecturer_instructions.strip():
            scenario = f"{scenario}\n[Lecturer Guidance Context: {lecturer_instructions.strip()}]"

        topic_name = topic.get("topic_name", topic["topic_id"])

        # Dispatch generation based on requested Bloom level
        if norm_bloom == "remember":
            text, subquestions, guide = self._generate_remember_question(
                canon_module, topic_name, topic, marks, norm_type, norm_diff
            )
        elif norm_bloom == "understand":
            text, subquestions, guide = self._generate_understand_question(
                canon_module, topic_name, topic, marks, norm_type, norm_diff
            )
        elif norm_bloom == "apply":
            text, subquestions, guide = self._generate_apply_question(
                canon_module, topic["topic_id"], topic_name, scenario, marks, norm_type, norm_diff
            )
        elif norm_bloom == "analyze":
            text, subquestions, guide = self._generate_analyze_question(
                canon_module, topic_name, scenario, marks, norm_type, norm_diff
            )
        elif norm_bloom == "evaluate":
            text, subquestions, guide = self._generate_evaluate_question(
                canon_module, topic_name, scenario, marks, norm_type, norm_diff
            )
        else:  # create
            text, subquestions, guide = self._generate_create_question(
                canon_module, topic_name, scenario, marks, norm_type, norm_diff
            )

        mcq_options = []
        if norm_type == "mcq":
            mcq_options = self._generate_mcq_options(topic_name, norm_bloom)
            options_text = "\n".join(
                f"({opt['option_id']}) {opt['option_text']}" for opt in mcq_options
            )
            text = f"{text}\n\nSelect the best option:\n{options_text}"

        seed_raw = f"{canon_module}_{topic['topic_id']}_{norm_bloom}_{norm_diff}_{marks}_{random.randint(1000, 9999)}"
        short_hash = hashlib.sha256(seed_raw.encode("utf-8")).hexdigest()[:8]
        module_code = mod.get("module_code", canon_module[:4].upper())
        question_id = f"GEN-{module_code}-{short_hash}"

        question_candidate = {
            "question_id": question_id,
            "question_text": text,
            "module_key": canon_module,
            "module_name": CANONICAL_MODULE_NAMES.get(canon_module, canon_module),
            "topic_id": topic["topic_id"],
            "topic_name": topic_name,
            "bloom_level": norm_bloom,
            "difficulty": norm_diff,
            "question_type": norm_type,
            "marks": marks,
            "subquestions": subquestions,
            "mcq_options": mcq_options,
            "marking_guide": guide,
            "lecturer_instructions": lecturer_instructions.strip(),
            "generation_method": "curriculum_grounded_bloom_template_v1",
            "provenance": "m21_bloom_controlled_generation",
            "is_authentic": False,  # Strict safeguard against historical exam evidence contamination
        }

        # Run multi-dimensional validation
        validation = self.validator.validate_all(question_candidate)
        question_candidate["validation"] = validation

        return question_candidate
