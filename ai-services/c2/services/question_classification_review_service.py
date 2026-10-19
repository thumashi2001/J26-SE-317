
import json
from pathlib import Path

from services.question_classification_review_repository import (
    QuestionClassificationReviewRepository,
)


BASE_DIR = Path(__file__).resolve().parents[1]


class QuestionClassificationReviewService:
    """
    Lecturer review of authentic exam-question topic classifications.

    Research integrity rules:
    - Only authentic questions can be reviewed.
    - A genuine proposed topic must exist.
    - Submitted topic must match the stored proposal.
    - Approval requires a verified module taxonomy.
    - Rejection requires explanatory notes.
    - Duplicate decisions are blocked by the repository.
    """

    def __init__(
        self,
        questions_path=None,
        modules_path=None,
        taxonomy_path=None,
        repository=None,
        classifications_path=None,
    ):
        self.questions_path = Path(
            questions_path
            or BASE_DIR / "datasets/processed/questions.json"
        )
        self.modules_path = Path(
            modules_path
            or BASE_DIR / "config/modules.json"
        )
        self.taxonomy_path = Path(
            taxonomy_path
            or BASE_DIR / "config/topic_taxonomies.json"
        )
        self.classifications_path = Path(
            classifications_path
            or BASE_DIR / "datasets/processed/topic_classifications.json"
        )
        self.repository = (
            repository
            or QuestionClassificationReviewRepository()
        )

    @staticmethod
    def _read_json(path):
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _normalize_topic(topic_id):
        if not isinstance(topic_id, str):
            return None

        normalized = topic_id.strip()

        if (
            not normalized
            or normalized.lower() == "unclassified"
        ):
            return None

        return normalized

    def _load_modules(self):
        document = self._read_json(self.modules_path)

        if not isinstance(document, dict):
            raise ValueError("Invalid modules configuration")

        modules = document.get("modules", [])

        if not isinstance(modules, list):
            raise ValueError("Invalid modules configuration")

        return modules

    def _load_taxonomies(self):
        document = self._read_json(self.taxonomy_path)

        if not isinstance(document, dict):
            raise ValueError("Invalid taxonomy configuration")

        taxonomies = document.get("taxonomies", [])

        if not isinstance(taxonomies, list):
            raise ValueError("Invalid taxonomy configuration")

        return taxonomies

    def _load_classifications(self):
        """
        Read validated classification proposals.

        Invalid records are excluded. Duplicate question IDs
        are treated as ambiguous rather than silently choosing
        the last proposal.
        """
        if not self.classifications_path.exists():
            return {}

        document = self._read_json(self.classifications_path)

        if (
            not isinstance(document, dict)
            or not isinstance(document.get("results"), list)
        ):
            raise ValueError(
                "Invalid topic classification repository"
            )

        proposals = {}
        duplicates = set()

        for result in document["results"]:
            if not isinstance(result, dict):
                continue

            if result.get("valid") is not True:
                continue

            classification = result.get("classification")

            if not isinstance(classification, dict):
                continue

            question_id = (
                result.get("question_id")
                or classification.get("question_id")
            )

            if (
                not isinstance(question_id, str)
                or not question_id.strip()
            ):
                continue

            # Do not accept contradictory question IDs.
            embedded_id = classification.get("question_id")
            if (
                embedded_id is not None
                and embedded_id != question_id
            ):
                continue

            if question_id in proposals:
                duplicates.add(question_id)
                continue

            proposals[question_id] = classification

        for question_id in duplicates:
            proposals.pop(question_id, None)

        return proposals

    def _proposed_classification(
        self,
        question,
        classifications,
    ):
        """
        Use the same proposal source for both queue display
        and review submission.

        A legacy question.topic value is accepted only when
        there is no usable topic in the classification record.
        """
        question_id = question.get("question_id")
        proposal = classifications.get(question_id, {})

        topic_id = self._normalize_topic(
            proposal.get("topic_id")
        )

        if topic_id is None:
            topic_id = self._normalize_topic(
                question.get("topic")
            )

        return {
            "topic_id": topic_id,
            "subtopic": proposal.get("subtopic"),
            "classification_method": proposal.get(
                "classification_method",
                "unclassified",
            ),
            "confidence_score": proposal.get(
                "confidence_score"
            ),
        }

    def review(
        self,
        *,
        question_id,
        module_key,
        topic_id,
        decision,
        reviewer_id,
        review_notes="",
    ):
        if decision not in ("approved", "rejected"):
            raise ValueError("Invalid review decision")

        required_values = (
            question_id,
            module_key,
            topic_id,
            reviewer_id,
        )

        if not all(
            isinstance(value, str) and value.strip()
            for value in required_values
        ):
            raise ValueError(
                "Required review fields are invalid"
            )

        if not isinstance(review_notes, str):
            raise ValueError(
                "Review notes must be a string"
            )

        if len(review_notes) > 2000:
            raise ValueError(
                "Review notes must be 2000 characters or fewer"
            )

        if decision == "rejected" and not review_notes.strip():
            raise ValueError(
                "Rejection requires review notes"
            )

        question_id = question_id.strip()
        module_key = module_key.strip()
        topic_id = topic_id.strip()
        reviewer_id = reviewer_id.strip()

        questions = self._read_json(self.questions_path)

        if not isinstance(questions, list):
            raise ValueError("Invalid question repository")

        matches = [
            question
            for question in questions
            if (
                isinstance(question, dict)
                and question.get("question_id") == question_id
            )
        ]

        if len(matches) != 1:
            raise ValueError(
                "Question does not exist uniquely in repository"
            )

        question = matches[0]

        if question.get("source_type") != "authentic":
            raise ValueError(
                "Only authentic questions may be reviewed"
            )

        modules = self._load_modules()

        matching_modules = [
            module
            for module in modules
            if (
                isinstance(module, dict)
                and module.get("module_key") == module_key
            )
        ]

        if len(matching_modules) != 1:
            raise ValueError(
                "Unknown or ambiguous module"
            )

        matching_module = matching_modules[0]
        module_code = matching_module.get("module_code")
        aliases = matching_module.get("aliases", [])
        valid_codes = {module_code} if module_code else set()
        if isinstance(aliases, list):
            valid_codes.update(aliases)

        if (
            not valid_codes
            or question.get("module_code") not in valid_codes
        ):
            raise ValueError(
                "Question does not belong to selected module"
            )

        # M15.3.2: Validate the stored proposal.
        classifications = self._load_classifications()

        proposal = self._proposed_classification(
            question,
            classifications,
        )

        proposed_topic_id = proposal["topic_id"]

        if proposed_topic_id is None:
            raise ValueError(
                "Question has no proposed topic classification to review"
            )

        if topic_id != proposed_topic_id:
            raise ValueError(
                "Submitted topic does not match the stored "
                "proposed classification"
            )

        # Preserve existing taxonomy verification rules.
        taxonomies = self._load_taxonomies()

        matching_taxonomies = [
            taxonomy
            for taxonomy in taxonomies
            if (
                isinstance(taxonomy, dict)
                and taxonomy.get("module_key") == module_key
            )
        ]

        if len(matching_taxonomies) != 1:
            raise ValueError(
                "Module taxonomy is missing or ambiguous"
            )

        taxonomy = matching_taxonomies[0]

        if decision == "approved":
            if (
                taxonomy.get("verification_status")
                != "verified"
            ):
                raise ValueError(
                    "Module taxonomy is not verified"
                )

            topics = taxonomy.get("topics", [])

            if not isinstance(topics, list):
                raise ValueError(
                    "Invalid taxonomy topics"
                )

            matching_topics = [
                topic
                for topic in topics
                if (
                    isinstance(topic, dict)
                    and topic.get("topic_id") == topic_id
                )
            ]

            if len(matching_topics) != 1:
                raise ValueError(
                    "Topic is not present in approved taxonomy"
                )

        # The repository enforces one decision per question.
        return self.repository.save_review({
            "question_id": question_id,
            "module_key": module_key,
            "topic_id": topic_id,
            "decision": decision,
            "reviewer_id": reviewer_id,
            "review_notes": review_notes.strip(),
        })

    def list_review_candidates(
        self,
        module_key=None,
        page=1,
        page_size=10,
        include_reviewed=False,
    ):
        if (
            isinstance(page, bool)
            or not isinstance(page, int)
            or page < 1
        ):
            raise ValueError("Invalid page")

        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not (1 <= page_size <= 100)
        ):
            raise ValueError("Invalid page size")

        questions = self._read_json(self.questions_path)

        if not isinstance(questions, list):
            raise ValueError("Invalid question repository")

        modules = self._load_modules()

        code_to_module = {}
        valid_module_keys = set()

        for module in modules:
            if not isinstance(module, dict):
                continue

            key = module.get("module_key")
            code = module.get("module_code")

            if key:
                valid_module_keys.add(key)

            if key and code:
                code_to_module[code] = key

            if key and isinstance(module.get("aliases"), list):
                for alias in module.get("aliases"):
                    code_to_module[alias] = key

        if (
            module_key is not None
            and module_key not in valid_module_keys
        ):
            raise ValueError(
                "Unknown or invalid module key"
            )

        classifications = self._load_classifications()

        saved_reviews = {}

        for review in self.repository.list_reviews():
            if (
                isinstance(review, dict)
                and review.get("question_id")
            ):
                saved_reviews[
                    review["question_id"]
                ] = review

        taxonomies = self._load_taxonomies()

        taxonomies_by_key = {
            taxonomy.get("module_key"): taxonomy
            for taxonomy in taxonomies
            if (
                isinstance(taxonomy, dict)
                and taxonomy.get("module_key")
            )
        }

        records = []

        for question in questions:
            if not isinstance(question, dict):
                continue

            if question.get("source_type") != "authentic":
                continue

            question_code = question.get("module_code")
            question_module = code_to_module.get(
                question_code
            )

            if (
                module_key is not None
                and question_module != module_key
            ):
                continue

            question_id = question.get("question_id")

            proposal = self._proposed_classification(
                question,
                classifications,
            )

            proposed_topic_id = proposal["topic_id"]
            saved_review = saved_reviews.get(question_id)

            taxonomy = taxonomies_by_key.get(
                question_module,
                {},
            )

            taxonomy_verified = (
                taxonomy.get("verification_status")
                == "verified"
            )

            taxonomy_topics = taxonomy.get("topics", [])

            if not isinstance(taxonomy_topics, list):
                taxonomy_topics = []

            topic_in_taxonomy = any(
                isinstance(topic, dict)
                and topic.get("topic_id")
                == proposed_topic_id
                for topic in taxonomy_topics
            )

            is_reviewed = saved_review is not None

            if is_reviewed:
                review_decision = saved_review.get(
                    "decision"
                )

                reviewed_topic_id = saved_review.get(
                    "topic_id"
                )

                reviewed_topic_in_taxonomy = any(
                    isinstance(topic, dict)
                    and topic.get("topic_id")
                    == reviewed_topic_id
                    for topic in taxonomy_topics
                )

                if review_decision == "approved":
                    status = (
                        "verified"
                        if (
                            taxonomy_verified
                            and reviewed_topic_in_taxonomy
                            and reviewed_topic_id
                            == proposed_topic_id
                        )
                        else "unverified"
                    )
                else:
                    status = "rejected"
            else:
                status = "pending"

            can_approve = bool(
                not is_reviewed
                and proposed_topic_id
                and taxonomy_verified
                and topic_in_taxonomy
            )

            records.append({
                "question_id": question_id,
                "paper_id": question.get("paper_id"),
                "module_code": question_code,
                "module_name": question.get("module_name"),
                "module_key": question_module,
                "calendar_year": question.get("calendar_year"),
                "semester": question.get("semester"),
                "question_number": question.get("question_number"),
                "part_id": question.get("part_id"),
                "parent_id": question.get("parent_id"),
                "question_text": question.get("question_text"),
                "context": question.get("context"),
                "marks": question.get("marks"),
                "marks_status": question.get("marks_status"),
                "source_type": "authentic",
                "source_filename": question.get(
                    "source_filename"
                ),
                "bloom_level": question.get("bloom_level"),
                "difficulty": question.get("difficulty"),
                "proposed_classification": proposal,
                "review": saved_review,
                "verification_status": status,
                "can_approve": can_approve,
                "taxonomy_verified": taxonomy_verified,
            })

        total_questions = len(records)

        approved_count = sum(
            1
            for record in records
            if (
                record["review"]
                and record["review"].get("decision")
                == "approved"
            )
        )

        rejected_count = sum(
            1
            for record in records
            if (
                record["review"]
                and record["review"].get("decision")
                == "rejected"
            )
        )

        pending_count = (
            total_questions
            - approved_count
            - rejected_count
        )

        if include_reviewed:
            display_records = records
        else:
            display_records = [
                record
                for record in records
                if record["review"] is None
            ]

        display_total = len(display_records)

        start = (page - 1) * page_size

        paged_records = display_records[
            start:start + page_size
        ]

        selected_taxonomy = (
            taxonomies_by_key.get(module_key)
            if module_key
            else None
        )

        return {
            "module_key": module_key,
            "total": display_total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(
                1,
                (display_total + page_size - 1)
                // page_size,
            ),
            "statistics": {
                "total": total_questions,
                "pending": pending_count,
                "approved": approved_count,
                "rejected": rejected_count,
            },
            "taxonomy_status": {
                "module_key": module_key,
                "verification_status": (
                    selected_taxonomy.get(
                        "verification_status",
                        "unverified",
                    )
                    if selected_taxonomy
                    else "unverified"
                ),
                "is_verified": (
                    selected_taxonomy.get(
                        "verification_status"
                    ) == "verified"
                    if selected_taxonomy
                    else False
                ),
                "topics": (
                    selected_taxonomy.get("topics", [])
                    if selected_taxonomy
                    else []
                ),
            } if module_key else None,
            "questions": paged_records,
        }
