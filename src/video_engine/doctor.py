"""Environment doctor for required and optional engine tooling."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from video_engine.config import EngineConfig
from video_engine.errors import EngineError
from video_engine.process import CommandRunner


class CheckStatus(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class DoctorCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: CheckStatus
    required: bool
    version: str | None = None
    detail: str = ""
    action: str | None = None


class DoctorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: list[DoctorCheck]

    @property
    def healthy(self) -> bool:
        return not any(check.required and check.status is CheckStatus.FAIL for check in self.checks)

    def summary(self) -> dict[str, int | bool]:
        return {
            "healthy": self.healthy,
            "passed": sum(check.status is CheckStatus.PASS for check in self.checks),
            "warnings": sum(check.status is CheckStatus.WARNING for check in self.checks),
            "failed": sum(check.status is CheckStatus.FAIL for check in self.checks),
        }


def _executable_check(
    name: str,
    executable: str,
    arguments: list[str],
    *,
    required: bool,
    runner: CommandRunner,
) -> DoctorCheck:
    resolved = shutil.which(executable)
    if resolved is None:
        return DoctorCheck(
            name=name,
            status=CheckStatus.FAIL if required else CheckStatus.WARNING,
            required=required,
            detail=f"{executable!r} was not found on PATH",
            action=f"Install {name} or configure its executable path.",
        )
    try:
        result = runner.run([resolved, *arguments], timeout=10)
    except Exception as exc:
        return DoctorCheck(
            name=name,
            status=CheckStatus.FAIL if required else CheckStatus.WARNING,
            required=required,
            detail=str(exc),
        )
    version = (result.stdout or result.stderr).splitlines()[0].strip()
    return DoctorCheck(
        name=name,
        status=CheckStatus.PASS,
        required=required,
        version=version,
        detail=resolved,
    )


def _ffmpeg_capabilities(config: EngineConfig, runner: CommandRunner) -> DoctorCheck:
    try:
        filters = runner.run([config.ffmpeg_path, "-hide_banner", "-filters"], timeout=10).stdout
        encoders = runner.run([config.ffmpeg_path, "-hide_banner", "-encoders"], timeout=10).stdout
    except Exception as exc:
        return DoctorCheck(
            name="FFmpeg capabilities",
            status=CheckStatus.FAIL,
            required=True,
            detail=str(exc),
        )
    required_filters = {
        "acompressor",
        "afftdn",
        "agate",
        "alimiter",
        "subtitles",
        "zscale",
        "tonemap",
        "loudnorm",
        "overlay",
        "rubberband",
        "xfade",
        "acrossfade",
        "amix",
        "aresample",
        "deesser",
        "equalizer",
        "pan",
        "sidechaincompress",
    }
    missing = sorted(name for name in required_filters if name not in filters)
    if "libx264" not in encoders:
        missing.append("encoder:libx264")
    return DoctorCheck(
        name="FFmpeg capabilities",
        status=CheckStatus.FAIL if missing else CheckStatus.PASS,
        required=True,
        detail=(
            "missing: " + ", ".join(missing)
            if missing
            else "required editing filters and H.264 encoder found"
        ),
    )


def _remotion_root(config: EngineConfig, project_root: Path) -> Path | None:
    candidates = (
        [config.remotion_root]
        if config.remotion_root is not None
        else [project_root, Path(__file__).resolve().parents[2]]
    )
    return next(
        (
            candidate.resolve()
            for candidate in candidates
            if candidate is not None
            and (candidate / "package.json").is_file()
            and (candidate / "node_modules").is_dir()
        ),
        None,
    )


def _remotion_check(config: EngineConfig, project_root: Path, runner: CommandRunner) -> DoctorCheck:
    root = _remotion_root(config, project_root)
    if root is None:
        return DoctorCheck(
            name="Remotion",
            status=CheckStatus.FAIL,
            required=True,
            detail="the Remotion package root could not be discovered",
            action="Run npm ci at the engine root or set VIDEO_ENGINE_REMOTION_ROOT.",
        )
    package = root / "node_modules" / "remotion" / "package.json"
    if not package.exists():
        return DoctorCheck(
            name="Remotion",
            status=CheckStatus.FAIL,
            required=True,
            detail="node_modules/remotion is not installed",
            action="Run npm ci from the repository root.",
        )
    try:
        version = str(json.loads(package.read_text(encoding="utf-8"))["version"])
        runner.run(
            [str(root / "node_modules" / ".bin" / "remotion"), "versions"],
            cwd=root,
            timeout=15,
        )
    except Exception as exc:
        return DoctorCheck(
            name="Remotion",
            status=CheckStatus.FAIL,
            required=True,
            detail=str(exc),
        )
    return DoctorCheck(
        name="Remotion",
        status=CheckStatus.PASS,
        required=True,
        version=version,
        detail=str(package),
    )


def _remotion_browser_check(config: EngineConfig, project_root: Path) -> DoctorCheck:
    candidates: list[Path] = []
    if config.remotion_browser_path is not None:
        candidates.append(config.remotion_browser_path)
    root = _remotion_root(config, project_root)
    search_roots = [Path.home() / ".cache" / "ms-playwright"]
    if root is not None:
        search_roots.append(root / "node_modules" / ".remotion")
    for search_root in search_roots:
        if not search_root.is_dir():
            continue
        candidates.extend(search_root.glob("**/chrome-headless-shell"))
        candidates.extend(search_root.glob("**/headless_shell"))
    browser = next(
        (
            candidate.resolve()
            for candidate in candidates
            if candidate.is_file() and candidate.stat().st_mode & 0o111
        ),
        None,
    )
    if browser is None:
        return DoctorCheck(
            name="Remotion browser",
            status=CheckStatus.FAIL,
            required=True,
            detail="Chrome headless-shell was not found",
            action="Install a Remotion browser or set VIDEO_ENGINE_REMOTION_BROWSER.",
        )
    return DoctorCheck(
        name="Remotion browser",
        status=CheckStatus.PASS,
        required=True,
        detail=str(browser),
    )


def _hyperframes_check(
    config: EngineConfig, project_root: Path, runner: CommandRunner
) -> DoctorCheck:
    root = (config.hyperframes_root or project_root).resolve()
    package = root / "node_modules" / "@hyperframes" / "producer" / "package.json"
    if not package.is_file():
        return DoctorCheck(
            name="HyperFrames producer",
            status=CheckStatus.FAIL,
            required=True,
            detail="@hyperframes/producer is not installed",
            action="Run npm ci from the engine root.",
        )
    try:
        version = str(json.loads(package.read_text(encoding="utf-8"))["version"])
        runner.run(
            [
                config.node_path,
                "--input-type=module",
                "-e",
                "import('@hyperframes/producer').then(m=>{if(!m.executeRenderJob)process.exit(2)})",
            ],
            cwd=root,
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError, EngineError) as exc:
        return DoctorCheck(
            name="HyperFrames producer",
            status=CheckStatus.FAIL,
            required=True,
            detail=str(exc),
            action="Reinstall the exact Node lock with npm ci --ignore-scripts.",
        )
    return DoctorCheck(
        name="HyperFrames producer",
        status=CheckStatus.PASS,
        required=True,
        version=version,
        detail=str(package),
    )


def _hyperframes_browser_check(config: EngineConfig, project_root: Path) -> DoctorCheck:
    candidates: list[Path] = []
    for configured in (config.hyperframes_browser_path, config.remotion_browser_path):
        if configured is not None:
            candidates.append(configured)
    roots = (
        Path.home() / ".cache" / "ms-playwright",
        project_root / "node_modules" / ".remotion",
        Path.home() / ".cache" / "puppeteer",
        Path.home() / ".cache" / "hyperframes",
    )
    for root in roots:
        if root.is_dir():
            candidates.extend(root.glob("**/chrome-headless-shell"))
            candidates.extend(root.glob("**/headless_shell"))
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return DoctorCheck(
                name="HyperFrames browser",
                status=CheckStatus.PASS,
                required=True,
                detail=str(resolved),
            )
    return DoctorCheck(
        name="HyperFrames browser",
        status=CheckStatus.FAIL,
        required=True,
        detail="no executable Chrome headless-shell was found",
        action=("Set VIDEO_ENGINE_HYPERFRAMES_BROWSER or install the exact Remotion browser."),
    )


def _fonts_check(runner: CommandRunner) -> DoctorCheck:
    try:
        result = runner.run(["fc-list", ":", "family"], timeout=10)
        families = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except Exception as exc:
        return DoctorCheck(
            name="Fonts",
            status=CheckStatus.FAIL,
            required=True,
            detail=str(exc),
        )
    return DoctorCheck(
        name="Fonts",
        status=CheckStatus.PASS if families else CheckStatus.FAIL,
        required=True,
        detail=f"{len(families)} font family records discovered",
    )


def run_doctor(
    config: EngineConfig,
    project_root: Path,
    *,
    require_extended_graphics: bool = False,
) -> DoctorReport:
    runner = CommandRunner(default_timeout=15)
    python_ok = sys.version_info[:2] == (3, 11)
    checks = [
        DoctorCheck(
            name="Python",
            status=CheckStatus.PASS if python_ok else CheckStatus.FAIL,
            required=True,
            version=platform.python_version(),
            detail=sys.executable,
            action=None if python_ok else "Use CPython 3.11 as declared by the project.",
        ),
        _executable_check("FFmpeg", config.ffmpeg_path, ["-version"], required=True, runner=runner),
        _executable_check(
            "FFprobe", config.ffprobe_path, ["-version"], required=True, runner=runner
        ),
        _ffmpeg_capabilities(config, runner),
        _executable_check("Node.js", config.node_path, ["--version"], required=True, runner=runner),
        _executable_check("npm", config.npm_path, ["--version"], required=True, runner=runner),
        _remotion_check(config, project_root, runner),
        _remotion_browser_check(config, project_root),
        _hyperframes_check(config, project_root, runner),
        _hyperframes_browser_check(config, project_root),
        _fonts_check(runner),
        _executable_check("Tesseract", "tesseract", ["--version"], required=False, runner=runner),
        _executable_check(
            "Blender",
            config.blender_path,
            ["--version"],
            required=require_extended_graphics,
            runner=runner,
        ),
        _executable_check(
            "Manim",
            config.manim_path,
            ["--version"],
            required=require_extended_graphics,
            runner=runner,
        ),
        _executable_check(
            "LaTeX",
            "latex",
            ["--version"],
            required=require_extended_graphics,
            runner=runner,
        ),
    ]
    checks.append(
        DoctorCheck(
            name="Pydantic",
            status=(
                CheckStatus.PASS
                if importlib.util.find_spec("pydantic") is not None
                else CheckStatus.FAIL
            ),
            required=True,
            detail="strict schema runtime",
        )
    )
    return DoctorReport(checks=checks)
