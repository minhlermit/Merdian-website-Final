import { useSyncExternalStore } from 'react';
import type { QualitySetting } from '../scene/config';

// Per-viewer motion and render-quality preferences. Stored in localStorage as a convenience;
// the page works the same when storage is unavailable.

export type MotionSetting = 'auto' | 'on' | 'off';
export interface MotionPrefs { motion: MotionSetting; quality: QualitySetting }

const KEY = 'scout-motion-prefs-v1';
const DEFAULTS: MotionPrefs = { motion: 'auto', quality: 'auto' };
const listeners = new Set<() => void>();

function load(): MotionPrefs {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (parsed && ['auto', 'on', 'off'].includes(parsed.motion) && ['auto', 'high', 'balanced', 'low'].includes(parsed.quality)) return parsed;
  } catch { /* storage unavailable */ }
  return DEFAULTS;
}

let prefs = typeof window === 'undefined' ? DEFAULTS : load();
const reducedQuery = typeof window === 'undefined' ? null : window.matchMedia('(prefers-reduced-motion: reduce)');
reducedQuery?.addEventListener?.('change', () => { snapshot = compute(); listeners.forEach(l => l()); });

export interface MotionState extends MotionPrefs { enabled: boolean; systemReduced: boolean }
function compute(): MotionState {
  const systemReduced = Boolean(reducedQuery?.matches);
  return { ...prefs, systemReduced, enabled: prefs.motion === 'on' || (prefs.motion === 'auto' && !systemReduced) };
}
let snapshot = compute();

export function setMotionPrefs(patch: Partial<MotionPrefs>) {
  prefs = { ...prefs, ...patch };
  try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch { /* storage unavailable */ }
  snapshot = compute();
  document.documentElement.dataset.motion = snapshot.enabled ? 'on' : 'off';
  listeners.forEach(l => l());
}

export function getMotionState() { return snapshot; }

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function useMotion(): MotionState {
  return useSyncExternalStore(subscribe, getMotionState, getMotionState);
}

if (typeof document !== 'undefined') document.documentElement.dataset.motion = snapshot.enabled ? 'on' : 'off';
