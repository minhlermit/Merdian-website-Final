import { demo } from '../data/demo';
import { isCurrent } from './cycle';
import type { ScoutPayload } from '../types';

const KEY = 'stock-scout-import-v1';

export function validPayload(value: unknown): value is ScoutPayload {
  if (!value || typeof value !== 'object') return false;
  const x = value as Record<string, unknown>;
  return x.schema === 1 && Array.isArray(x.candidates) && Array.isArray(x.events) &&
    x.candidates.every(c => c && typeof c === 'object' && typeof c.address === 'string' && typeof c.symbol === 'string');
}

export function savedPayload(): ScoutPayload | null {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    if (validPayload(parsed) && isCurrent(parsed.generated)) return { ...parsed, source: 'export' };
    if (raw) localStorage.removeItem(KEY);
    return null;
  } catch { return null; }
}

export function savePayload(value: ScoutPayload): void {
  localStorage.setItem(KEY, JSON.stringify({ ...value, source: 'export' }));
}

export function clearPayload(): void { localStorage.removeItem(KEY); }

export async function fetchLocal(): Promise<ScoutPayload | null> {
  try {
    const response = await fetch('/api/overview', { signal: AbortSignal.timeout(2500), cache: 'no-store' });
    if (!response.ok) return null;
    const value: unknown = await response.json();
    return validPayload(value) ? value : null;
  } catch { return null; }
}

export { demo };
