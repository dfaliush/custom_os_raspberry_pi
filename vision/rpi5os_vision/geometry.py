"""Detections and where the target is relative to the frame center."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """A box in frame pixels."""

    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    cls: int
    name: str


@dataclass(frozen=True)
class Target:
    """The target relative to the frame center.

    dx, dy are in [-1, 1]: -1 is the left / top edge, 0 the center, 1 the
    right / bottom edge. area is the box's share of the frame.
    """

    detected: bool
    confidence: float
    dx: float
    dy: float
    area: float
    class_name: str

    @staticmethod
    def none():
        return Target(False, 0.0, 0.0, 0.0, 0.0, "")


def _clamp(v):
    return max(-1.0, min(1.0, v))


def target_from(dets, width, height, target_class=""):
    """The most confident detection of target_class (any class if empty)."""
    cands = [d for d in dets if not target_class or d.name == target_class]
    if not cands:
        return Target.none()
    d = max(cands, key=lambda d: d.conf)
    cx, cy = (d.x1 + d.x2) / 2, (d.y1 + d.y2) / 2
    return Target(
        detected=True,
        confidence=d.conf,
        dx=_clamp((cx - width / 2) / (width / 2)),
        dy=_clamp((cy - height / 2) / (height / 2)),
        area=(d.x2 - d.x1) * (d.y2 - d.y1) / (width * height),
        class_name=d.name,
    )
