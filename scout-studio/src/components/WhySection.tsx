import { ChainBadge } from './ChainBadge';

const PROBLEMS = [
  {
    n: '01', problem: 'Token information is scattered.',
    answer: 'Pool depth, holders, contract permissions and project posts sit in different places. Scout gathers them into one research file per candidate.',
  },
  {
    n: '02', problem: 'A pitch is easy to mistake for proof.',
    answer: 'A project’s own announcement can read like evidence. Scout keeps it labelled as a claim until an on-chain or independent source supports it.',
  },
  {
    n: '03', problem: 'What is unverified gets lost.',
    answer: 'Open questions rarely make the headline. Every memo lists unconfirmed claims and risks next to the findings, and the rating comes from fixed rules.',
  },
];

export function WhySection({ sectionRef }: { sectionRef: React.Ref<HTMLElement> }) {
  return <section className="why-section" id="why" ref={sectionRef} aria-labelledby="why-title">
    <div className="shell">
      <div className="section-head" data-reveal>
        <p className="label">Why we built Stock Scout</p>
        <h2 id="why-title">Research should show its sources.</h2>
        <p className="section-lede">We wanted one place to check sources, risks and what has not been verified yet, before anyone forms a view. Stock Scout does not trade, and it is not investment advice.</p>
      </div>
      <ol className="why-list">
        {PROBLEMS.map((p, i) => <li className="why-item" key={p.n} data-reveal style={{ '--i': i } as React.CSSProperties}>
          <span className="why-num tabular">{p.n}</span>
          <h3>{p.problem}</h3>
          <p>{p.answer}</p>
        </li>)}
      </ol>
      <div className="why-chain" data-reveal>
        <ChainBadge />
        <div>
          <h3>Why Robinhood Chain?</h3>
          <p>Stock-paired tokens borrow the name of a company people already know. That borrowed credibility is where careful research matters most: a pair with NVDA or TSLA does not mean you own the stock, and a young network has few independent tools that check the difference. We start where the gap between a familiar name and real evidence is widest.</p>
        </div>
      </div>
    </div>
  </section>;
}
