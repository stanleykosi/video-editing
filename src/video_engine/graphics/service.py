"""Public helpers that prepare external graphics as canonical timeline data."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from video_engine.core.schema import (
    GeneratorAssetReference,
    GeneratorClip,
    JsonValue,
    MediaReference,
)
from video_engine.core.time import TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import (
    BlenderSceneProps,
    HyperFramesCompositionProps,
    ManimSceneProps,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PreparedGraphic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    clip: GeneratorClip
    media_references: tuple[MediaReference, ...]


class GraphicsService:
    """Build strict clips and content-addressed references without invoking tools."""

    def prepare_hyperframes(
        self,
        *,
        clip_id: str,
        timeline_range: TimeRange,
        entry_path: Path,
        asset_bindings: dict[str, Path] | None = None,
        variables: dict[str, JsonValue] | None = None,
        quality: Literal["draft", "standard", "high"] = "high",
        strictness: Literal["strict", "best-effort"] = "strict",
        workers: int = 1,
        transparent: bool = True,
    ) -> PreparedGraphic:
        props = HyperFramesCompositionProps(
            source_asset_id="source",
            asset_bindings={},
            variables=variables or {},
            quality=quality,
            strictness=strictness,
            workers=workers,
        )
        return self._prepare(
            clip_id=clip_id,
            timeline_range=timeline_range,
            source_path=entry_path,
            asset_bindings=asset_bindings or {},
            generator_id="hyperframes_composition",
            props=props,
            transparent=transparent,
        )

    def prepare_manim(
        self,
        *,
        clip_id: str,
        timeline_range: TimeRange,
        script_path: Path,
        scene_name: str,
        asset_bindings: dict[str, Path] | None = None,
        renderer: Literal["cairo", "opengl"] = "cairo",
        seed: int = 0,
        transparent: bool = True,
    ) -> PreparedGraphic:
        props = ManimSceneProps(
            source_asset_id="source",
            asset_bindings={},
            scene_name=scene_name,
            renderer=renderer,
            seed=seed,
        )
        return self._prepare(
            clip_id=clip_id,
            timeline_range=timeline_range,
            source_path=script_path,
            asset_bindings=asset_bindings or {},
            generator_id="manim_scene",
            props=props,
            transparent=transparent,
        )

    def prepare_blender(
        self,
        *,
        clip_id: str,
        timeline_range: TimeRange,
        blend_path: Path,
        asset_bindings: dict[str, Path] | None = None,
        scene_name: str | None = None,
        camera_name: str | None = None,
        render_engine: Literal[
            "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH", "CYCLES"
        ] = "BLENDER_EEVEE_NEXT",
        source_start_frame: int = 1,
        samples: int = 64,
        transparent: bool = True,
    ) -> PreparedGraphic:
        props = BlenderSceneProps(
            source_asset_id="source",
            asset_bindings={},
            scene_name=scene_name,
            camera_name=camera_name,
            render_engine=render_engine,
            source_start_frame=source_start_frame,
            samples=samples,
        )
        return self._prepare(
            clip_id=clip_id,
            timeline_range=timeline_range,
            source_path=blend_path,
            asset_bindings=asset_bindings or {},
            generator_id="blender_scene",
            props=props,
            transparent=transparent,
        )

    @staticmethod
    def _prepare(
        *,
        clip_id: str,
        timeline_range: TimeRange,
        source_path: Path,
        asset_bindings: dict[str, Path],
        generator_id: str,
        props: HyperFramesCompositionProps | ManimSceneProps | BlenderSceneProps,
        transparent: bool,
    ) -> PreparedGraphic:
        source = GraphicsService._media_reference(source_path)
        references = {source.id: source}
        clip_assets = [GeneratorAssetReference(id="source", media_reference_id=source.id)]
        normalized_bindings: dict[str, str] = {}
        for index, (relative_path, path) in enumerate(sorted(asset_bindings.items())):
            asset_id = f"asset-{index:03d}"
            reference = GraphicsService._media_reference(path)
            references[reference.id] = reference
            clip_assets.append(
                GeneratorAssetReference(id=asset_id, media_reference_id=reference.id)
            )
            normalized_bindings[relative_path] = asset_id
        parsed_props = props.model_copy(update={"asset_bindings": normalized_bindings})
        parsed_props = type(props).model_validate(parsed_props.model_dump(mode="json"))
        return PreparedGraphic(
            clip=GeneratorClip(
                id=clip_id,
                name=generator_id.replace("_", " ").title(),
                timeline_range=timeline_range,
                generator_id=generator_id,
                generator_version="1.0.0",
                properties=parsed_props.model_dump(mode="json"),
                assets=clip_assets,
                transparent=transparent,
            ),
            media_references=tuple(references.values()),
        )

    @staticmethod
    def _media_reference(path: Path) -> MediaReference:
        source = path.resolve()
        if path.is_symlink() or not source.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "graphics source is missing or is a symbolic link",
                context={"path": str(source)},
            )
        checksum = _sha256_file(source)
        return MediaReference(
            id=f"graphics-{checksum[:24]}",
            uri=str(source),
            sha256=checksum,
        )
