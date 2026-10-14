import { S, M, D } from './helpers.js';

export default {
  semester: 'Y3S1',
  module_code: 'SE3050',
  module_name: 'User Experience Engineering',
  topics: {
    ux_foundations_process: {
      label: 'UX Foundations and Design Process',
      lectures: 'L01-L02',
      practice: [
        S(
          'Don Norman and Jakob Nielsen define user experience. What does it include?',
          [
            'Only the look and layout of the buttons, colors and menus on screen',
            'Only how fast and reliably the product code runs on a device',
            'All aspects of the end user\'s interaction with the company, services and products',
            'Only the list of features that the project team has decided to build',
          ],
          2,
          'UX covers every part of the user\'s interaction, not just the screen elements. Thinking that UX equals the interface look is a common mistake.',
          'concept'
        ),
        S(
          'A movie review site has a perfect interface for finding films. Its database only has films from major studios. A user wants a small independent film. What is the result?',
          [
            'The UI is good, but the UX is poor for this user',
            'Both the UI and the UX are good because the screens are clear',
            'The UX is good because the interface is easy to use',
            'The UI is poor because the database is missing films',
          ],
          0,
          'UI is only the elements used to interact. UX is what the user takes away from the whole experience, and here the missing content spoils it.',
          'scenario'
        ),
        S(
          'In UX, what is a conversion rate?',
          [
            'The number of pages a visitor opens during one visit to the site',
            'The share of visitors who leave the site after viewing one page',
            'The money earned from each visitor who buys one product',
            'The percentage of all visitors who complete a desired goal',
          ],
          3,
          'Conversion rate is the percentage of visitors who complete a goal out of all visitors. It is used to measure the return on investment of UX.',
          'concept'
        ),
        S(
          'What is the correct order of the five stages of the Design Thinking model?',
          [
            'Define, Empathise, Ideate, Prototype, Test',
            'Empathise, Define, Ideate, Prototype, Test',
            'Empathise, Ideate, Define, Test, Prototype',
            'Define, Ideate, Empathise, Test, Prototype',
          ],
          1,
          'The model starts by understanding users (Empathise), then Define, Ideate, Prototype and Test. The stages can repeat, but this is the listed order.',
          'order'
        ),
        S(
          'In a gym booking app, the team puts a green "Book Now" button clearly on each class card. Which plane of UX is this decision on?',
          [
            'Strategy plane',
            'Scope plane',
            'Structure plane',
            'Skeleton plane',
          ],
          3,
          'Placing buttons and arranging interface elements for ease of use is Skeleton plane work. Structure is about how the system behaves and how information is organized.',
          'scenario'
        ),
        S(
          'Which organization developed the five-day Design Sprint process?',
          [
            'Hasso-Plattner Institute at Stanford',
            'Google Ventures (GV)',
            'Nielsen Norman Group',
            'Jesse James Garrett\'s team',
          ],
          1,
          'The Design Sprint was developed by Google Ventures. The five-stage Design Thinking model comes from the Stanford d.school, which is easy to mix up.',
          'concept'
        ),
        M(
          'Which of these are listed as common UX myths? Select all that apply.',
          [
            'Simple means minimal',
            'If you are an expert, you do not need to test your design',
            'People are rational',
            'Good UX needs a deep understanding of users and their limits',
          ],
          [0, 1, 2],
          'The first three are myths from the lecture. The last statement is true and is actually the core idea of UX, so it is not a myth.',
          'multi'
        ),
        M(
          'Which of these are benefits of good UX? Select all that apply.',
          [
            'Users stay loyal to the product or brand',
            'Lower hosting costs for the servers',
            'Users make fewer mistakes',
            'Business success',
          ],
          [0, 2, 3],
          'Good UX brings loyalty, fewer mistakes, faster work and business success. Server hosting cost is not a UX benefit named in the lecture.',
          'multi'
        ),
        M(
          'Which activities belong to the Empathise stage of Design Thinking? Select all that apply.',
          [
            'Consulting experts about the area of concern',
            'Building cheap, scaled-down versions of the product',
            'Observing and engaging with people to learn their experiences',
            'Immersing yourself in the physical environment',
          ],
          [0, 2, 3],
          'Empathise is about gaining a deep understanding of users and their problem. Building scaled-down versions is the Prototype stage.',
          'multi'
        ),
        M(
          'Which of these are ideation techniques named in the lecture? Select all that apply.',
          [
            'SCAMPER',
            'Brainwrite',
            'Eye tracking',
            'Clickstream analysis',
          ],
          [0, 1],
          'SCAMPER and Brainwrite help generate ideas in the Ideate stage. Eye tracking and clickstream analysis are user research methods.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'Which statement correctly separates UI from UX?',
          [
            'UI is the set of elements used to interact; UX is what the user takes away from the whole experience',
            'UI is what the user takes away from the experience; UX is the set of screen elements',
            'UI is about user research only; UX is about colors and fonts only',
            'UI and UX mean exactly the same thing in a project',
          ],
          0,
          'UI is the elements that let someone interact. UX is the overall experience the person gets, which is the reverse of option two.',
          'compare'
        ),
        D(
          'A team is in the Define stage. Which problem statement is written in a human-centered way?',
          [
            'We need to increase our market share among young teenage girls by 5%',
            'We want to sell more food products to teenagers this year',
            'We wish to launch a new snack for teenage girls',
            'Teenage girls need to eat nutritious food to be healthy and grow',
          ],
          3,
          'A problem statement should describe the user\'s need, not the company\'s wish or goal. The first three options are business wishes.',
          'scenario'
        ),
        D(
          'In a Design Sprint, which phase comes straight after Ideate?',
          [
            'Prototype',
            'Decide',
            'Test',
            'Understand',
          ],
          1,
          'The five sprint days are Understand, Ideate, Decide, Prototype and Test. On the Decide day the team chooses the best idea to move forward.',
          'order'
        ),
      ],
    },

    user_research_synthesis: {
      label: 'User Research and Synthesis',
      lectures: 'L03-L04',
      practice: [
        S(
          'What does attitudinal user research focus on?',
          [
            'The attitudes, opinions and beliefs of users',
            'Click paths recorded while users use a site',
            'The time users need to finish a task',
            'The number of errors users make on a screen',
          ],
          0,
          'Attitudinal research is about what users say and believe, often through surveys, interviews and focus groups. Behavioral research looks at what users actually do.',
          'concept'
        ),
        S(
          'Which description matches quantitative research?',
          [
            'In-depth, exploratory understanding gained through interviews',
            'Insights about opinions that numbers cannot easily capture',
            'Observing people in their natural environment',
            'Collecting numerical data and using statistical analysis',
          ],
          3,
          'Quantitative research collects numbers, for example through surveys, experiments and analytics. The other options describe qualitative research.',
          'compare'
        ),
        S(
          'A team wants to improve the information architecture of a site by learning how users group items. Which research method fits best?',
          [
            'Eye tracking',
            'Card sorting',
            'Diary study',
            'A/B testing',
          ],
          1,
          'Card sorting asks users to organize items into groups, which exposes their mental models. It helps create or refine the information architecture.',
          'scenario'
        ),
        S(
          'A team randomly shows two page designs to different groups of visitors and compares how they behave. Which method is this?',
          [
            'Concept testing',
            'Intercept survey',
            'A/B testing',
            'Participatory design',
          ],
          2,
          'A/B testing randomly assigns users to different designs and measures the effect on behavior. It is sometimes called bucket testing.',
          'scenario'
        ),
        S(
          'In Hierarchical Task Analysis, what does a "plan" describe?',
          [
            'The budget and schedule for the project',
            'The final visual design of the screen',
            'How the sub-tasks might be performed in practice, for example for a new or regular user',
            'The list of users who will test the system',
          ],
          2,
          'HTA breaks a goal into sub-tasks, and plans say in what order or under what condition they are done. In the DVD example, a regular user and a new user follow different plans.',
          'concept'
        ),
        S(
          'Ten users rated ease of finding a location: 3, 4, 4, 5, 2, 3, 4, 5, 4, 3. What is the mean rating?',
          [
            '3.4',
            '3.9',
            '4.0',
            '3.7',
          ],
          3,
          'The sum is 37 and 37 divided by 10 is 3.7. The median is 4, which is a common mix-up with the mean.',
          'calc'
        ),
        M(
          'Which of these are among the "5 W\'s" of user research? Select all that apply.',
          [
            'Who',
            'Which',
            'When',
            'Where',
          ],
          [0, 2, 3],
          'The 5 W\'s are Who, What, When, Where and Why. "Which" is not one of them.',
          'multi'
        ),
        M(
          'Which of these are steps of thematic analysis? Select all that apply.',
          [
            'Calculating Pearson\'s r for two variables',
            'Familiarization with the data',
            'Coding the data',
            'Reviewing the themes',
          ],
          [1, 2, 3],
          'Thematic analysis goes from familiarization to coding, finding and reviewing themes, naming them and reporting. Pearson\'s r belongs to quantitative correlation analysis.',
          'multi'
        ),
        M(
          'Which of these are parts of an empathy map? Select all that apply.',
          [
            'Says',
            'Feels',
            'Plans',
            'Does',
          ],
          [0, 1, 3],
          'An empathy map has Says, Thinks, Does and Feels, with optional Pains and Gains. "Plans" is not a quadrant.',
          'multi'
        ),
        M(
          'Which statements about the Impact and Effort prioritization matrix are correct? Select all that apply.',
          [
            'High impact and low effort items are quick wins to do first',
            'High impact and high effort items are major projects to plan',
            'Low impact and high effort items are the best items to start with',
            'Low impact and low effort items are time wasters to avoid',
          ],
          [0, 1],
          'Low impact and high effort items are usually avoided. Low impact and low effort items are fill-ins to do if time allows.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'Which one is a correctly written user story?',
          [
            'The system shall provide a room search function for all students',
            'As a student, I want to search by room number so that I can find lectures faster',
            'Room search is a high priority feature for the next sprint release',
            'Students are often late because they cannot find rooms on campus',
          ],
          1,
          'A user story follows "As a [user], I want [goal] so that [benefit]". It stays user-centered and explains why the feature matters.',
          'concept'
        ),
        D(
          'Which set of questions should a good problem statement answer?',
          [
            'Which tool to use, what it costs, who builds it and when it ships',
            'What the solution is, which features it needs, how long it takes and who pays',
            'Which persona to use, which method to run, how many users to test and what budget to set',
            'Who has the problem, what it is, where or when it occurs and why it matters',
          ],
          3,
          'A problem statement describes who is affected, what the problem is, where or when it happens and why it is important. It should stay solution-neutral.',
          'concept'
        ),
        D(
          'How does thematic analysis go further than affinity mapping?',
          [
            'It involves deeper interpretation of the meaning behind what users say',
            'It uses only numeric ratings collected from surveys',
            'It needs no coding or grouping of the data at all',
            'It groups sticky notes silently without any discussion',
          ],
          0,
          'Affinity mapping groups notes into themes. Thematic analysis goes beyond grouping to understand why users say what they say.',
          'compare'
        ),
      ],
    },

    structuring_prototyping: {
      label: 'Structuring and Prototyping',
      lectures: 'L05',
      practice: [
        S(
          'What is the purpose of a functional specification document?',
          [
            'To show the final colors and fonts of the product',
            'To tell developers how the application will function and what behavior is expected',
            'To record the results of every usability test',
            'To replace all communication between the team members',
          ],
          1,
          'It is a blueprint that describes expected behavior, so no time is wasted on code that will not be used. It also reduces back and forth and internal arguments.',
          'concept'
        ),
        S(
          'Which dimension of interaction design covers animations, videos and sounds?',
          [
            'Words (1D)',
            'Visual representations (2D)',
            'Physical objects or space (3D)',
            'Time (4D)',
          ],
          3,
          'Time (4D) relates to media that change over time, such as animation, video and sound. Words are text, such as button labels.',
          'concept'
        ),
        S(
          'An online store sorts its products into categories so that shoppers see fewer choices at one time. Which law supports this?',
          [
            'Hick\'s Law',
            'Fitts\' Law',
            'Tesler\'s Law',
            'Gestalt closure',
          ],
          0,
          'Hick\'s Law says that more choices make people take longer to decide. Fitts\' Law is about the size and distance of targets.',
          'scenario'
        ),
        S(
          'According to Tesler\'s Law, what should designers do with complexity that cannot be removed?',
          [
            'Show all of it to expert users on the main screen',
            'Spread it equally across every screen',
            'Move as much of it as possible to back-stage processes, away from the user',
            'Remove every feature that is complex',
          ],
          2,
          'Every application has some complexity that cannot be simplified. The designer should keep it away from the user to make the interface minimalist and easy to navigate.',
          'concept'
        ),
        S(
          'Which of these is NOT a characteristic of a sketch?',
          [
            'Quick to produce',
            'Costly and time-consuming to produce',
            'Disposable after it has helped explore a concept',
            'Plentiful, made as a collection of ideas',
          ],
          1,
          'Sketches are quick, timely, disposable, plentiful and minimalist. A sketch that takes long and costs a lot loses its purpose.',
          'not'
        ),
        S(
          'What does a mockup add compared with a wireframe?',
          [
            'Clickable links between all the screens',
            'Real back-end code and a database',
            'A freehand drawing on a sheet of paper',
            'Visual details such as colors, images and typography',
          ],
          3,
          'A wireframe lays out structure and content, while a mockup is a more polished static visual draft. A mockup shows the style and mood of the project.',
          'compare'
        ),
        M(
          'Which are elements of cognitive psychology that are valuable for information architecture? Select all that apply.',
          [
            'Mental models',
            'Cognitive load',
            'Sitemaps',
            'Color value',
          ],
          [0, 1],
          'Mental models and cognitive load are the key cognitive ideas named for IA. A sitemap is an IA diagram, and color value is a visual design element.',
          'multi'
        ),
        M(
          'Which tasks do information architects do? Select all that apply.',
          [
            'Create sitemaps that show the hierarchy of content',
            'Run card sorting and tree testing sessions',
            'Write the back-end database code',
            'Create taxonomies and labels for the content',
          ],
          [0, 1, 3],
          'IAs do content inventories, user research, taxonomies, hierarchy and navigation, and simple prototypes. Back-end coding is not part of the IA role.',
          'multi'
        ),
        M(
          'Which are interaction types listed in the lecture? Select all that apply.',
          [
            'Instructing',
            'Conversing',
            'Compiling',
            'Exploring',
          ],
          [0, 1, 3],
          'The five types are instructing, conversing, manipulating, exploring and responding. Compiling is not an interaction type.',
          'multi'
        ),
        M(
          'Which statements about the Crazy Eights method are correct? Select all that apply.',
          [
            'The paper is folded three times to make eight panels',
            'You have five minutes in total to draw eight sketches',
            'Each sketch should take a full day to finish',
            'Two rounds of Crazy Eights give the best results',
          ],
          [0, 1, 3],
          'Crazy Eights is a Google Ventures sprint technique to visualize many ideas in a short time. Speed matters, so sketches are not slow.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'A user looks for contact details and first searches for a link called "Contact Us". Which concept does this show?',
          [
            'Cognitive load',
            'Taxonomy',
            'Mental models',
            'Fitts\' Law',
          ],
          2,
          'Mental models are the assumptions people hold before they use a product. Good IA puts information where users expect to find it.',
          'scenario'
        ),
        D(
          'What is the difference between hierarchy and navigation in IA?',
          [
            'Hierarchy defines the structure of content; navigation defines how users move through it',
            'Hierarchy defines how users move through content; navigation defines its structure',
            'Hierarchy is about colors; navigation is about fonts',
            'They mean the same thing in information architecture',
          ],
          0,
          'The first sets the structure of the content and the second sets the way users move through it. IAs show them in sitemap diagrams.',
          'compare'
        ),
        D(
          'What does a content inventory show an information architect?',
          [
            'How accurate and useful each content item is',
            'How users group the items in their own minds',
            'How the items are related to each other',
            'What content exists and where it lives',
          ],
          3,
          'A content inventory is usually a spreadsheet or list of what content exists and where. Grouping shows relationships, and audits rate the usefulness of the content.',
          'compare'
        ),
      ],
    },

    visual_design_accessibility: {
      label: 'Visual Design and High-Fidelity Prototyping',
      lectures: 'L06a-L06b',
      practice: [
        S(
          'What is negative space (white space) in visual design?',
          [
            'The darkest part of a design',
            'An area filled with texture',
            'The empty area around a positive shape',
            'The space between two lines of text only',
          ],
          2,
          'Negative space is the empty area around a shape. It defines the boundaries of the shape and brings balance to a composition.',
          'concept'
        ),
        S(
          'Subtitles help deaf users and also help a commuter on a noisy bus. For the commuter, what kind of constraint is this?',
          [
            'Situational',
            'Permanent',
            'Temporary',
            'Economic',
          ],
          0,
          'The lecture groups constraints as permanent, temporary and situational. Noise on a bus is a situational limit that the same design helps.',
          'scenario'
        ),
        S(
          'Which describes a vertical prototype?',
          [
            'Many features with very little depth in each',
            'Deep functionality for only a narrow set of features',
            'One isolated detail such as the look of an icon',
            'A paper model drawn with colored markers',
          ],
          1,
          'A vertical prototype has as much depth as possible for a narrow breadth of features. A horizontal prototype is the opposite: broad but shallow.',
          'compare'
        ),
        S(
          'A user types on one computer. A hidden team member in another room sees the input and sends back simulated replies. Which technique is this?',
          [
            'Paper prototyping',
            'Animated prototype',
            'Click-through prototype',
            'Wizard of Oz prototype',
          ],
          3,
          'The Wizard of Oz technique uses a hidden human to simulate the system. It gives the appearance of high interactivity when user inputs are unpredictable.',
          'scenario'
        ),
        S(
          'What is the minimum text contrast ratio suggested for body text?',
          [
            '3:1',
            '7:1',
            '4.5:1',
            '2:1',
          ],
          2,
          'Body text should have a contrast of at least 4.5:1. The 3:1 ratio is for large text, which is a common mix-up.',
          'calc'
        ),
        S(
          'A site has several fixed layouts and picks the best one for the detected screen. Resizing the desktop browser does not change the layout. Which approach is this?',
          [
            'Responsive design',
            'Adaptive design',
            'Fluid grid design',
            'Standalone mobile design',
          ],
          1,
          'Adaptive design uses multiple fixed layouts, for example for six common widths. Responsive design instead rearranges elements as the browser width changes.',
          'compare'
        ),
        M(
          'Which are principles of visual design in the lecture? Select all that apply.',
          [
            'Unity',
            'Dominance',
            'Texture',
            'Balance',
          ],
          [0, 1, 3],
          'Unity, dominance and balance are principles. Texture is one of the basic elements of visual design, not a principle.',
          'multi'
        ),
        M(
          'Which input controls let users select more than one item at a time? Select all that apply.',
          [
            'Checkboxes',
            'Radio buttons',
            'List boxes',
            'Dropdown lists',
          ],
          [0, 2],
          'Checkboxes and list boxes allow multiple selections. Radio buttons and dropdown lists allow only one item at a time.',
          'multi'
        ),
        M(
          'Which design moves support visual accessibility? Select all that apply.',
          [
            'Show errors with an icon and text, not color alone',
            'Add alternative text to images that carry meaning',
            'Use thin red text only to show important warnings',
            'Allow text to be scaled by the user',
          ],
          [0, 1, 3],
          'Do not rely on color alone, give alternative text and allow scalable text. Avoid coloring text in red or green and do not use color as the only signal.',
          'multi'
        ),
        M(
          'Which are key considerations for internationalization and localization? Select all that apply.',
          [
            'Some languages grow 20 to 40 percent longer than English text',
            'Dates, times and currency should follow the locale',
            'Date formats should be hard-coded into the interface',
            'Right-to-left languages need a mirrored layout and icons',
          ],
          [0, 1, 3],
          'Text expansion, locale formats and RTL mirroring all matter. Hard-coded formats break localization.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'A user with a hand tremor often taps the wrong control. Which design move from the lecture helps most?',
          [
            'Use very small icons to save screen space',
            'Use gesture-only actions for all tasks',
            'Hide controls until the user moves the pointer',
            'Use touch targets of at least about 44 by 44 dp with spacing',
          ],
          3,
          'Motor accessibility needs large, forgiving targets with space between them, keyboard access and undo. Gesture-only actions should be avoided.',
          'scenario'
        ),
        D(
          'Which statement describes localization (l10n)?',
          [
            'Engineering the product so it adapts to any locale without code changes',
            'Making a site resize itself for desktops, tablets and phones',
            'Providing locale-specific content such as translations, formats and images',
            'Testing that text has enough color contrast',
          ],
          2,
          'Internationalization prepares the product, and localization supplies the locale-specific content and rules. The first option describes i18n.',
          'compare'
        ),
        D(
          'What is the first and most important role of a low-fidelity prototype?',
          [
            'To check and test functionality rather than visual appearance',
            'To get final design approval from stakeholders',
            'To show realistic fonts, images and spacing',
            'To replace the final working product',
          ],
          0,
          'Lo-fi prototypes quickly turn concepts into testable artifacts, mainly to check functionality. High-fidelity prototypes are used for realistic looks and final approval.',
          'concept'
        ),
      ],
    },

    ux_testing_heuristics: {
      label: 'Testing and Analysis of UX',
      lectures: 'L07',
      practice: [
        S(
          'Which description fits formative evaluation?',
          [
            'It evaluates a shipped product against a benchmark',
            'It is mainly diagnostic and finds and fixes problems early in design',
            'It is used only at the beta stage to collect numbers',
            'It gathers only quantitative data from large samples',
          ],
          1,
          'Formative evaluation helps form the design, using mostly qualitative data in an iterative process. Summative evaluation sums up the design, often against a benchmark.',
          'compare'
        ),
        S(
          'A manager asks, "Is this product good enough to launch?" Which type of evaluation answers this go or no-go question?',
          [
            'Formative evaluation',
            'Diagnostic evaluation',
            'Design walkthrough',
            'Summative evaluation',
          ],
          3,
          'Summative evaluation assesses quality late in the life cycle, for example against UX goals or benchmarks. Questions about whether users understand the navigation are formative.',
          'scenario'
        ),
        S(
          'How many evaluators are usually used in a heuristic evaluation?',
          [
            'Three to five',
            'One or two',
            'Six to eight',
            'Ten to twelve',
          ],
          0,
          'The project team selects a small group of about three to five evaluators. Each one inspects the design on their own first and then the group merges their lists.',
          'concept'
        ),
        S(
          'A website shows only "Error 0x45" with no explanation when a payment fails. Which heuristic does this break?',
          [
            'Aesthetic and minimalist design',
            'Flexibility and efficiency of use',
            'Help users recognize, diagnose and recover from errors',
            'Consistency and standards',
          ],
          2,
          'Error messages should use plain language with no codes, state the problem precisely and suggest a solution.',
          'scenario'
        ),
        S(
          'What is the key difference of the RITE method?',
          [
            'The prototype is changed during the study, after 1 to 3 participants meet an issue',
            'The prototype is changed only after the full study has ended',
            'It is used only after the product is released',
            'It uses only questionnaires to collect data',
          ],
          0,
          'RITE updates the prototype as soon as a usability issue appears, so problems are solved quickly. It came from the gaming division at Microsoft.',
          'compare'
        ),
        S(
          'Which of these is NOT one of the ten usability heuristics?',
          [
            'Error prevention',
            'Visibility of system status',
            'Recognition rather than recall',
            'Maximum number of features',
          ],
          3,
          'The heuristics include error prevention, visibility of system status and recognition rather than recall. Offering the maximum number of features is not a heuristic, and the "aesthetic and minimalist" heuristic argues against it.',
          'not'
        ),
        M(
          'Which are examples of objective UX data? Select all that apply.',
          [
            'Time to complete a task',
            'A user\'s opinion about the design',
            'Number of errors made',
            'A rating of joy of use',
          ],
          [0, 2],
          'Objective data are observed directly, such as time and errors. Opinions and satisfaction ratings are subjective data.',
          'multi'
        ),
        M(
          'Which are types of UX analytics named in the lecture? Select all that apply.',
          [
            'Descriptive',
            'Diagnostic',
            'Persuasive',
            'Predictive',
          ],
          [0, 1, 3],
          'The four types are descriptive, diagnostic, prescriptive and predictive. Persuasive is not a type.',
          'multi'
        ),
        M(
          'Which are types of UX analytics tools listed in the lecture? Select all that apply.',
          [
            'Funnel analytics',
            'Heatmap analytics',
            'Session recording',
            'Card sorting boards',
          ],
          [0, 1, 2],
          'Funnels show where users drop out, heatmaps show click activity and session recordings replay user sessions. Card sorting is a research method, not an analytics tool.',
          'multi'
        ),
        M(
          'Which statements follow good guidance for error messages? Select all that apply.',
          [
            'Use plain language without codes',
            'Add humor to make the error feel lighter',
            'Say why the error happened and how to fix it',
            'Be polite and avoid accusing wording such as FATAL ERROR',
          ],
          [0, 2, 3],
          'Good messages are clear, precise, constructive and polite. Humor or snide comments should not be used.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'What is the System Usability Scale (SUS)?',
          [
            'A five-item yes or no checklist for expert inspectors',
            'A device that tracks where participants look on a screen',
            'A 10-item questionnaire with five answer options from strongly agree to strongly disagree',
            'A list of ten design heuristics for walkthroughs',
          ],
          2,
          'SUS is a quick and reliable questionnaire created by John Brooke in 1986. It can be used for hardware, software, mobile devices and websites.',
          'concept'
        ),
        D(
          'A booking form grays out dates that are not available. Which heuristic does this support?',
          [
            'Visibility of system status',
            'Error prevention',
            'Consistency and standards',
            'Help and documentation',
          ],
          1,
          'Removing or graying out illegal choices stops errors before they happen. Good error prevention is better than a good error message.',
          'scenario'
        ),
        D(
          'Which statement is true of alpha testing compared with beta testing?',
          [
            'It is done by end users at their own location',
            'It needs no lab or testing environment',
            'It is made available to the public in real time',
            'It is done by internal employees at the developer\'s site',
          ],
          3,
          'Alpha testing is done by internal staff at the developer\'s site, often in a lab. Beta testing is done by clients or end users outside the organization.',
          'compare'
        ),
      ],
    },

    devices_trends_teams: {
      label: 'Devices, Design Trends, Teams and Portfolio',
      lectures: 'L08-L11',
      practice: [
        S(
          'A bank app shows your balance, but branch staff cannot see your app activity. Which type of channel experience is this?',
          [
            'Single-channel',
            'Multi-channel',
            'Cross-channel',
            'Omni-channel',
          ],
          1,
          'In a multi-channel experience, channels work separately with data silos. Cross-channel and omni-channel connect the channels.',
          'scenario'
        ),
        S(
          'A customer books a movie ticket in an app and scans a QR code at the cinema. Which type of channel experience is this?',
          [
            'Single-channel',
            'Multi-channel',
            'Cross-channel',
            'Fragmented-channel',
          ],
          2,
          'A task that starts in one channel and finishes in another with shared data is cross-channel. Click and Collect is another example.',
          'scenario'
        ),
        S(
          'Which cross-channel design principle says each channel has its own strengths, such as mobile for quick tasks and desktop for detailed browsing?',
          [
            'Channel-specific',
            'Recognizable',
            'Measurable',
            'Anchored in the organization',
          ],
          0,
          'Channel-specific design adapts features to each channel. Consistency in brand does not mean the design must be identical on every device.',
          'concept'
        ),
        S(
          'Why does the lecture advise designing for the smallest screen first?',
          [
            'Large screens are not important for most products',
            'Mobile users are always more distracted than desktop users',
            'It is cheaper to build than any other approach',
            'It forces you to decide what matters most and avoids the "kitchen sink" problem',
          ],
          3,
          'Starting small forces careful selection of features. Large screens still need attention and should not just be scaled-up copies.',
          'concept'
        ),
        S(
          'Which pair of color and resolution terms is correct for print and digital media?',
          [
            'Print uses RGB and PPI; digital uses CMYK and DPI',
            'Print uses CMYK and DPI; digital uses RGB and PPI',
            'Both print and digital use CMYK and DPI',
            'Print uses Pantone only; digital uses CMYK only',
          ],
          1,
          'Print uses physical pigments (CMYK, DPI), while digital uses light-based colors (RGB, PPI). Digital colors also vary between screens.',
          'compare'
        ),
        S(
          'In the evolution of UX design, which decade is linked with mobile-first and responsive design, for example Bootstrap?',
          [
            '2020s',
            '2000s',
            '1990s',
            '2010s',
          ],
          3,
          'The 2000s focused on usability and web navigation, the 2010s on mobile-first and responsive design, and the 2020s on emotion, AI and accessibility.',
          'order'
        ),
        M(
          'Which trend and challenge pairs match the lecture? Select all that apply.',
          [
            'Voice UX: accents and background noise',
            'AI-driven personalization: data privacy and bias',
            'Dark mode: slow server response',
            'Immersive experiences: device compatibility and development cost',
          ],
          [0, 1, 3],
          'The dark mode challenge is accessibility and contrast balance, not server speed.',
          'multi'
        ),
        M(
          'Which statements about print media are correct? Select all that apply.',
          [
            'It cannot be changed once it is printed',
            'Its engagement is measured through analytics',
            'It appeals to touch, smell and vision',
            'It uses CMYK colors',
          ],
          [0, 2, 3],
          'Print is static and tangible. Measurable engagement through analytics is a feature of digital media.',
          'multi'
        ),
        M(
          'Which UX profession and role pairs are correct? Select all that apply.',
          [
            'Information architect: creates sitemaps and navigation systems',
            'UX writer: writes labels, buttons and error messages',
            'Visual designer: runs usability tests with users',
            'Accessibility specialist: ensures compliance with standards such as WCAG',
          ],
          [0, 1, 3],
          'Visual designers work on aesthetics such as graphics and branding. Usability testing is the work of usability analysts and researchers.',
          'multi'
        ),
        M(
          'Which are good tips for building an effective design portfolio? Select all that apply.',
          [
            'Select your best work and favor quality over quantity',
            'Include every project you have ever done',
            'Keep the portfolio updated regularly',
            'Explain your role, the challenges and your solutions',
          ],
          [0, 2, 3],
          'A portfolio should show your best work with context. Showing everything weakens it because quality matters more than quantity.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'What does the "core user experience" of a product mean?',
          [
            'The most colorful screens of the product',
            'The list of all features ever requested by stakeholders',
            'The essential features and content that must work on every device or channel',
            'The version of the product made only for desktop users',
          ],
          2,
          'The core experience is the key features plus content that solves the main problem, such as requesting a ride on Uber. It must be supported on every device.',
          'concept'
        ),
        D(
          'Which device context is known as "the 10-foot experience"?',
          [
            'Television screens',
            'Smartwatches',
            'Tablets',
            'Desktop monitors',
          ],
          0,
          'From the couch, elements on a TV look smaller than on a desktop screen, so TV design needs its own approach and not just a scaled-up layout.',
          'concept'
        ),
        D(
          'Which item is a communication skill rather than an element of team dynamics?',
          [
            'Shared goals',
            'Leadership',
            'Decision-making',
            'Active listening',
          ],
          3,
          'Active listening is listed under communication, together with verbal, written and nonverbal communication and feedback. Shared goals, leadership and decision-making are team dynamics.',
          'compare'
        ),
      ],
    },
  },
};
