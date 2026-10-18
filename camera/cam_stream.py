#!/usr/bin/env python3
"""MJPEG stream of rpicam-vid to the browser, started by `cam stream`.

Every viewer always gets the newest frame: a slow network or browser skips
frames instead of queueing them, so latency does not build up. While the
stream runs this process owns the camera, so photos and video come from it.

  GET  /                   page: video, Photo/Video buttons, measured fps
  GET  /stream             multipart/x-mixed-replace JPEG stream (also works in <img>, VLC)
  GET  /stats              JSON: camera fps, frame size, bitrate, current recording
  POST /photo              save the current frame into --photo-dir
  POST /video/start|stop   record the stream into --video-dir as H.264 .mp4
  GET  /files/photos/NAME  download (also /files/videos/NAME)
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Kernel send buffer per viewer, ~2 frames. The default autotunes to megabytes,
# which on slow Wi-Fi would hold seconds of video.
SNDBUF = 128 * 1024

PAGE = """<!doctype html>
<html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Камера</title>
<style>
body{margin:0;background:#111;color:#ddd;font:15px system-ui,sans-serif}
canvas{display:block;margin:0 auto;max-width:100vw;max-height:calc(100vh - 6em);background:#000}
#bar{display:flex;gap:.6em;justify-content:center;align-items:center;flex-wrap:wrap;padding:.6em 1em 0}
button{font:inherit;padding:.4em 1.2em;border:0;border-radius:6px;background:#2d6cdf;color:#fff;cursor:pointer}
button:disabled{opacity:.5;cursor:default}
button.rec{background:#d33}
#msg a{color:#8bf}
#info{padding:.4em 1em .6em;text-align:center;font-variant-numeric:tabular-nums}
b{color:#fff}
</style></head><body>
<canvas id="v"></canvas>
<div id="bar"><button id="photo">Фото</button><button id="video">Відео</button><span id="msg"></span></div>
<div id="info">підключення…</div>
<script>
const cv = document.getElementById('v'), ctx = cv.getContext('2d');
const info = document.getElementById('info'), msg = document.getElementById('msg');
const photoBtn = document.getElementById('photo'), videoBtn = document.getElementById('video');
let pending = null, drawing = false, got = 0, shown = 0, t0 = performance.now(), cam = null, err = '';

// Decode one frame at a time; a frame that arrives meanwhile replaces the
// waiting one, so the picture never lags behind the camera.
async function draw() {
  if (drawing || !pending) return;
  drawing = true;
  const blob = pending; pending = null;
  try {
    const bmp = await createImageBitmap(blob);
    if (cv.width !== bmp.width || cv.height !== bmp.height) { cv.width = bmp.width; cv.height = bmp.height; }
    ctx.drawImage(bmp, 0, 0); bmp.close(); shown++;
  } catch (e) {}
  drawing = false; draw();
}

function find(buf, from) {           // index of \\r\\n\\r\\n
  for (let i = from; i + 3 < buf.length; i++)
    if (buf[i] === 13 && buf[i + 1] === 10 && buf[i + 2] === 13 && buf[i + 3] === 10) return i;
  return -1;
}

async function run() {
  for (;;) {
    try {
      const r = await fetch('/stream', {cache: 'no-store'});
      const rd = r.body.getReader();
      let buf = new Uint8Array(0);
      err = '';
      for (;;) {
        const {value, done} = await rd.read();
        if (done) break;
        const nb = new Uint8Array(buf.length + value.length);
        nb.set(buf); nb.set(value, buf.length); buf = nb;
        for (;;) {
          const h = find(buf, 0);
          if (h < 0) break;
          const m = /Content-Length: *(\\d+)/i.exec(new TextDecoder().decode(buf.subarray(0, h)));
          if (!m) { buf = buf.subarray(h + 4); continue; }
          const start = h + 4, len = +m[1];
          if (buf.length < start + len) break;
          pending = new Blob([buf.slice(start, start + len)], {type: 'image/jpeg'});
          buf = buf.subarray(start + len);
          got++; draw();
        }
      }
    } catch (e) {}
    err = 'немає зв\\'язку з Pi, перепідключаюсь…';
    await new Promise(r => setTimeout(r, 1000));
  }
}

async function post(path) {
  const r = await fetch(path, {method: 'POST', cache: 'no-store'});
  const j = await r.json().catch(() => ({error: 'HTTP ' + r.status}));
  if (!r.ok) throw new Error(j.error || 'HTTP ' + r.status);
  return j;
}

function link(f) { return `<a href="${f.url}" download>завантажити</a>`; }

function showRec(rec) {
  if (rec) {
    const s = Math.floor(rec.seconds), mm = String(Math.floor(s / 60)).padStart(2, '0');
    videoBtn.textContent = `Стоп запису ${mm}:${String(s % 60).padStart(2, '0')}`;
    videoBtn.classList.add('rec');
  } else {
    videoBtn.textContent = 'Відео';
    videoBtn.classList.remove('rec');
  }
}

photoBtn.onclick = async () => {
  photoBtn.disabled = true;
  try { const p = await post('/photo'); msg.innerHTML = `фото: ${p.name} · ${link(p)}`; }
  catch (e) { msg.textContent = 'фото: ' + e.message; }
  photoBtn.disabled = false;
};

videoBtn.onclick = async () => {
  videoBtn.disabled = true;
  try {
    if (cam && cam.recording) {
      msg.textContent = 'зберігаю відео…';
      const v = await post('/video/stop');
      cam.recording = null; showRec(null);
      msg.innerHTML = `відео: ${v.name} · ${v.seconds.toFixed(1)} с · ${v.fps.toFixed(1)} fps · ${link(v)}`;
    } else {
      const v = await post('/video/start');
      if (cam) cam.recording = {name: v.name, seconds: 0};
      showRec({seconds: 0});
      msg.textContent = 'запис: ' + v.name;
    }
  } catch (e) { msg.textContent = 'відео: ' + e.message; }
  videoBtn.disabled = false;
};

setInterval(async () => {
  const now = performance.now(), dt = (now - t0) / 1000;
  const g = got / dt, s = shown / dt;
  got = shown = 0; t0 = now;
  try { cam = await (await fetch('/stats', {cache: 'no-store'})).json(); } catch (e) { cam = null; }
  if (cam && !videoBtn.disabled) showRec(cam.recording);
  info.innerHTML = err ||
    (cam ? `${cam.width}×${cam.height} q${cam.quality} · камера <b>${cam.camera_fps.toFixed(1)}</b> fps · ` +
           `${cam.mbit.toFixed(1)} Мбіт/с · ` : '') +
    `отримано <b>${g.toFixed(1)}</b> fps · показано <b>${s.toFixed(1)}</b> fps`;
}, 1000);

run();
</script></body></html>
"""

FILE_RE = re.compile(r"^/files/(photos|videos)/([A-Za-z0-9_-][A-Za-z0-9_.-]*)$")


class NoFrame(Exception):
    """The camera has not produced a frame yet."""


class Busy(Exception):
    """A recording is already running / none is running."""


class Camera:
    """Runs rpicam-vid --codec mjpeg and keeps the newest JPEG."""

    def __init__(self, args, on_exit):
        self.args = args
        self.on_exit = on_exit
        self.cond = threading.Condition()
        self.frame = None
        self.seq = 0
        self.fps = 0.0
        self.frame_bytes = 0

    def run(self):
        a = self.args
        cmd = ["rpicam-vid", "-t", "0", "-n", "--mode", a.mode,
               "--width", str(a.width), "--height", str(a.height),
               "--framerate", str(a.fps), "--codec", "mjpeg", "-q", str(a.quality),
               "--flush", "-o", "-"]
        print("run:", " ".join(cmd), flush=True)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
        buf = b""
        n, t0 = 0, time.monotonic()
        while True:
            chunk = p.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            while True:
                s = buf.find(b"\xff\xd8")
                e = buf.find(b"\xff\xd9", s + 2) if s >= 0 else -1
                if e < 0:
                    break
                frame, buf = buf[s:e + 2], buf[e + 2:]
                with self.cond:
                    self.frame = frame
                    self.seq += 1
                    self.cond.notify_all()
                if self.seq == 1:
                    print("ready", flush=True)
                n += 1
                now = time.monotonic()
                if now - t0 >= 1:
                    self.fps, self.frame_bytes = n / (now - t0), len(frame)
                    n, t0 = 0, now
        # No camera means no stream: close a running recording, then exit so
        # `cam status` shows it.
        print(f"rpicam-vid exited with {p.wait()}", flush=True)
        self.on_exit()
        os._exit(1)


def jpeg_size(data):
    """(width, height) from the SOF marker of a JPEG."""
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return 0, 0


def new_path(directory, ext):
    """DIR/YYYYmmdd-HHMMSS.ext, with -2, -3... for several in one second."""
    os.makedirs(directory, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path, n = os.path.join(directory, stamp + ext), 2
    while os.path.exists(path):
        path, n = os.path.join(directory, f"{stamp}-{n}{ext}"), n + 1
    return path


def describe(path, kind):
    name = os.path.basename(path)
    return {"file": path, "name": name, "url": f"/files/{kind}/{name}",
            "kb": round(os.path.getsize(path) / 1024)}


def save_photo(cam, photo_dir):
    """The frame on screen right now, as is: no re-encoding, no pause."""
    with cam.cond:
        frame = cam.frame
    if frame is None:
        raise NoFrame("камера ще не дала жодного кадру")
    path = new_path(photo_dir, ".jpg")
    with open(path, "wb") as f:
        f.write(frame)
    w, h = jpeg_size(frame)
    return {**describe(path, "photos"), "width": w, "height": h}


class Recorder:
    """Pipes the stream's JPEGs into ffmpeg: H.264 .mp4 at a constant rate.

    ffmpeg ignores wall-clock timestamps on a piped MJPEG, so the rate is kept
    here: every 1/fps the newest frame is written, repeated if the camera is
    slower, skipped if faster. The file's duration is then the real time.
    `frames` counts distinct camera frames; `fps` is them per second.
    ffmpeg runs in its own session: `cam stop` signals the stream's process
    group, and only closing stdin (here) ends the file properly.
    """

    def __init__(self, cam, path, fps):
        self.cam, self.path, self.rate = cam, path, fps
        self.frames, self.written, self.stopping, self.error = 0, 0, False, ""
        self.t0 = time.monotonic()
        self.proc = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-f", "mjpeg", "-framerate", str(fps), "-i", "pipe:0",
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", "-y", path],
            stdin=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        self.thread = threading.Thread(target=self._feed, daemon=True)
        self.thread.start()

    def _feed(self):
        cam, last = self.cam, 0
        while not self.stopping:
            with cam.cond:
                frame, seq = cam.frame, cam.seq
            if frame is not None:
                if seq != last:
                    self.frames, last = self.frames + 1, seq
                due = int((time.monotonic() - self.t0) * self.rate) + 1
                try:
                    while self.written < due:
                        self.proc.stdin.write(frame)
                        self.written += 1
                except (BrokenPipeError, ValueError):
                    self.error = "ffmpeg завершився під час запису"
                    return
            with cam.cond:
                wait = self.t0 + self.written / self.rate - time.monotonic()
                cam.cond.wait_for(lambda: self.stopping, timeout=max(wait, 0.001))

    def status(self):
        return {"name": os.path.basename(self.path), "seconds": time.monotonic() - self.t0,
                "frames": self.frames}

    def stop(self):
        seconds = time.monotonic() - self.t0
        with self.cam.cond:
            self.stopping = True
            self.cam.cond.notify_all()
        self.thread.join()
        try:
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        err = self.proc.stderr.read().decode(errors="replace").strip()
        if self.proc.wait(timeout=60) != 0:
            raise RuntimeError(f"ffmpeg: {err or self.error or 'код ' + str(self.proc.returncode)}")
        return {**describe(self.path, "videos"), "frames": self.frames,
                "seconds": seconds, "fps": self.frames / seconds if seconds > 0 else 0.0}


class State:
    """Recording state shared by HTTP threads; finish() is safe to call twice."""

    def __init__(self, cam, args):
        self.cam, self.args = cam, args
        self.lock = threading.Lock()
        self.rec = None

    def start_video(self):
        with self.lock:
            if self.rec:
                raise Busy("запис уже йде: " + os.path.basename(self.rec.path))
            with self.cam.cond:
                if self.cam.frame is None:
                    raise NoFrame("камера ще не дала жодного кадру")
            self.rec = Recorder(self.cam, new_path(self.args.video_dir, ".mp4"), self.args.fps)
            return {**self.rec.status(), "file": self.rec.path}

    def stop_video(self):
        with self.lock:
            if not self.rec:
                raise Busy("запис не йде")
            rec, self.rec = self.rec, None
            return rec.stop()

    def recording(self):
        rec = self.rec
        return rec.status() if rec else None

    def finish(self):
        with self.lock:
            if self.rec:
                rec, self.rec = self.rec, None
                try:
                    print("video:", json.dumps(rec.stop(), ensure_ascii=False), flush=True)
                except RuntimeError as e:
                    print(e, flush=True)


def handler(cam, args, state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, ctype, body, code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, obj, code=200):
            self.send("application/json; charset=utf-8", json.dumps(obj, ensure_ascii=False).encode(), code)

        def do_GET(self):
            if self.path == "/":
                self.send("text/html; charset=utf-8", PAGE.encode())
            elif self.path == "/stats":
                self.send_json({
                    "width": args.width, "height": args.height, "quality": args.quality,
                    "camera_fps": cam.fps, "frame_kb": cam.frame_bytes / 1024,
                    "mbit": cam.frame_bytes * 8 * cam.fps / 1e6,
                    "recording": state.recording(),
                })
            elif self.path == "/stream":
                self.stream()
            elif self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            elif FILE_RE.match(self.path):
                self.download(*FILE_RE.match(self.path).groups())
            else:
                self.send_error(404)

        def do_POST(self):
            try:
                if self.path == "/photo":
                    self.send_json(save_photo(cam, args.photo_dir))
                elif self.path == "/video/start":
                    self.send_json(state.start_video())
                elif self.path == "/video/stop":
                    self.send_json(state.stop_video())
                else:
                    self.send_error(404)
            except NoFrame as e:
                self.send_json({"error": str(e)}, 503)
            except Busy as e:
                self.send_json({"error": str(e)}, 409)
            except (OSError, RuntimeError) as e:
                self.send_json({"error": str(e)}, 500)

        def download(self, kind, name):
            path = os.path.join(args.photo_dir if kind == "photos" else args.video_dir, name)
            if not os.path.isfile(path):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg" if name.endswith(".jpg") else "video/mp4")
            self.send_header("Content-Length", str(os.path.getsize(path)))
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.end_headers()
            with open(path, "rb") as f:
                try:
                    shutil.copyfileobj(f, self.wfile)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        def stream(self):
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SNDBUF)
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            last = 0
            try:
                while True:
                    with cam.cond:
                        cam.cond.wait_for(lambda: cam.seq != last, timeout=5)
                        frame, last = cam.frame, cam.seq
                    if frame is None:
                        continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                     + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n")
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass

    return Handler


def make_server(cam, args, host, port):
    state = State(cam, args)
    srv = ThreadingHTTPServer((host, port), handler(cam, args, state))
    srv.daemon_threads = True
    srv.state = state
    return srv


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--mode", default="1640:1232")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=960)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--photo-dir", default=os.path.expanduser("~/camera/photos"))
    ap.add_argument("--video-dir", default=os.path.expanduser("~/camera/videos"))
    args = ap.parse_args()

    states = []
    cam = Camera(args, on_exit=lambda: [s.finish() for s in states])
    srv = make_server(cam, args, "0.0.0.0", args.port)
    states.append(srv.state)
    threading.Thread(target=cam.run, daemon=True).start()
    print(f"listening on :{args.port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.state.finish()


if __name__ == "__main__":
    main()
