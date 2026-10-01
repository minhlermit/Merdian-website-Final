import { useEffect, useRef, useState } from 'react';
import { ScoutEngine, type EngineOptions, type EngineStats, type FrameInfo, type Layout } from '../scene/ScoutEngine';
import { CONTENT_WIDTH, HOTSPOTS, QUALITY, type HotspotId, type QualitySetting, type ViewAngle } from '../scene/config';
import { canUseWebGL } from '../scene/bridge';
import { getMotionState } from '../lib/motion';
import { BrandMark } from '../components/SiteHeader';
import { Icon } from '../components/Icons';
import { useSubjectDrag } from '../components/SubjectControls';
import '../styles/fonts.css';
import '../styles/tokens.css';
import '../styles/lab.css';

type LabOptions = Pick<EngineOptions, 'showSubject' | 'showProps' | 'showOrbit' | 'handheld' | 'quality'>;
type LabLayout = (w: number, h: number) => Omit<Layout, 'anchor'> & { anchor: { x: number; y: number; w: number; h: number } };

/** One engine rendering into a container; pauses while the container is off screen. */
function LabCanvas({ className, options, layout, onEngine, onFrame, children }: {
  className: string; options: LabOptions; layout: LabLayout; onEngine?: (engine: ScoutEngine | null) => void; onFrame?: (info: FrameInfo) => void; children?: React.ReactNode;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const layoutRef = useRef(layout);
  layoutRef.current = layout;
  const frameRef = useRef(onFrame);
  frameRef.current = onFrame;
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !canUseWebGL()) { setFailed(true); return; }
    const canvas = document.createElement('canvas');
    canvas.className = 'lab-canvas';
    host.prepend(canvas);
    let engine: ScoutEngine;
    try {
      engine = new ScoutEngine({
        canvas, motion: getMotionState().enabled, ...options,
        layout: () => layoutRef.current(canvas.clientWidth || 1, canvas.clientHeight || 1),
        onFrame: info => frameRef.current?.(info),
        onContextLost: () => setFailed(true),
      });
    } catch { canvas.remove(); setFailed(true); return; }
    onEngine?.(engine);
    const observer = new IntersectionObserver(([entry]) => engine.setActive(entry.isIntersecting && document.visibilityState === 'visible'));
    observer.observe(host);
    const onVisibility = () => engine.setActive(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', onVisibility);
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', onVisibility); onEngine?.(null); engine.dispose(); canvas.remove(); };
    // Options are fixed for the lifetime of a sample.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={hostRef} className={className}>
    {failed && <div className="lab-fallback"><img src="/assets/scout-avatar-3d.png" alt="" /><p>WebGL is unavailable here, so the static poster is shown.</p></div>}
    {children}
  </div>;
}

const fullAnchor: LabLayout = (w, h) => ({ anchor: { x: w * 0.1, y: h * 0.05, w: w * 0.8, h: h * 0.92 }, contentWidth: CONTENT_WIDTH.hero, story: -1, exit: 0, rest: 0, quiet: null });

function useStats(engine: ScoutEngine | null) {
  const [stats, setStats] = useState<EngineStats | null>(null);
  useEffect(() => {
    if (!engine) return;
    const id = window.setInterval(() => setStats(engine.stats()), 500);
    return () => window.clearInterval(id);
  }, [engine]);
  return stats;
}

function StatsReadout({ stats }: { stats: EngineStats | null }) {
  if (!stats) return <p className="lab-readout mono">Measuring…</p>;
  const uhd = stats.buffer.w >= 3840 && stats.buffer.h >= 2160;
  return <dl className="lab-readout mono">
    <div><dt>Viewport (CSS px)</dt><dd>{stats.viewport.w}×{stats.viewport.h}</dd></div>
    <div><dt>Device pixel ratio</dt><dd>{stats.devicePixelRatio}</dd></div>
    <div><dt>Render pixel ratio</dt><dd>{stats.renderPixelRatio.toFixed(2)}</dd></div>
    <div><dt>Drawing buffer</dt><dd>{stats.buffer.w}×{stats.buffer.h}{uhd ? ' · UHD' : ''}</dd></div>
    <div><dt>Quality tier</dt><dd>{stats.tier} ({stats.setting})</dd></div>
    <div><dt>Frame rate (EMA)</dt><dd>{stats.fps} fps</dd></div>
    <div><dt>Adaptive policy</dt><dd>{stats.adaptiveNote}</dd></div>
  </dl>;
}

// ---- Sample 1 ---------------------------------------------------------------------------------

function SubjectSample() {
  const [engine, setEngine] = useState<ScoutEngine | null>(null);
  const [angles, setAngles] = useState<Record<ViewAngle, string> | null>(null);
  const [active, setActive] = useState<HotspotId | null>(null);
  const hotspotRefs = useRef(new Map<string, HTMLButtonElement>());
  const engineRef = useRef<ScoutEngine | null>(null);
  engineRef.current = engine;
  const drag = useSubjectDrag(undefined, () => engineRef.current);

  const onFrame = (info: FrameInfo) => {
    for (const spot of info.hotspots) {
      const el = hotspotRefs.current.get(spot.id);
      if (!el) continue;
      el.style.transform = `translate3d(${spot.x.toFixed(1)}px, ${spot.y.toFixed(1)}px, 0)`;
      el.dataset.visible = String(spot.visible);
    }
  };
  const select = (id: HotspotId) => { const next = active === id ? null : id; setActive(next); engine?.focusHotspot(next); };

  return <section className="lab-sample" aria-labelledby="s1">
    <header><p className="label">Sample 01 · interactive subject</p><h2 id="s1">Scout in real 3D</h2>
      <p>Procedural meshes with physical materials and studio lighting. Drag horizontally (damped release, ±70° limit), move the pointer to steer the gaze, select a glowing point, or use the controls. Arrow keys rotate when the stage has focus.</p></header>
    <div className="lab-split">
      <LabCanvas className="lab-stage" options={{ showProps: false }} layout={fullAnchor} onEngine={setEngine} onFrame={onFrame}>
        <div className="lab-hit" tabIndex={0} role="group" aria-label="Interactive Scout. Arrow keys rotate, R resets."
          onKeyDown={e => { if (e.key === 'ArrowLeft') engine?.nudge(-1); if (e.key === 'ArrowRight') engine?.nudge(1); if (e.key.toLowerCase() === 'r') engine?.resetView(); }}
          onPointerMove={e => { drag.onPointerMove(e); if (e.pointerType === 'mouse') engine?.pointerAt(e.clientX, e.clientY); }}
          onPointerDown={drag.onPointerDown} onPointerUp={drag.onPointerUp} onPointerCancel={drag.onPointerCancel}>
          {HOTSPOTS.map(h => <button key={h.id} ref={el => { if (el) hotspotRefs.current.set(h.id, el); }} type="button" className={`hotspot ${active === h.id ? 'is-active' : ''}`} data-visible="false" onClick={() => select(h.id)} aria-label={h.label}><span className="hotspot-dot" /><span className="hotspot-label">{h.label}</span></button>)}
          <span className="drag-hint"><Icon name="arrow" size={14} className="flip" /> Drag to explore <Icon name="arrow" size={14} /></span>
        </div>
      </LabCanvas>
      <div className="lab-panel">
        <div className="lab-controls" role="group" aria-label="View presets">
          <button type="button" className="chip" onClick={() => engine?.setView('front')}>Front</button>
          <button type="button" className="chip" onClick={() => engine?.setView('threeQuarter')}>Three-quarter</button>
          <button type="button" className="chip" onClick={() => engine?.setView('side')}>Side</button>
          <button type="button" className="chip" onClick={() => { setActive(null); engine?.resetView(); }}><Icon name="refresh" size={14} /> Reset view</button>
        </div>
        <div className="capability-list">
          {HOTSPOTS.map((h, i) => <button key={h.id} type="button" aria-pressed={active === h.id} className={active === h.id ? 'is-active' : ''} onClick={() => select(h.id)}>
            <span className="num">0{i + 1}</span><span><b>{h.label}</b><small>{h.body}</small></span>
          </button>)}
        </div>
        <button type="button" className="btn btn-ghost" onClick={() => engine && setAngles(engine.captureAngles())}>Capture front · ¾ · side</button>
        {angles && <div className="lab-angles">{(['front', 'threeQuarter', 'side'] as ViewAngle[]).map(v => <figure key={v}><img src={angles[v]} alt={`Scout, ${v} view`} /><figcaption className="mono">{v}</figcaption></figure>)}</div>}
      </div>
    </div>
  </section>;
}

// ---- Sample 2 ---------------------------------------------------------------------------------

function BackgroundSample() {
  const [engine, setEngine] = useState<ScoutEngine | null>(null);
  const [quality, setQuality] = useState<QualitySetting>('auto');
  const stats = useStats(engine);
  return <section className="lab-sample" aria-labelledby="s2">
    <header><p className="label">Sample 02 · moving background</p><h2 id="s2">Technology-studio environment</h2>
      <p>A real-time shader rather than a video: slow spatial waves, a fine 80 px grid, drifting amber light and native-resolution dithering. It is non-repeating, so there is no loop seam. The readout reports the actual drawing buffer; at a 3840×2160 viewport (or 1920×1080 at DPR 2) the High tier renders a full UHD buffer.</p></header>
    <LabCanvas className="lab-stage lab-stage-wide" options={{ showSubject: false, showProps: false, showOrbit: false, quality: 'auto' }} layout={(w, h) => ({ ...fullAnchor(w, h), anchor: { x: w * 0.5, y: h * 0.1, w: w * 0.45, h: h * 0.8 }, quiet: { x: w * 0.05, y: h * 0.25, w: w * 0.38, h: h * 0.5 } })} onEngine={setEngine}>
      <div className="lab-quiet-note mono">Quiet region reserved for headings</div>
    </LabCanvas>
    <div className="lab-split lab-split-bottom">
      <div>
        <label className="lab-select"><span className="label">Quality</span>
          <select value={quality} onChange={e => { const q = e.target.value as QualitySetting; setQuality(q); engine?.setQuality(q); }}>
            <option value="auto">Auto</option>
            {(Object.keys(QUALITY) as (keyof typeof QUALITY)[]).map(k => <option key={k} value={k}>{QUALITY[k].label}</option>)}
          </select>
        </label>
        <StatsReadout stats={stats} />
      </div>
      <figure className="phone-frame"><iframe title="Background, mobile variant" src="/lab?frame=background&mobile=1" loading="lazy" /><figcaption className="mono">Mobile variant · 390×844 · handheld limit ≤ 1.5 MP</figcaption></figure>
    </div>
  </section>;
}

// ---- Sample 3 ---------------------------------------------------------------------------------

function StorySample() {
  const [progress, setProgress] = useState(0);
  const progressRef = useRef(0);
  progressRef.current = progress;
  const scrollRef = useRef<HTMLDivElement>(null);
  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setProgress(Math.round((el.scrollTop / (el.scrollHeight - el.clientHeight)) * 1000) / 1000);
  };
  return <section className="lab-sample" aria-labelledby="s3">
    <header><p className="label">Sample 03 · story transition</p><h2 id="s3">Discover → Verify, both directions</h2>
      <p>Scroll inside the strip (or drag the slider) to move from discovery, where sparse signal nodes collect on the scanner and one becomes the focus, to verification, where structured evidence layers slide in beside the reframed subject. Every state is a function of progress, so reversing is exact.</p></header>
    <div className="lab-split">
      <LabCanvas className="lab-stage" options={{}} layout={(w, h) => ({ anchor: { x: w * 0.04, y: h * 0.06, w: w * 0.92, h: h * 0.88 }, contentWidth: CONTENT_WIDTH.story, story: progressRef.current, exit: 0, rest: 0, quiet: null })} />
      <div className="lab-panel">
        <div className="lab-scrub" ref={scrollRef} onScroll={onScroll} tabIndex={0} aria-label="Scroll to scrub the transition">
          <div><p className="mono">↓ Scroll: Discover</p><p className="mono">…</p><p className="mono">Verify ↑ scroll back</p></div>
        </div>
        <label className="lab-select"><span className="label">Progress {progress.toFixed(2)} · {progress < 0.5 ? 'Discover' : 'Verify'}</span>
          <input type="range" min={0} max={1} step={0.001} value={progress} onChange={e => setProgress(Number(e.target.value))} />
        </label>
      </div>
    </div>
  </section>;
}

// ---- Sample 4 ---------------------------------------------------------------------------------

/** Renders the real page at 1440×900 and scales it to the container width. */
function ScaledFrame({ src, title }: { src: string; title: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.5);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setScale(entry.contentRect.width / 1440));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return <div className="frame-scale" ref={ref}><iframe title={title} src={src} loading="lazy" style={{ transform: `scale(${scale})` }} /></div>;
}

function HeroSample() {
  return <section className="lab-sample" aria-labelledby="s4">
    <header><p className="label">Sample 04 · complete hero</p><h2 id="s4">New hero next to the v2 baseline</h2>
      <p>Geist Sans and Geist Mono (self-hosted WOFF2, OFL), new header alignment with Get MC and Connect wallet at the top right, button hierarchy, the brand-mark cursor and the live 3D scene together. The frames below load the real page.</p></header>
    <div className="hero-compare">
      <figure className="desk-frame"><ScaledFrame title="New hero, desktop 1440×900" src="/" /><figcaption className="mono">New · desktop 1440×900</figcaption></figure>
      <figure className="desk-frame"><img src="/lab/baseline-desktop.png" alt="Version 2 hero, desktop baseline" loading="lazy" /><figcaption className="mono">Baseline v2 · desktop</figcaption></figure>
      <figure className="phone-frame"><iframe title="New hero, mobile 390×844" src="/" loading="lazy" /><figcaption className="mono">New · mobile 390×844</figcaption></figure>
      <figure className="phone-frame is-image"><img src="/lab/baseline-mobile.png" alt="Version 2 hero, mobile baseline" loading="lazy" /><figcaption className="mono">Baseline v2 · mobile</figcaption></figure>
    </div>
    <div className="type-specimen">
      <p className="label">Type scale</p>
      <p className="spec-hero">Follow the signal.</p>
      <p className="spec-h2">Before the verdict, follow the trail.</p>
      <p className="spec-body">Body 16–18 px with comfortable line length. Tabular numerals for metrics: <span className="tabular">$1,204.50 · 06:00:00 · 12/30</span></p>
      <p className="spec-mono mono">GEIST MONO · TECHNICAL LABELS · 0123456789</p>
      <p className="spec-body">Vietnamese glyph check: Nghiên cứu tín hiệu, kiểm chứng bằng chứng — Ưu tiên độ chính xác.</p>
    </div>
  </section>;
}

const INVENTORY: [string, string, string][] = [
  ['Scout subject (head, hair, glasses, ears, hoop, jacket, zipper)', 'Procedural geometry · built at runtime', 'src/scene/ScoutModel.ts'],
  ['Signal orbit, nodes, evidence layers, research paths, scoring frame, gate, report', 'Procedural geometry + runtime canvas textures', 'src/scene/EvidenceScene.ts'],
  ['Moving studio background', 'Real-time GLSL shader', 'src/scene/AnimatedBackground.ts'],
  ['Studio reflections', 'three.js RoomEnvironment (procedural)', 'src/scene/ScoutEngine.ts'],
  ['scout-avatar-3d.png', 'Raster · identity reference, loading poster, WebGL fallback', 'public/assets/'],
  ['signal-orbit-3d.png', 'Raster · story fallback, console card', 'public/assets/'],
  ['scout-mascot-pixel.png', 'Raster · empty state, guided demo', 'public/assets/'],
  ['Geist Sans / Geist Mono', 'Variable WOFF2 · SIL OFL 1.1', 'public/fonts/geist/'],
  ['Imported 3D models', 'None in this build', '—'],
];

function Inventory() {
  return <section className="lab-sample" aria-labelledby="inv">
    <header><p className="label">Asset inventory</p><h2 id="inv">What is geometry, what is an image</h2></header>
    <table className="lab-table"><thead><tr><th scope="col">Asset</th><th scope="col">Type</th><th scope="col">Location</th></tr></thead>
      <tbody>{INVENTORY.map(([a, t, l]) => <tr key={a}><th scope="row">{a}</th><td>{t}</td><td className="mono">{l}</td></tr>)}</tbody></table>
  </section>;
}

function BackgroundFrame({ mobile }: { mobile: boolean }) {
  return <LabCanvas className="lab-frame-full" options={{ showSubject: false, showProps: false, showOrbit: false, handheld: mobile }} layout={(w, h) => ({ ...fullAnchor(w, h), anchor: { x: 0, y: h * 0.35, w, h: h * 0.5 }, quiet: { x: w * 0.06, y: h * 0.08, w: w * 0.88, h: h * 0.24 } })} />;
}

export default function AssetLab() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('frame') === 'background') return <BackgroundFrame mobile={params.get('mobile') === '1'} />;
  return <div className="lab">
    <header className="lab-header shell">
      <a className="brand" href="/"><BrandMark size={30} /><span className="brand-name">stockscout<small>Asset lab</small></span></a>
      <a className="btn btn-ghost btn-sm" href="/">Back to site <Icon name="arrowUp" size={14} /></a>
    </header>
    <main className="shell">
      <section className="lab-intro">
        <p className="label">Review build · 3D motion direction</p>
        <h1>Approve the pieces before the page.</h1>
        <p>Four samples from the brief, each replaceable on its own. The reference clip could not be played in the build environment, so the motion here is a proposal based on the brief and the existing product, not a shot-by-shot match. Upload the clip directly for an exact comparison.</p>
      </section>
      <SubjectSample />
      <BackgroundSample />
      <StorySample />
      <HeroSample />
      <Inventory />
    </main>
  </div>;
}
