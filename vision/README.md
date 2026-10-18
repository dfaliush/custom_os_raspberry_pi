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
fps=30.0 infer=24ms cpu=314% sys=80% rss=193MB temp=62°C det=1 dx=0.34
```

`cpu` — цей процес у % одного ядра (4 ядра = 400%), `sys` — уся система.
Ctrl+C — вихід; потім `cam stream`, якщо потрібен звичайний стрім.

### Заміри (Pi 5 8 ГБ, IMX219 640×480 30 fps, duck-v1, по 60 с)

| Модель | Стрім | FPS | Інференс | CPU процесу | CPU системи | RAM | °C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 416 | так | 29,8 | 25 мс | 313% | 80% | 193 МБ | 59 |
| 416 | ні | 30,0 | 24 мс | 307% | 78% | 179 МБ | 62 |
| 320 | ні | 30,0 | 14 мс | 189% | 48% | 173 МБ | 58 |

Обидві моделі встигають за камерою (30 fps — стеля `rpicam-vid`). 320 бере
на третину менше CPU; throttling — `0x0`.

## Розробка і тести (WSL Ubuntu-24.04)

numpy і OpenCV беремо системні (з ними зібраний ROS 2 Jazzy), ncnn — з PyPI
**без залежностей**: інакше pip ставить у `~/.local` свої numpy 2.x і
opencv-python, і вони перекривають системні.

```bash
sudo apt install -y python3-venv python3-opencv python3-numpy python3-yaml python3-pytest
pip install --user --break-system-packages --no-deps ncnn==1.0.20260526
cd vision && python3 -m pytest -q
```
