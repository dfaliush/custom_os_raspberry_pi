#!/usr/bin/env python3
"""Fine-tune YOLO11n (COCO weights) on a dataset made by prepare.py.

  train.py DATASET/data.yaml [--imgsz 416] [--epochs 100] [--name NAME]

Runs go to ~/vision-work/runs/<name>: weights/best.pt, results.csv, plots.
"""
import argparse
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("data", help="data.yaml з prepare.py")
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=16)
    # 20 is too short for ~100 photos: the val metric is noisy for the first
    # epochs, and a lucky epoch 1 stopped a 320 run at epoch 21 with mAP50 0.11.
    ap.add_argument("--patience", type=int, default=50, help="епох без покращення до зупинки")
    ap.add_argument("--model", default="yolo11n.pt", help="стартові ваги")
    ap.add_argument("--name", help="назва запуску; типово <модель>-<imgsz>")
    ap.add_argument("--project", default=str(Path.home() / "vision-work" / "runs"))
    a = ap.parse_args(argv)

    from ultralytics import YOLO

    name = a.name or f"{Path(a.model).stem}-{a.imgsz}"
    model = YOLO(a.model)
    model.train(data=str(Path(a.data).resolve()), imgsz=a.imgsz, epochs=a.epochs, batch=a.batch,
                patience=a.patience, seed=0, deterministic=True, project=a.project, name=name, exist_ok=False)
    print(f"готово: {model.trainer.save_dir}")


if __name__ == "__main__":
    main()
