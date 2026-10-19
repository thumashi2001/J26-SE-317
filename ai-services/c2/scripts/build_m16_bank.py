"""Helper script to construct and validate config/m16_expanded_content_bank.json."""

import json
from pathlib import Path

from services.synthetic_content_bank import SyntheticContentBank

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "config" / "m16_expanded_content_bank.json"

M16_MODULES = [
    {
        "module_key": "database_systems",
        "topics": [
            {
                "name": "SQL Queries",
                "question_type": "apply",
                "response_format": "sql_code",
                "source_year": 2023,
                "scenarios": [
                    "A cinema ticketing database records films, cinema halls, daily screenings, ticket purchases, and loyalty club members.",
                    "A university library database maintains catalogued books, registered members, borrowing transactions, and overdue fines.",
                    "A multi-speciality hospital database tracks admitted patients, consultant doctors, clinical departments, ward stays, and scheduled surgeries.",
                    "An online retail marketplace records registered vendors, catalogued products, customer shopping carts, confirmed orders, and refund requests.",
                    "A public transit authority logs scheduled bus routes, vehicle fleets, assigned drivers, passenger smart-card taps, and delay incidents.",
                ],
                "tasks": [
                    "Formulate a SQL query joining the primary entities to calculate aggregate totals, applying a HAVING filter and descending sort.",
                    "Construct an optimized SQL query utilizing common table expressions (CTEs) or window functions to identify top-ranked records within each group.",
                    "Write a defensive SQL statement addressing NULL handling in left outer joins and conditional aggregation across missing transaction records.",
                    "Design a relational view with appropriate GROUP BY clauses that produces an operational audit report summarizing activity by time interval.",
                ],
            },
            {
                "name": "Database Indexing",
                "question_type": "analyze",
                "response_format": "technical_analysis",
                "source_year": 2023,
                "scenarios": [
                    "A logistics tracking platform experiences severe latency when querying shipment history tables exceeding fifty million records.",
                    "A commercial banking system experiences read bottlenecks during month-end customer statement generation across ledger tables.",
                    "A healthcare portal retrieves patient consultation logs filtered concurrently by medical department, doctor ID, and date ranges.",
                    "An e-commerce flash-sale platform handles concurrent high-volume product lookups by SKU, price range, and stock availability.",
                    "A smart-meter energy telemetry database inserts thousands of sensor readings per second while operators execute real-time anomaly queries.",
                ],
                "tasks": [
                    "Analyze the query workload and recommend a composite B-tree index, justifying the ordering of leading and secondary index columns.",
                    "Evaluate the trade-offs between clustered versus non-clustered indexing for this table in terms of disk I/O and page splits.",
                    "Compare index-only covering scans against full table scans with residual filtering, considering index maintenance overhead during bulk inserts.",
                    "Examine how index selectivity, data cardinality, and histogram statistics influence the query optimizer's access path selection.",
                ],
            },
            {
                "name": "Database Normalization and Schema Design",
                "question_type": "design",
                "response_format": "schema_design",
                "source_year": 2023,
                "scenarios": [
                    "An equipment rental firm stores rental contracts, customer details, equipment items, maintenance logs, and insurance waivers in a flat table.",
                    "A clinical trial management system records volunteer subjects, experimental drug regimens, adverse event reports, and attending clinicians in an unnormalized spreadsheet.",
                    "A university examination division maintains student registrations, course modules, instructor assignments, and grade submission records in a consolidated table.",
                    "A hotel chain logs guest reservations, room types, seasonal pricing tiers, billing folios, and amenity bookings in a denormalized database.",
                    "A fleet maintenance company tracks vehicle inspections, replacement parts, certified mechanics, and supplier purchase orders in a combined repository.",
                ],
                "tasks": [
                    "Identify the functional dependencies, determine the current normal form of the relation, and decompose the schema into Third Normal Form (3NF).",
                    "Analyze whether the proposed decomposition satisfies the lossless-join property and preserves all functional dependencies, proving your conclusion.",
                    "Illustrate the insertion, update, and deletion anomalies present in the unnormalized design with concrete data examples.",
                    "Design a Boyce-Codd Normal Form (BCNF) schema and discuss whether any dependency preservation trade-offs necessitate remaining in 3NF.",
                ],
            },
            {
                "name": "Transaction Concurrency and Recovery",
                "question_type": "evaluate",
                "response_format": "concurrency_analysis",
                "source_year": 2023,
                "scenarios": [
                    "Two concurrent booking agents attempt to reserve the final remaining seat on an intercity express train simultaneously.",
                    "An automated bank transfer debits a savings account while a simultaneous standing order processes loan repayment from the same balance.",
                    "An online auction system processes rapid bid increments while an administrative process aggregates the current highest bids for public display.",
                    "A warehouse management service updates stock quantities for an outgoing dispatch while a replenishment shipment is received concurrently.",
                    "A database server loses power while executing a multi-table financial settlement after writing data pages but prior to checkpoint completion.",
                ],
                "tasks": [
                    "Identify the concurrency anomaly (dirty read, non-repeatable read, or phantom read) that could arise and explain the minimum ANSI isolation level required.",
                    "Evaluate how strict two-phase locking (S2PL) prevents cascading aborts in this scenario and examine potential deadlock conditions.",
                    "Contrast pessimistic row-level locking against multi-version concurrency control (MVCC) for this specific read/write distribution.",
                    "Trace the write-ahead logging (WAL) redo and undo phases during crash recovery to explain how ACID atomicity and durability are guaranteed.",
                ],
            },
            {
                "name": "Query Optimization and Execution Plans",
                "question_type": "analyze",
                "response_format": "optimization_report",
                "source_year": 2023,
                "scenarios": [
                    "An analytical dashboard executes a multi-table join with nested subqueries that takes several minutes due to Cartesian product materialization.",
                    "A financial reporting query filtering historical ledger accounts by transaction year triggers expensive sequential table scans despite available indexes.",
                    "A customer relationship platform runs complex string-matching predicates and correlated subqueries across millions of interaction logs.",
                    "A billing calculation query computes running balances across customer accounts using self-joins instead of window partitioning.",
                    "A supply-chain analytics query joins distributed shipment and inventory partitions without leveraging partition pruning.",
                ],
                "tasks": [
                    "Analyze the relational algebra tree and recommend transformation heuristics that push selections and projections below join operators.",
                    "Explain why the cost-based optimizer chose a nested loop join over a hash join in this context, citing cardinality estimation errors.",
                    "Reformulate the correlated subquery into an equivalent join or window function construct and analyze the reduction in estimated query cost.",
                    "Recommend physical database design adjustments, such as table partitioning or materialized views, to accelerate this reporting workload.",
                ],
            },
        ],
    },
    {
        "module_key": "case_studies_software_engineering",
        "topics": [
            {
                "name": "Case Study Requirements",
                "question_type": "analyze",
                "response_format": "case_study",
                "source_year": 2024,
                "scenarios": [
                    "A regional municipal council commissions an online permit application and inspection platform involving citizens, field inspectors, and zoning officers.",
                    "A multi-branch veterinary clinic replaces fragmented paper cards with an integrated pet medical record, prescription, and surgery appointment system.",
                    "A national disaster management agency requires a resource dispatch and volunteer mobilization platform operating under intermittent mobile network coverage.",
                    "A commercial seaport authority plans an automated container gate inspection and berth allocation system coordinating shipping agents and customs.",
                    "A mental health counselling collective requires an anonymous booking, teleconsultation, and encrypted session notes platform with strict confidentiality rules.",
                ],
                "tasks": [
                    "Identify the primary and secondary actors, specify three critical functional requirements, and delineate clear system boundary constraints.",
                    "Analyze conflicting requirements between regulatory compliance and operational speed, proposing a defensible compromise based on risk.",
                    "Formulate a detailed use-case specification for the core business workflow, including preconditions, main success path, and two alternative flows.",
                    "Categorize the non-functional requirements into usability, reliability, and security, defining measurable metrics for verification.",
                ],
            },
            {
                "name": "UML and Design Decisions",
                "question_type": "design",
                "response_format": "uml_diagram",
                "source_year": 2024,
                "scenarios": [
                    "A vehicle leasing syndicate manages long-term fleet contracts, scheduled maintenance intervals, insurance claims, and telematics tracking.",
                    "A corporate talent acquisition system tracks candidate applications, interview panels, standardized evaluation rubrics, and automated job offers.",
                    "A subscription video-on-demand service manages content licensing windows, multi-device concurrent streams, parental controls, and billing tiers.",
                    "A digital smart-warehouse platform coordinates autonomous guided vehicles, pallet racking slots, picking lists, and barcode verification stations.",
                    "An academic peer-review portal manages journal manuscript submissions, double-blind reviewer assignments, rebuttal rounds, and editorial decisions.",
                ],
                "tasks": [
                    "Design a comprehensive UML class diagram detailing class attributes, method signatures, association cardinalities, and composition semantics.",
                    "Construct a state machine diagram capturing the complete lifecycle of the primary domain entity, including transition guards and actions.",
                    "Evaluate alternative modeling choices between class inheritance and object composition for this domain, justifying your final decision.",
                    "Create a package diagram illustrating high-level architectural decomposition and dependencies, ensuring low coupling across subsystems.",
                ],
            },
            {
                "name": "Sequence Diagrams and Interaction Modeling",
                "question_type": "design",
                "response_format": "sequence_diagram",
                "source_year": 2024,
                "scenarios": [
                    "An international funds transfer requires anti-money-laundering checks, currency exchange reservation, account debiting, and SWIFT notification.",
                    "An online examination portal authenticates a student via biometric verification, issues a time-locked exam paper, and monitors heartbeat connectivity.",
                    "A rideshare booking platform pairs a rider request with candidate drivers, handles countdown acceptance, pre-authorizes payment, and dispatches navigation.",
                    "A telemedicine consultation system initiates an encrypted WebRTC video bridge, records clinical vitals, and issues a digital prescription to an external pharmacy.",
                    "An automated baggage drop system at an international airport weighs luggage, verifies flight booking tags, scans for security alerts, and triggers conveyor routing.",
                ],
                "tasks": [
                    "Construct a detailed UML sequence diagram illustrating object lifelines, synchronous messages, asynchronous events, and return values for the primary flow.",
                    "Model alternate scenarios and exception handling using sequence diagram fragments (alt, opt, and loop) to represent system failure modes.",
                    "Analyze the sequence interaction to detect architectural bottlenecks, excessive round-trip chats, or tight coupling between client and backend lifelines.",
                    "Refactor the interaction sequence from a centralized controller paradigm to an event-driven choreography and compare the structural trade-offs.",
                ],
            },
            {
                "name": "Software Design Patterns",
                "question_type": "apply",
                "response_format": "pattern_justification",
                "source_year": 2024,
                "scenarios": [
                    "A document conversion utility must process diverse file formats (PDF, DOCX, EPUB) and export them into multiple target formats without tight coupling.",
                    "A financial analytics workstation needs to notify multiple charting widgets, risk meters, and trade alerts whenever real-time stock prices update.",
                    "A multi-carrier shipping calculator must apply distinct tariff calculation algorithms dynamically based on destination, weight, and delivery urgency.",
                    "A smart-home automation controller requires building complex multi-step scene routines comprising lighting, temperature, and security rules.",
                    "A legacy database wrapper needs a unified, simplified interface to insulate newly developed business modules from underlying complexity.",
                ],
                "tasks": [
                    "Identify the most suitable Gang of Four (GoF) design pattern for this problem and justify how it fulfills open/closed and single-responsibility principles.",
                    "Provide a class diagram or structural blueprint showing pattern participants, interfaces, and concrete implementations tailored to this context.",
                    "Explain how the chosen pattern prevents architectural rigidity and simplifies future extension when new domain variants are introduced.",
                    "Critique a potential misapplication of this pattern and evaluate whether a simpler refactoring would suffice without added indirection.",
                ],
            },
            {
                "name": "Architectural Refactoring and Quality Evaluation",
                "question_type": "evaluate",
                "response_format": "architectural_refactoring",
                "source_year": 2024,
                "scenarios": [
                    "A ten-year-old monolithic healthcare application suffers from frequent regression bugs and deployment lockouts during minor feature updates.",
                    "A retail inventory platform with embedded SQL queries throughout UI templates struggles to support a newly required mobile application.",
                    "A fintech startup built a prototype with hard-coded third-party payment APIs that now blocks international expansion into multi-gateway markets.",
                    "A school management system with tight circular dependencies between grading, attendance, and fee modules fails whenever any single module changes.",
                    "A logistics dispatch system with high CPU spikes refactors from polling-based batch sync to an asynchronous reactive pipeline.",
                ],
                "tasks": [
                    "Identify the underlying architectural code smells and anti-patterns in this case study, detailing their impact on system maintainability.",
                    "Formulate an incremental refactoring strategy utilizing the Strangler Fig pattern to modernize the system without operational disruption.",
                    "Evaluate the impact of the proposed refactoring on key ISO 25010 software quality attributes, specifically maintainability, testability, and performance.",
                    "Define a suite of automated regression and architecture fitness functions to guarantee that code quality invariants remain intact post-refactoring.",
                ],
            },
        ],
    },
    {
        "module_key": "software_project_management",
        "topics": [
            {
                "name": "Project Selection",
                "question_type": "evaluate",
                "response_format": "weighted_scoring",
                "source_year": 2024,
                "scenarios": [
                    "A regional university must allocate a fixed annual capital budget among a student mobile portal, an automated grading system, and a campus Wi-Fi upgrade.",
                    "A commercial healthcare provider evaluates three competing electronic health record replacement proposals from different software vendors.",
                    "A national postal corporation decides between developing an internal parcel tracking system or licensing an enterprise off-the-shelf platform.",
                    "A retail banking group prioritizes strategic IT initiatives across mobile biometric payments, automated loan origination, and core mainframe modernization.",
                    "A municipal transport authority assesses three smart-traffic management bids with varying capital expenditure and delivery schedules.",
                ],
                "tasks": [
                    "Construct a weighted scoring model with justified criteria weights and rating scales, calculating composite scores to rank candidate projects.",
                    "Perform a financial appraisal comparing Net Present Value (NPV), Internal Rate of Return (IRR), and Payback Period across the investment options.",
                    "Conduct a sensitivity analysis demonstrating how shifts in strategic corporate priorities would alter the recommended project selection.",
                    "Evaluate the non-financial criteria, including organizational readiness and technical risk, that could override a purely quantitative scoring outcome.",
                ],
            },
            {
                "name": "Project Risk and Control",
                "question_type": "analyze",
                "response_format": "management_report",
                "source_year": 2024,
                "scenarios": [
                    "A critical cloud-migration initiative loses two senior software architects three weeks prior to commencing integration test phases.",
                    "A government digital tax portal project experiences continuous scope creep due to shifting legislative guidelines during development sprints.",
                    "A distributed software development project suffers from severe communication breakdowns between offshore developers and onshore product owners.",
                    "A medical device firmware project discovers that a key third-party library has unpatched security vulnerabilities near scheduled release.",
                    "A mobile banking app release is threatened by vendor delivery delays for the core hardware security module integration.",
                ],
                "tasks": [
                    "Construct a comprehensive Risk Register detailing identified risks, probability and impact ratings, risk exposure scores, and root causes.",
                    "Develop proactive mitigation and reactive contingency strategies for the top two risks, assigning explicit ownership and monitoring triggers.",
                    "Analyze how scope creep and requirement churn affect the project triple constraints (cost, schedule, and quality) and propose a change control workflow.",
                    "Evaluate project monitoring indicators, including Earned Value Management (EVM) metrics, to diagnose whether the project is over budget or behind schedule.",
                ],
            },
            {
                "name": "Activity Scheduling and Critical Path Analysis",
                "question_type": "apply",
                "response_format": "cpm_pert_analysis",
                "source_year": 2024,
                "scenarios": [
                    "A software release project has twelve interconnected development and deployment activities with defined predecessor dependencies.",
                    "A core banking migration project must schedule parallel data extraction, validation, dress rehearsals, and customer cutover activities.",
                    "An enterprise ERP implementation project coordinates hardware provisioning, software customization, end-user training, and parallel run runs.",
                    "A cyber-security compliance upgrade project schedules vulnerability scans, system patching, penetration tests, and external audit milestones.",
                    "A telecommunications billing platform upgrade must execute database migration, API regression, load testing, and production cutover over a holiday weekend.",
                ],
                "tasks": [
                    "Construct an activity-on-node (AON) network diagram, calculate early/late start and finish dates, and identify the project Critical Path.",
                    "Determine total float and free float for all non-critical activities and explain their managerial significance for resource leveling.",
                    "Apply PERT three-point estimation (optimistic, most likely, pessimistic) to calculate expected project duration and the probability of on-time completion.",
                    "Evaluate schedule compression options (fast-tracking versus crashing) and assess the cost and risk implications of compressing the critical path.",
                ],
            },
            {
                "name": "Effort and Cost Estimation",
                "question_type": "apply",
                "response_format": "estimation_model",
                "source_year": 2024,
                "scenarios": [
                    "A software consulting firm must quote a fixed-price bid for an enterprise document management system based on preliminary functional specifications.",
                    "An agile development team estimates backlog effort for a customer self-service portal using story points and historical sprint velocity.",
                    "A mobile health startup plans engineering budgets using Function Point Analysis (FPA) from user interaction and data transaction counts.",
                    "A government contractor estimates software development effort and staffing curves using the COCOMO II post-architecture model.",
                    "A fintech engineering department plans annual headcount allocation across three major microservice modernization initiatives.",
                ],
                "tasks": [
                    "Calculate unadjusted and adjusted function points from transaction and data function counts, translating the result into estimated person-months.",
                    "Evaluate the strengths and limitations of algorithmic estimation (COCOMO) versus expert judgment (Planning Poker) for this project phase.",
                    "Calculate project staffing curves using Rayleigh-Putnam distribution concepts and discuss the dangers of Brook's Law during schedule slippage.",
                    "Formulate a cost breakdown structure (CBS) encompassing direct labor, tooling licenses, cloud infrastructure, and risk contingency reserves.",
                ],
            },
            {
                "name": "Agile Project Governance and Sprint Management",
                "question_type": "evaluate",
                "response_format": "agile_governance",
                "source_year": 2024,
                "scenarios": [
                    "A mature enterprise transitioning from Waterfall to Scrum experiences friction between traditional PMO reporting and cross-functional teams.",
                    "An agile development team consistently fails to complete committed user stories within two-week sprints due to shifting external priorities.",
                    "A safety-critical software project must demonstrate regulatory compliance and traceability while adopting iterative agile delivery practices.",
                    "A fast-growing scale-up coordinates five separate feature teams working on a unified mobile application using a scaled agile framework.",
                    "A software product team disputes the Definition of Done (DoD) between developers seeking rapid release and QA engineers demanding manual testing.",
                ],
                "tasks": [
                    "Analyze sprint burndown and velocity charts to diagnose team impediments, scope additions, and inaccurate backlog estimation.",
                    "Design a robust Definition of Ready (DoR) and Definition of Done (DoD) to enforce quality gates without compromising sprint agility.",
                    "Compare Scrum versus Kanban frameworks for this maintenance and enhancement workload, justifying the superior approach.",
                    "Evaluate governance mechanisms for tracking project progress, stakeholder communication, and architectural runway in a multi-team agile setting.",
                ],
            },
        ],
    },
    {
        "module_key": "user_experience_engineering",
        "topics": [
            {
                "name": "User Research and Design Thinking",
                "question_type": "analyze",
                "response_format": "ux_analysis",
                "source_year": 2024,
                "scenarios": [
                    "A public pension portal suffers from low online adoption among elderly citizens who rely on family members or postal forms.",
                    "An educational tablet application designed for primary school students receives complaints regarding confusing navigation and visual clutter.",
                    "A digital agricultural advisory app targeted at rural farmers encounters abandonment due to low digital literacy and intermittent connectivity.",
                    "A university course registration portal experiences extreme student frustration and abandonment during competitive registration windows.",
                    "A hospital patient discharge application designed for busy nurses on ward tablets exhibits frequent input errors during shift handovers.",
                ],
                "tasks": [
                    "Formulate a user research plan combining qualitative and quantitative methods (interviews, contextual inquiry, surveys) tailored to this cohort.",
                    "Synthesize empirical research findings into two detailed user personas and corresponding empathy maps representing distinct user behaviors.",
                    "Apply the five stages of Design Thinking (Empathize, Define, Ideate, Prototype, Test) to address the identified user pain points.",
                    "Construct an end-to-end user journey map documenting user emotional states, touchpoints, obstacles, and opportunities for experience enhancement.",
                ],
            },
            {
                "name": "Hierarchical Task Analysis",
                "question_type": "design",
                "response_format": "hta_diagram",
                "source_year": 2024,
                "scenarios": [
                    "A self-service kiosk at a railway station requires passengers to search routes, choose fare categories, select seats, and complete contactless payment.",
                    "A medical infusion pump interface requires clinical staff to calculate dosage, set delivery rates, confirm patient ID, and override safety limits.",
                    "An e-commerce mobile checkout workflow guides users through promo code validation, address selection, shipping speed, and payment authentication.",
                    "An online banking web portal enables business users to schedule batch salary disbursements requiring multi-signatory approval.",
                    "An automobile touchscreen infotainment dashboard allows drivers to navigate, adjust dual-zone climate, and manage media while driving.",
                ],
                "tasks": [
                    "Develop a comprehensive Hierarchical Task Analysis (HTA) diagram breaking down the top-level user goal into subtasks and sub-operations.",
                    "Specify rigorous task execution plans (e.g., Plan 0, Plan 1) detailing ordering, conditional branching, and cycle rules for subtasks.",
                    "Analyze the HTA structure to identify cognitive overload risks, redundant user actions, and opportunities for automation or error recovery.",
                    "Compare the HTA task flow against Norman's Action Cycle, identifying potential gulfs of execution and gulfs of evaluation in the workflow.",
                ],
            },
            {
                "name": "Usability Evaluation and Heuristic Inspection",
                "question_type": "evaluate",
                "response_format": "heuristic_evaluation",
                "source_year": 2024,
                "scenarios": [
                    "An online travel reservation site features complex dropdown menus, hidden booking fees, and obscure cancellation policies.",
                    "A collaborative project management tool presents cluttered dashboards with cryptic status icons and no undo capability for deleted tasks.",
                    "A digital pharmacy ordering application displays medication dosages with confusing abbreviations and unclear order status indicators.",
                    "A municipal parking meter mobile app fails to provide transaction receipts and locks user screens during slow network calls.",
                    "A cloud storage sharing interface uses ambiguous terminology ('Sync', 'Archive', 'Backup') leading to accidental data deletion.",
                ],
                "tasks": [
                    "Conduct a heuristic evaluation using Nielsen's Ten Usability Heuristics, documenting specific violations, affected screens, and severity ratings.",
                    "Design a formal usability testing experiment, specifying participant recruiting criteria, task scenarios, performance metrics, and post-test questionnaires (SUS).",
                    "Evaluate the trade-offs between expert heuristic inspection versus empirical user usability testing in terms of cost, time, and bug discovery.",
                    "Formulate concrete, prioritized redesign recommendations addressing the discovered heuristic violations to improve user satisfaction.",
                ],
            },
            {
                "name": "Interaction Prototyping and Wireframe Specification",
                "question_type": "design",
                "response_format": "wireframe_specification",
                "source_year": 2024,
                "scenarios": [
                    "A personal budgeting application requires an intuitive interface for quick expense logging, category breakdown, and monthly budget alerts.",
                    "A library book reservation app needs low-fidelity wireframes for book search, shelf location guidance, and digital loan renewals.",
                    "A food delivery app requires a tablet-optimized dashboard for restaurant kitchen staff to manage incoming, cooking, and dispatched orders.",
                    "A fitness tracking smartwatch companion app requires glanceable widgets and intuitive touch gestures for workout tracking.",
                    "A community recycling mobile app designs interactive onboarding screens explaining sorting rules and local drop-off collection spots.",
                ],
                "tasks": [
                    "Create structured wireframe specifications detailing layout hierarchy, visual affordances, information density, and interactive component states.",
                    "Design an interaction flow demonstrating responsive layout adaptations across mobile, tablet, and desktop breakpoints.",
                    "Evaluate the fidelity requirements (low-fidelity paper sketches vs high-fidelity interactive Figma prototypes) for testing this interaction.",
                    "Apply Gestalt visual perception principles (proximity, similarity, continuity, closure) to justify the spatial arrangement of interface elements.",
                ],
            },
            {
                "name": "Accessibility and Inclusive Interface Design",
                "question_type": "apply",
                "response_format": "accessibility_audit",
                "source_year": 2024,
                "scenarios": [
                    "A government social welfare portal must guarantee full accessibility for visually impaired citizens relying on screen readers.",
                    "A public utility billing web application uses subtle color shades to convey bill payment urgency, excluding color-blind citizens.",
                    "A university video lecture portal contains instructional audio without synchronized closed captions or downloadable transcripts.",
                    "A ride-booking application requires complex multi-touch drag gestures that pose barriers for users with motor impairments.",
                    "An emergency shelter guidance website must remain readable and navigable under high-stress conditions and low-bandwidth connections.",
                ],
                "tasks": [
                    "Audit the described interface against WCAG 2.2 AA standards across the four principles: Perceivable, Operable, Understandable, and Robust.",
                    "Formulate remediation steps for color contrast, keyboard navigability (focus states, tab order), and ARIA landmark roles.",
                    "Design an alternative accessible interaction path for motor-impaired users that replaces complex drag gestures with single-switch controls.",
                    "Evaluate how inclusive design practices benefit non-disabled users in situational impairments (e.g., bright sunlight, noisy environments).",
                ],
            },
        ],
    },
    {
        "module_key": "application_frameworks",
        "topics": [
            {
                "name": "REST API and Middleware",
                "question_type": "apply",
                "response_format": "api_design",
                "source_year": 2023,
                "scenarios": [
                    "An online restaurant ordering backend exposes endpoints for menu browsing, cart modifications, order placement, and delivery tracking.",
                    "A university student attendance platform provides secure REST APIs consumed by mobile apps and physical RFID gate scanners.",
                    "A digital music streaming service designs endpoints for playlist curation, collaborative song queues, and user playback history.",
                    "An inventory warehouse platform provides APIs for bulk stock intake, barcode scanner verification, and automated reorder alerts.",
                    "A telemedicine consultation system exposes endpoints for appointment scheduling, patient clinical history, and digital prescriptions.",
                ],
                "tasks": [
                    "Design a RESTful resource hierarchy detailing HTTP verbs, resource URIs, payload schemas, and precise HTTP status code conventions.",
                    "Construct an Express middleware pipeline demonstrating sequential execution of request validation, JWT authentication, and structured logging.",
                    "Implement robust API error handling middleware that captures uncaught exceptions and transforms them into standardized RFC 7807 problem details.",
                    "Formulate an API versioning and pagination strategy (cursor-based vs offset-based) to ensure backward compatibility and prevent database overload.",
                ],
            },
            {
                "name": "Framework Debugging",
                "question_type": "analyze",
                "response_format": "code_review",
                "source_year": 2023,
                "scenarios": [
                    "An Express.js application intermittently sends 'Headers already sent' error responses when database validation fails in asynchronous callbacks.",
                    "A React single-page application exhibits infinite re-rendering loops and UI stuttering during complex dashboard state updates.",
                    "A Node.js backend suffers from a memory leak where detached socket listeners and global cache maps cause heap exhaustion over time.",
                    "An asynchronous order processing service creates duplicate charges due to unhandled promise rejections and missing idempotency checks.",
                    "A web application framework fails to prevent Cross-Site Scripting (XSS) due to improper sanitization in user comment rendering templates.",
                ],
                "tasks": [
                    "Analyze the root cause of the described defect within the framework runtime lifecycle and explain why traditional try/catch failed.",
                    "Provide a refactored code snippet demonstrating proper asynchronous flow control with async/await and correct middleware error propagation.",
                    "Diagnose potential race conditions or state mutation hazards in the component lifecycle and implement defensive immutability patterns.",
                    "Recommend automated linting rules, static analysis checks, and unit test harnesses to catch this class of bug during CI/CD builds.",
                ],
            },
            {
                "name": "Full-Stack State Management and Data Binding",
                "question_type": "apply",
                "response_format": "state_architecture",
                "source_year": 2023,
                "scenarios": [
                    "A collaborative online spreadsheet application synchronizes cell edits across dozens of simultaneous browser clients.",
                    "An e-commerce checkout wizard requires persistent state sharing across multi-step shipping, billing, and review screens.",
                    "A real-time cryptocurrency trading platform updates high-frequency order books, candlestick charts, and user wallet balances.",
                    "A project task board application synchronizes drag-and-drop card movements with optimistic UI updates and server rollback.",
                    "A multi-tenant SaaS dashboard allows users to switch active organizations and role permissions dynamically across all app views.",
                ],
                "tasks": [
                    "Design a centralized state management architecture distinguishing between server cache, global client state, and local component state.",
                    "Evaluate the trade-offs between unidirectional data flow (Redux/Zustand) and two-way reactive data binding for this specific UI workload.",
                    "Implement an optimistic UI update strategy with rollback handling to provide instantaneous feedback while ensuring backend consistency.",
                    "Formulate a state rehydration and persistence mechanism using browser storage while securing sensitive session tokens against XSS.",
                ],
            },
            {
                "name": "Authentication and Security Middleware",
                "question_type": "analyze",
                "response_format": "security_implementation",
                "source_year": 2023,
                "scenarios": [
                    "A corporate employee intranet must support single sign-on (SSO) via OAuth2 and OpenID Connect with role-based access control.",
                    "A public API gateway experiences credential stuffing and brute-force attacks against its login and password reset endpoints.",
                    "A fintech mobile app backend implements refresh token rotation to mitigate token theft across untrusted public Wi-Fi networks.",
                    "A cloud storage sharing service needs granular resource authorization to prevent Insecure Direct Object Reference (IDOR) vulnerabilities.",
                    "A microservices application must validate user claims across service boundaries without querying the central user database on every hop.",
                ],
                "tasks": [
                    "Analyze the security vulnerabilities of storing JWT tokens in localStorage versus HttpOnly, Secure, SameSite cookies in modern browsers.",
                    "Construct an Express authorization middleware enforcing fine-grained Role-Based Access Control (RBAC) and object ownership validation.",
                    "Design an IP-aware sliding window rate-limiting middleware using Redis to protect public endpoints from distributed brute-force traffic.",
                    "Formulate a cryptographic token refresh and revocation architecture that balances stateless verification speed with instantaneous revocation.",
                ],
            },
            {
                "name": "Asynchronous Operations and Event-Driven Services",
                "question_type": "evaluate",
                "response_format": "architecture_tradeoff",
                "source_year": 2023,
                "scenarios": [
                    "A video sharing platform must process multi-gigabyte video uploads, transcoder pipelines, thumbnail generation, and user notifications.",
                    "An online ticketing platform must process reservation expirations and release unpaid tickets back to inventory after a ten-minute window.",
                    "An e-commerce notifications service dispatches emails, SMS alerts, and push messages asynchronously without delaying checkout responses.",
                    "A banking statement generator aggregates monthly transactions across multiple external databases and compiles encrypted PDF downloads.",
                    "An IoT fleet tracking platform ingests continuous GPS pings and publishes real-time location feeds to client dashboards via WebSockets.",
                ],
                "tasks": [
                    "Evaluate synchronous HTTP request-response versus asynchronous message broker (RabbitMQ/BullMQ) architectures for this workload.",
                    "Design a fault-tolerant background worker pipeline with exponential backoff, dead-letter queues, and idempotent job processing.",
                    "Analyze event-loop blocking hazards in Node.js when processing CPU-intensive tasks and propose worker threads or child process isolation.",
                    "Construct a WebSocket connection management and heartbeat architecture that gracefully handles client reconnections and session state recovery.",
                ],
            },
        ],
    },
    {
        "module_key": "distributed_systems",
        "topics": [
            {
                "name": "Distributed Communication",
                "question_type": "evaluate",
                "response_format": "technology_comparison",
                "source_year": 2023,
                "scenarios": [
                    "A fleet tracking system receives periodic telemetry coordinates from thousands of delivery trucks with intermittent mobile connectivity.",
                    "An automated high-frequency trading platform exchanges market order quotes between institutional exchange matching engines.",
                    "A microservice e-commerce backend coordinates order checkout, inventory reservation, and payment processing across internal networks.",
                    "A smart-home controller sends low-latency commands to battery-constrained environmental sensors and smart locks.",
                    "A healthcare platform distributes patient laboratory alert notifications to attending physicians' mobile devices in real time.",
                ],
                "tasks": [
                    "Compare synchronous Remote Procedure Calls (gRPC) against asynchronous publish-subscribe messaging (Kafka/RabbitMQ) for this scenario.",
                    "Evaluate message serialization formats (Protocol Buffers, JSON, Avro) regarding payload footprint, schema evolution, and CPU overhead.",
                    "Analyze the implications of network latency, packet loss, and connection timeouts on communication semantics (at-least-once, at-most-once).",
                    "Design an idempotency mechanism ensuring that duplicate message deliveries caused by transport retries do not corrupt application state.",
                ],
            },
            {
                "name": "Dependability and Fault Tolerance",
                "question_type": "apply",
                "response_format": "calculation_and_explanation",
                "source_year": 2023,
                "scenarios": [
                    "A cloud banking platform requires 99.999% annual availability across three independent geographic availability zones.",
                    "A telecommunications billing cluster utilizes primary-backup replication where heartbeats detect server node crashes.",
                    "A distributed storage cluster stores customer files across ten commodity storage nodes with expected individual failure rates.",
                    "A distributed payment gateway experiences cascading failures when an external fraud detection service experiences network latency.",
                    "An air-traffic control telemetry system requires triple-modular redundancy (TMR) to detect and mask Byzantine hardware faults.",
                ],
                "tasks": [
                    "Calculate system availability from component Mean Time Between Failures (MTBF) and Mean Time To Repair (MTTR) for serial and parallel setups.",
                    "Design a Circuit Breaker pattern with health checks and fallbacks to prevent cascading failures across downstream microservices.",
                    "Explain how primary-backup replication achieves fault tolerance, detailing the failover procedure and split-brain prevention mechanisms.",
                    "Evaluate checkpointing and message logging recovery protocols (coordinated checkpointing vs independent checkpointing with domino effect).",
                ],
            },
            {
                "name": "Service Discovery and Load Balancing",
                "question_type": "analyze",
                "response_format": "architecture_analysis",
                "source_year": 2023,
                "scenarios": [
                    "A containerized microservices application scales dynamically from five to one hundred instances during promotional marketing campaigns.",
                    "A global content delivery network distributes web traffic across edge servers in North America, Europe, and Asia-Pacific.",
                    "A database read-replica pool balances analytical query workloads while excluding replicas experiencing replication lag.",
                    "An internal corporate API gateway routes requests to multiple versions of backend microservices during canary deployments.",
                    "A streaming media platform distributes real-time video encoding jobs across heterogeneous GPU worker nodes.",
                ],
                "tasks": [
                    "Compare client-side service discovery (e.g., Netflix Eureka) versus server-side service discovery (e.g., Kubernetes DNS/Envoy) for this system.",
                    "Analyze load balancing algorithms (Round Robin, Least Connections, Consistent Hashing) and justify the optimal choice for this traffic profile.",
                    "Design a health-checking mechanism that detects partial service degradation (e.g., memory thrashing) beyond basic TCP port liveness.",
                    "Explain how Consistent Hashing minimizes cache disruption and data migration when cache cluster nodes are added or removed dynamically.",
                ],
            },
            {
                "name": "Distributed Consensus and Replication",
                "question_type": "evaluate",
                "response_format": "consensus_protocol",
                "source_year": 2023,
                "scenarios": [
                    "A distributed key-value store coordinates leader election and log replication across five nodes despite periodic network partitions.",
                    "A multi-datacenter database replicates financial balances across continents while complying with local data residency laws.",
                    "A distributed lock manager coordinates mutual exclusion for shared file modifications among concurrent worker nodes.",
                    "A blockchain network validates transaction blocks among untrusted nodes in the presence of malicious Byzantine actors.",
                    "A configuration management service maintains authoritative cluster configuration state that must remain consistent across all nodes.",
                ],
                "tasks": [
                    "Evaluate the Raft consensus algorithm phases (leader election, log replication, safety invariants) during a temporary network partition.",
                    "Analyze the CAP theorem trade-offs (Consistency vs Availability) for this system when a network partition disconnects two datacenters.",
                    "Explain quorum consensus rules (N, R, W) and determine parameter settings that guarantee strong consistency (R + W > N) versus low latency.",
                    "Contrast Paxos/Raft crash-fault-tolerant consensus against Byzantine Fault Tolerant (PBFT) consensus in terms of node count and message complexity.",
                ],
            },
            {
                "name": "Distributed Caching and Data Partitioning",
                "question_type": "design",
                "response_format": "caching_strategy",
                "source_year": 2023,
                "scenarios": [
                    "A news portal experiences massive read spikes on breaking news articles that threaten to overwhelm the backend database.",
                    "A social media platform stores user friendship graphs and timeline feeds requiring horizontal sharding across hundreds of nodes.",
                    "An online gaming platform caches player inventory and current session state with strict real-time response requirements.",
                    "A global e-commerce platform caches localized product pricing and currency conversions across multiple edge nodes.",
                    "A healthcare record system shards patient data by geographic jurisdiction while supporting cross-region specialist consultations.",
                ],
                "tasks": [
                    "Design a caching strategy (Cache-Aside, Write-Through, Write-Behind) and evaluate cache invalidation and cache stampede prevention.",
                    "Select an appropriate data partitioning key (range-based vs hash-based) to ensure uniform data distribution and avoid hotspotting.",
                    "Formulate an eviction policy (LRU, LFU, TTL) and analyze memory sizing requirements to maintain a target cache hit ratio above ninety percent.",
                    "Evaluate cross-partition query execution strategies when aggregations or joins span multiple distributed database shards.",
                ],
            },
        ],
    },
    {
        "module_key": "software_architecture",
        "topics": [
            {
                "name": "Architectural Styles and Trade-offs",
                "question_type": "evaluate",
                "response_format": "architecture_justification",
                "source_year": 2025,
                "scenarios": [
                    "A legacy monolith insurance claims application must modernize to support rapid feature rollout by five autonomous product teams.",
                    "A smart city traffic monitoring platform ingests high-volume sensor streams, generates instant alerts, and stores historical trends.",
                    "A banking institution builds an open-banking API platform integrating legacy mainframes, cloud fintech services, and mobile banking.",
                    "A computer-aided engineering simulation platform requires computationally intensive distributed mathematical modeling.",
                    "An enterprise resource planning platform serves diverse multinational subsidiaries with unique localized tax and workflow rules.",
                ],
                "tasks": [
                    "Evaluate Layered, Microservices, and Event-Driven architectural styles against the system's key quality attribute requirements.",
                    "Analyze the architectural trade-offs between monolithic simplicity and microservice operational complexity for this organization's size.",
                    "Justify the selection of Hexagonal (Ports and Adapters) architecture to decouple core business logic from external frameworks and databases.",
                    "Examine how Conway's Law influences the alignment between software architecture boundaries and organizational team communication structures.",
                ],
            },
            {
                "name": "Architecture Modeling",
                "question_type": "design",
                "response_format": "architecture_diagram",
                "source_year": 2025,
                "scenarios": [
                    "A digital health platform integrates patient mobile apps, hospital EHR systems, laboratory cloud services, and pharmacy APIs.",
                    "An online travel booking marketplace connects flight aggregators, hotel inventory, car rentals, and multi-currency payment providers.",
                    "A national tax administration platform processes tax filings, automated fraud detection, taxpayer notifications, and bank refunds.",
                    "A smart grid energy utility platform manages smart-meter ingestion, demand-response pricing, outage detection, and field worker dispatch.",
                    "An autonomous warehouse robotics platform coordinates fleet routing, inventory bin picking, safety monitoring, and ERP synchronization.",
                ],
                "tasks": [
                    "Design a C4 model Container diagram detailing major software containers, data stores, communication protocols, and technology choices.",
                    "Construct a C4 Component diagram for the most critical backend container, illustrating internal component interfaces and dependencies.",
                    "Design a Deployment diagram illustrating physical/virtual node infrastructure, network zones (DMZ, private subnet), and load balancers.",
                    "Evaluate the architecture model using Kruchten's 4+1 View Model, explaining how the logical, process, and physical views address stakeholder concerns.",
                ],
            },
            {
                "name": "Quality Attribute Scenarios and Tactics",
                "question_type": "analyze",
                "response_format": "tactic_tradeoff",
                "source_year": 2025,
                "scenarios": [
                    "A commercial banking platform must achieve sub-second transaction response times while sustaining five-thousand concurrent operations.",
                    "A military defense communications system must detect and resist cyber intrusion attacks while maintaining operational message delivery.",
                    "A medical monitoring platform must guarantee 99.999% availability and fail over to backup power and nodes within five seconds of hardware faults.",
                    "A consumer electronics firmware codebase must be adapted easily to support twelve new hardware peripheral sensors over two years.",
                    "A large enterprise SaaS platform must scale horizontally to handle unexpected ten-fold traffic spikes during black-friday sales.",
                ],
                "tasks": [
                    "Formulate a formal Quality Attribute Scenario specifying stimulus, source of stimulus, environment, artifact, response, and response measure.",
                    "Identify and analyze architectural tactics (e.g., manage queue size, reduce computational overhead, introduce concurrency) to fulfill the scenario.",
                    "Examine the conflicting trade-offs between the proposed architectural tactics (e.g., security encryption overhead versus performance latency).",
                    "Develop an Architecture Decision Record (ADR) documenting context, considered alternatives, chosen tactics, and resulting trade-off consequences.",
                ],
            },
            {
                "name": "Architecture Evaluation and Review Methods",
                "question_type": "evaluate",
                "response_format": "atam_evaluation",
                "source_year": 2025,
                "scenarios": [
                    "An architectural review board evaluates the proposed cloud modernization architecture for a national air traffic management system.",
                    "A fintech startup conducts an architecture audit prior to a venture capital funding round to identify scalability bottlenecks.",
                    "A public health authority reviews an infectious disease surveillance platform architecture against national data privacy mandates.",
                    "A retail conglomerate evaluates two competing architecture proposals for its global omnichannel supply-chain platform.",
                    "An automotive manufacturer audits the embedded vehicle software architecture against ISO 26262 functional safety standards.",
                ],
                "tasks": [
                    "Apply the Architecture Tradeoff Analysis Method (ATAM) phases to evaluate whether the proposed architecture satisfies utility tree requirements.",
                    "Identify architectural Sensitivity Points and Tradeoff Points, explaining how variations in key architectural decisions impact quality goals.",
                    "Formulate an Architecture Risk and Non-Risk assessment report categorizing structural vulnerabilities and recommending mitigations.",
                    "Design an Architecture Evaluation Utility Tree categorizing quality attributes into specific, prioritized, and measurable scenarios.",
                ],
            },
            {
                "name": "Microservice Decomposition and Domain-Driven Boundaries",
                "question_type": "design",
                "response_format": "service_decomposition",
                "source_year": 2025,
                "scenarios": [
                    "A global logistics and courier enterprise breaks down its legacy operations system into autonomous bounded microservices.",
                    "A university campus management platform decomposes admissions, course scheduling, billing, student housing, and alumni relations.",
                    "An online streaming and digital merchandising platform separates user subscriptions, media catalogs, playback streaming, and physical merchandise.",
                    "A multi-hospital network decomposes clinical patient care, laboratory test processing, surgical theatre scheduling, and billing.",
                    "An online marketplace decomposes seller onboarding, product catalog, buyer checkout, fraud prevention, and customer support.",
                ],
                "tasks": [
                    "Apply Domain-Driven Design (DDD) strategic design principles to identify Core, Supporting, and Generic subdomains and define Bounded Contexts.",
                    "Construct a Context Map depicting the relationship patterns (Shared Kernel, Customer-Supplier, Anti-Corruption Layer) between bounded contexts.",
                    "Design a distributed data management approach for a business transaction spanning multiple microservices using the Saga Pattern (orchestration vs choreography).",
                    "Analyze potential pitfalls of microservice decomposition, such as distributed transactions, chatty cross-service calls, and shared database anti-patterns.",
                ],
            },
        ],
    },
    {
        "module_key": "software_engineering_process_quality_management",
        "topics": [
            {
                "name": "Specification-Based Testing",
                "question_type": "apply",
                "response_format": "test_case_table",
                "source_year": 2024,
                "scenarios": [
                    "An online vehicle insurance quote calculator determines premium discounts based on driver age, annual mileage, and clean driving years.",
                    "A bank automated loan qualification system evaluates applicant monthly salary, credit score tiers, existing debt ratio, and loan tenure.",
                    "An airline loyalty rewards program awards frequent flyer tier status based on qualifying flight sectors, elite miles, and ticket spending bands.",
                    "An e-commerce parcel shipping calculator calculates freight costs using dimensional weight, postal zone distances, and express delivery options.",
                    "A university honors degree classification system computes final degree awards using weighted grade point averages, credit counts, and resit rules.",
                ],
                "tasks": [
                    "Apply Equivalence Partitioning (EP) to identify valid and invalid equivalence classes for all input variables, presenting a structured partition table.",
                    "Apply Boundary Value Analysis (BVA) to determine robust boundary test values (min, min+, nominal, max-, max, and out-of-range values).",
                    "Construct a comprehensive Decision Table covering all combinations of business rule conditions and specify the expected system actions.",
                    "Derive a prioritized test case suite from the equivalence classes and decision table, specifying inputs, preconditions, and expected outputs.",
                ],
            },
            {
                "name": "Code-Based Testing",
                "question_type": "analyze",
                "response_format": "control_flow_analysis",
                "source_year": 2024,
                "scenarios": [
                    "A Java method validates user credit card numbers using the Luhn algorithm with multiple nested loops, conditions, and format checks.",
                    "A payroll deduction function computes tax withholding brackets, pension contributions, and insurance levies through chained conditional statements.",
                    "A flight booking seat allocation algorithm evaluates passenger seat preferences, travel class availability, and emergency exit row constraints.",
                    "An account security throttling method inspects IP addresses, failed login counts, account lockout states, and CAPTCHA challenge requirements.",
                    "A warehouse picking optimization routine calculates optimal travel paths through warehouse aisles using nested decision branches.",
                ],
                "tasks": [
                    "Construct a Control Flow Graph (CFG) from the described logic, identifying all basic blocks, decision nodes, and directed edges.",
                    "Calculate McCabe's Cyclomatic Complexity using graph theory formulas and derive a minimal set of independent test paths for basis path testing.",
                    "Compare Statement Coverage, Branch/Decision Coverage, and Modified Condition/Decision Coverage (MC/DC) requirements for this algorithm.",
                    "Formulate input data sets that achieve 100% branch coverage and identify any unreachable code or potential off-by-one execution loops.",
                ],
            },
            {
                "name": "Software Quality Metrics and Defect Tracking",
                "question_type": "analyze",
                "response_format": "quality_metrics",
                "source_year": 2024,
                "scenarios": [
                    "A software development organization reviews defect tracking telemetry across three successive enterprise ERP sprint releases.",
                    "A mission-critical medical infusion pump software codebase undergoes static analysis to measure code quality and technical debt.",
                    "A cloud SaaS engineering team evaluates defect arrival rates, mean time to detect (MTTD), and mean time to resolve (MTTR) post-deployment.",
                    "A mobile banking app team tracks test execution progress, defect density per KLOC, and defect leakage into production releases.",
                    "An automotive software engineering unit measures maintainability index, code churn, and test coverage across legacy embedded C modules.",
                ],
                "tasks": [
                    "Analyze defect density, defect removal efficiency (DRE), and defect phase containment metrics to evaluate the effectiveness of QA gates.",
                    "Interpret static analysis metrics (Chidamber-Kemerer OO metrics, Halstead complexity, Maintainability Index) to identify high-risk modules.",
                    "Construct an orthogonal defect classification (ODC) report categorizing defects by trigger, impact, and defect type to guide process remediation.",
                    "Formulate a quality dashboard with defined threshold alerts that prevent automated deployment when defect density or test coverage degrades.",
                ],
            },
            {
                "name": "Software Process Models and Agile Quality Assurance",
                "question_type": "evaluate",
                "response_format": "process_improvement",
                "source_year": 2024,
                "scenarios": [
                    "A government contractor accustomed to traditional V-Model lifecycle delivery is required to adopt Scrum while retaining safety audits.",
                    "A medical software startup must align continuous integration/continuous delivery (CI/CD) pipelines with FDA Software as a Medical Device (SaMD) rules.",
                    "A fast-growing fintech company suffers from frequent production regressions due to lacking automated test pyramids and informal manual testing.",
                    "An enterprise IT division aims to advance its process maturity from CMMI Level 2 (Managed) to CMMI Level 3 (Defined).",
                    "A digital agency balances rapid time-to-market demands against technical debt and long-term maintainability across client projects.",
                ],
                "tasks": [
                    "Evaluate the adaptation of the V-Model versus Agile/DevOps practices for this safety-critical domain, justifying how quality assurance is preserved.",
                    "Design a test automation pyramid strategy (unit, integration, end-to-end, exploratory) detailing appropriate test ratios and execution triggers.",
                    "Formulate a software process improvement plan addressing root causes of escape defects using the Shewhart-Deming cycle (PDCA).",
                    "Analyze how Continuous Integration and automated quality gates (linters, security scans, unit tests) reinforce shift-left quality practices.",
                ],
            },
            {
                "name": "Integration and System Test Strategy",
                "question_type": "design",
                "response_format": "test_strategy",
                "source_year": 2024,
                "scenarios": [
                    "An omnichannel e-commerce platform integrates storefront web apps, mobile apps, third-party payment gateways, and warehouse ERP systems.",
                    "A connected vehicle platform integrates in-vehicle telematics hardware, mobile driver apps, cloud data lakes, and roadside emergency dispatch.",
                    "A smart hospital integrates bedside patient monitors, nursing station dashboards, central electronic health records, and laboratory diagnostic tools.",
                    "A global airline reservation platform integrates flight schedule engines, global distribution systems (GDS), passenger booking, and baggage tracking.",
                    "A financial trading clearinghouse integrates multi-broker trade order inputs, risk validation engines, clearing ledgers, and central bank settlement.",
                ],
                "tasks": [
                    "Formulate an Integration Test Strategy comparing Big Bang, Top-Down, Bottom-Up, and Sandwich (Hybrid) integration approaches for these components.",
                    "Design mock objects, stubs, and service virtualization fixtures to isolate subsystems during asynchronous integration testing.",
                    "Develop a non-functional system test suite encompassing performance stress testing, failover resilience, security vulnerability scans, and soak testing.",
                    "Construct an End-to-End Test Matrix defining critical business transaction paths, integration interface checkpoints, and regression verification criteria.",
                ],
            },
        ],
    },
]


def build():
    bank = {
        "schema_version": "1.0",
        "bank_id": "c2_m16_expanded_synthetic_content_bank_v1",
        "dataset_type": "synthetic_question_specifications",
        "verification_status": "unverified",
        "academic_review_status": "pending",
        "generation_mode": "development_fixture",
        "modules": M16_MODULES,
    }

    # Validate using the existing SyntheticContentBank validation rules
    SyntheticContentBank.validate(bank)

    OUTPUT_FILE.write_text(
        json.dumps(bank, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Successfully generated and validated {OUTPUT_FILE}")
    print(f"Modules: {len(bank['modules'])}")
    total_scenarios = sum(
        len(t["scenarios"])
        for m in bank["modules"]
        for t in m["topics"]
    )
    total_tasks = sum(
        len(t["tasks"])
        for m in bank["modules"]
        for t in m["topics"]
    )
    total_pairs = sum(
        len(t["scenarios"]) * len(t["tasks"])
        for m in bank["modules"]
        for t in m["topics"]
    )
    print(f"Total topics: {sum(len(m['topics']) for m in bank['modules'])}")
    print(f"Total scenarios: {total_scenarios}")
    print(f"Total tasks: {total_tasks}")
    print(f"Total possible questions: {total_pairs} (8 modules x 100 questions = 800)")


if __name__ == "__main__":
    build()
