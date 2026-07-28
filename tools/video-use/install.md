---
name: video-use-install
description: Install the canonical video editing engine and register its video-use workflow skill.
---

# video-use install

Use this file for first-time setup or reconnect. Daily editing instructions live
in `SKILL.md`. The repository root owns the `video_engine` package, exact Python
and Node locks, Remotion bridge, tests, and `video-engine` command. This
`tools/video-use/` directory is the workflow skill and compatibility-helper layer.

## Install contract

- Use a stable checkout such as `~/Developer/video-editing`.
- Install from the repository root, never from `tools/video-use/`.
- FFmpeg, FFprobe, fontconfig, Python 3.11, Node 22.18+, npm, the exact Remotion
  packages, and the pinned Remotion browser are required for the complete engine.
- Blender, Manim, LaTeX, HyperFrames, yt-dlp, and hosted transcription/voice APIs
  are optional integrations. Missing optional tools must not block baseline editing.
- Do not use `latest`, unversioned `npx`, or scaffold a second Remotion project.
- Verify with the engine doctor and one real canonical project command.

## 1. Clone the canonical repository

```bash
test -d ~/Developer/video-editing || \
  git clone https://github.com/stanleykosi/video-editing.git ~/Developer/video-editing
cd ~/Developer/video-editing
git pull --ff-only
```

## 2. Install system tools

FFmpeg must include the filters checked by `video-engine doctor`, including
Rubber Band support for continuous variable-speed audio.

```bash
# Debian / Ubuntu
sudo apt-get update
sudo apt-get install --yes ffmpeg fontconfig

# macOS
brew install ffmpeg fontconfig
```

Install Node 22.18 or a compatible newer release through the machine's normal
version manager. Do not install Remotion globally.

## 3. Install exact Python and Node environments

```bash
cd ~/Developer/video-editing
uv sync --frozen --extra legacy --extra interchange --group dev
npm ci --ignore-scripts
npm audit --audit-level=high
npm run remotion:browser
```

`uv.lock` and `package-lock.json` are authoritative. The `interchange` extra
enables the optional OpenTimelineIO adapter; `legacy` keeps preparation helpers
available while production rendering remains canonical.
There is intentionally no nested `tools/video-use` package or lockfile.

## 4. Register the workflow skill

Symlink `tools/video-use`, not the repository root. The engine stays installed
from the root while `SKILL.md` and compatibility helpers remain adjacent.

```bash
# Claude Code
mkdir -p ~/.claude/skills
ln -sfn ~/Developer/video-editing/tools/video-use ~/.claude/skills/video-use

# Codex
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -sfn ~/Developer/video-editing/tools/video-use \
  "${CODEX_HOME:-$HOME/.codex}/skills/video-use"
```

For another agent, link the same `tools/video-use` directory into its skills
directory or point its configuration at
`~/Developer/video-editing/tools/video-use/SKILL.md`.

## 5. Optional hosted API credentials

The engine does not require hosted transcription or voice synthesis. Workflows
that do may read the repository-root `.env`:

```text
DEEPGRAM_API_KEY=
ELEVENLABS_API_KEY=
```

Deepgram is preferred for current transcription and from-scratch voiceover.
`ELEVENLABS_API_KEY` is needed only by the older Scribe compatibility helper.
Never print, commit, or copy secrets into a project manifest.

## 6. Verify the installed engine

```bash
cd ~/Developer/video-editing
video-engine doctor --json
video-engine init /tmp/video-engine-install-check --name "Install Check" --json
video-engine project validate /tmp/video-engine-install-check/project.json --json
npm run graphics:typecheck
npm run remotion:bundle
```

`doctor` must pass every required check. Optional-tool warnings are acceptable
when those backends are not requested. The init/validate commands prove the
console script, strict project schema, storage, and JSON output path work.

## 7. Hand off

Tell the user where the repository and skill link live. They can then enter a
footage/project directory, start their agent, and request an edit. Project media,
renders, caches, reports, and manifests belong in that project directory, not in
the engine checkout.

## Updating

```bash
cd ~/Developer/video-editing
git pull --ff-only
uv sync --frozen --extra legacy --extra interchange --group dev
npm ci --ignore-scripts
video-engine doctor --json
```

Do not run transcription during installation verification; hosted calls may cost
money. Do not install local Whisper model checkpoints unless the user explicitly
requests that fallback.
