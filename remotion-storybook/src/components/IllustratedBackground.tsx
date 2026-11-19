import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {StorybookConfig} from '../config/storybook';

type Layer = 'back' | 'mid' | 'front';

/**
 * One illustrated layer with eased push-in, drift and gentle sway (all frame-based).
 * Layers are oversized (padX/padY margin) so the camera move never reveals an edge.
 * Use layer="back"/"mid" behind the performer and layer="front" in front of it.
 */
export const IllustratedBackground: React.FC<{cfg: StorybookConfig; layer: Layer}> = ({cfg, layer}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width, height} = useVideoConfig();
  const {scene, camera} = cfg;
  const e = interpolate(frame, [0, durationInFrames - 1], [0, 1], {easing: Easing.out(Easing.quad)}); // push slows toward the end
  const key = layer === 'back' ? 'back' : layer === 'mid' ? 'mid' : 'front';
  const scale = 1 + (camera.push[key] - 1) * e;
  const [dx, dy] = camera.driftPx[key];
  const sway = layer === 'mid' ? camera.sway.midDeg : layer === 'front' ? camera.sway.frontDeg : 0;
  const rot = sway * Math.sin((frame / camera.sway.period) * Math.PI * 2 + (layer === 'front' ? 1.3 : 0));
  const origin = `${camera.originX * 100}% ${camera.originY * 100}%`;
  // sway pivots from where the foliage is anchored: top-right for mid, bottom-left for the corner flowers
  const swayOrigin = layer === 'mid' ? '90% 0%' : '5% 100%';

  const srcs: string[] =
    layer === 'back' ? [scene.background] : layer === 'mid' ? [scene.midground] : [scene.foreground, scene.foregroundBlur];

  return (
    <AbsoluteFill style={{transform: `scale(${scale}) translate(${dx * e}px, ${dy * e}px)`, transformOrigin: origin}}>
      {srcs.map((s, i) => (
        <div
          key={s}
          style={{
            position: 'absolute',
            left: -scene.padX,
            top: -scene.padY,
            width: width + 2 * scene.padX,
            height: height + 2 * scene.padY,
            transform: i === 0 && sway ? `rotate(${rot}deg)` : undefined,
            transformOrigin: swayOrigin,
          }}
        >
          <Img src={s} style={{width: '100%', height: '100%'}} />
        </div>
      ))}
    </AbsoluteFill>
  );
};
