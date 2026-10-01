import { QUALITY, type QualitySetting } from '../scene/config';
import { setMotionPrefs, useMotion, type MotionSetting } from '../lib/motion';
import { BrandMark, type NavTarget } from './SiteHeader';

export function MotionPreferences() {
  const prefs = useMotion();
  return <div className="motion-prefs" role="group" aria-label="Motion and quality">
    <label>
      <span className="label">Motion</span>
      <select value={prefs.motion} onChange={e => setMotionPrefs({ motion: e.target.value as MotionSetting })}>
        <option value="auto">Auto{prefs.systemReduced ? ' (reduced by system)' : ''}</option>
        <option value="on">On</option>
        <option value="off">Off</option>
      </select>
    </label>
    <label>
      <span className="label">3D quality</span>
      <select value={prefs.quality} onChange={e => setMotionPrefs({ quality: e.target.value as QualitySetting })}>
        <option value="auto">Auto (adapts to device)</option>
        {(Object.keys(QUALITY) as (keyof typeof QUALITY)[]).map(k => <option key={k} value={k}>{QUALITY[k].label}</option>)}
      </select>
    </label>
  </div>;
}

export function SiteFooter({ onNavigate }: { onNavigate: (target: NavTarget) => void }) {
  return <footer className="site-footer">
    <div className="shell footer-grid">
      <div className="footer-brand">
        <span className="brand"><BrandMark size={30} /><span className="brand-name">stockscout<small>Research studio</small></span></span>
        <p>Follow the signal. Keep the proof.</p>
      </div>
      <nav className="footer-nav" aria-label="Footer">
        <button type="button" onClick={() => onNavigate('product')}>Product</button>
        <button type="button" onClick={() => onNavigate('story')}>How it works</button>
        <button type="button" onClick={() => onNavigate('console')}>Console</button>
        <button type="button" onClick={() => onNavigate('plans')}>MC plans</button>
        <button type="button" onClick={() => onNavigate('faq')}>FAQ</button>
        <a href="/lab">Asset lab</a>
      </nav>
      <MotionPreferences />
    </div>
    <div className="shell footer-base">
      <small>Research studio © 2026 · Research only, not investment advice. Stock-paired tokens do not automatically convey stock ownership.</small>
      <button type="button" className="text-link" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>Back to top ↑</button>
    </div>
  </footer>;
}
