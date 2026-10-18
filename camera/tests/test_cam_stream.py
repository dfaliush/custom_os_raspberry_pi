"""cam_stream.py without a camera: a fake Camera fed with real JPEG frames.

Run in WSL (needs ffmpeg/ffprobe for the recording tests):
    cd camera && python3 -m pytest -q tests
"""
import io
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from argparse import Namespace
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cam_stream  # noqa: E402

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="no ffmpeg")


def jpeg(i, w=64, h=48):
    b = io.BytesIO()
    Image.new("RGB", (w, h), (i * 8 % 256, 100, 200)).save(b, "JPEG")
    return b.getvalue()


class FakeCamera:
    """Same fields as cam_stream.Camera: cond, frame, seq, fps."""

    def __init__(self):
        self.cond = threading.Condition()
        self.frame = None
        self.seq = 0
        self.fps = 0.0
        self.frame_bytes = 0

    def push(self, data):
        with self.cond:
            self.frame = data
            self.seq += 1
            self.cond.notify_all()

    def feed(self, n, fps):
        for i in range(n):
            self.push(jpeg(i))
            time.sleep(1 / fps)


def args(tmp_path):
    return Namespace(port=0, mode="1640:1232", width=64, height=48, fps=30, quality=80,
                     photo_dir=str(tmp_path / "photos"), video_dir=str(tmp_path / "videos"))


@pytest.fixture
def server(tmp_path):
    cam = FakeCamera()
    srv = cam_stream.make_server(cam, args(tmp_path), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield cam, srv, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.state.finish()


def post(url):
    req = urllib.request.Request(url, method="POST", data=b"")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def test_photo_saves_current_frame(tmp_path):
    cam = FakeCamera()
    cam.push(jpeg(1))
    p = cam_stream.save_photo(cam, str(tmp_path))
    assert Path(p["file"]).read_bytes() == jpeg(1)
    assert (p["width"], p["height"]) == (64, 48)
    assert p["url"] == "/files/photos/" + p["name"]


def test_photos_in_same_second_get_unique_names(tmp_path):
    cam = FakeCamera()
    cam.push(jpeg(1))
    names = {cam_stream.save_photo(cam, str(tmp_path))["name"] for _ in range(3)}
    assert len(names) == 3


def test_photo_without_frame_fails(tmp_path):
    with pytest.raises(cam_stream.NoFrame):
        cam_stream.save_photo(FakeCamera(), str(tmp_path))


def test_http_photo_and_download(server):
    cam, _, base = server
    cam.push(jpeg(5))
    p = post(base + "/photo")
    with urllib.request.urlopen(base + p["url"], timeout=5) as r:
        assert r.read() == jpeg(5)
        assert "attachment" in r.headers["Content-Disposition"]


def test_http_photo_before_first_frame_is_503(server):
    _, _, base = server
    with pytest.raises(urllib.error.HTTPError) as e:
        post(base + "/photo")
    assert e.value.code == 503


def test_download_rejects_path_traversal(server):
    _, _, base = server
    for path in ("/files/photos/..%2Fx", "/files/photos/../x", "/files/etc/passwd"):
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + path, timeout=5)
        assert e.value.code == 404


@needs_ffmpeg
def test_recording_makes_mp4_with_real_duration(server):
    cam, _, base = server
    cam.push(jpeg(0))
    started = post(base + "/video/start")
    assert started["name"].endswith(".mp4")
    cam.feed(30, fps=15)  # ~2 s of video
    stats = json.load(urllib.request.urlopen(base + "/stats", timeout=5))
    assert stats["recording"]["name"] == started["name"]
    done = post(base + "/video/stop")
    assert done["frames"] >= 25
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", done["file"]]))
    assert 1.5 < dur < 3.0
    assert json.load(urllib.request.urlopen(base + "/stats", timeout=5))["recording"] is None


@needs_ffmpeg
def test_second_start_is_409(server):
    cam, _, base = server
    cam.push(jpeg(0))
    post(base + "/video/start")
    with pytest.raises(urllib.error.HTTPError) as e:
        post(base + "/video/start")
    assert e.value.code == 409


def test_stop_without_recording_is_409(server):
    _, _, base = server
    with pytest.raises(urllib.error.HTTPError) as e:
        post(base + "/video/stop")
    assert e.value.code == 409


@needs_ffmpeg
def test_finish_closes_running_recording(server):
    cam, srv, base = server
    cam.push(jpeg(0))
    f = post(base + "/video/start")["file"]
    cam.feed(10, fps=15)
    srv.state.finish()
    out = subprocess.run(["ffprobe", "-v", "error", f], capture_output=True)
    assert out.returncode == 0, out.stderr
