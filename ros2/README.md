# ros2/: ноди ROS 2 для rpi5os

Пакет `counter_pkg` (Python, `ament_python`, ROS 2 Jazzy): дві ноди і один
топік.

| Нода | Що робить |
| --- | --- |
| `counter_publisher` | раз на `period` с (1 с) публікує 1, 2, 3, … як `example_interfaces/msg/Int32` у топік `counter` |
| `counter_subscriber` | читає `counter`, пише `I heard: N`, попереджає про пропуски у послідовності |
| `counter_control` | клієнт сервісу: `counter_control start` або `stop` вмикає чи зупиняє лічильник і завершується |

Обидві ноди мають параметр `topic` (типово `counter`), publisher ще `period` і
`start_enabled` (типово `true`; з `false` лічильник чекає команди start).
`std_msgs/Int32` не використано навмисно: він deprecated із Foxy, рекомендована
заміна `example_interfaces`. Той самий пакет збирається у Yocto-образ через
meta-ros (див. `yocto/`).

## Збірка на ПК (WSL Ubuntu 24.04, ROS 2 Jazzy)

ROS 2 ставиться за офіційною інструкцією «Ubuntu (deb packages)»:
`ros-jazzy-ros-base`, `ros-jazzy-demo-nodes-cpp`, `ros-jazzy-demo-nodes-py`,
`ros-dev-tools`. Робочий простір на ext4, пакет підключено посиланням на репо:

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros2_ws/src && ln -sfn /mnt/d/git/custom_os_raspberry_pi/ros2/counter_pkg ~/ros2_ws/src/counter_pkg
cd ~/ros2_ws && colcon build --symlink-install && colcon test && colcon test-result
source install/setup.bash
```

## Запуск і перевірка (три термінали WSL)

У кожному терміналі спершу `source ~/ros2_ws/install/setup.bash`: `.bashrc`
підключає лише `/opt/ros/jazzy`, без цього `ros2 run` скаже
`Package 'counter_pkg' not found`. Після змін у коді: `cd ~/ros2_ws && colcon
build --symlink-install`, потім знову `source`.

**Термінал 1, publisher** (лишається запущеним):

```bash
ros2 run counter_pkg counter_publisher
# [counter_publisher]: publishing to "counter" every 1 s, running
# [counter_publisher]: published 1
# [counter_publisher]: published 2
```

**Термінал 2, subscriber** (лишається запущеним):

```bash
ros2 run counter_pkg counter_subscriber
# [counter_subscriber]: listening on "counter"
# [counter_subscriber]: I heard: 1
# [counter_subscriber]: I heard: 2
```

Замість двох терміналів можна один: `ros2 launch counter_pkg counter.launch.py`
піднімає обидві ноди разом.

**Термінал 3, команди ROS 2** і що вони мають показати:

```bash
ros2 node list                  # /counter_publisher, /counter_subscriber
ros2 topic list -t              # /counter [example_interfaces/msg/Int32]
ros2 topic info /counter        # Publisher count: 1, Subscription count: 1
ros2 node info /counter_publisher
ros2 topic echo /counter --once # data: N
ros2 topic hz /counter          # average rate: 1.000, Ctrl-C
ros2 interface show example_interfaces/msg/Int32
```

Якщо `ros2 node list` порожній, ноди в терміналах 1 і 2 не запущені або
впали; якщо вони працюють, а список усе одно порожній, скинь кеш графа:
`ros2 daemon stop`, і повтори команду.

## Service start/stop

Publisher тримає сервіс `/counter_publisher/enable` типу `std_srvs/srv/SetBool`
(`bool data` → `bool success, string message`): `data: true` запускає таймер,
`data: false` зупиняє. Значення не скидається, після start лічильник продовжує
з того місця, де зупинився, тому subscriber не бачить пропусків. Повторний
start чи stop нічого не ламає, відповідь `counter already running` або
`counter already stopped`. Параметр `start_enabled:=false` запускає publisher
одразу в зупиненому стані.

Керує лічильником окрема нода `counter_control`: вона викликає сервіс, друкує
відповідь і завершується з кодом 0 (успіх) або 1 (сервісу немає чи немає
відповіді). Власний `.srv` не створювався: стандартного `SetBool` достатньо, і
він є в meta-ros для Yocto.

**Перевірка.** Термінали 1 і 2 працюють, команди в терміналі 3:

```bash
ros2 service list -t | grep enable        # /counter_publisher/enable [std_srvs/srv/SetBool]
ros2 service type /counter_publisher/enable
ros2 interface show std_srvs/srv/SetBool
ros2 node info /counter_publisher         # Service Servers: /counter_publisher/enable

ros2 run counter_pkg counter_control stop     # [counter_control]: counter stopped at 7
ros2 topic hz /counter                        # нових повідомлень немає, Ctrl-C
ros2 run counter_pkg counter_control stop     # counter already stopped (ідемпотентно)
ros2 run counter_pkg counter_control start    # counter started at 8
ros2 topic echo /counter                      # data: 8, 9, 10, …, Ctrl-C
```

Поки лічильник зупинений, у терміналах 1 і 2 нові рядки не з'являються. Після
start publisher пише `counter started at 8`, `published 8`, subscriber
`I heard: 8` без попередження `gap`.

Те саме без ноди-клієнта, прямо з CLI:

```bash
ros2 service call /counter_publisher/enable std_srvs/srv/SetBool "{data: false}"
# response: std_srvs.srv.SetBool_Response(success=True, message='counter stopped at 7')
ros2 service call /counter_publisher/enable std_srvs/srv/SetBool "{data: true}"
# response: std_srvs.srv.SetBool_Response(success=True, message='counter started at 8')
```

## vision_pkg: камера → детектор → рішення

Ускладнений рівень завдання: відео передається між нодами, детектор визначає
положення предмета відносно центру кадру, окрема нода приймає рішення.
Детектор — пакет `rpi5os_vision` з `vision/` (YOLO11n у форматі NCNN).

```text
camera_node ──/camera/image_raw──► detector_node ──/target──► decision_node ──► /cmd_vel, /decision
              sensor_msgs/Image              vision_interfaces/TargetOffset     Twist, String
              bgr8 640×480, best effort      detected, confidence, dx, dy, area, class_name
```

| Нода | Параметри (типово) | Що робить |
| --- | --- | --- |
| `camera_node` | `source` (`camera`), `width` 640, `height` 480, `fps` 30, `loop` (`true`) | `rpicam-vid` або тека зображень/відео → `/camera/image_raw`; камера відпала — повтор раз на 2 с |
| `detector_node` | `model_dir` (`''`), `target_class` (`''` — будь-який), `conf` 0.25, `stream_port` 8000 | найсвіжіший кадр → YOLO → `/target` на кожен кадр; MJPEG з рамками на порту |
| `decision_node` | `conf_threshold` 0.6, `deadband` 0.15, `stale_timeout` 0.5, `rate` 10.0, `forward_speed` 0.2, `turn_speed` 0.5 | 10 Гц, незалежно від камери: STOP / TURN_LEFT / TURN_RIGHT / MOVE_FORWARD |

`dx`, `dy` у `[-1, 1]`: −1 — лівий/верхній край кадру, 0 — центр, +1 —
правий/нижній край. Рішення (`vision_pkg/decision.py`, тести —
`test/test_decision.py`):

| Умова | `/decision` | `/cmd_vel` |
| --- | --- | --- |
| `/target` не приходить довше `stale_timeout` (камера, детектор) | STOP | 0 |
| предмета немає або `confidence < conf_threshold` | STOP | 0 |
| `dx < −deadband` | TURN_LEFT | `angular.z = +turn_speed` |
| `dx > +deadband` | TURN_RIGHT | `angular.z = −turn_speed` |
| інакше | MOVE_FORWARD | `linear.x = forward_speed` |

Моторів немає: `/cmd_vel` публікується для контролера, якого в проєкті немає.

### Збірка і запуск на ПК (без камери)

`rpi5os_vision` береться з репо через `PYTHONPATH` (залежності — `vision/README.md`):

```bash
ln -sfn /mnt/d/git/custom_os_raspberry_pi/ros2/vision_interfaces ~/ros2_ws/src/
ln -sfn /mnt/d/git/custom_os_raspberry_pi/ros2/vision_pkg ~/ros2_ws/src/
cd ~/ros2_ws && colcon build --packages-select vision_interfaces vision_pkg
export PYTHONPATH=/mnt/d/git/custom_os_raspberry_pi/vision:$PYTHONPATH
colcon test --packages-select vision_pkg && colcon test-result     # 20 tests, 0 failures
source install/setup.bash
R=/mnt/d/git/custom_os_raspberry_pi/vision
ros2 launch vision_pkg vision.launch.py source:=$R/tests/data model_dir:=$R/models/coco-yolo11n target_class:=bus
```

`source:=<тека>` крутить зображення по колу замість камери. В іншому терміналі:

```bash
ros2 node list                    # /camera_node /decision_node /detector_node
ros2 topic echo /target --once    # detected: true, confidence: 0.90, dx: 0.02, class_name: bus
ros2 topic hz /decision           # average rate: 10.000
ros2 topic echo /decision         # data: MOVE_FORWARD
pkill -f lib/vision_pkg/detector_node   # через ~0.5 с: data: STOP
```

Перевірено в WSL: `/camera/image_raw` 29 Гц, детектор 27 fps (16 мс на кадр),
`/decision` 10 Гц; після `pkill` детектора STOP за 0,57 с (`stale_timeout`
0,5 с + один такт 10 Гц).
