# rpi5os, ітерація 1: власна ОС для Raspberry Pi 5 на Buildroot

Дата: 2026-10-01 · Статус: затверджено в обговоренні, реалізація йде

## Мета

Зібрати власний образ Linux для Raspberry Pi 5 через Buildroot
(<https://gitlab.com/buildroot.org/buildroot>), додати SSH, записати образ на
microSD цієї ж Pi, перевірити віддалений вхід і опублікувати реліз на GitHub.

Ітерація 2 (окремий spec): та сама задача через Yocto, свій реліз.

## Вихідні умови (перевірено на залізі)

| Що | Значення |
| --- | --- |
| Плата | Raspberry Pi 5 Model B Rev 1.1, 8 ГБ, 4 ядра |
| Робоча ОС зараз | Raspberry Pi OS trixie на **NVMe SSD** (`nvme0n1`): `/` і `/boot/firmware` |
| microSD | `mmcblk0`, 58 ГБ, старий Raspberry Pi OS: **перезаписуємо** |
| Мережа | **тільки Wi-Fi**: `wlan0`, 5 ГГц, DHCP, regdomain `UA`. Ethernet не підключений |
| Доступ | `ssh user@raspberrypi` (ключ `id_ed25519` з Windows-машини) |
| EEPROM | `BOOT_ORDER=0xf146`: NVMe → USB → SD |
| Машина збірки | Windows 11 + WSL2 Ubuntu 22.04, 24 ядра, 31 ГБ RAM, 950 ГБ |

## Обмеження від замовника

- **SSD не чіпати.** На NVMe нічого не пишемо і не змонтовуємо з rpi5os.
- **В образі немає SSH-ключа.** Ключ додається вже в піднятій системі.
- Образ іде в **публічний** реліз: у ньому немає жодного секрету (ключів,
  паролів, Wi-Fi PSK, host keys).

## Ключові рішення

| Рішення | Чому |
| --- | --- |
| Buildroot **2026.02.3** (LTS), прибитий тегом | відтворюваність; LTS отримує security-фікси |
| Основа: `configs/raspberrypi5_defconfig` | kernel `bcm2712` з форку raspberrypi/linux на фіксованому коміті, toolchain Bootlin |
| Збірка локально у WSL2, тека `~/br` на ext4 | швидко (24 ядра); на `/mnt/d` ламаються регістр імен і права |
| Наша частина як `BR2_EXTERNAL` у репо, Buildroot у репо не кладемо | у git лише «рецепт», бінарники тільки в релізі |
| BusyBox init | мінімально; systemd побачимо в Yocto-ітерації |
| eudev | автозавантаження `brcmfmac` за modalias, без нього `wlan0` не з'являється |
| Wi-Fi: `brcmfmac_sdio-firmware-rpi`, `wpa_supplicant`, `wireless-regdb`, `iw`; `cfg80211.ieee80211_regdom=UA` | чип CYW43455; regdb потрібна для 5 ГГц каналів |
| OpenSSH (не Dropbear) | потрібен `sftp-server`: сучасний `scp` ходить через SFTP |
| Avahi, hostname `rpi5os` | `ssh user@rpi5os.local` без пошуку IP у роутері |
| `BOOT_ORDER=0xf461` (SD → NVMe → USB) | щоб стартувала SD; без картки Pi іде на SSD сама |

## Доступ: як потрапити в систему без вшитого ключа

1. В образі є тільки `root` із **заблокованим** паролем (`*`) і `PermitRootLogin no`.
2. Після запису SD на FAT-розділ кладуться два файли:
   - `userconf.txt` — рядок `ім'я:hash`, hash з `openssl passwd -6` (як у Raspberry Pi Imager);
   - `wpa_supplicant.conf` — SSID і PSK.
3. `S30bootcfg` при старті створює користувача (група `wheel` → `sudo`),
   переносить Wi-Fi конфіг у `/etc` (600) і **видаляє обидва файли з FAT**.
4. `sshd` стартує з `PasswordAuthentication yes`, host keys генерує `ssh-keygen -A`
   при першому старті, тож на кожному пристрої вони свої.
5. Перший вхід за паролем → `ssh-copy-id` → `sudo ssh-keys-only`
   (перевіряє непорожній `authorized_keys` і лише тоді вимикає паролі).

## Склад репо

```text
custom_os_raspberry_pi/
├─ README.md
├─ docs/specs/                         # цей файл
└─ buildroot/                          # BR2_EXTERNAL (name: RPI5OS)
   ├─ external.desc, external.mk, Config.in, VERSION
   ├─ configs/rpi5os_defconfig
   ├─ board/rpi5os/
   │  ├─ config.txt, cmdline.txt, genimage.cfg.in (boot 64M)
   │  ├─ post-build.sh                 # fstab /boot, lock root, sshd_config, sudoers, os-release, перевірка секретів
   │  ├─ post-image.sh                 # genimage + приклади конфігів на bootfs
   │  ├─ bootfs/*.example
   │  └─ rootfs-overlay/
   │     ├─ etc/init.d/S30bootcfg, S41wifi, S99fallback
   │     ├─ usr/sbin/boot-ssd, ssh-keys-only
   │     └─ usr/lib/rpi5os/common.sh   # log() у /boot/rpi5os-boot.log
   └─ scripts/
      ├─ build.sh                      # WSL: rsync external на ext4 → clone тегу → defconfig → make
      ├─ flash-to-pi.sh                # запис на mmcblk0 Pi по ssh
      ├─ dist.sh                       # артефакти релізу в ~/br/dist (реліз: gh release create)
      └─ pi/flash-sd.sh, sd-boot.sh, boot-order.sh   # виконуються на Raspberry Pi OS
```

## Порядок старту rpi5os

`mount -a` (з `/boot`) → S10udev (brcmfmac) → S30bootcfg → S40network (`lo`)
→ S41wifi (`wpa_supplicant -B`, `udhcpc -b`) → S50sshd, S50avahi-daemon → S99fallback.

`udhcpc -b`, а не `ifupdown inet dhcp`: ifupdown запускає `udhcpc -n`, і той
здається, якщо асоціація з точкою доступу затягнулась.

## Відкат

Wi-Fi єдиний канал, тому rpi5os, яка не вийшла в мережу, недосяжна. Два механізми:

- **Автовідкат `S99fallback`:** якщо за 180 с немає IPv4 на `wlan0` або не працює
  `sshd`, діагностика йде в `/boot/rpi5os-boot.log`, потім `boot-ssd` і `reboot`.
  Вимикається файлом `/boot/no-fallback`. Озброєний лише до першого успішного
  виходу в мережу (маркер `/var/lib/rpi5os/network-ok`): інакше відключення
  світла, після якого роутер стартує довше за Pi, назавжди вимикало SD
  (виправлено 2026-10-08).
- **`boot-ssd`** (вручну або з fallback): переносить усі boot-файли SD у
  `/boot/disabled/`. Без `config.txt` і kernel bootloader іде до наступного
  пристрою з `BOOT_ORDER`, тобто на NVMe. `scripts/pi/sd-boot.sh on` з Raspberry
  Pi OS повертає файли на місце.

Те, що bootloader Pi 5 справді переходить на NVMe за порожньої SD, **не задокументовано
явно**, тому це перший тест (T0) до того, як на цей механізм покладатися.

## Запис на SD (`flash-to-pi.sh`)

1. `scp` образу на Pi.
2. Перевірки перед `dd`: ціль `/dev/mmcblk0`, `TRAN=mmc`, на ній не змонтовано
   `/` чи `/boot/firmware`, розмір картки ≥ розміру образу. Інакше зупинка.
3. Відмонтування старих розділів SD, `dd conv=fsync`, звірка sha256 записаного.
4. `wpa_supplicant.conf` генерується **на Pi** з активного NetworkManager-з'єднання
   (`nmcli -s`): PSK не проходить через Windows-машину.
5. `userconf.txt` створює замовник сам (`openssl passwd -6`), пароль не проходить через агента.
6. EEPROM (`pi/boot-order.sh sd-first`): бекап поточного конфігу, потім `BOOT_ORDER=0xf461`.
   `flashrom` на Pi немає, тож `rpi-eeprom-config --apply` кладе `pieeprom.upd/.sig` і
   `recovery.bin` у `/boot/firmware` на SSD; bootloader споживає їх на наступному reboot.
   Це єдиний запис на SSD у всьому процесі, потребує окремого «так» від замовника.

## Критерії приймання

| # | Тест | Очікування |
| --- | --- | --- |
| T0 | SD записана, `sd-boot.sh off`, reboot | Pi на NVMe, `ssh user@raspberrypi` працює |
| T1 | `sd-boot.sh on`, reboot | `rpi5os.local` резолвиться; `ssh user@rpi5os.local` за паролем |
| T2 | Це наша ОС | `os-release`: Buildroot 2026.02.3, `IMAGE_VERSION=1.0.0`; `findmnt /` = `mmcblk0p2`; `nvme0n1*` не змонтовані |
| T3 | Ключ у живій системі | після `ssh-copy-id` вхід з `BatchMode=yes`; після `ssh-keys-only` пароль відхиляється |
| T4 | Немає секретів в образі | у `output/target` і в rootfs.ext4 немає `ssh_host_*`, `authorized_keys`, `wpa_supplicant.conf`, root locked |
| T5 | Reboot | ключ і Wi-Fi переживають перезавантаження |
| T6 | Автовідкат | без `wpa_supplicant.conf` за ~3 хв Pi на SSD, причина в `rpi5os-boot.log` |
| T7 | Ручний відкат | `sudo boot-ssd && sudo reboot` → `raspberrypi` на NVMe |

## Реліз

- Тег `buildroot-v<VERSION>` у цьому репо; Yocto-ітерація отримає `yocto-v…`.
- Assets: `rpi5os-buildroot-v1.0.0-sdcard.img.xz`, `SHA256SUMS`, `buildroot.config` (повний `.config`),
  `legal-info-manifest.csv` (з `make legal-info`: ліцензії й версії пакетів).
- Потрібен `gh` + `gh auth login` (робить замовник). Push тегу і публікація — лише після окремого підтвердження.

## Поза scope

Yocto (ітерація 2), CI-збірка, A/B-оновлення, підпис образу, Bluetooth, Ethernet, systemd.

## Ризики / відкриті питання

- Перехід bootloader на NVMe за порожньої SD — перевіряє T0.
- Фізичний доступ до Pi не підтверджено: автовідкат закриває випадок «немає мережі»,
  але не випадок «kernel не завантажився» (тоді bootloader не дійде до S99fallback,
  але й SD-завантаження впаде → швидше за все, Pi сама піде на NVMe; перевірити не можна без зламаного образу).
- Wi-Fi на 5 ГГц з DFS-каналом може асоціюватися повільніше: 180 с з запасом.

## План реалізації

1. `BR2_EXTERNAL` + `build.sh`, перша збірка, T4 на артефактах.
2. README проєкту (як зібрати, записати, зайти, відкотитися).
3. `scripts/pi/sd-boot.sh`, `flash-to-pi.sh`; запис SD; T0.
4. `userconf.txt` від замовника; EEPROM; T1–T3, T5.
5. T6, T7; повернення Pi у стан, який обере замовник.
6. `dist.sh` + `gh release create`, реліз після підтвердження.
