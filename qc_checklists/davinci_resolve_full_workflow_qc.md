# DaVinci Resolve Full Workflow QC

Use this checklist before previewing or exporting a complete Resolve project.

## Project And Media

- Project library, timeline, and exported `.drp` backup names identify the project and version.
- All used footage is imported into the Media Pool, not only visible through Media Storage.
- Bins, keywords, smart bins, and metadata labels are useful enough to find footage again.
- External audio syncs were checked by playback and failed syncs are marked for manual repair.
- Multi-channel WAV dialogue is routed to usable mono or stereo tracks without one-sided speech.

## Edit And Cut

- Timeline starts on the intended first frame with no accidental leading black.
- No timeline gaps or black frames remain unless intentionally marked.
- Source In/Out edits preserve the useful action and do not include handles as dead time.
- Insert shots answer a story question, clarify action, hide a continuity mismatch, or provide needed perspective.
- Cut-on-action edits keep motion believable across the cut.
- Cut page or Sync Bin choices were reviewed in the Edit page if layered audio or narrative detail is required.

## Fusion And Motion

- Fusion node order is intentional and named enough to debug.
- Masks are feathered/refined enough that edges do not draw attention.
- Tracker or Magic Mask results were reviewed across the whole affected range.
- Edit page keyframes and Fusion keyframes ease cleanly and hold after landing when readability matters.
- Fusion effects do not crop faces, captions, proof, UI, or action.

## Color

- Color management or color transforms are correct for log/wide-gamut footage.
- Scopes show no accidental crushed important shadows or clipped important highlights.
- Hero still comparison was used for shot matching, not only memory or adjacent shots.
- Timeline look nodes do not hide shot-level mismatch, faces, captions, or proof.
- Windows, qualifiers, and tracked secondaries remain subtle and do not reveal rough keys.

## Fairlight And Mix

- Dialogue, ambience, music, and SFX live on controllable tracks or buses.
- Room tone or ambience prevents empty-feeling dead air under dialogue scenes.
- Major SFX are synced to visible story actions and are not only heard while soloed.
- Bus routing reaches the main output; no audible track is silently routed to nowhere.
- Dialogue compression improves intelligibility without sounding crushed, noisy, or unnatural.
- EQ distance effects sound motivated by screen space or story context.
- Music edits happen on beats, phrase endings, or matching waveform shapes and use fades/crossfades where needed.
- Full mix has no clipping, harsh pops, or SFX peaks that overpower dialogue.

## Deliver

- Render range, timeline, resolution, frame rate, filename, and output folder match the intended delivery.
- Container and codec match purpose: compact web file, client review, archive, alpha, or editing handoff.
- Audio settings include the needed mix or separate tracks for archive/handoff.
- Render queue contains only intended jobs.
- Final exported file was watched for wrong range, offline media, black frames, clipping, caption collisions, and codec/playback problems.

