"""Approval register: ties a lecturer-validation record to the exact rubric content it was given for.

A rubric document carries a self-reported `provenance` block. The approval register is a separate file kept by the custodian:
for each question it records the sha256 of the rubric object that was approved, the approval date, the approver's role, and a
pointer to where the institutional evidence is held (a reference such as a ticket number or the location of a signed form, never
the evidence itself, and no names).

What this does: if a rubric is edited after the register entry was made, the hashes differ and the approval is reported as
stale; a gold sheet cannot be built from a rubric whose approval is missing, stale or inconsistent.

What this does NOT do: authenticate anything. The software cannot tell whether the approver exists, is qualified, is authorised
by the study plan, or that the evidence reference is genuine; anyone who can edit the register can write a matching entry.
The register makes an honest process traceable and an accidental change visible; it is not proof of approval.
"""

import datetime
import re

from datasets.gold.common import canonical_bytes, sha256_hex
from datasets.gold.rubric_check import PLACEHOLDER

FORMAT = "c3-gold-approvals/1"
APPROVER_ROLE = "lecturer"
ENTRY_KEYS = {"question_id", "rubric_sha256", "approved_on", "approver_role", "evidence_ref", "recorded_by"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
AUTHENTICATION_LIMIT = (
    "The approval register is a record kept by people, not a proof. The software cannot authenticate the approver, check that "
    "they are authorised, or verify the evidence reference; it only checks that the record is complete, names no individual, and "
    "matches the rubric content it was made for."
)


def rubric_sha256(doc: dict) -> str:
    """Hash of the rubric object alone (not the provenance block), so a change to marking content changes the hash."""
    return sha256_hex(canonical_bytes(doc["rubric"]))


def _date(value: object) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def register_problems(register: object) -> list[str]:
    """Every problem found in a register (empty list = well-formed)."""
    if not isinstance(register, dict):
        return ["register must be a JSON object"]
    problems = []
    if register.get("format") != FORMAT:
        problems.append(f"format must be {FORMAT!r}")
    entries = register.get("entries")
    if not isinstance(entries, list):
        return problems + ["entries must be a list"]
    seen: set[str] = set()
    for n, e in enumerate(entries):
        where = f"entries[{n}]"
        if not isinstance(e, dict):
            problems.append(f"{where}: must be an object")
            continue
        extra = set(e) - ENTRY_KEYS
        if extra:
            problems.append(f"{where}: unexpected field(s) {sorted(extra)}; the register holds no names or other personal data")
        qid = str(e.get("question_id", "")).strip()
        if not qid or PLACEHOLDER.search(qid):
            problems.append(f"{where}: question_id is required")
        elif qid in seen:
            problems.append(f"{where}: more than one entry for {qid}")
        seen.add(qid)
        if not HEX64.match(str(e.get("rubric_sha256", ""))):
            problems.append(f"{where}: rubric_sha256 must be 64 lowercase hex characters")
        if _date(e.get("approved_on")) is None:
            problems.append(f"{where}: approved_on must be an ISO date (YYYY-MM-DD)")
        if e.get("approver_role") != APPROVER_ROLE:
            problems.append(f"{where}: approver_role must be {APPROVER_ROLE!r}")
        for field in ("evidence_ref", "recorded_by"):
            value = str(e.get(field, "")).strip()
            if not value or PLACEHOLDER.search(value):
                problems.append(f"{where}: {field} is required and must not be placeholder text")
    return problems


def approval_state(register: dict | None, doc: dict) -> str:
    """How well the register backs the document's lecturer-validation claim.

    no_register, register_invalid, no_entry, stale (rubric changed after the entry), date_inconsistent, or matches.
    """
    if register is None:
        return "no_register"
    if register_problems(register):
        return "register_invalid"
    entry = next((e for e in register["entries"] if e["question_id"] == doc.get("question_id")), None)
    if entry is None:
        return "no_entry"
    if entry["rubric_sha256"] != rubric_sha256(doc):
        return "stale"
    prov = doc.get("provenance", {})
    approved, validated, drafted = _date(entry["approved_on"]), _date(prov.get("validated_on")), _date(prov.get("drafted_on"))
    if approved is None or drafted is None or approved < drafted or (validated is not None and approved < validated):
        return "date_inconsistent"
    return "matches"
