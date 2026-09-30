import { useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { HOTSPOTS, MOTION, type HotspotId } from '../scene/config';
import { sceneBridge, useSceneStatus } from '../scene/bridge';
import type { ScoutEngine } from '../scene/ScoutEngine';
import { setMotionPrefs, useMotion } from '../lib/motion';
import { Icon } from './Icons';

const HINT_KEY = 'scout-drag-hint-v1';
const readHint = () => { try { return sessionStorage.getItem(HINT_KEY) === '1'; } catch { return false; } };
const saveHint = () => { try { sessionStorage.setItem(HINT_KEY, '1'); } catch { /* storage unavailable */ } };

/**
 * Horizontal drag on the subject area. Mouse drags start after 3px; touch waits for a deliberate
 * horizontal gesture so vertical page scrolling (touch-action: pan-y) keeps working.
 */
export function useSubjectDrag(onDragStart?: () => void, getEngine: () => ScoutEngine | null = () => sceneBridge.engine) {
  const s = useRef({ id: -1, x0: 0, y0: 0, lastX: 0, lastT: 0, v: 0, dragging: false, touch: false });
  const end = (event: PointerEvent<HTMLElement>) => {
    const st = s.current;
    if (event.pointerId !== st.id) return;
    if (st.dragging) getEngine()?.dragEnd(event.timeStamp - st.lastT > 90 ? 0 : st.v);
    st.id = -1;
    st.dragging = false;
  };
  return {
    onPointerDown(event: PointerEvent<HTMLElement>) {
      if (!getEngine() || event.button !== 0 || (event.target as Element).closest('button, a')) return;
      s.current = { id: event.pointerId, x0: event.clientX, y0: event.clientY, lastX: event.clientX, lastT: event.timeStamp, v: 0, dragging: false, touch: event.pointerType !== 'mouse' };
    },
    onPointerMove(event: PointerEvent<HTMLElement>) {
      const st = s.current;
      if (event.pointerId !== st.id) return;
      const dx = event.clientX - st.x0, dy = event.clientY - st.y0;
      if (!st.dragging) {
        const threshold = st.touch ? MOTION.touchIntentPx : 3;
        if (Math.abs(dx) > threshold && Math.abs(dx) > Math.abs(dy) * 1.2) {
          st.dragging = true;
          st.lastX = event.clientX;
          st.lastT = event.timeStamp;
          event.currentTarget.setPointerCapture(event.pointerId);
          getEngine()?.dragStart();
          onDragStart?.();
        } else if (st.touch && Math.abs(dy) > threshold) {
          st.id = -1; // vertical intent: leave it to page scrolling
        }
        return;
      }
      const step = event.clientX - st.lastX;
      const dt = event.timeStamp - st.lastT;
      getEngine()?.dragMove(step);
      if (dt > 0) st.v = 0.75 * (step / dt) + 0.25 * st.v;
      st.lastX = event.clientX;
      st.lastT = event.timeStamp;
    },
    onPointerUp: end,
    onPointerCancel: end,
  };
}

export function SubjectStage() {
  const status = useSceneStatus();
  const motion = useMotion();
  const ready = status === 'ready';
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<HotspotId | null>(null);
  const [hintSeen, setHintSeen] = useState(readHint);
  const drag = useSubjectDrag(() => { if (!hintSeen) { setHintSeen(true); saveHint(); } });

  const select = (id: HotspotId) => {
    const next = active === id ? null : id;
    setActive(next);
    setOpen(true);
    sceneBridge.engine?.focusHotspot(next);
  };
  const reset = () => { setActive(null); sceneBridge.engine?.resetView(); };
  const nudge = (d: -1 | 1) => sceneBridge.engine?.nudge(d);
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.target !== event.currentTarget) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); nudge(-1); }
    else if (event.key === 'ArrowRight') { event.preventDefault(); nudge(1); }
    else if (event.key === 'Home' || event.key.toLowerCase() === 'r') { event.preventDefault(); reset(); }
    else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setOpen(o => !o); }
  };
  const detail = HOTSPOTS.find(h => h.id === active);

  return <div className={`subject ${ready ? 'is-ready' : ''}`}>
    <div
      ref={sceneBridge.slot('heroAnchor')}
      className="subject-stage"
      tabIndex={ready ? 0 : -1}
      role="group"
      aria-roledescription="interactive 3D model"
      aria-label="Scout, the Stock Scout character. Left and right arrow keys rotate, R resets, Enter opens the capability panel."
      onKeyDown={onKeyDown}
      {...drag}
    >
      <img className="subject-poster" src="/assets/scout-avatar-3d.png" alt={ready ? '' : 'Scout, the Stock Scout character'} aria-hidden={ready} />
      {HOTSPOTS.map(h => <button
        key={h.id}
        ref={sceneBridge.hotspot(h.id)}
        type="button"
        className={`hotspot ${active === h.id ? 'is-active' : ''}`}
        data-visible="false"
        tabIndex={-1}
        aria-hidden="true"
        onClick={() => select(h.id)}
      ><span className="hotspot-dot" /><span className="hotspot-label">{h.label}</span></button>)}
      {ready && !hintSeen && <span className="drag-hint" aria-hidden="true"><Icon name="arrow" size={14} className="flip" /> Drag to explore <Icon name="arrow" size={14} /></span>}
    </div>

    <div className="subject-toolbar" role="toolbar" aria-label="3D Scout controls">
      <button type="button" className={`chip ${open ? 'is-on' : ''}`} aria-expanded={open} aria-controls="scout-capabilities" onClick={() => setOpen(o => !o)}>
        <Icon name="spark" size={15} /> Explore Scout
      </button>
      {ready && <>
        <button type="button" className="chip icon-only" aria-label="Rotate Scout left" onClick={() => nudge(-1)}><Icon name="arrow" size={15} className="flip" /></button>
        <button type="button" className="chip icon-only" aria-label="Rotate Scout right" onClick={() => nudge(1)}><Icon name="arrow" size={15} /></button>
        <button type="button" className="chip" onClick={reset}><Icon name="refresh" size={14} /> Reset view</button>
      </>}
      <button type="button" className="chip" aria-pressed={!motion.enabled} onClick={() => setMotionPrefs({ motion: motion.enabled ? 'off' : 'on' })}>
        <Icon name={motion.enabled ? 'pause' : 'play'} size={13} /> {motion.enabled ? 'Pause motion' : 'Play motion'}
      </button>
    </div>

    {open && <section id="scout-capabilities" className="capability-panel" aria-label="What Scout does">
      <div className="capability-head">
        <span className="label">Explore Scout</span>
        <button type="button" className="icon-button" aria-label="Close capability panel" onClick={() => { setOpen(false); setActive(null); sceneBridge.engine?.focusHotspot(null); }}><Icon name="close" size={16} /></button>
      </div>
      <div className="capability-list">
        {HOTSPOTS.map((h, i) => <button key={h.id} type="button" aria-pressed={active === h.id} className={active === h.id ? 'is-active' : ''} onClick={() => select(h.id)}>
          <span className="num">0{i + 1}</span><span><b>{h.label}</b><small>{h.short}</small></span>
        </button>)}
      </div>
      <p className="capability-detail" aria-live="polite">{detail ? detail.body : 'Choose a capability, or select a glowing point on Scout, to see how the research engine works.'}</p>
    </section>}
  </div>;
}
