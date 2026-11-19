import React from 'react';
import {Img, staticFile} from 'remotion';

export const pad5 = (n: number) => String(n).padStart(5, '0');

/**
 * CSS mask from a per-frame RGBA PNG (alpha = mask).
 * The mask is ALWAYS applied for the current frame (no async "ready" state: Remotion may capture a frame before effect-registered
 * holds, so hiding/unmounting while loading caused missing frames). Instead, `holder` renders the same image invisibly through
 * Remotion's <Img>, which reliably delays the capture until it has loaded; the CSS mask then uses the cached image.
 */
export const useFrameMask = (dir: string, frame: number): {style: React.CSSProperties; holder: React.ReactElement} => {
  const url = staticFile(`${dir}/${pad5(frame)}.png`);
  return {
    style: {WebkitMaskImage: `url(${url})`, maskImage: `url(${url})`, WebkitMaskSize: '100% 100%', maskSize: '100% 100%'},
    holder: React.createElement(Img, {src: url, style: {position: 'absolute', width: 1, height: 1, opacity: 0, pointerEvents: 'none'}}),
  };
};

/** Same camera transform the performer layer uses (eased push-in + drift). */
export const subjectTransform = (scale: number, dx: number, dy: number, ox: number, oy: number): React.CSSProperties => ({
  transform: `scale(${scale}) translate(${dx}px, ${dy}px)`,
  transformOrigin: `${ox * 100}% ${oy * 100}%`,
});
