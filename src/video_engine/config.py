"""Engine configuration loaded from strict files and environment variables."""

from __future__ import annotations

import json
import os
import shutil
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from video_engine.errors import ConfigurationError


class EngineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    node_path: str = "node"
    npm_path: str = "npm"
    remotion_root: Path | None = None
    remotion_browser_path: Path | None = None
    remotion_timeout_seconds: float = Field(default=600, gt=0, le=3600)
    remotion_browser_timeout_seconds: int = Field(default=120, ge=7, le=300)
    remotion_max_workers: int = Field(default=1, ge=1, le=8)
    hyperframes_root: Path | None = None
    hyperframes_browser_path: Path | None = None
    hyperframes_timeout_seconds: float = Field(default=900, gt=0, le=7200)
    hyperframes_max_workers: int = Field(default=1, ge=1, le=8)
    manim_path: str = "manim"
    manim_timeout_seconds: float = Field(default=900, gt=0, le=7200)
    blender_path: str = "blender"
    blender_timeout_seconds: float = Field(default=1800, gt=0, le=14_400)
    cache_dir: Path = Field(default_factory=lambda: Path(".video-engine/cache"))
    temp_dir: Path | None = None
    max_workers: int = Field(default=max(1, min(8, os.cpu_count() or 1)), ge=1, le=64)
    render_section_duration_seconds: int = Field(default=60, ge=1, le=3600)
    max_render_inputs: int = Field(default=64, ge=2, le=1024)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    keep_temporary_files: bool = False
    allow_backend_overrides: bool = False

    @classmethod
    def from_file(cls, path: Path) -> EngineConfig:
        try:
            if path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix.lower() in {".toml", ".tml"}:
                payload = tomllib.loads(path.read_text(encoding="utf-8"))
                payload = payload.get("video_engine", payload)
            else:
                raise ConfigurationError(
                    "configuration files must be JSON or TOML",
                    context={"path": str(path)},
                )
        except (OSError, ValueError, TypeError) as exc:
            raise ConfigurationError(
                "failed to load configuration",
                context={"path": str(path), "detail": str(exc)},
            ) from exc
        return cls.model_validate(payload)

    @classmethod
    def from_environment(cls, base: EngineConfig | None = None) -> EngineConfig:
        values: dict[str, Any] = (base or cls()).model_dump()
        mappings: dict[str, tuple[str, type[Any]]] = {
            "VIDEO_ENGINE_FFMPEG": ("ffmpeg_path", str),
            "VIDEO_ENGINE_FFPROBE": ("ffprobe_path", str),
            "VIDEO_ENGINE_NODE": ("node_path", str),
            "VIDEO_ENGINE_NPM": ("npm_path", str),
            "VIDEO_ENGINE_CACHE_DIR": ("cache_dir", Path),
            "VIDEO_ENGINE_TEMP_DIR": ("temp_dir", Path),
            "VIDEO_ENGINE_REMOTION_ROOT": ("remotion_root", Path),
            "VIDEO_ENGINE_REMOTION_BROWSER": ("remotion_browser_path", Path),
            "VIDEO_ENGINE_REMOTION_TIMEOUT": ("remotion_timeout_seconds", float),
            "VIDEO_ENGINE_REMOTION_BROWSER_TIMEOUT": (
                "remotion_browser_timeout_seconds",
                int,
            ),
            "VIDEO_ENGINE_REMOTION_MAX_WORKERS": ("remotion_max_workers", int),
            "VIDEO_ENGINE_HYPERFRAMES_ROOT": ("hyperframes_root", Path),
            "VIDEO_ENGINE_HYPERFRAMES_BROWSER": ("hyperframes_browser_path", Path),
            "VIDEO_ENGINE_HYPERFRAMES_TIMEOUT": ("hyperframes_timeout_seconds", float),
            "VIDEO_ENGINE_HYPERFRAMES_MAX_WORKERS": ("hyperframes_max_workers", int),
            "VIDEO_ENGINE_MANIM": ("manim_path", str),
            "VIDEO_ENGINE_MANIM_TIMEOUT": ("manim_timeout_seconds", float),
            "VIDEO_ENGINE_BLENDER": ("blender_path", str),
            "VIDEO_ENGINE_BLENDER_TIMEOUT": ("blender_timeout_seconds", float),
            "VIDEO_ENGINE_MAX_WORKERS": ("max_workers", int),
            "VIDEO_ENGINE_RENDER_SECTION_SECONDS": (
                "render_section_duration_seconds",
                int,
            ),
            "VIDEO_ENGINE_MAX_RENDER_INPUTS": ("max_render_inputs", int),
            "VIDEO_ENGINE_LOG_LEVEL": ("log_level", str),
        }
        for variable, (field, converter) in mappings.items():
            if variable in os.environ:
                values[field] = converter(os.environ[variable])
        if "VIDEO_ENGINE_KEEP_TEMP" in os.environ:
            values["keep_temporary_files"] = os.environ["VIDEO_ENGINE_KEEP_TEMP"].lower() in {
                "1",
                "true",
                "yes",
            }
        if "VIDEO_ENGINE_ALLOW_BACKEND_OVERRIDES" in os.environ:
            values["allow_backend_overrides"] = os.environ[
                "VIDEO_ENGINE_ALLOW_BACKEND_OVERRIDES"
            ].lower() in {"1", "true", "yes"}
        return cls.model_validate(values)

    def materialize(self, project_root: Path) -> EngineConfig:
        values = self.model_dump()
        cache_dir = Path(values["cache_dir"])
        if not cache_dir.is_absolute():
            values["cache_dir"] = project_root / cache_dir
        temp_dir = values.get("temp_dir")
        if temp_dir is not None and not Path(temp_dir).is_absolute():
            values["temp_dir"] = project_root / Path(temp_dir)
        browser_path = values.get("remotion_browser_path")
        if browser_path is not None and not Path(browser_path).is_absolute():
            values["remotion_browser_path"] = project_root / Path(browser_path)
        remotion_root = values.get("remotion_root")
        if remotion_root is not None and not Path(remotion_root).is_absolute():
            values["remotion_root"] = project_root / Path(remotion_root)
        hyperframes_root = values.get("hyperframes_root")
        if hyperframes_root is not None and not Path(hyperframes_root).is_absolute():
            values["hyperframes_root"] = project_root / Path(hyperframes_root)
        hyperframes_browser = values.get("hyperframes_browser_path")
        if hyperframes_browser is not None and not Path(hyperframes_browser).is_absolute():
            values["hyperframes_browser_path"] = project_root / Path(hyperframes_browser)
        if values["manim_path"] == "manim":
            bundled_manim = (
                project_root
                / "tools"
                / "video-use"
                / "vendor"
                / "manim-video"
                / ".venv"
                / "bin"
                / "manim"
            )
            if bundled_manim.is_file() and os.access(bundled_manim, os.X_OK):
                values["manim_path"] = str(bundled_manim.resolve())
            elif shutil.which("manim") is None:
                values["manim_path"] = "manim"
        for field in ("manim_path", "blender_path"):
            executable = Path(str(values[field]))
            if not executable.is_absolute() and executable.parent != Path("."):
                values[field] = str((project_root / executable).resolve())
        return EngineConfig.model_validate(values)
