"""Script-to-Film production layer.

This package owns project data, storyboard planning, continuity checking and the
edit timeline. It never calls ComfyUI; generation stays in ``production.py``.
See docs/FILM_PRODUCTION_GUIDE.md.
"""

from .continuity import Issue, check_continuity, has_errors
from .project import FilmProject, load_project, project_dir, validate_project, write_model
from .schemas import (
    CameraMove,
    CameraSpec,
    ContinuitySpec,
    EditTimeline,
    GenerationSpec,
    Layers,
    MotionSpec,
    Narration,
    NarrationSegment,
    Screenplay,
    ShotSize,
    ShotSpec,
    ShotStatus,
    SourceText,
    Storyboard,
    TimelineEntry,
    Transition,
    VisualBible,
)
from .prompts import build_keyframe_prompt, build_video_prompt, compile_shot_prompts
from .storyboard import plan_storyboard
from .timeline import build_timeline, narration_spans

__all__ = [
    "CameraMove",
    "CameraSpec",
    "ContinuitySpec",
    "EditTimeline",
    "FilmProject",
    "GenerationSpec",
    "Issue",
    "Layers",
    "MotionSpec",
    "Narration",
    "NarrationSegment",
    "Screenplay",
    "ShotSize",
    "ShotSpec",
    "ShotStatus",
    "SourceText",
    "Storyboard",
    "TimelineEntry",
    "Transition",
    "VisualBible",
    "build_keyframe_prompt",
    "build_timeline",
    "build_video_prompt",
    "check_continuity",
    "compile_shot_prompts",
    "has_errors",
    "load_project",
    "narration_spans",
    "plan_storyboard",
    "project_dir",
    "validate_project",
    "write_model",
]
