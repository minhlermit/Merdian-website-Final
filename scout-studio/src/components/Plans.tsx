import { Icon } from './Icons';

const PLANS = [
  { name: 'Explorer', kind: 'Public board', mc: 'Free', unit: '', body: 'Six-hour candidate rotation, open evidence and the guided Scout demo.', cta: 'Explore candidates', featured: false },
  { name: 'Researcher', kind: 'Premium concept', mc: '300', unit: 'MC / month', body: 'Concept allocation for targeted jobs, deeper investigations and memo history.', cta: 'Get MC', featured: true },
  { name: 'Studio', kind: 'Team concept', mc: '1,200', unit: 'MC / month', body: 'Concept allocation for shared research, batch work and collaborative review.', cta: 'Explore plans', featured: false },
];

const ROWS: [string, boolean, boolean, boolean][] = [
  ['Six-hour public candidate board', true, true, true],
  ['Evidence ledger and risk flags', true, true, true],
  ['Guided Scout demo', true, true, true],
  ['Targeted research jobs (quoted in MC)', false, true, true],
  ['Memo and evidence history', false, true, true],
  ['Shared allocation and batch work', false, false, true],
];

export function Plans({ sectionRef, onConsole, onGetMC }: { sectionRef: React.Ref<HTMLElement>; onConsole: () => void; onGetMC: () => void }) {
  return <section className="plans-section" id="mc" ref={sectionRef} aria-labelledby="plans-title">
    <div className="shell">
      <div className="section-head" data-reveal>
        <p className="label">MC plans · concept</p>
        <h2 id="plans-title">More depth,<br />on your terms.</h2>
        <p className="section-lede">Reading the public board stays free. A premium subscription could grant MC for focused research, with the cost shown before each command. Nothing here charges, mints or burns yet.</p>
      </div>
      <div className="plan-cards">
        {PLANS.map((p, i) => <article key={p.name} className={`plan ${p.featured ? 'is-featured' : ''}`} data-reveal style={{ '--i': i } as React.CSSProperties}>
          <p className="plan-kind label">{p.kind}</p>
          <h3>{p.name}</h3>
          <p className="plan-price"><strong>{p.mc}</strong>{p.unit && <span>{p.unit}</span>}</p>
          <p className="plan-body">{p.body}</p>
          <button type="button" className={`btn ${p.featured ? 'btn-primary' : 'btn-ghost'}`} onClick={p.name === 'Explorer' ? onConsole : onGetMC}>{p.cta} <Icon name="arrowUp" size={15} /></button>
        </article>)}
      </div>
      <div className="plan-compare" data-reveal>
        <table>
          <caption className="sr-only">Plan comparison (concept)</caption>
          <thead><tr><th scope="col">Included</th>{PLANS.map(p => <th scope="col" key={p.name}>{p.name}</th>)}</tr></thead>
          <tbody>{ROWS.map(([label, ...cells]) => <tr key={label}><th scope="row">{label}</th>{cells.map((on, i) => <td key={i}>{on ? <><Icon name="check" size={16} /><span className="sr-only">Included</span></> : <><span aria-hidden="true">—</span><span className="sr-only">Not included</span></>}</td>)}</tr>)}</tbody>
        </table>
      </div>
      <div className="plan-note" data-reveal>
        <p className="label">MC / command economy</p>
        <p>Quote → confirm → run → verify → burn MC. When MC runs out, a user could choose a wallet top-up and confirm its cost. Prices, payments, balances and burns are not active in this preview.</p>
        <button type="button" className="text-link" onClick={onGetMC}>View usage concept <Icon name="arrow" size={15} /></button>
      </div>
    </div>
  </section>;
}
