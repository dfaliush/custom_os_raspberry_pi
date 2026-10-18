from pathlib import Path

import pytest
import yaml

from rpi5os_vision.model import ModelNotFound, locate, validate_class


def make_model(d, names=None, imgsz=(416, 416), with_bin=True):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.ncnn.param").write_text("7767517\n")
    if with_bin:
        (d / "model.ncnn.bin").write_bytes(b"\0" * 8)
    meta = {"names": names if names is not None else {0: "cup"}, "imgsz": list(imgsz)}
    (d / "metadata.yaml").write_text(yaml.safe_dump(meta))
    return d


def test_explicit_dir_wins(tmp_path):
    a, b = make_model(tmp_path / "a"), make_model(tmp_path / "b")
    info = locate(str(a), dirs=(str(b),))
    assert info.dir == a
    assert info.param == a / "model.ncnn.param" and info.bin == a / "model.ncnn.bin"
    assert (info.names, info.imgsz) == (["cup"], 416)


def test_first_existing_default(tmp_path):
    b = make_model(tmp_path / "b")
    assert locate(None, dirs=(str(tmp_path / "missing"), str(b))).dir == b


def test_explicit_incomplete_raises(tmp_path):
    a = make_model(tmp_path / "a", with_bin=False)
    b = make_model(tmp_path / "b")
    with pytest.raises(ModelNotFound) as e:
        locate(str(a), dirs=(str(b),))
    assert str(a) in str(e.value)


def test_nothing_found_lists_paths(tmp_path):
    dirs = (str(tmp_path / "x"), str(tmp_path / "y"))
    with pytest.raises(ModelNotFound) as e:
        locate(None, dirs=dirs)
    assert all(d in str(e.value) for d in dirs)


def test_non_square_imgsz_raises(tmp_path):
    a = make_model(tmp_path / "a", imgsz=(416, 320))
    with pytest.raises(ModelNotFound):
        locate(str(a))


def test_int_imgsz(tmp_path):
    a = make_model(tmp_path / "a")
    (a / "metadata.yaml").write_text(yaml.safe_dump({"names": {0: "cup"}, "imgsz": 320}))
    assert locate(str(a)).imgsz == 320


def test_names_ordered_by_index(tmp_path):
    a = make_model(tmp_path / "a", names={1: "b", 0: "a"})
    assert locate(str(a)).names == ["a", "b"]


def test_validate_class_unknown(tmp_path):
    info = locate(str(make_model(tmp_path / "a", names={0: "duck_pirate"})))
    with pytest.raises(ValueError) as e:
        validate_class(info, "mug")
    assert "mug" in str(e.value) and "duck_pirate" in str(e.value)


def test_validate_class_known_and_empty(tmp_path):
    info = locate(str(make_model(tmp_path / "a", names={0: "duck_pirate"})))
    validate_class(info, "duck_pirate")
    validate_class(info, "")
