from pathlib import Path

import cv2
import numpy as np
import pytest

from rpi5os_vision.model import locate
from rpi5os_vision.yolo_ncnn import Detector, decode, letterbox, nms

HERE = Path(__file__).parent
MODEL = HERE.parent / "models" / "coco-yolo11n"


def test_letterbox_shape_and_scale():
    img = np.zeros((480, 640, 3), np.uint8)
    out, r, (px, py) = letterbox(img, 416)
    assert out.shape == (416, 416, 3) and out.dtype == np.uint8
    assert r == pytest.approx(0.65)
    assert (px, py) == (0, 52)
    assert out[0, 0, 0] == 114 and out[52, 0, 0] == 0 and out[363, 0, 0] == 0 and out[364, 0, 0] == 114


def test_letterbox_portrait():
    out, r, (px, py) = letterbox(np.zeros((400, 200, 3), np.uint8), 416)
    assert r == pytest.approx(1.04) and (px, py) == (104, 0)


def test_decode_filters_and_converts():
    out = np.zeros((4 + 2, 3), np.float32)
    out[:4, 0] = [100, 100, 20, 40]
    out[5, 0] = .9          # class 1
    out[:4, 1] = [50, 50, 10, 10]
    out[4, 1] = .1          # below conf
    boxes, scores, cls = decode(out, conf=.25)
    np.testing.assert_allclose(boxes, [[90, 80, 110, 120]])
    np.testing.assert_allclose(scores, [.9], rtol=1e-6)
    assert cls.tolist() == [1]


def test_decode_nothing_above_conf():
    boxes, scores, cls = decode(np.zeros((5, 4), np.float32), conf=.25)
    assert boxes.shape == (0, 4) and scores.shape == (0,) and cls.shape == (0,)


def test_nms_suppresses_overlap_same_class():
    boxes = np.array([[0, 0, 100, 100], [5, 5, 100, 100]], np.float32)
    keep = nms(boxes, np.array([.8, .9], np.float32), np.array([0, 0]), iou=.45)
    assert keep.tolist() == [1]


def test_nms_keeps_overlap_different_class():
    boxes = np.array([[0, 0, 100, 100], [5, 5, 100, 100]], np.float32)
    keep = nms(boxes, np.array([.8, .9], np.float32), np.array([0, 1]), iou=.45)
    assert keep.tolist() == [1, 0]


def test_nms_keeps_separate_boxes():
    boxes = np.array([[0, 0, 10, 10], [50, 50, 60, 60]], np.float32)
    assert nms(boxes, np.array([.5, .6], np.float32), np.array([0, 0]), iou=.45).tolist() == [1, 0]


@pytest.fixture(scope="module")
def detector():
    return Detector(locate(str(MODEL)))


def test_detector_finds_bus_and_person(detector):
    img = cv2.imread(str(HERE / "data" / "bus.jpg"))
    dets = detector.detect(img)
    names = {d.name for d in dets}
    assert {"bus", "person"} <= names
    h, w = img.shape[:2]
    for d in dets:
        assert d.conf >= .25
        assert 0 <= d.x1 < d.x2 <= w and 0 <= d.y1 < d.y2 <= h
    bus = max((d for d in dets if d.name == "bus"), key=lambda d: d.conf)
    assert bus.conf > .5
    assert detector.last_infer_ms > 0


def test_detector_empty_frame(detector):
    assert detector.detect(np.full((480, 640, 3), 114, np.uint8)) == []
