---
name: scriptwriting
description: Use when crafting scripts, storyboards, and messaging for video content.
---

# Video Scriptwriting Systems Skill

## Required Subagent Review Loop

For any new or substantially rewritten video script, use
`content_creation/script_subagent_review_loop.md`.

- A dedicated writer subagent drafts the script using this skill and the relevant
  project knowledge.
- A separate critic subagent judges it harshly and independently.
- The script is not accepted until the critic returns `PASS`.
- If the critic returns `FAIL`, the writer revises from the critique and the loop
  repeats.

## When to Use

- Developing scripts for explainer, testimonial, thought leadership, or product videos.
- Aligning scripts with positioning, CTA, and voice/tone guidelines.
- Iterating on scripts based on feedback or performance data.

## Framework

1. **Hook** - capture attention in first 5 seconds (question, stat, bold claim).
2. **Problem/Insight** - relate to audience pain or opportunity.
3. **Solution Story** - product capability or narrative proof with visuals.
4. **Proof** - customer quote, metric, analyst validation.
5. **CTA** - single next step (demo, trial, download, subscribe).

## Templates

- Script template with columns for VO/dialogue, visuals, motion notes, duration.
- Storyboard grid with frame, description, audio, graphics, CTA.
- Tone/voice checklist (personality traits, jargon allowances, compliance notes).

## Tips

- Write for ear: short sentences, contractions, conversational tone.
- Add direction for B-roll, overlays, animations, and text callouts.
- Plan variant clips (15s teaser, 6s bumper, square stories) from the start.
- Avoid model-script cliches such as "it's not X, it's Y", "if not X then Y",
  "what happens next changes everything", "this is where things get interesting",
  "little did he know", "one thing is clear", and "a testament to".
- Make every beat visual, causal, and specific enough for an editor to cut
  against.

## Repo Usage Note

For movie recaps, anime recaps, and narration-over-source edits, combine this
with `skills/movie_recap_workflow.md`, `content_creation/scriptwriter.md`, and
the relevant story/QC knowledge. Use this skill for stronger hooks, clearer
voiceover structure, visual notes, duration planning, and tone control; do not
force product-video CTAs into recap scripts unless the user asks for them.
