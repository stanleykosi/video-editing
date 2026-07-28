"""Versioned graphics component registry with strict props and source identity."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from video_engine.core.schema import JsonValue
from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import (
    BlenderSceneProps,
    CallToActionProps,
    ComparisonProps,
    CountdownProps,
    DiagramOverlayProps,
    EmphasisTextProps,
    GraphicBoundsPolicy,
    GraphicRenderer,
    HyperFramesCompositionProps,
    KineticCaptionProps,
    LogoRevealProps,
    LowerThirdProps,
    ManimSceneProps,
    MediaFrameProps,
    PictureInPictureProps,
    ProductFeatureProps,
    ProgressAccentProps,
    QuoteCardProps,
    SplitScreenProps,
    StatCardProps,
    TextCardProps,
)


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    id: str
    version: str
    props_model: type[BaseModel]
    source_digest: str
    renderer: GraphicRenderer = GraphicRenderer.REMOTION
    bounds_policy: GraphicBoundsPolicy = GraphicBoundsPolicy.SAFE_AREA


class GraphicsRegistry:
    def __init__(self) -> None:
        self._components: dict[tuple[str, str], ComponentDefinition] = {}

    def register(self, definition: ComponentDefinition, *, replace: bool = False) -> None:
        key = (definition.id, definition.version)
        if key in self._components and not replace:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "graphics component is already registered",
                context={"component_id": definition.id},
            )
        self._components[key] = definition

    def get(self, component_id: str, version: str) -> ComponentDefinition:
        definition = self._components.get((component_id, version))
        if definition is None:
            versions = sorted(
                component_version
                for registered_id, component_version in self._components
                if registered_id == component_id
            )
            if versions:
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "graphics component version is unavailable",
                    context={
                        "component_id": component_id,
                        "requested": version,
                        "available": versions,
                    },
                )
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "graphics component is not registered",
                context={"component_id": component_id, "available": list(self.ids)},
            )
        return definition

    def validate_props(
        self,
        component_id: str,
        version: str,
        props: dict[str, JsonValue],
    ) -> tuple[ComponentDefinition, dict[str, JsonValue]]:
        definition = self.get(component_id, version)
        try:
            parsed = definition.props_model.model_validate(props)
        except ValueError as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "graphics component props are invalid",
                context={
                    "component_id": component_id,
                    "version": version,
                    "detail": str(exc),
                },
            ) from exc
        return definition, parsed.model_dump(mode="json")

    @staticmethod
    def validate_asset_references(
        component_id: str,
        props: dict[str, JsonValue],
        declared_asset_ids: set[str],
    ) -> None:
        required: set[str] = set()

        def visit(value: JsonValue, key: str = "") -> None:
            if key.endswith("asset_id") and isinstance(value, str):
                required.add(value)
            elif key == "asset_bindings" and isinstance(value, dict):
                required.update(child for child in value.values() if isinstance(child, str))
            elif isinstance(value, dict):
                for child_key, child in value.items():
                    visit(child, child_key)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(props)
        missing = required - declared_asset_ids
        if missing:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "graphics props reference undeclared assets",
                context={"component_id": component_id, "asset_ids": sorted(missing)},
            )

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted({component_id for component_id, _ in self._components}))


def _source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".mjs", ".css"}
    )
    if not files:
        raise EngineError(
            ErrorCode.CONFIGURATION,
            "Remotion component source files are missing",
            context={"root": str(root)},
        )
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def builtin_graphics_registry() -> GraphicsRegistry:
    source_root = Path(__file__).resolve().parent / "remotion"
    digest = _source_digest(source_root)
    models: dict[str, type[BaseModel]] = {
        "title_card": TextCardProps,
        "hook_card": TextCardProps,
        "chapter_card": TextCardProps,
        "lower_third": LowerThirdProps,
        "quote_card": QuoteCardProps,
        "stat_card": StatCardProps,
        "number_card": StatCardProps,
        "countdown": CountdownProps,
        "comparison": ComparisonProps,
        "product_feature": ProductFeatureProps,
        "screenshot_frame": MediaFrameProps,
        "device_mockup": MediaFrameProps,
        "picture_in_picture": PictureInPictureProps,
        "split_screen": SplitScreenProps,
        "logo_reveal": LogoRevealProps,
        "call_to_action": CallToActionProps,
        "end_card": CallToActionProps,
        "progress_accent": ProgressAccentProps,
        "diagram_overlay": DiagramOverlayProps,
        "emphasis_text": EmphasisTextProps,
        "kinetic_caption": KineticCaptionProps,
    }
    registry = GraphicsRegistry()
    full_frame = {
        "title_card",
        "hook_card",
        "chapter_card",
        "quote_card",
        "stat_card",
        "number_card",
        "countdown",
        "comparison",
        "product_feature",
        "screenshot_frame",
        "device_mockup",
        "split_screen",
        "logo_reveal",
        "call_to_action",
        "end_card",
    }
    for component_id, props_model in models.items():
        bounds_policy = (
            GraphicBoundsPolicy.EDGE_ACCENT
            if component_id == "progress_accent"
            else (
                GraphicBoundsPolicy.FULL_FRAME
                if component_id in full_frame
                else GraphicBoundsPolicy.SAFE_AREA
            )
        )
        registry.register(
            ComponentDefinition(
                id=component_id,
                version="1.0.0",
                props_model=props_model,
                source_digest=digest,
                bounds_policy=bounds_policy,
            )
        )
    external_digest = hashlib.sha256(
        (Path(__file__).resolve().parent / "external.py").read_bytes()
    ).hexdigest()
    for component_id, props_model, renderer in (
        ("hyperframes_composition", HyperFramesCompositionProps, GraphicRenderer.HYPERFRAMES),
        ("manim_scene", ManimSceneProps, GraphicRenderer.MANIM),
        ("blender_scene", BlenderSceneProps, GraphicRenderer.BLENDER),
    ):
        registry.register(
            ComponentDefinition(
                id=component_id,
                version="1.0.0",
                props_model=props_model,
                source_digest=external_digest,
                renderer=renderer,
                bounds_policy=GraphicBoundsPolicy.FULL_FRAME,
            )
        )
    return registry
