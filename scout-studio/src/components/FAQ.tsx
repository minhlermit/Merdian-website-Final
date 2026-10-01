const QUESTIONS: [string, string][] = [
  ['What happens at the six-hour reset?', 'The candidate board follows UTC windows starting at 00:00, 06:00, 12:00 and 18:00. When a new window starts, this browser clears the board and any imported snapshot from the previous window, so stale research is never shown as current.'],
  ['Does a reset mean new research ran?', 'No. A reset only clears what this page shows. New candidates appear when the local Scout runs a cycle, or when you import a fresh export from a machine that ran it in the current window. The static website cannot run the Python pipeline on its own.'],
  ['What is the difference between Run demo and Run Scout?', 'On the hosted site, Run demo plays a guided walkthrough with clearly labelled fictional candidates. With the local bridge running on your computer, the button becomes Run Scout and starts the original research cycle, which may take several minutes when a signal needs investigation.'],
  ['Where do scores and risk levels come from?', 'From the Python research core: a fixed scorecard, an exit-risk floor and a completion gate. The interface only displays those results. The memo writer cannot improve a rating with persuasive prose.'],
  ['Is the demo data real?', 'No. Demo candidates, names and numbers are invented and labelled as a fictional scenario. Real data only appears from your own local Scout or an export you import.'],
  ['Is MC live? Can I buy it?', 'Not yet. MC plans, quotes and burns are a product concept. There is no token contract, payment, balance or entitlement in this preview.'],
  ['What does connecting a wallet do?', 'It shows your public address to this page and can ask for a readable sign-in signature, verified in this browser only. It cannot move funds or approve tokens, and there is no server session or premium access yet.'],
];

export function FAQ({ sectionRef }: { sectionRef: React.Ref<HTMLElement> }) {
  return <section className="faq-section" id="faq" ref={sectionRef} aria-labelledby="faq-title">
    <div className="shell faq-grid">
      <div className="section-head" data-reveal>
        <p className="label">FAQ</p>
        <h2 id="faq-title">Straight answers.</h2>
        <p className="section-lede">How research, resets and the concept features behave in this preview.</p>
      </div>
      <div className="faq-list" data-reveal>
        {QUESTIONS.map(([q, a]) => <details key={q}><summary>{q}<span className="faq-icon" aria-hidden="true" /></summary><p>{a}</p></details>)}
      </div>
    </div>
  </section>;
}
