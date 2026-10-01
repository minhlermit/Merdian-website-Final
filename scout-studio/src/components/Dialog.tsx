import { useCallback, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { getMotionState } from '../lib/motion';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])';
const stack: HTMLElement[] = [];
const EXIT_MS = 180;

/**
 * Accessible modal: traps focus, closes on Escape or backdrop click, restores focus to the
 * element that opened it, and plays a short exit transition before unmounting.
 */
export function Dialog({ label, onClose, className, variant = 'center', children }: {
  label: string;
  onClose: () => void;
  className: string;
  variant?: 'center' | 'drawer';
  children: (close: () => void) => ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [closing, setClosing] = useState(false);
  const closingRef = useRef(false);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const close = useCallback(() => {
    if (closingRef.current) return;
    closingRef.current = true;
    if (!getMotionState().enabled) { onCloseRef.current(); return; }
    setClosing(true);
    window.setTimeout(() => onCloseRef.current(), EXIT_MS);
  }, []);

  // Layout effect: focus moves and Escape works from the first painted frame, even when the main
  // thread is busy (for example while the 3D scene renders).
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    stack.push(node);
    document.body.classList.add('modal-open');
    const first = node.querySelector<HTMLElement>('[data-autofocus]') ?? node.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? node).focus({ preventScroll: true });

    const onKey = (event: KeyboardEvent) => {
      if (stack[stack.length - 1] !== node) return;
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); return; }
      if (event.key !== 'Tab') return;
      const items = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(el => el.offsetParent !== null || el === document.activeElement);
      if (!items.length) { event.preventDefault(); node.focus(); return; }
      const firstItem = items[0], lastItem = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === firstItem || document.activeElement === node)) { event.preventDefault(); lastItem.focus(); }
      else if (!event.shiftKey && document.activeElement === lastItem) { event.preventDefault(); firstItem.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      const index = stack.lastIndexOf(node);
      if (index >= 0) stack.splice(index, 1);
      if (!stack.length) document.body.classList.remove('modal-open');
      if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
    };
  }, [close]);

  return <div
    className={`overlay ${variant === 'center' ? 'modal-center' : 'overlay-drawer'} ${closing ? 'is-closing' : ''}`}
    onMouseDown={event => { if (event.target === event.currentTarget) close(); }}
  >
    <div ref={ref} className={className} role="dialog" aria-modal="true" aria-label={label} tabIndex={-1}>
      {children(close)}
    </div>
  </div>;
}
