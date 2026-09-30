import { useEffect, useRef } from 'react';
import { BrandMark } from './SiteHeader';

export function useReveal() {
  useEffect(() => {
    const nodes = document.querySelectorAll<HTMLElement>('[data-reveal]');
    if (!('IntersectionObserver' in window)) {
      nodes.forEach(node => node.classList.add('is-visible'));
      return;
    }
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -35px 0px' });
    nodes.forEach(node => observer.observe(node));
    return () => observer.disconnect();
  }, []);
}

const NATIVE = 'input, textarea, select, iframe, [contenteditable="true"], .native-cursor';

/**
 * Brand-mark cursor for precise pointers. The mark is drawn exactly at the pointer on every
 * move (no smoothing); only the decorative ring eases behind it. Native cursors return over
 * text fields, selects and embedded reports, and for touch or coarse pointers.
 */
export function BrandCursor() {
  const markRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const media = window.matchMedia('(pointer: fine) and (hover: hover)');
    const mark = markRef.current, ring = ringRef.current;
    if (!mark || !ring) return;
    let enabled = false, raf = 0, x = -100, y = -100, rx = -100, ry = -100, shown = false;

    const setShown = (value: boolean) => {
      if (shown === value) return;
      shown = value;
      mark.classList.toggle('is-shown', value);
      ring.classList.toggle('is-shown', value);
    };
    const tick = () => {
      rx += (x - rx) * 0.24;
      ry += (y - ry) * 0.24;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      raf = Math.abs(x - rx) + Math.abs(y - ry) > 0.2 ? requestAnimationFrame(tick) : 0;
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') { setShown(false); return; }
      x = event.clientX; y = event.clientY;
      mark.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      const target = event.target as Element | null;
      const native = Boolean(target?.closest?.(NATIVE));
      setShown(!native);
      ring.classList.toggle('is-interactive', Boolean(target?.closest?.('button, a, summary, label, [role="button"], .subject-stage, .story-stage')));
      if (!raf) raf = requestAnimationFrame(tick);
    };
    const down = () => ring.classList.add('is-pressed');
    const up = () => ring.classList.remove('is-pressed');
    const leave = () => setShown(false);

    const enable = () => {
      if (enabled) return;
      enabled = true;
      document.body.classList.add('brand-cursor-active');
      window.addEventListener('pointermove', move, { passive: true });
      window.addEventListener('pointerdown', down);
      window.addEventListener('pointerup', up);
      document.documentElement.addEventListener('mouseleave', leave);
    };
    const disable = () => {
      if (!enabled) return;
      enabled = false;
      setShown(false);
      document.body.classList.remove('brand-cursor-active');
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerdown', down);
      window.removeEventListener('pointerup', up);
      document.documentElement.removeEventListener('mouseleave', leave);
    };
    const sync = () => (media.matches ? enable() : disable());
    sync();
    media.addEventListener('change', sync);
    return () => { media.removeEventListener('change', sync); disable(); cancelAnimationFrame(raf); };
  }, []);

  return <>
    <div className="cursor-ring" ref={ringRef} aria-hidden="true" />
    <div className="cursor-mark" ref={markRef} aria-hidden="true"><BrandMark size={22} /><i /></div>
  </>;
}
