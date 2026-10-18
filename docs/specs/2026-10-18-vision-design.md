# rpi5os, ітерація 3: розпізнавання об'єкта камерою (YOLO + NCNN + ROS 2)

Дата: 2026-10-18 · Статус: дизайн погоджено в розмові, spec чекає на перегляд.

## Мета

Власна модель Object Detection для одного обраного предмета, яка працює на
Raspberry Pi 5 з відеопотоком камери в реальному часі. Три рівні:

| Рівень | Що | Де |
| --- | --- | --- |
| базовий | модель натренована і працює з камерою | Raspberry Pi OS (SSD) |
| просунутий | та сама модель у власній ОС | rpi5os-yocto на microSD |
| ускладнений | ROS 2: відео між нодами, положення відносно центру кадру, нода рішень | rpi5os-yocto на microSD |

Мотори не підключаємо: нода рішень публікує команду (`/cmd_vel`), але її
ніхто не виконує.

Вихідні вимоги: завдання курсу і лекція «Практичне застосування AI та Computer
Vision на Raspberry Pi 5» (pipeline, Perception → Decision → Control, топологія
нод, QA-чеклист). Звідти ж критерії приймання нижче.

## Безпека SSD

Pi стартує Raspberry Pi OS з NVMe SSD; ця система не перезаписується ніколи.

- Образ rpi5os пишеться **тільки** на microSD і **тільки** через
  `buildroot/scripts/pi/flash-sd.sh` (ціль `/dev/mmcblk0`, `TRAN=mmc`, `/` і
  `/boot/firmware` не на цілі, образ у `/dev/shm`, звірка sha256). Нових
  скриптів запису не з'являється.
- Перед кожним записом картки: вивід `lsblk -o NAME,TRAN,SIZE,MOUNTPOINTS` і
  `findmnt /` показується людині, запис після її підтвердження.
- Образ не монтує NVMe і не пише на нього; vision-код пише лише в rootfs SD.
- Критерій приймання V9: після тестів на SD Pi стартує з SSD як раніше.

## Залізо

- Raspberry Pi 5 + M.2 HAT+ (SSD), камера IMX219 (8 Мп, FOV 79.3°, сторонній
  модуль) у роз'ємі **CAM/DISP 0**.
- Перевірено на Raspberry Pi OS: `rpicam-hello --list-cameras` бачить imx219,
  `rpicam-vid` пише відео.

## Рішення

| Рішення | Чому |
| --- | --- |
| Ultralytics **YOLO11n**, fine-tune з COCO, `imgsz` 416 (порівняння з 320) | найменша модель сімейства; один великий предмет не потребує 640 |
| NCNN на Pi (рекомендація завдання), без PyTorch/Ultralytics на Pi | ncnn легкий і швидкий на ARM; Ultralytics потрібен лише на ПК |
| Власний детектор на Python: ncnn + numpy + OpenCV | один код для RPi OS, Yocto і ROS-нод; pre/post-processing ~150 рядків |
| Камера через `rpicam-vid --codec yuv420 -o -` у пайп | працює однаково на RPi OS і в Yocto; не потрібен picamera2 (його немає в шарах) і не потрібен libav |
| Ширина кадру кратна 64 (640×480) | рядки yuv420 без вирівнювання, кадр = W·H·3/2 байт |
| Перегляд: MJPEG-стрім із рамками на `http://<pi>:8000` | у Pi немає монітора, в образі немає GUI; браузер є на будь-якому ПК |
| Розмітка в Label Studio на ПК (WSL), експорт «YOLO with Images» | локально, без акаунтів; не входить в образ |
| Датасет **лише локально** (`D:\work\iot\camera\photo_storage`) | на фото можуть бути приватні речі; у git і релізах — код, модель, метрики |
| Модель у git: `vision/models/current/` (~5 МБ) | образ збирається без зовнішніх завантажень; спершу COCO yolo11n, потім своя |
| Заміна моделі без перепрошивки: `/var/lib/rpi5os-vision/model/` має пріоритет | нова модель = `scp` двох файлів |
| ROS: власні `camera_node` і повідомлення `TargetOffset` | без `camera_ros` (тягне другу libcamera) і без `cv_bridge` (кадр у numpy через `frombuffer`) |

Ліцензія: Ultralytics і ваги YOLO11 — AGPL-3.0. Код на Pi Ultralytics не
імпортує; модель, натреновану ним, публікуємо разом з кодом у відкритому репо.

## Склад

```text
vision/
├─ rpi5os_vision/             # Python-пакет, спільний для всіх рівнів
│  ├─ camera.py               # RpicamSource: rpicam-vid → BGR, лише останній кадр
│  ├─ source.py               # FileSource: тека зображень / відео (replay, тести)
│  ├─ yolo_ncnn.py            # Detector: letterbox → ncnn → decode → NMS (numpy)
│  ├─ geometry.py             # TargetOffset: dx, dy ∈ [-1, 1], area
│  ├─ model.py                # пошук моделі: /var/lib/... → /usr/share/... → --model
│  ├─ metrics.py              # FPS, inference ms, CPU% (процес/система), RSS, °C, throttling
│  ├─ stream.py               # MJPEG HTTP-сервер (останній кадр із рамками)
│  └─ run.py                  # CLI rpi5os-detect
├─ pyproject.toml
├─ tests/                     # pytest: letterbox, decode, NMS, geometry, source, model
├─ models/current/            # model.ncnn.param, model.ncnn.bin, metadata.yaml
└─ train/                     # тільки ПК (WSL + CUDA)
   ├─ requirements.txt        # ultralytics, ncnn — прибиті версії
   ├─ prepare.py              # auto-orient + resize ≤1600 px (фото з телефону)
   ├─ split.py                # експорт Label Studio → train/val/test за сесіями
   ├─ train.py
   ├─ evaluate.py             # .pt і NCNN (наш детектор) на test → report.md + картинки
   └─ export.py               # → models/current/

ros2/
├─ vision_interfaces/         # ament_cmake: msg/TargetOffset.msg
└─ vision_pkg/                # ament_python: camera_node, detector_node, decision_node, launch

yocto/meta-rpi5os-ros/        # (існуючий шар)
├─ recipes-multimedia/ncnn/   # ncnn_<тег>.bb
├─ recipes-vision/            # rpi5os-vision (пакет + модель + rpi5os-detect)
├─ recipes-ros/               # vision-interfaces, vision-pkg
└─ recipes-core/rpi5os-ros/   # + rpi5os-vision.service
```

Vision-рецепти живуть у `meta-rpi5os-ros`, а не в окремому шарі: образ один,
окремий шар без ROS ніхто не збиратиме.

## Детектор (`rpi5os_vision`)

- **Кадри.** `RpicamSource(width=640, height=480, fps=30)` запускає
  `rpicam-vid -t 0 -n --codec yuv420 --width W --height H --framerate F -o -`,
  окремий потік читає по `W*H*3/2` байт і перетворює I420 → BGR. Зберігається
  тільки останній кадр: інференс повільніший за камеру, черга не росте.
  EOF або вихід `rpicam-vid` → `CameraLost`. `FileSource` дає той самий
  інтерфейс із теки/відео.
- **Детектор.** `Detector(model_dir, conf=0.25, iou=0.45, threads=4)`:
  letterbox до `imgsz` з `metadata.yaml`, BGR→RGB, /255, ncnn
  (`in0` → `out0`, форма `(4+nc) × N`), відсів за conf, NMS на numpy, координати
  назад у кадр. Вихід: `[Detection(x1, y1, x2, y2, conf, cls, name)]`.
- **Геометрія.** Для найвпевненішої детекції цільового класу:
  `dx = (cx − W/2)/(W/2)`, `dy = (cy − H/2)/(H/2)`, `area = w·h/(W·H)`.
  `dx < 0` — об'єкт ліворуч.
- **Модель.** Перша існуюча з: `--model`, `/var/lib/rpi5os-vision/model/`,
  `/usr/share/rpi5os-vision/model/`. `metadata.yaml`: `names`, `imgsz`.
- **CLI.** `rpi5os-detect [--model DIR] [--source camera|PATH] [--stream PORT]
  [--csv FILE] [--imgsz N] [--conf X]`. Раз на секунду рядок
  `fps=… infer=…ms cpu=…% sys=…% rss=…MB temp=…°C det=… dx=…`; CSV з тими ж
  полями для звіту.

## Yocto (просунутий рівень)

- `build.sh`: у `BBLAYERS` додається `meta-openembedded/meta-multimedia` (вмикає
  dynamic-layer `meta-raspberrypi`: libcamera з IPA `rpi/pisp`, `libpisp`,
  `libcamera-apps`).
- `PREFERRED_VERSION_libcamera = "0.6.0"` (рецепт `meta-multimedia`):
  `meta-ros` jazzy має власний libcamera 0.7.2, у образі має бути одна.
- `RPI_EXTRA_CONFIG`: `camera_auto_detect=0`, `dtoverlay=imx219,cam0`.
- `PACKAGECONFIG:pn-opencv = "python3 jpeg png"`: без GUI, gstreamer, gphoto2,
  gapi, samples.
- `ncnn`: тег релізу з GitHub, прибитий у рецепті; CMake, `NCNN_VULKAN=OFF`,
  `NCNN_BUILD_TOOLS=OFF`, `NCNN_PYTHON=ON` (модуль у site-packages). Якщо Python
  bindings не зберуться в розумний час — запасний план: C++ детектор з тим самим
  інтерфейсом через ctypes; рішення фіксується в цьому spec.
- `rpi5os-vision`: пакет `rpi5os_vision`, модель у
  `/usr/share/rpi5os-vision/model/`, `/var/lib/rpi5os-vision/model/` (порожня),
  команда `rpi5os-detect`. RDEPENDS: `libcamera-apps python3-numpy
  python3-opencv ncnn python3-pyyaml`.
- `DISTRO_VERSION = "1.2.0"`, реліз `rpi5os-yocto-v1.2.0` тим самим `dist.sh`.

## ROS 2 (ускладнений рівень)

```text
camera_node ──/camera/image_raw──► detector_node ──/target──► decision_node ──► /cmd_vel, /decision
              sensor_msgs/Image              vision_interfaces/TargetOffset     Twist, String
              bgr8 640×480                   header, detected, confidence,
                                             dx, dy, area, class_name
```

- QoS відео: best-effort, depth 1 (`qos_profile_sensor_data`); `/target`:
  reliable, depth 10.
- `camera_node`: `RpicamSource` → `Image`; параметри `width`, `height`, `fps`,
  `source` (`camera` або шлях для replay). Після `CameraLost` — лог і повторний
  запуск `rpicam-vid` раз на 2 с.
- `detector_node`: обробляє лише найсвіжіший кадр; параметри `model_dir`, `conf`,
  `target_class` (порожньо — будь-який), `stream_port` (8000, 0 — вимкнено). На
  кожен оброблений кадр публікує `/target` (також коли `detected=false`). Раз на
  5 с логує FPS і час інференсу.
- `decision_node`: таймер 10 Гц, незалежно від камери. Логіка (слайд 19):

  | Умова | Команда | `/cmd_vel` |
  | --- | --- | --- |
  | `/target` старший за `stale_timeout` (0.5 с) | STOP | 0 |
  | `detected=false` | STOP | 0 |
  | `confidence < conf_threshold` (0.6) | STOP | 0 |
  | `dx < −deadband` (0.15) | TURN_LEFT | `angular.z = +turn_speed` |
  | `dx > +deadband` | TURN_RIGHT | `angular.z = −turn_speed` |
  | інакше | MOVE_FORWARD | `linear.x = forward_speed` |

  Поріг 0.6 — стартове значення (у лекції приклад 0.8); підбирається за V7.
  `/decision` (`std_msgs/String`) — назва команди; лог лише при зміні команди.
  Логіка — чиста функція `decide(target, now, params)`, ноду лише обгортає.
- `vision.launch.py` піднімає три ноди; `rpi5os-vision.service` запускає launch
  на старті (як `rpi5os-counter.service`). `rpi5os-detect` і сервіс не працюють
  одночасно (одна камера): перед CLI — `systemctl stop rpi5os-vision`.

## Помилки і safe state

| Подія | Поведінка |
| --- | --- |
| камера відключена / `rpicam-vid` впав | `camera_node` перезапускає захоплення; кадрів немає → `/target` старіє → STOP |
| `detector_node` впав | `/target` старіє → STOP за ≤0.5 с; systemd перезапускає сервіс, якщо launch завершився |
| модель не знайдена / битий файл | `detector_node` і `rpi5os-detect` завершуються з повідомленням, де шукали |
| перевантаження CPU | `decision_node` тримає 10 Гц: черг немає, детектор пропускає кадри |

## Тестування

- **pytest на ПК** (`vision/tests`): letterbox і зворотне перетворення координат,
  decode на синтетичному тензорі, NMS, geometry на краях кадру, вибір моделі,
  `FileSource`.
- **`decide()`**: по тесту на кожен рядок таблиці рішень і QA-чеклиста.
- **Parity**: `evaluate.py` рахує mAP50 для `.pt` і для NCNN через наш детектор
  на тих самих test-фото; різниця ≤ 2 п.п.
- **ROS на ПК** (WSL, Jazzy): `vision.launch.py` з `camera_node source=<тека>`,
  перевірка `ros2 topic hz` і вмісту `/target`, `/decision`.
- **Yocto**: `bitbake` кожного нового рецепта окремо, потім образ; у rootfs
  перевіряється наявність модулів і моделі. Імпорт `ncnn`, `cv2`, `numpy` і
  запуск — на Pi (V4).

## Критерії приймання

| # | Тест | Очікування |
| --- | --- | --- |
| V1 | `evaluate.py` на test-сесії (камера Pi, інше місце) | mAP50, precision, recall у `report.md`; NCNN ≈ `.pt` (≤ 2 п.п.) |
| V2 | RPi OS: `rpi5os-detect --stream 8000` | рамка навколо предмета в браузері; рядок метрик раз на секунду |
| V3 | Заміри (imgsz 416 і 320, 60 с, зі стрімом і без) | таблиця FPS / infer ms / CPU / RAM / °C у README; ціль ≥ 10 FPS при 416 |
| V4 | SD з образом 1.2.0 | `rpicam-hello --list-cameras` бачить imx219; `rpi5os-detect` працює як у V2 |
| V5 | SD: `rpi5os-vision.service` | `ros2 node list`: три ноди; `ros2 topic hz /camera/image_raw`, `/target`, `/decision` (10 Гц) |
| V6 | Предмет ліворуч / праворуч / по центру | `/decision`: TURN_LEFT / TURN_RIGHT / MOVE_FORWARD |
| V7 | Предмет прибрали; низька впевненість (далеко, темно) | STOP |
| V8 | `kill` detector_node; камера без кадрів (зупинити `rpicam-vid`) | STOP ≤ 0.5 с; відновлення після перезапуску |
| V9 | Вийняти SD, ввімкнути | Raspberry Pi OS з SSD стартує як раніше |
| V10 | Нова модель через `scp` у `/var/lib/rpi5os-vision/model/` + restart | детектор використовує її без перепрошивки |

## Порядок робіт

1. `rpi5os_vision` + тести + COCO yolo11n у `models/current/` → V2 на RPi OS
   (з чашкою як ціллю).
2. Yocto: шари, libcamera, `rpicam-apps`, overlay, OpenCV, ncnn, `rpi5os-vision`
   → V4.
3. ROS 2: `vision_interfaces`, `vision_pkg`, тести на ПК, рецепти, сервіс →
   V5–V8.
4. Скрипти `train/` (паралельно з розміткою), своя модель → V1, V3, V10.
5. Реліз 1.2.0, README, заміри.
