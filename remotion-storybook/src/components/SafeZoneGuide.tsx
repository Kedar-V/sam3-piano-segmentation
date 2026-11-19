import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import type {StorybookConfig} from '../config/storybook';

/** Debug overlay of the approximate Reels UI zones. Off in renders unless the `showSafeZones` prop is set. */
export const SafeZoneGuide: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const {width, height} = useVideoConfig();
  const z = cfg.safeZones;
  const box = (l: number, t: number, w: number, h: number) => (
    <div style={{position: 'absolute', left: l, top: t, width: w, height: h, background: 'rgba(255,0,0,0.28)', outline: '2px solid rgba(255,80,80,0.9)'}} />
  );
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {box(0, 0, width, z.top)}
      {box(0, height - z.bottom, width, z.bottom)}
      {box(z.rightColumn.x, z.rightColumn.y0, width - z.rightColumn.x, z.rightColumn.y1 - z.rightColumn.y0)}
    </AbsoluteFill>
  );
};
