# DaVinci Resolve Full Workflow

## Purpose

Guide full DaVinci Resolve projects from media organization through Edit/Cut,
Fusion, Color, Fairlight, and Deliver so the agent can build complete edits
rather than isolated effects.

## When To Use This Skill

- Building or planning a complete Resolve edit from raw footage to final export.
- Translating Resolve tutorials into reusable agent workflow knowledge.
- Organizing large footage pools with bins, keywords, metadata, and smart bins.
- Syncing external audio to camera footage by waveform.
- Choosing between Resolve Edit page and Cut page workflows.
- Building Fusion composites, tracked graphics, masks, simple VFX, or titles.
- Matching shots, building looks, using scopes, or applying tracked secondaries.
- Finishing a mix in Fairlight with dialogue, ambience, music, SFX, tracks, and buses.
- Selecting delivery settings for web upload, client review, archive, or roundtrip handoff.
- Building reusable Resolve show, podcast, course, or creator-brand intros that combine Fusion motion, Text+, logo/proof footage, and Fairlight SFX.

## Core Principles

- Treat Resolve as a page-based pipeline: Media organizes, Edit/Cut builds story,
  Fusion creates effects, Color shapes the image, Fairlight shapes sound, and
  Deliver creates the watchable file.
- Organize footage before timeline complexity makes search expensive.
- The Media Storage browser is not the same thing as imported project media; the
  Media Pool is the project source of truth.
- Edit/Cut choices should answer story questions, preserve action continuity,
  and build a watchable cut before visual polish begins.
- Fusion nodes are modular. Node order decides what gets affected.
- Color nodes group corrections; use clip nodes for shot-specific work and
  timeline nodes for whole-timeline looks.
- Fairlight is clips, tracks, and buses. Keep dialogue, ambience, music, and SFX
  controllable.
- Delivery settings are editorial decisions: container, codec, audio, range, and
  filename should match the purpose of the render.
- Resolve Studio AI features can be valuable, but every repeatable agent workflow
  should keep a free/manual fallback unless the project explicitly requires Studio.

Contradiction note: the Cut page can be the fastest route for simple assemblies
and Sync Bin multicam, but the Edit page is preferred for layered narrative work,
complex audio, detailed trimming, and workflows that need Premiere-like control.

Contradiction note: color can be neutral and technically balanced, but a creative
look may intentionally bias temperature, contrast, or saturation. Prefer
intentional consistency, readable faces/proof, and scope-safe levels over blindly
neutral white balance.

Contradiction note: Fusion can make intros feel premium, but ordinary mid-length
YouTube videos should usually start with value. Use a formal Resolve intro only
when brand identity, credible proof, or outcome packaging earns the delay.

## Techniques

- `technique_cards/davinci_project_library_media_pool_setup_001.json`
- `technique_cards/davinci_bins_keywords_smart_bins_001.json`
- `technique_cards/davinci_waveform_audio_sync_media_pool_001.json`
- `technique_cards/davinci_edit_page_in_out_story_assembly_001.json`
- `technique_cards/davinci_anchor_shot_action_cutting_001.json`
- `technique_cards/davinci_cut_page_speed_sync_bin_multicam_001.json`
- `technique_cards/davinci_edit_page_keyframe_easing_titles_001.json`
- `technique_cards/davinci_fusion_node_compositing_basics_001.json`
- `technique_cards/davinci_fusion_tracker_magic_mask_graphics_001.json`
- `technique_cards/davinci_color_management_primary_look_001.json`
- `technique_cards/davinci_color_hero_still_shot_matching_001.json`
- `technique_cards/davinci_color_secondary_windows_qualifier_tracker_001.json`
- `technique_cards/davinci_fairlight_dialogue_ambience_bus_mix_001.json`
- `technique_cards/davinci_deliver_codec_render_queue_archive_001.json`
- `technique_cards/davinci_timeline_shortcuts_efficiency_001.json`
- `technique_cards/sound_audio_leveling_track_hygiene_001.json`
- `technique_cards/beat_sync_needle_drop_action_cue_001.json`
- `technique_cards/retention_intro_format_gate_001.json`
- `technique_cards/retention_brand_authority_outcome_intro_001.json`
- `technique_cards/motion_premium_intro_text_logo_flicker_001.json`
- `technique_cards/sound_frame_locked_intro_sfx_drums_001.json`

## Timing Rules

- Remove leading black, accidental gaps, and empty audio holes before polish.
- Set source In/Out points before placing footage when only a portion of the
  clip serves the story.
- Cut on action when a closeup, insert, or alternate angle would otherwise reveal
  a continuity mismatch.
- Use a wide or anchor shot to establish the action path, then place closeups or
  inserts over it where they clarify action, perspective, or emotion.
- Use waveform-based trimming for dialogue only after checking that removed
  pauses are truly dead air.
- Move keyframes closer for faster motion and farther apart for calmer motion;
  add easing so title/position moves do not slam or drift.
- In Fairlight, align major SFX to visible action and keep music edits on beats
  or similar waveform shapes when shortening a track manually.
- In Deliver, render only the intended timeline/range and watch the output before
  treating it as final.
- For formal show/podcast/course intros, cap the opener around 10-15 seconds maximum unless the brief explicitly requires a longer program open.
- For social-series intros built in Resolve, cap the opener around 3-5 seconds and hand off immediately to the content.

## Motion Rules

- Use Edit page inspector keyframes for simple position, scale, opacity, and title moves.
- Use Fusion when the effect needs multiple sources, masks, tracking, merge
  order, procedural texture, or node reuse.
- For simple titles or graphics, ease the final keyframe and flatten/smooth the
  curve enough that the move resolves cleanly.
- In Fusion, use Merge nodes to combine foreground/background, mask inputs to
  localize an effect, and Transform nodes to scale/position elements.
- Use tracker data for attached text, rectangles, heat signatures, or masks when
  the camera or subject moves.
- Use Magic Mask only when Studio is available and the subject isolation is worth
  the extra review; still inspect edges and tracking.
- Use Fusion clips, Text+, MultiMerge, Transform nodes, masks, motion blur, and 3D/camera-style setups only where they clarify brand, proof, and outcome.
- In premium intros, each text or logo layer needs a role before keyframing.

## Sound Rules

- Sync external audio by waveform when camera scratch audio and external audio
  share a clear reference.
- Split multi-channel production WAV files into proper mono dialogue tracks when
  dialogue appears only on one side.
- Use Fairlight range mode for partial clip gain, deletion, or automation without
  unnecessary splitting.
- Add room tone or ambience under dialogue scenes so gaps do not become dead air.
- Add SFX in passes: start with obvious story sounds the viewer expects, then
  layer supporting body, object, and environment texture.
- Use separate tracks for distinct SFX families, then group or bus related tracks
  when shared volume or EQ/reverb is needed.
- Use low-pass/EQ to make off-screen or behind-door sounds feel farther away.
- Use dialogue compression sparingly: reduce loud peaks, add makeup gain, and
  stop before the voice sounds crushed or noisy.
- In Fairlight, align intro SFX to visible Fusion/Text+ events and duck or fade the intro bed before the first body line.

## Caption Rules

- Captions follow the audible edited dialogue, not the original source clip timing.
- Do not let titles, Fusion graphics, or Color/Fairlight page work cause caption
  collisions that were not present in the rough cut.
- When a Fusion or Color secondary is designed around a face, eyes, lips, UI, or
  proof detail, keep captions away from that region.
- Check caption readability after final grade and after any render upscaling.

## Color Rules

- Use Resolve color management or explicit color transforms for log/wide-gamut
  footage before judging contrast and saturation.
- Use scopes because eyes adapt quickly to a grade.
- Build primary balance before secondaries: exposure, contrast, temperature/tint,
  saturation, and useful curve shaping.
- Choose a hero still and match other shots against that reference rather than
  comparing each new shot to the previous shot only.
- Use timeline nodes for global looks and clip nodes for shot matching under that look.
- Use windows, qualifiers, and tracked masks subtly; harsh keys and aggressive
  secondaries reveal bad selections quickly.
- Preserve faces, proof, captions, and compression cleanliness before stylized looks.

## Tool Implementation Notes

- Resolve project/library: keep projects in a project library and export `.drp`
  backups for sharing or archiving.
- Resolve media: build bins, use list/thumbnail/metadata views, add keywords,
  and use smart bins for live filters.
- Resolve audio sync: select camera clips and external audio, run waveform sync,
  then inspect the synced audio column and playback before muting or deleting
  scratch audio.
- Resolve Edit: use source viewer In/Out, insert/overwrite/replace/place-on-top,
  trim tools, ripple trims, blade/split, markers, and inspector keyframes.
- Resolve Cut: use Source Tape, dual timelines, smart insert, one-click
  transitions, and Sync Bin for quick assemblies and multicam cutaways.
- Resolve Fusion: build from MediaIn to MediaOut with focused nodes; rename nodes
  when the graph grows.
- Resolve Color: use serial nodes, parallel nodes, stills, scopes, windows,
  qualifiers, trackers, and timeline nodes deliberately.
- Resolve Fairlight: use range mode, focus mode, track naming/color, mixer,
  sound library, buses, EQ, dynamics, and output routing.
- Resolve Deliver: choose Single Clip for final movies, Individual Clips for
  conversion or handoff, then set container, codec, audio, filename, location,
  render queue, and archive/web variants.
- Resolve intro workflow: mark brand, proof, outcome, SFX, and body-start frames; build the intro as a nested/compound section; then QC it at final aspect ratio before reuse.
- ffmpeg: store Resolve-equivalent trim, sync, color, overlay, gain, and export
  decisions in JSON/EDL before rendering.
- Remotion: represent pages as explicit project phases and store technique card
  data for clips, masks, transforms, color passes, audio buses, and export profiles.
- CapCut/Premiere equivalent: use bins, source monitor I/O, timeline tracks,
  masks, effects controls, color panels, audio track mixer/buses, and export presets.

## Common Mistakes

- Treating visible Media Storage footage as imported project media.
- Dragging folders into the wrong Media Pool area and losing useful folder structure.
- Batch syncing audio and never checking failed or one-sided results.
- Starting Fusion, Color, or Fairlight polish before the story edit works.
- Using the Cut page for a sequence that needs detailed layered trimming and audio control.
- Leaving title/keyframe motion linear, abrupt, or drifting after it lands.
- Adding Fusion nodes without knowing whether the correction belongs before or after a Merge.
- Matching color by eye only after staring at the same frame too long.
- Forcing an extreme look that fights the actual production design or client tone.
- Leaving dialogue, music, SFX, and ambience collapsed into one uncontrollable track.
- Routing tracks to a bus that does not feed the main output.
- Exporting with a codec chosen by habit instead of delivery purpose.
- Building a complex Fusion intro without first deciding whether the video format needs an intro.
- Letting motion blur, 3D camera movement, or SFX make proof quotes and outcome text harder to read.

## QC Checklist

- Project, timeline, media pool, bins, and backups are named clearly enough to reopen later.
- Imported media is in the Media Pool; external folders are not only visible in Media Storage.
- Synced external audio plays centered or correctly routed and failed syncs are marked for manual repair.
- Rough cut has no accidental leading black, gaps, or dead air.
- Edit/Cut page choice matches the actual complexity of the sequence.
- Fusion effects have intentional node order, masks, tracking, and easing.
- Color management, scopes, hero stills, and shot matching were checked before final look approval.
- Fairlight tracks, buses, effects, and main output routing are audible and organized.
- Dialogue, ambience, music, and SFX are balanced in the full mix, not only while soloed.
- Render settings match the target platform, client, or archive purpose.
- Final exported file is watched for black frames, offline media, clipping, caption collisions, and wrong range.
- Formal intros pass the format gate, duration cap, brand/proof/outcome readability, and Fairlight SFX handoff checks.

## Source Lessons Added

- 2026-05-29: `DaVinci Resolve Full Tutorial`
- 2026-05-29: `Killer Intros`
