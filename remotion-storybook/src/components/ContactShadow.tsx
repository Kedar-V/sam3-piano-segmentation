import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {StorybookConfig} from '../config/storybook';
import {subjectTransform, useFrameMask} from './useMaskStyle';

/**
 * Grounds the performer in the garden: a blurred, offset silhouette shadow (strongest near the bottom, cast to the lower-left,
 * away from the warm upper-right light) plus a faint ambient-occlusion halo. Built from the per-frame matte; nothing is baked.
 */
export const ContactShadow: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, height} = useVideoConfig();
  const {camera, contactShadow: cs, ambientOcclusion: ao} = cfg;
  const {style: mask, holder} = useFrameMask(cfg.footage.matteDir, frame);
  const e = interpolate(frame, [0, durationInFrames - 1], [0, 1], {easing: Easing.out(Easing.quad)});
  const s = 1 + (camera.push.subject - 1) * e;
  const [dx, dy] = camera.driftPx.subject;
  const t = subjectTransform(s, dx * e, dy * e, camera.originX, camera.originY);
  const silhouette = (color: string) => <AbsoluteFill style={{...mask, backgroundColor: color}} />;
  const aoGrad = `linear-gradient(to bottom, transparent ${(ao.fromY / height) * 100}%, black ${(ao.toY / height) * 100}%)`;
  const grad = `linear-gradient(to bottom, transparent ${(cs.fromY / height) * 100}%, black ${(cs.toY / height) * 100}%)`;
  return (
    <AbsoluteFill style={t}>
      {holder}
      {ao.enabled && (
        <AbsoluteFill style={{WebkitMaskImage: aoGrad, maskImage: aoGrad, opacity: ao.opacity}}>
          <AbsoluteFill style={{filter: `blur(${ao.blurPx}px)`}}>{silhouette(ao.color)}</AbsoluteFill>
        </AbsoluteFill>
      )}
      {cs.enabled && (
        <AbsoluteFill style={{WebkitMaskImage: grad, maskImage: grad, opacity: cs.opacity}}>
          <AbsoluteFill style={{filter: `blur(${cs.blurPx}px)`, transform: `translate(${cs.offsetPx[0]}px, ${cs.offsetPx[1]}px)`}}>
            {silhouette(cs.color)}
          </AbsoluteFill>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
