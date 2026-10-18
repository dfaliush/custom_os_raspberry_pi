import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from rpi5os_vision.camera import CameraLost, RpicamSource
from rpi5os_vision.source import FileSource, SourceEnded, open_source

FAKE = str(Path(__file__).parent / "fake_rpicam.py")


def fake(w, h, n, delay=0.0):
    return [sys.executable, FAKE, str(w), str(h), str(n), str(delay)]


def test_bad_width_rejected():
    with pytest.raises(ValueError):
        RpicamSource(600, 480)


def test_odd_height_rejected():
    with pytest.raises(ValueError):
        RpicamSource(640, 479)


def test_default_command():
    cmd = RpicamSource(640, 480, 30).cmd
    assert cmd[0] == "rpicam-vid" and cmd[cmd.index("--codec") + 1] == "yuv420"
    assert cmd[cmd.index("--width") + 1] == "640" and cmd[-2:] == ["-o", "-"]


def test_reads_frames_then_camera_lost():
    with RpicamSource(64, 48, cmd=fake(64, 48, 2, 0.05)) as cam:
        frame, ts = cam.read()
        assert frame.shape == (48, 64, 3) and frame.dtype == np.uint8 and ts > 0
        with pytest.raises(CameraLost):
            for _ in range(3):
                cam.read(timeout=2)


def bgr_of_luma(y):
    """BGR value of a gray I420 pixel with luma y (BT.601 limited range)."""
    yuv = np.concatenate([np.full((2, 2), y, np.uint8), np.full((1, 2), 128, np.uint8)])
    return int(cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)[0, 0, 0])


def test_returns_newest_frame():
    with RpicamSource(64, 48, cmd=fake(64, 48, 5)) as cam:
        time.sleep(0.5)
        frame, _ = cam.read()
        assert int(frame[0, 0, 0]) == bgr_of_luma(80)   # frame #4 of 0..4, luma 80


def test_read_never_repeats_a_frame():
    with RpicamSource(64, 48, cmd=fake(64, 48, 3, 0.05)) as cam:
        seen = []
        try:
            while True:
                seen.append(int(cam.read(timeout=1)[0][0, 0, 0]))
        except CameraLost:
            pass
        assert len(seen) == len(set(seen)) >= 1


def write_pngs(d, n):
    for i in range(n):
        cv2.imwrite(str(d / f"{i:02d}.png"), np.full((8, 8, 3), i * 10, np.uint8))


def test_file_source_dir_order(tmp_path):
    write_pngs(tmp_path, 3)
    with FileSource(str(tmp_path)) as src:
        assert [int(src.read()[0][0, 0, 0]) for _ in range(3)] == [0, 10, 20]
        with pytest.raises(SourceEnded):
            src.read()


def test_file_source_loop(tmp_path):
    write_pngs(tmp_path, 3)
    with FileSource(str(tmp_path), loop=True) as src:
        vals = [int(src.read()[0][0, 0, 0]) for _ in range(4)]
    assert vals[3] == vals[0]


def test_file_source_single_image(tmp_path):
    write_pngs(tmp_path, 1)
    with FileSource(str(tmp_path / "00.png")) as src:
        assert src.read()[0].shape == (8, 8, 3)


def test_file_source_empty_dir(tmp_path):
    with pytest.raises(SourceEnded):
        FileSource(str(tmp_path)).read()


def test_open_source_camera_spec():
    assert isinstance(open_source("camera", 640, 480, 30), RpicamSource)


def test_open_source_path(tmp_path):
    assert isinstance(open_source(str(tmp_path), 640, 480, 30), FileSource)
