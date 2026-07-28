"""High-level API for project lifecycle and engine services."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from video_engine.adapters.exporter import ExportService
from video_engine.adapters.service import AdapterService
from video_engine.captions.service import CaptionService
from video_engine.color.service import ColorService
from video_engine.config import EngineConfig
from video_engine.core.schema import (
    DeliveryProfile,
    Project,
    ProjectSettings,
    Sequence,
    Timeline,
)
from video_engine.core.time import FrameRate
from video_engine.core.validation import ValidationReport, validate_project
from video_engine.doctor import DoctorReport, run_doctor
from video_engine.errors import InvalidProjectError
from video_engine.inspection.service import InspectionService
from video_engine.media.service import MediaService
from video_engine.operations.editor import TimelineEditor
from video_engine.qc.approval import QCApprovalService
from video_engine.qc.parity import MediaParityService
from video_engine.qc.service import QCService
from video_engine.render.service import RenderService
from video_engine.storage.project_store import ProjectStore
from video_engine.visual.service import VisualService


def _stable_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


class VideoEngine:
    """Stable orchestration facade; backends remain behind subsystem APIs."""

    def __init__(
        self,
        project_root: Path | None = None,
        config: EngineConfig | None = None,
    ) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.config = EngineConfig.from_environment(config).materialize(self.project_root)

    def create_project(
        self,
        name: str,
        *,
        width: int = 1920,
        height: int = 1080,
        frame_rate: FrameRate | None = None,
        audio_sample_rate: int = 48_000,
    ) -> Project:
        project_id = f"project-{_stable_slug(name)}-{uuid.uuid4().hex[:8]}"
        sequence_id = "sequence-main"
        settings = ProjectSettings(
            width=width,
            height=height,
            frame_rate=frame_rate or FrameRate(numerator=24),
            audio_sample_rate=audio_sample_rate,
        )
        return Project(
            id=project_id,
            name=name,
            settings=settings,
            sequences=[Sequence(id=sequence_id, name="Main", timeline=Timeline())],
            active_sequence_id=sequence_id,
            delivery_profiles=[
                DeliveryProfile(
                    id="preview",
                    name="Preview",
                    width=width,
                    height=height,
                    frame_rate=settings.frame_rate,
                    crf=22,
                    preset="veryfast",
                ),
                DeliveryProfile(
                    id="final",
                    name="Final",
                    width=width,
                    height=height,
                    frame_rate=settings.frame_rate,
                    crf=18,
                    preset="medium",
                ),
            ],
        )

    def save_project(self, project: Project, path: Path | None = None) -> Path:
        return ProjectStore(path or self.project_root / "project.json").save(project)

    def load_project(self, path: Path | None = None) -> tuple[Project, list[str]]:
        return ProjectStore(path or self.project_root / "project.json").load()

    def validate_project(self, project: Project) -> ValidationReport:
        report = validate_project(project)
        if not report.valid:
            raise InvalidProjectError(
                "project invariant validation failed",
                context=report.model_dump(mode="json"),
            )
        return report

    def doctor(self) -> DoctorReport:
        return run_doctor(self.config, self.project_root)

    def media(self) -> MediaService:
        return MediaService(self.project_root, self.config)

    def adapters(self) -> AdapterService:
        return AdapterService(self.project_root, self.config)

    def exporter(self) -> ExportService:
        return ExportService(self.project_root, self.config)

    def inspection(self, project: Project) -> InspectionService:
        return InspectionService(project, self.project_root, self.config)

    def captions(self) -> CaptionService:
        return CaptionService(self.config)

    def color(self) -> ColorService:
        return ColorService(self.project_root, self.config)

    def editor(self, project: Project) -> TimelineEditor:
        return TimelineEditor(project)

    def renderer(self, project: Project) -> RenderService:
        return RenderService(project, self.project_root, self.config)

    def qc(self, project: Project) -> QCService:
        return QCService(project, self.project_root, self.config)

    def parity(self) -> MediaParityService:
        return MediaParityService(self.project_root, self.config)

    def approvals(self) -> QCApprovalService:
        return QCApprovalService()

    def visual(self) -> VisualService:
        return VisualService()
