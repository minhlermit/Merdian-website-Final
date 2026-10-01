import * as THREE from 'three';
import { PALETTE } from './config';

// Supporting story objects around the Scout. Every state is a pure function of story
// progress p (-1 hero, 0 discover … 4 deliver), so scrolling reverses cleanly.
// These are explanatory illustrations, not live market data.

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const v3 = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);

function random(seed: number) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Level = 'VERIFIED ON-CHAIN' | 'LIKELY' | 'UNCONFIRMED' | 'CONFLICT';
const LEVEL_COLOUR: Record<Level, string> = { 'VERIFIED ON-CHAIN': '#a9d3b7', LIKELY: '#e8b368', UNCONFIRMED: '#8f9a9c', CONFLICT: '#ed9074' };

interface PanelSpec { tag: string; title: string; rows: [string, Level][]; }
const PANELS: PanelSpec[] = [
  { tag: 'EVIDENCE 01 · CLAIM', title: 'Official stock pair?', rows: [['Pair contract', 'VERIFIED ON-CHAIN'], ['Issuer statement', 'LIKELY'], ['Listing claim', 'UNCONFIRMED']] },
  { tag: 'EVIDENCE 02 · POOL', title: 'Depth and holders', rows: [['Pool liquidity', 'VERIFIED ON-CHAIN'], ['Top-10 share', 'VERIFIED ON-CHAIN'], ['Team wallets', 'CONFLICT']] },
  { tag: 'EVIDENCE 03 · CONTROLS', title: 'Contract permissions', rows: [['Mint authority', 'VERIFIED ON-CHAIN'], ['Upgradeability', 'LIKELY'], ['Pause switch', 'UNCONFIRMED']] },
];

const MONO = '"Geist Mono", ui-monospace, SFMono-Regular, Menlo, monospace';
const SANS = '"Geist", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif';

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function panelSurface(ctx: CanvasRenderingContext2D, w: number, h: number) {
  ctx.clearRect(0, 0, w, h);
  roundRect(ctx, 4, 4, w - 8, h - 8, 26);
  const grad = ctx.createLinearGradient(0, 0, w, h);
  grad.addColorStop(0, 'rgba(26,32,37,0.9)');
  grad.addColorStop(1, 'rgba(12,16,19,0.84)');
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = 'rgba(232,179,104,0.55)';
  ctx.stroke();
}

function drawEvidence(ctx: CanvasRenderingContext2D, spec: PanelSpec, w: number, h: number) {
  panelSurface(ctx, w, h);
  ctx.fillStyle = '#e8b368';
  ctx.font = `500 26px ${MONO}`;
  ctx.fillText(spec.tag, 48, 70);
  ctx.fillStyle = '#f2efe7';
  ctx.font = `560 50px ${SANS}`;
  ctx.fillText(spec.title, 48, 140);
  spec.rows.forEach(([label, level], i) => {
    const y = 220 + i * 118;
    ctx.fillStyle = 'rgba(255,255,255,0.08)';
    ctx.fillRect(48, y - 40, w - 96, 2);
    ctx.fillStyle = '#c9cfcc';
    ctx.font = `450 34px ${SANS}`;
    ctx.fillText(label, 48, y + 22);
    ctx.fillStyle = LEVEL_COLOUR[level];
    ctx.beginPath();
    ctx.arc(w - 390, y + 10, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = `500 24px ${MONO}`;
    ctx.fillText(level, w - 364, y + 19);
  });
}

function drawReport(ctx: CanvasRenderingContext2D, w: number, h: number) {
  panelSurface(ctx, w, h);
  ctx.fillStyle = '#e8b368';
  ctx.font = `500 28px ${MONO}`;
  ctx.fillText('DELIVER · INVESTOR MEMO', 56, 84);
  ctx.fillStyle = '#f2efe7';
  ctx.font = `560 62px ${SANS}`;
  ctx.fillText('One report.', 56, 172);
  ctx.fillText('Clear reasons.', 56, 244);
  const sections = ['Thesis', 'Evidence ledger', 'Risk flags', 'What could change it'];
  sections.forEach((label, i) => {
    const y = 350 + i * 190;
    ctx.fillStyle = '#9aa4a3';
    ctx.font = `500 26px ${MONO}`;
    ctx.fillText(`0${i + 1}  ${label.toUpperCase()}`, 56, y);
    ctx.fillStyle = 'rgba(242,239,231,0.16)';
    for (let k = 0; k < 3; k++) {
      const lw = (w - 112) * (k === 2 ? 0.58 : 0.92 - k * 0.07);
      roundRect(ctx, 56, y + 30 + k * 38, lw, 16, 8);
      ctx.fill();
    }
  });
  ctx.fillStyle = 'rgba(169,211,183,0.9)';
  ctx.font = `500 24px ${MONO}`;
  ctx.fillText('SCORE FROM CORE · EXIT-RISK FLOOR APPLIED', 56, h - 110);
  ctx.fillStyle = '#7d8786';
  ctx.fillText('ILLUSTRATION · NOT LIVE DATA', 56, h - 66);
}

function canvasTexture(w: number, h: number, draw: (ctx: CanvasRenderingContext2D) => void) {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;
  draw(ctx);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return { texture, redraw: () => { draw(ctx); texture.needsUpdate = true; } };
}

/** A tube whose index order follows the path, so drawRange can "draw" it progressively. */
function pathTube(curve: THREE.Curve<THREE.Vector3>, segments: number, radius: number, material: THREE.Material) {
  const geometry = new THREE.TubeGeometry(curve, segments, radius, 5, false);
  const mesh = new THREE.Mesh(geometry, material);
  const total = geometry.getIndex()!.count;
  return { mesh, reveal(amount: number) { geometry.setDrawRange(0, Math.floor((total * Math.min(1, Math.max(0, amount))) / 6) * 6); } };
}

export interface PropsRig {
  group: THREE.Group;
  orbit: THREE.Group;
  update(p: number, time: number, motion: number, exit: number): void;
  dispose(): void;
}

export function createProps(): PropsRig {
  const disposables: { dispose(): void }[] = [];
  const keep = <T extends { dispose(): void }>(x: T) => (disposables.push(x), x);
  const group = new THREE.Group();
  group.name = 'story-props';
  const rand = random(19);

  // Signal orbit / scanner around the Scout's head.
  const orbit = new THREE.Group();
  const ringMat = keep(new THREE.MeshStandardMaterial({ color: 0x3a434c, metalness: 1, roughness: 0.35, transparent: true, opacity: 0.5 }));
  const ringMatThin = keep(new THREE.MeshStandardMaterial({ color: PALETTE.titanium, metalness: 0.8, roughness: 0.4, transparent: true, opacity: 0.18 }));
  const ringA = new THREE.Mesh(keep(new THREE.TorusGeometry(2.05, 0.011, 8, 220)), ringMat);
  const ringB = new THREE.Mesh(keep(new THREE.TorusGeometry(2.45, 0.006, 6, 220)), ringMatThin);
  const tiltA = new THREE.Group();
  tiltA.rotation.set(0.32, -0.55, 0.28);
  tiltA.position.set(0.1, 0.35, -1.5);
  const tiltB = new THREE.Group();
  tiltB.rotation.set(0.5, 0.6, -0.2);
  tiltB.position.set(0.1, 0.3, -1.8);
  tiltA.add(ringA);
  tiltB.add(ringB);
  const arcMat = keep(new THREE.MeshBasicMaterial({ color: new THREE.Color(PALETTE.amberHot).multiplyScalar(0.9), transparent: true, opacity: 0.6, toneMapped: false }));
  const arcCurve = new THREE.EllipseCurve(0, 0, 2.05, 2.05, 0, 0.95, false, 0);
  const arcPath = new THREE.CatmullRomCurve3(arcCurve.getPoints(40).map(p => v3(p.x, p.y, 0)));
  const arcSpin = new THREE.Group();
  arcSpin.add(new THREE.Mesh(keep(new THREE.TubeGeometry(arcPath, 64, 0.02, 6)), arcMat));
  tiltA.add(arcSpin);
  const dotGeo = keep(new THREE.SphereGeometry(0.026, 12, 8));
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2 + 0.4;
    const dot = new THREE.Mesh(dotGeo, arcMat);
    dot.position.set(Math.cos(a) * 2.05, Math.sin(a) * 2.05, 0);
    tiltA.add(dot);
  }
  orbit.add(tiltA, tiltB);
  // Evidence objects sit a little closer to the subject and slightly larger than their authoring units.
  group.position.set(-0.62, 0.02, 0);
  group.scale.setScalar(1.14);

  // Signal nodes: scattered → collected on the scanner ring; node 0 becomes the focus.
  const NODE_COUNT = 22;
  const nodeGeo = keep(new THREE.SphereGeometry(0.034, 14, 10));
  const nodeMat = keep(new THREE.MeshBasicMaterial({ color: 0x8b969f, transparent: true, opacity: 0, toneMapped: false }));
  const nodes = new THREE.InstancedMesh(nodeGeo, nodeMat, NODE_COUNT - 1);
  nodes.frustumCulled = false;
  group.add(nodes);
  const scatter: THREE.Vector3[] = [], collected: THREE.Vector3[] = [], drift: number[] = [];
  tiltA.updateMatrix();
  for (let i = 0; i < NODE_COUNT; i++) {
    scatter.push(v3(-3.8 + rand() * 7.8, -2.3 + rand() * 4.6, -2.6 + rand() * 3.2));
    const a = (i / NODE_COUNT) * Math.PI * 2 + rand() * 0.2;
    collected.push(v3(Math.cos(a) * 2.05, Math.sin(a) * 2.05, 0).applyMatrix4(tiltA.matrix));
    drift.push(rand() * Math.PI * 2);
  }
  const focusMat = keep(new THREE.MeshBasicMaterial({ color: 0x9aa4ad, transparent: true, opacity: 0, toneMapped: false }));
  const focus = new THREE.Mesh(nodeGeo, focusMat);
  const haloMat = keep(new THREE.MeshBasicMaterial({ color: PALETTE.amber, transparent: true, opacity: 0, depthWrite: false, toneMapped: false }));
  const halo = new THREE.Mesh(keep(new THREE.RingGeometry(0.09, 0.105, 48)), haloMat);
  group.add(focus, halo);
  const FOCUS_POS = v3(1.0, 0.62, 0.55);

  // Evidence layers
  const panelGeo = keep(new THREE.PlaneGeometry(1.5, 0.9));
  const textures = PANELS.map(spec => canvasTexture(1024, 620, ctx => drawEvidence(ctx, spec, 1024, 620)));
  textures.forEach(t => keep(t.texture));
  const panels = textures.map(t => {
    const m = new THREE.Mesh(panelGeo, keep(new THREE.MeshBasicMaterial({ map: t.texture, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, toneMapped: false })));
    group.add(m);
    return m;
  });
  const report = canvasTexture(1024, 1320, ctx => drawReport(ctx, 1024, 1320));
  keep(report.texture);
  const reportMat = keep(new THREE.MeshBasicMaterial({ map: report.texture, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }));
  const reportMesh = new THREE.Mesh(keep(new THREE.PlaneGeometry(1.55, 2.0)), reportMat);
  reportMesh.position.set(2.05, 0.05, 0.2);
  reportMesh.rotation.y = -0.12;
  group.add(reportMesh);
  if (typeof document !== 'undefined' && document.fonts) {
    Promise.all([document.fonts.load(`500 26px ${MONO}`), document.fonts.load(`560 50px ${SANS}`)])
      .then(() => { textures.forEach(t => t.redraw()); report.redraw(); })
      .catch(() => { /* fallback fonts already drawn */ });
  }

  // Research paths
  const pathMat = keep(new THREE.MeshBasicMaterial({ color: 0xa3adb6, transparent: true, opacity: 0, toneMapped: false }));
  const ENDPOINTS = [v3(2.55, 1.4, -0.3), v3(3.05, 0.6, 0.15), v3(2.9, -0.3, -0.2), v3(2.35, -1.1, 0.25)];
  const endMat = keep(new THREE.MeshBasicMaterial({ color: PALETTE.titanium, transparent: true, opacity: 0, toneMapped: false }));
  const endGeo = keep(new THREE.TorusGeometry(0.075, 0.011, 8, 36));
  const paths = ENDPOINTS.map(end => {
    const mid = FOCUS_POS.clone().lerp(end, 0.5).add(v3(0.15, 0.22, 0.35));
    const curve = new THREE.QuadraticBezierCurve3(FOCUS_POS.clone(), mid, end);
    const tube = pathTube(curve, 64, 0.009, pathMat);
    keep(tube.mesh.geometry);
    const ring = new THREE.Mesh(endGeo, endMat);
    ring.position.copy(end);
    group.add(tube.mesh, ring);
    return { curve, tube, ring };
  });

  // Scoring frame, exit-risk floor and completion gate
  const frameMat = keep(new THREE.MeshStandardMaterial({ color: PALETTE.titanium, metalness: 0.9, roughness: 0.3, transparent: true, opacity: 0 }));
  const frame = new THREE.Group();
  frame.position.set(2.05, 0.05, 0.05);
  const FW = 1.8, FH = 2.4, bar = 0.018;
  const hBar = keep(new THREE.BoxGeometry(FW, bar, bar)), vBar = keep(new THREE.BoxGeometry(bar, FH, bar)), tick = keep(new THREE.BoxGeometry(0.09, 0.008, 0.008));
  for (const y of [FH / 2, -FH / 2]) { const m = new THREE.Mesh(hBar, frameMat); m.position.y = y; frame.add(m); }
  for (const x of [FW / 2, -FW / 2]) { const m = new THREE.Mesh(vBar, frameMat); m.position.x = x; frame.add(m); }
  for (let i = 0; i < 9; i++) { const m = new THREE.Mesh(tick, frameMat); m.position.set(-FW / 2 - 0.06, -FH / 2 + (i / 8) * FH, 0); frame.add(m); }
  group.add(frame);
  const floorMat = keep(new THREE.MeshBasicMaterial({ color: new THREE.Color(PALETTE.amber).multiplyScalar(1.05), transparent: true, opacity: 0, toneMapped: false }));
  const floor = new THREE.Mesh(keep(new THREE.BoxGeometry(FW + 0.3, 0.024, 0.024)), floorMat);
  group.add(floor);
  const gateMat = keep(new THREE.MeshBasicMaterial({ color: PALETTE.amber, transparent: true, opacity: 0, toneMapped: false }));
  const gateCurve = new THREE.CatmullRomCurve3(new THREE.EllipseCurve(0, 0, 0.2, 0.2, Math.PI / 2, Math.PI / 2 + Math.PI * 2 - 0.001, false, 0).getPoints(64).map(p => v3(p.x, p.y, 0)));
  const gate = pathTube(gateCurve, 96, 0.016, gateMat);
  keep(gate.mesh.geometry);
  gate.mesh.position.set(2.05 + FW / 2 + 0.05, 0.05 + FH / 2 + 0.05, 0.08);
  const gateDotMat = keep(new THREE.MeshBasicMaterial({ color: PALETTE.mint, transparent: true, opacity: 0, toneMapped: false }));
  const gateDot = new THREE.Mesh(keep(new THREE.SphereGeometry(0.06, 16, 12)), gateDotMat);
  gateDot.position.copy(gate.mesh.position);
  group.add(gate.mesh, gateDot);

  const mat4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = v3(), pos = v3(), tmp = v3();
  const amber = new THREE.Color(PALETTE.amber), dim = new THREE.Color(0x9aa4ad), mint = new THREE.Color(PALETTE.mint);

  return {
    group,
    orbit,
    update(p, time, motion, exit) {
      const live = 1 - exit;
      // Orbit: always present, spins a little faster while discovering.
      const discover = smooth(-0.6, 0.3, p) * (1 - smooth(1.0, 1.8, p));
      arcSpin.rotation.z = time * (0.35 + discover * 0.9) * motion;
      tiltB.rotation.z = -0.2 + time * 0.05 * motion;
      ringMat.opacity = 0.5 * live;
      ringMatThin.opacity = 0.18 * live;
      arcMat.opacity = (0.42 + 0.33 * discover) * live;

      // Nodes
      const ambient = 0.16 * (1 - smooth(-1, -0.4, p));
      const storyNodes = smooth(-0.8, -0.1, p) * (1 - smooth(1.2, 1.9, p));
      nodeMat.opacity = Math.max(ambient, storyNodes * 0.5) * live;
      // Ring positions live in the parent (content) space; convert into this group's space.
      const onRing = (i: number) => tmp.copy(collected[i]).multiplyScalar(orbit.scale.x).add(orbit.position).sub(group.position).divideScalar(group.scale.x);
      for (let i = 1; i < NODE_COUNT; i++) {
        const c = smooth(-0.6 + i * 0.012, 0.3 + i * 0.012, p);
        pos.copy(scatter[i]).lerp(onRing(i), c);
        pos.y += Math.sin(time * 0.6 + drift[i]) * 0.05 * motion * (1 - c);
        q.identity();
        sc.setScalar(0.8 + 0.4 * c);
        mat4.compose(pos, q, sc);
        nodes.setMatrixAt(i - 1, mat4);
      }
      nodes.instanceMatrix.needsUpdate = true;

      // Focus node path through the story
      const chosen = smooth(0.15, 0.6, p);
      pos.copy(scatter[0]).lerp(onRing(0), smooth(-0.6, 0.3, p));
      pos.lerp(FOCUS_POS, smooth(0.55, 1.15, p));
      if (p > 1.85 && p < 2.65) {
        const s = (p - 1.85) / 0.8;
        const k = Math.min(3, Math.floor(s * 4));
        const f = s * 4 - k;
        paths[k].curve.getPoint(f < 0.5 ? f * 2 : (1 - f) * 2, tmp);
        pos.copy(tmp);
      }
      pos.lerp(gate.mesh.position, smooth(2.85, 3.3, p));
      pos.lerp(reportMesh.position, smooth(3.6, 4.1, p));
      focus.position.copy(pos);
      focus.scale.setScalar(1 + chosen * 1.3 - smooth(3.6, 4.1, p) * 1.6);
      focusMat.color.copy(dim).lerp(amber, chosen);
      focusMat.opacity = Math.max(ambient, smooth(-0.8, -0.1, p) * (1 - smooth(3.9, 4.2, p))) * live;
      halo.position.copy(pos);
      halo.scale.setScalar(1 + chosen * 0.8 + Math.sin(time * 2.4) * 0.12 * motion);
      halo.quaternion.identity();
      haloMat.opacity = chosen * (1 - smooth(3.6, 4.0, p)) * 0.65 * live;

      // Evidence layers
      const wV = (i: number) => smooth(0.45 + i * 0.1, 1.05 + i * 0.1, p);
      const wI = smooth(1.45, 1.9, p);
      const wE = smooth(2.55, 3.2, p);
      const wD = smooth(3.45, 3.95, p);
      panels.forEach((panel, i) => {
        const v = wV(i);
        const verifyPos = v3(1.55 + i * 0.3, 0.78 - i * 0.62, 0.35 - i * 0.3).add(v3((1 - v) * 1.4, 0, 0));
        const investigatePos = verifyPos.clone().add(v3(0.35, 0, -0.75));
        const evaluatePos = v3(2.05, 0.8 - i * 0.72, 0.1);
        panel.position.copy(verifyPos).lerp(investigatePos, wI * (1 - wE)).lerp(evaluatePos, wE).lerp(reportMesh.position, wD);
        panel.rotation.y = -0.42 * (1 - wE) - 0.12 * wE;
        panel.scale.setScalar((1 - 0.08 * wE) * (1 - 0.45 * wD));
        (panel.material as THREE.MeshBasicMaterial).opacity = v * (1 - 0.62 * wI * (1 - wE)) * (1 - wD) * live;
      });

      // Research paths
      const pathFade = 1 - smooth(2.7, 3.1, p);
      pathMat.opacity = smooth(1.4, 1.75, p) * pathFade * 0.8 * live;
      endMat.opacity = smooth(1.5, 1.95, p) * pathFade * live;
      paths.forEach((path, k) => {
        const r = smooth(1.5 + k * 0.1, 1.95 + k * 0.1, p);
        path.tube.reveal(r);
        path.ring.scale.setScalar(0.4 + 0.6 * r);
      });
      endMat.color.copy(dim).lerp(amber, smooth(1.9, 2.3, p));

      // Frame, floor, gate
      const frameIn = wE * (1 - wD * 0.85);
      frameMat.opacity = frameIn * live;
      frame.scale.setScalar(0.94 + 0.06 * wE);
      floorMat.opacity = frameIn * live;
      floor.position.set(2.05, -1.62 + 0.45 * wE, 0.05);
      const gateAmount = smooth(3.0, 3.45, p);
      gate.reveal(gateAmount);
      gateMat.opacity = frameIn * live;
      gateMat.color.copy(amber).lerp(mint, smooth(0.9, 1, gateAmount));
      gateDotMat.opacity = smooth(0.92, 1, gateAmount) * frameIn * live;

      // Report
      reportMat.opacity = smooth(3.55, 4.05, p) * live;
      reportMesh.position.z = 0.2 + (1 - smooth(3.55, 4.05, p)) * 0.4;
    },
    dispose() { for (const d of disposables) d.dispose(); nodes.dispose(); },
  };
}
