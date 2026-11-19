# Piano Storybook (Remotion)

A 10 s, 1080x1920 (9:16) Instagram Reel: your **real** piano performance (from the SAM 3 exports) composited over a layered, hand-painted-style
Indian garden. Remotion handles all animation and compositing; the performance itself is never regenerated, retimed or repainted.

```
src/
  compositions/PianoStorybook.tsx     layer order + timeline
  components/IllustratedBackground.tsx  back / mid / front illustration layers (parallax, push-in, sway)
  components/PianoForeground.tsx        the performance: matte/alpha, grade, light wrap
  components/SoftOutline.tsx            off-white silhouette outline (separate matte, not baked)
  components/FloatingPetals.tsx         seeded drifting petals
  components/PaperTexture.tsx           paper overlay + shared film grain
  components/CinematicTitle.tsx         serif caption
  config/storybook.ts                   ALL tweakable parameters
  assets/illustrations/                 replaceable scene layers (see below)
scripts/                                asset builders (illustrations, mattes, keep masks, static preview)
public/                                 footage + per-frame masks (large; git-ignored, see "Setup")
```

## Run
```bash
npm install
npm run studio                                   # live preview
npx remotion still src/index.ts PianoStorybook out/frame.png --frame=120
npm run render                                   # -> out/piano_storybook_demo.mp4 (H.264, CRF 16, yuv420p, BT.709)
```
Use React 18 (pinned). React 19.3 failed to load the Remotion root in headless Chrome.

## Setup (large assets are not in git)
`public/` holds derived copies of the exports in `../outputs/piano_compositing` (APFS clones, no extra disk):
```bash
SRC=../outputs/piano_compositing
cp -c $SRC/alpha/foreground_alpha.mov $SRC/source/original_audio.wav public/footage/
cp -cR $SRC/masks/outline public/masks/outline && cp -cR $SRC/masks/combined public/masks/combined
# opaque 10 s plate: the same 240 frames as the export, from the untouched source video
ffmpeg -i /path/to/TujhseNarazPiano.mov -t 10 -an -fps_mode passthrough -c:v libx264 -preset slow -crf 8 -pix_fmt yuv420p \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 public/footage/plate_10s.mp4
python scripts/make_mattes.py 7 5000 1500        # gap-closed matte + outline from the refined masks
python scripts/make_keep_masks.py 5000 8         # only needed for footage.mode = 'alphaVideo'
python scripts/make_illustrations.py             # regenerate the prototype illustration layers (needs numpy, scipy, opencv, pillow)
```
Source assets (original video, `foreground_alpha.mov`, raw masks, SAM 3 outputs) are never modified.

## Footage modes (`footage.mode`)
- `plateMatte` (default): opaque original frames + a soft matte from your existing refined masks. The raw performer and piano masks
  overlap by 0 px, which leaves a thin halo of background between hands and keys in the exported alpha video; `make_mattes.py` fills that
  seam (and tiny pinholes / specks) so the hands sit cleanly on the keys.
- `alphaVideo`: the exported `foreground_alpha.mov` (ProRes 4444, straight alpha). **Verified:** Remotion's `<OffthreadVideo transparent>`
  renders its alpha correctly (46% of a test frame was exactly the background colour, matching the export's transparency). It is the
  conformant path if you want the export used untouched; it just carries the seam halo.

## Replace the background
1. Make new layers at **1200x2134** (the frame plus a 60/107 px margin so parallax and the push-in never show an edge):
   `background` (opaque), `midground` (RGBA, behind you), `foreground` (RGBA, in front; keep it off the hands/keys), `foregroundBlur`
   (RGBA soft corner leaves), `paper` (grayscale texture).
2. Drop them into `src/assets/illustrations/` and change the five imports at the top of `src/config/storybook.ts`.
3. Design around your silhouette: the free background areas are the top ~third, the right of your head, and small bits of the bottom-left.
   Keep the zone around the hands and keyboard quiet. No re-segmentation is needed for a new scene.

## Replace the text
Edit `title` in `src/config/storybook.ts`: `lines` (explicit line breaks), `fontFamily`, `fontSize`, `color`, position (`centerX`, `topPx`) and
fade frames. For Hindi lyrics load a Devanagari font in `CinematicTitle.tsx`, e.g.
`import {loadFont} from '@remotion/google-fonts/TiroDevanagariHindi'`, and set `fontFamily` to it. The title sits in the upper right, clear of the face.

## Key parameters (`src/config/storybook.ts`)
| Group | Notes |
|---|---|
| `outline` | `color #F5EBDD`, `widthPx 3` (matte is exported at 3 px; larger dilates it), `blurPx 1.5`, `opacity 0.65`. External silhouette only. |
| `edgeFeatherExtraPx` | Extra alpha softening. The matte/export already has ~2 px feather, so default 0. |
| `lightWrap` | Simplified rim light: an SVG filter band just inside the silhouette tinted with `color`, `opacity 0.15`. It does not sample the background. |
| `grade` | Foreground only: saturation 0.92, contrast 0.96, lifted blacks, slight warmth. Skin tones and the black piano stay natural. |
| `camera` | Eased push-in (slows toward the end) with per-layer scale and drift for parallax; leaf/flower sway. |
| `petals` | 9 slow petals between ~4.6 s and ~9 s, kept clear of the face (`minX`) and hands (`maxY`). Deterministic (`seed`). |
| `grain`, `paper`, `atmosphere` | Shared film grain, paper texture, slow warm-light variation. |

Everything is frame-based (`useCurrentFrame`/`interpolate`/`random(seed)`); no browser timers.

## Timeline (24 fps, 240 frames)
0-2 s background + performance visible, push-in starts, title fades in. 2-5 s gentle parallax and foliage sway. 5-8 s a few petals drift, light
shifts slightly. 8-10 s camera movement slows, title fades out. The performance is never cut, frozen or retimed. Audio is the original WAV.

## IMPORTANT: illustrations are a prototype
I had no image-generation model available, so `scripts/make_illustrations.py` paints the layers procedurally (two-tone leaves, rough painted
edges, wash, brushy grain, paper texture). They follow the reference palette and layout but are **not real hand-painted art**. Still to be generated
or commissioned in the reference's style (hand-painted Indian storybook, muted olive/moss, dusty pink flowers, warm light):
- the full `background` plate (with a believable garden wall / light source rather than a repeating leaf pattern),
- `midground` branches and blossoms, and `foreground` tulips/flowers with real painterly brushwork,
- optionally separate drifting-petal sprites (petals are currently drawn as simple SVG shapes).

## Known limitations
- Outline/light wrap follow the matte, so any matte error shows up there. Dark patches under the legs (bench/shadow) are part of the exported mask.
- Masks are binary-derived, not true alpha mattes: hair strands and finger motion blur are not matted.
- The footage is a 10 s segment (0:00-0:10 of the source). A different segment needs a new SAM 3 run and export first.
