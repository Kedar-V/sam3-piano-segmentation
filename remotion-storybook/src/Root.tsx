import React from 'react';
import {Composition} from 'remotion';
import {PianoStorybook} from './compositions/PianoStorybook';
import {storybook} from './config/storybook';

export const Root: React.FC = () => (
  <Composition
    id="PianoStorybook"
    component={PianoStorybook}
    durationInFrames={storybook.durationInFrames}
    fps={storybook.fps}
    width={storybook.width}
    height={storybook.height}
    defaultProps={{cfg: storybook, showSafeZones: false}}
  />
);
