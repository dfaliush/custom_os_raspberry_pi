import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
import export  # noqa: E402


def test_clean_metadata_drops_home_path():
    text = ("description: Ultralytics YOLO11n model trained on "
            "/home/dmytro/vision-work/datasets/duck-v1/data.yaml\nauthor: Ultralytics\n")
    out = export.clean_metadata(text)
    assert "/home/" not in out and "dmytro" not in out
    assert "trained on duck-v1/data.yaml" in out
    assert "author: Ultralytics" in out


def test_clean_metadata_keeps_other_fields():
    text = "names:\n  0: duck_pirate\nimgsz:\n- 416\n- 416\n"
    assert export.clean_metadata(text) == text
