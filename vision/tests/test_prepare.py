import sys
import zipfile
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
import prepare  # noqa: E402


def test_session_of_pi():
    assert prepare.session_of("s03_lamp_0042.jpg") == "s03_lamp"


def test_session_of_label_studio_prefix():
    assert prepare.session_of("a0aa4a82__s01_kitchen_0007.jpg") == "s01_kitchen"


def test_session_of_none():
    assert prepare.session_of("a0aa4a82__IMG20261018183506.jpg") == ""
    assert prepare.session_of("20261018-193059.jpg") == ""


def test_assign_test_session_whole_and_val_fraction():
    names = [f"s01_a_{i:02d}.jpg" for i in range(10)] + [f"s02_b_{i:02d}.jpg" for i in range(5)]
    split = prepare.assign(names, test_sessions={"s02_b"}, val=0.2, seed=0)
    assert {n for n, s in split.items() if s == "test"} == set(names[10:])
    assert sum(s == "val" for s in split.values()) == 2
    assert split == prepare.assign(list(reversed(names)), {"s02_b"}, 0.2, 0)   # deterministic


def make_export(path, items):
    """items: name → (size, label text, exif orientation or None)."""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("classes.txt", "duck_pirate\n")
        for name, (size, label, orient) in items.items():
            img = Image.new("RGB", size, (200, 180, 0))
            exif = Image.Exif()
            if orient:
                exif[274] = orient
            p = path.parent / name
            img.save(p, "JPEG", exif=exif.tobytes())
            z.write(p, f"images/{name}")
            z.writestr(f"labels/{Path(name).stem}.txt", label)


def test_prepare_builds_dataset(tmp_path):
    zp = tmp_path / "export.zip"
    items = {f"h{i:07d}__IMG{i}.jpg": ((3000, 4000), "0 0.5 0.5 0.2 0.3\n", None) for i in range(10)}
    items["hneg0000__IMGneg.jpg"] = ((400, 300), "", None)
    make_export(zp, items)
    out = tmp_path / "ds"
    prepare.main([str(zp), str(out), "--max", "1600"])
    data = yaml.safe_load((out / "data.yaml").read_text())
    assert data["names"] == {0: "duck_pirate"} and data["path"] == str(out)
    imgs = list((out / "images").rglob("*.jpg"))
    assert len(imgs) == 11
    assert {p.parent.name for p in imgs} == {"train", "val"}
    big = Image.open(next(p for p in imgs if "neg" not in p.name))
    assert max(big.size) == 1600
    neg = next(p for p in imgs if "neg" in p.name)
    lab = out / "labels" / neg.parent.name / (neg.stem + ".txt")
    assert lab.exists() and lab.read_text() == ""


def test_prepare_applies_exif_rotation(tmp_path):
    zp = tmp_path / "export.zip"
    make_export(zp, {"r__IMG.jpg": ((40, 20), "0 0.5 0.5 0.1 0.1\n", 6)})
    out = tmp_path / "ds"
    prepare.main([str(zp), str(out), "--val", "0"])
    img = Image.open(next((out / "images").rglob("*.jpg")))
    assert img.size == (20, 40)
    assert img.getexif().get(274) in (None, 1)


def test_prepare_refuses_missing_label(tmp_path):
    zp = tmp_path / "export.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("classes.txt", "duck_pirate\n")
        b = tmp_path / "x.jpg"
        Image.new("RGB", (8, 8)).save(b)
        z.write(b, "images/x.jpg")
    with pytest.raises(SystemExit):
        prepare.main([str(zp), str(tmp_path / "ds")])
