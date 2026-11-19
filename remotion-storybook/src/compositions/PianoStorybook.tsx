import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {storybook, type StorybookConfig} from '../config/storybook';
import {IllustratedBackground} from '../components/IllustratedBackground';
import {PianoForeground} from '../components/PianoForeground';
import {FloatingPetals} from '../components/FloatingPetals';
import {PaperTexture} from '../components/PaperTexture';
import {CinematicTitle} from '../components/CinematicTitle';
import {ContactShadow} from '../components/ContactShadow';
import {LightWrap} from '../components/LightWrap';
import {SafeZoneGuide} from '../components/SafeZoneGuide';

/**
 * Layer order (back to front):
 *   illustrated background -> midground foliage -> contact shadow -> [outline + real performance] -> sampled light wrap
 *   -> corner flowers -> petals
 *   -> warm atmosphere -> paper + grain -> title
 * Timeline (24 fps, 10 s): 0-2s bg + performance visible, push-in begins, title fades in; 2-5s gentle parallax;
 * 5-8s petals drift, light shifts; 8-10s camera slows (eased), title fades out. The performance is never cut or retimed.
 */
export const PianoStorybook: React.FC<{cfg?: StorybookConfig; showSafeZones?: boolean}> = ({cfg = storybook, showSafeZones = false}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const a = cfg.atmosphere;
  const atm = a.base + a.swing * Math.sin(Math.PI * Math.min(1, Math.max(0, (frame - 48) / (durationInFrames - 48))));
  return (
    <AbsoluteFill style={{backgroundColor: '#1c2214'}}>
      <Audio src={staticFile(cfg.footage.audio)} />
      <IllustratedBackground cfg={cfg} layer="back" />
      <IllustratedBackground cfg={cfg} layer="mid" />
      <ContactShadow cfg={cfg} />
      <PianoForeground cfg={cfg} />
      <LightWrap cfg={cfg} />
      <IllustratedBackground cfg={cfg} layer="front" />
      <FloatingPetals cfg={cfg} />
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          mixBlendMode: 'screen',
          opacity: atm,
          background: `radial-gradient(ellipse 75% 45% at 82% 6%, ${a.color} 0%, transparent 70%)`,
        }}
      />
      <PaperTexture cfg={cfg} />
      <CinematicTitle cfg={cfg} />
      {showSafeZones && <SafeZoneGuide cfg={cfg} />}
    </AbsoluteFill>
  );
};
