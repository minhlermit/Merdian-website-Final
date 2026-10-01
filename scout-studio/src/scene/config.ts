// Motion, quality and storyboard settings for the Scout scene.
// These are tuning values for review, not measurements taken from the reference clip.

export const MOTION = {
  uiFeedbackMs: 200,
  entranceMs: 700,
  entranceStaggerMs: 70,
  heroSettleMs: 900,
  lightSweepMs: 1500,
  pointerTiltDeg: 7,
  dragLimitDeg: 70,
  dragSensitivity: 0.0068, // radians per CSS pixel
  dragInertiaDecay: 5.5, // per second, applied to release velocity
  dragReleaseGain: 0.35, // share of the release velocity carried into inertia
  dragOverscrollDeg: 17, // rubber-band travel past the limit before it springs back
  dragSpring: 9, // pulls the rotation back inside the soft limit
  keyboardStepDeg: 15,
  scrollSmoothing: 6.5, // exponential smoothing rate for story progress
  anchorSmoothing: 10,
  gazeSmoothing: 6,
  touchIntentPx: 10, // horizontal travel before a touch becomes a drag
  blinkEverySeconds: [2.8, 6.2] as const,
} as const;

export type QualityTier = 'high' | 'balanced' | 'low';
export type QualitySetting = 'auto' | QualityTier;

export const QUALITY: Record<QualityTier, { maxDpr: number; maxPixels: number; label: string }> = {
  high: { maxDpr: 2, maxPixels: 3840 * 2160, label: 'High · up to UHD 3840×2160' },
  balanced: { maxDpr: 1.5, maxPixels: 2560 * 1440, label: 'Balanced · up to 1440p' },
  low: { maxDpr: 1, maxPixels: 1920 * 1080, label: 'Low · up to 1080p' },
};

// Phones and coarse-pointer tablets never pay the desktop 4K cost.
export const HANDHELD_LIMIT = { maxDpr: 2, maxPixels: 1_500_000 };

// Automatic quality steps down when the average frame time stays above this for the window.
export const ADAPTIVE = { slowFrameMs: 24, windowFrames: 90, recoverFrameMs: 12 };

// Asset budgets (uncompressed transfer unless noted). Procedural assets cost code, not downloads.
export const BUDGETS = {
  subjectModelKB: 450, // a replacement GLB must stay under this (Draco/meshopt compressed)
  backgroundKB: 6000, // a replacement 4K video loop; the shipped background is a shader (0 KB)
  texturesKB: 512, // procedural canvas textures are generated at runtime
  fontsKB: 160, // Geist Sans + Geist Mono variable WOFF2 ≈ 141 KB
  sceneChunkKBGzip: 200, // three.js + scene code, lazy-loaded after first paint
};

export type Chapter = 'discover' | 'verify' | 'investigate' | 'evaluate' | 'deliver';
export const CHAPTERS: Chapter[] = ['discover', 'verify', 'investigate', 'evaluate', 'deliver'];

// Subject pose per storyboard moment. Index 0 is the hero, 1–5 are the five research chapters.
// yaw/pitch in radians; x/y offsets in model units (the head is ~1 unit); scale is relative.
export interface Pose { yaw: number; pitch: number; x: number; y: number; scale: number; lookUp: number; roll: number; }
export const POSES: Pose[] = [
  { yaw: -0.5, pitch: 0.02, x: 0, y: 0, scale: 1, lookUp: 0.14, roll: -0.1 }, // hero
  { yaw: -0.24, pitch: 0.02, x: -1.1, y: 0.05, scale: 0.88, lookUp: 0.05, roll: -0.04 }, // discover
  { yaw: 0.42, pitch: -0.02, x: -1.3, y: 0.05, scale: 0.82, lookUp: 0.0, roll: 0.03 }, // verify
  { yaw: 0.16, pitch: 0.04, x: -1.25, y: 0.05, scale: 0.82, lookUp: 0.08, roll: 0 }, // investigate
  { yaw: -0.3, pitch: 0.0, x: -1.3, y: 0.05, scale: 0.82, lookUp: 0.02, roll: -0.03 }, // evaluate
  { yaw: -0.12, pitch: 0.02, x: -1.35, y: 0.05, scale: 0.8, lookUp: 0.06, roll: -0.02 }, // deliver
];

// Horizontal model units each layout must fit: the subject alone, or the subject plus evidence.
export const CONTENT_WIDTH = { hero: 3.6, story: 6.3 };

// Named presentation angles used by the asset lab (total yaw, radians).
export const VIEW_ANGLES = { front: 0, threeQuarter: -0.62, side: -1.35 } as const;
export type ViewAngle = keyof typeof VIEW_ANGLES;

export const HOTSPOTS = [
  {
    id: 'lens',
    label: 'Evidence lens',
    short: 'Claims meet sources',
    body: 'Every project claim is checked against on-chain data and a claim ledger. Evidence stays labeled as verified on-chain, verified off-chain, likely, unconfirmed or in conflict.',
  },
  {
    id: 'signal',
    label: 'Six-hour listening',
    short: 'Changes, not listings',
    body: 'The Scout compares public market snapshots at UTC 00:00, 06:00, 12:00 and 18:00, so only a meaningful change becomes a signal worth researching.',
  },
  {
    id: 'rules',
    label: 'Rules that hold',
    short: 'Fixed scorecard',
    body: 'Scores and the exit-risk floor come from fixed rules in the research engine. The memo writer cannot improve a rating with persuasive prose, and a memo only runs after research is marked complete.',
  },
] as const;
export type HotspotId = (typeof HOTSPOTS)[number]['id'];

export const PALETTE = {
  ink: 0x07090b,
  graphite: 0x14181c,
  titanium: 0xaeb6bf,
  amber: 0xe8b368,
  amberHot: 0xffc47a,
  mint: 0xa9d3b7,
  coral: 0xed9074,
  skin: 0xf3dcc7,
  skinShade: 0xe6bea4,
  blush: 0xf29a9c,
  hairSilver: 0xd9d5cd,
  hairDark: 0x1b1a1f,
  jacket: 0x141518,
  metal: 0xc9ccd2,
};
