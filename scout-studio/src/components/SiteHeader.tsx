import { useEffect, useState } from 'react';
import { Icon } from './Icons';

export type NavTarget = 'memo' | 'why' | 'story' | 'console' | 'plans' | 'faq';

export function BrandMark({ size = 36 }: { size?: number }) {
  return <svg className="brand-glyph" width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
    <circle cx="20" cy="20" r="18.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <path d="M25.6 14.2c-1.2-1.7-3.2-2.6-5.6-2.6-3.3 0-5.6 1.8-5.6 4.4 0 2.5 1.9 3.6 5.3 4.4 3.2.7 4.5 1.5 4.5 3.2 0 1.8-1.8 3-4.4 3-2.6 0-4.5-1.1-5.5-3" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
    <circle cx="34" cy="7" r="3.2" fill="currentColor" />
  </svg>;
}

const LINKS: [NavTarget, string][] = [['memo', 'Sample memo'], ['why', 'Why Scout'], ['story', 'How it works'], ['console', 'Console'], ['faq', 'FAQ']];
const MOBILE_LINKS: [NavTarget, string][] = [...LINKS.slice(0, 4), ['plans', 'MC plans'], ['faq', 'FAQ']];

export function SiteHeader({ onNavigate, onWallet, onGetMC, onRun, runLabel, walletLabel, connected }: {
  onNavigate: (target: NavTarget) => void; onWallet: () => void; onGetMC: () => void; onRun: () => void; runLabel: string; walletLabel: string; connected: boolean;
}) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const go = (target: NavTarget) => { setOpen(false); onNavigate(target); };

  return <header className={`site-header ${scrolled ? 'is-scrolled' : ''} ${open ? 'menu-open' : ''}`}>
    <div className="shell header-row">
      <a className="brand" href="#top" onClick={event => { event.preventDefault(); setOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }); }} aria-label="Stock Scout Studio, back to top">
        <BrandMark size={34} />
        <span className="brand-name">stockscout<small>Research studio</small></span>
      </a>
      <nav className="header-nav" aria-label="Main">
        {LINKS.map(([target, label]) => <button key={target} type="button" onClick={() => go(target)}>{label}</button>)}
      </nav>
      <div className="header-actions">
        <button type="button" className="btn btn-quiet btn-sm mc-button" onClick={onGetMC}>Get MC <span className="concept-tag">Concept</span></button>
        <button type="button" className={`btn btn-ghost btn-sm wallet-button ${connected ? 'is-connected' : ''}`} onClick={onWallet} aria-label={connected ? `Wallet ${walletLabel}` : 'Connect wallet'}>
          <Icon name="wallet" size={16} /><span>{walletLabel}</span>
        </button>
        <button type="button" className="btn btn-primary btn-sm run-button" onClick={() => { setOpen(false); onRun(); }}>{runLabel} <Icon name="play" size={11} /></button>
        <button type="button" className="menu-toggle" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} aria-controls="mobile-menu" onClick={() => setOpen(o => !o)}>
          <Icon name={open ? 'close' : 'menu'} size={22} />
        </button>
      </div>
    </div>
    <div id="mobile-menu" className="mobile-menu" hidden={!open}>
      <nav className="shell" aria-label="Mobile">
        {MOBILE_LINKS.map(([target, label]) => <button key={target} type="button" onClick={() => go(target)}>{label}<Icon name="arrow" size={18} /></button>)}
        <button type="button" onClick={() => { setOpen(false); onGetMC(); }}>Get MC <span className="concept-tag">Concept</span><Icon name="arrowUp" size={18} /></button>
        <a href="/lab">Asset lab<Icon name="arrowUp" size={18} /></a>
      </nav>
    </div>
  </header>;
}
