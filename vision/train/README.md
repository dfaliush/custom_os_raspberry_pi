# Тренування моделі (ПК, WSL Ubuntu-24.04 + NVIDIA GPU)

Від експорту Label Studio до файлів моделі для Pi. Датасет у git не потрапляє:
фото лежать локально, у репо — скрипти й готова модель (`../models/current/`).

## Середовище (один раз)

Ultralytics із PyTorch (CUDA) — окреме venv, щоб не чіпати системний Python,
з яким працює ROS 2:

```bash
python3 -m venv ~/venvs/train
~/venvs/train/bin/pip install -r /mnt/d/git/custom_os_raspberry_pi/vision/train/requirements.txt
~/venvs/train/bin/python -c "import torch; print(torch.cuda.is_available())"   # True
```

Далі `P=~/venvs/train/bin/python; T=/mnt/d/git/custom_os_raspberry_pi/vision/train`.
Робоча тека — `~/vision-work` (ext4: з `/mnt/d` тренування повільніше).

## 1. Датасет із Label Studio

Label Studio → *Export* → **YOLO with Images** → zip. Потім:

```bash
cd ~/vision-work
$P $T/prepare.py /mnt/d/work/iot/yolo_with_images_dataset.zip datasets/duck-v1
# datasets/duck-v1: train 62, val 15; без об'єкта 1; класи: duck_pirate
```

`prepare.py` повертає фото за EXIF (телефон), зменшує довшу сторону до 1600 px,
копіює мітки і розбиває train/val 80/20 з фіксованим seed. Якщо назви фото мають
сесію (`s03_lamp_0042.jpg`), сесію можна цілком віддати на тест:
`--test s03_lamp`. Для нового експорту — нова тека (`duck-v2`) або `--force`.

## 2. Тренування

```bash
$P $T/train.py datasets/duck-v1/data.yaml --imgsz 416 --name duck-v1-416   # ~1 хв на RTX 4070 Ti
```

YOLO11n з вагами COCO донавчається на ваш предмет; результат —
`runs/duck-v1-416/weights/best.pt`, графіки й `results.csv` поруч.
`--patience 50` (типово): на ~100 фото метрика перших епох шумна, і з 20 запуск
на 320 зупинився на 21-й епосі з mAP50 0,11.

## 3. Експорт у NCNN і оцінка

```bash
$P $T/export.py runs/duck-v1-416            # → runs/duck-v1-416/weights/best_ncnn_model
$P $T/evaluate.py runs/duck-v1-416          # → runs/duck-v1-416/eval/report.md
```

`evaluate.py` рахує метрики двічі: для `best.pt` (Ultralytics) і для NCNN через
`rpi5os_vision` — той самий код, що працює на Pi. Якщо NCNN помітно гірший за
`.pt`, зламався експорт або обробка кадру. Картинки з рамками: `eval/ok`,
`eval/fp` (хибні спрацювання), `eval/fn` (пропуски); біле — розмітка, зелене —
модель.

## 4. Модель на Pi

```bash
$P $T/export.py runs/duck-v1-416 --out /mnt/d/git/custom_os_raspberry_pi/vision/models/current
```

Raspberry Pi OS: скопіювати `vision/` на Pi і запустити `rpi5os-detect` (див.
`../README.md`). rpi5os на SD: три файли моделі в `/var/lib/rpi5os-vision/model/`,
потім перезапуск сервісу — перепрошивати не треба.

## Результати

duck-v1: 77 фото (64 телефон, 13 знімків екрана стріму), 1 без об'єкта; val —
15 випадкових фото з того ж набору, тож цифри оптимістичні.

| Модель | `.pt` mAP50 | `.pt` mAP50-95 | NCNN mAP50 | NCNN P / R (conf 0,25) | NCNN на ПК |
| --- | --- | --- | --- | --- | --- |
| duck-v1-416 | 0,995 | 0,821 | 0,991 | 0,94 / 1,00 (1 FP) | 12 мс |
| duck-v1-320 | 0,995 | 0,852 | 1,000 | 1,00 / 1,00 | 8 мс |

Єдина помилка 416 — кадр із камери Pi: качка знайдена лише з 0,42, і поруч хибна
рамка 0,43. На фото з телефону впевненість ~0,9. Модель вчилась майже лише на
телефоні; потрібні кадри з самої камери Pi (кнопка «Фото» у `cam stream`) і
фото без качки.
