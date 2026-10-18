#!/usr/bin/env python3
"""Quality of a trained model: .pt via Ultralytics and the NCNN export via our detector.

  evaluate.py RUN_DIR [--split val|test] [--conf 0.25]

RUN_DIR is what train.py made (weights/best.pt, weights/best_ncnn_model from
export.py, args.yaml). Writes RUN_DIR/eval/report.md and pictures with boxes:
white — the label, green — the model; eval/fp and eval/fn hold the mistakes.
The NCNN numbers come from rpi5os_vision, the code that runs on the Pi, so
they also check the export and our pre/post-processing.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

IOU = 0.5


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def yolo_to_xyxy(line, w, h):
    _, cx, cy, bw, bh = (float(v) for v in line.split()[:5])
    return ((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h)


def match(gts, preds, conf):
    """gts: image → [box]; preds: image → [(box, score)]. One class.

    ap50 uses every prediction (101-point interpolation, as COCO and
    Ultralytics); tp/fp/fn and the image lists only those with score ≥ conf.
    """
    ranked, n_gt = [], sum(len(v) for v in gts.values())
    tp = fp = fn = 0
    fp_images, fn_images = [], []
    for img, gt in gts.items():
        used = set()
        for box, score in sorted(preds.get(img, []), key=lambda p: -p[1]):
            best, best_iou = None, IOU
            for i, g in enumerate(gt):
                v = iou(box, g)
                if i not in used and v >= best_iou:
                    best, best_iou = i, v
            if best is not None:
                used.add(best)
            ranked.append((score, best is not None))
        kept = [p for p in preds.get(img, []) if p[1] >= conf]
        used_c = set()
        img_fp = 0
        for box, _ in sorted(kept, key=lambda p: -p[1]):
            hit = next((i for i, g in enumerate(gt) if i not in used_c and iou(box, g) >= IOU), None)
            if hit is None:
                img_fp += 1
            else:
                used_c.add(hit)
        tp, fp, fn = tp + len(used_c), fp + img_fp, fn + len(gt) - len(used_c)
        if img_fp:
            fp_images.append(img)
        if len(used_c) < len(gt):
            fn_images.append(img)

    ranked.sort(key=lambda r: -r[0])
    hits = np.array([h for _, h in ranked], dtype=float)
    ctp, cfp = np.cumsum(hits), np.cumsum(1 - hits)
    recall = ctp / n_gt if n_gt else ctp * 0
    precision = ctp / np.maximum(ctp + cfp, 1e-9)
    ap = np.mean([precision[recall >= r].max() if (recall >= r).any() else 0.0
                  for r in np.linspace(0, 1, 101)]) if len(hits) else 0.0
    return {"ap50": float(ap), "tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
            "fp_images": fp_images, "fn_images": fn_images}


def draw(path, gt, preds, conf, out):
    import cv2
    img = cv2.imread(str(path))
    for g in gt:
        cv2.rectangle(img, (int(g[0]), int(g[1])), (int(g[2]), int(g[3])), (255, 255, 255), 3)
    for box, score in preds:
        if score >= conf:
            p1 = (int(box[0]), int(box[1]))
            cv2.rectangle(img, p1, (int(box[2]), int(box[3])), (0, 220, 0), 3)
            cv2.putText(img, f"{score:.2f}", (p1[0], max(p1[1] - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 220, 0), 2)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", help="тека тренування (runs/…/<name>)")
    ap.add_argument("--split", default="val", choices=["val", "test"])
    ap.add_argument("--conf", type=float, default=0.25)
    a = ap.parse_args(argv)

    import cv2
    import yaml
    from ultralytics import YOLO

    from rpi5os_vision.model import locate
    from rpi5os_vision.yolo_ncnn import Detector

    run = Path(a.run)
    data = Path(yaml.safe_load((run / "args.yaml").read_text())["data"])
    ds = yaml.safe_load(data.read_text())
    images = sorted((Path(ds["path"]) / ds[a.split]).glob("*.jpg"))
    if not images:
        sys.exit(f"evaluate: немає фото у split {a.split}")

    pt = YOLO(str(run / "weights" / "best.pt")).val(data=str(data), split=a.split, plots=False, verbose=False)
    det = Detector(locate(str(run / "weights" / "best_ncnn_model")), conf=0.001)

    gts, preds, times = {}, {}, []
    for p in images:
        h, w = cv2.imread(str(p)).shape[:2]
        lab = Path(str(p).replace("/images/", "/labels/")).with_suffix(".txt")
        gts[p.name] = [yolo_to_xyxy(line, w, h) for line in lab.read_text().splitlines() if line.strip()]
        dets = det.detect(cv2.imread(str(p)))
        times.append(det.last_infer_ms)
        preds[p.name] = [((d.x1, d.y1, d.x2, d.y2), d.conf) for d in dets]
    r = match(gts, preds, a.conf)

    ev = run / "eval"
    for p in images:
        kind = "fp" if p.name in r["fp_images"] else "fn" if p.name in r["fn_images"] else "ok"
        draw(p, gts[p.name], preds[p.name], a.conf, ev / kind / p.name)

    report = f"""# Оцінка моделі: {run.name}

Split `{a.split}`: {len(images)} фото, {sum(len(v) for v in gts.values())} рамок,
без об'єкта {sum(not v for v in gts.values())}. Поріг впевненості {a.conf}.

| Модель | mAP50 | mAP50-95 | precision | recall |
| --- | --- | --- | --- | --- |
| `best.pt` (Ultralytics) | {pt.box.map50:.3f} | {pt.box.map:.3f} | {pt.box.mp:.3f} | {pt.box.mr:.3f} |
| NCNN (rpi5os_vision) | {r['ap50']:.3f} | — | {r['precision']:.3f} | {r['recall']:.3f} |

NCNN при conf {a.conf}: TP {r['tp']}, FP {r['fp']}, FN {r['fn']}; інференс на ПК
{np.mean(times):.1f} мс/кадр (CPU, ncnn).

- Хибні спрацювання (FP): {', '.join(r['fp_images']) or 'немає'}
- Пропуски (FN): {', '.join(r['fn_images']) or 'немає'}

Картинки: `eval/ok`, `eval/fp`, `eval/fn` (біле — розмітка, зелене — модель).
"""
    ev.mkdir(exist_ok=True)
    (ev / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
