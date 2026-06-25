# Professional Title Graphics Pipeline

## Purpose

Make title cards, hook cards, chapter cards, stat cards, lower thirds, and major
motion-typography overlays look professionally designed before they enter a final
video render.

## When To Use This Skill

- Designing a title card, hook card, chapter card, stat card, or lower third.
- Adding a major typographic overlay to a clipped short, podcast cutdown,
  faceless video, documentary explainer, or social edit.
- Replacing a rough placeholder card with a final title treatment.
- Preparing approval frames before a title or motion graphic is composited.
- Reviewing whether captions should continue through a title moment.

## Non-Negotiables

- Final captions use ASS subtitles from the repo caption style system.
- HyperFrames is the default engine for title cards, hook cards, chapter cards,
  stat cards, lower thirds, and designed text systems.
- Remotion is the default engine for polished motion graphics, animated
  typography, reusable components, data-driven graphics, and precise timing.
- Pillow/PIL must not be used for final title, caption, lower-third, hook-card, or
  chapter-card typography. It is allowed only for diagnostics, masks, contact
  sheets, rough placeholders, or non-typographic helper assets.
- Title text must be meaningful, human, short, and tied to the actual clip.
- New or materially changed title designs require user approval before final
  compositing.
- Captions continue through title overlays by default. Reposition or restyle
  captions instead of suppressing them. Suppression requires explicit user
  approval and must preserve spoken meaning.

## Workflow

1. Read the active brief, reference video, caption style, typography skill, motion
   graphics skill, and QC checklist.
2. Write the title job in plain language: what the viewer should feel or
   understand, exact title copy, timing window, and why it belongs in the edit.
3. Choose the render engine:
   - HyperFrames for static-to-animated title cards, hook cards, stat cards,
     lower thirds, HTML/CSS layouts, GSAP motion, and transparent WebM overlays.
   - Remotion for React/CSS motion systems, reusable typography components,
     animated graphics, data-driven components, and frame-precise sequences.
4. Build the design with explicit font roles, hierarchy, line breaks, safe region,
   colors, motion states, and caption interaction notes.
5. Render approval frames or a contact sheet before compositing:
   - reveal start
   - reveal midpoint
   - final readable hold
   - clear/exit frame
   - optional bright/dark background checks for alpha overlays
6. Show the approval frames to the user and wait for approval before continuing.
7. After approval, render the final alpha/overlay asset and composite it into the
   edit.
8. Apply ASS captions last and verify captions remain readable through the title
   window.
9. Run visual QC contact sheets and fix collisions, weak title copy, bad kerning,
   poor line breaks, alpha artifacts, face blocking, source overlays, or caption
   conflicts before final.

## Required Artifacts

- `title_design_brief.md` or an equivalent section in `project.md`.
- A title approval contact sheet or exported still frames.
- A note recording user approval before final compositing.
- Rendered HyperFrames or Remotion source inside the project animation slot.
- Caption continuity notes in the EDL or project log.

## Design Standards

- Prefer simple, confident titles over busy decorative systems.
- Use one primary phrase and one support phrase at most unless the user approved a
  denser editorial title card.
- Keep text aligned, optically centered, and phone-readable.
- Make the title feel native to the clip, not like a generic AI-generated overlay.
- Use reference-driven typography and motion, but do not copy protected publisher
  identity.
- Avoid vague labels, filler jargon, fake interface language, random numbers, and
  title copy that does not add meaning.
- Motion should reveal hierarchy, not distract from the spoken idea.

## QC Checklist

- The title copy is clear, relevant, and not generic.
- HyperFrames or Remotion was used for the final title/motion graphic.
- No final title or caption typography was rendered with Pillow/PIL.
- Approval frames were reviewed by the user before final compositing.
- ASS captions remain visible, repositioned, or explicitly approved for any
  suppression window.
- Title, captions, face, proof, UI, source text, and platform safe areas do not
  collide.
- The title reads at phone size in reveal, hold, and exit frames.
- Alpha overlays have no black boxes, fringes, muddy halos, or codec-related
  transparency loss.
