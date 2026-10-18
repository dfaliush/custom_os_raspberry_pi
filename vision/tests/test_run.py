import csv
import sys
import urllib.request
from pathlib import Path

import numpy as np

from rpi5os_vision import run
from rpi5os_vision.camera import RpicamSource
from rpi5os_vision.geometry import Detection, Target
from rpi5os_vision.metrics import CSV_FIELDS, PerfMeter, format_line
from rpi5os_vision.stream import MjpegServer, annotate

HERE = Path(__file__).parent
MODEL = str(HERE.parent / "models" / "current")
DATA = str(HERE / "data")
FAKE = str(HERE / "fake_rpicam.py")


def test_run_on_files_writes_csv(tmp_path):
    out = tmp_path / "perf.csv"
    assert run.main(["--model", MODEL, "--source", DATA, "--frames", "1", "--csv", str(out)]) == 0
    with open(out) as f:
        assert next(csv.reader(f)) == CSV_FIELDS


def test_run_end_of_files_is_0():
    assert run.main(["--model", MODEL, "--source", DATA]) == 0


def test_run_missing_model_exit_2(tmp_path):
    assert run.main(["--model", str(tmp_path / "none"), "--source", DATA]) == 2


def test_run_unknown_class_exit_2():
    assert run.main(["--model", MODEL, "--source", DATA, "--target-class", "mug"]) == 2


def test_run_camera_lost_exit_3(monkeypatch):
    cam = RpicamSource(64, 48, cmd=[sys.executable, FAKE, "64", "48", "1"])
    monkeypatch.setattr(run, "open_source", lambda *a, **k: cam)
    assert run.main(["--model", MODEL, "--source", "camera"]) == 3


def test_stream_serves_jpeg():
    srv = MjpegServer(0).start()
    try:
        srv.publish(np.zeros((48, 64, 3), np.uint8))
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.port}/frame.jpg", timeout=5) as r:
            assert r.read(2) == b"\xff\xd8"
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.port}/", timeout=5) as r:
            assert b'src="/stream"' in r.read()
    finally:
        srv.close()


def test_annotate_keeps_frame_untouched():
    frame = np.zeros((48, 64, 3), np.uint8)
    out = annotate(frame, [Detection(10, 10, 30, 30, .9, 0, "cup")],
                   Target(True, .9, -.37, -.17, .13, "cup"))
    assert out.shape == frame.shape and out.any() and not frame.any()


class FakeClock:
    t = 100.0

    def __call__(self):
        return self.t


def test_perfmeter_fps():
    clock = FakeClock()
    m = PerfMeter(clock=clock)
    assert m.sample() is None
    for _ in range(10):
        m.frame(20.0)
    clock.t += 1.0
    s = m.sample()
    assert s["fps"] == 10 and s["infer_ms"] == 20.0
    assert s["rss_mb"] > 0 and s["cpu_proc"] >= 0 and 0 <= s["cpu_sys"] <= 100
    assert m.sample() is None   # less than 1 s since the last sample


def test_format_line():
    s = {"fps": 24.8, "infer_ms": 31.2, "cpu_proc": 310.4, "cpu_sys": 82.0, "rss_mb": 180.2, "temp_c": 62.1}
    line = format_line(s, Target(True, .91, -.42, .1, .2, "duck_pirate"))
    assert line == "fps=24.8 infer=31ms cpu=310% sys=82% rss=180MB temp=62°C det=1 dx=-0.42"
    s["temp_c"] = None
    assert "temp=-" in format_line(s, Target.none()) and "det=0" in format_line(s, Target.none())
