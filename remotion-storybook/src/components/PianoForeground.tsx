import React from 'react';
import {AbsoluteFill, Easing, interpolate, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {StorybookConfig} from '../config/storybook';
import {hexToRgb01, pad5, SoftOutline} from './SoftOutline';
import {useFrameMask} from './useMaskStyle';

/** 4x5 colour matrix: saturation -> per-channel warm gain -> contrast -> lifted blacks / warm highlights. */
const gradeMatrix = (g: StorybookConfig['grade']): string => {
  const s = g.saturation;
  const sat = [
    [0.213 + 0.787 * s, 0.715 - 0.715 * s, 0.072 - 0.072 * s],
    [0.213 - 0.213 * s, 0.715 + 0.285 * s, 0.072 - 0.072 * s],
    [0.213 - 0.213 * s, 0.715 - 0.715 * s, 0.072 + 0.928 * s],
  ];
  const gain = [1 + g.warmth, 1 + g.warmth * 0.35, 1 - g.warmth];
  const hl = [g.highlightWarmth * 0.5, 0, -g.highlightWarmth * 0.5];
  const off = 0.5 * (1 - g.contrast) + g.liftBlacks;
  const rows = sat.map((row, i) => [...row.map((v) => (v * gain[i] * g.contrast).toFixed(4)), '0', (off + hl[i]).toFixed(4)].join(' '));
  return [...rows, '0 0 0 1 0'].join('  ');
};

/**
 * The real performance: exported ProRes 4444 (straight alpha) rendered with transparency, then graded and given an
 * optional light wrap, all as non-destructive SVG filters. Specks are removed via a per-frame keep mask. The source
 * footage is never modified.
 */
export const PianoForeground: React.FC<{cfg: StorybookConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width, height} = useVideoConfig();
  const {camera, footage, lightWrap, edgeFeatherExtraPx} = cfg;
  const e = interpolate(frame, [0, durationInFrames - 1], [0, 1], {easing: Easing.out(Easing.quad)});
  const scale = 1 + (camera.push.subject - 1) * e;
  const [dx, dy] = camera.driftPx.subject;

  const plate = footage.mode === 'plateMatte';
  const {style: maskStyle, holder} = useFrameMask(plate ? footage.matteDir : footage.keepDir, frame);

  const wrapSize = Math.max(1, lightWrap.sizePx);
  return (
    <AbsoluteFill style={{transform: `scale(${scale}) translate(${dx * e}px, ${dy * e}px)`, transformOrigin: `${camera.originX * 100}% ${camera.originY * 100}%`}}>
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <defs>
          <filter id="pf-finish" x="-3%" y="-3%" width="106%" height="106%" colorInterpolationFilters="sRGB">
            <feColorMatrix in="SourceGraphic" type="matrix" values={gradeMatrix(cfg.grade)} result="graded" />
            {edgeFeatherExtraPx > 0 ? (
              <>
                <feGaussianBlur in="SourceAlpha" stdDeviation={edgeFeatherExtraPx / 2} result="softA" />
                <feComposite in="graded" in2="softA" operator="in" result="gradedSoft" />
              </>
            ) : (
              <feOffset in="graded" dx="0" dy="0" result="gradedSoft" />
            )}
            {lightWrap.enabled && lightWrap.mode === 'tint' ? (
              <>
                <feMorphology in="SourceAlpha" operator="erode" radius={wrapSize} result="eroded" />
                <feComposite in="SourceAlpha" in2="eroded" operator="out" result="band" />
                <feGaussianBlur in="band" stdDeviation={wrapSize * 0.6} result="bandSoft" />
                <feFlood floodColor={lightWrap.color} floodOpacity={lightWrap.opacity} result="wrapColor" />
                <feComposite in="wrapColor" in2="bandSoft" operator="in" result="wrapRaw" />
                <feComposite in="wrapRaw" in2="SourceAlpha" operator="in" result="wrap" />
                <feMerge>
                  <feMergeNode in="gradedSoft" />
                  <feMergeNode in="wrap" />
                </feMerge>
              </>
            ) : null}
          </filter>
        </defs>
      </svg>
      {/* outline sits behind; footage (alpha video or plate) is masked, then graded/wrapped by the SVG filter */}
      {holder}
      <SoftOutline cfg={cfg} />
      <AbsoluteFill style={{filter: 'url(#pf-finish)'}}>
        <AbsoluteFill style={maskStyle}>
          {plate ? (
            <OffthreadVideo src={staticFile(footage.plate)} muted style={{width, height}} />
          ) : (
            <OffthreadVideo src={staticFile(footage.video)} transparent muted style={{width, height}} />
          )}
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export {hexToRgb01};
