"""YOLO11 detector on ncnn: letterbox → ncnn → decode → NMS, all in numpy.

Pre- and post-processing match Ultralytics, so the NCNN model gives the same
boxes as the .pt it was exported from.
"""
import time

import cv2
import ncnn
import numpy as np

from .geometry import Detection

PAD = 114
CLASS_OFFSET = 4096  # NMS per class: boxes of different classes never overlap


def letterbox(img, size):
    """Resize keeping aspect, pad to size×size. Returns (image, scale, (pad_x, pad_y))."""
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nw, nh = round(w * r), round(h * r)
    if (nw, nh) != (w, h):
        img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    dw, dh = (size - nw) / 2, (size - nh) / 2
    top, bottom = round(dh - 0.1), round(dh + 0.1)
    left, right = round(dw - 0.1), round(dw + 0.1)
    out = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(PAD, PAD, PAD))
    return out, r, (left, top)


def decode(out, conf):
    """out: (4+nc, N) rows cx, cy, w, h, class scores. Returns xyxy boxes, scores, classes."""
    scores_all = out[4:]
    cls = scores_all.argmax(axis=0)
    scores = scores_all[cls, np.arange(out.shape[1])]
    keep = scores >= conf
    cx, cy, w, h = out[:4, keep]
    boxes = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1).astype(np.float32)
    return boxes.reshape(-1, 4), scores[keep].astype(np.float32), cls[keep]


def nms(boxes, scores, cls, iou):
    """Greedy NMS per class. Indices of kept boxes, highest score first."""
    b = boxes + (cls[:, None] * CLASS_OFFSET).astype(np.float32)
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        rest = order[1:]
        xx1 = np.maximum(b[i, 0], b[rest, 0])
        yy1 = np.maximum(b[i, 1], b[rest, 1])
        xx2 = np.minimum(b[i, 2], b[rest, 2])
        yy2 = np.minimum(b[i, 3], b[rest, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        overlap = inter / (area[i] + area[rest] - inter + 1e-9)
        order = rest[overlap <= iou]
    return np.array(keep, dtype=np.int64)


class Detector:
    def __init__(self, model, conf=0.25, iou=0.45, threads=4):
        self.model, self.conf, self.iou = model, conf, iou
        self.net = ncnn.Net()
        self.net.opt.use_vulkan_compute = False
        self.net.opt.num_threads = threads
        if self.net.load_param(str(model.param)) != 0 or self.net.load_model(str(model.bin)) != 0:
            raise RuntimeError(f"ncnn не завантажив модель з {model.dir}")
        self.input_name = self.net.input_names()[0]
        self.output_name = self.net.output_names()[0]
        self.last_infer_ms = 0.0

    def detect(self, bgr):
        h, w = bgr.shape[:2]
        img, r, (px, py) = letterbox(bgr, self.model.imgsz)
        chw = np.ascontiguousarray(img[:, :, ::-1].transpose(2, 0, 1), dtype=np.float32) / 255.0
        t0 = time.perf_counter()
        ex = self.net.create_extractor()
        ex.input(self.input_name, ncnn.Mat(chw))
        _, out = ex.extract(self.output_name)
        out = np.array(out)
        self.last_infer_ms = (time.perf_counter() - t0) * 1000
        boxes, scores, cls = decode(out, self.conf)
        dets = []
        for i in nms(boxes, scores, cls, self.iou):
            x1, y1, x2, y2 = boxes[i]
            x1, x2 = np.clip([(x1 - px) / r, (x2 - px) / r], 0, w)
            y1, y2 = np.clip([(y1 - py) / r, (y2 - py) / r], 0, h)
            if x2 > x1 and y2 > y1:
                c = int(cls[i])
                dets.append(Detection(float(x1), float(y1), float(x2), float(y2), float(scores[i]), c,
                                      self.model.names[c]))
        return dets
