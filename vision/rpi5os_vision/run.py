"""rpi5os-detect: camera (or files) → YOLO on ncnn → target offset, FPS and CPU.

Exit codes: 0 — done (end of files, --frames reached, Ctrl+C), 2 — no model or
unknown --target-class, 3 — camera lost.
"""
import argparse
import csv
import sys

from .camera import CameraLost
from .geometry import target_from
from .metrics import CSV_FIELDS, PerfMeter, csv_row, format_line
from .model import ModelNotFound, locate, validate_class
from .source import SourceEnded, open_source
from .stream import MjpegServer, annotate
from .yolo_ncnn import Detector


def parse(argv):
    ap = argparse.ArgumentParser(prog="rpi5os-detect", description=__doc__.splitlines()[0])
    ap.add_argument("--model", help="тека з model.ncnn.param/.bin і metadata.yaml")
    ap.add_argument("--source", default="camera", help="camera, тека зображень, зображення або відео")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--conf", type=float, default=0.25)
    # 2, not 4: with all 4 cores in ncnn the Pi 5's core current peaked at
    # 9.2 A and the board powered off; 2 threads peak at 5.7 A, ~28 fps.
    ap.add_argument("--threads", type=int, default=2, help="потоки ncnn (4 вимикали Pi 5 під навантаженням)")
    ap.add_argument("--target-class", default="", help="клас цілі; порожньо — будь-який")
    ap.add_argument("--stream", type=int, default=0, metavar="PORT", help="MJPEG з рамками; 0 — вимкнено")
    ap.add_argument("--csv", help="метрики раз на секунду в CSV")
    ap.add_argument("--frames", type=int, default=0, help="зупинитись після N кадрів; 0 — без кінця")
    ap.add_argument("--loop", action="store_true", help="файлове джерело по колу")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse(argv)
    try:
        info = locate(a.model)
        validate_class(info, a.target_class)
    except (ModelNotFound, ValueError) as e:
        print(f"rpi5os-detect: {e}", file=sys.stderr)
        return 2
    det = Detector(info, conf=a.conf, threads=a.threads)
    print(f"модель: {info.dir} ({len(info.names)} класів, {info.imgsz}px); джерело: {a.source}", flush=True)
    src = open_source(a.source, a.width, a.height, a.fps, loop=a.loop)
    server = MjpegServer(a.stream).start() if a.stream else None
    if server:
        print(f"стрім: http://<pi>:{server.port}/", flush=True)
    out = open(a.csv, "w", newline="") if a.csv else None
    writer = csv.writer(out) if out else None
    if writer:
        writer.writerow(CSV_FIELDS)
    meter, n = PerfMeter(), 0
    try:
        while True:
            frame, _ = src.read()
            dets = det.detect(frame)
            h, w = frame.shape[:2]
            target = target_from(dets, w, h, a.target_class)
            meter.frame(det.last_infer_ms)
            if server:
                server.publish(annotate(frame, dets, target))
            s = meter.sample()
            if s:
                print(format_line(s, target), flush=True)
                if writer:
                    writer.writerow(csv_row(s, target))
                    out.flush()
            n += 1
            if a.frames and n >= a.frames:
                break
    except SourceEnded:
        pass
    except CameraLost as e:
        print(f"rpi5os-detect: камера: {e}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        pass
    finally:
        src.close()
        if server:
            server.close()
        if out:
            out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
