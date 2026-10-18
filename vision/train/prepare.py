#!/usr/bin/env python3
"""Label Studio "YOLO with Images" export → YOLO dataset for training.

  prepare.py EXPORT.zip OUT [--max 1600] [--val 0.2] [--test SESSION ...]

Each image is rotated by its EXIF orientation (phones store rotation there;
Label Studio shows the rotated picture, so the boxes refer to it), shrunk to
--max px on the longer side and saved as JPEG; labels are copied as they are
(YOLO coordinates are relative). Images of a --test session go to test whole,
the rest is split train/val at random with a fixed seed.

A session is the sNN_<place> prefix of a file name (s03_lamp_0042.jpg →
s03_lamp); names without it (IMG..., 20261018-...) have no session.
"""
import argparse
import random
import re
import shutil
import sys
import zipfile
from pathlib import Path

import yaml
from PIL import Image, ImageOps

IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LS_PREFIX = re.compile(r"^[0-9a-f]{8}__")
SESSION = re.compile(r"^(s\d+_[^_]+)_")


def session_of(name):
    m = SESSION.match(LS_PREFIX.sub("", Path(name).name))
    return m.group(1) if m else ""


def assign(names, test_sessions, val, seed):
    """name → train | val | test; the same for the same set of names."""
    names = sorted(names)
    split = {n: "test" for n in names if session_of(n) in test_sessions}
    rest = [n for n in names if n not in split]
    random.Random(seed).shuffle(rest)
    n_val = round(len(rest) * val)
    split.update({n: "val" for n in rest[:n_val]})
    split.update({n: "train" for n in rest[n_val:]})
    return split


def safe_stem(name):
    return re.sub(r"\s+", "_", Path(name).stem)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("export", help="zip з Label Studio (YOLO with Images)")
    ap.add_argument("out", help="тека датасету (буде створена)")
    ap.add_argument("--max", type=int, default=1600, help="довша сторона, px")
    ap.add_argument("--val", type=float, default=0.2, help="частка val серед не-test фото")
    ap.add_argument("--test", action="append", default=[], metavar="SESSION")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="перезаписати наявну теку OUT")
    a = ap.parse_args(argv)

    out = Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):
        if not a.force:
            sys.exit(f"prepare: {out} не порожня (--force, щоб перезаписати)")
        shutil.rmtree(out)

    z = zipfile.ZipFile(a.export)
    names = [n for n in z.namelist() if n.startswith("images/") and Path(n).suffix.lower() in IMAGES]
    labels = {Path(n).stem: n for n in z.namelist() if n.startswith("labels/") and n.endswith(".txt")}
    missing = [n for n in names if Path(n).stem not in labels]
    if missing:
        sys.exit(f"prepare: немає міток для {len(missing)} фото, напр. {missing[0]}")
    classes = [c.strip() for c in z.read("classes.txt").decode().splitlines() if c.strip()]

    split = assign([Path(n).name for n in names], set(a.test), a.val, a.seed)
    counts, negatives = {}, 0
    for n in names:
        s = split[Path(n).name]
        stem = safe_stem(n)
        (out / "images" / s).mkdir(parents=True, exist_ok=True)
        (out / "labels" / s).mkdir(parents=True, exist_ok=True)
        with z.open(n) as f:
            img = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        if max(img.size) > a.max:
            img.thumbnail((a.max, a.max), Image.LANCZOS)
        img.save(out / "images" / s / f"{stem}.jpg", "JPEG", quality=92)
        label = z.read(labels[Path(n).stem]).decode()
        negatives += not label.strip()
        (out / "labels" / s / f"{stem}.txt").write_text(label)
        counts[s] = counts.get(s, 0) + 1

    data = {"path": str(out), "train": "images/train",
            "val": "images/val" if counts.get("val") else "images/train",
            "names": dict(enumerate(classes))}
    if counts.get("test"):
        data["test"] = "images/test"
    (out / "data.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    print(f"{out}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
          + f"; без об'єкта {negatives}; класи: {', '.join(classes)}")


if __name__ == "__main__":
    main()
