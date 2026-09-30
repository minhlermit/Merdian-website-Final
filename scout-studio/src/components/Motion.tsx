import { useEffect, useRef, useState } from 'react';

export function useReveal() {
  useEffect(() => {
    const nodes = document.querySelectorAll<HTMLElement>('[data-reveal]');
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      nodes.forEach(node => node.classList.add('is-visible'));
      return;
    }
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
      });
    }, {threshold:.08,rootMargin:'0px 0px -35px 0px'});
    nodes.forEach(node => observer.observe(node));
    return () => observer.disconnect();
  }, []);
}

export function BrandCursor() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const fine = window.matchMedia('(pointer:fine)');
    const reduced = window.matchMedia('(prefers-reduced-motion:reduce)');
    if (reduced.matches) return;
    const el = ref.current; if (!el) return;
    let x = -100, y = -100, raf = 0;
    const move = (event:PointerEvent) => {
      if (event.pointerType !== 'mouse' && !fine.matches) { el.classList.remove('shown'); document.body.classList.remove('brand-cursor-active'); return; }
      document.body.classList.add('brand-cursor-active');
      x = event.clientX; y = event.clientY;
      el.classList.add('shown');
      el.classList.toggle('is-interactive', Boolean((event.target as Element)?.closest?.('button,a,input,select,[role="button"]')));
      if (!raf) raf=requestAnimationFrame(() => { el.style.transform=`translate3d(${x}px,${y}px,0)`; raf=0; });
    };
    const down = () => el.classList.add('is-pressed');
    const up = () => el.classList.remove('is-pressed');
    const hide = () => el.classList.remove('shown');
    window.addEventListener('pointermove',move,{passive:true});
    window.addEventListener('pointerdown',down);window.addEventListener('pointerup',up);document.addEventListener('mouseleave',hide);
    return () => { document.body.classList.remove('brand-cursor-active');cancelAnimationFrame(raf);window.removeEventListener('pointermove',move);window.removeEventListener('pointerdown',down);window.removeEventListener('pointerup',up);document.removeEventListener('mouseleave',hide); };
  }, []);
  return <div className="brand-cursor" ref={ref} aria-hidden="true"><span className="cursor-core">S</span><span className="cursor-orbit"/></div>;
}

export function OpeningSequence() {
  const [visible,setVisible] = useState(() => {
    try { return !sessionStorage.getItem('scout-intro-seen') && !window.matchMedia('(prefers-reduced-motion:reduce)').matches; }
    catch { return false; }
  });
  useEffect(() => {
    if (!visible) return;
    const id=setTimeout(() => {setVisible(false);sessionStorage.setItem('scout-intro-seen','1');},1250);
    return () => clearTimeout(id);
  },[visible]);
  if (!visible) return null;
  return <div className="opening-sequence" role="status" aria-label="Opening Stock Scout Studio"><div className="opening-inner"><img src="/assets/scout-mascot-pixel.png" alt=""/><span>STOCKSCOUT / INITIALIZING</span><div className="opening-progress"><i/></div><p>Find the signal. Keep the proof.</p></div><button onClick={()=>{setVisible(false);sessionStorage.setItem('scout-intro-seen','1');}}>SKIP ↗</button></div>;
}
