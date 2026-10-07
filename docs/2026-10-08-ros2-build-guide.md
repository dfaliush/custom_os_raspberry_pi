# Як зібрати rpi5os з ROS 2: команди по порядку

Дата: 2026-10-08 · Статус: чернетка, доповнюється після першої збірки.

Що на виході: образ `rpi5os-yocto-v1.1.0-sdcard.img.xz` для Raspberry Pi 5
з ROS 2 Jazzy, нодами `counter_pkg` і systemd-сервісом, який їх запускає.
Усе робиться на Windows 10/11 через WSL 2. Buildroot-гілка ROS не має: у
Buildroot немає пакетів ROS 2, а завдання вимагає окремий meta-layer, тобто Yocto.

Етапи: 0) WSL → 1) ROS 2 на ПК → 2) пакет `counter_pkg` → 3) Yocto з
meta-ros → 4) образ на картку і перевірка на Pi → 5) реліз.

## 0. WSL 2 з Ubuntu 24.04

ROS 2 Jazzy ставиться з deb-пакетів лише на Ubuntu 24.04, Yocto 6.0 на ній
теж збирається, тож один дистрибутив на все. Диск WSL кладемо на D:, бо
збірка займає 100+ ГБ. У PowerShell:

```powershell
wsl --update                                   # WSL 2.x → 3.x, у списку з'являється Ubuntu-24.04
wsl --install Ubuntu-24.04 --location D:\wsl\Ubuntu-24.04 --no-launch
wsl -d Ubuntu-24.04 -u root -- bash -c 'useradd -m -s /bin/bash -G sudo dmytro; echo "dmytro ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dmytro; chmod 440 /etc/sudoers.d/dmytro; printf "[user]\ndefault=dmytro\n\n[boot]\nsystemd=true\n" > /etc/wsl.conf'
wsl --terminate Ubuntu-24.04
```

Ресурси для збірки (хост: 8 ядер, 16 ГБ): файл `C:\Users\<ти>\.wslconfig`,
діє після `wsl --shutdown`.

```ini
[wsl2]
memory=12GB
swap=16GB
processors=8
```

Хост-пакети Yocto (список з docs.yoctoproject.org, розділ Ubuntu):

```bash
sudo apt update && sudo apt install -y build-essential chrpath cpio debianutils diffstat file gawk gcc git \
  iputils-ping libacl1 liblz4-tool locales lz4 python3 python3-git python3-jinja2 python3-pexpect python3-pip \
  python3-subunit socat texinfo unzip wget xz-utils zstd bmap-tools rsync
```

## 1. ROS 2 Jazzy на ПК

За офіційною сторінкою «Ubuntu (deb packages)». Сторінка «Ubuntu (source)»
не потрібна: вона про збірку самого ROS 2 з вихідників для розробки ядра ROS.

```bash
sudo apt install -y locales software-properties-common curl
sudo locale-gen en_US en_US.UTF-8 && sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
sudo add-apt-repository -y universe
V=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | awk -F'"' '{print $4}')
curl -sL -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/$V/ros2-apt-source_$V.noble_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y ros-jazzy-ros-base ros-jazzy-demo-nodes-cpp ros-jazzy-demo-nodes-py ros-dev-tools
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
```

Перевірка на офіційних demo-нодах, два термінали:

```bash
ros2 run demo_nodes_cpp talker        # Publishing: 'Hello World: N'
ros2 run demo_nodes_py listener       # I heard: [Hello World: N]
ros2 node list                        # /talker /listener
```

Пастка: `setup.bash` не можна `source` під `set -u` (читає незадану
`AMENT_TRACE_SETUP_FILES`).

## 2. Пакет counter_pkg на ПК

Код у `ros2/counter_pkg/` (каркас від `ros2 pkg create --build-type
ament_python`). Робочий простір на ext4, пакет підключено посиланням:

```bash
mkdir -p ~/ros2_ws/src && ln -sfn /mnt/d/git/custom_os_raspberry_pi/ros2/counter_pkg ~/ros2_ws/src/counter_pkg
cd ~/ros2_ws && colcon build --symlink-install && colcon test && colcon test-result --verbose
source install/setup.bash
```

Запуск і перевірка (ноди, топік, сервіс): `ros2/README.md`. Коротко:
`ros2 launch counter_pkg counter.launch.py`, потім `ros2 node list`,
`ros2 topic echo /counter`, `ros2 run counter_pkg counter_control stop|start`.

Пастки Jazzy: `with rclpy.init()` є лише з Kilted; `std_msgs/Int32`
deprecated, тому `example_interfaces/msg/Int32`; ament-стиль docstring
(D208, D213) перевіряє `colcon test`.

## 3. Yocto-образ з ROS 2

### Шари

| Шар | Звідки | Навіщо |
| --- | --- | --- |
| `openembedded-core`, `bitbake` | тег `yocto-6.0.3`, клонує `build.sh` | базова система, Yocto 6.0 «wrynose» |
| `meta-raspberrypi` | прибитий коміт у `build.sh` | BSP Raspberry Pi 5 |
| `meta-openembedded` (`meta-oe`, `meta-python`) | submodule `yocto/layers/meta-openembedded`, гілка `wrynose` | залежності meta-ros |
| `meta-ros` (`meta-ros-common`, `meta-ros2`, `meta-ros2-jazzy`) | submodule `yocto/layers/meta-ros`, гілка `wrynose` | рецепти ROS 2 Jazzy |
| `meta-rpi5os` | репо | distro `rpi5os`, образ, Wi-Fi, SSH, перший старт |
| `meta-rpi5os-ros` | репо | **наш окремий ROS-шар**: рецепт `counter-pkg`, bbappend образу, профіль і systemd-сервіс |

Submodules додано так (коміти прибиті, `build.sh` читає їх з git-індексу
і клонує в WSL сам, тож `git submodule update` на Windows не обов'язковий):

```bash
git submodule add -b wrynose https://github.com/openembedded/meta-openembedded.git yocto/layers/meta-openembedded
git submodule add -b wrynose https://github.com/ros/meta-ros.git yocto/layers/meta-ros
git -C yocto/layers/meta-openembedded checkout 14282a02be9c74a1276a7cda7d6c89e054699a11   # пін з kas-конфігу meta-ros для wrynose
git -C yocto/layers/meta-ros checkout 95c08773cff114b3fe1a8c8f43643e59151bc8db            # HEAD гілки wrynose, 2026-09-16
git add yocto/layers .gitmodules
```

Що в `meta-rpi5os-ros`:

- `conf/layer.conf`: залежить від `rpi5os` і трьох шарів meta-ros; змінна
  `RPI5OS_ROS2_SRC` вказує на `ros2/` у репо (`build.sh` підміняє на копію в ext4).
- `recipes-ros/counter-pkg/counter-pkg_1.0.0.bb`: той самий `counter_pkg`,
  зібраний класом `ros_ament_python` з meta-ros, за зразком `demo-nodes-py`.
  Джерело `file://counter_pkg/`, тобто код не дублюється.
- `recipes-core/images/rpi5os-image.bbappend`: додає в образ `ros-workspace`,
  `ros-environment`, `rclpy`, `rmw-fastrtps-cpp`, `ros2cli` з розширеннями,
  `ros2launch`, `demo-nodes-py`, `counter-pkg`, `rpi5os-ros`.
- `recipes-core/rpi5os-ros/`: `/etc/profile.d/ros2.sh` (підключає
  `/opt/ros/jazzy/setup.sh` у кожному логін-шелі, `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`)
  і `rpi5os-counter.service` (запускає `counter.launch.py` при старті).

Що змінилося в `build.sh`: клонування двох нових шарів, `rsync` шару і
`ros2/` на ext4, `BBLAYERS` з шістьма новими записами, у `local.conf`
`ROS_DISTRO = "jazzy"`, `RPI5OS_ROS2_SRC`, `BB_NUMBER_THREADS`/`PARALLEL_MAKE`
з розрахунку 2 ГБ RAM на задачу, `ERROR_QA:remove = "license-exists"` (як у
kas-конфігах meta-ros). Версія образу `DISTRO_VERSION = "1.1.0"`.

### Збірка

З кореня репо у PowerShell (або ті самі `bash yocto/scripts/...` зсередини WSL):

```powershell
wsl -d Ubuntu-24.04 -- bash yocto/scripts/build.sh -p            # 1. клонує шари в ~/yocto, лише парсинг: помилки конфігурації видно за хвилини
wsl -d Ubuntu-24.04 -- bash yocto/scripts/build.sh counter-pkg   # 2. (необов'язково) лише наш рецепт і його залежності
wsl -d Ubuntu-24.04 -- bash yocto/scripts/build.sh               # 3. повний образ: ~/yocto/build/tmp/deploy/images/raspberrypi5/rpi5os-image-raspberrypi5.rootfs.wic
wsl -d Ubuntu-24.04 -- bash yocto/scripts/dist.sh                # 4. артефакти релізу в ~/yocto/dist
```

Перша збірка на 8 ядрах і 12 ГБ: _TODO: тривалість і розмір після збірки_.
Повторні збірки беруть sstate з `~/yocto/sstate`.

## 4. Картка і перевірка на Pi

Запис образу і перший вхід ті самі, що в README (розділи «Встановити готовий
образ» і «Yocto-образ»), hostname `rpi5os-yocto.local`. Далі на Pi:

```bash
ssh user@rpi5os-yocto.local
grep -E '^(NAME|VERSION_ID|IMAGE_ID)' /etc/os-release        # rpi5os, 1.1.0, rpi5os-yocto
systemctl status rpi5os-counter.service                     # active: publisher і subscriber уже працюють
ros2 node list                                              # /counter_publisher /counter_subscriber
ros2 topic echo /counter --once                             # data: N
ros2 run counter_pkg counter_control stop                   # counter stopped at N
ros2 run counter_pkg counter_control start                  # counter started at N+1
ros2 run demo_nodes_py talker                               # офіційна demo-нода, Ctrl-C
```

_TODO: фактичний вивід після перевірки на залізі._

## 5. Реліз

Тег `yocto-v1.1.0`, у GitHub Releases файли з `~/yocto/dist`:
`rpi5os-yocto-v1.1.0-sdcard.img.xz`, `SHA256SUMS`, `layers.txt`,
`license.manifest`, `*.spdx.json`.
