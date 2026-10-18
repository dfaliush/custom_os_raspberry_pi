"""Frames from files: a directory of images, one image or a video.

Same read()/close() as RpicamSource, for replay and tests without a camera.
"""
import time
from pathlib import Path

import cv2

from .camera import RpicamSource

IMAGES = {".jpg", ".jpeg", ".png", ".bmp"}


class SourceEnded(Exception):
    """No more frames (and loop is off)."""


class FileSource:
    def __init__(self, path, loop=False, fps=0):
        self.path, self.loop, self.period = Path(path), loop, 1 / fps if fps > 0 else 0
        if self.path.is_dir():
            self.files = sorted(p for p in self.path.iterdir() if p.suffix.lower() in IMAGES)
        elif self.path.suffix.lower() in IMAGES:
            self.files = [self.path]
        else:
            self.files = None   # a video
        self.i, self.video, self.last = 0, None, 0.0

    def start(self):
        pass

    def _next(self):
        if self.files is not None:
            if self.i >= len(self.files):
                return None
            self.i += 1
            return cv2.imread(str(self.files[self.i - 1]))
        if self.video is None:
            self.video = cv2.VideoCapture(str(self.path))
        ok, frame = self.video.read()
        return frame if ok else None

    def _rewind(self):
        self.i = 0
        if self.video is not None:
            self.video.release()
            self.video = None

    def read(self, timeout=2.0):
        frame = self._next()
        if frame is None and self.loop:
            self._rewind()
            frame = self._next()
        if frame is None:
            raise SourceEnded(f"кадри з {self.path} закінчились")
        if self.period:
            wait = self.last + self.period - time.monotonic()
            if wait > 0:
                time.sleep(wait)
        self.last = time.monotonic()
        return frame, self.last

    def close(self):
        if self.video is not None:
            self.video.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def open_source(spec, width, height, fps, loop=False):
    if spec == "camera":
        return RpicamSource(width, height, fps)
    return FileSource(spec, loop=loop)
