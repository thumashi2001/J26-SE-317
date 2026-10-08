import { getDb } from '../../../config/db.js';
import { ObjectId } from 'mongodb';

function httpError(status, message) {
  return Object.assign(new Error(message), { status });
}

function col() {
  return getDb().collection('c3_assessments');
}

/** Seed the PP1 development assessment if none exists. */
export async function seedDevAssessment() {
  const c = col();
  const existing = await c.findOne({ question_id: 'SE-DB-001' });
  if (existing) return existing;

  const doc = {
    title: 'Database Systems — PP1 Demonstration',
    course: 'Database Systems',
    question_id: 'SE-DB-001',
    question_text:
      'Explain database normalization and describe the purpose of the First Normal Form (1NF), Second Normal Form (2NF), and Third Normal Form (3NF).',
    reference_answer:
      'Database normalization is the process of organizing data in a relational database to reduce redundancy and prevent insertion, update, and deletion anomalies. First Normal Form requires attributes to contain atomic values and records to be uniquely identifiable. Second Normal Form requires the relation to be in 1NF and every non-key attribute to depend on the entire primary key. Third Normal Form requires the relation to be in 2NF and non-key attributes must not have transitive dependencies on the primary key.',
    expected_concepts: [
      'Database Normalization',
      'Data Redundancy',
      'Data Anomalies',
      'First Normal Form',
      'Atomic Values',
      'Second Normal Form',
      'Entire Primary Key',
      'Third Normal Form',
      'Transitive Dependency',
    ],
    rubric: {
      rubric_id: 'rubric-se-db-001',
      title: 'Database Normalization Rubric',
      criteria: [
        {
          criterion_id: 'c1',
          description: 'Normalization Purpose',
          max_marks: 2.0,
          scoring_levels: [
            {
              level_id: 'c1-l1',
              label: 'Demonstrated',
              mark: 2.0,
              descriptor: 'Clearly explains the purpose of reducing redundancy and anomalies.',
              required_concepts: ['Database Normalization', 'Data Redundancy', 'Data Anomalies'],
              evidence_requirements: ['Must mention reducing redundancy and avoiding anomalies.'],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 2, minimum_partial: 0, allow_partial: true },
            },
            {
              level_id: 'c1-l2',
              label: 'Partial',
              mark: 1.0,
              descriptor: 'Mentions database normalization but incomplete purpose.',
              required_concepts: ['Database Normalization'],
              evidence_requirements: ['Mentions database normalization.'],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 1, minimum_partial: 0, allow_partial: true },
            },
            {
              level_id: 'c1-l3',
              label: 'Not Demonstrated',
              mark: 0.0,
              descriptor: 'Fails to explain the purpose.',
              required_concepts: [],
              evidence_requirements: [],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 0, minimum_partial: 0, allow_partial: true },
            },
          ],
        },
        {
          criterion_id: 'c2',
          description: 'First Normal Form (1NF)',
          max_marks: 2.0,
          scoring_levels: [
            {
              level_id: 'c2-l1',
              label: 'Demonstrated',
              mark: 2.0,
              descriptor: 'Explains 1NF and atomic values correctly.',
              required_concepts: ['First Normal Form', 'Atomic Values'],
              evidence_requirements: ['Must mention atomic values and unique identification.'],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 1, minimum_partial: 0, allow_partial: true },
            },
            {
              level_id: 'c2-l2',
              label: 'Not Demonstrated',
              mark: 0.0,
              descriptor: 'Fails to explain 1NF.',
              required_concepts: [],
              evidence_requirements: [],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 0, minimum_partial: 0, allow_partial: true },
            },
          ],
        },
        {
          criterion_id: 'c3',
          description: 'Second Normal Form (2NF)',
          max_marks: 3.0,
          scoring_levels: [
            {
              level_id: 'c3-l1',
              label: 'Demonstrated',
              mark: 3.0,
              descriptor: 'Explains 2NF and full functional dependency correctly.',
              required_concepts: ['Second Normal Form', 'Entire Primary Key'],
              evidence_requirements: ['Must mention entire primary key dependency.'],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 1, minimum_partial: 0, allow_partial: true },
            },
            {
              level_id: 'c3-l2',
              label: 'Not Demonstrated',
              mark: 0.0,
              descriptor: 'Fails to explain 2NF.',
              required_concepts: [],
              evidence_requirements: [],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 0, minimum_partial: 0, allow_partial: true },
            },
          ],
        },
        {
          criterion_id: 'c4',
          description: 'Third Normal Form (3NF)',
          max_marks: 3.0,
          scoring_levels: [
            {
              level_id: 'c4-l1',
              label: 'Demonstrated',
              mark: 3.0,
              descriptor: 'Explains 3NF and transitive dependency correctly.',
              required_concepts: ['Third Normal Form', 'Transitive Dependency'],
              evidence_requirements: ['Must mention lack of transitive dependency.'],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 1, minimum_partial: 0, allow_partial: true },
            },
            {
              level_id: 'c4-l2',
              label: 'Not Demonstrated',
              mark: 0.0,
              descriptor: 'Fails to explain 3NF.',
              required_concepts: [],
              evidence_requirements: [],
              evidence_rule: { type: 'required_concept_count', minimum_demonstrated: 0, minimum_partial: 0, allow_partial: true },
            },
          ],
        },
      ],
    },
    answer_type: 'essay',
    max_marks: 10,
    status: 'active',
    created_by: 'system',
    is_dev_seed: true,
    created_at: new Date(),
    updated_at: new Date(),
  };
  await c.insertOne(doc);
  return doc;
}

export async function listAssessments() {
  return col().find({ status: 'active' }, { projection: { reference_answer: 0, rubric: 0 } }).toArray();
}

export async function getAssessment(id) {
  let doc;
  if (ObjectId.isValid(id)) {
    doc = await col().findOne({ _id: new ObjectId(id) });
  }
  if (!doc) doc = await col().findOne({ question_id: id });
  if (!doc) throw httpError(404, 'Assessment not found');
  return doc;
}

/** Returns the full assessment including private fields (for internal use by submission processing). */
export async function getAssessmentFull(id) {
  let doc;
  if (ObjectId.isValid(id)) {
    doc = await col().findOne({ _id: new ObjectId(id) });
  }
  if (!doc) doc = await col().findOne({ question_id: id });
  if (!doc) throw httpError(404, 'Assessment not found');
  return doc;
}
