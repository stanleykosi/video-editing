"""Strict contracts shared by the canonical graphics registry and Remotion bridge."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import JsonValue
from video_engine.core.time import FrameRate


class GraphicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GraphicBoundsPolicy(StrEnum):
    SAFE_AREA = "safe_area"
    EDGE_ACCENT = "edge_accent"
    FULL_FRAME = "full_frame"


class GraphicAsset(GraphicModel):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    source_path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: Literal["image", "video"]
    staged_name: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")


class GraphicStagedAsset(GraphicModel):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: Literal["image", "video"]
    staged_name: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")


class GraphicComponentRef(GraphicModel):
    id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class GraphicCanvas(GraphicModel):
    width: int = Field(gt=0, le=16_384)
    height: int = Field(gt=0, le=16_384)
    frame_rate: FrameRate
    duration_frames: int = Field(gt=0)


class GraphicFrameRange(GraphicModel):
    start_frame: int = Field(ge=0)
    end_frame_exclusive: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> GraphicFrameRange:
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("graphic frame range must be positive")
        return self


class GraphicRenderRequest(GraphicModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    component: GraphicComponentRef
    canvas: GraphicCanvas
    render_range: GraphicFrameRange
    props: dict[str, JsonValue]
    assets: tuple[GraphicStagedAsset, ...] = ()
    transparent: bool = True
    color_space: Literal["rec709"] = "rec709"

    @model_validator(mode="after")
    def valid_range_and_assets(self) -> GraphicRenderRequest:
        if self.render_range.end_frame_exclusive > self.canvas.duration_frames:
            raise ValueError("graphic render range exceeds composition duration")
        ids = [asset.id for asset in self.assets]
        names = [asset.staged_name for asset in self.assets]
        if len(ids) != len(set(ids)) or len(names) != len(set(names)):
            raise ValueError("graphic asset ids and staged names must be unique")
        return self


Color = str


class CommonProps(GraphicModel):
    accent_color: Color = Field(default="#F4C95D", pattern=r"^#[0-9A-Fa-f]{6}$")
    text_color: Color = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: Color = Field(default="#111111", pattern=r"^#[0-9A-Fa-f]{6}$")


class TextCardProps(CommonProps):
    title: str = Field(min_length=1, max_length=180)
    subtitle: str | None = Field(default=None, max_length=280)
    label: str | None = Field(default=None, max_length=80)
    alignment: Literal["left", "center", "right"] = "left"


class LowerThirdProps(CommonProps):
    name: str = Field(min_length=1, max_length=100)
    role: str | None = Field(default=None, max_length=140)


class QuoteCardProps(CommonProps):
    quote: str = Field(min_length=1, max_length=400)
    attribution: str | None = Field(default=None, max_length=120)


class StatCardProps(CommonProps):
    value: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=140)
    detail: str | None = Field(default=None, max_length=180)


class CountdownProps(CommonProps):
    from_number: int = Field(default=3, ge=1, le=99)
    label: str | None = Field(default=None, max_length=100)


class ComparisonSide(GraphicModel):
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=120)


class ComparisonProps(CommonProps):
    title: str | None = Field(default=None, max_length=120)
    left: ComparisonSide
    right: ComparisonSide


class ProductFeatureProps(CommonProps):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=260)
    bullets: tuple[str, ...] = Field(default=(), max_length=5)
    asset_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+$")


class MediaFrameProps(CommonProps):
    asset_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    title: str | None = Field(default=None, max_length=120)
    caption: str | None = Field(default=None, max_length=180)


class PictureInPictureProps(CommonProps):
    asset_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    corner: Literal["top_left", "top_right", "bottom_left", "bottom_right"] = "bottom_right"
    label: str | None = Field(default=None, max_length=80)


class SplitScreenProps(CommonProps):
    left_asset_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    right_asset_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    divider: Literal["vertical", "horizontal"] = "vertical"


class LogoRevealProps(CommonProps):
    asset_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    tagline: str | None = Field(default=None, max_length=140)


class CallToActionProps(CommonProps):
    title: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=80)
    detail: str | None = Field(default=None, max_length=180)


class ProgressAccentProps(CommonProps):
    global_start_frame: int = Field(ge=0)
    total_frames: int = Field(gt=0)


class DiagramOverlayProps(CommonProps):
    variant: Literal["corner_pulse", "arrow_trace", "outline_trace", "label_pop"]
    label: str | None = Field(default=None, max_length=120)
    layout_variant: Literal["default", "payoff"] = "default"


class EmphasisTextProps(CommonProps):
    text: str = Field(min_length=1, max_length=180)
    variant: Literal[
        "highlight_wipe",
        "staggered_glitch",
        "axis_stretch",
        "font_shift",
        "slide_up",
        "glow_underline",
    ] = "glow_underline"
    secondary_accent: Color = Field(default="#FACC15", pattern=r"^#[0-9A-Fa-f]{6}$")
    danger_accent: Color = Field(default="#FB7185", pattern=r"^#[0-9A-Fa-f]{6}$")


class KineticCaptionProps(CommonProps):
    text: str = Field(min_length=1, max_length=400)
    variant: Literal["default", "adaptive_texture", "player3", "stock_panel"] = "default"
    emphasis_terms: tuple[str, ...] = Field(default=(), max_length=24)
    secondary_accent: Color = Field(default="#FACC15", pattern=r"^#[0-9A-Fa-f]{6}$")


PropsModel = (
    TextCardProps
    | LowerThirdProps
    | QuoteCardProps
    | StatCardProps
    | CountdownProps
    | ComparisonProps
    | ProductFeatureProps
    | MediaFrameProps
    | PictureInPictureProps
    | SplitScreenProps
    | LogoRevealProps
    | CallToActionProps
    | ProgressAccentProps
    | DiagramOverlayProps
    | EmphasisTextProps
    | KineticCaptionProps
)
