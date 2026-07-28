"""Canonical HyperFrames HTML composition backend."""

from __future__ import annotations

import json
import os
from functools import cached_property
from pathlib import Path
from threading import BoundedSemaphore

from video_engine.config import EngineConfig
from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import GraphicRenderer, HyperFramesCompositionProps
from video_engine.process import CommandRunner
from video_engine.render.backends.base import BackendExecution
from video_engine.render.backends.external_graphics import ExternalMotionGraphicBackend
from video_engine.render.cache import sha256_file
from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import RenderNode


class HyperFramesBackend(ExternalMotionGraphicBackend):
    name = "hyperframes"
    version = "1.0.0"
    renderer = GraphicRenderer.HYPERFRAMES

    def __init__(
        self,
        config: EngineConfig,
        project_root: Path,
        runner: CommandRunner | None = None,
    ) -> None:
        super().__init__(config, project_root, runner)
        self.bridge_root = Path(__file__).resolve().parents[2] / "graphics" / "hyperframes"
        self.runner_path = self.bridge_root / "runner.mjs"
        self._render_slots = BoundedSemaphore(config.hyperframes_max_workers)

    @cached_property
    def tool_root(self) -> Path:
        return self._tool_root()

    def _tool_root(self) -> Path:
        candidates: tuple[Path, ...]
        if self.config.hyperframes_root is not None:
            candidates = (self.config.hyperframes_root.resolve(),)
        else:
            candidates = tuple(self.bridge_root.parents)
        for candidate in candidates:
            package = candidate / "node_modules" / "@hyperframes" / "producer" / "package.json"
            if (candidate / "package.json").is_file() and package.is_file():
                return candidate
        raise EngineError(
            ErrorCode.DEPENDENCY_MISSING,
            "HyperFrames producer package root could not be discovered",
            context={"bridge_root": str(self.bridge_root)},
        )

    @cached_property
    def browser_path(self) -> Path:
        candidates: tuple[Path, ...]
        if self.config.hyperframes_browser_path is not None:
            candidates = (self.config.hyperframes_browser_path.resolve(),)
        elif self.config.remotion_browser_path is not None:
            candidates = (self.config.remotion_browser_path.resolve(),)
        else:
            roots = (
                Path.home() / ".cache" / "ms-playwright",
                self.tool_root / "node_modules" / ".remotion",
                Path.home() / ".cache" / "puppeteer",
                Path.home() / ".cache" / "hyperframes",
            )
            discovered: list[Path] = []
            for root in roots:
                if root.is_dir():
                    discovered.extend(root.glob("**/chrome-headless-shell"))
                    discovered.extend(root.glob("**/headless_shell"))
            candidates = tuple(sorted(discovered, reverse=True))
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
        raise EngineError(
            ErrorCode.DEPENDENCY_MISSING,
            "HyperFrames requires a configured Chrome headless-shell",
            context={"environment": "VIDEO_ENGINE_HYPERFRAMES_BROWSER"},
        )

    @cached_property
    def tool_fingerprint(self) -> str:
        if not self.runner_path.is_file():
            raise EngineError(
                ErrorCode.DEPENDENCY_MISSING,
                "HyperFrames bridge runner is missing",
                context={"path": str(self.runner_path)},
            )
        package_path = (
            self.tool_root / "node_modules" / "@hyperframes" / "producer" / "package.json"
        )
        try:
            package_version = json.loads(package_path.read_text(encoding="utf-8"))["version"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise EngineError(
                ErrorCode.DEPENDENCY_MISSING,
                "HyperFrames package metadata is unavailable",
                context={"path": str(package_path)},
            ) from exc
        node_version = self.runner.run([self.config.node_path, "--version"]).stdout.strip()
        lockfile = self.tool_root / "package-lock.json"
        return (
            f"node={node_version};@hyperframes/producer={package_version};"
            f"lock={sha256_file(lockfile)};runner={sha256_file(self.runner_path)};"
            f"browser={sha256_file(self.browser_path)}"
        )

    def execute(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        output_path: Path,
        work_dir: Path,
    ) -> BackendExecution:
        graphic = self._node(node)
        if inputs:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "HyperFrames requires a zero-input motion graphic node",
            )
        props = HyperFramesCompositionProps.model_validate(graphic.props)
        project_dir = work_dir / "project"
        self._stage_project(graphic, props, project_dir, source_name="index.html")
        request = {
            "entryFile": "index.html",
            "browserPath": str(self.browser_path),
            "frameRate": {
                "num": graphic.frame_rate.numerator,
                "den": graphic.frame_rate.denominator,
            },
            "quality": props.quality,
            "strictness": props.strictness,
            "variables": props.variables,
            "workers": props.workers,
        }
        (work_dir / "request.json").write_text(
            json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with self._render_slots:
            self.runner.run(
                [self.config.node_path, self.runner_path, "--job-root", work_dir],
                cwd=self.tool_root,
                env={
                    "HYPERFRAMES_NO_UPDATE_CHECK": "1",
                    "HYPERFRAMES_NO_TELEMETRY": "1",
                    "PRODUCER_HEADLESS_SHELL_PATH": str(self.browser_path),
                },
                timeout=self.config.hyperframes_timeout_seconds,
            )
        full_output = work_dir / "full.mov"
        if not full_output.is_file():
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "HyperFrames did not produce its declared output",
                context={"path": str(full_output)},
            )
        self._conform_range(graphic, full_output, output_path, work_dir)
        result_path = work_dir / "hyperframes-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        lint = result.get("lint", {})
        return self._result(
            graphic,
            output_path,
            {
                "browser_sha256": sha256_file(self.browser_path),
                "lint_errors": int(lint.get("errorCount", 0)),
                "lint_warnings": int(lint.get("warningCount", 0)),
            },
        )
