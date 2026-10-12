import { S, M, D } from './helpers.js';
export default {
  semester: 'Y3S2',
  module_code: 'SEPQM',
  module_name: 'Software Engineering Process and Quality Management',
  topics: {
    qm_testing_basics: {
      label: 'Software Testing Basics and Specification-Based Test Design',
      lectures: 'L01-L02',
      practice: [
        S(
          'In the definitions of software quality, which one is the customer view?',
          ['Conformance to requirements', 'Fit for use', 'Zero defects at release', 'The lowest cost of testing'],
          1,
          "Juran and Deming say quality is fit for use, which is the customer view. Crosby's conformance to requirements is the producer view.",
          'concept'
        ),
        S(
          'Which statement describes validation?',
          [
            'It checks that the software meets the user needs',
            'It checks that the software meets the written requirements',
            'It checks that the test plan strategy is complete',
            'It checks that every reported defect has been fixed',
          ],
          0,
          'Validation checks that the software meets user needs. Verification checks it against the requirements. Students often swap the two.',
          'compare'
        ),
        S(
          'All 200 test cases passed. What does the principle "testing shows presence of defects, not absence" tell us?',
          [
            'The software has no defects left',
            'Testing is finished and can stop',
            'The software may still hide defects',
            'The test cases were all too easy',
          ],
          2,
          'Passing tests cannot prove that no defects remain. Testing can only show that defects exist.',
          'scenario'
        ),
        S(
          'A system accepts ages 18 to 60. Which set has one value from each equivalence partition?',
          ['18, 40, 60', '15, 17, 19', '30, 45, 55', '10, 30, 70'],
          3,
          'The partitions are below 18, 18 to 60, and above 60. Only 10, 30 and 70 give one value from each. The other sets miss at least one partition.',
          'concept'
        ),
        S(
          'A gym accepts ages 16 to 60. Which set is the full set of boundary value analysis test values?',
          ['16, 17, 59, 60', '15, 16, 17, 59, 60, 61', '15, 16, 60, 61', '5, 30, 65'],
          1,
          'For each boundary we test the exact value, one less and one more: 15, 16, 17 and 59, 60, 61. The values 5, 30 and 65 come from equivalence partitioning.',
          'calc'
        ),
        S(
          'A decision table has two conditions, and each can be True or False. How many rules are needed to cover all combinations?',
          ['2', '3', '4', '8'],
          2,
          'Two conditions with two values each give 2 x 2 = 4 combinations. Each combination is one rule.',
          'calc'
        ),
        M(
          'A gym accepts ages 16 to 60. Which of these boundary test values are valid and should be accepted?',
          ['15', '16', '17', '61'],
          [1, 2],
          'Ages 16 and 17 are inside the valid range. Ages 15 and 61 are invalid boundary values and should be rejected.',
          'multi'
        ),
        M(
          'Which are drawbacks of equivalence partitioning?',
          [
            'The result depends on correct partitioning',
            'The tester must read the source code first',
            'It gives no insight into the code inside',
            'It is limited to what the requirements state',
          ],
          [0, 2, 3],
          'Equivalence partitioning is a black box method. It relies on good partitions and stated requirements, and it does not look at the code.',
          'multi'
        ),
        M(
          'Which statements about boundary value analysis are true?',
          [
            'It extends equivalence partitioning',
            'It works well on unordered text categories',
            'It tests the minimum and maximum of a partition',
            'It handles rules with many inputs very well',
          ],
          [0, 2],
          'Boundary value analysis needs ordered data such as numbers. It cannot handle decisions that depend on more than one input.',
          'multi'
        ),
        M(
          'Which of these are testing principles?',
          [
            'Early testing saves time and cost',
            'Testing can prove that no defects remain',
            'Exhaustive testing is impossible',
            'Defects tend to cluster in some areas',
          ],
          [0, 2, 3],
          'Early testing, impossible exhaustive testing and defect clustering are listed principles. Testing cannot prove that software is defect free.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'What does specification-based (black box) testing focus on?',
          [
            'How the code is written inside',
            'Which code lines are executed',
            'How fast the team writes code',
            'What the system should do',
          ],
          3,
          'Specification-based testing uses the requirements to check what the system should do, not how it is built inside.',
          'concept'
        ),
        D(
          'A membership form must not accept both a total amount and a number of months. What should happen when the user enters neither field?',
          [
            'The system calculates the months',
            'The system calculates the total cost',
            'The system shows an error message',
            'The system calculates both values',
          ],
          2,
          'With no input, no calculation is possible. The decision table assumes an error message for this combination.',
          'scenario'
        ),
        D(
          'An order box accepts 1 to 10 pizzas. Which set is the boundary value analysis test set?',
          ['0, 1, 2, 9, 10, 11', '1, 5, 10', '0, 1, 10, 11', '-1, 5, 15'],
          0,
          'Test the exact boundary, one below and one above each end: 0, 1, 2 and 9, 10, 11. The set -1, 5, 15 is from equivalence partitioning.',
          'calc'
        ),
      ],
    },

    qm_functional_nonfunctional: {
      label: 'Functional and Non-Functional Testing',
      lectures: 'L03',
      practice: [
        S(
          'Which of these is a type of functional testing?',
          ['Smoke testing', 'Load testing', 'Usability testing', 'Localization testing'],
          0,
          'Unit, smoke, regression, sanity, system and user acceptance testing are functional types. Load, usability and localization testing are non-functional.',
          'concept'
        ),
        S(
          'Which test is usually non-scripted and is done after a build with minor changes?',
          ['Smoke testing', 'Regression testing', 'System testing', 'Sanity testing'],
          3,
          'Sanity testing checks that the planned functionality works after a small change and is usually non-scripted. It is a subset of regression testing.',
          'compare'
        ),
        S(
          'A new overtime rule is added. The team re-runs earlier scripted tests on all subsystems to confirm nothing broke. Which test is this?',
          ['Smoke testing', 'Regression testing', 'Unit testing', 'Sanity testing'],
          1,
          'Regression testing re-runs the original test scenarios to make sure a change did not break existing functions.',
          'scenario'
        ),
        S(
          'Which test pushes a system beyond normal or peak load to see how it recovers?',
          ['Load testing', 'Endurance testing', 'Stress testing', 'Volume testing'],
          2,
          'Stress testing checks stability when resources are insufficient and how the system recovers. Load testing keeps raising the load until a time threshold is reached.',
          'compare'
        ),
        S(
          'A ticket website suddenly gets a very large number of users when sales open. Which test checks this case?',
          ['Volume testing', 'Scalability testing', 'Endurance testing', 'Spike testing'],
          3,
          'Spike testing suddenly raises the number of users by a very large amount to see if the system can sustain it.',
          'scenario'
        ),
        S(
          'Which test verifies the application with newer, upcoming versions?',
          [
            'Backward compatibility testing',
            'Forward compatibility testing',
            'Localization testing',
            'Usability testing',
          ],
          1,
          'Forward compatibility checks newer versions. Backward compatibility checks older versions.',
          'compare'
        ),
        M(
          'Which of these are types of functional testing?',
          ['Unit testing', 'Endurance testing', 'Regression testing', 'Volume testing'],
          [0, 2],
          'Unit and regression testing are functional types. Endurance and volume testing are types of performance testing.',
          'multi'
        ),
        M(
          'Which of these are types of performance testing?',
          ['Load testing', 'Spike testing', 'Endurance testing', 'Smoke testing'],
          [0, 1, 2],
          'Load, spike and endurance testing are performance types. Smoke testing is a functional test of the core features.',
          'multi'
        ),
        M(
          'Which are uses of performance testing?',
          [
            'Find bottlenecks such as database setup',
            'Replace all functional testing',
            'Gather metrics for tuning the system',
            'Write the user requirements',
          ],
          [0, 2],
          'Performance testing finds bottlenecks, gives tuning metrics and shows if a release is ready. It does not replace functional testing.',
          'multi'
        ),
        M(
          'Which statements about user acceptance testing are true?',
          [
            'It is usually done by the customer or end user',
            'It is done only by the unit developers',
            'It compares the program with current user needs',
            'It is done before any code is written',
          ],
          [0, 2],
          'User acceptance testing compares the program with the initial requirements and the current needs of end users, usually by the customer.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'What does unit testing check?',
          [
            'The entire system against its objectives',
            'Individual subprograms, classes or procedures',
            'Only the login and the main modules',
            'The system under very heavy load',
          ],
          1,
          'Unit testing checks the smallest parts, such as subprograms and classes, and it makes debugging easier.',
          'concept'
        ),
        D(
          'A server is run with the expected load for several days to look for memory leaks. Which test is this?',
          ['Endurance testing', 'Spike testing', 'Scalability testing', 'Volume testing'],
          0,
          'Endurance testing uses an expected load over a long time and looks for problems such as memory leaks.',
          'scenario'
        ),
        D(
          'Which statement about regression testing is NOT correct?',
          [
            'It re-runs scenarios that were scripted earlier',
            'It checks that a change has not broken old features',
            'It usually needs an automated testing tool',
            'It is non-scripted and done only once',
          ],
          3,
          'Regression testing re-runs scripted tests and normally uses automation. Non-scripted checks describe sanity testing.',
          'not'
        ),
      ],
    },

    qm_coverage_complexity: {
      label: 'Code Coverage and Cyclomatic Complexity',
      lectures: 'L04a-L04b',
      practice: [
        S(
          'What does statement coverage ensure?',
          [
            'Every true and false outcome is tested',
            'Every path from start to end is run',
            'Every statement runs at least once',
            'Every combination of conditions is tested',
          ],
          2,
          'Statement coverage checks that each statement is executed at least once. It is a white box method.',
          'concept'
        ),
        S(
          'A program has 8 statements. The tests execute 6 of them. What is the statement coverage?',
          ['75%', '60%', '80%', '86%'],
          0,
          'Statement coverage = executed statements / total statements x 100 = 6 / 8 x 100 = 75%.',
          'calc'
        ),
        S(
          'A program has 6 decision outcomes. The tests exercise 4 of them. What is the decision coverage, rounded?',
          ['50%', '60%', '75%', '67%'],
          3,
          'Decision coverage = outcomes exercised / total outcomes x 100 = 4 / 6 x 100, which is about 67%.',
          'calc'
        ),
        S(
          'A control flow graph has 9 edges and 7 nodes. What is the cyclomatic complexity V(G) = e - n + 2?',
          ['3', '4', '5', '6'],
          1,
          'V(G) = 9 - 7 + 2 = 4. A common mistake is to forget the + 2.',
          'calc'
        ),
        S(
          'A decision has 3 conditions. How many test cases give full multiple condition coverage?',
          ['6', '3', '8', '9'],
          2,
          'Multiple condition coverage needs 2 to the power n tests. For n = 3 this is 8.',
          'calc'
        ),
        S(
          'A method is: if (a) print x; else { if (b) print y; else print z; }. What is V(G) using d + 1?',
          ['2', '3', '4', '5'],
          1,
          'There are 2 decisions, so V(G) = 2 + 1 = 3. The else part is not a separate decision.',
          'calc'
        ),
        M(
          'Which statements about cyclomatic complexity are true?',
          [
            'It measures the number of linearly independent paths',
            'It counts the lines of code in a method',
            'It can be found as e - n + 2',
            'It can be found as d + 1 (d = decision nodes)',
          ],
          [0, 2, 3],
          'Cyclomatic complexity counts independent paths. It uses e - n + 2, or d + 1 for decision nodes, and not lines of code.',
          'multi'
        ),
        M(
          'Which statements about condition coverage and multiple condition coverage are true?',
          [
            'Condition coverage tests each sub-expression as True and False',
            'Multiple condition coverage needs 2 to the power n tests',
            'Condition coverage tests every combination of conditions',
            'Multiple condition coverage needs only 2 tests',
          ],
          [0, 1],
          'Condition coverage does not check all combinations. Multiple condition coverage does, so it needs 2 to the power n tests.',
          'multi'
        ),
        M(
          'Which rules for drawing a control flow graph are correct?',
          [
            'Edges must show direction',
            'A procedure node holds only decision statements',
            'Start, stop and decision nodes are labeled',
            'A procedure node can hold several non-decision statements',
          ],
          [0, 2, 3],
          'A procedure node holds one or more non-decisional statements. Decisions have their own nodes.',
          'multi'
        ),
        M(
          'Which are true about code coverage analysis?',
          [
            'It gives a quantitative measurement',
            'It proves the program has no bugs',
            'It shows the degree to which code was tested',
            'It helps find code that tests do not cover',
          ],
          [0, 2, 3],
          'Coverage analysis measures how much code is tested and shows what is missed. It cannot prove that no bugs exist.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'A function has 3 linearly independent paths. The tests execute 2 of them. What is the path coverage, rounded?',
          ['33%', '50%', '67%', '100%'],
          2,
          'Path coverage = paths executed / total paths x 100 = 2 / 3 x 100, which is about 67%.',
          'calc'
        ),
        D(
          'A graph has d decision nodes and p procedure nodes. With e = 2d + p and n = d + p + 1, what is V(G)?',
          ['d + 1', 'd + p', '2d + 1', 'p + 1'],
          0,
          'V(G) = (2d + p) - (d + p + 1) + 2 = d + 1. The procedure nodes cancel out.',
          'calc'
        ),
        D(
          'Code: if (a > 5) a = a * 3. The tests use only a = 2. What is the decision coverage?',
          ['25%', '50%', '75%', '100%'],
          1,
          'There are 2 decision outcomes (True and False). With a = 2 only the False outcome is tested, so 1 / 2 = 50%.',
          'calc'
        ),
      ],
    },

    qm_size_complexity_metrics: {
      label: 'Cognitive Functional Size and Weighted Composite Complexity',
      lectures: 'L05, L07, L07g',
      practice: [
        S(
          'Cognitive functional size (CFS) depends on which three factors?',
          [
            'Cognitive weights of control structures, inputs and outputs',
            'Lines of code, tokens and nesting level',
            'Decision nodes, edges and nodes',
            'Classes, methods and inheritance level',
          ],
          0,
          'CFS is a function of the cognitive weights of basic control structures, the number of inputs and the number of outputs.',
          'concept'
        ),
        S(
          'Which basic control structure runs a code block again and again until a condition is met?',
          ['Sequence structure', 'Branch structure', 'Recursive structure', 'Iterative structure'],
          3,
          'The three basic control structures are sequence, branch and iterative. A for loop is iterative.',
          'concept'
        ),
        S(
          'A method has Ni = 3 inputs, No = 2 outputs and total cognitive weight Wc = 4. What is its cognitive functional size Sf?',
          ['9', '14', '20', '24'],
          2,
          'Sf is the product of (Ni + No) and Wc: (3 + 2) x 4 = 20. Adding the values instead of multiplying is the common mistake.',
          'calc'
        ),
        S(
          'Which is NOT one of the four key factors behind weighted composite complexity (WCC)?',
          [
            'Size of a statement',
            'Number of outputs',
            'Nesting level of control structures',
            'Inheritance level of statements',
          ],
          1,
          'WCC uses size, type of control structure, nesting level and inheritance level. Inputs and outputs belong to CFS.',
          'not'
        ),
        S(
          'A statement has size S = 4, Wc = 1, Wn = 2 and Wi = 1. What is its weighted complexity WC?',
          ['16', '8', '12', '7'],
          0,
          'Total weight Wt = 1 + 2 + 1 = 4. WC = S x Wt = 4 x 4 = 16.',
          'calc'
        ),
        S(
          'How many tokens does this statement have in WCC? System.out.println("Pass");',
          ['4', '5', '7', '6'],
          3,
          'The tokens are System, ., out, ., println( ) and "Pass", which is 6. The semicolon is not a token.',
          'calc'
        ),
        M(
          'Which items are counted as tokens in WCC?',
          [
            'A string such as "Fail"',
            'The semicolon at the end of a statement',
            'The dot operator between names',
            'The keyword return',
          ],
          [0, 2],
          'Strings and the dot operator are tokens. The statement terminator and the keyword return are not counted.',
          'multi'
        ),
        M(
          'Which weights for type of control structure are correct?',
          ['Sequential is 0', 'Branch is 2', 'Iterative is 2', 'A switch with 4 cases is 4'],
          [0, 2, 3],
          'Sequential is 0, branch is 1, iterative is 2, and a switch with n cases has weight n.',
          'multi'
        ),
        M(
          'Which nesting level weights are correct?',
          [
            'Sequential statements have weight 0',
            'Statements in first level structures have weight 1',
            'Statements in second level structures have weight 1',
            'Statements in third level structures have weight 3',
          ],
          [0, 1, 3],
          'The nesting weight equals the level: first level is 1, second is 2 and third is 3. Sequential statements have weight 0.',
          'multi'
        ),
        M(
          'Which statements about the CFS metric are true?',
          [
            'It is a paradigm independent metric',
            'Cognitive weight shows the effort to understand a component',
            'For one method, Sf is (Ni + No) times Wc',
            'It only counts the lines of code in a method',
          ],
          [0, 1, 2],
          'CFS is based on control structure weights, inputs and outputs. It is not a line count.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'What is the inheritance weight Wi for statements in the second derived class?',
          ['1', '2', '3', '0'],
          1,
          'Wi is 0 in the base class, 1 in the first derived class and n in the nth derived class. So the second derived class has 2.',
          'concept'
        ),
        D(
          'Four program lines have WC values 2, 10, 6 and 6. What is the WCC of the program?',
          ['22', '26', '30', '24'],
          3,
          'WCC is the sum of the WC values of all lines: 2 + 10 + 6 + 6 = 24.',
          'calc'
        ),
        D(
          'How many tokens does this statement have in WCC? r.outresult(50);',
          ['2', '4', '3', '5'],
          2,
          'The tokens are r, the dot operator and outresult( ). The method name with its round brackets is one token, and the argument inside a user-defined method is not counted.',
          'calc'
        ),
      ],
    },

    qm_stlc_automation: {
      label: 'Software Testing Life Cycle and Test Automation',
      lectures: 'T1-T2',
      practice: [
        S(
          'What is the correct order of the first four STLC phases?',
          [
            'Test planning, requirement analysis, test case development, environment setup',
            'Requirement analysis, test planning, test case development, environment setup',
            'Requirement analysis, test case development, test planning, environment setup',
            'Requirement analysis, test planning, environment setup, test case development',
          ],
          1,
          'STLC starts with requirement analysis, then test planning, test case development and test environment setup. Test execution and closure follow.',
          'order'
        ),
        S(
          'What is a Requirement Traceability Matrix (RTM)?',
          [
            'A report of defects found per cycle',
            'A list of tools used for automation',
            'A plan that assigns testers to tasks',
            'A map from requirements to design and tests',
          ],
          3,
          'An RTM maps each requirement to its design, development and testing elements.',
          'concept'
        ),
        S(
          'Which item is a high-level idea of what needs to be tested?',
          ['Test scenario', 'Test case', 'Test script', 'Test data'],
          0,
          'A test scenario is high level, for example verifying a valid login. A test case adds detailed steps and expected results.',
          'compare'
        ),
        S(
          'A team writes a test summary report and records lessons learned. Which STLC phase is this?',
          ['Test execution', 'Test planning', 'Test cycle closure', 'Test environment setup'],
          2,
          'Test cycle closure produces the test summary report, test metrics and lessons learned document.',
          'scenario'
        ),
        S(
          'Which test is the best candidate for automation?',
          [
            'Regression tests run on every build',
            'A one-time data migration check',
            'Exploratory testing for visual bugs',
            'A usability review of a new color scheme',
          ],
          0,
          'Frequent, repetitive tests such as regression tests are worth automating. One-time, exploratory and usability tests need humans or give little return.',
          'scenario'
        ),
        S(
          'Which framework keeps test data in external files such as Excel or CSV, apart from the script logic?',
          [
            'Linear scripting framework',
            'Modular testing framework',
            'Data-driven framework',
            'Keyword-driven framework',
          ],
          2,
          'The data-driven framework separates test logic from test data, so one script can run many data sets.',
          'concept'
        ),
        M(
          'Which activities belong to the test execution phase?',
          [
            'Log defects found',
            'Define the test scope',
            'Retest after fixes',
            'Estimate effort and resources',
          ],
          [0, 2],
          'Execution covers running tests, logging defects, retesting and updating results. Scope and estimates belong to test planning.',
          'multi'
        ),
        M(
          'Which are poor candidates for automation?',
          [
            'Exploratory testing',
            'Regression tests run often',
            'A feature that will be removed soon',
            'Data-driven tests with 500 inputs',
          ],
          [0, 2],
          'Exploratory testing needs human intuition, and short-lived features are not worth the effort. Regression and data-driven tests suit automation.',
          'multi'
        ),
        M(
          'Which are common causes of flaky tests?',
          [
            'Timing and async waits',
            'A change in the code between runs',
            'Slow network or API responses',
            'A third-party API that is down',
          ],
          [0, 2, 3],
          'A flaky test passes and fails with no code change. Timing, network delays and external systems are common causes.',
          'multi'
        ),
        M(
          'Which statements are listed as myths about test automation?',
          [
            'Automation completely removes manual testing',
            'Flaky tests reduce trust in results',
            'Automation is only for large projects',
            'Automation is a one-time activity',
          ],
          [0, 2, 3],
          'Automation does not replace manual testing, it suits projects of any size and it needs ongoing maintenance. Flaky tests really do reduce trust.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'Which framework is also known as Record and Playback?',
          [
            'Hybrid framework',
            'Data-driven framework',
            'Keyword-driven framework',
            'Linear scripting framework',
          ],
          3,
          'The linear scripting framework records browser actions and plays them back, as in Selenium IDE. It is simple but hard to maintain.',
          'concept'
        ),
        D(
          'A team uses modular test logic, Excel test data and keyword-based actions together. Which framework is this?',
          [
            'BDD framework',
            'Hybrid framework',
            'Linear scripting framework',
            'Data-driven framework',
          ],
          1,
          'A hybrid framework combines two or more approaches. Most real projects use hybrid frameworks.',
          'scenario'
        ),
        D(
          'Which statement correctly compares SDLC and STLC?',
          [
            'SDLC covers only testing activities',
            'STLC is mainly done by business analysts',
            'STLC outputs include test cases and bug reports',
            'SDLC outputs only test summary reports',
          ],
          2,
          'SDLC covers the whole development from requirements to deployment. STLC covers testing only and produces test cases, bug reports and test summary reports.',
          'compare'
        ),
      ],
    },

    qm_tdd_trends: {
      label: 'Test-Driven Development and Testing Trends',
      lectures: 'T3-T4',
      practice: [
        S(
          'Which TDD phase has the goal to write just enough code to make the failing test pass?',
          ['Red phase', 'Refactor phase', 'Green phase', 'Release phase'],
          2,
          'The Green phase writes the minimum code to pass the test. Cleaning the code comes later in the Refactor phase.',
          'concept'
        ),
        S(
          'How does TDD differ from traditional testing?',
          [
            'Tests are written before the code',
            'Tests are written only by dedicated QA testers',
            'Feedback comes late in the testing phase',
            'Testing covers the whole application at the end',
          ],
          0,
          'In TDD developers write small tests first and get quick feedback. Traditional testing happens after the code is written.',
          'compare'
        ),
        S(
          'A developer writes five long tests before any code exists for a sum function. Which TDD rule is broken?',
          [
            'Rule 1, no code without a test',
            'Rule 3, no more code than needed',
            'The refactor step of the cycle',
            'Rule 2, no more test than needed',
          ],
          3,
          'Rule 2 says to write only enough test to see it fail. Do not write many or long tests upfront.',
          'scenario'
        ),
        S(
          'A ReportService class collects data, formats it and sends email. Which SOLID principle does it break?',
          [
            'Open/Closed Principle',
            'Single Responsibility Principle',
            'Liskov Substitution Principle',
            'Interface Segregation Principle',
          ],
          1,
          'A class should have only one reason to change. TDD pushes you to split these roles into separate classes.',
          'scenario'
        ),
        S(
          'QAOps integrates QA into which cycle?',
          [
            'The waterfall cycle',
            'The requirements cycle',
            'The DevOps cycle',
            'The release cycle',
          ],
          2,
          'QAOps embeds QA continuously into the DevOps cycle, with automated tests across the CI/CD pipeline.',
          'concept'
        ),
        S(
          'UserSignupService uses a concrete EmailService, so tests send real emails. Which principle says to depend on an abstraction instead?',
          [
            'Dependency Inversion Principle',
            'Single Responsibility Principle',
            'Open/Closed Principle',
            'Liskov Substitution Principle',
          ],
          0,
          'The Dependency Inversion Principle says to depend on abstractions, not concrete classes. Then tests can use a mock and stay fast.',
          'scenario'
        ),
        M(
          'Which are benefits of TDD?',
          [
            'Tests act as live documentation',
            'It removes any need for refactoring',
            'Immediate feedback when something breaks',
            'Confidence to refactor safely',
          ],
          [0, 2, 3],
          'TDD gives documentation through tests, quick feedback and safe refactoring. Refactoring is still part of the cycle.',
          'multi'
        ),
        M(
          'Why are mocks used in TDD?',
          [
            'To avoid slow dependencies such as networks',
            'To make tests send real emails',
            'To simulate errors or timeouts',
            'To test several units at once',
          ],
          [0, 2],
          'Mocks let the test focus on one unit, avoid slow or unreliable dependencies and simulate special cases.',
          'multi'
        ),
        M(
          'Which are benefits of shift-left testing?',
          [
            'Issues are found sooner',
            'Testing is done only at the end',
            'Less time is spent on debugging',
            'Release quality improves',
          ],
          [0, 2, 3],
          'Shift-left testing moves testing early. It finds issues sooner, reduces debugging time and improves release quality.',
          'multi'
        ),
        M(
          'Which are uses of AI and ML in software testing?',
          [
            'Defect prediction',
            'Working without any training data',
            'Test case prioritization',
            'Test case generation',
          ],
          [0, 2, 3],
          'AI and ML can predict defects, prioritize tests and generate test cases. They need large amounts of data, which is a challenge.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'In the Red phase of TDD, why should the new test fail first?',
          [
            'It proves the code is already finished',
            'It shows the feature is missing, so the test is valid',
            'It means the refactoring is done',
            'It lowers the number of tests to write',
          ],
          1,
          'A test that fails when the feature is missing shows the test is valid. A test that passes at once would be wrong.',
          'concept'
        ),
        D(
          'Load tests show 10% of API responses at 700 ms, while normal is 100 to 200 ms. A model flags them although no test failed. Which technique is this?',
          ['Clustering', 'Reinforcement learning', 'Classification', 'Anomaly detection'],
          3,
          'Anomaly detection finds data that deviates from what is normal, even when the test case itself did not fail.',
          'scenario'
        ),
        D(
          'Which approach uses a large group of testers outside the company internal QA team, reached through crowdsourcing platforms?',
          [
            'Crowdtesting',
            'Shift-left testing',
            'Mobile test automation',
            'Accessibility testing',
          ],
          0,
          'Crowdtesting uses external testers from crowdsourcing platforms. It gives scalable resources and quicker feedback from users.',
          'concept'
        ),
      ],
    },
  },
};
