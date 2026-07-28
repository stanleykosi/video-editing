# Remotion Seeded Glitch Scramble Text

Use this preset for short tech, AMV, decode, or shock text where the agent needs
repeatable glitch motion.

## Pattern

`short word -> seeded jitter/scramble -> lock/resolve -> stable readable hold`

## Settings

- Randomness: seeded by frame and/or character index; avoid direct random calls.
- Jitter cadence: every 2-3 frames when every-frame changes are too noisy.
- Text length: short words or short phrases only.
- Sound: optional glitch cue should end with the resolve.

## QC

- Same frame renders the same offsets on repeated exports.
- Final word locks before the cut.
- RGB/scramble stays readable at phone size.

## Related Cards

- `knowledge/techniques/typography/typography_remotion_seeded_scramble_glitch_001.json`

