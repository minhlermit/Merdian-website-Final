import * as THREE from 'three';
import { PALETTE, type HotspotId } from './config';

// Procedural Scout: a real mesh built at runtime from the supplied avatar's identity cues
// (silver hair over a dark underlayer, rimless glasses, capsule eyes, blush, silver hoop,
// black high-collar zip jacket). Units: the head is roughly one unit in radius.

const v3 = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);

function random(seed: number) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

// ---- Head surface --------------------------------------------------------------------------

/** Maps a unit direction to the chibi head surface: fuller cheeks, softly flattened crown and chin. */
export function deformHead(u: THREE.Vector3, out = new THREE.Vector3()) {
  const y = u.y;
  const cheek = 1 + 0.07 * Math.exp(-((y + 0.35) ** 2) / 0.08);
  const jaw = 1 + 0.03 * Math.exp(-((y + 0.3) ** 2) / 0.1);
  const sy = 0.915 + 0.015 * Math.tanh(y * 4);
  return out.set(u.x * 1.07 * cheek, y * sy, u.z * 0.98 * jaw);
}

/** Surface point and outward normal for a direction from the head centre. */
export function headSurface(dir: THREE.Vector3) {
  const u = dir.clone().normalize();
  const p = deformHead(u);
  const axis = Math.abs(u.y) > 0.9 ? v3(1, 0, 0) : v3(0, 1, 0);
  const t1 = axis.cross(u).normalize();
  const t2 = u.clone().cross(t1).normalize();
  const e = 1e-3;
  const p1 = deformHead(u.clone().addScaledVector(t1, e).normalize()).sub(p);
  const p2 = deformHead(u.clone().addScaledVector(t2, e).normalize()).sub(p);
  const n = p1.cross(p2).normalize();
  if (n.dot(u) < 0) n.negate();
  return { p, n };
}

function weldNormals(g: THREE.BufferGeometry) {
  g.computeVertexNormals();
  const pos = g.getAttribute('position');
  const nor = g.getAttribute('normal');
  const groups = new Map<string, number[]>();
  for (let i = 0; i < pos.count; i++) {
    const key = `${pos.getX(i).toFixed(4)},${pos.getY(i).toFixed(4)},${pos.getZ(i).toFixed(4)}`;
    const list = groups.get(key);
    if (list) list.push(i); else groups.set(key, [i]);
  }
  const n = v3();
  for (const ids of groups.values()) {
    if (ids.length < 2) continue;
    n.set(0, 0, 0);
    for (const i of ids) n.x += nor.getX(i), n.y += nor.getY(i), n.z += nor.getZ(i);
    n.normalize();
    for (const i of ids) nor.setXYZ(i, n.x, n.y, n.z);
  }
  nor.needsUpdate = true;
}

function headGeometry(widthSegments: number, heightSegments: number) {
  const g = new THREE.SphereGeometry(1, widthSegments, heightSegments);
  g.rotateY(-Math.PI / 2); // keeps the sphere seam at the back, under the hair
  const pos = g.getAttribute('position');
  const unit = new Float32Array(pos.array as ArrayLike<number>);
  const u = v3(), o = v3();
  for (let i = 0; i < pos.count; i++) {
    u.fromBufferAttribute(pos, i);
    deformHead(u, o);
    pos.setXYZ(i, o.x, o.y, o.z);
  }
  weldNormals(g);
  return { g, unit };
}

// Hairline height (unit-sphere y) by absolute azimuth: high forehead, temples, sideburns in
// front of the ear, hair over the ear, then down to the nape.
const HAIRLINE: [number, number][] = [
  [0, 0.5], [0.5, 0.44], [0.95, 0.2], [1.22, -0.02], [1.4, -0.2], [1.5, 0.13], [1.78, 0.08], [2.2, -0.45], [Math.PI, -0.62],
];
function hairlineY(azimuth: number) {
  const x = Math.abs(azimuth);
  for (let i = 1; i < HAIRLINE.length; i++) {
    const [x1, y1] = HAIRLINE[i];
    if (x <= x1) {
      const [x0, y0] = HAIRLINE[i - 1];
      return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
    }
  }
  return HAIRLINE[HAIRLINE.length - 1][1];
}
function zigzag(azimuth: number, teeth = 11, amplitude = 0.045) {
  const s = (((azimuth * teeth) / Math.PI) % 2 + 2) % 2;
  return (Math.abs(s - 1) - 0.5) * 2 * amplitude;
}
function isScalp(u: THREE.Vector3, margin = 0) {
  const a = Math.atan2(u.x, u.z);
  return u.y > hairlineY(a) + zigzag(a) + margin;
}

// ---- Hair locks -------------------------------------------------------------------------------

interface LockOptions { length: number; width: number; thick: number; lift: number; root: THREE.Color; tip: THREE.Color; }

class LockBuilder {
  private positions: number[] = [];
  private colors: number[] = [];
  private indices: number[] = [];
  private static SEG = 9;
  private static RAD = 6;

  add(root: THREE.Vector3, normal: THREE.Vector3, dir: THREE.Vector3, o: LockOptions) {
    const { SEG, RAD } = LockBuilder;
    const P0 = root.clone().addScaledVector(normal, -0.05);
    const P1 = root.clone().addScaledVector(normal, o.length * o.lift * 0.55).addScaledVector(dir, o.length * 0.5);
    const P2 = root.clone().addScaledVector(normal, o.length * o.lift).addScaledVector(dir, o.length);
    const base = this.positions.length / 3;
    const c = v3(), d = v3(), S = v3(), N = v3(), col = new THREE.Color();
    const a = P1.clone().sub(P0), b = P2.clone().sub(P1);
    for (let s = 0; s <= SEG; s++) {
      const t = s / SEG;
      c.set(0, 0, 0).addScaledVector(P0, (1 - t) ** 2).addScaledVector(P1, 2 * (1 - t) * t).addScaledVector(P2, t * t);
      d.set(0, 0, 0).addScaledVector(a, 2 * (1 - t)).addScaledVector(b, 2 * t).normalize();
      S.crossVectors(d, normal).normalize();
      N.crossVectors(S, d).normalize();
      const w = o.width * Math.pow(1 - t, 0.85) * (0.82 + 0.3 * Math.sin(Math.PI * Math.min(1, t * 1.7)));
      const th = o.thick * Math.pow(1 - t, 0.8);
      col.copy(o.root).lerp(o.tip, smooth(0, 0.7, t));
      for (let k = 0; k < RAD; k++) {
        const ang = (k / RAD) * Math.PI * 2;
        const x = Math.cos(ang), y = Math.sin(ang);
        this.positions.push(c.x + S.x * x * w + N.x * y * th, c.y + S.y * x * w + N.y * y * th, c.z + S.z * x * w + N.z * y * th);
        this.colors.push(col.r, col.g, col.b);
      }
    }
    for (let s = 0; s < SEG; s++) {
      for (let k = 0; k < RAD; k++) {
        const i0 = base + s * RAD + k, i1 = base + s * RAD + ((k + 1) % RAD);
        const i2 = base + (s + 1) * RAD + ((k + 1) % RAD), i3 = base + (s + 1) * RAD + k;
        this.indices.push(i0, i2, i1, i0, i3, i2);
      }
    }
  }

  build() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.positions, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(this.colors, 3));
    g.setIndex(this.indices);
    g.computeVertexNormals();
    return g;
  }
}

function fibonacci(n: number, i: number, out = v3()) {
  const y = 1 - ((i + 0.5) / n) * 2;
  const r = Math.sqrt(1 - y * y);
  const phi = i * 2.399963229728653;
  return out.set(Math.cos(phi) * r, y, Math.sin(phi) * r);
}

function tangentTowards(normal: THREE.Vector3, target: THREE.Vector3, fallback: THREE.Vector3) {
  const t = target.clone().addScaledVector(normal, -target.dot(normal));
  if (t.lengthSq() < 0.04) t.copy(fallback).addScaledVector(normal, -fallback.dot(normal));
  return t.normalize();
}

function buildHair(materials: { silver: THREE.Material; dark: THREE.Material }) {
  const rand = random(7);
  const silver = new LockBuilder(), dark = new LockBuilder();
  const u = v3();
  const flow = v3(0.55, 0.5, -0.68).normalize();
  const nape = v3(0.25, -0.7, -0.66).normalize();
  const silverRoot = new THREE.Color(0x6f6b67), silverTip = new THREE.Color(PALETTE.hairSilver).offsetHSL(0, 0, 0.07);
  const darkRoot = new THREE.Color(0x0f0e11), darkTip = new THREE.Color(PALETTE.hairDark).offsetHSL(0, 0, 0.05);
  const swept = (n: THREE.Vector3, uy: number) => {
    const a = Math.abs(Math.atan2(n.x, n.z));
    const earZone = smooth(1.2, 1.42, a) * (1 - smooth(1.8, 2.0, a));
    const low = smooth(0.35, -0.25, uy) * (1 - earZone);
    return { low, dir: tangentTowards(n, flow.clone().lerp(nape, low).normalize(), v3(0.3, 0, -1)) };
  };

  // Dark lower layer: rooted along the hairline, swept with the flow; its roots form the jagged edge.
  for (let i = 0; i < 620; i++) {
    fibonacci(620, i, u);
    if (!isScalp(u, 0.03) || isScalp(u, 0.34) || rand() < 0.25) continue;
    const { p, n } = headSurface(u);
    const { low, dir } = swept(n, u.y);
    dir.applyAxisAngle(n, (rand() - 0.5) * 0.5);
    dark.add(p.clone().addScaledVector(n, 0.02), n, dir, { length: 0.42 + rand() * 0.2 - low * 0.1, width: 0.22 + rand() * 0.07, thick: 0.09, lift: 0.14 + rand() * 0.1, root: darkRoot, tip: darkTip });
  }
  // Sideburn spikes pointing down in front of the ears.
  for (let i = 0; i < 900; i++) {
    fibonacci(900, i, u);
    const a = Math.abs(Math.atan2(u.x, u.z));
    if (a < 1.05 || a > 1.46 || !isScalp(u, 0.0) || isScalp(u, 0.14) || rand() < 0.35) continue;
    const { p, n } = headSurface(u);
    const dir = tangentTowards(n, v3(0, -1, 0.1), v3(0, -1, 0)).applyAxisAngle(n, (rand() - 0.5) * 0.3);
    dark.add(p.clone().addScaledVector(n, 0.022), n, dir, { length: 0.16 + rand() * 0.1, width: 0.1, thick: 0.04, lift: 0.05, root: darkRoot, tip: darkTip });
  }
  // Silver upper mass: wide soft locks swept up, back and toward the character's left.
  for (let i = 0; i < 900; i++) {
    fibonacci(900, i, u);
    if (!isScalp(u, 0.2) || rand() < 0.1) continue;
    const { p, n } = headSurface(u);
    const { low, dir } = swept(n, u.y);
    dir.applyAxisAngle(n, (rand() - 0.5) * 0.45);
    const front = u.z > 0.25 && u.y > 0.3;
    const length = front ? 0.74 + rand() * 0.24 : 0.58 + rand() * 0.3 - low * 0.18;
    const lift = front ? 0.36 + rand() * 0.16 : 0.1 + rand() * 0.18 - low * 0.06;
    silver.add(p.clone().addScaledVector(n, 0.06), n, dir, { length, width: 0.26 + rand() * 0.1, thick: 0.12 + rand() * 0.03, lift, root: silverRoot, tip: silverTip });
  }
  const group = new THREE.Group();
  group.add(new THREE.Mesh(silver.build(), materials.silver), new THREE.Mesh(dark.build(), materials.dark));
  return group;
}

// ---- Helpers ----------------------------------------------------------------------------------

function roundedRectPoints(w: number, h: number, r: number, steps = 8) {
  const pts: THREE.Vector2[] = [];
  const corners = [
    [w / 2 - r, h / 2 - r, 0], [-w / 2 + r, h / 2 - r, Math.PI / 2], [-w / 2 + r, -h / 2 + r, Math.PI], [w / 2 - r, -h / 2 + r, Math.PI * 1.5],
  ];
  for (const [cx, cy, start] of corners) {
    for (let i = 0; i <= steps; i++) {
      const a = start + (i / steps) * (Math.PI / 2);
      pts.push(new THREE.Vector2(cx + Math.cos(a) * r, cy + Math.sin(a) * r));
    }
  }
  return pts;
}

/** A decal that follows the head surface, e.g. blush. */
function conformDecal(dir: THREE.Vector3, width: number, height: number, lift: number, material: THREE.Material) {
  const { n } = headSurface(dir);
  const up = v3(0, 1, 0);
  const t1 = up.clone().cross(n).normalize(), t2 = n.clone().cross(t1).normalize();
  const g = new THREE.PlaneGeometry(width, height, 10, 6);
  const pos = g.getAttribute('position');
  const centre = deformHead(dir.clone().normalize());
  const q = v3();
  for (let i = 0; i < pos.count; i++) {
    q.copy(centre).addScaledVector(t1, pos.getX(i)).addScaledVector(t2, pos.getY(i));
    const s = headSurface(q);
    s.p.addScaledVector(s.n, lift);
    pos.setXYZ(i, s.p.x, s.p.y, s.p.z);
  }
  g.computeVertexNormals();
  return new THREE.Mesh(g, material);
}

function radialTexture(inner: string, outer: string) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d')!;
  const grad = ctx.createRadialGradient(64, 64, 4, 64, 64, 64);
  grad.addColorStop(0, inner);
  grad.addColorStop(0.55, inner);
  grad.addColorStop(1, outer);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export interface FadeUniforms { uFadeTop: { value: number }; uFadeBottom: { value: number } }

/** Fades the lower jacket into the background (object-space Y, independent of framing). */
function addBottomFade(material: THREE.Material, uniforms: FadeUniforms) {
  material.transparent = true;
  material.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying float vFadeY;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvFadeY = transformed.y;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vFadeY;\nuniform float uFadeTop;\nuniform float uFadeBottom;')
      .replace('#include <dithering_fragment>', '#include <dithering_fragment>\ngl_FragColor.a *= smoothstep(uFadeBottom, uFadeTop, vFadeY);');
  };
  material.customProgramCacheKey = () => 'scout-bottom-fade';
}

// ---- Rig ------------------------------------------------------------------------------------

export interface ScoutRig {
  root: THREE.Group;
  body: THREE.Group;
  head: THREE.Group;
  eyes: THREE.Object3D[];
  hotspots: Record<HotspotId, { anchor: THREE.Object3D; normal: THREE.Vector3 }>;
  fade: FadeUniforms;
  /** Framing box in model units: the visible bust from jacket fade to hair tips. */
  frame: { top: number; bottom: number; width: number };
  highlight(id: HotspotId | null, amount: number): void;
  dispose(): void;
}

export function createScout(): ScoutRig {
  const disposables: { dispose(): void }[] = [];
  const keep = <T extends { dispose(): void }>(x: T) => (disposables.push(x), x);

  const skin = keep(new THREE.MeshPhysicalMaterial({ color: PALETTE.skin, roughness: 0.5, clearcoat: 0.28, clearcoatRoughness: 0.45, sheen: 0.35, sheenColor: new THREE.Color(0xffe8da), sheenRoughness: 0.6 }));
  const skinShade = keep(new THREE.MeshPhysicalMaterial({ color: PALETTE.skinShade, roughness: 0.6, clearcoat: 0.15 }));
  const hairSilver = keep(new THREE.MeshPhysicalMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.34, metalness: 0.06, clearcoat: 0.55, clearcoatRoughness: 0.26, sheen: 0.6, sheenColor: new THREE.Color(0xffffff), sheenRoughness: 0.35 }));
  const hairDark = keep(new THREE.MeshPhysicalMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.42, clearcoat: 0.45, clearcoatRoughness: 0.34 }));
  const eyeMat = keep(new THREE.MeshPhysicalMaterial({ color: 0x0b0b0d, roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.06 }));
  const blushMap = keep(radialTexture('rgba(242,154,156,0.78)', 'rgba(242,154,156,0)'));
  const blushMat = keep(new THREE.MeshStandardMaterial({ map: blushMap, transparent: true, depthWrite: false, roughness: 0.85, polygonOffset: true, polygonOffsetFactor: -2 }));
  const metal = keep(new THREE.MeshStandardMaterial({ color: PALETTE.metal, metalness: 1, roughness: 0.2 }));
  const earringMetal = keep(metal.clone());
  const pullMetal = keep(new THREE.MeshStandardMaterial({ color: 0xb9bdc4, metalness: 1, roughness: 0.28 }));
  const lensMat = keep(new THREE.MeshPhysicalMaterial({ color: 0xe9f1f5, transparent: true, opacity: 0.14, roughness: 0.02, clearcoat: 1, envMapIntensity: 2.2, depthWrite: false, side: THREE.DoubleSide }));
  const lensEdge = keep(new THREE.MeshPhysicalMaterial({ color: 0xeef4f7, transparent: true, opacity: 0.75, roughness: 0.06, metalness: 0.3, emissive: new THREE.Color(PALETTE.amber), emissiveIntensity: 0 }));
  const jacket = keep(new THREE.MeshPhysicalMaterial({ color: PALETTE.jacket, roughness: 0.58, clearcoat: 0.18, clearcoatRoughness: 0.5, sheen: 0.4, sheenColor: new THREE.Color(0x66707c), sheenRoughness: 0.45 }));
  const collarMat = keep(jacket.clone());
  collarMat.side = THREE.DoubleSide;
  const seamMat = keep(new THREE.MeshStandardMaterial({ color: 0x2b2d32, roughness: 0.55, metalness: 0.1 }));
  const zipMat = keep(new THREE.MeshStandardMaterial({ color: 0x6f747c, metalness: 0.9, roughness: 0.35 }));
  for (const m of [earringMetal, pullMetal]) m.emissive = new THREE.Color(PALETTE.amber);

  const fade: FadeUniforms = { uFadeTop: { value: -1.9 }, uFadeBottom: { value: -2.9 } };
  for (const m of [jacket, seamMat, zipMat]) addBottomFade(m, fade);

  const root = new THREE.Group();
  root.name = 'scout';
  const body = new THREE.Group();
  const head = new THREE.Group();
  root.add(body, head);

  // Head, cap and hair
  const headMesh = new THREE.Mesh(keep(headGeometry(128, 96).g), skin);
  head.add(headMesh);

  const cap = headGeometry(176, 132);
  cap.g.scale(1.028, 1.03, 1.03);
  const index = cap.g.getIndex()!;
  const kept: number[] = [];
  const u = v3();
  const U = cap.unit;
  for (let i = 0; i < index.count; i += 3) {
    const a = index.getX(i) * 3, b = index.getX(i + 1) * 3, c = index.getX(i + 2) * 3;
    u.set(U[a] + U[b] + U[c], U[a + 1] + U[b + 1] + U[c + 1], U[a + 2] + U[b + 2] + U[c + 2]).normalize();
    if (isScalp(u)) kept.push(index.getX(i), index.getX(i + 1), index.getX(i + 2));
  }
  cap.g.setIndex(kept);
  keep(cap.g);
  const capMat = keep(new THREE.MeshPhysicalMaterial({ color: PALETTE.hairDark, roughness: 0.55, clearcoat: 0.3 }));
  head.add(new THREE.Mesh(cap.g, capMat));

  const hair = buildHair({ silver: hairSilver, dark: hairDark });
  hair.traverse(o => { if (o instanceof THREE.Mesh) keep(o.geometry); });
  head.add(hair);

  // Eyes
  const eyeGeo = keep(new THREE.CapsuleGeometry(0.056, 0.15, 8, 20));
  const eyes: THREE.Object3D[] = [];
  for (const side of [-1, 1]) {
    const { p, n } = headSurface(v3(side * 0.3, -0.09, 0.95));
    const pivot = new THREE.Group();
    pivot.position.copy(p).addScaledVector(n, 0.004);
    pivot.quaternion.setFromUnitVectors(v3(0, 0, 1), n);
    const eye = new THREE.Mesh(eyeGeo, eyeMat);
    eye.scale.set(1, 1, 0.34);
    pivot.add(eye);
    head.add(pivot);
    eyes.push(pivot);
  }

  // Blush
  for (const side of [-1, 1]) head.add(conformDecal(v3(side * 0.56, -0.27, 0.8), 0.3, 0.19, 0.006, blushMat));

  // Ears and the silver hoop (character's left ear shows the hoop, matching the avatar)
  const earGeo = keep(new THREE.SphereGeometry(0.2, 28, 18));
  const earInnerGeo = keep(new THREE.SphereGeometry(0.12, 20, 14));
  let hoopAnchor = new THREE.Object3D();
  for (const side of [-1, 1]) {
    const { p, n } = headSurface(v3(side, -0.08, -0.04));
    const ear = new THREE.Group();
    ear.position.copy(p).addScaledVector(n, 0.05);
    ear.rotation.set(0, side * 0.28, side * -0.06);
    const outer = new THREE.Mesh(earGeo, skin);
    outer.scale.set(0.46, 1.1, 0.78);
    const inner = new THREE.Mesh(earInnerGeo, skinShade);
    inner.scale.set(0.22, 0.78, 0.5);
    inner.position.set(side * 0.05, 0.01, 0.02);
    ear.add(outer, inner);
    if (side === 1) {
      const hoop = new THREE.Mesh(keep(new THREE.TorusGeometry(0.058, 0.013, 14, 48)), earringMetal);
      hoop.position.set(0.035, -0.225, 0.04);
      hoop.rotation.y = Math.PI / 2 - 0.35;
      ear.add(hoop);
      hoopAnchor = new THREE.Object3D();
      hoopAnchor.position.set(0.06, -0.24, 0.05);
      ear.add(hoopAnchor);
    }
    head.add(ear);
  }

  // Rimless glasses
  const glasses = new THREE.Group();
  const lensW = 0.5, lensH = 0.3, lensR = 0.075;
  const outline = roundedRectPoints(lensW, lensH, lensR);
  const lensShape = new THREE.Shape(outline);
  const lensGeo = keep(new THREE.ShapeGeometry(lensShape, 10));
  const edgeCurve = new THREE.CatmullRomCurve3(outline.map(p => v3(p.x, p.y, 0)), true, 'centripetal');
  const edgeGeo = keep(new THREE.TubeGeometry(edgeCurve, 120, 0.006, 6, true));
  const lenses: THREE.Group[] = [];
  for (const side of [-1, 1]) {
    const lens = new THREE.Group();
    lens.position.set(side * 0.35, -0.07, 1.03);
    lens.rotation.y = side * 0.22;
    lens.add(new THREE.Mesh(lensGeo, lensMat), new THREE.Mesh(edgeGeo, lensEdge));
    glasses.add(lens);
    lenses.push(lens);
  }
  glasses.updateMatrixWorld(true);
  const onLens = (lens: THREE.Object3D, x: number, y: number) => lens.localToWorld(v3(x, y, 0.004));
  const innerL = onLens(lenses[0], lensW / 2 - 0.035, lensH / 2 - 0.05);
  const innerR = onLens(lenses[1], -lensW / 2 + 0.035, lensH / 2 - 0.05);
  const bridge = new THREE.CatmullRomCurve3([innerL, v3(0, innerL.y + 0.035, innerL.z + 0.03), innerR]);
  glasses.add(new THREE.Mesh(keep(new THREE.TubeGeometry(bridge, 32, 0.011, 8)), metal));
  const clampGeo = keep(new THREE.BoxGeometry(0.036, 0.05, 0.03));
  const hingeGeo = keep(new THREE.BoxGeometry(0.075, 0.04, 0.036));
  const screwGeo = keep(new THREE.CylinderGeometry(0.009, 0.009, 0.05, 10));
  for (const [i, side] of [[0, -1], [1, 1]] as const) {
    const lens = lenses[i];
    const clamp = new THREE.Mesh(clampGeo, metal);
    clamp.position.copy(i === 0 ? innerL : innerR);
    clamp.rotation.y = lens.rotation.y;
    glasses.add(clamp);
    const hingePos = onLens(lens, side * (lensW / 2 - 0.01), lensH / 2 - 0.05);
    const hinge = new THREE.Mesh(hingeGeo, metal);
    hinge.position.copy(hingePos);
    hinge.rotation.y = lens.rotation.y;
    glasses.add(hinge);
    const screw = new THREE.Mesh(screwGeo, metal);
    screw.position.copy(hingePos).add(v3(side * 0.012, 0, 0.02));
    glasses.add(screw);
    const temple = new THREE.CatmullRomCurve3([
      hingePos.clone().add(v3(side * 0.03, 0, -0.01)), v3(side * 0.92, hingePos.y + 0.01, 0.62), v3(side * 1.11, hingePos.y - 0.01, 0.16), v3(side * 1.12, hingePos.y - 0.05, -0.18),
    ]);
    glasses.add(new THREE.Mesh(keep(new THREE.TubeGeometry(temple, 40, 0.011, 8)), metal));
  }
  const lensAnchor = new THREE.Object3D();
  lenses[1].add(lensAnchor);
  lensAnchor.position.set(0, 0, 0.01);
  head.add(glasses);

  // Neck (mostly hidden by the collar)
  const neck = new THREE.Mesh(keep(new THREE.CylinderGeometry(0.34, 0.42, 0.5, 24)), skin);
  neck.position.y = -0.98;
  body.add(neck);

  // Jacket torso
  const profile = [
    [0.64, -1.1], [0.84, -1.22], [1.08, -1.32], [1.3, -1.44], [1.44, -1.64], [1.5, -1.92], [1.48, -2.4], [1.43, -2.8], [1.36, -3.1],
  ].map(([r, y]) => new THREE.Vector2(r, y)).reverse();
  const torsoGeo = keep(new THREE.LatheGeometry(profile, 96));
  torsoGeo.scale(1, 1, 0.62);
  torsoGeo.computeVertexNormals();
  body.add(new THREE.Mesh(torsoGeo, jacket));

  const radiusAt = (y: number) => {
    const pts = profile.map(p => [p.x, p.y]).sort((a, b) => b[1] - a[1]);
    for (let i = 1; i < pts.length; i++) {
      if (y >= pts[i][1]) {
        const t = (y - pts[i - 1][1]) / (pts[i][1] - pts[i - 1][1]);
        return pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t;
      }
    }
    return pts[pts.length - 1][0];
  };
  const onTorso = (phi: number, y: number, lift = 0.012) => {
    const r = radiusAt(y) + lift;
    return v3(Math.sin(phi) * r, y, Math.cos(phi) * r * 0.62);
  };

  // High stand collar with a rolled edge
  const collarProfile = [[0.745, -0.66], [0.725, -0.78], [0.715, -0.92], [0.74, -1.05], [0.82, -1.17], [0.92, -1.26]]
    .map(([r, y]) => new THREE.Vector2(r, y)).reverse();
  const collarGeo = keep(new THREE.LatheGeometry(collarProfile, 96));
  collarGeo.scale(1, 1, 0.82);
  collarGeo.computeVertexNormals();
  body.add(new THREE.Mesh(collarGeo, collarMat));
  const rim = new THREE.Mesh(keep(new THREE.TorusGeometry(0.745, 0.032, 12, 96)), collarMat);
  rim.rotation.x = Math.PI / 2;
  rim.scale.set(1, 0.82, 1);
  rim.position.y = -0.66;
  body.add(rim);

  // Panel seams
  const seams: THREE.Vector3[][] = [];
  for (const side of [-1, 1]) {
    seams.push([onTorso(side * 0.45, -1.26), onTorso(side * 0.9, -1.42), onTorso(side * 1.25, -1.6), onTorso(side * 1.45, -1.9)]);
    seams.push([onTorso(side * 0.34, -1.46), onTorso(side * 0.36, -2.0), onTorso(side * 0.34, -2.6), onTorso(side * 0.33, -3.05)]);
    seams.push([onTorso(side * 0.42, -2.05), onTorso(side * 0.62, -2.08), onTorso(side * 0.82, -2.06)]);
  }
  for (const pts of seams) body.add(new THREE.Mesh(keep(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 48, 0.0075, 6)), seamMat));

  // Zipper and pull
  const zipPath = new THREE.CatmullRomCurve3([
    v3(0, -0.72, 0.605), v3(0, -0.9, 0.59), v3(0, -1.04, 0.61), v3(0, -1.16, 0.68), v3(0, -1.26, 0.77), onTorso(0, -1.38), onTorso(0, -1.52), onTorso(0, -1.74), onTorso(0, -2.05), onTorso(0, -2.5), onTorso(0, -3.05),
  ]);
  body.add(new THREE.Mesh(keep(new THREE.TubeGeometry(zipPath, 160, 0.014, 6)), zipMat));
  const pull = new THREE.Group();
  pull.position.set(0, -0.8, 0.608);
  pull.rotation.x = -0.12;
  const tab = new THREE.Mesh(keep(new THREE.BoxGeometry(0.062, 0.15, 0.022)), pullMetal);
  tab.position.y = -0.07;
  const slot = new THREE.Mesh(keep(new THREE.BoxGeometry(0.03, 0.05, 0.026)), zipMat);
  slot.position.y = -0.1;
  const ring = new THREE.Mesh(keep(new THREE.TorusGeometry(0.02, 0.006, 8, 24)), pullMetal);
  ring.position.y = 0.012;
  pull.add(tab, slot, ring);
  const pullAnchor = new THREE.Object3D();
  pullAnchor.position.set(0, -0.07, 0.02);
  pull.add(pullAnchor);
  body.add(pull);

  const hotspots: ScoutRig['hotspots'] = {
    lens: { anchor: lensAnchor, normal: v3(0, 0, 1) },
    signal: { anchor: hoopAnchor, normal: v3(1, 0, 0.25).normalize() },
    rules: { anchor: pullAnchor, normal: v3(0, 0, 1) },
  };
  const glow: Record<HotspotId, THREE.MeshStandardMaterial[]> = { lens: [lensEdge], signal: [earringMetal], rules: [pullMetal] };

  return {
    root, body, head, eyes, hotspots, fade,
    frame: { top: 1.72, bottom: -2.55, width: 3.4 },
    highlight(id, amount) {
      for (const key of Object.keys(glow) as HotspotId[]) {
        for (const m of glow[key]) m.emissiveIntensity = key === id ? amount * 1.6 : 0;
      }
    },
    dispose() { for (const d of disposables) d.dispose(); },
  };
}
