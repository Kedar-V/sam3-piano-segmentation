import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import type {StorybookConfig} from '../config/storybook';

export const hexToRgb01 = (hex: string): [number, number, number] => {
  const h = hex.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255) as [number, number, number];
};

export const pad5 = (n: number) => String(n).padStart(5, '0');

/**
 * Soft off-white outline drawn from the exported per-frame outline matte (external silhouette only,
 * not every finger or key). The matte is grayscale; an SVG filter turns its luminance into the alpha of
 * a flat colour, so colour / width / blur / opacity stay adjustable and nothing is baked into the footage.
 * Rendered behind the performer, so it only shows outside the silhouette.
 */
export const SoftOutline: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const o = cfg.outline;
  if (!o.enabled) return null;
  const [r, g, b] = hexToRgb01(o.color);
  const dilate = Math.max(0, (o.widthPx - 3) / 2); // matte is exported at 3px
  return (
    <AbsoluteFill>
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <defs>
          <filter id="pf-outline" x="-2%" y="-2%" width="104%" height="104%" colorInterpolationFilters="sRGB">
            <feColorMatrix type="matrix" values={`0 0 0 0 ${r}  0 0 0 0 ${g}  0 0 0 0 ${b}  1 0 0 0 0`} />
            {dilate > 0 && <feMorphology operator="dilate" radius={dilate} />}
            {o.blurPx > 0 && <feGaussianBlur stdDeviation={o.blurPx} />}
          </filter>
        </defs>
      </svg>
      <Img
        src={staticFile(`${cfg.footage.mode === 'plateMatte' ? cfg.footage.outlineDirClosed : cfg.footage.outlineDir}/${pad5(frame)}.png`)}
        style={{width: '100%', height: '100%', filter: 'url(#pf-outline)', opacity: o.opacity}}
      />
    </AbsoluteFill>
  );
};
