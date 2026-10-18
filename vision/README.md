# vision/: розпізнавання предмета камерою (YOLO11n → NCNN)

Дизайн: [`docs/specs/2026-10-18-vision-design.md`](../docs/specs/2026-10-18-vision-design.md).

| Тека | Що |
| --- | --- |
| `rpi5os_vision/` | Python-пакет для Pi: камера, ncnn-детектор, положення цілі, метрики, MJPEG-стрім, команда `rpi5os-detect` |
| `models/current/` | модель, яку бере детектор (`model.ncnn.param`, `model.ncnn.bin`, `metadata.yaml`) |
| `train/` | тільки ПК: підготовка датасету, тренування, оцінка, експорт |
| `tests/` | pytest |

## Розробка і тести (WSL Ubuntu-24.04)

numpy і OpenCV беремо системні (з ними зібраний ROS 2 Jazzy), ncnn — з PyPI
**без залежностей**: інакше pip ставить у `~/.local` свої numpy 2.x і
opencv-python, і вони перекривають системні.

```bash
sudo apt install -y python3-venv python3-opencv python3-numpy python3-yaml python3-pytest
pip install --user --break-system-packages --no-deps ncnn==1.0.20260526
cd vision && python3 -m pytest -q
```
