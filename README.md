# rpi5os: власна ОС для Raspberry Pi 5 на Buildroot

Власний образ Linux для Raspberry Pi 5, зібраний через Buildroot: SSH,
Wi-Fi, запис на плату і віддалений вхід. Ітерація 2 (поруч, у `yocto/`) — та сама
задача через Yocto.

Головна думка: перейти від «Linux, який ми налаштували руками» до
«Linux, який можна гарантовано зібрати ще раз». Тому в репо лежить не образ,
а **рецепт**: версія Buildroot прибита тегом, наші зміни — у `BR2_EXTERNAL`,
одна команда дає той самий `sdcard.img`. Готовий образ — у GitHub Releases.

Дизайн і всі рішення з обґрунтуванням: [`docs/specs/2026-10-01-buildroot-design.md`](docs/specs/2026-10-01-buildroot-design.md).

## Що всередині образу

| Шар | Що | Навіщо |
| --- | --- | --- |
| Kernel | `bcm2712` з форку raspberrypi/linux, фіксований коміт | Pi 5 (BCM2712 + RP1) |
| Init | BusyBox init, eudev | мінімально; eudev сам вантажить `brcmfmac` |
| Wi-Fi | firmware CYW43455, `wpa_supplicant`, `wireless-regdb`, `iw` | у стенду тільки Wi-Fi, 5 ГГц, `country=UA` |
| SSH | OpenSSH (`sshd` + `sftp-server`) | `scp`/`sftp` з Windows працюють |
| mDNS | Avahi, hostname `rpi5os` | `ssh user@rpi5os.local` без пошуку IP |
| Адмін | `sudo` для групи `wheel` | |

Чого в образі **немає навмисно**: SSH-ключів, паролів (root заблокований),
Wi-Fi PSK, host keys (генеруються на першому старті, тож вони свої на кожному
пристрої). Образ публічний, і це перевіряє `post-build.sh`: збірка падає, якщо
щось із цього потрапило в rootfs.

## Стенд

| Що | Деталі |
| --- | --- |
| Плата | Raspberry Pi 5 Model B Rev 1.1, 8 ГБ |
| Основна ОС | Raspberry Pi OS trixie на NVMe SSD, `ssh user@raspberrypi`. **SSD не чіпаємо** |
| rpi5os | на microSD у слоті тієї ж Pi (`/dev/mmcblk0`) |
| Мережа | тільки Wi-Fi |
| Збірка | Windows 11 + WSL2 Ubuntu 22.04 (24 ядра, 31 ГБ RAM) |

## Структура

```text
custom_os_raspberry_pi/
├─ docs/specs/                    # дизайн
└─ buildroot/                     # BR2_EXTERNAL, name: RPI5OS
   ├─ configs/rpi5os_defconfig    # raspberrypi5_defconfig + наші зміни (розмічено в файлі)
   ├─ VERSION                     # версія образу → /etc/os-release, ім'я релізу
   ├─ board/rpi5os/
   │  ├─ config.txt, cmdline.txt  # boot-розділ: kernel=Image, regdom=UA
   │  ├─ genimage.cfg.in          # розмітка SD: boot 64M (FAT) + rootfs ext4
   │  ├─ post-build.sh            # sshd_config, lock root, /boot у fstab, перевірка секретів
   │  ├─ post-image.sh            # sdcard.img + приклади конфігів на FAT
   │  ├─ bootfs/*.example         # шаблони wpa_supplicant.conf і userconf.txt
   │  └─ rootfs-overlay/          # init-скрипти й утиліти rpi5os
   └─ scripts/
      ├─ build.sh                 # WSL: від нуля до sdcard.img
      ├─ dist.sh                  # WSL: .img.xz, .config, manifest ліцензій, SHA256SUMS
      ├─ flash-to-pi.sh           # Git Bash: образ → microSD Pi по ssh
      └─ pi/                      # виконуються на Raspberry Pi OS
         ├─ flash-sd.sh           # dd на mmcblk0 з перевірками + конфіги на FAT
         ├─ sd-boot.sh            # on|off|status: увімкнути/вимкнути SD-завантаження
         └─ boot-order.sh         # sd-first|restore|show: BOOT_ORDER в EEPROM
```

## Зібрати

Разово поставити залежності у WSL:

```bash
sudo apt install build-essential unzip bc libncurses-dev rsync cpio file wget git
```

Збірка (перший раз ~30–60 хв, далі інкрементально):

```powershell
wsl -d Ubuntu -- bash buildroot/scripts/build.sh
wsl -d Ubuntu -- bash buildroot/scripts/dist.sh
```

`build.sh` копіює `buildroot/` у `~/br/external` (на ext4, з явними правами),
клонує Buildroot `2026.02.3` у `~/br/buildroot` і збирає в `~/br/output`.
Результат: `~/br/output/images/sdcard.img`, артефакти релізу — у `~/br/dist/`.

> **Пастки WSL.** (1) Збирати тільки на ext4 (`~`), не на `/mnt/d`: drvfs не
> тримає права й регістр імен. (2) WSL дописує в `PATH` теки Windows з
> пробілами, і Buildroot відмовляється стартувати («Your PATH contains
> spaces»). `build.sh` вирізає з `PATH` усе, що на `/mnt/`.

## Пастки, знайдені на залізі

- **Pi 5 Rev 1.1 = кремній D0, потрібен `overlays/bcm2712d0.dtbo`.** Firmware
  бере базовий `bcm2712-rpi-5-b.dtb` і накладає на нього цей overlay
  (`vclog -m` на Raspberry Pi OS: `Loaded overlay 'bcm2712d0'`). У
  `raspberrypi5_defconfig` overlays вимкнені, і перший образ падав у kernel
  panic за 2–4 с: rootfs жодного разу не змонтувався (`tune2fs -l`:
  `Mount count: 0`), зелений LED горів рівно, без кодів помилки.
  `post-image.sh` тепер кладе overlay з того ж дерева kernel і падає, якщо його немає.
- **Без монітора й UART діагностували так:** `vclog -m` (лог bootloader),
  `tune2fs -l` на rootfs SD (чи доходило до монтування), час від reboot до
  повернення на SSD, і **`tryboot`**: на FAT немає `config.txt`, є
  `tryboot.txt`; звичайний boot SD пропускає (`[sdcard] config.txt not found`
  → NVMe), а `sudo reboot "0 tryboot"` один раз запускає rpi5os. З
  `panic=10 rootwait=30` у cmdline будь-яке падіння саме повертало Pi на SSD.
- **BusyBox `addgroup user group` не працює** без `FEATURE_ADDUSER_TO_GROUP`,
  а в skeleton немає `/home`. Обидва мовчки ламали `userconf.txt`: вхід за
  паролем був, але без home і без `sudo`. `S30bootcfg` тепер створює home
  явно, дописує `wheel` у `/etc/group` і пише результат у лог.
- **Пакет `wpa_supplicant` кладе свій `/etc/wpa_supplicant.conf`** з
  `network={key_mgmt=NONE}` («до будь-якої відкритої мережі»). Його ловить
  перевірка секретів у `post-build.sh`, файл видаляється.
- **`nmcli -g` екранує `:` і `\`**: `flash-sd.sh` читає SSID/PSK з `--escape no`.
- **`udhcpc` при `leasefail` запускає `avahi-autoipd`**, і той вішає на `wlan0`
  `169.254.x.x`. Перша версія `S99fallback` рахувала будь-яку IPv4 і писала
  `OK: 169.254.x.x/16`, доки DHCP ще не відповів. З неправильним PSK або
  без роутера Pi лишилась би на SD недосяжною. Тепер link-local не рахується.
  Перевірено на залізі: з `psk="wrong"` відкат на SSD через ~200 с, у лог
  записано `wpa_state=SCANNING`.

## Записати на microSD Pi

Записуємо прямо з Raspberry Pi OS на SSD у microSD тієї ж Pi; образ і
тимчасові файли лежать у `/dev/shm` (RAM), на SSD нічого не пишеться.

**1. Пароль першого входу** (робиш сам, пароль нікуди не передається відкритим):

Зайти на Pi (`ssh user@raspberrypi`) і вже там виконати (openssl двічі спитає пароль):

```bash
printf 'user:%s\n' "$(openssl passwd -6)" > /dev/shm/rpi5os-userconf.txt
```

На Pi лягає тільки sha512-crypt hash, і той у RAM.

**2. Запис** (Git Bash):

```bash
bash buildroot/scripts/flash-to-pi.sh //wsl.localhost/Ubuntu/home/<user>/br/dist/rpi5os-buildroot-v1.0.0-sdcard.img.xz
```

`flash-sd.sh` на Pi перевіряє, що ціль — справді microSD (`TRAN=mmc`, не
носій `/` чи `/boot/firmware`), пише `dd`, звіряє sha256 записаного і кладе на
FAT-розділ `userconf.txt` та `wpa_supplicant.conf`. Wi-Fi береться з активного
з'єднання NetworkManager на самій Pi: PSK не виходить за її межі.

**3. Порядок завантаження.** У Pi стояло `BOOT_ORDER=0xf146` (NVMe першим),
з таким microSD ніколи не стартує. Ставимо SD першою:

```bash
ssh user@raspberrypi "sudo bash /dev/shm/boot-order.sh sd-first && sudo reboot"
```

З вийнятою або вимкненою SD Pi сама йде на NVMe.

## Перший вхід

```bash
ssh user@rpi5os.local                      # пароль з кроку 1
```

Ключ додається вже в живу систему (у образі ключів немає):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh user@rpi5os.local "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

> Якщо `type … | ssh` у PowerShell 5.1 нічого не дописав (файл лишився
> порожнім) — встав ключ прямо в команду: `ssh … "echo 'ssh-ed25519 AAAA…' >> ~/.ssh/authorized_keys"`.

Перевірити вхід за ключем і вимкнути паролі:

```bash
ssh -o BatchMode=yes user@rpi5os.local true && ssh -t user@rpi5os.local sudo ssh-keys-only
```

`ssh-keys-only` відмовиться, якщо `authorized_keys` порожній: так неможливо
відрізати собі доступ.

## Як воно стартує

`mount -a` (FAT-розділ → `/boot`, `umask=0077`) → `S10udev` (вантажить
`brcmfmac`) → `S30bootcfg` (створює користувача з `userconf.txt`, переносить
`wpa_supplicant.conf` у `/etc`, **видаляє обидва з FAT**) → `S41wifi`
(`wpa_supplicant` + `udhcpc -b`) → `sshd`, `avahi-daemon` → `S99fallback`.

Чому `S41wifi`, а не `ifupdown` з `inet dhcp`: ifupdown запускає `udhcpc -n`,
який здається після кількох спроб, а асоціація з точкою на 5 ГГц буває довшою.

## Відкат на SSD

Wi-Fi тут єдиний канал: rpi5os, яка не вийшла в мережу, була б недосяжна.

- **Автоматично.** `S99fallback` чекає 3 хв IPv4 на `wlan0` і живий `sshd`.
  Не дочекався → пише діагностику в `/boot/rpi5os-boot.log`, вимикає SD
  (`boot-ssd`) і перезавантажується. Pi стартує з SSD, лог видно звідти:
  `sudo bash /dev/shm/sd-boot.sh status`. Вимкнути автовідкат: покласти
  порожній `no-fallback` на FAT-розділ.
- **Вручну з rpi5os:** `sudo boot-ssd && sudo reboot`.
- **Знову на rpi5os з SSD:** `sudo bash /dev/shm/sd-boot.sh on && sudo reboot`.
- **Повністю повернути як було:** `sudo bash /dev/shm/boot-order.sh restore`.

«Вимкнути SD» означає перенести boot-файли в `disabled/` на тому ж FAT:
без `config.txt` і kernel bootloader вважає картку порожньою і йде далі по
`BOOT_ORDER`.

## Реліз

Тег `buildroot-v<VERSION>` (Yocto-ітерація отримає `yocto-v<VERSION>`).
Assets з `~/br/dist/`: `.img.xz`, `SHA256SUMS`, `buildroot.config`,
`legal-info-manifest.csv` (пакети, версії, ліцензії).

Записати реліз без збірки: завантажити `.img.xz`, перевірити `sha256sum -c
SHA256SUMS`, далі розділ «Записати на microSD Pi» (або Raspberry Pi Imager →
Use custom, потім підкласти `userconf.txt` і `wpa_supplicant.conf` на FAT за
прикладами `*.example`).
