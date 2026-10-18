"""Where the NCNN model is: --model, else the first complete default dir.

A model dir holds what `yolo export format=ncnn` writes: model.ncnn.param,
model.ncnn.bin and metadata.yaml (class names, input size).
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

# /var/lib first: a model copied there with scp replaces the one in the image.
DEFAULT_DIRS = ("/var/lib/rpi5os-vision/model", "/usr/share/rpi5os-vision/model")
FILES = ("model.ncnn.param", "model.ncnn.bin", "metadata.yaml")


class ModelNotFound(Exception):
    pass


@dataclass(frozen=True)
class ModelInfo:
    dir: Path
    param: Path
    bin: Path
    names: list
    imgsz: int


def _missing(d):
    return [f for f in FILES if not (d / f).is_file()]


def _load(d):
    meta = yaml.safe_load((d / "metadata.yaml").read_text()) or {}
    names = meta.get("names") or {}
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names, key=int)]
    imgsz = meta.get("imgsz")
    if isinstance(imgsz, (list, tuple)):
        if len(imgsz) != 2 or imgsz[0] != imgsz[1]:
            raise ModelNotFound(f"{d}/metadata.yaml: imgsz {imgsz} не квадратний")
        imgsz = imgsz[0]
    if not isinstance(imgsz, int) or not names:
        raise ModelNotFound(f"{d}/metadata.yaml: немає names або imgsz")
    return ModelInfo(d, d / FILES[0], d / FILES[1], list(names), imgsz)


def locate(explicit=None, dirs=DEFAULT_DIRS):
    if explicit:
        d = Path(explicit)
        missing = _missing(d)
        if missing:
            raise ModelNotFound(f"у {d} немає {', '.join(missing)}")
        return _load(d)
    for s in dirs:
        d = Path(s)
        if not _missing(d):
            return _load(d)
    raise ModelNotFound("модель не знайдено; шукав у: " + ", ".join(dirs))


def validate_class(info, target_class):
    if target_class and target_class not in info.names:
        raise ValueError(f"класу {target_class!r} немає в моделі; є: {', '.join(info.names)}")
