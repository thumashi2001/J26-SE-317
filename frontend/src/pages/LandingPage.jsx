import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle.jsx';
import Logo from '../components/Logo.jsx';
import LaptopScene from '../components/LaptopScene.jsx';
import JoinScene from '../components/JoinScene.jsx';
import { TOPIC_INFO } from '../utils/topicLabels.js';
import './landing.css';

const NAV = [
  { href: '#how', label: 'How it works' },
  { href: '#modules', label: 'Your modules' },
  { href: '#features', label: 'Digital twin' },
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

const EXPLORE = ['what you know', 'what you forget', 'how you answer', 'what to study next', 'your exam forecast'];

// Swaps the highlighted words under the "join us" heading. Stays on the first phrase for reduced motion.
function useRotatingWord(list, ms = 2600) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    const id = setInterval(() => setI((n) => (n + 1) % list.length), ms);
    return () => clearInterval(id);
  }, [list.length, ms]);
  return { word: list[i], i };
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
  const { word, i: wordI } = useRotatingWord(EXPLORE);
  const topicCount = Object.keys(TOPIC_INFO).length;
  const moduleCount = new Set(Object.values(TOPIC_INFO).map((t) => t.module)).size;

  const list = Object.values(modules[sem] || {});

  return (
    <div className="lp">
      <a className="lp-skip" href="#main">Skip to content</a>

      <header className="lp-nav">
        <div className="lp-wrap lp-nav-in">
          <Link to="/" className="lp-brand" aria-label="AdaptiveLearnSE home"><Logo size={38} onDark /></Link>
          <nav className={'lp-links' + (open ? ' open' : '')} aria-label="Main">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} onClick={() => setOpen(false)}>{n.label}</a>
            ))}
          </nav>
          <div className="lp-nav-cta">
            <ThemeToggle onDark />
            <button type="button" className="lp-burger" aria-expanded={open} aria-label="Menu" onClick={() => setOpen(!open)}>
              <span /><span /><span />
            </button>
          </div>
        </div>
      </header>

      <main id="main">
        {/* join us */}
        <section className="lp-join" aria-labelledby="lp-join-title">
          <div className="lp-wrap lp-join-in">
            <div className="lp-join-text">
              <p className="lp-join-kicker"><span className="lp-dot" /> Calling all SLIIT 3rd year Software Engineering students</p>
              <h2 id="lp-join-title">Are you a SLIIT 3rd year Software Engineering student?<br /><span>Join us and let&rsquo;s explore the world of learning.</span></h2>
              <p className="lp-join-line">
                Together we will look at <b key={wordI} className="lp-swap">{word}</b>
              </p>
              <ul className="lp-join-facts">
                <li><strong>{moduleCount}</strong> modules</li>
                <li><strong>{topicCount}</strong> topics</li>
                <li><strong>2</strong> semesters</li>
              </ul>
              <div className="lp-hero-cta">
                <Link className="lp-btn solid big" to="/register">Get started</Link>
                <Link className="lp-btn light big" to="/login">I already have an account</Link>
              </div>
            </div>
            <div className="lp-join-art"><JoinScene /></div>
          </div>
        </section>

        {/* how it works */}
        <section id="how" className="lp-sec">
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

        {/* hero */}
        <section className="lp-hero">
          <div className="lp-wrap lp-hero-in">
            <div className="lp-hero-text">
              <h1>Know what you know.<br /><span>Learn what matters next.</span></h1>
              <p className="lp-lead">
                AdaptiveLearnSE joins four tools in one place: a digital twin of what you know, exam intelligence, automated marking and an adaptive learning path.
              </p>
            </div>

            <div className="lp-hero-art">
              <div className="lp-art-card"><LaptopScene /></div>
            </div>
          </div>
        </section>

        {/* modules */}
        <section id="modules" className="lp-sec alt">
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
        <section id="features" className="lp-sec">
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

      </main>

      <footer className="lp-foot">
        <div className="lp-wrap lp-foot-in">
          <div>
            <Logo size={36} onDark />
            <p>A student research project (2026), specialised for SLIIT Year 3 Software Engineering students. It is not an official SLIIT service.</p>
          </div>
          <nav aria-label="Footer">
            {NAV.map((n) => <a key={n.href} href={n.href}>{n.label}</a>)}
          </nav>
        </div>
      </footer>
    </div>
  );
}
