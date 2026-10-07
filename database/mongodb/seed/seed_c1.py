"""
Seed script for Component 1 (Cognitive Digital Twin).
Run from the repo root:  python database\mongodb\seed\seed_c1.py
Safe to run more than once. Question text is PLACEHOLDER content.
"""
import os
from pymongo import MongoClient, ASCENDING

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "adaptivelearnse")

SEMESTER_MODULES = {
    "Y3S1": ["SE3010", "SE3020", "SE3030", "SE3040"],
    "Y3S2": ["SE3050", "SE3060", "SE3070", "SE3080"],
}

TOPICS = {
    "SE3010": [("sdlc_models", "SDLC Models"), ("quality_assurance", "Quality Assurance"), ("process_metrics", "Process Metrics")],
    "SE3020": [("distributed_transactions", "Distributed Transactions"), ("consistency_models", "Consistency Models"), ("microservices", "Microservices")],
    "SE3030": [("architectural_patterns", "Architectural Patterns"), ("quality_attributes", "Quality Attributes"), ("design_tradeoffs", "Design Trade-offs")],
    "SE3040": [("mvc_architecture", "MVC Architecture"), ("orm_frameworks", "ORM & Frameworks"), ("dependency_injection", "Dependency Injection")],
    "SE3050": [("usability_heuristics", "Usability Heuristics"), ("user_research_methods", "User Research Methods"), ("prototyping", "Prototyping")],
    "SE3060": [("normalization", "Normalization"), ("indexing", "Indexing"), ("query_optimization", "Query Optimization")],
    "SE3070": [("case_analysis_techniques", "Case Analysis Techniques"), ("industry_case_studies", "Industry Case Studies"), ("lessons_learned", "Lessons Learned & Reporting")],
    "SE3080": [("risk_management", "Risk Management"), ("estimation", "Estimation"), ("agile_planning", "Agile Planning")],
}

QUESTIONS_PER_TOPIC = 3
DIFFICULTIES = ["easy", "medium", "hard"]
ANSWER_KEYS = ["A", "B", "C", "D"]

DEMO_STUDENTS = [
    ("STU001", "Demo Student 1", "Y3S1"),
    ("STU002", "Demo Student 2", "Y3S1"),
    ("STU003", "Demo Student 3", "Y3S1"),
    ("STU004", "Demo Student 4", "Y3S2"),
    ("STU005", "Demo Student 5", "Y3S2"),
    ("STU006", "Demo Student 6", "Y3S2"),
]


def build_questions():
    questions = []
    for semester, modules in SEMESTER_MODULES.items():
        for module in modules:
            for topic_key, topic_name in TOPICS[module]:
                for n in range(1, QUESTIONS_PER_TOPIC + 1):
                    questions.append({
                        "question_id": f"Q-{module}-{topic_key}-{n}",
                        "module_code": module,
                        "topic": topic_key,
                        "semester": semester,
                        "difficulty": DIFFICULTIES[(n - 1) % 3],
                        "question_text": f"[PLACEHOLDER] Sample question {n} about {topic_name}",
                        "options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                        "correct_answer": ANSWER_KEYS[(n - 1) % 4],
                        "is_placeholder": True,
                    })
    return questions


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]

    for q in build_questions():
        db.question_bank.replace_one({"question_id": q["question_id"]}, q, upsert=True)

    for sid, name, semester in DEMO_STUDENTS:
        db.students.replace_one(
            {"student_id": sid},
            {"student_id": sid, "name": name, "semester": semester,
             "enrolled_modules": SEMESTER_MODULES[semester], "role": "student"},
            upsert=True,
        )

    db.question_bank.create_index([("semester", ASCENDING), ("module_code", ASCENDING), ("topic", ASCENDING)])
    db.learning_events.create_index([("student_id", ASCENDING), ("timestamp", ASCENDING)])
    db.mastery_state.create_index([("student_id", ASCENDING)], unique=True)
    db.diagnostic_assignments.create_index([("student_id", ASCENDING)])
    db.alerts.create_index([("student_id", ASCENDING), ("created_at", ASCENDING)])

    print(f"Connected to {DB_NAME}")
    print(f"question_bank: {db.question_bank.count_documents({})} questions")
    print(f"students: {db.students.count_documents({})} demo students")
    print("Collections ready:", ", ".join(sorted(db.list_collection_names())))


if __name__ == "__main__":
    main()