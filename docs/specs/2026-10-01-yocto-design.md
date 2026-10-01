# rpi5os, ітерація 2: та сама ОС для Raspberry Pi 5 на Yocto

Дата: 2026-10-01 · Статус: реалізовано; T1–T7 пройдено на залізі 2026-10-02.
Рішення прийняті без окремого затвердження (за домовленістю «виконуй») і
чекають на перегляд.

## Завдання

Повторити ітерацію 1 ([buildroot-design](2026-10-01-buildroot-design.md)) через
Yocto: власний образ Linux для Raspberry Pi 5 з Wi-Fi і SSH, запис на microSD
тієї ж Pi, перевірка віддаленого входу, окремий реліз на GitHub.

Для користувача поведінка та сама, що в Buildroot-образі: ті самі файли на FAT,
ті самі команди, ті самі скрипти запису й перемикання SD ↔ SSD.

## Ключові рішення

| Рішення | Чому |
| --- | --- |
| Yocto **6.0.3 «Wrynose»** (LTS): `openembedded-core` і `bitbake` на тегу `yocto-6.0.3` | LTS, остання точкова версія; тег дає відтворюваність |
| `meta-raspberrypi` гілка `wrynose`, прибита до коміту `f62c679` | у шарі немає тегів релізів; machine `raspberrypi5`, kernel 6.18 |
| Без `poky` і `meta-yocto`: власний дистрибутив `rpi5os` у шарі `meta-rpi5os` | `poky` для нових релізів не ведеться; reference-дистрибутив тут не потрібен |
| Без `meta-openembedded` | `wpa_supplicant`, `openssh`, `avahi`, `sudo`, `iw`, `wireless-regdb`, `shadow` є в `openembedded-core` |
| systemd (не BusyBox init) | так задумано ще в ітерації 1: подивитись на systemd-варіант |
| Wi-Fi: upstream-unit `wpa_supplicant-nl80211@wlan0` + `systemd-networkd` (DHCP) | без власного аналога `S41wifi`; `LinkLocalAddressing=no`, тож `169.254.x.x` не з'являється |
| SSH: `sshd.socket` (типово в Yocto), опції в `sshd_config.d/10-rpi5os.conf` | `Include` стоїть на початку `sshd_config`, а в sshd виграє перше входження; `ssh-keys-only` правує тільки цей файл |
| Hostname **`rpi5os-yocto`** | видно, яка з двох систем піднялась; `known_hosts` для двох образів не конфліктують |
| FAT з міткою `RPI5OS-BOOT`, `umask=0077` (своя `.wks`) | ті самі інструкції в README (пошук диска за міткою), файли з паролями недоступні не-root |
| Збірка скриптом у WSL, робоча тека `~/yocto` на ext4 | як у Buildroot; без kas/bitbake-setup, щоб не додавати інструментів |
| Локаль `en_US.UTF-8` генерується в `~/yocto/locale` без root, якщо її немає в системі | bitbake вимагає саме її; `locale-gen` потребує `sudo` |

## Склад

```text
yocto/
├─ meta-rpi5os/
│  ├─ conf/layer.conf
│  ├─ conf/distro/rpi5os.conf            # systemd, hostname, DISTRO_VERSION = версія релізу
│  └─ recipes-core/
│     ├─ images/rpi5os-image.bb          # склад образу + rootfs-перевірки секретів
│     ├─ images/rpi5os-sdimage.wks       # FAT RPI5OS-BOOT (umask=0077) + ext4
│     ├─ os-release/os-release.bbappend  # VARIANT_ID, IMAGE_ID, IMAGE_VERSION
│     ├─ rpi5os-bootfs/                  # *.example на FAT
│     └─ rpi5os-scripts/                 # bootcfg, fallback, boot-ssd, ssh-keys-only, units
└─ scripts/
   ├─ build.sh                           # шари на прибитих ревізіях → bitbake rpi5os-image
   └─ dist.sh                            # .img.xz, layers.txt, license.manifest, SPDX, SHA256SUMS
```

Скрипти для Raspberry Pi OS (`flash-sd.sh`, `sd-boot.sh`, `boot-order.sh`) спільні
з ітерацією 1 і лежать у `buildroot/scripts/pi/`: вони працюють з будь-яким
образом із FAT першим розділом.

## Порядок старту

`boot.mount` (FAT → `/boot`) → `rpi5os-bootcfg.service` (користувач із
`userconf.txt` через `useradd`/`usermod`, Wi-Fi у
`/etc/wpa_supplicant/wpa_supplicant-nl80211-wlan0.conf`, обидва файли
видаляються з FAT) → `wpa_supplicant-nl80211@wlan0` + `systemd-networkd` →
`sshd.socket`, `avahi-daemon` → `rpi5os-fallback.service`.

## Відмінності від Buildroot-образу

| Що | Buildroot | Yocto |
| --- | --- | --- |
| init | BusyBox init, `S*`-скрипти | systemd, units |
| DHCP | `udhcpc -b` | `systemd-networkd` |
| link-local `169.254` | `avahi-autoipd` вішав, fallback фільтрує | вимкнено в `.network`, фільтр лишився |
| перевірка sshd у fallback | `pidof sshd` | `systemctl is-active sshd.socket` |
| користувач | `adduser` + правка `/etc/group` (BusyBox) | `useradd -m`, `usermod -aG wheel` (shadow) |
| kernel на FAT | `Image` | `kernel_2712.img` |
| регіон Wi-Fi | ще й `cfg80211.ieee80211_regdom=UA` у cmdline | тільки `country=` у `wpa_supplicant.conf` |

## Критерії приймання

Ті самі T0–T7, що в ітерації 1, з поправками:

| # | Тест | Очікування |
| --- | --- | --- |
| T1 | SD з образом, reboot | `rpi5os-yocto.local` резолвиться; вхід за паролем з `userconf.txt` |
| T2 | Це наша ОС | `os-release`: `NAME=rpi5os`, `VERSION_ID=1.0.0`, `IMAGE_ID=rpi5os-yocto`; root з `mmcblk0p2`; `nvme0n1*` не змонтовані |
| T3 | Ключ | після додавання ключа вхід з `BatchMode=yes`; після `ssh-keys-only` пароль відхиляється |
| T4 | Немає секретів | збірка падає, якщо в rootfs є host keys, `authorized_keys`, конфіг Wi-Fi або шлях `/home/<user>`; root locked |
| T5 | Reboot | ключ і Wi-Fi переживають перезавантаження |
| T6 | Автовідкат | з неправильним PSK і без конфігу Wi-Fi за ~3 хв Pi на SSD, причина в `rpi5os-boot.log` |
| T7 | Ручний відкат | `sudo boot-ssd && sudo reboot` → Raspberry Pi OS на NVMe |

## Реліз

Тег `yocto-v<VERSION>` у цьому репо. Assets: `rpi5os-yocto-v1.0.0-sdcard.img.xz`,
`SHA256SUMS`, `layers.txt` (ревізії шарів і `local.conf`), `license.manifest`,
`rpi5os-yocto-v1.0.0.spdx.json` (SBOM від `create-spdx`). Реліз робить
власник репо вручну.

## Знайдено під час реалізації

- **Firmware Wi-Fi не потрапляє в образ сам.** `meta-raspberrypi` додає
  `linux-firmware-rpidistro-bcm43455/43456` лише в `MACHINE_EXTRA_RRECOMMENDS`,
  а явний `IMAGE_INSTALL` їх не тягне. Знайшла статична перевірка rootfs до запису
  на SD; тепер пакети в `IMAGE_INSTALL`.
- **Цикл упорядкування systemd.** `rpi5os-bootcfg.service` з типовими
  залежностями (`After=basic.target`) і `Before=sshd.socket` давав цикл через
  `sockets.target`; systemd викидав одну з задач, система ставала `degraded`.
  Тепер `DefaultDependencies=no`, `After=local-fs.target`, `WantedBy=sysinit.target`.
- **bitbake вимагає саме `en_US.UTF-8`**, `C.UTF-8` не годиться. Без `sudo`
  локаль генерується `localedef` у `~/yocto/locale` і передається через `LOCPATH`.
- `DISTRO_FEATURES_BACKFILL_CONSIDERED` у 6.0 перейменовано на
  `DISTRO_FEATURES_OPTED_OUT`; `defaultsetup.conf` уже підключає uninative і
  `security_flags.inc`.

## Результати на залізі (Pi 5 Rev 1.1, 2026-10-02)

| # | Результат |
| --- | --- |
| T1 | старт з SD до SSH за ~33 с; `rpi5os-yocto.local` резолвиться |
| T2 | `NAME=rpi5os`, `IMAGE_ID=rpi5os-yocto`, kernel 6.18.33, root `mmcblk0p2`, NVMe не змонтовано, `systemctl is-system-running` = `running` |
| T3 | після `ssh-keys-only` сервер пропонує лише `publickey` |
| T4 | перевірка в `ROOTFS_POSTPROCESS_COMMAND` і в `dist.sh`; у rootfs, `.wic` і артефактах немає секретів та імені користувача збірки |
| T5 | після reboot ключ і Wi-Fi (5 ГГц, DHCP) працюють |
| T6 | неправильний PSK: `Not connected`, відкат на 185-й с; без конфігу: `Failed to open config file`, відкат на 185-й с |
| T7 | `sudo boot-ssd && sudo reboot` → Raspberry Pi OS на NVMe |

## Ризики

- Перша збірка — години і ~100–150 ГБ; WSL попереджає про ріст VHDX.
- `chrpath`, `diffstat`, `zstd` на хості збірки поставлено без root у
  `~/.local/bin`; постійно — `sudo apt install chrpath diffstat zstd`.
- Bluetooth не налаштований: firmware `BCM4345C0.hcd` в образі немає, у журналі
  є відповідна помилка kernel. На Wi-Fi і SSH це не впливає.
