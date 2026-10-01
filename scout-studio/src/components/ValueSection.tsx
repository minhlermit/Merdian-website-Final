const BENEFITS = [
  {
    n: '01', title: 'Signals, not listings.',
    body: 'Every six hours the Scout compares public market snapshots of stock-paired pools. A new pool or a meaningful change becomes an event; unchanged noise stops the cycle.',
    source: 'scout_cycle.py · discover.py',
  },
  {
    n: '02', title: 'Claims need sources.',
    body: 'On-chain checks and a claim ledger test the pair, pool depth, holders and contract permissions. A project story stays a claim until evidence supports it.',
    source: 'onchain.py · ledger.py',
  },
  {
    n: '03', title: 'Rules the prose can’t bend.',
    body: 'A fixed scorecard and exit-risk floor come from the Python core. Investor memos only run after research is marked complete, and the writer cannot upgrade a rating.',
    source: 'run_report.py · completion gate',
  },
];

export function ValueSection({ sectionRef }: { sectionRef: React.Ref<HTMLElement> }) {
  return <section className="value-section" id="product" ref={sectionRef} aria-labelledby="value-title">
    <div className="shell">
      <div className="section-head" data-reveal>
        <p className="label">Product</p>
        <h2 id="value-title">Built for evidence,<br />not excitement.</h2>
        <p className="section-lede">A research interface for Robinhood Chain stock-paired tokens. It explains what changed, what is proven and what is still a claim. It does not trade, and it is not investment advice.</p>
      </div>
      <div className="value-grid">
        {BENEFITS.map((b, i) => <article className="value-card" key={b.n} data-reveal style={{ '--i': i } as React.CSSProperties}>
          <span className="value-num mono">{b.n}</span>
          <h3>{b.title}</h3>
          <p>{b.body}</p>
          <span className="value-source mono">{b.source}</span>
        </article>)}
      </div>
    </div>
  </section>;
}
