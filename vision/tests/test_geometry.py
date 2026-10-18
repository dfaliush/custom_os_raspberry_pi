import pytest

from rpi5os_vision.geometry import Detection, Target, target_from


def test_center_is_zero():
    t = target_from([Detection(270, 190, 370, 290, .9, 0, "cup")], 640, 480)
    assert (t.detected, t.dx, t.dy) == (True, 0.0, 0.0)
    assert t.area == pytest.approx(100 * 100 / (640 * 480))
    assert (t.confidence, t.class_name) == (.9, "cup")


def test_left_is_negative():
    assert target_from([Detection(0, 200, 64, 280, .9, 0, "cup")], 640, 480).dx == pytest.approx(-0.9)


def test_below_center_is_positive_dy():
    assert target_from([Detection(300, 400, 340, 480, .9, 0, "cup")], 640, 480).dy == pytest.approx(0.833, abs=1e-3)


def test_picks_highest_conf_of_target_class():
    d = [Detection(0, 0, 10, 10, .95, 0, "person"),
         Detection(600, 0, 640, 10, .7, 41, "cup"),
         Detection(0, 0, 10, 10, .5, 41, "cup")]
    t = target_from(d, 640, 480, "cup")
    assert (t.confidence, t.class_name) == (.7, "cup")


def test_any_class_when_target_empty():
    d = [Detection(0, 0, 10, 10, .5, 41, "cup"), Detection(0, 0, 10, 10, .95, 0, "person")]
    assert target_from(d, 640, 480).class_name == "person"


def test_no_detections():
    assert target_from([], 640, 480) == Target.none()


def test_only_other_classes_is_none():
    assert target_from([Detection(0, 0, 10, 10, .9, 0, "person")], 640, 480, "cup") == Target.none()


def test_box_outside_frame_is_clamped():
    assert target_from([Detection(700, 0, 800, 10, .9, 0, "x")], 640, 480).dx == 1.0
