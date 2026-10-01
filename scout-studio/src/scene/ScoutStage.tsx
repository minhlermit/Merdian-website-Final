import { useEffect, useRef } from 'react';
import { ScoutEngine, type FrameInfo, type Layout, type Rect } from './ScoutEngine';
import { CONTENT_WIDTH } from './config';
import { sceneBridge } from './bridge';
import { getMotionState, useMotion } from '../lib/motion';

// Lazily loaded: owns the shared WebGL scene behind the hero and the story.

const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smoothstep = (a: number, b: number, x: number) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const rectOf = (el?: HTMLElement): Rect | null => {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return r.width && r.height ? { x: r.left, y: r.top, w: r.width, h: r.height } : null;
};
const mix = (a: Rect | null, b: Rect | null, t: number): Rect | null => {
  if (!a) return b; if (!b) return a;
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, w: a.w + (b.w - a.w) * t, h: a.h + (b.h - a.h) * t };
};

/** Story progress from chapter centres crossing the middle of the viewport. */
function storyProgress(vh: number) {
  const centres = sceneBridge.chapters.filter((el): el is HTMLElement => Boolean(el)).map(el => {
    const r = el.getBoundingClientRect();
    return r.top + r.height / 2;
  });
  if (!centres.length) return -1;
  const line = vh * 0.5;
  if (line <= centres[0]) return -Math.min(1, (centres[0] - line) / (vh * 0.9));
  const last = centres.length - 1;
  if (line >= centres[last]) return last;
  for (let i = 0; i < last; i++) if (line < centres[i + 1]) return i + (line - centres[i]) / (centres[i + 1] - centres[i]);
  return last;
}

export function siteLayout(): Layout {
  const vh = window.innerHeight;
  const slots = sceneBridge.slots;
  const heroEl = slots.get('heroAnchor');
  const hero = rectOf(heroEl);
  const story = storyProgress(vh);
  const w = smoothstep(-1, -0.12, story);
  // The hero subject follows its column, then rests near the top while the next section is read.
  const heroRect = hero ? { ...hero, y: Math.max(hero.y, -hero.h * 0.3) } : null;
  const rest = hero ? clamp(-hero.y / (hero.h * 0.6)) * (1 - w) : 0;
  const storyRect = rectOf(slots.get('storyAnchor'));
  const consoleRect = rectOf(slots.get('console'));
  return {
    anchor: mix(heroRect, storyRect, w),
    contentWidth: CONTENT_WIDTH.hero + (CONTENT_WIDTH.story - CONTENT_WIDTH.hero) * w,
    story,
    exit: consoleRect ? clamp((vh - consoleRect.y) / (vh * 0.85)) : 0,
    rest,
    quiet: mix(rectOf(slots.get('heroCopy')), rectOf(slots.get('storyText')), w),
  };
}

export default function ScoutStage() {
  const hostRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<ScoutEngine | null>(null);
  const motion = useMotion();

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const canvas = document.createElement('canvas');
    canvas.className = 'scene-canvas';
    host.appendChild(canvas);
    const layer = host.parentElement;
    const shown = new Map<string, boolean>();
    let lastOpacity = -1;

    const onFrame = (info: FrameInfo) => {
      const stage = sceneBridge.slots.get('heroAnchor')?.getBoundingClientRect();
      const heroActive = info.story < -0.7;
      for (const spot of info.hotspots) {
        const el = sceneBridge.hotspots.get(spot.id);
        if (!el || !stage) continue;
        const visible = spot.visible && heroActive;
        el.style.transform = `translate3d(${(spot.x - stage.left).toFixed(1)}px, ${(spot.y - stage.top).toFixed(1)}px, 0)`;
        if (shown.get(spot.id) !== visible) { shown.set(spot.id, visible); el.dataset.visible = String(visible); }
        const side = spot.x - stage.left > stage.width * 0.6 ? 'left' : 'right';
        if (el.dataset.side !== side) el.dataset.side = side;
      }
      const opacity = Math.round((1 - info.exit) * 100) / 100;
      if (layer && opacity !== lastOpacity) { lastOpacity = opacity; layer.style.opacity = String(opacity); }
    };

    let engine: ScoutEngine;
    try {
      const state = getMotionState();
      engine = new ScoutEngine({
        canvas,
        layout: siteLayout,
        quality: state.quality,
        motion: state.enabled,
        handheld: window.matchMedia('(pointer: coarse)').matches || window.innerWidth < 760,
        onFrame,
        onFirstFrame: () => sceneBridge.setStatus('ready'),
        onContextLost: () => sceneBridge.setStatus('fallback'),
      });
    } catch {
      canvas.remove();
      sceneBridge.setStatus('fallback');
      return;
    }
    engineRef.current = engine;
    sceneBridge.engine = engine;

    let inView = true;
    let pageVisible = document.visibilityState === 'visible';
    const sync = () => engine.setActive(inView && pageVisible);
    const zone = sceneBridge.slots.get('zone');
    const observer = zone ? new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; sync(); }, { rootMargin: '0px 0px 0px 0px' }) : null;
    if (zone && observer) observer.observe(zone);
    const onVisibility = () => { pageVisible = document.visibilityState === 'visible'; sync(); };
    const onPointer = (event: PointerEvent) => { if (event.pointerType === 'mouse') engine.pointerAt(event.clientX, event.clientY); };
    const onLeave = () => engine.pointerLeave();
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('pointermove', onPointer, { passive: true });
    document.documentElement.addEventListener('mouseleave', onLeave);
    sync();

    // ?debug=scene shows the actual render resolution for QA (viewport, DPR, drawing buffer).
    let debugTimer = 0;
    const readout = new URLSearchParams(window.location.search).get('debug') === 'scene' ? document.createElement('pre') : null;
    if (readout) {
      readout.className = 'scene-debug';
      document.body.appendChild(readout);
      debugTimer = window.setInterval(() => {
        const s = engine.stats();
        readout.textContent = `viewport ${s.viewport.w}×${s.viewport.h} · device DPR ${s.devicePixelRatio} · render DPR ${s.renderPixelRatio.toFixed(2)}\nbuffer ${s.buffer.w}×${s.buffer.h} · tier ${s.tier} (${s.setting}) · ${s.fps} fps\n${s.adaptiveNote}`;
      }, 500);
    }

    return () => {
      window.clearInterval(debugTimer);
      readout?.remove();
      observer?.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('pointermove', onPointer);
      document.documentElement.removeEventListener('mouseleave', onLeave);
      if (sceneBridge.engine === engine) sceneBridge.engine = null;
      engineRef.current = null;
      engine.dispose();
      canvas.remove();
      if (layer) layer.style.opacity = '';
    };
  }, []);

  useEffect(() => { engineRef.current?.setMotion(motion.enabled); }, [motion.enabled]);
  useEffect(() => { engineRef.current?.setQuality(motion.quality); }, [motion.quality]);

  return <div ref={hostRef} className="scene-host" />;
}
