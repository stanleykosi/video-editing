import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {GraphicRequest} from './schemas';

type Props = {request: GraphicRequest};
type Asset = GraphicRequest['assets'][number];

const baseFont = "Inter, 'DejaVu Sans', 'Liberation Sans', sans-serif";

const clampNumber = (value: number, minimum: number, maximum: number) =>
  Math.max(minimum, Math.min(maximum, value));

const fitTextSize = (
  text: string,
  maxWidth: number,
  maxHeight: number,
  preferred: number,
  minimum = 8,
) => {
  const characters = Math.max(1, text.trim().length);
  const longestWord = Math.max(1, ...text.split(/\s+/).map((word) => word.length));
  const byArea = Math.sqrt((maxWidth * maxHeight) / (characters * 0.78));
  const byWord = maxWidth / (longestWord * 0.62);
  return clampNumber(Math.min(preferred, byArea, byWord), minimum, preferred);
};

const useCanvasMetrics = () => {
  const {width, height} = useVideoConfig();
  const shortSide = Math.min(width, height);
  return {
    width,
    height,
    padding: clampNumber(shortSide * 0.065, 10, 72),
    gap: clampNumber(shortSide * 0.025, 4, 28),
    heading: clampNumber(shortSide * 0.075, 16, 72),
    body: clampNumber(shortSide * 0.036, 10, 34),
    label: clampNumber(shortSide * 0.026, 8, 24),
    display: clampNumber(shortSide * 0.17, 32, 170),
  };
};

const wrappingText: React.CSSProperties = {
  overflowWrap: 'anywhere',
  whiteSpace: 'pre-wrap',
};

const useEntrance = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = spring({frame, fps, config: {damping: 18, stiffness: 130}});
  return {
    opacity: interpolate(frame, [0, Math.max(1, fps * 0.2)], [0, 1], {
      extrapolateRight: 'clamp',
    }),
    transform: `translateY(${(1 - progress) * 28}px)`,
  };
};

const assetById = (request: GraphicRequest, id: string): Asset => {
  const asset = request.assets.find((candidate) => candidate.id === id);
  if (!asset) throw new Error(`undeclared graphic asset: ${id}`);
  return asset;
};

const Media = ({asset, style}: {asset: Asset; style?: React.CSSProperties}) => {
  const source = staticFile(asset.staged_name);
  return asset.media_type === 'video' ? (
    <OffthreadVideo muted src={source} style={{objectFit: 'cover', ...style}} />
  ) : (
    <Img src={source} style={{objectFit: 'cover', ...style}} />
  );
};

const Surface = ({request, children}: Props & {children: React.ReactNode}) => {
  const common = request.props as {background_color: string; text_color: string};
  return (
    <AbsoluteFill
      style={{
        backgroundColor: request.transparent ? 'transparent' : common.background_color,
        color: common.text_color,
        fontFamily: baseFont,
        letterSpacing: 0,
        overflow: 'hidden',
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

const TextCard = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {
    title: string;
    subtitle: string | null;
    label: string | null;
    alignment: 'left' | 'center' | 'right';
    accent_color: string;
    background_color: string;
  };
  const inset = metrics.padding;
  const innerWidth = metrics.width - inset * 3.2;
  const innerHeight = metrics.height - inset * 3.2;
  const titleSize = fitTextSize(
    props.title,
    innerWidth,
    innerHeight * (props.subtitle ? 0.58 : 0.82),
    metrics.heading,
  );
  const subtitleSize = props.subtitle
    ? fitTextSize(props.subtitle, innerWidth, innerHeight * 0.25, metrics.body)
    : metrics.body;
  return (
    <Surface request={request}>
      <AbsoluteFill style={{justifyContent: 'center', padding: inset}}>
        <div
          style={{
            ...motion,
            alignSelf: props.alignment === 'center' ? 'center' : undefined,
            borderLeft: props.alignment === 'left' ? `8px solid ${props.accent_color}` : undefined,
            borderRight:
              props.alignment === 'right' ? `8px solid ${props.accent_color}` : undefined,
            boxSizing: 'border-box',
            maxHeight: metrics.height - inset * 2,
            maxWidth: metrics.width - inset * 2,
            overflow: 'hidden',
            padding: inset * 0.45,
            textAlign: props.alignment,
            backgroundColor: `${props.background_color}E8`,
          }}
        >
          {props.label ? (
            <div style={{...wrappingText, color: props.accent_color, fontSize: metrics.label}}>
              {props.label}
            </div>
          ) : null}
          <div style={{...wrappingText, fontSize: titleSize, fontWeight: 800, lineHeight: 1.08}}>
            {props.title}
          </div>
          {props.subtitle ? (
            <div style={{...wrappingText, fontSize: subtitleSize, lineHeight: 1.25, marginTop: metrics.gap}}>
              {props.subtitle}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const LowerThird = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {
    name: string;
    role: string | null;
    accent_color: string;
    background_color: string;
  };
  return (
    <Surface request={request}>
      <AbsoluteFill style={{justifyContent: 'flex-end', padding: metrics.padding}}>
        <div
          style={{
            ...motion,
            alignSelf: 'flex-start',
            backgroundColor: `${props.background_color}EE`,
            borderBottom: `6px solid ${props.accent_color}`,
            maxWidth: '82%',
            padding: `${metrics.gap}px ${metrics.padding}px`,
          }}
        >
          <div style={{...wrappingText, fontSize: metrics.heading, fontWeight: 800}}>{props.name}</div>
          {props.role ? <div style={{...wrappingText, fontSize: metrics.body, marginTop: metrics.gap}}>{props.role}</div> : null}
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const Quote = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {
    quote: string;
    attribution: string | null;
    accent_color: string;
    background_color: string;
  };
  return (
    <Surface request={request}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: metrics.padding}}>
        <div style={{...motion, maxWidth: '88%', padding: '6%', background: `${props.background_color}E8`}}>
          <div style={{color: props.accent_color, fontSize: metrics.heading, lineHeight: 0.7}}>“</div>
          <div style={{...wrappingText, fontSize: fitTextSize(props.quote, metrics.width * 0.75, metrics.height * 0.5, metrics.heading * 0.78), fontWeight: 700, lineHeight: 1.18}}>{props.quote}</div>
          {props.attribution ? (
            <div style={{...wrappingText, fontSize: metrics.body, marginTop: metrics.gap, color: props.accent_color}}>
              {props.attribution}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const Stat = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {
    value: string;
    label: string;
    detail: string | null;
    accent_color: string;
    background_color: string;
  };
  return (
    <Surface request={request}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{...motion, textAlign: 'center', padding: '6%', background: `${props.background_color}E8`}}>
          <div style={{...wrappingText, color: props.accent_color, fontSize: fitTextSize(props.value, metrics.width * 0.75, metrics.height * 0.38, metrics.display), fontWeight: 900}}>{props.value}</div>
          <div style={{...wrappingText, fontSize: metrics.heading * 0.72, fontWeight: 700}}>{props.label}</div>
          {props.detail ? <div style={{...wrappingText, fontSize: metrics.body, marginTop: metrics.gap}}>{props.detail}</div> : null}
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const Countdown = ({request}: Props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const metrics = useCanvasMetrics();
  const props = request.props as {from_number: number; label: string | null; accent_color: string};
  const value = Math.max(0, props.from_number - Math.floor(frame / fps));
  return (
    <Surface request={request}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{fontSize: metrics.display, fontWeight: 900, color: props.accent_color}}>{value}</div>
        {props.label ? <div style={{...wrappingText, fontSize: metrics.body}}>{props.label}</div> : null}
      </AbsoluteFill>
    </Surface>
  );
};

const Comparison = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {
    title: string | null;
    left: {label: string; value: string};
    right: {label: string; value: string};
    accent_color: string;
    background_color: string;
  };
  return (
    <Surface request={request}>
      <AbsoluteFill style={{justifyContent: 'center', padding: metrics.padding}}>
        {props.title ? <div style={{...wrappingText, fontSize: metrics.heading * 0.75, fontWeight: 800, marginBottom: metrics.gap}}>{props.title}</div> : null}
        <div style={{...motion, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: metrics.gap}}>
          {[props.left, props.right].map((side) => (
            <div key={side.label} style={{background: `${props.background_color}EB`, padding: '9%'}}>
              <div style={{...wrappingText, color: props.accent_color, fontSize: metrics.label}}>{side.label}</div>
              <div style={{...wrappingText, fontSize: fitTextSize(side.value, metrics.width * 0.34, metrics.height * 0.32, metrics.heading * 0.72), fontWeight: 800, marginTop: metrics.gap}}>{side.value}</div>
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const MediaFrame = ({request, device = false}: Props & {device?: boolean}) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {asset_id: string; title: string | null; caption: string | null};
  const asset = assetById(request, props.asset_id);
  return (
    <Surface request={request}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: metrics.padding}}>
        {props.title ? <div style={{...wrappingText, fontSize: metrics.heading * 0.7, fontWeight: 800, marginBottom: metrics.gap}}>{props.title}</div> : null}
        <div
          style={{
            ...motion,
            width: device ? '58%' : '86%',
            height: device ? '72%' : '68%',
            border: device ? '14px solid #202020' : '3px solid #FFFFFF',
            borderRadius: device ? 28 : 4,
            overflow: 'hidden',
          }}
        >
          <Media asset={asset} style={{width: '100%', height: '100%'}} />
        </div>
        {props.caption ? <div style={{...wrappingText, fontSize: metrics.body, marginTop: metrics.gap}}>{props.caption}</div> : null}
      </AbsoluteFill>
    </Surface>
  );
};

const ProductFeature = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {
    title: string;
    description: string | null;
    bullets: string[];
    asset_id: string | null;
    accent_color: string;
    background_color: string;
  };
  return (
    <Surface request={request}>
      <AbsoluteFill style={{display: 'grid', gridTemplateColumns: props.asset_id ? '1fr 1fr' : '1fr', gap: metrics.gap, padding: metrics.padding, alignItems: 'center'}}>
        <div style={{...motion, background: `${props.background_color}E8`, padding: '8%'}}>
          <div style={{...wrappingText, fontSize: fitTextSize(props.title, metrics.width * (props.asset_id ? 0.36 : 0.72), metrics.height * 0.28, metrics.heading), fontWeight: 850}}>{props.title}</div>
          {props.description ? <div style={{...wrappingText, fontSize: metrics.body, lineHeight: 1.3, marginTop: metrics.gap}}>{props.description}</div> : null}
          {props.bullets.map((bullet) => (
            <div key={bullet} style={{...wrappingText, fontSize: metrics.body, marginTop: metrics.gap, borderLeft: `4px solid ${props.accent_color}`, paddingLeft: metrics.gap}}>{bullet}</div>
          ))}
        </div>
        {props.asset_id ? <Media asset={assetById(request, props.asset_id)} style={{width: '100%', maxHeight: '76%'}} /> : null}
      </AbsoluteFill>
    </Surface>
  );
};

const PictureInPicture = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {asset_id: string; corner: string; label: string | null; accent_color: string};
  const vertical = props.corner.startsWith('top') ? 'flex-start' : 'flex-end';
  const horizontal = props.corner.endsWith('left') ? 'flex-start' : 'flex-end';
  return (
    <Surface request={request}>
      <AbsoluteFill style={{alignItems: horizontal, justifyContent: vertical, padding: metrics.padding}}>
        <div style={{...motion, width: '36%', aspectRatio: '16 / 9', border: `5px solid ${props.accent_color}`, position: 'relative'}}>
          <Media asset={assetById(request, props.asset_id)} style={{width: '100%', height: '100%'}} />
          {props.label ? <div style={{...wrappingText, position: 'absolute', bottom: 0, left: 0, maxWidth: '100%', background: '#111111E8', padding: `${metrics.gap}px`, fontSize: metrics.label}}>{props.label}</div> : null}
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const SplitScreen = ({request}: Props) => {
  const metrics = useCanvasMetrics();
  const props = request.props as {left_asset_id: string; right_asset_id: string; divider: string; accent_color: string};
  const vertical = props.divider === 'vertical';
  return (
    <Surface request={request}>
      <AbsoluteFill style={{display: 'flex', flexDirection: vertical ? 'row' : 'column', gap: Math.max(2, metrics.gap * 0.35), background: props.accent_color}}>
        {[props.left_asset_id, props.right_asset_id].map((id) => (
          <div key={id} style={{flex: 1, overflow: 'hidden'}}>
            <Media asset={assetById(request, id)} style={{width: '100%', height: '100%'}} />
          </div>
        ))}
      </AbsoluteFill>
    </Surface>
  );
};

const LogoReveal = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {asset_id: string; tagline: string | null};
  return (
    <Surface request={request}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{...motion, textAlign: 'center'}}>
          <Media asset={assetById(request, props.asset_id)} style={{width: '42%', maxHeight: '58%'}} />
          {props.tagline ? <div style={{...wrappingText, fontSize: metrics.body, marginTop: metrics.gap}}>{props.tagline}</div> : null}
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const CallToAction = ({request}: Props) => {
  const motion = useEntrance();
  const metrics = useCanvasMetrics();
  const props = request.props as {title: string; action: string; detail: string | null; accent_color: string; background_color: string};
  return (
    <Surface request={request}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: metrics.padding}}>
        <div style={{...motion, textAlign: 'center', background: `${props.background_color}EA`, padding: '7%'}}>
          <div style={{...wrappingText, fontSize: fitTextSize(props.title, metrics.width * 0.72, metrics.height * 0.34, metrics.heading), fontWeight: 850}}>{props.title}</div>
          {props.detail ? <div style={{...wrappingText, fontSize: metrics.body, marginTop: metrics.gap}}>{props.detail}</div> : null}
          <div style={{...wrappingText, display: 'inline-block', maxWidth: '86%', color: '#111111', background: props.accent_color, fontSize: metrics.body, fontWeight: 800, marginTop: metrics.gap, padding: `${metrics.gap}px ${metrics.padding}px`}}>{props.action}</div>
        </div>
      </AbsoluteFill>
    </Surface>
  );
};

const ProgressAccent = ({request}: Props) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const props = request.props as {
    global_start_frame: number;
    total_frames: number;
    accent_color: string;
  };
  const progress = clampNumber(
    (props.global_start_frame + frame + 1) / props.total_frames,
    0,
    1,
  );
  const pulse = 0.45 + Math.sin(frame * 0.22) * 0.2;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: width * progress, height: Math.max(3, height * 0.006), background: props.accent_color}} />
      <div style={{position: 'absolute', left: 0, top: height * 0.2, width: Math.max(3, width * 0.008), height: height * 0.6, background: props.accent_color, opacity: pulse}} />
    </AbsoluteFill>
  );
};

const DiagramOverlay = ({request}: Props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const props = request.props as {
    variant: 'corner_pulse' | 'arrow_trace' | 'outline_trace' | 'label_pop';
    label: string | null;
    layout_variant: 'default' | 'payoff';
    accent_color: string;
    text_color: string;
    background_color: string;
  };
  const reveal = interpolate(frame, [0, Math.max(1, fps * 0.28)], [0, 1], {extrapolateRight: 'clamp'});
  if (props.variant === 'corner_pulse') {
    return <AbsoluteFill style={{border: `clamp(3px, 0.8vw, 10px) solid ${props.accent_color}`, boxSizing: 'border-box', opacity: reveal * 0.75}} />;
  }
  if (props.variant === 'outline_trace') {
    return <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}><div style={{border: `clamp(3px, 0.7vw, 9px) solid ${props.accent_color}`, width: `${62 * reveal}%`, height: `${42 * reveal}%`}} /></AbsoluteFill>;
  }
  if (props.variant === 'arrow_trace') {
    const right = props.layout_variant === 'payoff';
    return <AbsoluteFill style={{justifyContent: 'center', alignItems: right ? 'flex-end' : 'flex-start', padding: '12%'}}><div style={{display: 'flex', alignItems: 'center', flexDirection: right ? 'row-reverse' : 'row', opacity: reveal}}><div style={{height: 6, width: '22vw', maxWidth: 280, background: props.accent_color}} /><div style={{width: 0, height: 0, borderTop: '14px solid transparent', borderBottom: '14px solid transparent', borderLeft: right ? undefined : `24px solid ${props.accent_color}`, borderRight: right ? `24px solid ${props.accent_color}` : undefined}} /></div></AbsoluteFill>;
  }
  if (!props.label) return null;
  return <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}><div style={{...wrappingText, background: `${props.background_color}E8`, borderBottom: `6px solid ${props.accent_color}`, color: props.text_color, fontFamily: baseFont, fontSize: 'clamp(18px, 5vw, 64px)', fontWeight: 800, maxWidth: '78%', opacity: reveal, padding: '2% 4%'}}>{props.label}</div></AbsoluteFill>;
};

const EmphasisText = ({request}: Props) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const props = request.props as {
    text: string;
    variant: 'highlight_wipe' | 'staggered_glitch' | 'axis_stretch' | 'font_shift' | 'slide_up' | 'glow_underline';
    accent_color: string;
    secondary_accent: string;
    danger_accent: string;
    text_color: string;
    background_color: string;
  };
  const reveal = interpolate(frame, [0, Math.max(1, fps * 0.22)], [0, 1], {extrapolateRight: 'clamp'});
  const glitch = props.variant === 'staggered_glitch' ? Math.sin(frame * 2.4) * (1 - reveal) * 18 : 0;
  const translateY = props.variant === 'slide_up' ? (1 - reveal) * height * 0.12 : 0;
  const scaleX = props.variant === 'axis_stretch' ? 0.7 + reveal * 0.3 : 1;
  const color = props.variant === 'font_shift' && frame % 12 < 6 ? props.secondary_accent : props.text_color;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '8%'}}>
      <div style={{...wrappingText, color, fontFamily: baseFont, fontSize: fitTextSize(props.text, width * 0.8, height * 0.28, Math.min(width, height) * 0.11), fontWeight: 900, lineHeight: 1.05, maxWidth: '86%', opacity: reveal, padding: '2% 4%', position: 'relative', textAlign: 'center', textShadow: props.variant === 'glow_underline' ? `0 0 18px ${props.accent_color}` : undefined, transform: `translate(${glitch}px, ${translateY}px) scaleX(${scaleX})`}}>
        {props.text}
        <div style={{position: 'absolute', left: 0, bottom: 0, width: props.variant === 'highlight_wipe' ? `${reveal * 100}%` : '100%', height: 6, background: props.accent_color}} />
      </div>
    </AbsoluteFill>
  );
};

const KineticCaption = ({request}: Props) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const props = request.props as {
    text: string;
    variant: 'default' | 'adaptive_texture' | 'player3' | 'stock_panel';
    emphasis_terms: string[];
    accent_color: string;
    secondary_accent: string;
    text_color: string;
    background_color: string;
  };
  const reveal = interpolate(frame, [0, Math.max(1, fps * 0.15)], [0, 1], {extrapolateRight: 'clamp'});
  const emphasis = new Set(props.emphasis_terms.map((term) => term.toLowerCase()));
  const words = props.text.split(/(\s+)/);
  const background = props.variant === 'adaptive_texture' ? `${props.background_color}CC` : `${props.background_color}E8`;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', padding: '7%'}}>
      <div style={{...wrappingText, background, borderLeft: props.variant === 'player3' ? `7px solid ${props.secondary_accent}` : undefined, color: props.text_color, fontFamily: baseFont, fontSize: fitTextSize(props.text, width * 0.84, height * 0.18, Math.min(width, height) * 0.065), fontWeight: 850, lineHeight: 1.12, maxWidth: '88%', opacity: reveal, padding: '2.5% 4%', textAlign: 'center', transform: `translateY(${(1 - reveal) * 24}px)`}}>
        {words.map((word, index) => <React.Fragment key={`${index}-${word}`}><span style={{color: emphasis.has(word.trim().replace(/[^\p{L}\p{N}]/gu, '').toLowerCase()) ? props.accent_color : undefined}}>{word}</span></React.Fragment>)}
      </div>
    </AbsoluteFill>
  );
};

export const GraphicComponent: React.FC<Props> = ({request}) => {
  switch (request.component.id) {
    case 'title_card':
    case 'hook_card':
    case 'chapter_card':
      return <TextCard request={request} />;
    case 'lower_third':
      return <LowerThird request={request} />;
    case 'quote_card':
      return <Quote request={request} />;
    case 'stat_card':
    case 'number_card':
      return <Stat request={request} />;
    case 'countdown':
      return <Countdown request={request} />;
    case 'comparison':
      return <Comparison request={request} />;
    case 'product_feature':
      return <ProductFeature request={request} />;
    case 'screenshot_frame':
      return <MediaFrame request={request} />;
    case 'device_mockup':
      return <MediaFrame request={request} device />;
    case 'picture_in_picture':
      return <PictureInPicture request={request} />;
    case 'split_screen':
      return <SplitScreen request={request} />;
    case 'logo_reveal':
      return <LogoReveal request={request} />;
    case 'call_to_action':
    case 'end_card':
      return <CallToAction request={request} />;
    case 'progress_accent':
      return <ProgressAccent request={request} />;
    case 'diagram_overlay':
      return <DiagramOverlay request={request} />;
    case 'emphasis_text':
      return <EmphasisText request={request} />;
    case 'kinetic_caption':
      return <KineticCaption request={request} />;
    default:
      throw new Error(`unknown component: ${request.component.id}`);
  }
};
