"""Public package for the programmable nonlinear video editing engine."""

from video_engine.api.engine import VideoEngine
from video_engine.core.schema import Project

__all__ = ["Project", "VideoEngine", "__version__"]

__version__ = "0.2.0"
