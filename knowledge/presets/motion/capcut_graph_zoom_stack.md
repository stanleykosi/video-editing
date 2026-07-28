# CapCut Graph Zoom Stack

## Use When

- A stylized short, AMV, action edit, or sports montage needs a strong
  After Effects-style zoom built in CapCut.
- Source resolution and crop safety can survive heavy magnification.

## Pattern

`clip -> scale_300_graph_zoom -> export -> reimport -> split -> scale_150_graph_zoom -> export -> motion_blur`

## Suggested Values

- First pass: end scale around `300`, reposition subject to center.
- Second pass: end scale around `150`, re-center after splitting the re-imported clip.
- Motion blur: start around Blur `10`, Blend `10`, then lower if readability drops.
- Graph: use a smooth curve unless the edit intentionally needs a hard snap.

## QC

- The subject stays centered through both passes.
- The image is not too soft after export/re-import.
- Motion blur does not smear captions, faces, proof, UI, products, or action.
