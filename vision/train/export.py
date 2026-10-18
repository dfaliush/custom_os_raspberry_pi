#!/usr/bin/env python3
"""best.pt → NCNN (weights/best_ncnn_model), optionally copied to the model dir the Pi uses.

  export.py RUN_DIR [--imgsz N] [--out vision/models/current]

--imgsz defaults to the size the run was trained with. --out gets the three
files rpi5os_vision needs: model.ncnn.param, model.ncnn.bin, metadata.yaml.
"""
import argparse
import shutil
from pathlib import Path

FILES = ("model.ncnn.param", "model.ncnn.bin", "metadata.yaml")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", help="тека тренування")
    ap.add_argument("--imgsz", type=int)
    ap.add_argument("--out", help="куди скопіювати модель (напр. vision/models/current)")
    a = ap.parse_args(argv)

    import yaml
    from ultralytics import YOLO

    run = Path(a.run)
    imgsz = a.imgsz or yaml.safe_load((run / "args.yaml").read_text())["imgsz"]
    path = Path(YOLO(str(run / "weights" / "best.pt")).export(format="ncnn", imgsz=imgsz))
    print(f"NCNN: {path} ({imgsz}px)")
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        for f in FILES:
            shutil.copy2(path / f, out / f)
        print(f"скопійовано в {out}")


if __name__ == "__main__":
    main()
