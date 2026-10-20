// Paste this whole file into https://script.google.com (New project), press Run, and allow access.
// It creates the pilot form and a response sheet in your Google Drive, then prints the links in the log.
function createPilotForm() {
  const sections = [
  {
    "name": "Project Risk Management",
    "questions": [
      {
        "title": "Q01. A pandemic hits a project and nobody predicted it. Which reserve is used for such unknown risks?",
        "choices": [
          "Contingency reserve",
          "Management reserve",
          "Schedule buffer",
          "Cost baseline"
        ],
        "multi": false
      },
      {
        "title": "Q02. What is the difference between a risk and an issue?",
        "choices": [
          "A risk already happened and an issue may happen",
          "Both have a probability below 1",
          "An issue is a realized risk with probability 1",
          "An issue is a risk that was avoided"
        ],
        "multi": false
      },
      {
        "title": "Q03. What is residual risk?",
        "choices": [
          "The risk remaining after controls are applied",
          "The risk that exists before any control",
          "The risk caused only by suppliers",
          "The risk of an issue that already happened"
        ],
        "multi": false
      },
      {
        "title": "Q04. Build option: 60% chance of strong demand with a net gain of 8M, and 40% chance of weak demand with a net loss of 3M. What is the EMV?",
        "choices": [
          "4.8M",
          "4.6M",
          "5.0M",
          "3.6M"
        ],
        "multi": false
      },
      {
        "title": "Q05. A company buys insurance against data loss. Which risk response strategy is this?",
        "choices": [
          "Avoidance",
          "Mitigation",
          "Transfer",
          "Acceptance"
        ],
        "multi": false
      },
      {
        "title": "Q06. What is an Agile spike?",
        "choices": [
          "A daily meeting to report risks",
          "A time-boxed research task",
          "A chart showing risk burndown",
          "A reserve for unknown risks"
        ],
        "multi": false
      },
      {
        "title": "Q07. Which are response strategies for negative risks (threats)? (select ALL that apply)",
        "choices": [
          "Avoid",
          "Exploit",
          "Transfer",
          "Mitigate"
        ],
        "multi": true
      },
      {
        "title": "Q08. Which are response strategies for positive risks (opportunities)? (select ALL that apply)",
        "choices": [
          "Exploit",
          "Enhance",
          "Transfer",
          "Share"
        ],
        "multi": true
      },
      {
        "title": "Q09. Which are traditional quantitative risk analysis techniques? (select ALL that apply)",
        "choices": [
          "Monte Carlo simulation",
          "Sensitivity analysis",
          "Probability-impact matrix",
          "Decision trees"
        ],
        "multi": true
      },
      {
        "title": "Q10. Which are Agile ways to handle risk? (select ALL that apply)",
        "choices": [
          "Daily stand-ups",
          "Risk burndown charts",
          "A separate formal risk management plan",
          "Retrospectives"
        ],
        "multi": true
      }
    ]
  },
  {
    "name": "Unit, API and Integration Testing",
    "questions": [
      {
        "title": "Q11. In an object-oriented context, what is usually a unit in unit testing?",
        "choices": [
          "A whole subsystem",
          "A complete database",
          "A class or a method",
          "The full running system"
        ],
        "multi": false
      },
      {
        "title": "Q12. Which statement matches the test pyramid?",
        "choices": [
          "Many unit tests, fewer integration tests, few end-to-end tests",
          "Many end-to-end tests, fewer integration tests, few unit tests",
          "The same number of tests at every single level",
          "Only integration tests are needed in practice"
        ],
        "multi": false
      },
      {
        "title": "Q13. Which JUnit annotation runs once before all the tests in a class?",
        "choices": [
          "@BeforeEach",
          "@Test",
          "@AfterAll",
          "@BeforeAll"
        ],
        "multi": false
      },
      {
        "title": "Q14. A test checks that divide(5, 0) fails with an exception. Which assertion fits best?",
        "choices": [
          "assertNull",
          "assertThrows",
          "assertFalse",
          "assertEquals"
        ],
        "multi": false
      },
      {
        "title": "Q15. What is the correct order of the Test-Driven Development cycle?",
        "choices": [
          "Write code, write test, run tests, refactor, repeat",
          "Refactor, write test, write code, run tests, repeat",
          "Write test, see it fail, write minimum code, run tests, refactor",
          "Run all tests, refactor, write code, write test, repeat"
        ],
        "multi": false
      },
      {
        "title": "Q16. Which pair about integration testing is correct?",
        "choices": [
          "Top-down needs drivers; bottom-up needs stubs",
          "Neither approach needs stubs or drivers at all",
          "Both approaches need stubs only",
          "Top-down needs stubs; bottom-up needs drivers"
        ],
        "multi": false
      },
      {
        "title": "Q17. Which things should unit tests check? (select ALL that apply)",
        "choices": [
          "Boundary values such as zero and null",
          "Invalid inputs that should cause exceptions",
          "Only valid inputs on the happy path",
          "One value from each equivalence class"
        ],
        "multi": true
      },
      {
        "title": "Q18. Which are benefits of Test-Driven Development? (select ALL that apply)",
        "choices": [
          "It drives design by thinking about interfaces",
          "Feedback is delayed until coding finishes",
          "Bugs are caught early",
          "It avoids over-engineering"
        ],
        "multi": true
      },
      {
        "title": "Q19. Which statements about bottom-up integration testing are true? (select ALL that apply)",
        "choices": [
          "Drivers are needed",
          "No stubs are needed",
          "The user interface is tested last",
          "Stubs replace the lower-level modules"
        ],
        "multi": true
      },
      {
        "title": "Q20. Why do we do integration testing? (select ALL that apply)",
        "choices": [
          "Unit tests only test a unit in isolation",
          "Many failures come from interaction between subsystems",
          "Off-the-shelf components cannot be unit tested",
          "It removes the need for unit tests"
        ],
        "multi": true
      }
    ]
  },
  {
    "name": "Testing and Analysis of UX",
    "questions": [
      {
        "title": "Q21. Which description fits formative evaluation?",
        "choices": [
          "It evaluates a shipped product against a benchmark",
          "It is mainly diagnostic and finds and fixes problems early in design",
          "It is used only at the beta stage to collect numbers",
          "It gathers only quantitative data from large samples"
        ],
        "multi": false
      },
      {
        "title": "Q22. A manager asks, \"Is this product good enough to launch?\" Which type of evaluation answers this go or no-go question?",
        "choices": [
          "Formative evaluation",
          "Diagnostic evaluation",
          "Design walkthrough",
          "Summative evaluation"
        ],
        "multi": false
      },
      {
        "title": "Q23. How many evaluators are usually used in a heuristic evaluation?",
        "choices": [
          "Three to five",
          "One or two",
          "Six to eight",
          "Ten to twelve"
        ],
        "multi": false
      },
      {
        "title": "Q24. A website shows only \"Error 0x45\" with no explanation when a payment fails. Which heuristic does this break?",
        "choices": [
          "Aesthetic and minimalist design",
          "Flexibility and efficiency of use",
          "Help users recognize, diagnose and recover from errors",
          "Consistency and standards"
        ],
        "multi": false
      },
      {
        "title": "Q25. What is the key difference of the RITE method?",
        "choices": [
          "The prototype is changed during the study, as issues appear",
          "The prototype is changed only after the full study has finished",
          "It is used only after the product has been released to users",
          "It uses only questionnaires to collect data from participants"
        ],
        "multi": false
      },
      {
        "title": "Q26. Which of these is NOT one of the ten usability heuristics?",
        "choices": [
          "Error prevention",
          "Visibility of system status",
          "Recognition rather than recall",
          "Maximum number of features"
        ],
        "multi": false
      },
      {
        "title": "Q27. Which are examples of objective UX data? Select all that apply. (select ALL that apply)",
        "choices": [
          "Time to complete a task",
          "A user's opinion about the design",
          "Number of errors made",
          "A rating of joy of use"
        ],
        "multi": true
      },
      {
        "title": "Q28. Which are types of UX analytics named in the lecture? Select all that apply. (select ALL that apply)",
        "choices": [
          "Descriptive",
          "Diagnostic",
          "Persuasive",
          "Predictive"
        ],
        "multi": true
      },
      {
        "title": "Q29. Which are types of UX analytics tools listed in the lecture? Select all that apply. (select ALL that apply)",
        "choices": [
          "Funnel analytics",
          "Heatmap analytics",
          "Session recording",
          "Card sorting boards"
        ],
        "multi": true
      },
      {
        "title": "Q30. Which statements follow good guidance for error messages? Select all that apply. (select ALL that apply)",
        "choices": [
          "Use plain language without codes",
          "Add humor to make the error feel lighter",
          "Say why the error happened and how to fix it",
          "Be polite and avoid accusing wording such as FATAL ERROR"
        ],
        "multi": true
      }
    ]
  }
];
  const form = FormApp.create('Question pilot (30 questions, about 30 minutes)');
  form.setDescription('Please answer on your own, without notes or searching, because your answers only help if they show what you really know. ' +
    'Some questions say "select ALL that apply". There is no name or email in this form. Please submit only once. Thank you!');
  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setConfirmationMessage('Thank you! Your answers were saved.');
  sections.forEach(function (s, si) {
    if (si > 0) form.addPageBreakItem().setTitle(s.name);
    else form.addSectionHeaderItem().setTitle(s.name);
    s.questions.forEach(function (q) {
      const item = q.multi ? form.addCheckboxItem() : form.addMultipleChoiceItem();
      item.setTitle(q.title).setChoiceValues(q.choices).setRequired(true);
    });
  });
  const sheet = SpreadsheetApp.create('Question pilot responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());
  Logger.log('SHARE THIS LINK WITH CLASSMATES: ' + form.getPublishedUrl());
  Logger.log('Responses sheet: ' + sheet.getUrl());
  Logger.log('Edit the form: ' + form.getEditUrl());
}
