# Audio

## Canonical Model

Audio clips use rational source/timeline ranges plus an audio sample clock.
Tracks have explicit roles: dialogue, voice-over, source, music, ambience,
room-tone, foley, and SFX. Items may override track routing. Buses form one strict
tree rooted at master; disabling a bus mutes its full subtree.

## Processing

The engine compiles gain, pan, fades, crossfades, automation, EQ,
compression, limiting, gate, de-essing, noise reduction, side-chain ducking,
channel mapping, sample-rate conversion, and loudness normalization. Effects are
typed; backend filter expressions are compilation output.

## Correctness And QC

- Cue placement and J/L-cut boundaries are sample-accurate.
- Every hard source boundary receives configurable pop prevention.
- Loudness/true-peak targets belong to delivery profiles; there is no global
  social-media target.
- QC measures integrated loudness, true peak, clipping, unexpected silence,
  missing audio, channel imbalance, mono compatibility, boundary discontinuity,
  and A/V duration mismatch.

The legacy -14 LUFS behavior remains a compatibility profile only.

## Implemented Boundary

Static item/track/bus gain, stereo pan, rational gain/pan automation, fades, EQ,
compression, limiting, gate, de-essing, noise reduction, channel mapping,
sample-rate conversion, mixing, side-chain ducking, exact transition crossfades,
and one/two-pass loudness lowering are executable. Source-rate probing, float PCM
intermediates, sample-count delays, range/full automation equivalence, exact
output length, delivery channel layout, clipping, loudness, true peak, silence,
channel balance, mono compatibility, boundary discontinuity, and A/V duration
checks are tested. Explicit cue and automation boundaries must be exactly
representable on the delivery sample clock. General multichannel pan matrices
outside the typed channel-map contract fail explicitly.
