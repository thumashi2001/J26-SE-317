import { useState } from 'react';
import { Link } from 'react-router-dom';
import Celebration from '../../components/Celebration.jsx';

// Developer page (only built into the dev server): press a button to see the celebration again.
export default function CelebratePreview() {
  const [show, setShow] = useState(null); // { perfect, n }
  const play = (perfect) => setShow({ perfect, n: Date.now() });
  return (
    <div className="panel">
      <h1>Celebration preview</h1>
      <p className="muted">This page only exists while you run the dev server. Press a button to play the effect. It lasts about 5 seconds.</p>
      <div className="row" style={{ justifyContent: 'flex-start', gap: 12 }}>
        <button className="btn" onClick={() => play(false)}>Play fireworks (5 or 6 of 7)</button>
        <button className="btn secondary" onClick={() => play(true)}>Play perfect score (7 of 7)</button>
      </div>
      <p className="muted small">If nothing shows, your computer may have "reduce motion" turned on, and the effect is skipped on purpose.</p>
      <Link to="/c1/dashboard">Back to my learning state</Link>
      {show && <Celebration key={show.n} perfect={show.perfect} />}
    </div>
  );
}
