import { demo } from '../data/demo';
import type { ScoutPayload } from '../types';

export const SIX_HOURS = 6 * 60 * 60;
export const windowStart = (time = Date.now() / 1000) => Math.floor(time / SIX_HOURS) * SIX_HOURS;
export const nextWindow = (time = Date.now() / 1000) => windowStart(time) + SIX_HOURS;
export const isCurrent = (generated: number) => Number.isFinite(generated) && generated >= windowStart();

export function countdown(time = Date.now() / 1000) {
  const left = Math.max(0, Math.floor(nextWindow(time) - time));
  return [Math.floor(left / 3600), Math.floor(left % 3600 / 60), left % 60].map(x => String(x).padStart(2,'0')).join(':');
}

export function freshDemo(): ScoutPayload {
  const now = Date.now() / 1000;
  return { ...demo, generated: windowStart(now),
    candidates: demo.candidates.map(c => ({...c, updated: now - (demo.generated - (c.updated || demo.generated))})),
    events: demo.events.map(e => ({...e, time: now - (demo.generated - e.time)})),
  };
}

export function emptyDemo(): ScoutPayload {
  return {...freshDemo(), candidates:[], events:[], warnings:['The six-hour candidate window reset. Run the guided demo to view a fictional scenario, or connect a fresh Scout export.']};
}
