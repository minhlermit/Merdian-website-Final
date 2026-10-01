import { useSyncExternalStore } from 'react';
import type { ScoutEngine } from './ScoutEngine';

// Shared registry between page components (always loaded) and the lazily loaded 3D scene.
// Components register DOM anchors here; the scene reads them each frame. No React state is
// updated per frame.

export type SceneStatus = 'idle' | 'loading' | 'ready' | 'fallback';
export type SceneSlot = 'zone' | 'heroAnchor' | 'heroCopy' | 'storyAnchor' | 'storyText' | 'console';

class SceneBridge {
  status: SceneStatus = 'idle';
  engine: ScoutEngine | null = null;
  readonly slots = new Map<SceneSlot, HTMLElement>();
  readonly chapters: (HTMLElement | undefined)[] = [];
  readonly hotspots = new Map<string, HTMLElement>();
  private listeners = new Set<() => void>();
  private slotRefs = new Map<string, (el: HTMLElement | null) => void>();

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  };

  setStatus(status: SceneStatus) {
    if (this.status === status) return;
    this.status = status;
    this.listeners.forEach(listener => listener());
  }

  private cachedRef(key: string, set: (el: HTMLElement | null) => void) {
    let ref = this.slotRefs.get(key);
    if (!ref) { ref = set; this.slotRefs.set(key, ref); }
    return ref;
  }

  /** Stable callback ref that registers an element for a named slot. */
  slot(name: SceneSlot) {
    return this.cachedRef(`slot:${name}`, el => { if (el) this.slots.set(name, el); else this.slots.delete(name); });
  }

  chapter(index: number) {
    return this.cachedRef(`chapter:${index}`, el => { this.chapters[index] = el ?? undefined; });
  }

  hotspot(id: string) {
    return this.cachedRef(`hotspot:${id}`, el => { if (el) this.hotspots.set(id, el); else this.hotspots.delete(id); });
  }
}

export const sceneBridge = new SceneBridge();

export function useSceneStatus() {
  return useSyncExternalStore(sceneBridge.subscribe, () => sceneBridge.status, () => 'idle' as SceneStatus);
}

/** Cheap capability check that does not load three.js. */
export function canUseWebGL() {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    const ok = Boolean(gl);
    gl?.getExtension('WEBGL_lose_context')?.loseContext();
    return ok;
  } catch {
    return false;
  }
}
