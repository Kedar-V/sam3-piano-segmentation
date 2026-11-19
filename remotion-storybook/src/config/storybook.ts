import background from '../assets/illustrations/background.jpg';
import midground from '../assets/illustrations/midground.png';
import foreground from '../assets/illustrations/foreground.png';
import foregroundBlur from '../assets/illustrations/foreground_blur.png';
import paper from '../assets/illustrations/paper.png';

// All visual parameters for the piano storybook reel live here. Nothing below is baked into the footage.
// Replace `scene` to swap the illustrated world; replace `title.text` to change the caption (e.g. Hindi lyrics).

export type StorybookConfig = typeof storybook;

export const storybook = {
  // ---- timing (matches the source footage: 24 fps, 240 frames = 10.0 s) ----
  fps: 24,
  durationInFrames: 240,
  width: 1080,
  height: 1920,

  // ---- source footage (untouched exports; see outputs/piano_compositing) ----
  footage: {
    // 'plateMatte' (default): opaque original frames + gap-closed matte (no halo between hands and keys).
    // 'alphaVideo': the exported ProRes 4444 alpha video as-is (verified to render with transparency in Remotion).
    mode: 'plateMatte' as 'plateMatte' | 'alphaVideo',
    plate: 'footage/plate_10s.mp4', // same 240 frames as the export, opaque (derived from the source; source untouched)
    matteDir: 'masks/matte', // plateMatte: per-frame RGBA matte (alpha = soft combined foreground)
    outlineDirClosed: 'masks/outline_closed', // plateMatte: outline rebuilt from the closed matte
    video: 'footage/foreground_alpha.mov', // alphaVideo: ProRes 4444, straight alpha (rendered via <OffthreadVideo transparent>)
    outlineDir: 'masks/outline', // alphaVideo: the exported outline matte
    keepDir: 'masks/keep', // alphaVideo: drops tiny stray specks (RGBA, alpha = keep)
    audio: 'footage/original_audio.wav',
  },

  // ---- replaceable illustrated scene (1200x2134 layers: 10% margin for parallax / push-in) ----
  scene: {
    // To change the world, point these imports at new 1200x2134 layers (see README).
    background, // opaque back layer
    midground, // RGBA, sits behind the performer
    foreground, // RGBA, in front of the performer (kept off hands/keys)
    foregroundBlur, // RGBA soft out-of-focus corner leaves, in front
    paper, // grayscale paper texture overlay
    padX: 60,
    padY: 107,
  },

  // ---- camera / parallax (frame-based, eased; nearer layers move more) ----
  camera: {
    originX: 0.5,
    originY: 0.52,
    push: { back: 1.02, mid: 1.03, subject: 1.04, front: 1.07 }, // end scale per layer (start is 1.0)
    driftPx: { back: [0, -10], mid: [-8, -14], subject: [0, -4], front: [-10, -18] }, // total drift [x, y]
    sway: { midDeg: 0.35, frontDeg: 0.5, period: 150 }, // gentle leaf / flower sway
  },

  // ---- soft off-white silhouette outline (applied to the combined external silhouette matte) ----
  outline: {
    enabled: true,
    color: '#F5EBDD',
    widthPx: 3, // the exported matte is 3px; larger values dilate it, smaller values need a re-export
    blurPx: 1.5, // extra blur on top of the matte's own softness
    opacity: 0.65,
    fadeOutFromY: 1250, // fade the outline out below the keyboard (the gap between legs and piano is open at the frame edge)
    fadeOutToY: 1450,
  },
  // soft shadow of the performer + piano on the garden, strongest near the bottom, cast away from the upper-right light
  contactShadow: {enabled: true, color: '#0d1208', opacity: 0.55, blurPx: 22, offsetPx: [-14, 16] as [number, number], fromY: 700, toY: 1500},
  ambientOcclusion: {enabled: true, color: '#0d1208', opacity: 0.18, blurPx: 34, fromY: 650, toY: 1150}, // faint darkening around the lower body only (no halo around the head)
  edgeFeatherExtraPx: 0, // extra alpha softening on top of the 2px already in the export
  // 'sampled': the blurred garden bleeds onto a soft band just inside the silhouette edge (band width is set in make_mattes.py).
  // 'tint': older flat-colour rim via SVG filter.
  lightWrap: {enabled: true, mode: 'sampled' as 'sampled' | 'tint', opacity: 0.15, blurPx: 16, bandDir: 'masks/wrapband', color: '#E9C98E', sizePx: 7},

  // ---- colour matching (foreground only; keeps skin tones and the black piano realistic) ----
  grade: {
    saturation: 0.92,
    contrast: 0.96,
    liftBlacks: 0.012, // faded print feel
    warmth: 0.05, // +red / -blue
    highlightWarmth: 0.03,
  },
  grain: { opacity: 0.07, scale: 1.0 },
  paper: { opacity: 0.32, shiftPx: 18 },
  atmosphere: { color: '#F2C27A', base: 0.10, swing: 0.06 }, // slow warm-light variation, peaks around 6.5 s

  // ---- petals (a few, slow, deterministic) ----
  petals: {
    count: 9,
    startFrame: 110,
    endFrame: 215,
    color: '#D49A94',
    seed: 'storybook-petals',
    maxY: 760, // keep them clear of the hands and keyboard
    minX: 560, // and clear of the face (face spans roughly x 100-370 at y 330-800)
  },

  // ---- approximate Instagram Reels UI zones (not official numbers): header, caption/audio, right icon column ----
  safeZones: {top: 250, bottom: 400, rightColumn: {x: 930, y0: 900, y1: 1700}},

  // ---- typography ----
  title: {
    text: 'Some melodies never get old',
    lines: ['Some melodies', 'never get old'], // explicit line breaks; edit freely (Hindi lyrics etc.)
    fontFamily: 'Cormorant Garamond',
    fontStyle: 'italic' as const,
    fontWeight: 600,
    fontSize: 94,
    color: '#F2E3B3',
    letterSpacing: 1.5,
    centerX: 0.66, // fraction of width (kept right of the head)
    topPx: 262, // below the Reels header (see safeZones)
    scrimOpacity: 0.3, // very soft dark glow behind the text for legibility over blossoms (not a text shadow)
    fadeInFrames: [8, 52] as [number, number],
    fadeOutFrames: [196, 224] as [number, number],
    risePx: 22,
  },
};
