import { useEffect, useState } from 'react';
import { Icon } from './Icons';

function useTypewriter(text: string, speed = 42, startDelay = 500) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    const timeout = setTimeout(() => {
      interval = setInterval(() => setCount(n => {
        if (n >= text.length) { clearInterval(interval); return n; }
        return n + 1;
      }), speed);
    }, startDelay);
    return () => { clearTimeout(timeout); clearInterval(interval); };
  }, [text, speed, startDelay]);
  return { displayed: text.slice(0, count), done: count >= text.length };
}

export function Hero({onExplore, onStory, onPlans, onAssets, onWallet, onGetMC, walletLabel}: {onExplore:()=>void; onStory:()=>void; onPlans:()=>void; onAssets:()=>void; onWallet:()=>void; onGetMC:()=>void; walletLabel:string}) {
  const [navOpen, setNavOpen] = useState(false);
  const [pointer, setPointer] = useState({x:0,y:0});
  const [ready, setReady] = useState(false);
  const line = useTypewriter('What deserves a closer look?');
  useEffect(() => { const id = setTimeout(() => setReady(true), 400); return () => clearTimeout(id); }, []);
  const scroll = (fn:()=>void) => { setNavOpen(false); fn(); };
  return <section className="hero" id="top" onPointerMove={event => {
    if (event.pointerType === 'touch') return;
    const r = event.currentTarget.getBoundingClientRect();
    setPointer({ x: ((event.clientX-r.left)/r.width-.5)*2, y: ((event.clientY-r.top)/r.height-.5)*2 });
  }}>
    <div className="hero-grid" aria-hidden="true" />
    <div className="hero-glow" aria-hidden="true" />
    <header className="nav wrap-wide">
      <button className="brand" onClick={() => window.scrollTo({top:0,behavior:'smooth'})} aria-label="Stock Scout Studio home">
        <span className="brand-mark"><span>S</span><i /></span>
        <span className="brand-word">stockscout<span className="brand-sup">®</span><small>RESEARCH STUDIO</small></span>
      </button>
      <nav className="desktop-links" aria-label="Main navigation">
        <button onClick={() => scroll(onStory)}>How it works</button><span>·</span>
        <button onClick={() => scroll(onExplore)}>The console</button><span>·</span>
        <button onClick={() => scroll(onPlans)}>MC plans</button>
      </nav>
      <div className="nav-actions"><button className="nav-get-mc" onClick={onGetMC}>Get MC <Icon name="arrowUp" size={14}/></button><button className="nav-wallet" onClick={onWallet}><Icon name="wallet" size={17}/><span>{walletLabel}</span></button></div>
      <button className="mobile-nav-toggle" onClick={() => setNavOpen(!navOpen)} aria-label={navOpen?'Close menu':'Open menu'} aria-expanded={navOpen}><Icon name={navOpen?'close':'menu'} size={25}/></button>
    </header>
    <div className={`mobile-menu ${navOpen?'is-open':''}`}>
      <button onClick={() => scroll(onStory)}>How it works <Icon name="arrowUp"/></button>
      <button onClick={() => scroll(onExplore)}>The console <Icon name="arrowUp"/></button>
      <button onClick={() => scroll(onPlans)}>MC plans <Icon name="arrowUp"/></button>
      <button onClick={() => scroll(onAssets)}>Asset lab <Icon name="arrowUp"/></button>
      <button onClick={() => scroll(onGetMC)}>Get MC <Icon name="arrowUp"/></button>
    </div>
    <div className="hero-main wrap-wide">
      <div className="hero-copy">
        <div className="eyebrow"><span className="live-dot"/> ROBINHOOD CHAIN / RESEARCH INTERFACE <span className="eyebrow-index">01—05</span></div>
        <h1>Follow the <em>signal.</em><br/>Keep the proof<span className="period">.</span></h1>
        <div className="hero-lede"><span className="lede-line"/><p>One signal becomes a trail of proof. Follow the research engine before you run it.</p></div>
        <div className="hero-prompt"><span className="prompt-prefix">SCOUT /</span><span>{line.displayed}</span>{!line.done&&<span className="cursor" aria-hidden="true"/>}</div>
        <div className={`hero-actions ${ready?'visible':''}`}>
          <button className="button-primary" onClick={onStory}>See how it works <Icon name="arrowUp" size={18}/></button>
          <button className="button-outline" onClick={onExplore}>Explore candidates <Icon name="arrow" size={18}/></button>
        </div>
      </div>
      <div className="hero-art" style={{'--pointer-x':pointer.x,'--pointer-y':pointer.y} as React.CSSProperties}>
        <div className="art-halo"/><div className="art-circle circle-one"/><div className="art-circle circle-two"/>
        <img className="orbit-asset" src="/assets/signal-orbit-3d.png" alt="" />
        <img className="avatar-asset" src="/assets/scout-avatar-3d.png" alt="3D Stock Scout character based on the supplied avatar" />
        <div className="art-stamp"><span>SS/01</span><small>SEE BEYOND<br/>THE HYPE</small></div>
        <div className="floating-chip chip-top"><span className="chip-icon">✳</span><span>SCAN ACTIVE<small>4663 / ROBINHOOD</small></span><span className="chip-wave">▂▅▃▆▂</span></div>
        <div className="floating-chip chip-bottom"><span className="chip-ring"/><span>Signal found<small>Evidence first, always.</small></span><Icon name="arrowUp" size={18}/></div>
      </div>
    </div>
    <div className="hero-footer wrap-wide"><span><span className="mini-asterisk">✳</span> ON-CHAIN DATA. HUMAN JUDGMENT.</span><button onClick={onStory}>FOLLOW THE STORY <span>↓</span></button><span>CREATED FOR CURIOUS MINDS <b>© 2026</b></span></div>
  </section>;
}
