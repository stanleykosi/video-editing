# Lesson: DaVinci Resolve Full Workflow Foundations

## Source

- Tutorial: `transcripts/davinci resolve full tutorial.txt`
- Related cards:
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

## What The Tutorial Teaches

This tutorial teaches Resolve as a full post-production pipeline rather than a
single editing page. The useful agent abstraction is:

1. Organize projects, folders, bins, metadata, keywords, smart bins, and synced audio.
2. Assemble story in the Edit page or rough fast assemblies in the Cut page.
3. Use Fusion for node-based compositing, titles, masks, tracking, and subject isolation.
4. Use Color for project color management, primary balance, shot matching, looks, secondaries, and tracked windows.
5. Use Fairlight for clip, track, bus, ambience, SFX, music, EQ, and dialogue dynamics.
6. Use Deliver to choose a container, codec, audio format, render range, queue, filename, and archive/web preset.

The course is especially valuable because it separates page purpose: Edit/Cut
decide story, Fusion builds visual effects and graphics, Color shapes image
consistency and style, Fairlight shapes sound, and Deliver makes the finished
file. The pages share the same timeline, so the agent can move between them
without an external roundtrip.

## Agent Decision Rules

- Use Media page organization before a long edit when the source pool is large,
  messy, multi-camera, or documentary-like.
- Use keywords and smart bins when searching manually would slow the edit or
  when footage categories should update automatically.
- Use waveform audio sync when camera scratch audio and external audio share a
  visible waveform; check failed syncs before deleting camera audio.
- Use the Edit page for narrative editing, layered audio, detailed trimming, and
  Premiere-like workflows.
- Use the Cut page for fast one-clip-after-another assembly, rough news/vlog
  work, and simple multicam angle insertion from Sync Bin.
- Use Fusion when an effect needs masks, node order, tracking, compositing, or
  reusable procedural graphics. Use basic Edit page inspector keyframes for
  simple title or position moves.
- Use Color page clip nodes for per-shot correction and timeline nodes for a
  global look. Build or preview the look early when it is extreme enough to
  change matching decisions.
- Use Fairlight when track/bus organization, range edits, dynamics, EQ, ambience,
  SFX layering, or detailed music edits matter.
- Use Deliver presets only after confirming the target: web upload, client
  review, future edit/archive, alpha delivery, or per-clip conversion.

## Timeline Patterns

- Full workflow:
  `project_library -> media_pool_bins -> optional_audio_sync -> edit_or_cut_assembly -> Fusion_graphics -> Color_match_and_look -> Fairlight_mix -> Deliver_export`
- Edit page assembly:
  `source_preview -> set_in_out -> insert_or_overwrite -> cut_on_action_or_question -> trim_silence -> layer_inserts -> second_pass`
- Anchor shot structure:
  `wide_anchor_action -> cutaway_or_closeup_on_action -> return_or_continue_anchor -> add sound/color polish`
- Fusion compositing:
  `MediaIn -> source_correction -> mask_or_transform -> Merge -> tracker_or_magic_mask_if_needed -> MediaOut`
- Color pass:
  `project_color_management -> primary_balance -> hero_still -> shot_match -> creative_timeline_look -> secondaries -> final_scope_review`
- Fairlight pass:
  `dialogue_tracks -> ambience_bed -> music_fit -> obvious_SFX_pass -> group_or_bus_related_tracks -> EQ/dynamics -> full_mix_QC`
- Deliver pass:
  `choose_timeline -> set_range -> container -> codec -> audio -> filename/location -> render_queue -> watch_output`

## Implementation Notes

- Resolve: keep projects in a project library, export `.drp` backups when sharing
  or archiving, and use bins/metadata before timeline work grows.
- Resolve Media: dragging a folder into the bin list can preserve folder
  structure; dragging media directly into the pool can flatten it.
- Resolve Edit: use source In/Out points, insert/overwrite/replace/place-on-top,
  ripple trims, blade/split, timeline viewer shortcuts, and inspector keyframes.
- Resolve Fusion: node order matters. Corrections before a Merge affect the
  source branch; corrections after a Merge affect the combined result.
- Resolve Color: use color management for log/wide-gamut footage, scopes for
  objective balance, stills for shot matching, and subtle secondaries for faces,
  eyes, lips, or region control.
- Resolve Fairlight: organize by clips, tracks, and buses. Use range mode for
  partial clip edits, sound library search for large SFX pools, buses for group
  EQ/reverb/dynamics, and dialogue compression carefully.
- Resolve Deliver: choose codec by purpose. H.264/H.265 for compact web files,
  ProRes/DNxHR for handoff/archive, and individual clips only when converting or
  preparing clips for another app.
- ffmpeg: represent Resolve timeline choices as EDL/JSON data with explicit
  trim points, audio sync offsets, overlay graphs, color transforms, gain
  envelopes, and export profiles.
- Remotion: model bins, clips, overlays, Fusion-like node graphs, color presets,
  audio buses, and delivery profiles as structured project metadata.
- CapCut/Premiere: map the same ideas to project bins, source monitor I/O,
  insert/overwrite edits, nested/compound clips, masks, color correction,
  audio buses or track groups, and export presets.

## Mistakes And QC

- Do not start Fusion, Color, or Fairlight polish before the edit has a clear
  story and selected timeline version.
- Do not assume a clip is imported because it is visible in Media Storage; check
  the Media Pool.
- Do not trust batch audio sync without checking failures and channel layout.
- Do not leave leading black, accidental gaps, dead air, or empty audio holes.
- Do not use Cut page speed when the sequence needs detailed layered audio or
  narrative control.
- Do not use AI-only Studio features without a free/manual fallback.
- Do not overcompress dialogue or over-EQ SFX until they sound artificial.
- Do not render with a codec that does not match the delivery purpose.
- QC the rendered output, not only the Resolve timeline.

