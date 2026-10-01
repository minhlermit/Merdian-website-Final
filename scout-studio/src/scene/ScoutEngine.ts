import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { createScout, type ScoutRig } from './ScoutModel';
import { createBackground, type BackgroundRig } from './AnimatedBackground';
import { createProps, type PropsRig } from './EvidenceScene';
import {
  ADAPTIVE, HANDHELD_LIMIT, HOTSPOTS, MOTION, POSES, QUALITY, VIEW_ANGLES,
  type HotspotId, type Pose, type QualitySetting, type QualityTier, type ViewAngle,
} from './config';

export interface Rect { x: number; y: number; w: number; h: number }

export interface Layout {
  /** Where the subject should sit, in canvas CSS pixels. */
  anchor: Rect | null;
  /** Model units the anchor must fit horizontally (see CONTENT_WIDTH). */
  contentWidth: number;
  /** -1 hero, 0 discover … 4 deliver (fractional while scrolling). */
  story: number;
  /** 0–1: recede as the console takes over. */
  exit: number;
  /** 0–1: dim while resting behind page content. */
  rest: number;
  /** Text region kept calm in the background, canvas CSS pixels. */
  quiet: Rect | null;
}

export interface HotspotProjection { id: HotspotId; x: number; y: number; visible: boolean }
export interface FrameInfo { hotspots: HotspotProjection[]; story: number; exit: number }
export interface EngineStats {
  viewport: { w: number; h: number };
  devicePixelRatio: number;
  renderPixelRatio: number;
  buffer: { w: number; h: number };
  tier: QualityTier;
  setting: QualitySetting;
  fps: number;
  adaptiveNote: string;
}

export interface EngineOptions {
  canvas: HTMLCanvasElement;
  layout: () => Layout;
  quality?: QualitySetting;
  motion?: boolean;
  handheld?: boolean;
  showSubject?: boolean;
  showProps?: boolean;
  showOrbit?: boolean;
  onFrame?: (info: FrameInfo) => void;
  onFirstFrame?: () => void;
  onContextLost?: () => void;
}

const smoothstep = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const damp = (current: number, target: number, rate: number, dt: number) => current + (target - current) * (1 - Math.exp(-rate * dt));
const deg = (d: number) => (d * Math.PI) / 180;

function poseAt(progress: number): Pose {
  const i = Math.min(POSES.length - 1, Math.max(0, progress + 1));
  const a = Math.floor(i), b = Math.min(POSES.length - 1, a + 1);
  const t = smoothstep(0, 1, i - a);
  const A = POSES[a], B = POSES[b];
  return {
    yaw: A.yaw + (B.yaw - A.yaw) * t, pitch: A.pitch + (B.pitch - A.pitch) * t,
    x: A.x + (B.x - A.x) * t, y: A.y + (B.y - A.y) * t, scale: A.scale + (B.scale - A.scale) * t,
    lookUp: A.lookUp + (B.lookUp - A.lookUp) * t, roll: A.roll + (B.roll - A.roll) * t,
  };
}

export function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return Boolean(c.getContext('webgl2'));
  } catch {
    return false;
  }
}

export class ScoutEngine {
  private opts: EngineOptions;
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
  private stage = new THREE.Group();
  private content = new THREE.Group();
  private rig: ScoutRig;
  private props: PropsRig;
  private bg: BackgroundRig;
  private envTarget: THREE.WebGLRenderTarget;
  private keyLight: THREE.DirectionalLight;
  private raf = 0;
  private running = false;
  private disposed = false;
  private lastTime = 0;
  private clock = 0;
  private startedAt = 0;
  private firstFrame = false;
  private size = { w: 0, h: 0, dpr: 0 };

  // Settings
  private motion: boolean;
  private qualitySetting: QualitySetting;
  private tier: QualityTier;
  private adaptiveNote = 'Not needed';
  private frameTimes: number[] = [];
  private fps = 0;

  // Smoothed story state
  private story = -1;
  private exit = 0;
  private rest = 0;
  private storyInit = false;

  // Interaction state (refs, never React state)
  private yawUser = 0;
  private yawVelocity = 0;
  private yawTarget: number | null = null;
  private dragging = false;
  private gaze = { x: 0, y: 0, tx: 0, ty: 0 };
  private focusId: HotspotId | null = null;
  private blinkAt = 2;
  private blinkPhase = -1;
  private lastAnchorKey = '';
  private settled = false;

  private tmp = new THREE.Vector3();
  private tmp2 = new THREE.Vector3();
  private onLost = (event: Event) => {
    event.preventDefault();
    this.stop();
    this.opts.onContextLost?.();
  };

  constructor(opts: EngineOptions) {
    this.opts = opts;
    this.motion = opts.motion ?? true;
    this.qualitySetting = opts.quality ?? 'auto';
    this.tier = this.qualitySetting === 'auto' ? 'high' : this.qualitySetting;

    this.renderer = new THREE.WebGLRenderer({ canvas: opts.canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.toneMappingExposure = 1.02;
    this.renderer.autoClear = false;
    opts.canvas.addEventListener('webglcontextlost', this.onLost);

    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const room = new RoomEnvironment();
    this.envTarget = pmrem.fromScene(room, 0.04);
    room.dispose();
    pmrem.dispose();
    this.scene.environment = this.envTarget.texture;
    this.scene.environmentIntensity = 0.5;

    // Graphite / titanium studio lighting with a restrained amber accent.
    // Softer rim and kicker than v3: edges stay readable without hot specular lines on the jacket.
    this.keyLight = new THREE.DirectionalLight(0xffe4c4, 2.25);
    this.keyLight.position.set(-3.2, 4.2, 5.5);
    const rim = new THREE.DirectionalLight(0xbccbff, 1.85);
    rim.position.set(4.5, 2.4, -4.5);
    const kicker = new THREE.DirectionalLight(0xdfe6ee, 0.7);
    kicker.position.set(-5, 0.5, -2);
    const fill = new THREE.DirectionalLight(0xe6ecf2, 0.45);
    fill.position.set(2.5, -1.2, 6);
    const amber = new THREE.PointLight(0xffb45a, 6, 12, 2);
    amber.position.set(3.6, -0.6, -2.2);
    const hemi = new THREE.HemisphereLight(0x2c333a, 0x07090a, 0.7);
    this.scene.add(this.keyLight, rim, kicker, fill, amber, hemi);

    this.rig = createScout();
    this.props = createProps();
    this.bg = createBackground();
    this.content.add(this.rig.root, this.props.orbit, this.props.group);
    this.stage.add(this.content);
    this.scene.add(this.stage);
    this.rig.root.visible = opts.showSubject ?? true;
    this.props.group.visible = opts.showProps ?? true;
    this.props.orbit.visible = opts.showOrbit ?? true;
    this.camera.position.set(0, 0, 14);
  }

  // ---- lifecycle ---------------------------------------------------------------------------

  start() {
    if (this.running || this.disposed) return;
    this.running = true;
    this.lastTime = performance.now();
    if (!this.startedAt) this.startedAt = this.lastTime;
    const loop = (now: number) => {
      if (!this.running) return;
      this.raf = requestAnimationFrame(loop);
      const dt = Math.min(0.05, Math.max(0.001, (now - this.lastTime) / 1000));
      this.lastTime = now;
      this.frame(dt, now);
    };
    this.raf = requestAnimationFrame(loop);
  }

  stop() {
    this.running = false;
    cancelAnimationFrame(this.raf);
  }

  setActive(active: boolean) {
    if (active) this.start(); else this.stop();
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.stop();
    this.opts.canvas.removeEventListener('webglcontextlost', this.onLost);
    this.rig.dispose();
    this.props.dispose();
    this.bg.dispose();
    this.envTarget.dispose();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
  }

  // ---- settings ----------------------------------------------------------------------------

  setMotion(enabled: boolean) {
    this.motion = enabled;
    this.settled = false;
  }

  setQuality(setting: QualitySetting) {
    this.qualitySetting = setting;
    this.tier = setting === 'auto' ? 'high' : setting;
    this.adaptiveNote = setting === 'auto' ? 'Not needed' : 'Manual setting';
    this.frameTimes = [];
    this.size.w = 0; // force resize
    this.settled = false;
  }

  // ---- interaction -------------------------------------------------------------------------

  pointerAt(clientX: number, clientY: number) {
    const rect = this.opts.canvas.getBoundingClientRect();
    const anchor = this.opts.layout().anchor;
    const cx = anchor ? anchor.x + anchor.w / 2 : rect.width / 2;
    const cy = anchor ? anchor.y + anchor.h * 0.35 : rect.height / 2;
    this.gaze.tx = Math.max(-1, Math.min(1, (clientX - rect.left - cx) / (rect.width * 0.45)));
    this.gaze.ty = Math.max(-1, Math.min(1, (clientY - rect.top - cy) / (rect.height * 0.45)));
    this.settled = false;
  }

  pointerLeave() {
    this.gaze.tx = 0;
    this.gaze.ty = 0;
    this.settled = false;
  }

  dragStart() {
    this.dragging = true;
    this.yawVelocity = 0;
    this.yawTarget = null;
    this.settled = false;
  }

  dragMove(dxPx: number) {
    const limit = deg(MOTION.dragLimitDeg);
    let next = this.yawUser + dxPx * MOTION.dragSensitivity;
    if (Math.abs(next) > limit) next = this.yawUser + dxPx * MOTION.dragSensitivity * 0.25; // resistance past the limit
    const stretch = limit + deg(MOTION.dragOverscrollDeg);
    this.yawUser = Math.max(-stretch, Math.min(stretch, next));
    this.settled = false;
  }

  /** velocity in CSS px per millisecond */
  dragEnd(velocityPxPerMs: number) {
    this.dragging = false;
    this.yawVelocity = this.motion ? velocityPxPerMs * 1000 * MOTION.dragSensitivity * MOTION.dragReleaseGain : 0;
    this.settled = false;
  }

  nudge(direction: -1 | 1) {
    const limit = deg(MOTION.dragLimitDeg);
    const base = this.yawTarget ?? this.yawUser;
    this.yawTarget = Math.max(-limit, Math.min(limit, base + direction * deg(MOTION.keyboardStepDeg)));
    this.yawVelocity = 0;
    this.settled = false;
  }

  resetView() {
    this.yawTarget = 0;
    this.yawVelocity = 0;
    this.focusId = null;
    this.rig.highlight(null, 0);
    this.settled = false;
  }

  /** Present a named angle (asset lab). */
  setView(view: ViewAngle) {
    this.yawTarget = VIEW_ANGLES[view] - poseAt(this.story).yaw;
    this.yawVelocity = 0;
    this.settled = false;
  }

  focusHotspot(id: HotspotId | null) {
    this.focusId = id;
    if (id) {
      const facing: Record<HotspotId, number> = { lens: -0.28, signal: -1.1, rules: -0.08 };
      this.yawTarget = facing[id] - poseAt(this.story).yaw;
      this.yawVelocity = 0;
    } else {
      this.rig.highlight(null, 0);
    }
    this.settled = false;
  }

  stats(): EngineStats {
    const buffer = this.renderer.getDrawingBufferSize(new THREE.Vector2());
    return {
      viewport: { w: this.size.w, h: this.size.h },
      devicePixelRatio: window.devicePixelRatio || 1,
      renderPixelRatio: this.renderer.getPixelRatio(),
      buffer: { w: buffer.x, h: buffer.y },
      tier: this.tier,
      setting: this.qualitySetting,
      fps: Math.round(this.fps),
      adaptiveNote: this.adaptiveNote,
    };
  }

  /** Render front, three-quarter and side views of the subject to data URLs. */
  captureAngles(): Record<ViewAngle, string> {
    const saved = { yawUser: this.yawUser, target: this.yawTarget, props: this.props.group.visible };
    const out = {} as Record<ViewAngle, string>;
    this.props.group.visible = false;
    this.rig.head.rotation.set(0, 0, 0);
    for (const view of Object.keys(VIEW_ANGLES) as ViewAngle[]) {
      this.rig.root.rotation.y = VIEW_ANGLES[view];
      this.render();
      out[view] = this.opts.canvas.toDataURL('image/png');
    }
    this.props.group.visible = saved.props;
    this.yawUser = saved.yawUser;
    this.yawTarget = saved.target;
    this.settled = false;
    return out;
  }

  // ---- frame -------------------------------------------------------------------------------

  private limits() {
    const q = QUALITY[this.tier];
    if (!this.opts.handheld) return q;
    return { maxDpr: Math.min(q.maxDpr, HANDHELD_LIMIT.maxDpr), maxPixels: Math.min(q.maxPixels, HANDHELD_LIMIT.maxPixels) };
  }

  private resize() {
    const canvas = this.opts.canvas;
    const w = Math.max(1, canvas.clientWidth), h = Math.max(1, canvas.clientHeight);
    const lim = this.limits();
    let dpr = Math.min(window.devicePixelRatio || 1, lim.maxDpr);
    if (w * h * dpr * dpr > lim.maxPixels) dpr = Math.sqrt(lim.maxPixels / (w * h));
    dpr = Math.max(0.5, dpr);
    if (w === this.size.w && h === this.size.h && Math.abs(dpr - this.size.dpr) < 1e-3) return;
    this.size = { w, h, dpr };
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    const buffer = this.renderer.getDrawingBufferSize(new THREE.Vector2());
    this.bg.uniforms.uResolution.value.copy(buffer);
    this.bg.uniforms.uDpr.value = dpr;
    this.settled = false;
  }

  private adapt(dt: number) {
    this.fps = this.fps ? this.fps * 0.95 + (1 / dt) * 0.05 : 1 / dt;
    if (this.qualitySetting !== 'auto' || !this.motion) return;
    this.frameTimes.push(dt * 1000);
    if (this.frameTimes.length < ADAPTIVE.windowFrames) return;
    const avg = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
    this.frameTimes = [];
    if (avg > ADAPTIVE.slowFrameMs && this.tier !== 'low') {
      const from = this.tier;
      this.tier = this.tier === 'high' ? 'balanced' : 'low';
      this.adaptiveNote = `Reduced ${from} → ${this.tier} (average frame ${avg.toFixed(1)} ms)`;
      this.size.w = 0;
    }
  }

  private frame(dt: number, now: number) {
    this.resize();
    const layout = this.opts.layout();
    const motion = this.motion ? 1 : 0;
    if (motion) this.clock += dt;

    // Story state: smoothed when moving, snapped for reduced motion.
    if (!this.storyInit) { this.story = layout.story; this.exit = layout.exit; this.rest = layout.rest; this.storyInit = true; }
    const target = { story: layout.story, exit: layout.exit, rest: layout.rest };
    const storyMoving = Math.abs(this.story - target.story) > 1e-4 || Math.abs(this.exit - target.exit) > 1e-4 || Math.abs(this.rest - target.rest) > 1e-4;
    if (motion) {
      this.story = damp(this.story, target.story, MOTION.scrollSmoothing, dt);
      this.exit = damp(this.exit, target.exit, MOTION.scrollSmoothing, dt);
      this.rest = damp(this.rest, target.rest, MOTION.scrollSmoothing, dt);
    } else {
      this.story = target.story; this.exit = target.exit; this.rest = target.rest;
    }

    const anchorKey = layout.anchor ? `${layout.anchor.x.toFixed(1)},${layout.anchor.y.toFixed(1)},${layout.anchor.w.toFixed(1)},${layout.anchor.h.toFixed(1)}` : '-';
    const gazeMoving = Math.abs(this.gaze.x - this.gaze.tx) > 1e-4 || Math.abs(this.gaze.y - this.gaze.ty) > 1e-4;
    const yawMoving = this.dragging || Math.abs(this.yawVelocity) > 1e-4 || this.yawTarget !== null;
    const introT = motion ? Math.min(1, (now - this.startedAt) / MOTION.heroSettleMs) : 1;
    const sweepT = motion ? Math.min(1, (now - this.startedAt) / MOTION.lightSweepMs) : 1;
    const active = motion || storyMoving || gazeMoving || yawMoving || sweepT < 1 || anchorKey !== this.lastAnchorKey || !this.settled;
    this.lastAnchorKey = anchorKey;
    if (!active && this.firstFrame) return;
    this.settled = !(storyMoving || gazeMoving || yawMoving);

    // Rotation physics
    const limit = deg(MOTION.dragLimitDeg);
    if (!this.dragging) {
      if (this.yawTarget !== null) {
        this.yawUser = motion ? damp(this.yawUser, this.yawTarget, 8, dt) : this.yawTarget;
        if (Math.abs(this.yawUser - this.yawTarget) < 1e-3) { this.yawUser = this.yawTarget; this.yawTarget = null; }
      } else {
        this.yawUser += this.yawVelocity * dt;
        this.yawVelocity *= Math.exp(-MOTION.dragInertiaDecay * dt);
        if (Math.abs(this.yawVelocity) < 1e-3) this.yawVelocity = 0;
        if (Math.abs(this.yawUser) > limit) {
          this.yawVelocity = 0;
          this.yawUser = damp(this.yawUser, Math.sign(this.yawUser) * limit, MOTION.dragSpring, dt);
        }
      }
    }

    // Gaze
    this.gaze.x = motion ? damp(this.gaze.x, this.gaze.tx, MOTION.gazeSmoothing, dt) : this.gaze.tx;
    this.gaze.y = motion ? damp(this.gaze.y, this.gaze.ty, MOTION.gazeSmoothing, dt) : this.gaze.ty;

    // Blink
    if (motion) {
      if (this.blinkPhase < 0 && this.clock > this.blinkAt) this.blinkPhase = 0;
      if (this.blinkPhase >= 0) {
        this.blinkPhase += dt / 0.16;
        const s = this.blinkPhase < 1 ? 1 - Math.sin(this.blinkPhase * Math.PI) * 0.9 : 1;
        for (const e of this.rig.eyes) e.scale.y = s;
        if (this.blinkPhase >= 1) {
          this.blinkPhase = -1;
          const [a, b] = MOTION.blinkEverySeconds;
          this.blinkAt = this.clock + a + Math.random() * (b - a);
        }
      }
    } else {
      for (const e of this.rig.eyes) e.scale.y = 1;
    }

    // Stage: place the framing box inside the anchor.
    const { w, h } = this.size;
    const visibleH = 2 * this.camera.position.z * Math.tan(deg(this.camera.fov / 2));
    const k = visibleH / h;
    const frame = this.rig.frame;
    const frameH = frame.top - frame.bottom;
    const anchor = layout.anchor ?? { x: w * 0.5, y: 0, w: w * 0.5, h };
    const fit = Math.min((anchor.h * k) / frameH, (anchor.w * k) / layout.contentWidth);
    const ease = 1 - Math.pow(1 - introT, 3);
    this.stage.position.set((anchor.x + anchor.w / 2 - w / 2) * k, -(anchor.y + anchor.h / 2 - h / 2) * k, 0);
    this.stage.scale.setScalar(fit * (1 - this.exit * 0.12));
    this.content.position.y = -(frame.top + frame.bottom) / 2;

    const pose = poseAt(this.story);
    const root = this.rig.root;
    root.position.set(pose.x, pose.y - (1 - ease) * 0.3 + Math.sin(this.clock * 1.05) * 0.018 * motion, -this.exit * 1.5);
    root.scale.setScalar(pose.scale * (0.92 + 0.08 * ease));
    root.rotation.set(pose.pitch, pose.yaw + this.yawUser - (1 - ease) * 0.55, 0);
    this.rig.body.scale.set(1, 1 + Math.sin(this.clock * 1.6) * 0.004 * motion, 1);
    const tilt = deg(MOTION.pointerTiltDeg);
    this.rig.head.rotation.set(
      -pose.lookUp + this.gaze.y * tilt * 0.6 + Math.sin(this.clock * 0.7) * 0.015 * motion,
      this.gaze.x * tilt + Math.sin(this.clock * 0.5) * 0.03 * motion,
      pose.roll + Math.sin(this.clock * 0.45) * 0.01 * motion,
    );
    this.keyLight.intensity = 1.6 + 0.8 * ease;

    this.props.orbit.position.copy(root.position);
    this.props.orbit.scale.setScalar(root.scale.x);
    this.props.update(this.story, this.clock, motion, this.exit);

    const pulse = this.focusId ? 0.65 + 0.35 * Math.sin(this.clock * 4) * motion : 0;
    this.rig.highlight(this.focusId, pulse);

    // Background
    const u = this.bg.uniforms;
    u.uTime.value = this.clock;
    u.uStory.value = this.story;
    u.uIntro.value = sweepT;
    u.uExit.value = this.exit;
    u.uRest.value = this.rest;
    u.uSubject.value.set((anchor.x + anchor.w / 2) / w, 1 - (anchor.y + anchor.h * 0.4) / h);
    if (layout.quiet) {
      const q = layout.quiet;
      u.uQuiet.value.set(q.x / w, 1 - (q.y + q.h) / h, (q.x + q.w) / w, 1 - q.y / h);
    } else {
      u.uQuiet.value.set(-1, -1, -1, -1);
    }

    this.render();
    this.adapt(dt);

    if (!this.firstFrame) { this.firstFrame = true; this.opts.onFirstFrame?.(); }
    this.opts.onFrame?.({ hotspots: this.projectHotspots(), story: this.story, exit: this.exit });
  }

  private render() {
    this.renderer.clear();
    this.renderer.render(this.bg.scene, this.bg.camera);
    this.renderer.render(this.scene, this.camera);
  }

  private projectHotspots(): HotspotProjection[] {
    const { w, h } = this.size;
    this.scene.updateMatrixWorld();
    return HOTSPOTS.map(({ id }) => {
      const spot = this.rig.hotspots[id];
      const world = spot.anchor.getWorldPosition(this.tmp);
      const normal = this.tmp2.copy(spot.normal).transformDirection(spot.anchor.matrixWorld);
      const toCamera = this.camera.position.clone().sub(world).normalize();
      const facing = normal.dot(toCamera);
      const ndc = world.clone().project(this.camera);
      return { id, x: (ndc.x * 0.5 + 0.5) * w, y: (-ndc.y * 0.5 + 0.5) * h, visible: this.rig.root.visible && facing > 0.12 && ndc.z < 1 };
    });
  }
}
