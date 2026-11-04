"""Deterministic motion: camera moves, local micro-motion and ink transitions.

The package is shared by both core styles. Style differences come from
``config/styles.yaml`` (``motion.camera`` / ``motion.local_policy`` /
``motion.transition``); no function here branches on a style id.
"""

from .spec import (
    Box,
    CameraSpec,
    LocalMotionSpec,
    MaskSpec,
    MotionPlan,
    ShotSpec,
    TransitionSpec,
    load_plan,
    resolve_camera,
)

__all__ = [
    "Box",
    "CameraSpec",
    "LocalMotionSpec",
    "MaskSpec",
    "MotionPlan",
    "ShotSpec",
    "TransitionSpec",
    "load_plan",
    "resolve_camera",
]
