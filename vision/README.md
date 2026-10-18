# vision/: розпізнавання предмета камерою (YOLO11n → NCNN)

Дизайн: [`docs/specs/2026-10-18-vision-design.md`](../docs/specs/2026-10-18-vision-design.md).

| Тека | Що |
| --- | --- |
| `rpi5os_vision/` | Python-пакет для Pi: камера, ncnn-детектор, положення цілі, метрики, MJPEG-стрім, команда `rpi5os-detect` |
| `models/current/` | модель, яку бере детектор (`model.ncnn.param`, `model.ncnn.bin`, `metadata.yaml`) |
| `train/` | тільки ПК: підготовка датасету, тренування, оцінка, експорт |
| `tests/` | pytest |

## Запуск на Raspberry Pi OS (базовий рівень)

Один раз на Pi (Raspberry Pi OS trixie): OpenCV з apt, ncnn у venv **без
залежностей** (numpy вже системний):

```bash
sudo apt install -y python3-opencv python3-numpy python3-yaml
python3 -m venv --system-site-packages ~/venv && ~/venv/bin/pip install --no-deps ncnn==1.0.20260526
```

З ПК (корінь репо, Git Bash або WSL) — пакет і моделі:

```bash
tar -C vision -cf - rpi5os_vision models | ssh <user>@<pi> 'rm -rf ~/vision && mkdir ~/vision && tar -C ~/vision -xf -'
```

На Pi. Камеру тримає один процес, тож спершу `cam stop`:

```bash
cam stop
cd ~/vision && ~/venv/bin/python -m rpi5os_vision.run --model models/current \
    --target-class duck_pirate --stream 8000 --csv perf.csv
```

У браузері `http://<pi>.local:8000/` — кадр з рамкою: зелена — ціль, синя —
інші класи, жовтий хрестик — центр кадру і лінія до цілі, внизу `dx/dy`
(−1 — лівий/верхній край, +1 — правий/нижній). У консолі раз на секунду:

```text
fps=28.0 infer=30ms cpu=189% sys=50% rss=177MB temp=58°C det=1 dx=-0.42
```

`cpu` — цей процес у % одного ядра (4 ядра = 400%), `sys` — уся система.
Ctrl+C — вихід; потім `cam stream`, якщо потрібен звичайний стрім.

### Заміри (Pi 5 8 ГБ, IMX219 640×480 30 fps, duck-v1)

Типово ncnn працює на **2 потоках** (`--threads`). На 4 потоках Pi 5 під
навантаженням вимикався: короткі піки струму ядра до 9,2 А (PMIC,
`vcgencmd pmic_read_adc`), червоний LED без попереджень. На 2 потоках пік
5,7 А.

| Модель | Потоки | Де | Стрім | FPS | Інференс | CPU процесу | CPU системи | RAM | °C |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 416 | **2** | rpi5os 1.2.0 (SD), `rpi5os-detect` | ні | 30,0 | 30 мс | 197% | 51% | 89 МБ | 54 |
| 416 | **2** | Raspberry Pi OS | ні, 60 с | 28,0 | 30 мс | 189% | 50% | 177 МБ | 58 |
| 416 | **2** | Raspberry Pi OS | так, глядач у браузері, 15 хв | 22,5 | 30 мс | ~155% | 42% | 190 МБ | 55 |
| 416 | **2** | rpi5os 1.2.0, ROS (`detector_node`) | так | 25 | 31 мс | — | — | — | — |
| 416 | 4 | Raspberry Pi OS | ні, 60 с | 30,0 | 24 мс | 307% | 78% | 179 МБ | 62 |
| 320 | 3 | Raspberry Pi OS | ні, 60 с | 29,9 | 16 мс | 163% | 43% | 172 МБ | 55 |

Рядок з 4 потоками лишився для порівняння: так швидше, але саме так Pi
вимикався. Стеля 30 fps — це `rpicam-vid`; стрім із рамками (малювання +
JPEG) забирає кілька fps. Throttling у всіх замірах — `0x0`.

**Ліцензія моделі.** Ваги YOLO11 донавчені з Ultralytics — AGPL-3.0 (так
записано і в `metadata.yaml`); код `rpi5os_vision` — MIT.

## Розробка і тести (WSL Ubuntu-24.04)

numpy і OpenCV беремо системні (з ними зібраний ROS 2 Jazzy), ncnn — з PyPI
**без залежностей**: інакше pip ставить у `~/.local` свої numpy 2.x і
opencv-python, і вони перекривають системні.

```bash
sudo apt install -y python3-venv python3-opencv python3-numpy python3-yaml python3-pytest
pip install --user --break-system-packages --no-deps ncnn==1.0.20260526
cd vision && python3 -m pytest -q
```
