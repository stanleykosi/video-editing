# Manim Video Skill

Production pipeline for mathematical and technical animations using [Manim Community Edition](https://www.manim.community/).

## What it does

Creates 3Blue1Brown-style animated videos from text prompts. The agent handles the full pipeline: creative planning, Python code generation, rendering, scene stitching, and iterative refinement.

## Use cases

- **Concept explainers** — "Explain how neural networks learn"
- **Equation derivations** — "Animate the proof of the Pythagorean theorem"
- **Algorithm visualizations** — "Show how quicksort works step by step"
- **Data stories** — "Animate our before/after performance metrics"
- **Architecture diagrams** — "Show our microservice architecture building up"

## Prerequisites

Python 3.11, Manim CE, LaTeX, and FFmpeg. Manim is intentionally isolated from
the root engine environment because current Manim requires NumPy 2.1+, while
the media stack is pinned to NumPy 1.26.

```bash
uv sync --project tools/video-use/vendor/manim-video --frozen
export VIDEO_ENGINE_MANIM="$PWD/tools/video-use/vendor/manim-video/.venv/bin/manim"
```

The canonical engine invokes this executable through its typed `manim_scene`
backend. Do not render and stitch Manim output manually for engine projects.
