#!/usr/bin/env python3
"""MJPEG stream of rpicam-vid to the browser, started by `cam stream`.

Every viewer always gets the newest frame: a slow network or browser skips
frames instead of queueing them, so latency does not build up.

  GET /        page: video + measured fps (camera on the Pi, frames shown here)
  GET /stream  multipart/x-mixed-replace JPEG stream (also works in <img>, VLC)
  GET /stats   JSON: camera fps measured on the Pi, frame size, bitrate
"""
import argparse
import json
import os
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
canvas{display:block;margin:0 auto;max-width:100vw;max-height:calc(100vh - 3em);background:#000}
#info{padding:.6em 1em;text-align:center;font-variant-numeric:tabular-nums}
b{color:#fff}
</style></head><body>
<canvas id="v"></canvas>
<div id="info">підключення…</div>
<script>
const cv = document.getElementById('v'), ctx = cv.getContext('2d');
const info = document.getElementById('info');
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

function find(buf, from) {           // index of \r\n\r\n
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

setInterval(async () => {
  const now = performance.now(), dt = (now - t0) / 1000;
  const g = got / dt, s = shown / dt;
  got = shown = 0; t0 = now;
  try { cam = await (await fetch('/stats', {cache: 'no-store'})).json(); } catch (e) { cam = null; }
  info.innerHTML = err ||
    (cam ? `${cam.width}×${cam.height} q${cam.quality} · камера <b>${cam.camera_fps.toFixed(1)}</b> fps · ` +
           `${cam.mbit.toFixed(1)} Мбіт/с · ` : '') +
    `отримано <b>${g.toFixed(1)}</b> fps · показано <b>${s.toFixed(1)}</b> fps`;
}, 1000);

run();
</script></body></html>
"""


class Camera:
    """Runs rpicam-vid --codec mjpeg and keeps the newest JPEG."""

    def __init__(self, args):
        self.args = args
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
        # No camera means no stream: exit so `cam status` shows it.
        print(f"rpicam-vid exited with {p.wait()}", flush=True)
        os._exit(1)


def handler(cam, args):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, ctype, body):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.send("text/html; charset=utf-8", PAGE.encode())
            elif self.path == "/stats":
                self.send("application/json", json.dumps({
                    "width": args.width, "height": args.height, "quality": args.quality,
                    "camera_fps": cam.fps, "frame_kb": cam.frame_bytes / 1024,
                    "mbit": cam.frame_bytes * 8 * cam.fps / 1e6,
                }).encode())
            elif self.path == "/stream":
                self.stream()
            elif self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                self.send_error(404)

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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--mode", default="1640:1232")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=960)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--quality", type=int, default=60)
    args = ap.parse_args()

    cam = Camera(args)
    threading.Thread(target=cam.run, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), handler(cam, args))
    srv.daemon_threads = True
    print(f"listening on :{args.port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
