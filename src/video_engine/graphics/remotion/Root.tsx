import React from 'react';
import {Composition} from 'remotion';
import {GraphicComponent} from './registry';
import {requestSchema, type GraphicRequest} from './schemas';

const defaults: GraphicRequest = {
  schema_version: '1.0.0',
  component: {id: 'title_card', version: '1.0.0', source_digest: '0'.repeat(64)},
  canvas: {
    width: 1920,
    height: 1080,
    frame_rate: {numerator: 30, denominator: 1},
    duration_frames: 90,
  },
  render_range: {start_frame: 0, end_frame_exclusive: 90},
  props: {
    title: 'Video Engine',
    subtitle: null,
    label: null,
    alignment: 'left',
    accent_color: '#F4C95D',
    text_color: '#FFFFFF',
    background_color: '#111111',
  },
  assets: [],
  transparent: true,
  color_space: 'rec709',
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="VideoEngineGraphic"
    component={({request}: {request: GraphicRequest}) => (
      <GraphicComponent request={requestSchema.parse(request)} />
    )}
    defaultProps={{request: defaults}}
    durationInFrames={defaults.canvas.duration_frames}
    fps={30}
    width={defaults.canvas.width}
    height={defaults.canvas.height}
    calculateMetadata={({props}) => {
      const request = requestSchema.parse(props.request);
      return {
        width: request.canvas.width,
        height: request.canvas.height,
        fps: request.canvas.frame_rate.numerator / request.canvas.frame_rate.denominator,
        durationInFrames: request.canvas.duration_frames,
      };
    }}
  />
);
