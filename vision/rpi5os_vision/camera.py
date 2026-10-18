"""Camera frames from `rpicam-vid --codec yuv420 -o -`.

A reader thread keeps only the newest raw frame; read() converts it to BGR
when asked. Inference is slower than the camera, so older frames are dropped
instead of queueing up: latency stays one frame.
"""
import collections
import subprocess
import threading
import time

import cv2
import numpy as np


class CameraLost(Exception):
    """rpicam-vid exited or stopped sending frames."""


class RpicamSource:
    def __init__(self, width=640, height=480, fps=30, cmd=None):
        # yuv420 rows are unpadded only for widths that are a multiple of 64.
        if width % 64 or height % 2:
            raise ValueError(f"кадр {width}x{height}: ширина має бути кратна 64, висота парна")
        self.width, self.height = width, height
        self.cmd = cmd or ["rpicam-vid", "-t", "0", "-n", "--codec", "yuv420",
                           "--width", str(width), "--height", str(height),
                           "--framerate", str(fps), "-o", "-"]
        self.size = width * height * 3 // 2
        self.cond = threading.Condition()
        self.raw, self.ts, self.seq, self.taken = None, 0.0, 0, 0
        self.lost = False
        self.stderr = collections.deque(maxlen=20)
        self.proc = None

    def start(self):
        if self.proc:
            return
        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        threading.Thread(target=self._read_frames, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_frames(self):
        out = self.proc.stdout
        while True:
            buf = bytearray(self.size)
            view, got = memoryview(buf), 0
            while got < self.size:
                n = out.readinto(view[got:])
                if not n:
                    with self.cond:
                        self.lost = True
                        self.cond.notify_all()
                    return
                got += n
            with self.cond:
                self.raw, self.ts = buf, time.monotonic()
                self.seq += 1
                self.cond.notify_all()

    def _read_stderr(self):
        for line in self.proc.stderr:
            self.stderr.append(line.decode(errors="replace").rstrip())

    def read(self, timeout=2.0):
        """The newest frame not returned before: (BGR array, monotonic time)."""
        self.start()
        with self.cond:
            self.cond.wait_for(lambda: self.seq != self.taken or self.lost, timeout)
            if self.seq == self.taken:
                if self.lost:
                    tail = " | ".join(list(self.stderr)[-3:])
                    raise CameraLost(f"rpicam-vid завершився ({self.proc.poll()}): {tail}")
                raise CameraLost(f"немає кадрів {timeout:.0f} с")
            raw, ts, self.taken = self.raw, self.ts, self.seq
        yuv = np.frombuffer(raw, np.uint8).reshape(self.height * 3 // 2, self.width)
        return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420), ts

    def close(self):
        if not self.proc:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()
