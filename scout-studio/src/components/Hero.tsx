import { sceneBridge } from '../scene/bridge';
import { Icon } from './Icons';
import { SubjectStage } from './SubjectControls';

export function Hero({ onStory, onConsole }: { onStory: () => void; onConsole: () => void }) {
  return <section className="hero" id="top" aria-labelledby="hero-title">
    <div className="shell hero-grid">
      <div className="hero-copy" ref={sceneBridge.slot('heroCopy')}>
        <p className="eyebrow"><span className="live-dot" aria-hidden="true" /> Research studio · Robinhood Chain</p>
        <h1 id="hero-title" className="hero-title enter" style={{ '--i': 1 } as React.CSSProperties}>
          <span>Follow the signal.</span>
          <span>Keep the <em>proof.</em></span>
        </h1>
        <p className="hero-lede enter" style={{ '--i': 2 } as React.CSSProperties}>
          Stock Scout watches stock-paired tokens, turns meaningful changes into signals and checks each claim against evidence before a memo is written.
        </p>
        <div className="hero-actions enter" style={{ '--i': 3 } as React.CSSProperties}>
          <button type="button" className="btn btn-primary btn-lg" onClick={onStory}>See how it works <Icon name="arrow" size={18} /></button>
          <button type="button" className="btn btn-ghost btn-lg" onClick={onConsole}>Open the console <Icon name="arrowUp" size={16} /></button>
        </div>
        <ul className="hero-facts enter" style={{ '--i': 4 } as React.CSSProperties} aria-label="Key facts">
          <li><span className="mono">06H</span> Board resets at UTC 00, 06, 12, 18</li>
          <li><span className="mono">5</span> Evidence levels on every claim</li>
          <li><span className="mono">0</span> Trading or wallet spending</li>
        </ul>
      </div>
      <SubjectStage />
    </div>
  </section>;
}
