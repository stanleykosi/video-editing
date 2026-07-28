import {z} from 'zod';

const color = z.string().regex(/^#[0-9A-Fa-f]{6}$/);
const common = {
  accent_color: color,
  text_color: color,
  background_color: color,
};

const textCard = z.strictObject({
  ...common,
  title: z.string().min(1).max(180),
  subtitle: z.string().max(280).nullable(),
  label: z.string().max(80).nullable(),
  alignment: z.enum(['left', 'center', 'right']),
});
const lowerThird = z.strictObject({
  ...common,
  name: z.string().min(1).max(100),
  role: z.string().max(140).nullable(),
});
const quoteCard = z.strictObject({
  ...common,
  quote: z.string().min(1).max(400),
  attribution: z.string().max(120).nullable(),
});
const statCard = z.strictObject({
  ...common,
  value: z.string().min(1).max(40),
  label: z.string().min(1).max(140),
  detail: z.string().max(180).nullable(),
});
const countdown = z.strictObject({
  ...common,
  from_number: z.number().int().min(1).max(99),
  label: z.string().max(100).nullable(),
});
const comparisonSide = z.strictObject({
  label: z.string().min(1).max(80),
  value: z.string().min(1).max(120),
});
const comparison = z.strictObject({
  ...common,
  title: z.string().max(120).nullable(),
  left: comparisonSide,
  right: comparisonSide,
});
const productFeature = z.strictObject({
  ...common,
  title: z.string().min(1).max(120),
  description: z.string().max(260).nullable(),
  bullets: z.array(z.string()).max(5),
  asset_id: z.string().regex(/^[A-Za-z0-9_.-]+$/).nullable(),
});
const mediaFrame = z.strictObject({
  ...common,
  asset_id: z.string().regex(/^[A-Za-z0-9_.-]+$/),
  title: z.string().max(120).nullable(),
  caption: z.string().max(180).nullable(),
});
const pictureInPicture = z.strictObject({
  ...common,
  asset_id: z.string().regex(/^[A-Za-z0-9_.-]+$/),
  corner: z.enum(['top_left', 'top_right', 'bottom_left', 'bottom_right']),
  label: z.string().max(80).nullable(),
});
const splitScreen = z.strictObject({
  ...common,
  left_asset_id: z.string().regex(/^[A-Za-z0-9_.-]+$/),
  right_asset_id: z.string().regex(/^[A-Za-z0-9_.-]+$/),
  divider: z.enum(['vertical', 'horizontal']),
});
const logoReveal = z.strictObject({
  ...common,
  asset_id: z.string().regex(/^[A-Za-z0-9_.-]+$/),
  tagline: z.string().max(140).nullable(),
});
const callToAction = z.strictObject({
  ...common,
  title: z.string().min(1).max(120),
  action: z.string().min(1).max(80),
  detail: z.string().max(180).nullable(),
});
const progressAccent = z.strictObject({
  ...common,
  global_start_frame: z.number().int().nonnegative(),
  total_frames: z.number().int().positive(),
});
const diagramOverlay = z.strictObject({
  ...common,
  variant: z.enum(['corner_pulse', 'arrow_trace', 'outline_trace', 'label_pop']),
  label: z.string().max(120).nullable(),
  layout_variant: z.enum(['default', 'payoff']),
});
const emphasisText = z.strictObject({
  ...common,
  text: z.string().min(1).max(180),
  variant: z.enum([
    'highlight_wipe',
    'staggered_glitch',
    'axis_stretch',
    'font_shift',
    'slide_up',
    'glow_underline',
  ]),
  secondary_accent: color,
  danger_accent: color,
});
const kineticCaption = z.strictObject({
  ...common,
  text: z.string().min(1).max(400),
  variant: z.enum(['default', 'adaptive_texture', 'player3', 'stock_panel']),
  emphasis_terms: z.array(z.string()).max(24),
  secondary_accent: color,
});

export const propSchemas = {
  title_card: textCard,
  hook_card: textCard,
  chapter_card: textCard,
  lower_third: lowerThird,
  quote_card: quoteCard,
  stat_card: statCard,
  number_card: statCard,
  countdown,
  comparison,
  product_feature: productFeature,
  screenshot_frame: mediaFrame,
  device_mockup: mediaFrame,
  picture_in_picture: pictureInPicture,
  split_screen: splitScreen,
  logo_reveal: logoReveal,
  call_to_action: callToAction,
  end_card: callToAction,
  progress_accent: progressAccent,
  diagram_overlay: diagramOverlay,
  emphasis_text: emphasisText,
  kinetic_caption: kineticCaption,
} as const;

const asset = z.strictObject({
  id: z.string().regex(/^[A-Za-z0-9_.-]+$/),
  sha256: z.string().regex(/^[0-9a-f]{64}$/),
  media_type: z.enum(['image', 'video']),
  staged_name: z.string().regex(/^[A-Za-z0-9_.-]+$/),
});

export const requestSchema = z
  .strictObject({
    schema_version: z.literal('1.0.0'),
    component: z.strictObject({
      id: z.string().regex(/^[a-z0-9_]+$/),
      version: z.string().regex(/^\d+\.\d+\.\d+$/),
      source_digest: z.string().regex(/^[0-9a-f]{64}$/),
    }),
    canvas: z.strictObject({
      width: z.number().int().positive().max(16384),
      height: z.number().int().positive().max(16384),
      frame_rate: z.strictObject({
        numerator: z.number().int().positive(),
        denominator: z.number().int().positive(),
      }),
      duration_frames: z.number().int().positive(),
    }),
    render_range: z.strictObject({
      start_frame: z.number().int().nonnegative(),
      end_frame_exclusive: z.number().int().positive(),
    }),
    props: z.record(z.string(), z.unknown()),
    assets: z.array(asset),
    transparent: z.boolean(),
    color_space: z.literal('rec709'),
  })
  .superRefine((value, context) => {
    if (value.component.version !== '1.0.0') {
      context.addIssue({code: 'custom', message: 'unsupported component version'});
    }
    if (value.render_range.end_frame_exclusive > value.canvas.duration_frames) {
      context.addIssue({code: 'custom', message: 'render range exceeds duration'});
    }
    const schema = propSchemas[value.component.id as keyof typeof propSchemas];
    if (!schema) {
      context.addIssue({code: 'custom', message: 'unknown component id'});
      return;
    }
    const result = schema.safeParse(value.props);
    if (!result.success) {
      for (const issue of result.error.issues) {
        context.addIssue({...issue, path: ['props', ...issue.path]});
      }
    }
  });

export type GraphicRequest = z.infer<typeof requestSchema>;
