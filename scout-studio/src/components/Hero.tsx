import { sceneBridge } from '../scene/bridge';
import { ChainBadge } from './ChainBadge';
import { Icon } from './Icons';
import { SubjectStage } from './SubjectControls';

export function Hero({ onMemo, onRun, live }: { onMemo: () => void; onRun: () => void; live: boolean }) {
  return <section className="hero" id="top" aria-labelledby="hero-title">
    <div className="shell hero-grid">
      <div className="hero-copy" ref={sceneBridge.slot('heroCopy')}>
        <ChainBadge className="enter" />
        <h1 id="hero-title" className="hero-title enter" style={{ '--i': 1 } as React.CSSProperties}>
          <span><span className="nowrap">Evidence-first</span> research</span>{' '}
          <span>for Robinhood <em>Chain.</em></span>
        </h1>
        <p className="hero-lede enter" style={{ '--i': 2 } as React.CSSProperties}>
          Stock-paired tokens borrow familiar names. Stock Scout checks each one against on-chain data and public sources, and shows what is proven, what is risky and what is still unverified.
        </p>
        <div className="hero-actions enter" style={{ '--i': 3 } as React.CSSProperties}>
          <button type="button" className="btn btn-primary btn-lg" onClick={onMemo}>See a sample memo <Icon name="arrow" size={18} /></button>
          <button type="button" className="btn btn-ghost btn-lg" onClick={onRun}>{live ? 'Run Scout' : 'Try the demo'} <Icon name="play" size={13} /></button>
        </div>
        <p className="hero-trust enter" style={{ '--i': 4 } as React.CSSProperties}>
          <Icon name="shield" size={15} /> Research only. No trading, no wallet spending.
        </p>
      </div>
      <SubjectStage />
    </div>
  </section>;
}
