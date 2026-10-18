"""Annotated frames as an MJPEG stream: http://<pi>:PORT/ in any browser.

Each viewer gets the newest frame; a slow viewer skips frames, so latency
does not grow.
"""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

GREEN, BLUE, YELLOW = (0, 220, 0), (255, 160, 0), (0, 220, 255)

PAGE = b"""<!doctype html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>rpi5os-detect</title>
<style>body{margin:0;background:#111}img{display:block;margin:auto;max-width:100vw;max-height:100vh}</style>
</head><body><img src="/stream" alt="stream"></body></html>"""


def annotate(frame, dets, target):
    """A copy of frame with boxes, the frame center and a line to the target."""
    img = frame.copy()
    h, w = img.shape[:2]
    best = None
    if target.detected:
        cands = [d for d in dets if d.name == target.class_name]
        best = max(cands, key=lambda d: d.conf, default=None)
    for d in dets:
        color = GREEN if d is best else BLUE
        p1, p2 = (int(d.x1), int(d.y1)), (int(d.x2), int(d.y2))
        cv2.rectangle(img, p1, p2, color, 2)
        cv2.putText(img, f"{d.name} {d.conf:.2f}", (p1[0], max(p1[1] - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    c = (w // 2, h // 2)
    cv2.drawMarker(img, c, YELLOW, cv2.MARKER_CROSS, 20, 1)
    if target.detected:
        t = (int(c[0] + target.dx * w / 2), int(c[1] + target.dy * h / 2))
        cv2.line(img, c, t, YELLOW, 1, cv2.LINE_AA)
        cv2.putText(img, f"dx={target.dx:+.2f} dy={target.dy:+.2f}", (8, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, YELLOW, 1, cv2.LINE_AA)
    return img


class MjpegServer:
    def __init__(self, port, quality=80):
        self.quality = quality
        self.cond = threading.Condition()
        self.jpeg, self.seq = None, 0
        self.srv = ThreadingHTTPServer(("0.0.0.0", port), self._handler())
        self.srv.daemon_threads = True
        self.port = self.srv.server_address[1]

    def start(self):
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self

    def publish(self, bgr):
        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        if ok:
            with self.cond:
                self.jpeg, self.seq = buf.tobytes(), self.seq + 1
                self.cond.notify_all()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path == "/":
                    self._send("text/html; charset=utf-8", PAGE)
                elif self.path == "/frame.jpg":
                    with server.cond:
                        jpeg = server.jpeg
                    if jpeg is None:
                        self.send_error(503)
                    else:
                        self._send("image/jpeg", jpeg)
                elif self.path == "/stream":
                    self._stream()
                else:
                    self.send_error(404)

            def _send(self, ctype, body):
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _stream(self):
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                last = 0
                try:
                    while True:
                        with server.cond:
                            server.cond.wait_for(lambda: server.seq != last, timeout=5)
                            jpeg, last = server.jpeg, server.seq
                        if jpeg is None:
                            continue
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                         + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass

        return Handler
