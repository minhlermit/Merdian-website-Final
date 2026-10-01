import { useEffect, useState } from 'react';
import { sceneBridge, useSceneStatus } from '../scene/bridge';
import { Icon } from './Icons';
import { useSubjectDrag } from './SubjectControls';

const chapters = [
  { n: '01', tag: 'Discover', title: 'A new pool appears.', body: 'On a machine you control, the research engine checks stock-paired pools every six hours. It compares snapshots, so only a meaningful change becomes a signal.', output: 'Pool → snapshot → event', signal: 'New stock-paired pool' },
  { n: '02', tag: 'Verify', title: 'The pair gets checked.', body: 'On-chain data tests the stock pair, pool depth, holders and contract permissions. A project’s story stays a claim until evidence supports it.', output: 'Claim → source → confidence', signal: 'Verified on-chain' },
  { n: '03', tag: 'Investigate', title: 'Only signals use AI.', body: 'If nothing important changed, the cycle stops. When something did, focused research looks at the creator, product, incentives and risks.', output: 'Signal → research queue', signal: 'Evidence packet ready' },
  { n: '04', tag: 'Evaluate', title: 'The rules hold the line.', body: 'A fixed scorecard and an exit-risk floor set the rating. Persuasive writing cannot raise it, and no memo is written until research is complete.', output: 'Score → risk floor → gate', signal: 'Research complete' },
  { n: '05', tag: 'Deliver', title: 'One report. Clear reasons.', body: 'Memos and a comparison board land in one report, showing what supports each conclusion and what remains unverified.', output: 'Candidates → investor memo', signal: 'Ready to explore' },
];

// Where each stage runs in the research core, for readers who want the technical detail.
const UNDER_THE_HOOD: [string, string, string][] = [
  ['Discover', 'scout_cycle.py · discover.py', 'Six-hour market snapshots and event detection.'],
  ['Verify', 'onchain.py · ledger.py', 'Pair, pool, holder and permission checks; the claim ledger.'],
  ['Investigate', 'context.py → research agents', 'Runs only for new signals and skips unchanged evidence.'],
  ['Evaluate', 'run_report.py · completion gate', 'Scorecard, exit-risk floor and the memo gate.'],
  ['Deliver', 'latest.html', 'The comparison board and investor memos in one file.'],
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
          <p>A research pipeline, not a trading bot. Five stages sit between a new token appearing and a memo you can inspect.</p>
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
        </li>)}
      </ol>
    </div>

    <div className="shell">
      <details className="tech-detail" data-reveal>
        <summary>Technical detail: where each stage runs <span className="faq-icon" aria-hidden="true" /></summary>
        <dl>
          {UNDER_THE_HOOD.map(([stage, files, note]) => <div key={stage}><dt>{stage}</dt><dd><code>{files}</code><span>{note}</span></dd></div>)}
        </dl>
      </details>
      <div className="story-finale" data-reveal>
        <div>
          <p className="label">Now you know what Run means</p>
          <h3>Curiosity is good.<br />Evidence is better.</h3>
          <p>{live ? 'Start a real Scout cycle on this machine through the local bridge.' : 'The hosted site cannot run the research engine, so Run plays a fictional walkthrough. Then inspect the candidate board.'}</p>
        </div>
        <div className="finale-actions">
          <button type="button" className="btn btn-primary btn-lg" onClick={onRun}>{live ? 'Run Scout now' : 'Run the demo'} <Icon name="play" size={14} /></button>
          <button type="button" className="btn btn-ghost btn-lg" onClick={onConsole}>View candidates <Icon name="arrow" size={17} /></button>
        </div>
      </div>
    </div>
  </section>;
}
