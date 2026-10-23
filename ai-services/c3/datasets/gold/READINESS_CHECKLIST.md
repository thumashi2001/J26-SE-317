# Human-validation readiness checklist (Component 3)

Use this before any real marking. It separates what the repository already does in software from what only real people or the
institution can do. **Every item is Open.** Nothing here records an approval, a consent, a storage arrangement or an ethics
decision; when one is made, record its evidence in the study plan (outside the repository if it names people), not in this file.

How to read the columns: *Software safeguard* is what the tooling in this directory does today (each module is tested only on
simulated toy fixtures and has not been operationally validated). *Needs people or institution* is what no code can supply.
*Evidence to keep* is the record that would show the item was done.

## 1. Reviewers, markers and adjudicator: qualifications and consent

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Rubric reviewers are lecturers or equivalently qualified in the subject | `rubric_check` requires a named validator different from the drafter; `approval.py` requires role `lecturer` and holds no names | Decide who is qualified and authorised; the software cannot check this | Authorised-reviewer list in the study plan | Open |
| Two independent markers and one adjudicator, none the rubric drafter for the same item | `sheets.py` needs two distinct pseudonyms; `adjudication.py` refuses an adjudicator who is a marker | Recruit them; confirm independence | Roster by role and pseudonym | Open |
| Informed, voluntary participation | None | Explain the task, time and data use; obtain consent | Consent records held by the custodian | Open |

## 2. Rubric review and approval

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Each held-out question has a multi-level rubric document | `readiness.py` counts missing, unreadable and invalid documents | Draft the rubrics (a lecturer, or an AI tool whose use is declared) | Rubric documents | Open |
| An AI draft is not treated as validated | `rubric_check` rejects validation fields on `ai_drafted`; gold generation refuses it | Do not set `lecturer_validated` on anyone's behalf | Provenance block in each document | Open |
| A lecturer reviews and approves the exact rubric | `approval.py` records the approved rubric's hash; a later edit makes the record stale; gold generation refuses a missing or stale record | The review itself; the register entry | Register entry plus the institutional evidence it points to (`evidence_ref`) | Open |
| Approvals are authentic | **Not possible in software** (`approval.AUTHENTICATION_LIMIT`) | Custodian checks the approver and evidence; second person spot-checks the register | Custodian's verification note | Open |

## 3. Restricted storage and a named custodian

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| A named custodian holds the salt, key, plan and seals | The generator writes them to a separate custody directory and refuses to write inside a git working tree | Appoint the custodian; provide access-controlled storage outside the repository | Custodian appointment, storage location | Open |
| The key and salt never reach markers | Marker sheets contain no key, salt or dataset id (tested by scanning every file and file name) | Keep access limited to the custodian | Access list | Open |
| Salt is random and secret | Length of at least 16 characters only; not an entropy check | Generate it randomly and keep it private | Custodian's note | Open |
| Confidentiality of stored files | **Nothing**: no encryption, authentication or access log | Institutional controls | Storage policy reference | Open |

## 4. Distribution of blind marking sheets

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Sheets hide tiers, scores and dataset ids | Leak scans of all marker-visible text and pseudonyms; opaque ids; per-marker shuffled order | Send each marker only their own sheet through a private channel | Transmission log held by the custodian | Open |
| The 26 held-out questions only; pilot kept apart | `sampling.py` and `validate_plan` | Fix and record the seeds before looking at any model output | Plan hash and seeds in the study plan | Open |
| Sheets match what was sealed | Pre-marking seal; `--seal` checks | Store the seal where markers cannot change it | Seal copy held by the custodian | Open |

## 5. Return collection and integrity checks

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Returns are complete and use only allowed levels | `returns.py` validates each return against its own sheet | Collect returns privately | Receipt log | Open |
| A return belongs to the sealed sheet | The return names the sheet hash; `--seal` compares it with the seal | Keep the pre-marking seal out of the markers' reach | Seal copy | Open |
| Markers worked independently | **Cannot be checked** | Instruct markers; observe where possible | Instructions given | Open |

## 6. Pseudonym management and separation of identifying information

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Pseudonyms used in sheets, files and reports | Pseudonym format enforced; dataset ids and tier names refused as pseudonyms; reports name no reviewer | Keep the pseudonym-to-person register separate and restricted | Register held by the custodian | Open |
| Approval register and rubric documents carry no personal data | Register accepts only listed fields and rejects names; the `validated_by` field in a rubric document is a free string | Use a pseudonym or staff identifier there, never a full name, if the document leaves the custodian | Document review | Open |

## 7. Marking, thresholds, adjudication and unresolved scores

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Agreement thresholds fixed before marking | None applied by the tools (deliberately) | Decide and record them in the study plan first | Dated study plan | Open |
| Disagreements adjudicated by a third person; originals kept | `adjudication.py` never averages, never edits returns, requires reason and level from the rubric | Provide the adjudicator and the reasons | Adjudication record | Open |
| Unresolved and unmarkable items | Excluded, counted, and given no label | Decide how many exclusions are acceptable before marking | Study plan | Open |
| A pilot refines the procedure | `sampling.py` draws pilot questions from the training split | Run it; note what changed | Pilot notes (pilot items never enter the held-out set) | Open |

## 8. Ethics, data retention and participant privacy

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Ethics or data-governance confirmation | None | Confirm with the institution whether the exercise needs approval, and obtain it if so | Approval or written exemption | Open |
| No authentic student work | The dataset is synthetic; the decision log (DEC-06) forbids real scripts without clearance | Keep to it | Decision log | Open |
| Retention and deletion | None | Set retention for returns, the key and the pseudonym register | Retention schedule | Open |
| Participant privacy in published results | Reports use pseudonyms and counts | Review before publishing | Review note | Open |

## 9. Post-marking sealing and audit records

| Item | Software safeguard | Needs people or institution | Evidence to keep | Status |
|---|---|---|---|---|
| Returns, adjudication record and final labels are fixed after marking | `seal.py`: post-marking seal that binds each return to its sealed sheet and chains to the pre-marking seal | Run it; store the seal with the custodian | Post-marking seal | Open |
| Simulated results cannot pass as human results | Toy material carries `toy_fixture`, the notice, and `simulated: true`; the command line cannot create toy sheets | Never present a report from toy fixtures; check the origin and the notice | Report review | Open |
| An audit trail of who did what, when | **Not implemented**: no access log or signed steps | Keep a dated log of each step | Custodian's log | Open |
| Models are scored only after sealing | None enforced | Follow the protocol | Dated run record | Open |

## Reading the result

Software passing every test here still leaves every row above Open. The readiness audit (`readiness.py`) reports how many
held-out rubrics could go to genuine gold-sheet generation; today that is a count of documented, hash-matched records, not a
statement that anyone has been qualified, has consented, or has approved anything.
