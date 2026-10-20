export const C3_PRESETS = [
  {
    id: 'arch-full',
    title: 'Software Architecture — Full Credit (100%)',
    description: 'Demonstrates all 3 core concepts: high-level structure, components, and relationships.',
    payload: {
      question_id: 'SE3010-Q01',
      question_text: 'Explain the concept of software architecture and how its key elements organize a system.',
      student_answer:
        'Software architecture defines the high-level structure of a system. It organizes components and specifies their relationships clearly to ensure architectural integrity.',
      reference_answer:
        'Software architecture defines the high-level structure of a system comprising components and their relationships.',
      expected_concepts: ['high-level structure', 'components', 'relationships'],
      answer_type: 'short',
      rubric: {
        rubric_id: 'R-ARCH-01',
        title: 'Software Architecture Evaluation Rubric',
        criteria: [
          {
            criterion_id: 'C1',
            description: 'Demonstrate understanding of architectural structure and components.',
            max_marks: 4,
            required_concepts: ['high-level structure', 'components', 'relationships'],
            scoring_levels: [
              {
                level_id: 'L0',
                label: 'Unsatisfactory',
                mark: 0,
                descriptor: 'No relevant architectural concepts demonstrated.',
              },
              {
                level_id: 'L2',
                label: 'Developing',
                mark: 2,
                descriptor: 'At least one architectural concept demonstrated.',
                required_concepts: ['high-level structure', 'components', 'relationships'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 1,
                },
              },
              {
                level_id: 'L4',
                label: 'Proficient',
                mark: 4,
                descriptor: 'All three core concepts (structure, components, relationships) clearly demonstrated.',
                required_concepts: ['high-level structure', 'components', 'relationships'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 3,
                },
              },
            ],
          },
        ],
      },
    },
  },
  {
    id: 'arch-partial',
    title: 'Software Architecture — Partial Credit (50%)',
    description: 'Demonstrates structure only; misses components and relationships.',
    payload: {
      question_id: 'SE3010-Q01',
      question_text: 'Explain the concept of software architecture and how its key elements organize a system.',
      student_answer:
        'Software architecture provides a high-level structure for large-scale software applications.',
      reference_answer:
        'Software architecture defines the high-level structure of a system comprising components and their relationships.',
      expected_concepts: ['high-level structure', 'components', 'relationships'],
      answer_type: 'short',
      rubric: {
        rubric_id: 'R-ARCH-01',
        title: 'Software Architecture Evaluation Rubric',
        criteria: [
          {
            criterion_id: 'C1',
            description: 'Demonstrate understanding of architectural structure and components.',
            max_marks: 4,
            required_concepts: ['high-level structure', 'components', 'relationships'],
            scoring_levels: [
              {
                level_id: 'L0',
                label: 'Unsatisfactory',
                mark: 0,
                descriptor: 'No relevant architectural concepts demonstrated.',
              },
              {
                level_id: 'L2',
                label: 'Developing',
                mark: 2,
                descriptor: 'At least one architectural concept demonstrated.',
                required_concepts: ['high-level structure', 'components', 'relationships'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 1,
                },
              },
              {
                level_id: 'L4',
                label: 'Proficient',
                mark: 4,
                descriptor: 'All three core concepts (structure, components, relationships) clearly demonstrated.',
                required_concepts: ['high-level structure', 'components', 'relationships'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 3,
                },
              },
            ],
          },
        ],
      },
    },
  },
  {
    id: 'arch-zero',
    title: 'Irrelevant Answer — Zero Credit (0%)',
    description: 'Completely off-topic answer with no matching evidence.',
    payload: {
      question_id: 'SE3010-Q01',
      question_text: 'Explain the concept of software architecture and how its key elements organize a system.',
      student_answer:
        'I prefer cooking pasta and baking delicious homemade sourdough bread over the weekend.',
      reference_answer:
        'Software architecture defines the high-level structure of a system comprising components and their relationships.',
      expected_concepts: ['high-level structure', 'components', 'relationships'],
      answer_type: 'short',
      rubric: {
        rubric_id: 'R-ARCH-01',
        title: 'Software Architecture Evaluation Rubric',
        criteria: [
          {
            criterion_id: 'C1',
            description: 'Demonstrate understanding of architectural structure and components.',
            max_marks: 4,
            required_concepts: ['high-level structure', 'components', 'relationships'],
            scoring_levels: [
              {
                level_id: 'L0',
                label: 'Unsatisfactory',
                mark: 0,
                descriptor: 'No relevant architectural concepts demonstrated.',
              },
              {
                level_id: 'L2',
                label: 'Developing',
                mark: 2,
                descriptor: 'At least one architectural concept demonstrated.',
                required_concepts: ['high-level structure', 'components', 'relationships'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 1,
                },
              },
              {
                level_id: 'L4',
                label: 'Proficient',
                mark: 4,
                descriptor: 'All three core concepts (structure, components, relationships) clearly demonstrated.',
                required_concepts: ['high-level structure', 'components', 'relationships'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 3,
                },
              },
            ],
          },
        ],
      },
    },
  },
  {
    id: 'oop-higher',
    title: 'OOP Principles — Higher-Level Concept Progression',
    description: 'Multi-level rubric evaluating encapsulation, polymorphism, and runtime dispatch.',
    payload: {
      question_id: 'SE2020-Q03',
      question_text: 'Discuss polymorphism and explain its mechanism during execution.',
      student_answer:
        'Polymorphism enables interchangeable behavior across object hierarchies. In modern languages, it relies on dynamic runtime dispatch to select the correct implementation.',
      reference_answer:
        'Polymorphism allows objects of different types to be treated uniformly, achieved via runtime dispatch.',
      expected_concepts: ['polymorphism', 'runtime dispatch'],
      answer_type: 'short',
      rubric: {
        rubric_id: 'R-OOP-01',
        title: 'Object-Oriented Programming Progression Rubric',
        criteria: [
          {
            criterion_id: 'C1',
            description: 'Understanding OOP behavioral abstraction mechanisms.',
            max_marks: 3,
            scoring_levels: [
              {
                level_id: 'L0',
                label: 'None',
                mark: 0,
                descriptor: 'No relevant OOP evidence provided.',
              },
              {
                level_id: 'L1',
                label: 'Basic',
                mark: 1,
                descriptor: 'Demonstrates basic encapsulation concepts.',
                required_concepts: ['encapsulation'],
              },
              {
                level_id: 'L2',
                label: 'Intermediate',
                mark: 2,
                descriptor: 'Demonstrates polymorphism principles.',
                required_concepts: ['polymorphism'],
              },
              {
                level_id: 'L3',
                label: 'Advanced',
                mark: 3,
                descriptor: 'Demonstrates both polymorphism and runtime dispatch mechanisms.',
                required_concepts: ['polymorphism', 'runtime dispatch'],
              },
            ],
          },
        ],
      },
    },
  },
  {
    id: 'quality-multi',
    title: 'System Quality — Multi-Criterion Evaluation',
    description: 'Separate criteria for Security (C1) and Reliability (C2) with distinct concept requirements.',
    payload: {
      question_id: 'SE3040-Q02',
      question_text: 'Explain how access control ensures security and fault tolerance ensures reliability.',
      student_answer:
        'We strictly enforce access control across all API boundaries using fine-grained authorization policies.',
      reference_answer:
        'Security is ensured through access control, while reliability is maintained via fault tolerance.',
      expected_concepts: ['access control', 'fault tolerance'],
      answer_type: 'short',
      rubric: {
        rubric_id: 'R-QUALITY-01',
        title: 'Non-Functional Requirements Rubric',
        criteria: [
          {
            criterion_id: 'C1',
            description: 'Security & Access Control.',
            max_marks: 2,
            required_concepts: ['access control'],
            scoring_levels: [
              {
                level_id: 'L0',
                label: 'None',
                mark: 0,
                descriptor: 'No security evidence provided.',
              },
              {
                level_id: 'L2',
                label: 'Proficient',
                mark: 2,
                descriptor: 'Access control mechanisms clearly demonstrated.',
                required_concepts: ['access control'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 1,
                },
              },
            ],
          },
          {
            criterion_id: 'C2',
            description: 'System Reliability & Fault Tolerance.',
            max_marks: 2,
            required_concepts: ['fault tolerance'],
            scoring_levels: [
              {
                level_id: 'L0',
                label: 'None',
                mark: 0,
                descriptor: 'No reliability evidence provided.',
              },
              {
                level_id: 'L2',
                label: 'Proficient',
                mark: 2,
                descriptor: 'Fault tolerance mechanisms clearly demonstrated.',
                required_concepts: ['fault tolerance'],
                evidence_rule: {
                  type: 'required_concept_count',
                  minimum_demonstrated: 1,
                },
              },
            ],
          },
        ],
      },
    },
  },
  {
    id: 'mcq-correct',
    title: 'Architecture Pattern MCQ — Correct Key (100%)',
    description: 'Deterministic answer-key evaluation: selects Option B (Microservices). Awards full marks (2/2).',
    payload: {
      question_id: 'SE3010-MCQ-01',
      question_text: 'Which architectural style structures an application as a collection of loosely coupled, independently deployable services?',
      student_answer: 'Option B',
      selected_option_id: 'B',
      correct_answer: 'B',
      answer_type: 'mcq',
      max_marks: 2,
      expected_concepts: ['microservices', 'loosely coupled'],
      options: [
        { option_id: 'A', label: 'A', text: 'Monolithic Architecture' },
        { option_id: 'B', label: 'B', text: 'Microservices Architecture' },
        { option_id: 'C', label: 'C', text: 'Pipe and Filter Architecture' },
        { option_id: 'D', label: 'D', text: 'Model-View-Controller (MVC)' },
      ],
    },
  },
  {
    id: 'mcq-incorrect',
    title: 'Architecture Pattern MCQ — Incorrect Key (0%)',
    description: 'Deterministic answer-key evaluation: selects Option A (Monolith). Awards zero marks (0/2).',
    payload: {
      question_id: 'SE3010-MCQ-01',
      question_text: 'Which architectural style structures an application as a collection of loosely coupled, independently deployable services?',
      student_answer: 'Option A',
      selected_option_id: 'A',
      correct_answer: 'B',
      answer_type: 'mcq',
      max_marks: 2,
      expected_concepts: ['microservices', 'loosely coupled'],
      options: [
        { option_id: 'A', label: 'A', text: 'Monolithic Architecture' },
        { option_id: 'B', label: 'B', text: 'Microservices Architecture' },
        { option_id: 'C', label: 'C', text: 'Pipe and Filter Architecture' },
        { option_id: 'D', label: 'D', text: 'Model-View-Controller (MVC)' },
      ],
    },
  },
];

