import React from 'react';
import {AbsoluteFill, Img, useCurrentFrame, useVideoConfig} from 'remotion';
import type {StorybookConfig} from '../config/storybook';

/** Paper fibre overlay (very light, slowly shifting) plus shared film grain over the whole picture. */
export const PaperTexture: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const {paper, grain, scene} = cfg;
  const op = paper.opacity * (0.92 + 0.08 * Math.sin(frame / 37));
  const sx = paper.shiftPx * Math.sin(frame / 90);
  const sy = paper.shiftPx * 0.6 * Math.cos(frame / 110);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <Img
        src={scene.paper}
        style={{
          position: 'absolute',
          left: -24,
          top: -24,
          width: width + 48,
          height: height + 48,
          transform: `translate(${sx}px, ${sy}px)`,
          mixBlendMode: 'soft-light',
          opacity: op,
        }}
      />
      <svg width={width} height={height} style={{position: 'absolute', inset: 0, mixBlendMode: 'overlay', opacity: grain.opacity}}>
        <filter id="pf-grain" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency={0.85 / grain.scale} numOctaves={2} seed={frame} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#pf-grain)" />
      </svg>
    </AbsoluteFill>
  );
};
