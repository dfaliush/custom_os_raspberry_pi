import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
import evaluate  # noqa: E402


def test_iou():
    assert evaluate.iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert evaluate.iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3)
    assert evaluate.iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0.0


def test_match_perfect():
    gts = {"a": [(0, 0, 10, 10)], "b": [(0, 0, 10, 10)]}
    preds = {"a": [((0, 0, 10, 10), .9)], "b": [((1, 1, 10, 10), .8)]}
    r = evaluate.match(gts, preds, conf=.25)
    assert r["ap50"] == pytest.approx(1.0, abs=0.01)
    assert (r["tp"], r["fp"], r["fn"]) == (2, 0, 0)


def test_match_missed_and_false_positive():
    gts = {"a": [(0, 0, 10, 10)], "b": [(0, 0, 10, 10)], "neg": []}
    preds = {"a": [((0, 0, 10, 10), .9)], "b": [], "neg": [((0, 0, 5, 5), .7)]}
    r = evaluate.match(gts, preds, conf=.25)
    assert (r["tp"], r["fp"], r["fn"]) == (1, 1, 1)
    assert r["precision"] == .5 and r["recall"] == .5
    assert r["fp_images"] == ["neg"] and r["fn_images"] == ["b"]
    assert 0.4 < r["ap50"] < 0.6


def test_match_low_conf_counts_only_for_ap():
    gts = {"a": [(0, 0, 10, 10)]}
    preds = {"a": [((0, 0, 10, 10), .1)]}
    r = evaluate.match(gts, preds, conf=.25)
    assert (r["tp"], r["fn"]) == (0, 1)
    assert r["ap50"] == pytest.approx(1.0, abs=0.01)


def test_yolo_label_to_xyxy():
    assert evaluate.yolo_to_xyxy("0 0.5 0.5 0.2 0.4", 100, 50) == (40.0, 15.0, 60.0, 35.0)
