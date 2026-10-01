import { Component, lazy, Suspense, useEffect, useState, type ReactNode } from 'react';
import { canUseWebGL, sceneBridge, useSceneStatus } from '../scene/bridge';

const ScoutStage = lazy(() => import('../scene/ScoutStage'));

class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { sceneBridge.setStatus('fallback'); }
  render() { return this.state.failed ? null : this.props.children; }
}

/**
 * Fixed layer behind the hero and story. Shows a static poster background immediately, then
 * loads the WebGL scene after first paint. Never intercepts pointer input.
 */
export function SceneLayer() {
  const status = useSceneStatus();
  const [load, setLoad] = useState(false);

  useEffect(() => {
    if (!canUseWebGL()) { sceneBridge.setStatus('fallback'); return; }
    sceneBridge.setStatus('loading');
    const begin = () => setLoad(true);
    if ('requestIdleCallback' in window) {
      const id = window.requestIdleCallback(begin, { timeout: 900 });
      return () => window.cancelIdleCallback(id);
    }
    const id = setTimeout(begin, 250);
    return () => clearTimeout(id);
  }, []);

  return <div className={`scene-layer is-${status}`} aria-hidden="true">
    <div className="scene-poster" />
    {load && status !== 'fallback' && <SceneBoundary><Suspense fallback={null}><ScoutStage /></Suspense></SceneBoundary>}
  </div>;
}
