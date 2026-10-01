import * as THREE from 'three';

// Real-time procedural studio background. Everything is computed per drawing-buffer pixel,
// so it stays sharp at whatever resolution the renderer runs (up to 3840×2160 on desktop).
// Colours are authored in display (sRGB) space; the material bypasses tone mapping.

const vertexShader = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = position.xy * 0.5 + 0.5;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}`;

const fragmentShader = /* glsl */ `
varying vec2 vUv;
uniform float uTime;
uniform float uStory;
uniform float uIntro;
uniform float uExit;
uniform float uRest;
uniform float uDpr;
uniform vec2 uResolution;
uniform vec2 uSubject;
uniform vec4 uQuiet;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 3; i++) { v += a * noise(p); p = p * 2.03 + vec2(17.1, 9.2); a *= 0.5; }
  return v;
}
float boxMask(vec2 uv, vec4 r, float feather) {
  vec2 lo = smoothstep(r.xy - feather, r.xy + feather, uv);
  vec2 hi = 1.0 - smoothstep(r.zw - feather, r.zw + feather, uv);
  return lo.x * lo.y * hi.x * hi.y;
}

void main() {
  vec2 px = vUv * uResolution;
  float aspect = uResolution.x / uResolution.y;
  vec2 p = vec2((vUv.x - 0.5) * aspect, vUv.y - 0.5);
  vec2 s = vec2((uSubject.x - 0.5) * aspect, uSubject.y - 0.5);
  float t = uTime;

  float verify = smoothstep(0.4, 1.2, uStory) * (1.0 - smoothstep(2.2, 3.0, uStory));
  float evaluate = smoothstep(2.4, 3.2, uStory) * (1.0 - smoothstep(3.6, 4.3, uStory));

  vec3 ink = vec3(0.024, 0.031, 0.039);
  vec3 graphite = vec3(0.082, 0.098, 0.114);
  vec3 titanium = vec3(0.56, 0.61, 0.66);
  vec3 amber = vec3(0.91, 0.70, 0.41);

  // Base: graphite pool of light around the subject, darker floor and edges.
  float dS = length((p - s) * vec2(0.8, 1.0));
  vec3 col = mix(graphite, ink, smoothstep(0.02, 1.05, dS));
  col = mix(col, ink, 0.4 * smoothstep(0.35, 1.0, 1.0 - vUv.y));
  col += titanium * 0.03 * exp(-dS * 2.2) * (1.0 + verify * 0.6);

  // Slow spatial waves: anti-aliased contour lines of a drifting field.
  vec2 q = p * 1.6;
  float warp = fbm(q * 0.85 + vec2(t * 0.011, -t * 0.007));
  float field = q.y * 0.85 + q.x * 0.28 + warp * 1.4 + sin(q.x * 1.15 + t * 0.045) * 0.2;
  float density = 8.0 + evaluate * 3.0;
  float bands = field * density;
  float fw = max(fwidth(bands), 1e-4);
  float d = abs(fract(bands - 0.5) - 0.5);
  float line = 1.0 - smoothstep(0.0, fw * 1.3, d);
  float crest = 0.5 + 0.5 * sin(field * 2.2 - t * 0.32);
  float nearSubject = exp(-dS * 2.4);

  // Fine 80 CSS-pixel grid, kept away from the text side.
  vec2 g = px / (80.0 * uDpr);
  vec2 gd = abs(fract(g - 0.5) - 0.5) / max(fwidth(g), vec2(1e-4));
  float grid = 1.0 - min(min(gd.x, gd.y), 1.0);

  float quiet = boxMask(vUv, uQuiet, 0.07);
  float calm = 1.0 - 0.82 * quiet;

  col += vec3(0.9, 0.93, 1.0) * line * (0.028 + 0.035 * nearSubject) * calm;
  col += amber * line * crest * nearSubject * (0.2 + 0.1 * evaluate) * calm;
  col += vec3(1.0) * grid * 0.022 * smoothstep(0.05, 0.6, vUv.x) * calm;

  // Restrained amber light field drifting behind the subject.
  vec2 c1 = s + vec2(0.22 * sin(t * 0.031), 0.1 * cos(t * 0.043)) + vec2(0.18, -0.08);
  col += amber * 0.075 * exp(-length(p - c1) * 2.7) * (1.0 - 0.5 * verify) * calm;
  vec2 c2 = s + vec2(-0.35 + 0.1 * cos(t * 0.027), 0.28);
  col += titanium * 0.03 * exp(-length(p - c2) * 3.0) * calm;

  // Atmospheric depth: soft haze and vignette.
  col = mix(col, ink, 0.25 * smoothstep(0.55, 1.25, length(p * vec2(0.75, 1.0))));
  col *= 1.0 - 0.18 * quiet;

  // One-time light sweep as the hero settles.
  float sweepPos = mix(-0.4, 1.5, uIntro);
  float sweepCoord = vUv.x * 0.78 + vUv.y * 0.42;
  float sweep = exp(-pow((sweepCoord - sweepPos) * 7.0, 2.0)) * sin(3.14159 * clamp(uIntro, 0.0, 1.0));
  col += vec3(1.0, 0.86, 0.64) * sweep * 0.07 * (0.4 + nearSubject);

  // Rest behind content, recede toward the console.
  col = mix(col, ink, uRest * 0.35);
  col = mix(col, ink * 0.8, uExit * 0.65);

  // Native-resolution dithering prevents banding in the dark gradients.
  col += (hash(px + fract(t * 7.0) * 91.0) - 0.5) * (1.6 / 255.0);
  gl_FragColor = vec4(col, 1.0);
}`;

export interface BackgroundRig {
  scene: THREE.Scene;
  camera: THREE.OrthographicCamera;
  uniforms: {
    uTime: { value: number }; uStory: { value: number }; uIntro: { value: number }; uExit: { value: number }; uRest: { value: number };
    uDpr: { value: number }; uResolution: { value: THREE.Vector2 }; uSubject: { value: THREE.Vector2 }; uQuiet: { value: THREE.Vector4 };
  };
  dispose(): void;
}

export function createBackground(): BackgroundRig {
  const uniforms: BackgroundRig['uniforms'] = {
    uTime: { value: 0 }, uStory: { value: -1 }, uIntro: { value: 0 }, uExit: { value: 0 }, uRest: { value: 0 }, uDpr: { value: 1 },
    uResolution: { value: new THREE.Vector2(1, 1) }, uSubject: { value: new THREE.Vector2(0.68, 0.5) }, uQuiet: { value: new THREE.Vector4(0.04, 0.2, 0.44, 0.82) },
  };
  const material = new THREE.ShaderMaterial({ uniforms, vertexShader, fragmentShader, depthTest: false, depthWrite: false, toneMapped: false });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  const scene = new THREE.Scene();
  scene.add(mesh);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  return { scene, camera, uniforms, dispose() { geometry.dispose(); material.dispose(); } };
}
