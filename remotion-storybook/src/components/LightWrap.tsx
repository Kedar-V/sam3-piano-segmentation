import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {StorybookConfig} from '../config/storybook';
import {IllustratedBackground} from './IllustratedBackground';
import {subjectTransform, useFrameMask} from './useMaskStyle';

/**
 * Sampled light wrap: a blurred copy of the garden (back + mid layers, in their own camera space) shows through a soft band just
 * inside the performer's edge, so the edges pick up the surrounding colour and light. The band follows the performer's camera move;
 * the garden copy is counter-transformed so it stays aligned with the real background.
 */
export const LightWrap: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const {camera, lightWrap: lw} = cfg;
  const {style: band, holder} = useFrameMask(lw.bandDir, frame);
  if (!lw.enabled || lw.mode !== 'sampled') return null;
  const e = interpolate(frame, [0, durationInFrames - 1], [0, 1], {easing: Easing.out(Easing.quad)});
  const s = 1 + (camera.push.subject - 1) * e;
  const [dx, dy] = camera.driftPx.subject;
  const origin = `${camera.originX * 100}% ${camera.originY * 100}%`;
  return (
    <AbsoluteFill style={subjectTransform(s, dx * e, dy * e, camera.originX, camera.originY)}>
      {holder}
      <AbsoluteFill style={{...band, opacity: lw.opacity}}>
        {/* inverse of the performer transform -> back to screen space, where the background layers live */}
        <AbsoluteFill style={{transform: `translate(${-dx * e}px, ${-dy * e}px) scale(${1 / s})`, transformOrigin: origin}}>
          <AbsoluteFill style={{filter: `blur(${lw.blurPx}px)`}}>
            <IllustratedBackground cfg={cfg} layer="back" />
            <IllustratedBackground cfg={cfg} layer="mid" />
          </AbsoluteFill>
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
