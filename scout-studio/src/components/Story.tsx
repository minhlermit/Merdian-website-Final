import { useEffect, useState } from 'react';
import { sceneBridge, useSceneStatus } from '../scene/bridge';
import { Icon } from './Icons';
import { useSubjectDrag } from './SubjectControls';

const chapters = [
  { n: '01', tag: 'Discover', title: 'A new pool appears.', body: 'Every six hours the Scout checks public market data for stock-paired tokens. It compares snapshots, so a meaningful change becomes a signal instead of another noisy listing.', code: 'scout_cycle.py', output: 'Pool → snapshot → event', signal: 'New stock-paired pool' },
  { n: '02', tag: 'Verify', title: 'The pair gets checked.', body: 'On-chain data and a claim ledger test the stock pair, pool depth, holders and contract permissions. A project’s story remains a claim until evidence supports it.', code: 'onchain.py + ledger.py', output: 'Claim → source → confidence', signal: 'Verified on-chain' },
  { n: '03', tag: 'Investigate', title: 'Only signals use AI.', body: 'If nothing important changed, the cycle stops. When there is a signal, specialised research looks at the creator, product, incentives and risks without rereading unchanged evidence.', code: 'context.py → research agents', output: 'Signal → research queue', signal: 'Evidence packet ready' },
  { n: '04', tag: 'Evaluate', title: 'The rules hold the line.', body: 'A fixed scorecard and exit-risk floor come from the Python core. The writer cannot improve a rating with persuasive prose. The final memo runs only after research is marked complete.', code: 'run_report.py / completion gate', output: 'Score → risk floor → gate', signal: 'Research complete' },
  { n: '05', tag: 'Deliver', title: 'One report. Clear reasons.', body: 'A comparison board and investor memos land in one HTML report. You can inspect what supports each conclusion, what remains unverified and what could change the thesis.', code: 'latest.html', output: 'Candidates → investor memo', signal: 'Ready to explore' },
];

export function Story({ onRun, onConsole, live, sectionRef }: { onRun: () => void; onConsole: () => void; live: boolean; sectionRef: React.Ref<HTMLElement> }) {
  const [active, setActive] = useState(0);
  const status = useSceneStatus();
  const drag = useSubjectDrag();

  useEffect(() => {
    const elements = sceneBridge.chapters.filter((el): el is HTMLElement => Boolean(el));
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActive(Number((visible.target as HTMLElement).dataset.step || 0));
    }, { threshold: [0.3, 0.6], rootMargin: '-35% 0px -35% 0px' });
    elements.forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const goTo = (i: number) => sceneBridge.chapters[i]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  const step = chapters[active];

  return <section className="story-section" id="story" ref={sectionRef} aria-labelledby="story-title">
    <div className="shell">
      <div className="section-head story-head" data-reveal>
        <p className="label">How it works</p>
        <h2 id="story-title">Before the verdict,<br />follow the trail.</h2>
        <div className="section-lede">
          <p>The engine is a research pipeline, not a trading bot. Five stages sit between a new token appearing and a memo you can inspect.</p>
          <button type="button" className="text-link" onClick={onConsole}>Skip to the console <Icon name="arrow" size={15} /></button>
        </div>
      </div>
    </div>

    <div className="shell story-grid">
      <div className="story-stage" ref={sceneBridge.slot('storyAnchor')} {...drag}>
        {status === 'fallback' && <img className="story-poster" src="/assets/signal-orbit-3d.png" alt="" />}
        <div className="story-overlay">
          <div className="story-overlay-top"><span className="mono">{step.n} / 05</span><span className="mono">{step.tag}</span></div>
          <div className="story-readout" key={active}>
            <span className="mono tag-line">{step.signal}</span>
            <strong>{step.output}</strong>
            <code>$ {step.code}</code>
          </div>
          <div className="story-dots" role="group" aria-label="Story chapters">
            {chapters.map((c, i) => <button key={c.n} type="button" className={i === active ? 'is-active' : ''} aria-label={`Go to chapter ${c.n}, ${c.tag}`} aria-current={i === active ? 'step' : undefined} onClick={() => goTo(i)}><i /></button>)}
          </div>
          <span className="story-note mono">Illustration · not live market data</span>
        </div>
      </div>

      <ol className="story-chapters" ref={sceneBridge.slot('storyText')}>
        {chapters.map((c, i) => <li key={c.n} ref={sceneBridge.chapter(i)} data-step={i} className={`story-chapter ${i === active ? 'is-active' : ''}`}>
          <p className="chapter-meta"><span className="mono">{c.n}</span><span className="label">{c.tag}</span></p>
          <h3>{c.title}</h3>
          <p>{c.body}</p>
          <p className="chapter-code mono">{c.code}</p>
        </li>)}
      </ol>
    </div>

    <div className="shell">
      <div className="story-finale" data-reveal>
        <div>
          <p className="label">Now you know what Run means</p>
          <h3>Curiosity is good.<br />Evidence is better.</h3>
          <p>{live ? 'Start a real Scout cycle on this machine through the local bridge.' : 'Try the guided demo first, then inspect the candidate board. The hosted preview does not call live chain APIs.'}</p>
        </div>
        <div className="finale-actions">
          <button type="button" className="btn btn-primary btn-lg" onClick={onRun}>{live ? 'Run Scout now' : 'Run the demo'} <Icon name="play" size={14} /></button>
          <button type="button" className="btn btn-ghost btn-lg" onClick={onConsole}>View candidates <Icon name="arrow" size={17} /></button>
        </div>
      </div>
    </div>
  </section>;
}
