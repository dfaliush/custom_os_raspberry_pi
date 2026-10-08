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
