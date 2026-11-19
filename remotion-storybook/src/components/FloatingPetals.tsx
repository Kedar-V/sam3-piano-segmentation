import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame, useVideoConfig} from 'remotion';
import type {StorybookConfig} from '../config/storybook';

/** A handful of slow drifting petals. Fully deterministic: every value derives from `random(seed)` and the frame number. */
export const FloatingPetals: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = cfg.petals;

  const petals = useMemo(
    () =>
      Array.from({length: p.count}, (_, i) => {
        const r = (k: string) => random(`${p.seed}-${i}-${k}`);
        const dur = 78 + r('d') * 40;
        return {
          start: p.startFrame + r('s') * Math.max(1, p.endFrame - p.startFrame - dur),
          dur,
          x0: 640 + r('x') * 520,
          y0: -50 + r('y') * 240,
          vx: -(30 + r('vx') * 60), // px / s (slow, leftwards)
          vy: 150 + r('vy') * 130, // px / s (downwards)
          sway: 26 + r('sw') * 36,
          phase: r('p') * 6.28,
          size: 20 + r('z') * 16,
          rot0: r('r') * 360,
          rotV: (r('rv') - 0.5) * 120,
        };
      }),
    [p.count, p.seed, p.startFrame, p.endFrame],
  );

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <svg width="100%" height="100%" viewBox={`0 0 ${cfg.width} ${cfg.height}`} style={{position: 'absolute'}}>
        {petals.map((pt, i) => {
          const t = frame - pt.start;
          if (t < 0 || t > pt.dur) return null;
          const dt = t / fps;
          const x = pt.x0 + pt.vx * dt + pt.sway * Math.sin(pt.phase + dt * 2.0);
          const y = pt.y0 + pt.vy * dt;
          const fade =
            interpolate(t, [0, 14, pt.dur - 20, pt.dur], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) *
            interpolate(y, [p.maxY - 120, p.maxY], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) *
            interpolate(x, [p.minX, p.minX + 120], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          if (fade <= 0.01) return null;
          const flip = 0.35 + 0.65 * Math.abs(Math.cos(pt.phase + dt * 2.6));
          const rotate = pt.rot0 + pt.rotV * dt;
          return (
            <g key={i} transform={`translate(${x.toFixed(2)} ${y.toFixed(2)}) rotate(${rotate.toFixed(2)}) scale(${flip.toFixed(3)} 1) scale(${pt.size})`} opacity={fade * 0.85}>
              <path d="M0,-1 C0.85,-0.55 0.95,0.55 0,1 C-0.95,0.55 -0.85,-0.55 0,-1 Z" fill={p.color} />
              <path d="M0,-0.9 C0.35,-0.4 0.4,0.3 0,0.9" fill="none" stroke="#F0CFC4" strokeWidth={0.07} opacity={0.6} />
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
