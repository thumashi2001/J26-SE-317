import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle.jsx';
import BrandMark from '../components/BrandMark.jsx';
import StudentsArt from '../components/StudentsArt.jsx';
import { TOPIC_INFO } from '../utils/topicLabels.js';
import './landing.css';

const NAV = [
  { href: '#components', label: 'Four components' },
  { href: '#how', label: 'How it works' },
  { href: '#modules', label: 'Your modules' },
  { href: '#features', label: 'Digital twin' },
];

// The four parts of AdaptiveLearnSE, one for each member of the research team.
const COMPONENTS = [
  {
    id: 'C1', icon: '\u{1F9E0}', tone: 'green', title: 'Cognitive Digital Twin',
    text: 'A live score for every topic. It fades like real memory and rises again when you practise.',
    points: ['Diagnostic test for each semester', 'Forgetting curve and early alerts', 'What if I study forecasts'],
  },
  {
    id: 'C2', icon: '\u{1F4C4}', tone: 'blue', title: 'Exam Intelligence',
    text: 'Reads question papers, rubrics and exam patterns, so you know what exams really ask.',
    points: ['Past paper questions sorted by topic', 'Exam structure and patterns', 'Rubrics explained clearly'],
  },
  {
    id: 'C3', icon: '\u2705', tone: 'amber', title: 'Automated Marking',
    text: 'Marks your answers and gives feedback you can learn from, with lecturers able to review.',
    points: ['Quick marks against a rubric', 'Clear feedback on every answer', 'Lecturer review of results'],
  },
  {
    id: 'C4', icon: '\u{1F6E4}\uFE0F', tone: 'violet', title: 'Adaptive Learning Path',
    text: 'Turns your twin into a study plan: what to learn next, and in what order.',
    points: ['Plans based on your weak topics', 'Updates as your scores change', 'Short steps toward the exam'],
  },
];

const STEPS = [
  { icon: '\u{1F9ED}', tag: 'Digital Twin', title: 'Find where you stand', text: 'Take one short diagnostic. Your twin keeps a score for every topic in your semester.' },
  { icon: '\u{1F4C4}', tag: 'Exam Intelligence', title: 'Learn what exams ask', text: 'See how past papers and rubrics are built, and which topics come up most.' },
  { icon: '\u2705', tag: 'Automated Marking', title: 'Check your answers', text: 'Get your answers marked with feedback that says what to fix.' },
  { icon: '\u{1F6E4}\uFE0F', tag: 'Learning Path', title: 'Follow your path', text: 'Get a study plan that changes as your twin changes, right up to the exam.' },
];

const FEATURES = [
  { icon: '\u{23F3}', title: 'Forgetting curve', text: 'Scores fade the longer you wait. Your twin shows how much has faded, so you review at the right time.' },
  { icon: '\u{1F50D}', title: 'Your answer style', text: 'Fast and wrong? Slow but right? You get simple tips that match how you really answer.' },
  { icon: '\u{1F52E}', title: 'What if I study?', text: 'Pick how often you will study and see the forecast for each topic before you commit.' },
  { icon: '\u{1F514}', title: 'Early alerts', text: 'A sudden drop or a run of guesses raises a friendly alert, early enough to act.' },
  { icon: '\u{1F4A1}', title: 'Fair hints', text: 'A 50/50 hint is there when you are stuck, and it counts honestly toward your score.' },
  { icon: '\u{1F3C6}', title: 'Celebrate progress', text: 'Do well in a quiz and the screen lights up. Small wins keep you going.' },
];

// Group the real topics by semester and module.
function useModules() {
  return useMemo(() => {
    const bySem = {};
    for (const [key, t] of Object.entries(TOPIC_INFO)) {
      const sem = (bySem[t.semester] ||= {});
      const mod = (sem[t.module] ||= { code: t.module, name: t.moduleName, topics: [] });
      mod.topics.push({ key, label: t.label });
    }
    return bySem;
  }, []);
}

function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.lp-reveal');
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      els.forEach((e) => e.classList.add('in'));
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && (e.target.classList.add('in'), io.unobserve(e.target))),
      { threshold: 0.12 }
    );
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
}

export default function LandingPage() {
  const modules = useModules();
  const [sem, setSem] = useState('Y3S1');
  const [open, setOpen] = useState(false);
  useReveal();

  const list = Object.values(modules[sem] || {});

  return (
    <div className="lp">
      <a className="lp-skip" href="#main">Skip to content</a>

      <header className="lp-nav">
        <div className="lp-wrap lp-nav-in">
          <Link to="/" className="lp-brand" aria-label="AdaptiveLearnSE home"><BrandMark onDark /></Link>
          <nav className={'lp-links' + (open ? ' open' : '')} aria-label="Main">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} onClick={() => setOpen(false)}>{n.label}</a>
            ))}
          </nav>
          <div className="lp-nav-cta">
            <ThemeToggle onDark />
            <Link className="lp-btn ghost" to="/login">Log in</Link>
            <Link className="lp-btn solid" to="/register">Register</Link>
            <button type="button" className="lp-burger" aria-expanded={open} aria-label="Menu" onClick={() => setOpen(!open)}>
              <span /><span /><span />
            </button>
          </div>
        </div>
      </header>

      <main id="main">
        {/* hero */}
        <section className="lp-hero">
          <div className="lp-wrap lp-hero-in">
            <div className="lp-hero-text">
              <p className="lp-kicker">SLIIT Software Engineering, Year 3</p>
              <h1>Know what you know.<br /><span>Learn what matters next.</span></h1>
              <p className="lp-lead">
                AdaptiveLearnSE joins four tools in one place: a digital twin of what you know, exam intelligence, automated marking and an adaptive learning path.
              </p>
              <div className="lp-hero-cta">
                <Link className="lp-btn solid big" to="/register">Get started</Link>
                <Link className="lp-btn light big" to="/login">I already have an account</Link>
              </div>
            </div>

            <div className="lp-hero-art" aria-hidden="true">
              <div className="lp-art-card"><StudentsArt /></div>
              <div className="lp-float f1">
                <span className="lp-tag">Example</span>
                <svg viewBox="0 0 44 44" width="46" height="46"><circle cx="22" cy="22" r="18" fill="none" stroke="#e3e9ef" strokeWidth="5" /><circle cx="22" cy="22" r="18" fill="none" stroke="#0fa883" strokeWidth="5" strokeLinecap="round" strokeDasharray="88 113" transform="rotate(-90 22 22)" /></svg>
                <div><strong>78%</strong><small>Topic score</small></div>
              </div>
              <div className="lp-float f2">
                <span className="lp-tag">Example</span>
                <svg viewBox="0 0 120 44" width="96" height="36"><path d="M2 8 C30 10 50 30 118 38" fill="none" stroke="#c9d3dc" strokeWidth="2" strokeDasharray="4 4" /><path d="M2 8 L40 18 L40 6 L80 16 L80 4 L118 12" fill="none" stroke="#0fa883" strokeWidth="2.5" strokeLinejoin="round" /></svg>
                <div><strong>Review in time</strong><small>Beat the forgetting curve</small></div>
              </div>
              <div className="lp-float f3">
                <span className="lp-tag">Example</span>
                <span className="lp-emoji">{'\u{1F389}'}</span>
                <div><strong>Great work!</strong><small>6 of 7 correct</small></div>
              </div>
            </div>
          </div>
        </section>

        {/* four components */}
        <section id="components" className="lp-sec">
          <div className="lp-wrap">
            <p className="lp-eyebrow">One platform, four components</p>
            <h2>Everything you need for exam success</h2>
            <p className="lp-sub">Each part solves one problem. Together they follow you from your first test to the exam hall.</p>
            <div className="lp-comps">
              {COMPONENTS.map((c, i) => (
                <article key={c.id} className={'lp-comp lp-reveal ' + c.tone} style={{ transitionDelay: `${i * 70}ms` }}>
                  <div className="lp-comp-top">
                    <span className="lp-comp-icon" aria-hidden="true">{c.icon}</span>
                  </div>
                  <h3>{c.title}</h3>
                  <p>{c.text}</p>
                  <ul>{c.points.map((pt) => <li key={pt}>{pt}</li>)}</ul>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* how it works */}
        <section id="how" className="lp-sec alt">
          <div className="lp-wrap">
            <p className="lp-eyebrow">How it works</p>
            <h2>From first test to exam ready, in four steps</h2>
            <ol className="lp-steps">
              {STEPS.map((s, i) => (
                <li key={s.title} className="lp-step lp-reveal" style={{ transitionDelay: `${i * 70}ms` }}>
                  <span className="lp-step-n">{i + 1}</span>
                  <span className="lp-step-icon" aria-hidden="true">{s.icon}</span>
                  <span className="lp-step-tag">{s.tag}</span>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* modules */}
        <section id="modules" className="lp-sec">
          <div className="lp-wrap">
            <p className="lp-eyebrow">Your modules</p>
            <h2>Built from your own lecture slides</h2>
            <p className="lp-sub">Every question comes from the real slides of your modules, grouped into clear topics.</p>
            <div className="lp-tabs" role="tablist" aria-label="Semester">
              {['Y3S1', 'Y3S2'].map((s) => (
                <button key={s} role="tab" aria-selected={sem === s} className={'lp-tab' + (sem === s ? ' on' : '')} onClick={() => setSem(s)}>
                  Year 3 Semester {s === 'Y3S1' ? '1' : '2'}
                </button>
              ))}
            </div>
            <div className="lp-mods" role="tabpanel">
              {list.map((m) => (
                <article key={m.code} className="lp-mod">
                  <header>
                    <span className="lp-code">{m.code}</span>
                    <span className="lp-count">{m.topics.length} topics</span>
                  </header>
                  <h3>{m.name}</h3>
                  <ul>
                    {m.topics.slice(0, 4).map((t) => <li key={t.key}>{t.label}</li>)}
                    {m.topics.length > 4 && <li className="more">and {m.topics.length - 4} more</li>}
                  </ul>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* features */}
        <section id="features" className="lp-sec alt">
          <div className="lp-wrap">
            <p className="lp-eyebrow">Inside the Digital Twin</p>
            <h2>A study partner that learns about you</h2>
            <div className="lp-feats">
              {FEATURES.map((f, i) => (
                <article key={f.title} className="lp-feat lp-reveal" style={{ transitionDelay: `${(i % 3) * 70}ms` }}>
                  <span className="lp-feat-icon" aria-hidden="true">{f.icon}</span>
                  <h3>{f.title}</h3>
                  <p>{f.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* call to action */}
        <section className="lp-cta">
          <div className="lp-wrap lp-cta-in">
            <div>
              <h2>Ready to see where you stand?</h2>
              <p>Your first test takes about 15 to 20 minutes and builds your twin.</p>
            </div>
            <div className="lp-hero-cta">
              <Link className="lp-btn solid big" to="/register">Create my account</Link>
              <Link className="lp-btn light big" to="/login">Log in</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="lp-foot">
        <div className="lp-wrap lp-foot-in">
          <div>
            <BrandMark onDark />
            <p>A student research project (IT4010, 2026) for SLIIT Software Engineering students. It is not an official SLIIT service.</p>
          </div>
          <nav aria-label="Footer">
            {NAV.map((n) => <a key={n.href} href={n.href}>{n.label}</a>)}
            <Link to="/login">Log in</Link>
            <Link to="/register">Register</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
