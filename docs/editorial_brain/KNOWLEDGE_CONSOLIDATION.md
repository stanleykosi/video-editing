# Knowledge Consolidation Contract

`editorial_brain.knowledge` implements a deterministic compilation pipeline:

```text
playbooks + lessons + techniques + presets + styles + QC
    -> safe atomic statements
    -> normalized semantic signatures
    -> duplicate clusters
    -> principles / recipes / gates
    -> contextual conflict graph
    -> checked source-neutral base
    -> per-video TasteProfile
    -> bounded EditorialPolicy directives
```

Normalization removes URLs, markup, tool boilerplate, path-like material, and
lexical variants before clustering. `use_when` and `avoid_when` become
applicability predicates; they are not promoted into standalone taste advice.
Technique and preset mirrors collapse into recipes. Checks and common mistakes
become quality gates rather than silently changing cut weights.

The build fails validation for duplicate principle IDs, duplicate semantic
signatures, dangling conflict references, duplicate recipe/gate IDs, or any
unresolved conflict. Tests additionally reject creator/source/path fields and
known video URLs in the canonical artifact.

Conflict resolution is contextual. The base preserves both legitimate sides
of an axis, while the per-video profile chooses a direction from the brief,
source evidence, and optional reference grammar. A tutorial statement's
`support_count` is diagnostic only and never affects ranking, confidence, or
weight.

The canonical artifact is versioned (`1.0.0`, compiler
`source-neutral-v1`) and tied to the aggregate input fingerprint. A stale or
corrupt checked base is rejected and rebuilt deterministically. Runtime loads
are cached by file modification time and input fingerprint.
