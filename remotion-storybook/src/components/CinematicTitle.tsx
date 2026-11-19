import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/google-fonts/CormorantGaramond';
import type {StorybookConfig} from '../config/storybook';

// Elegant serif. For Hindi lyrics, load a Devanagari font (e.g. '@remotion/google-fonts/TiroDevanagariHindi') and set cfg.title.fontFamily.
const {fontFamily: cormorant} = loadFont('italic', {weights: ['600'], subsets: ['latin']});

/** Understated caption: gentle fade-in, slow upward drift, fade-out. No shadows, no flashy motion. */
export const CinematicTitle: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  const t = cfg.title;
  const opacity =
    interpolate(frame, t.fadeInFrames, [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)}) *
    interpolate(frame, t.fadeOutFrames, [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
  const rise = interpolate(frame, [t.fadeInFrames[0], t.fadeOutFrames[1]], [t.risePx, -t.risePx * 0.6], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  const family = t.fontFamily === 'Cormorant Garamond' ? cormorant : `${t.fontFamily}, serif`;
  const lines = t.lines && t.lines.length ? t.lines : [t.text];
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          top: t.topPx,
          left: width * t.centerX,
          transform: `translate(-50%, ${rise}px)`,
          opacity,
          textAlign: 'center',
          fontFamily: family,
          fontStyle: t.fontStyle,
          fontWeight: t.fontWeight,
          fontSize: t.fontSize,
          lineHeight: 1.08,
          letterSpacing: t.letterSpacing,
          color: t.color,
          whiteSpace: 'nowrap',
        }}
      >
        {t.scrimOpacity > 0 && (
          <div
            style={{
              position: 'absolute',
              inset: '-40% -18%',
              zIndex: -1,
              background: `radial-gradient(ellipse at center, rgba(16,20,10,${t.scrimOpacity}) 0%, rgba(16,20,10,0) 70%)`,
            }}
          />
        )}
        {lines.map((l, i) => (
          <div key={i} style={{position: 'relative'}}>{l}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
