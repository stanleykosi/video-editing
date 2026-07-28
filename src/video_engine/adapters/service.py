"""Stable facade for legacy and interchange imports."""

from __future__ import annotations

from pathlib import Path

from video_engine.config import EngineConfig
from video_engine.core.time import FrameRate

from .cmx import CMXAdapterService
from .faceless import FacelessAdapterService
from .fcpxml import FCPXMLAdapterService
from .legacy import LegacyAdapterService
from .models import MigrationResult
from .otio import OTIOAdapterService


class AdapterService:
    def __init__(self, project_root: Path, config: EngineConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)

    def import_legacy_edl(self, path: Path, *, name: str | None = None) -> MigrationResult:
        return LegacyAdapterService(self.project_root, self.config).import_existing_edl(
            path, name=name
        )

    def import_faceless(
        self,
        path: Path,
        *,
        name: str | None = None,
        voiceover: Path | None = None,
        captions: Path | None = None,
        rich_captions: Path | None = None,
    ) -> MigrationResult:
        return FacelessAdapterService(self.project_root, self.config).import_project(
            path,
            name=name,
            voiceover=voiceover,
            captions=captions,
            rich_captions=rich_captions,
        )

    def import_cmx(
        self,
        path: Path,
        *,
        frame_rate: FrameRate | None = None,
        name: str | None = None,
        media_paths: dict[str, Path] | None = None,
        source_timecodes: dict[str, str] | None = None,
    ) -> MigrationResult:
        return CMXAdapterService(self.project_root, self.config).import_file(
            path,
            frame_rate=frame_rate,
            name=name,
            media_paths=media_paths,
            source_timecodes=source_timecodes,
        )

    def import_fcpxml(
        self,
        path: Path,
        *,
        name: str | None = None,
        media_paths: dict[str, Path] | None = None,
    ) -> MigrationResult:
        return FCPXMLAdapterService(self.project_root, self.config).import_file(
            path,
            name=name,
            media_paths=media_paths,
        )

    def import_otio(
        self,
        path: Path,
        *,
        frame_rate: FrameRate | None = None,
        name: str | None = None,
        width: int = 1920,
        height: int = 1080,
    ) -> MigrationResult:
        return OTIOAdapterService(self.project_root, self.config).import_file(
            path,
            frame_rate=frame_rate,
            name=name,
            width=width,
            height=height,
        )
