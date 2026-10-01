import { Icon } from './Icons';

// A fictional memo built from the AURA demo candidate, so the example matches what the console shows.
const EVIDENCE: [string, 'verified' | 'unconfirmed', string][] = [
  ['Verified on-chain', 'verified', 'Pool and NVDA pair observed in the market snapshot'],
  ['Verified on-chain', 'verified', 'Top 10 wallets hold 29.4% of supply across 1,682 holders'],
  ['Unconfirmed', 'unconfirmed', 'Creator adoption claim has no independent source yet'],
];
const OPEN = [
  'Product activity has not been verified.',
  'A stock pair does not mean ownership of the stock.',
  'Liquidity can leave quickly, so exit risk stays at medium.',
];

export function SampleMemo({ sectionRef, canOpen, onOpen, onConsole }: {
  sectionRef: React.Ref<HTMLElement>; canOpen: boolean; onOpen: () => void; onConsole: () => void;
}) {
  return <section className="memo-section" id="memo" ref={sectionRef} aria-labelledby="memo-title">
    <div className="shell memo-grid">
      <div className="memo-intro" data-reveal>
        <p className="label">What you get</p>
        <h2 id="memo-title">A memo that shows its work.</h2>
        <p className="section-lede">Each candidate ends in a short research memo: what changed, which evidence supports it and which risks are still open. This example is fictional.</p>
        <div className="memo-actions">
          <button type="button" className="btn btn-primary" onClick={onOpen}>{canOpen ? 'Open the full research file' : 'Replay the demo'} <Icon name="arrowUp" size={15} /></button>
          <button type="button" className="text-link" onClick={onConsole}>Go to the candidate board <Icon name="arrow" size={15} /></button>
        </div>
      </div>

      <article className="memo-card" data-reveal style={{ '--i': 1 } as React.CSSProperties} aria-label="Sample research memo for a fictional token">
        <header className="memo-head">
          <div>
            <p className="memo-kicker">Research memo · Fictional example</p>
            <h3>AURA <span>paired with NVDA</span></h3>
          </div>
          <dl className="memo-verdict">
            <div><dt>Rating</dt><dd>Research</dd></div>
            <div><dt>Score</dt><dd className="tabular">21 / 30</dd></div>
            <div><dt>Exit risk</dt><dd><span className="memo-risk">Medium</span></dd></div>
          </dl>
        </header>
        <div className="memo-body">
          <section>
            <h4><span className="memo-num">1</span>What changed</h4>
            <p>24-hour volume rose against the previous snapshot, and pool liquidity climbed to about $318k over the last thirteen snapshots.</p>
          </section>
          <section>
            <h4><span className="memo-num">2</span>What supports it</h4>
            <ul className="memo-evidence">
              {EVIDENCE.map(([level, tone, text]) => <li key={text}><span className={`memo-level is-${tone}`}>{level}</span>{text}</li>)}
            </ul>
          </section>
          <section>
            <h4><span className="memo-num">3</span>What is still open</h4>
            <ul className="memo-open">{OPEN.map(text => <li key={text}>{text}</li>)}</ul>
          </section>
        </div>
        <footer className="memo-foot">
          <span>Score and exit-risk floor come from fixed rules, not the writer.</span>
          <span>Illustration · not live data</span>
        </footer>
      </article>
    </div>
  </section>;
}
